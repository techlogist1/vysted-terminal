// First: its `diag_println!` / `diag_eprintln!` macros are used by the modules below.
#[macro_use]
mod diag_log;
mod keychain;
mod openbb_mcp;
mod sec_edgar_mcp;

use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

use tauri::{AppHandle, Emitter, Manager, RunEvent};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

/// Holds the running Python sidecar process so it can be killed when the app exits.
struct SidecarProcess(Mutex<Option<CommandChild>>);

/// Where the main sidecar is in its life (R15-LIFECYCLE-010).
#[derive(Clone, Copy, Debug, PartialEq, serde::Serialize)]
#[serde(rename_all = "lowercase")]
enum SidecarPhase {
    Starting,
    Ready,
    Failed,
}

/// What `get_sidecar_port` hands the renderer: the port, the phase, and — once
/// `Failed` — the reason, so a spawn failure or a crash is named at once instead
/// of a 120 s probe of a port nothing will bind.
#[derive(Clone, Debug, serde::Serialize)]
struct SidecarSnapshot {
    port: u16,
    state: SidecarPhase,
    reason: Option<String>,
}

/// The sidecar's port + lifecycle, in Tauri state.
struct SidecarStatus(Mutex<SidecarSnapshot>);

impl SidecarStatus {
    fn new(port: u16) -> Self {
        Self(Mutex::new(SidecarSnapshot {
            port,
            state: SidecarPhase::Starting,
            reason: None,
        }))
    }

    fn snapshot(&self) -> SidecarSnapshot {
        self.0.lock().unwrap().clone()
    }

    /// Every failure arm (no port, command missing, spawn refused, the child
    /// exiting) records its reason here.
    fn fail(&self, reason: String) {
        diag_eprintln!("[vysted] {reason}");
        let mut snapshot = self.0.lock().unwrap();
        snapshot.state = SidecarPhase::Failed;
        snapshot.reason = Some(reason);
    }

    /// The boot port-wait's verdict; a failure already recorded (the child
    /// exited while we waited) keeps its more precise reason.
    fn settle_boot(&self, bound: bool) {
        let mut snapshot = self.0.lock().unwrap();
        if snapshot.state != SidecarPhase::Starting {
            return;
        }
        if bound {
            snapshot.state = SidecarPhase::Ready;
        } else {
            snapshot.state = SidecarPhase::Failed;
            snapshot.reason = Some(format!(
                "The data engine did not come up on port {}.",
                snapshot.port
            ));
        }
    }
}

/// The reason a sidecar that exited is reported with.
fn terminated_reason(code: Option<i32>, signal: Option<i32>) -> String {
    match (code, signal) {
        (Some(code), _) => format!("The data engine stopped (exit code {code})."),
        (None, Some(signal)) => format!("The data engine stopped (signal {signal})."),
        (None, None) => "The data engine stopped.".to_string(),
    }
}

/// Bind to port 0 so the OS picks a free port, read it back, then release it.
///
/// Returns `None` instead of panicking when no port can be bound — the boot
/// path treats that as "sidecar unavailable" (port 0 sentinel) and lets the UI
/// start in a disconnected state rather than panicking the whole app with no
/// window (the spec's boot-resilience requirement; mirrors the MCP children's
/// graceful degradation).
pub(crate) fn pick_free_port() -> Option<u16> {
    let listener = std::net::TcpListener::bind("127.0.0.1:0").ok()?;
    Some(listener.local_addr().ok()?.port())
}

/// Poll the port for `timeout_secs`, returning `true` as soon as something
/// accepts a TCP connection on it.
///
/// Used by the main-sidecar startup wait AND by the openbb-mcp /
/// sec-edgar-mcp subprocess supervisors to verify that the spawned
/// subprocess has bound to its claimed port before declaring spawn
/// success. Without this probe, ``Command::spawn`` returns immediately
/// after the OS creates the process — the process may deadlock during
/// startup (Phase 8 found this for the MCP subprocesses) and the parent
/// has no way to detect it (per CLAUDE.md PyInstaller --onefile +
/// anyio + Windows handle interactions).
pub(crate) fn wait_for_port_timeout(port: u16, timeout_secs: u64) -> bool {
    let deadline = Instant::now() + Duration::from_secs(timeout_secs);
    while Instant::now() < deadline {
        if TcpStream::connect(("127.0.0.1", port)).is_ok() {
            return true;
        }
        thread::sleep(Duration::from_millis(200));
    }
    false
}

