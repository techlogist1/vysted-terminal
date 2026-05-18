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

/// Poll the port until something accepts TCP connections, or time out after 15s.
///
/// Used by the main-sidecar startup wait AND by the openbb-mcp /
/// sec-edgar-mcp subprocess supervisors to verify that the spawned
/// subprocess has bound to its claimed port before declaring spawn
/// success. Without this probe, ``Command::spawn`` returns immediately
/// after the OS creates the process — the process may deadlock during
/// startup (Phase 8 found this for the MCP subprocesses) and the parent
/// has no way to detect it (per CLAUDE.md PyInstaller --onefile +
/// anyio + Windows handle interactions).
pub(crate) fn wait_for_port(port: u16) -> bool {
    let deadline = Instant::now() + Duration::from_secs(15);
    while Instant::now() < deadline {
        if TcpStream::connect(("127.0.0.1", port)).is_ok() {
            return true;
        }
        thread::sleep(Duration::from_millis(200));
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

            // Spawn the openbb-mcp subprocess BEFORE the main sidecar so the
            // ``VYSTED_OPENBB_MCP_PORT`` env var is in place when the
            // Python sidecar imports ``services.openbb_mcp_provider``. The
            // helper picks its own free port, supervises the child, and
            // tolerates a missing binary by registering port=0 (sidecar
            // then falls back to yfinance — see CLAUDE.md Phase-3 fix).
            openbb_mcp::spawn(app.handle())?;

            // Spawn the sec-edgar-mcp subprocess alongside openbb-mcp. Same
            // non-fatal pattern: a missing binary registers port=0 and the
            // ``/sec`` routes return 501 until ``pnpm sec-edgar-mcp-sidecar:build``
            // is run.
            sec_edgar_mcp::spawn(app.handle())?;

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
    use super::pick_free_port;

    #[test]
    fn pick_free_port_returns_a_usable_port() {
        let port = pick_free_port();
        assert!(port > 0, "expected a non-zero port, got {port}");
    }
}
