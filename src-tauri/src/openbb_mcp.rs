//! openbb-mcp subprocess supervisor — Tauri Rust side of the Phase-3 fix.
//!
//! The Phase-2 OpenBB integration spawned its FastAPI subprocess from Python
//! via ``subprocess.Popen`` and hung indefinitely on Windows (anyio +
//! PyInstaller ``_MEIPASS`` + Windows handle inheritance — see CLAUDE.md
//! Gotchas). Phase 3's architectural fix swaps both halves:
//!
//! - the bespoke subprocess → the stock ``openbb-mcp-server`` package (1.4.0)
//!   packaged as its own PyInstaller --onefile binary in
//!   ``sidecar/openbb_mcp_subprocess/``;
//! - ``subprocess.Popen`` → Tauri Rust ``Command::new`` via
//!   ``tauri-plugin-shell``. Different Windows handle semantics side-step
//!   the deadlock.
//!
//! This module owns the child process lifecycle:
//!
//! - :fn:`spawn` is called from ``lib.rs`` ``setup``. It picks a free port,
//!   spawns the bundled binary, drains the child's stdout/stderr so its
//!   pipes never block, manages a ``CommandChild`` in Tauri state, and sets
//!   the ``VYSTED_OPENBB_MCP_PORT`` env var so the Python sidecar's
//!   ``openbb_mcp_provider`` learns the port without an explicit handshake.
//! - :fn:`get_openbb_mcp_port` exposes the port to the frontend, in case any
//!   future UI needs to address the child directly (the plugin manager UI's
//!   "OpenBB MCP" chip might want to link to it).
//! - The Tauri ``RunEvent::Exit`` handler in ``lib.rs`` kills the child on
//!   shutdown via the same pattern the main sidecar uses.

use std::sync::Mutex;

use tauri::{AppHandle, Manager};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

use crate::{pick_free_port, wait_for_port};

/// Holds the running openbb-mcp subprocess so it can be killed on app exit.
pub struct OpenbbMcpProcess(pub Mutex<Option<CommandChild>>);

/// The localhost port the openbb-mcp subprocess is bound to. Stored in Tauri
/// state and exposed to the frontend via the ``get_openbb_mcp_port`` command.
pub struct OpenbbMcpPort(pub u16);

/// Expose the openbb-mcp port to the frontend.
///
/// Returns ``0`` when the subprocess could not be spawned (binary missing or
/// crashed during startup) — the plugin manager UI interprets ``0`` as
/// "openbb-mcp unavailable, falling back to yfinance".
#[tauri::command]
pub fn get_openbb_mcp_port(port: tauri::State<'_, OpenbbMcpPort>) -> u16 {
    port.0
}

/// Spawn the openbb-mcp subprocess and register its handle + port in Tauri state.
///
/// Called from ``lib.rs`` ``setup`` exactly once. The function never panics —
/// when the bundled binary is missing (a dev build that skipped
/// ``pnpm openbb-mcp-sidecar:build``) it logs and registers a zero port so
/// the main sidecar falls back to yfinance for OpenBB-backed routes.
pub fn spawn(app: &AppHandle) -> tauri::Result<()> {
    let port = pick_free_port();

    // Hand the port to the Python sidecar via env var. The sidecar spawn in
    // ``lib.rs`` runs AFTER this function, so the env var is in place by the
    // time the sidecar imports ``services.openbb_mcp_provider``.
    std::env::set_var("VYSTED_OPENBB_MCP_PORT", port.to_string());
    std::env::set_var("VYSTED_OPENBB_MCP_HOST", "127.0.0.1");

    let sidecar = match app
        .shell()
        .sidecar("vysted-openbb-mcp-sidecar")
        .map(|cmd| cmd.args(["--port", &port.to_string()]))
    {
        Ok(cmd) => cmd,
        Err(err) => {
            eprintln!(
                "[openbb-mcp] subprocess binary unavailable ({err}); \
                 falling back to yfinance for OpenBB-backed routes."
            );
            // Register a zero port so ``openbb_mcp_provider`` treats this
            // build as not having openbb-mcp bundled.
            std::env::remove_var("VYSTED_OPENBB_MCP_PORT");
            app.manage(OpenbbMcpPort(0));
            app.manage(OpenbbMcpProcess(Mutex::new(None)));
            return Ok(());
        }
    };

    let (mut rx, child) = match sidecar.spawn() {
        Ok(parts) => parts,
        Err(err) => {
            eprintln!("[openbb-mcp] failed to spawn subprocess: {err}; falling back to yfinance.");
            std::env::remove_var("VYSTED_OPENBB_MCP_PORT");
            app.manage(OpenbbMcpPort(0));
            app.manage(OpenbbMcpProcess(Mutex::new(None)));
            return Ok(());
        }
    };

    // Drain the child's stdout/stderr so its pipes never block. Mirrors the
    // main sidecar's drain. Spawn the drain BEFORE the port-bind probe so
    // any startup error messages from the child are surfaced.
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    println!("[openbb-mcp] {}", String::from_utf8_lossy(&line));
                }
                CommandEvent::Stderr(line) => {
                    eprintln!("[openbb-mcp] {}", String::from_utf8_lossy(&line));
                }
                _ => {}
            }
        }
    });

    // Probe the claimed port — `Command::spawn` returns success the moment
    // the OS creates the process, NOT when the child actually binds. The
    // openbb-mcp-server bootstrap can take several seconds (loading
    // openbb-platform extensions), and historically (Phase 8 finding
    // UC1-openbb-mcp-not-listening) was observed to deadlock silently —
    // the child stayed alive but never bound, and the main sidecar's MCP
    // client hit `asyncio.CancelledError` on every /fundamentals call.
    // Without this probe, the supervisor lies about availability.
    if !wait_for_port(port) {
        eprintln!(
            "[openbb-mcp] subprocess did not bind to 127.0.0.1:{port} within 15s; \
             treating as unavailable. /fundamentals + /macro + /screener + /earnings + \
             analyst-rating routes will fall back to yfinance or 501. \
             Check the bundled binary for a startup deadlock (Phase 8 \
             finding UC1-openbb-mcp-not-listening)."
        );
        let _ = child.kill();
        std::env::remove_var("VYSTED_OPENBB_MCP_PORT");
        std::env::remove_var("VYSTED_OPENBB_MCP_HOST");
        app.manage(OpenbbMcpPort(0));
        app.manage(OpenbbMcpProcess(Mutex::new(None)));
        return Ok(());
    }

    app.manage(OpenbbMcpPort(port));
    app.manage(OpenbbMcpProcess(Mutex::new(Some(child))));

    println!("[openbb-mcp] subprocess healthy on 127.0.0.1:{port}");
    Ok(())
}

/// Kill the openbb-mcp subprocess if it is still running. Idempotent.
///
/// Called from the Tauri ``RunEvent::Exit`` handler in ``lib.rs`` so the
/// child is reaped on app shutdown alongside the main sidecar.
pub fn kill(app: &AppHandle) {
    if let Some(state) = app.try_state::<OpenbbMcpProcess>() {
        if let Some(child) = state.0.lock().unwrap().take() {
            let _ = child.kill();
        }
    }
}