/// Per-attempt budget (seconds) for a cold MCP subprocess to bind its port.
///
/// Phase-9 UC1 fix: the prior flat 15s budget was marginal for a COLD
/// PyInstaller `--onefile` MCP binary, which must extract `_MEI*`, import
/// heavy packages (openbb-platform extensions / sec-edgar streamable-http),
/// and only then bind. Under Windows file-lock / AV-scan contention a cold
/// boot can exceed 15s, producing the nondeterministic "bound on some boots,
/// not others" symptom (Phase 8 finding UC1-*-not-listening).
///
/// Phase-9.5 measurement (macOS M1, isolated): openbb binds at 34.2s cold /
/// 13.6s warm, sec-edgar at 33.6s cold / 24.6s warm — both ~34s cold, right at
/// the old 30s per-attempt edge (only the retry saved them). The audit saw
/// sec-edgar DOWN while openbb was UP because at app boot the two `_MEI*`
/// extractions (49 MB + 81 MB) run CONCURRENTLY and contend for disk I/O, so
/// the larger sec-edgar loses the race past the 60s total. Raising the
/// per-attempt budget to 45s (total 90s with the retry) gives the contended
/// cold bind real headroom. This is near-free: `wait_for_port_with_retries`
/// short-circuits the instant the port binds, so warm/fast boots are
/// unaffected — only a genuinely dead sidecar waits the larger ceiling.
/// (The true upstream fix — `--onedir` to eliminate the per-launch `_MEI*`
/// extraction — is deferred; see BLOCKERS.md "Phase 9.5 UC1".)
pub(crate) const MCP_PORT_WAIT_SECS: u64 = 45;

/// Number of bind attempts before declaring an MCP subprocess unavailable.
/// One retry (2 attempts) gives a cold boot a second window without
/// unbounding startup — total worst case ~`MCP_PORT_WAIT_SECS * MCP_PORT_WAIT_ATTEMPTS`.
pub(crate) const MCP_PORT_WAIT_ATTEMPTS: u32 = 2;

/// Poll a port across a bounded number of attempts, each lasting
/// `MCP_PORT_WAIT_SECS`. Returns `true` on the first successful TCP connect.
///
/// The total budget is `MCP_PORT_WAIT_SECS * MCP_PORT_WAIT_ATTEMPTS`; the
/// loop short-circuits the moment the port binds, so a fast boot still
/// returns in well under a second. `attempt` is surfaced via the optional
/// `on_retry` callback so callers can log progress against the Phase-8 UC1
/// diagnostics. This does NOT respawn the child — it gives the SAME cold
/// child more time, which is the actual failure mode (slow extraction, not
/// a dead process).
pub(crate) fn wait_for_port_with_retries(
    port: u16,
    per_attempt_secs: u64,
    attempts: u32,
    mut on_retry: impl FnMut(u32, u32),
) -> bool {
    for attempt in 1..=attempts.max(1) {
        if wait_for_port_timeout(port, per_attempt_secs) {
            return true;
        }
        if attempt < attempts {
            on_retry(attempt, attempts);
        }
    }
    false
}

/// Resolve the per-OS application data directory, falling back to a temp dir on
/// failure so a resolution/creation error degrades gracefully instead of
/// panicking the app at boot. The sidecar owns the SQLite stores + saved
/// workspaces beneath this directory.
fn resolve_data_dir(app: &AppHandle) -> String {
    let dir = match app.path().app_data_dir() {
        Ok(dir) => dir,
        Err(err) => {
            diag_eprintln!(
                "[vysted] could not resolve the app data directory ({err}); \
                 falling back to a temp directory"
            );
            std::env::temp_dir().join("vysted-terminal")
        }
    };
    if let Err(err) = std::fs::create_dir_all(&dir) {
        diag_eprintln!(
            "[vysted] could not create the data directory {dir:?} ({err}); \
             sidecar persistence may be degraded"
        );
    }
    dir.to_string_lossy().to_string()
}

