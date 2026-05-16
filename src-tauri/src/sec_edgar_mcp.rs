//! sec-edgar-mcp subprocess supervisor — Phase 6 (v0.6.0) Teammate F.
//!
//! Mirrors the openbb-mcp pattern (``src-tauri/src/openbb_mcp.rs``) — the
//! v0.4.0 Phase-2 deadlock fix proved that spawning a PyInstaller --onefile
//! MCP server via Tauri Rust ``Command::new`` side-steps the anyio +
//! ``_MEIPASS`` + Windows handle-inheritance interaction that hangs
//! ``subprocess.Popen`` indefinitely on Windows (CLAUDE.md Gotcha).
//!
//! The Vysted main sidecar talks to this child as an MCP client over
//! Streamable-HTTP and proxies its Company / Filings / Financials /
//! Insider-Trading tool surface through
//! ``sidecar/services/sec_filings_provider.py`` into the
//! ``/sec/...`` REST routes.
//!
//! Lifecycle ownership:
//!
//! - :fn:`spawn` is called from ``lib.rs`` ``setup`` AFTER ``openbb_mcp::spawn``
//!   and (when present) ``fred_mcp::spawn``. It picks a free port, spawns the
//!   bundled binary, drains the child's stdout/stderr so its pipes never
//!   block, manages a ``CommandChild`` in Tauri state, and sets the
//!   ``VYSTED_SEC_EDGAR_MCP_PORT`` env var so the Python sidecar's
//!   ``sec_filings_provider`` learns the port without an explicit handshake.
//! - :fn:`get_sec_edgar_mcp_port` exposes the port to the frontend so the
//!   plugin-manager UI can colour the "SEC EDGAR MCP" plugin chip.
//! - The Tauri ``RunEvent::Exit`` handler in ``lib.rs`` reaps the child on
//!   shutdown alongside the main sidecar.

use std::sync::Mutex;

use tauri::{AppHandle, Manager};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

use crate::pick_free_port;

/// Holds the running sec-edgar-mcp subprocess so it can be killed on app exit.
pub struct SecEdgarMcpProcess(pub Mutex<Option<CommandChild>>);

/// The localhost port the sec-edgar-mcp subprocess is bound to.
pub struct SecEdgarMcpPort(pub u16);

/// Expose the sec-edgar-mcp port to the frontend.
///
/// Returns ``0`` when the subprocess could not be spawned (binary missing or
/// crashed during startup) — the plugin manager UI interprets ``0`` as
/// "sec-edgar-mcp unavailable, /sec routes return 501".
#[tauri::command]
pub fn get_sec_edgar_mcp_port(port: tauri::State<'_, SecEdgarMcpPort>) -> u16 {
    port.0
}

/// Spawn the sec-edgar-mcp subprocess and register its handle + port in Tauri state.
///
/// Called from ``lib.rs`` ``setup`` exactly once. The function never panics —
/// when the bundled binary is missing (a dev build that skipped
/// ``pnpm sec-edgar-mcp-sidecar:build``) it logs and registers a zero port so
/// the main sidecar's SEC filings provider treats this build as not having
/// sec-edgar-mcp bundled (the routes 501 cleanly rather than crashing).
pub fn spawn(app: &AppHandle) -> tauri::Result<()> {
    let port = pick_free_port();

    // Hand the port to the Python sidecar via env var. The sidecar spawn in
    // ``lib.rs`` runs AFTER this function, so the env var is in place by the
    // time the sidecar imports ``services.sec_filings_provider``.
    std::env::set_var("VYSTED_SEC_EDGAR_MCP_PORT", port.to_string());
    std::env::set_var("VYSTED_SEC_EDGAR_MCP_HOST", "127.0.0.1");

    let sidecar = match app
        .shell()
        .sidecar("vysted-sec-edgar-mcp-sidecar")
        .map(|cmd| cmd.args(["--port", &port.to_string()]))
    {
        Ok(cmd) => cmd,
        Err(err) => {
            eprintln!(
                "[sec-edgar-mcp] subprocess binary unavailable ({err}); \
                 /sec routes will 501 until the bundle is rebuilt."
            );
            std::env::remove_var("VYSTED_SEC_EDGAR_MCP_PORT");
            app.manage(SecEdgarMcpPort(0));
            app.manage(SecEdgarMcpProcess(Mutex::new(None)));
            return Ok(());
        }
    };

    let (mut rx, child) = match sidecar.spawn() {
        Ok(parts) => parts,
        Err(err) => {
            eprintln!(
                "[sec-edgar-mcp] failed to spawn subprocess: {err}; /sec routes will 501."
            );
            std::env::remove_var("VYSTED_SEC_EDGAR_MCP_PORT");
            app.manage(SecEdgarMcpPort(0));
            app.manage(SecEdgarMcpProcess(Mutex::new(None)));
            return Ok(());
        }
    };

    app.manage(SecEdgarMcpPort(port));
    app.manage(SecEdgarMcpProcess(Mutex::new(Some(child))));

    // Drain the child's stdout/stderr so its pipes never block. Mirrors the
    // openbb-mcp drain pattern.
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    println!("[sec-edgar-mcp] {}", String::from_utf8_lossy(&line));
                }
                CommandEvent::Stderr(line) => {
                    eprintln!("[sec-edgar-mcp] {}", String::from_utf8_lossy(&line));
                }
                _ => {}
            }
        }
    });

    println!("[sec-edgar-mcp] subprocess spawned on 127.0.0.1:{port}");
    Ok(())
}

/// Kill the sec-edgar-mcp subprocess if it is still running. Idempotent.
///
/// Called from the Tauri ``RunEvent::Exit`` handler in ``lib.rs`` so the
/// child is reaped on app shutdown alongside the main sidecar.
pub fn kill(app: &AppHandle) {
    if let Some(state) = app.try_state::<SecEdgarMcpProcess>() {
        if let Some(child) = state.0.lock().unwrap().take() {
            let _ = child.kill();
        }
    }
}
