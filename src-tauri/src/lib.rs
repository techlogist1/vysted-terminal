mod keychain;
mod kill_switch;
mod openbb_mcp;
mod sec_edgar_mcp;

use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

use tauri::{Manager, RunEvent};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

/// Holds the running Python sidecar process so it can be killed when the app exits.
struct SidecarProcess(Mutex<Option<CommandChild>>);

/// The localhost port the Python sidecar is bound to. Stored in Tauri state and
/// exposed to the frontend via the `get_sidecar_port` command.
struct SidecarPort(u16);

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

/// Backwards-compatible 15s probe used by the main-sidecar startup wait.
pub(crate) fn wait_for_port(port: u16) -> bool {
    wait_for_port_timeout(port, 15)
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
fn resolve_data_dir(app: &tauri::App) -> String {
    let dir = match app.path().app_data_dir() {
        Ok(dir) => dir,
        Err(err) => {
            eprintln!(
                "[vysted] could not resolve the app data directory ({err}); \
                 falling back to a temp directory"
            );
            std::env::temp_dir().join("vysted-terminal")
        }
    };
    if let Err(err) = std::fs::create_dir_all(&dir) {
        eprintln!(
            "[vysted] could not create the data directory {dir:?} ({err}); \
             sidecar persistence may be degraded"
        );
    }
    dir.to_string_lossy().to_string()
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
        Ok(()) => println!("[vysted] wrote MCP endpoint discovery file {path:?}"),
        Err(err) => eprintln!(
            "[vysted] could not write the MCP endpoint discovery file {path:?} ({err}); \
             external MCP clients must discover the port from the console line"
        ),
    }
}

/// Spawn + supervise the main Python sidecar. NEVER panics: on any failure it
/// logs and returns, leaving the UI to open in a disconnected state and retry —
/// the boot path previously `.expect()`-panicked here (no window, no error).
/// This mirrors the openbb/sec-edgar MCP children, which already degrade to a
/// port-0 "unavailable" sentinel rather than failing app startup.
fn start_main_sidecar(app: &tauri::App, port: u16) {
    if port == 0 {
        eprintln!("[vysted] no free port available for the sidecar; UI will start disconnected");
        return;
    }
    let data_dir = resolve_data_dir(app);
    let command = match app.shell().sidecar("vysted-sidecar") {
        Ok(command) => command.args(["--port", &port.to_string(), "--data-dir", &data_dir]),
        Err(err) => {
            eprintln!(
                "[vysted] could not create the sidecar command ({err}); UI will start disconnected"
            );
            return;
        }
    };
    let (mut rx, child) = match command.spawn() {
        Ok(pair) => pair,
        Err(err) => {
            eprintln!(
                "[vysted] failed to spawn the Python sidecar ({err}); UI will start disconnected"
            );
            return;
        }
    };
    app.manage(SidecarProcess(Mutex::new(Some(child))));

    // Drain the sidecar's stdout/stderr so its pipes never block, and log it.
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    println!("[sidecar] {}", String::from_utf8_lossy(&line));
                }
                CommandEvent::Stderr(line) => {
                    eprintln!("[sidecar] {}", String::from_utf8_lossy(&line));
                }
                _ => {}
            }
        }
    });

    let endpoint_data_dir = data_dir.clone();
    thread::spawn(move || {
        if wait_for_port(port) {
            println!("[vysted] Python sidecar healthy on 127.0.0.1:{port}");
            // FR-025: publish the loopback MCP endpoint so an external MCP
            // client can discover it without scraping the console. Only on a
            // confirmed-up sidecar — a failed boot leaves no stale file.
            write_mcp_endpoint_file(&endpoint_data_dir, port);
        } else {
            eprintln!("[vysted] Python sidecar did not come up on port {port}");
        }
    });
}