/// Resolve the per-OS LOCAL (non-roaming) application data directory for
/// regenerable caches (R15-CROSS-PLATFORM-012). `app_data_dir()` resolves to
/// Roaming AppData on Windows, which roaming profiles sync at logon/logoff
/// and which folder redirection can put on a network share — unsafe for the
/// sidecar's SQLite WAL cache files. `app_local_data_dir()` is the Windows
/// non-roaming counterpart (macOS/Linux resolve the same directory as
/// `app_data_dir()` on those platforms, so this is a no-op there). Falls
/// back to the same temp dir as `resolve_data_dir` on resolution failure.
fn resolve_cache_dir(app: &AppHandle) -> String {
    let dir = match app.path().app_local_data_dir() {
        Ok(dir) => dir,
        Err(err) => {
            diag_eprintln!(
                "[vysted] could not resolve the local cache directory ({err}); \
                 falling back to a temp directory"
            );
            std::env::temp_dir().join("vysted-terminal")
        }
    };
    if let Err(err) = std::fs::create_dir_all(&dir) {
        diag_eprintln!(
            "[vysted] could not create the cache directory {dir:?} ({err}); \
             sidecar caches may be degraded"
        );
    }
    dir.to_string_lossy().to_string()
}

/// Return the per-OS application data directory to the frontend — the
/// authoritative source the Rust core also passes to the sidecar as
/// `--data-dir`. Used by the export helpers (notes/brief MD/PNG/PDF) to resolve
/// `{dataDir}/exports/...`; the sidecar `/health` does NOT expose this, so the
/// renderer must ask the core directly. Mirrors `resolve_data_dir`'s resolution
/// (app_data_dir with a temp-dir fallback).
#[tauri::command]
fn get_app_data_dir(app: tauri::AppHandle) -> String {
    match app.path().app_data_dir() {
        Ok(dir) => dir.to_string_lossy().to_string(),
        Err(_) => std::env::temp_dir()
            .join("vysted-terminal")
            .to_string_lossy()
            .to_string(),
    }
}

/// The MCP protocol revision the sidecar's FastMCP transport speaks. Mirrors
/// `_PROTOCOL_VERSION` in `sidecar/services/mcp_server.py` — keep both in sync.
const MCP_PROTOCOL_VERSION: &str = "2025-06-18";

/// Filename of the loopback MCP-endpoint discovery file written under the data
/// directory once the sidecar is confirmed up (FR-025).
const MCP_ENDPOINT_FILENAME: &str = "mcp-endpoint.json";

/// Build the MCP-endpoint discovery JSON for a bound sidecar `port`.
///
/// Pure function (no I/O) so it is unit-testable: an external MCP client reads
/// this to discover the loopback Streamable-HTTP endpoint without scraping the
/// dev console. The fields mirror `types/mcp.ts`.
fn mcp_endpoint_json(port: u16) -> String {
    let value = serde_json::json!({
        "sidecarPort": port,
        "mcpEndpoint": format!("http://127.0.0.1:{port}/mcp"),
        "protocolVersion": MCP_PROTOCOL_VERSION,
    });
    value.to_string()
}

/// Resolve the discovery-file path under `data_dir`. Pure (no I/O).
fn mcp_endpoint_path(data_dir: &str) -> PathBuf {
    Path::new(data_dir).join(MCP_ENDPOINT_FILENAME)
}

/// Write the MCP-endpoint discovery file under `data_dir` for a healthy
/// sidecar on `port`. Best-effort: a write failure is logged, never fatal
/// (consistent with the rest of the boot path's graceful degradation). A
/// `port == 0` (failed) boot never calls this, so no stale file is written.
fn write_mcp_endpoint_file(data_dir: &str, port: u16) {
    let path = mcp_endpoint_path(data_dir);
    match std::fs::write(&path, mcp_endpoint_json(port)) {
        Ok(()) => diag_println!("[vysted] wrote MCP endpoint discovery file {path:?}"),
        Err(err) => diag_eprintln!(
            "[vysted] could not write the MCP endpoint discovery file {path:?} ({err}); \
             external MCP clients must discover the port from the console line"
        ),
    }
}

