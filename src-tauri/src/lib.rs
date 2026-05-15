mod keychain;

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
fn pick_free_port() -> u16 {
    std::net::TcpListener::bind("127.0.0.1:0")
        .expect("failed to bind a free port for the sidecar")
        .local_addr()
        .expect("failed to read the sidecar port")
        .port()
}

/// Poll the port until the sidecar accepts TCP connections, or time out after 15s.
fn wait_for_sidecar(port: u16) -> bool {
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
        .invoke_handler(tauri::generate_handler![
            get_sidecar_port,
            keychain::keychain_set,
            keychain::keychain_get,
            keychain::keychain_delete,
        ])
        .setup(|app| {
            let port = pick_free_port();
            app.manage(SidecarPort(port));

            // Phase 3 reservation: Teammate B (MCP layer) replaces this line
            // with `openbb_mcp::spawn(&app.handle())?;` to launch the
            // openbb-mcp-server subprocess via Tauri Rust `Command::new`
            // (Phase-2 Gotcha — never via Python `subprocess.Popen` on
            // Windows). The spawn helper picks a free port, supervises the
            // child, and exposes the port via `get_openbb_mcp_port`.
            // Placeholder kept here so B's worktree applies as a one-line
            // replacement instead of a multi-hunk edit.

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
                if wait_for_sidecar(port) {
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
