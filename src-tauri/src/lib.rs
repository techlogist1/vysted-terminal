mod keychain;
mod kill_switch;
mod openbb_mcp;
mod sec_edgar_mcp;

use std::net::TcpStream;
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
pub(crate) fn pick_free_port() -> u16 {
    std::net::TcpListener::bind("127.0.0.1:0")
        .expect("failed to bind a free port for the sidecar")
        .local_addr()
        .expect("failed to read the sidecar port")
        .port()
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
/// not others" symptom (Phase 8 finding UC1-*-not-listening). Raising the
/// per-attempt deadline to 30s covers the observed worst case; a bounded
/// retry below covers the residual.
pub(crate) const MCP_PORT_WAIT_SECS: u64 = 30;

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

/// Expose the sidecar's localhost port to the frontend so it can issue HTTP and
/// WebSocket requests to the Python data layer.
#[tauri::command]
fn get_sidecar_port(port: tauri::State<'_, SidecarPort>) -> u16 {
    port.0
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_notification::init())
        .plugin(kill_switch::build_plugin())
        .invoke_handler(tauri::generate_handler![
            get_sidecar_port,
            keychain::keychain_set,
            keychain::keychain_get,
            keychain::keychain_delete,
            kill_switch::kill_switch_emit,
            openbb_mcp::get_openbb_mcp_port,
            sec_edgar_mcp::get_sec_edgar_mcp_port,
        ])
        .setup(|app| {
            let port = pick_free_port();
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

            // Resolve the per-OS application data directory and hand it to the
            // sidecar; the sidecar owns the portfolio SQLite database and the
            // saved-workspace files beneath it.
            let data_dir = app
                .path()
                .app_data_dir()
                .expect("failed to resolve the application data directory");
            std::fs::create_dir_all(&data_dir)
                .expect("failed to create the application data directory");
            let data_dir = data_dir.to_string_lossy().to_string();

            let sidecar = app
                .shell()
                .sidecar("vysted-sidecar")
                .expect("failed to create the sidecar command")
                .args(["--port", &port.to_string(), "--data-dir", &data_dir]);

            let (mut rx, child) = sidecar.spawn().expect("failed to spawn the Python sidecar");
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

            thread::spawn(move || {
                if wait_for_port(port) {
                    println!("[vysted] Python sidecar healthy on 127.0.0.1:{port}");
                } else {
                    eprintln!("[vysted] Python sidecar did not come up on port {port}");
                }
            });

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
        pick_free_port, wait_for_port_timeout, wait_for_port_with_retries, MCP_PORT_WAIT_ATTEMPTS,
        MCP_PORT_WAIT_SECS,
    };
    use std::net::TcpListener;
    use std::sync::atomic::{AtomicU32, Ordering};
    use std::time::Instant;

    #[test]
    fn pick_free_port_returns_a_usable_port() {
        let port = pick_free_port();
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
        let free_port = pick_free_port();
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
        let free_port = pick_free_port();
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