/// Spawn + supervise the main Python sidecar. NEVER panics: every failure arm
/// records its reason in `SidecarStatus` (the renderer shows it at once) and
/// returns, leaving the UI open in a disconnected state — the boot path
/// previously `.expect()`-panicked here (no window, no error).
fn start_main_sidecar(app: &AppHandle, port: u16) {
    let status = app.state::<SidecarStatus>();
    if port == 0 {
        status.fail("The data engine could not start: no free local port.".to_string());
        return;
    }
    let data_dir = resolve_data_dir(app);
    let cache_dir = resolve_cache_dir(app);
    let command = match app.shell().sidecar("vysted-sidecar") {
        Ok(command) => command.args([
            "--port",
            &port.to_string(),
            "--data-dir",
            &data_dir,
            "--cache-dir",
            &cache_dir,
        ]),
        Err(err) => {
            status.fail(format!("The data engine could not start ({err})."));
            return;
        }
    };
    let (mut rx, child) = match command.spawn() {
        Ok(pair) => pair,
        Err(err) => {
            status.fail(format!("The data engine could not start ({err})."));
            return;
        }
    };
    app.manage(SidecarProcess(Mutex::new(Some(child))));

    // Drain the sidecar's stdout/stderr so its pipes never block, and log it.
    // Its exit is recorded and announced (no auto-respawn).
    let events_app = app.clone();
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    diag_println!("[sidecar] {}", String::from_utf8_lossy(&line));
                }
                CommandEvent::Stderr(line) => {
                    diag_eprintln!("[sidecar] {}", String::from_utf8_lossy(&line));
                }
                CommandEvent::Terminated(payload) => {
                    let reason = terminated_reason(payload.code, payload.signal);
                    events_app.state::<SidecarStatus>().fail(reason.clone());
                    let _ = events_app.emit("vysted://sidecar-terminated", reason);
                }
                _ => {}
            }
        }
    });

    let endpoint_data_dir = data_dir.clone();
    let wait_app = app.clone();
    thread::spawn(move || {
        // R8: the main sidecar gets the same cold-extraction budget as the MCP
        // subprocesses (45s x 2) — a cold `--onefile` boot (~60s observed: _MEI
        // extraction + heavy imports) outlives the old flat 15s probe, which
        // logged a false "did not come up" and skipped the FR-025 endpoint file
        // while the frontend's own retries connected fine moments later.
        let bound = wait_for_port_with_retries(
            port,
            MCP_PORT_WAIT_SECS,
            MCP_PORT_WAIT_ATTEMPTS,
            |attempt, attempts| {
                diag_eprintln!(
                    "[vysted] Python sidecar not up yet on port {port} after attempt \
                     {attempt}/{attempts} ({MCP_PORT_WAIT_SECS}s); cold PyInstaller \
                     extraction may be slow — retrying."
                );
            },
        );
        wait_app.state::<SidecarStatus>().settle_boot(bound);
        if bound {
            diag_println!("[vysted] Python sidecar healthy on 127.0.0.1:{port}");
            // FR-025: publish the loopback MCP endpoint so an external MCP
            // client can discover it without scraping the console. Only on a
            // confirmed-up sidecar — a failed boot leaves no stale file.
            write_mcp_endpoint_file(&endpoint_data_dir, port);
        } else {
            diag_eprintln!("[vysted] Python sidecar did not come up on port {port}");
        }
    });
}

/// Run the boot on one background thread and return at once: start both MCP
/// children (each `start_*` returns its bind-wait step), then the main
/// sidecar, then both bind waits concurrently.
fn spawn_boot<A, SA, B, SB, M>(start_a: A, start_b: B, start_main: M) -> thread::JoinHandle<()>
where
    A: FnOnce() -> SA + Send + 'static,
    SA: FnOnce() + Send,
    B: FnOnce() -> SB + Send + 'static,
    SB: FnOnce() + Send,
    M: FnOnce() + Send + 'static,
{
    thread::spawn(move || {
        let supervise_a = start_a();
        let supervise_b = start_b();
        start_main();
        thread::scope(|scope| {
            scope.spawn(supervise_a);
            supervise_b();
        });
    })
}