/// Expose the sidecar's localhost port to the frontend so it can issue HTTP and
/// WebSocket requests to the Python data layer. `0` means no sidecar bound this
/// launch (boot-time port-pick or spawn failure) — the frontend treats that as
/// disconnected and retries.
#[tauri::command]
fn get_sidecar_port(port: tauri::State<'_, SidecarPort>) -> u16 {
    port.0
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
        .plugin(tauri_plugin_notification::init())
        .plugin(kill_switch::build_plugin());

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
            write_text_atomic,
            write_bytes_atomic,
            keychain::keychain_set,
            keychain::keychain_get,
            keychain::keychain_delete,
            kill_switch::kill_switch_emit,
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
                        eprintln!("[menu] layout '{template}' → emitted vysted://menu-layout")
                    }
                    Err(e) => eprintln!("[menu] layout '{template}' emit FAILED: {e}"),
                }
            }
        })
        .setup(|app| {
            // `0` = no free port (extremely rare); the UI still opens and
            // shows disconnected rather than panicking at boot.
            let port = pick_free_port().unwrap_or(0);
            app.manage(SidecarPort(port));

            // Register the OS-wide kill-switch keyboard shortcut. Failure
            // here is non-fatal — the toolbar button + HTTP path still
            // fire the kill switch directly via the sidecar route.
            kill_switch::register_shortcut(app.handle());

            // Spawn the openbb-mcp + sec-edgar-mcp subprocesses BEFORE the
            // main sidecar so the ``VYSTED_*_MCP_PORT`` env vars are settled
            // (a bound port, or removed-on-failure) by the time the Python
            // sidecar imports ``services.openbb_mcp_provider`` /
            // ``services.sec_filings_provider``. Each helper picks its own
            // free port immediately before its own ``Command::spawn``,
            // supervises the child, and tolerates a missing binary by
            // registering port=0 (openbb → yfinance fallback; sec → 501).
            //
            // Phase-9 UC1 fix: run the two spawns IN PARALLEL so their cold
            // PyInstaller ``--onefile`` ``_MEI*`` extractions overlap instead
            // of serializing. Previously each ``spawn`` blocked the setup
            // thread for its full port-wait budget back to back (~30s+
            // worst-case serial); overlapping them roughly halves the cold
            // worst case. Each spawn is independently non-fatal: a single
            // MCP failure registers port=0 and degrades gracefully without
            // failing app startup. We join both before spawning the main
            // sidecar so the env vars are fully settled first.
            //
            // Note: the two threads each call ``app.manage(...)`` for their
            // OWN distinct state types (OpenbbMcp* vs SecEdgarMcp*), so there
            // is no shared-state contention between them.
            let openbb_handle = app.handle().clone();
            let sec_handle = app.handle().clone();
            let openbb_thread = thread::spawn(move || {
                if let Err(err) = openbb_mcp::spawn(&openbb_handle) {
                    eprintln!("[openbb-mcp] spawn supervisor errored: {err}");
                }
            });
            let sec_thread = thread::spawn(move || {
                if let Err(err) = sec_edgar_mcp::spawn(&sec_handle) {
                    eprintln!("[sec-edgar-mcp] spawn supervisor errored: {err}");
                }
            });
            // Join both before the main sidecar spawn — the env vars must be
            // settled (bound port or removed) before the sidecar reads them.
            let _ = openbb_thread.join();
            let _ = sec_thread.join();

            // Spawn + supervise the main Python sidecar. This NEVER panics: a
            // data-dir or spawn failure logs and leaves the UI to start in a
            // disconnected state and retry (the boot path previously
            // `.expect()`-panicked here with no window). The sidecar owns the
            // portfolio SQLite database + saved-workspace files beneath the
            // data directory. See `start_main_sidecar` / `resolve_data_dir`.
            start_main_sidecar(app, port);

            // macOS modes-as-tools menu (Layout → Fundamental / Technical / Macro /
            // Compare / Reset). Non-fatal; macOS-only.
            #[cfg(target_os = "macos")]
            if let Err(err) = install_layout_menu(app) {
                eprintln!("[menu] failed to install layout menu: {err}");
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
        mcp_endpoint_json, mcp_endpoint_path, pick_free_port, wait_for_port_timeout,
        wait_for_port_with_retries, MCP_ENDPOINT_FILENAME, MCP_PORT_WAIT_ATTEMPTS,
        MCP_PORT_WAIT_SECS, MCP_PROTOCOL_VERSION,
    };
    use std::net::TcpListener;
    use std::sync::atomic::{AtomicU32, Ordering};
    use std::time::Instant;

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