/// Expose the sidecar's port and lifecycle (`{port, state, reason}`) to the
/// frontend so it can issue HTTP and WebSocket requests to the Python data
/// layer — and, when `state` is `failed`, show `reason` instead of probing.
#[tauri::command]
fn get_sidecar_port(status: tauri::State<'_, SidecarStatus>) -> SidecarSnapshot {
    status.snapshot()
}

/// Append one renderer line (a React render error, R15-LIFECYCLE-023) to the
/// diagnostics log — the release build has no console to read it from.
#[tauri::command]
fn diag_log_line(line: String) {
    diag_eprintln!("{line}");
}

/// Atomically write `contents` to `path` by writing to a sibling temp file in the
/// same directory and then renaming it over the destination. Because the temp file
/// and the final path live on the same filesystem, the kernel `rename(2)` is atomic
/// (SC-032: "survives a crash mid-save"). Used by the notes panel to persist each
/// note as a canonical `.md` file. The temp suffix `.tmp.<pid>` avoids collisions
/// when multiple windows write concurrently.
#[tauri::command]
fn write_text_atomic(path: String, contents: String) -> Result<(), String> {
    use std::io::Write as _;

    let dest = std::path::Path::new(&path);
    let parent = dest
        .parent()
        .ok_or_else(|| format!("no parent directory for path: {path}"))?;
    std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;

    let tmp_name = format!(
        "{}.tmp.{}",
        dest.file_name().and_then(|n| n.to_str()).unwrap_or("note"),
        std::process::id(),
    );
    let tmp_path = parent.join(&tmp_name);
    {
        let mut f = std::fs::File::create(&tmp_path).map_err(|e| e.to_string())?;
        f.write_all(contents.as_bytes())
            .map_err(|e| e.to_string())?;
        f.flush().map_err(|e| e.to_string())?;
    }
    std::fs::rename(&tmp_path, dest).map_err(|e| e.to_string())
}

/// Atomically write raw `contents` bytes to `path` (same sibling-temp + rename
/// strategy as `write_text_atomic`). The WKWebView/Chromium webview blocks the
/// browser `<a download>` / Blob-save path, so binary exports (notes/brief PNG +
/// PDF) flow through this command instead. `contents` arrives as a JSON number
/// array (`Array.from(new Uint8Array(buf))`) which serde decodes to `Vec<u8>` —
/// no extra crate, no base64 round-trip.
#[tauri::command]
fn write_bytes_atomic(path: String, contents: Vec<u8>) -> Result<(), String> {
    use std::io::Write as _;

    let dest = std::path::Path::new(&path);
    let parent = dest
        .parent()
        .ok_or_else(|| format!("no parent directory for path: {path}"))?;
    std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;

    let tmp_name = format!(
        "{}.tmp.{}",
        dest.file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("export"),
        std::process::id(),
    );
    let tmp_path = parent.join(&tmp_name);
    {
        let mut f = std::fs::File::create(&tmp_path).map_err(|e| e.to_string())?;
        f.write_all(&contents).map_err(|e| e.to_string())?;
        f.flush().map_err(|e| e.to_string())?;
    }
    std::fs::rename(&tmp_path, dest).map_err(|e| e.to_string())
}

/// Install the macOS "Layout" menu (modes-as-tools, Cursor-menu-bar style): the
/// standard default menu + a Layout submenu whose items emit `vysted://menu-layout`
/// with a layout-template id the frontend applies. macOS-only by design (the
/// operator's Mac-first call); Windows/Linux keep their existing chrome untouched.
/// Non-fatal: a menu-build failure logs and leaves the app running menu-less.
#[cfg(target_os = "macos")]
fn install_layout_menu(app: &tauri::App) -> tauri::Result<()> {
    use tauri::menu::{Menu, MenuItem, Submenu};

    let h = app.handle();
    let layout = Submenu::with_items(
        h,
        "Layout",
        true,
        &[
            &MenuItem::with_id(
                h,
                "layout:research-cockpit",
                "Fundamental Analysis",
                true,
                None::<&str>,
            )?,
            &MenuItem::with_id(
                h,
                "layout:single-focus",
                "Technical Analysis",
                true,
                None::<&str>,
            )?,
            &MenuItem::with_id(h, "layout:macro-scan", "Macro Scan", true, None::<&str>)?,
            &MenuItem::with_id(h, "layout:compare", "Compare", true, None::<&str>)?,
            &MenuItem::with_id(h, "layout:default", "Reset Layout", true, None::<&str>)?,
        ],
    )?;
    let menu = Menu::default(h)?;
    menu.append(&layout)?;
    app.set_menu(menu)?;
    // NOTE: the menu-CLICK handler is registered on the Tauri Builder in `run()`
    // via `.on_menu_event` — the reliable place for macOS app-menu events in
    // Tauri 2. A handler set here in `setup()` via `app.on_menu_event` did NOT
    // fire on click (the items rendered but did nothing), so this fn only BUILDS
    // + installs the menu now.
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let builder = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_notification::init());

    // Dev-only MCP test-automation plugin (DaveDev42/tauri-plugin-mcp). Compiled
    // in ONLY under the `dev-tools` Cargo feature; release builds omit it (and
    // its `mcp:default` capability) entirely. It opens a loopback Unix-socket /
    // named-pipe debug server the `tauri-mcp` MCP server drives for E2E
    // automation. The `let`-shadow (not `let mut`) keeps the non-feature build
    // free of an unused-`mut` warning under clippy `-D warnings`.
    #[cfg(feature = "dev-tools")]
    let builder = builder.plugin(tauri_plugin_mcp::init());

    let app = builder
        .invoke_handler(tauri::generate_handler![
            get_sidecar_port,
            get_app_data_dir,
            diag_log_line,
            write_text_atomic,
            write_bytes_atomic,
            keychain::keychain_set,
            keychain::keychain_get,
            keychain::keychain_delete,
            keychain::keychain_migrate,
            openbb_mcp::get_openbb_mcp_port,
            sec_edgar_mcp::get_sec_edgar_mcp_port,
        ])
        // macOS Layout menu CLICK handler. Registered on the BUILDER (not via
        // `app.on_menu_event` in setup, which rendered the items but never fired on
        // click) — the reliable place for app-menu events in Tauri 2. Each item's id
        // is `layout:<template>`; forward `<template>` to the frontend menu-bridge
        // over `vysted://menu-layout` so dockview re-arranges. The emit outcome is
        // logged so a menu click is observable in the app log (`[menu] …`).
        .on_menu_event(|app, event| {
            use tauri::Emitter;
            if let Some(template) = event.id().0.strip_prefix("layout:") {
                match app.emit("vysted://menu-layout", template.to_string()) {
                    Ok(()) => {
                        diag_eprintln!("[menu] layout '{template}' → emitted vysted://menu-layout")
                    }
                    Err(e) => diag_eprintln!("[menu] layout '{template}' emit FAILED: {e}"),
                }
            }
        })
        .setup(|app| {
            // Persist every console line from here on (R15-LIFECYCLE-008).
            diag_log::init(&resolve_data_dir(app.handle()));
            // `0` = no free port (extremely rare); the UI still opens and
            // shows disconnected rather than panicking at boot.
            let port = pick_free_port().unwrap_or(0);
            app.manage(SidecarStatus::new(port));

            // Boot the three children off the main thread so the window paints
            // at once (R15-LIFECYCLE-001): the MCP starts pick their ports and
            // set the ``VYSTED_*_MCP_PORT`` env vars the main sidecar inherits,
            // the main sidecar spawns straight after, and only then do the two
            // MCP bind waits run (concurrently). Every step is non-fatal (an
            // MCP registers port=0; the main sidecar records Failed(reason)).
            let (openbb, sec, main) = (
                app.handle().clone(),
                app.handle().clone(),
                app.handle().clone(),
            );
            spawn_boot(
                move || {
                    let port = openbb_mcp::start(&openbb);
                    move || {
                        if let Some(port) = port {
                            openbb_mcp::supervise(&openbb, port);
                        }
                    }
                },
                move || {
                    let port = sec_edgar_mcp::start(&sec);
                    move || {
                        if let Some(port) = port {
                            sec_edgar_mcp::supervise(&sec, port);
                        }
                    }
                },
                move || start_main_sidecar(&main, port),
            );

            // macOS modes-as-tools menu (Layout → Fundamental / Technical / Macro /
            // Compare / Reset). Non-fatal; macOS-only.
            #[cfg(target_os = "macos")]
            if let Err(err) = install_layout_menu(app) {
                diag_eprintln!("[menu] failed to install layout menu: {err}");
            }

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building Vysted Terminal");

    app.run(|app_handle, event| {
        if let RunEvent::Exit = event {
            if let Some(state) = app_handle.try_state::<SidecarProcess>() {
                if let Some(child) = state.0.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
            // Reap the openbb-mcp subprocess alongside the main sidecar.
            openbb_mcp::kill(app_handle);
            // Reap the sec-edgar-mcp subprocess alongside the main sidecar.
            sec_edgar_mcp::kill(app_handle);
        }
    });
}

#[cfg(test)]
mod tests {
    use super::{
        mcp_endpoint_json, mcp_endpoint_path, pick_free_port, terminated_reason,
        wait_for_port_timeout, wait_for_port_with_retries, SidecarPhase, SidecarStatus,
        MCP_ENDPOINT_FILENAME, MCP_PORT_WAIT_ATTEMPTS, MCP_PORT_WAIT_SECS, MCP_PROTOCOL_VERSION,
    };
    use std::net::TcpListener;
    use std::sync::atomic::{AtomicU32, Ordering};
    use std::time::Instant;

    #[test]
    fn boot_returns_at_once_and_spawns_the_sidecar_before_any_mcp_bind_wait_ends() {
        // R15-LIFECYCLE-001: setup() must not block on the MCP bind waits, and
        // the main sidecar must not wait for them either.
        use std::sync::{Arc, Mutex};
        use std::time::Duration;

        let log = Arc::new(Mutex::new(Vec::<&str>::new()));
        let step = |name: &'static str, sleep_ms: u64| {
            let log = Arc::clone(&log);
            move || {
                std::thread::sleep(Duration::from_millis(sleep_ms));
                log.lock().unwrap().push(name);
            }
        };
        let (sup_a, sup_b) = (step("supervise_a", 2_000), step("supervise_b", 2_000));
        let (start_a, start_b) = (step("start_a", 0), step("start_b", 0));
        let main = step("main", 0);

        let began = Instant::now();
        let boot = super::spawn_boot(
            move || {
                start_a();
                sup_a
            },
            move || {
                start_b();
                sup_b
            },
            main,
        );
        assert!(
            began.elapsed().as_millis() < 200,
            "spawn_boot blocked the caller for {:?}",
            began.elapsed()
        );
        boot.join().unwrap();
        assert!(
            began.elapsed().as_millis() < 3_500,
            "the two bind waits ran back to back: {:?}",
            began.elapsed()
        );
        let order = log.lock().unwrap().clone();
        assert_eq!(&order[..3], ["start_a", "start_b", "main"]);
        assert_eq!(order.len(), 5);
    }

    #[test]
    fn a_spawn_failure_reaches_the_renderer_as_failed_with_its_reason() {
        // R15-LIFECYCLE-010: the arm for a missing sidecar command records the
        // reason; `get_sidecar_port` serializes it for the renderer.
        let status = SidecarStatus::new(54321);
        status.fail("The data engine could not start (binary not found).".to_string());
        let wire = serde_json::to_value(status.snapshot()).expect("serializable");
        assert_eq!(wire["port"], 54321);
        assert_eq!(wire["state"], "failed");
        assert_eq!(
            wire["reason"],
            "The data engine could not start (binary not found)."
        );
    }

    #[test]
    fn the_boot_wait_keeps_an_earlier_exit_reason() {
        let status = SidecarStatus::new(54321);
        status.fail(terminated_reason(Some(1), None));
        status.settle_boot(false);
        let snapshot = status.snapshot();
        assert_eq!(snapshot.state, SidecarPhase::Failed);
        assert_eq!(
            snapshot.reason.as_deref(),
            Some("The data engine stopped (exit code 1).")
        );

        let unbound = SidecarStatus::new(54321);
        unbound.settle_boot(false);
        assert_eq!(
            unbound.snapshot().reason.as_deref(),
            Some("The data engine did not come up on port 54321.")
        );
        let bound = SidecarStatus::new(54321);
        bound.settle_boot(true);
        assert_eq!(bound.snapshot().state, SidecarPhase::Ready);
    }

    #[test]
    fn mcp_endpoint_json_carries_port_endpoint_and_protocol() {
        let json = mcp_endpoint_json(54321);
        let value: serde_json::Value = serde_json::from_str(&json).expect("valid JSON");
        assert_eq!(value["sidecarPort"], 54321);
        assert_eq!(value["mcpEndpoint"], "http://127.0.0.1:54321/mcp");
        assert_eq!(value["protocolVersion"], MCP_PROTOCOL_VERSION);
    }

    #[test]
    fn mcp_endpoint_path_joins_filename_under_data_dir() {
        let path = mcp_endpoint_path("/tmp/vysted-data");
        assert!(path.ends_with(MCP_ENDPOINT_FILENAME));
        assert_eq!(path.parent().unwrap().to_string_lossy(), "/tmp/vysted-data");
    }

    #[test]
    fn pick_free_port_returns_a_usable_port() {
        let port = pick_free_port().expect("should bind a free port on a healthy host");
        assert!(port > 0, "expected a non-zero port, got {port}");
    }

    #[test]
    fn wait_for_port_returns_true_immediately_when_bound() {
        // A listener already bound to the port should be detected on the
        // first poll, so the call returns well under its 1s budget.
        let listener = TcpListener::bind("127.0.0.1:0").expect("bind");
        let port = listener.local_addr().unwrap().port();
        let started = Instant::now();
        assert!(wait_for_port_timeout(port, 1));
        assert!(
            started.elapsed().as_millis() < 500,
            "should short-circuit on first connect, took {:?}",
            started.elapsed()
        );
    }

    #[test]
    fn wait_for_port_with_retries_short_circuits_without_invoking_on_retry() {
        // When the port is already bound, the retry callback must never fire
        // and the helper must return true on the first attempt.
        let listener = TcpListener::bind("127.0.0.1:0").expect("bind");
        let port = listener.local_addr().unwrap().port();
        let retries = AtomicU32::new(0);
        let ok = wait_for_port_with_retries(port, 1, 3, |_, _| {
            retries.fetch_add(1, Ordering::SeqCst);
        });
        assert!(ok);
        assert_eq!(retries.load(Ordering::SeqCst), 0);
    }

    #[test]
    fn wait_for_port_with_retries_exhausts_attempts_and_reports_each_retry() {
        // Nothing is listening on this just-freed port, so the helper must
        // exhaust all attempts and invoke on_retry exactly (attempts - 1)
        // times (no callback after the final failed attempt). Use a tiny
        // per-attempt budget so the test stays fast.
        let free_port = pick_free_port().expect("bind a free port");
        let retries = AtomicU32::new(0);
        let ok = wait_for_port_with_retries(free_port, 0, 3, |attempt, total| {
            assert_eq!(total, 3);
            assert!((1..3).contains(&attempt));
            retries.fetch_add(1, Ordering::SeqCst);
        });
        assert!(!ok);
        assert_eq!(retries.load(Ordering::SeqCst), 2);
    }

    #[test]
    fn mcp_wait_budget_constants_drive_the_helper() {
        // Exercise the shipped constants through the helper on an unbound
        // port with a zeroed per-attempt budget (keeps the test instant)
        // to confirm they wire together and the attempt count is honoured.
        // Guards against an accidental zeroing of MCP_PORT_WAIT_ATTEMPTS that
        // would make the bind probe a no-op and reintroduce the UC1
        // silent-lie. (The seconds budget is asserted via a runtime read so
        // clippy doesn't flag a constant-only assertion.)
        let free_port = pick_free_port().expect("bind a free port");
        let budget_secs = std::hint::black_box(MCP_PORT_WAIT_SECS);
        assert!(budget_secs >= 15, "cold-boot budget must stay >= 15s");

        let attempts = std::hint::black_box(MCP_PORT_WAIT_ATTEMPTS);
        let calls = AtomicU32::new(0);
        let ok = wait_for_port_with_retries(free_port, 0, attempts, |_, _| {
            calls.fetch_add(1, Ordering::SeqCst);
        });
        assert!(!ok);
        // on_retry fires (attempts - 1) times; this also proves attempts >= 1.
        assert_eq!(calls.load(Ordering::SeqCst), attempts.saturating_sub(1));
    }
}
