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
//! - :fn:`start` is called from ``lib.rs``'s boot thread. It picks a free
//!   port (``lib.rs`` hands it to the main sidecar as
//!   ``VYSTED_OPENBB_MCP_PORT`` on that child's own environment, so the
//!   Python ``openbb_mcp_provider`` learns it without a handshake), spawns
//!   the bundled binary, drains the child's stdout/stderr
//!   so its pipes never block, and manages the ``CommandChild`` in Tauri
//!   state. :fn:`supervise` then waits for the bind (after the main sidecar
//!   has been spawned).
//! - :fn:`get_openbb_mcp_port` exposes the port to the frontend, in case any
//!   future UI needs to address the child directly (the plugin manager UI's
//!   "OpenBB MCP" chip might want to link to it).
//! - The Tauri ``RunEvent::Exit`` handler in ``lib.rs`` kills the child on
//!   shutdown via the same pattern the main sidecar uses.

use std::sync::Mutex;

use tauri::{AppHandle, Manager};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

use crate::{
    pick_free_port, wait_for_port_with_retries, MCP_PORT_WAIT_ATTEMPTS, MCP_PORT_WAIT_SECS,
};

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

/// Register this build as "openbb-mcp unavailable": port=0 + no child.
/// The Python sidecar's ``openbb_mcp_provider`` reads the empty
/// ``VYSTED_OPENBB_MCP_PORT`` and falls back to yfinance.
fn register_unavailable(app: &AppHandle) {
    app.manage(OpenbbMcpPort(0));
    app.manage(OpenbbMcpProcess(Mutex::new(None)));
}

/// Start the openbb-mcp subprocess: pick its port, spawn it and keep its handle
/// in Tauri state. Fast — no bind wait (that is :fn:`supervise`), so the main
/// sidecar can spawn right after with the port in its env (R15-LIFECYCLE-001). Returns the port to supervise, or
/// ``None`` once registered unavailable. Never panics — when the bundled
/// binary is missing (a dev build that skipped ``pnpm
/// openbb-mcp-sidecar:build``) the main sidecar falls back to yfinance for
/// OpenBB-backed routes.
///
/// Phase-9 UC1 fix: the port is picked IMMEDIATELY before ``Command::spawn``
/// (first line, no late pick) to keep the bind-vs-spawn TOCTTOU window
/// minimal.
pub fn start(app: &AppHandle) -> Option<u16> {
    let port = match pick_free_port() {
        Some(port) => port,
        None => {
            diag_eprintln!(
                "[openbb-mcp] could not bind a free port; \
                 falling back to yfinance for OpenBB-backed routes."
            );
            register_unavailable(app);
            return None;
        }
    };

    let sidecar = match app
        .shell()
        .sidecar("vysted-openbb-mcp-sidecar")
        .map(|cmd| cmd.args(["--port", &port.to_string()]))
    {
        Ok(cmd) => cmd,
        Err(err) => {
            diag_eprintln!(
                "[openbb-mcp] subprocess binary unavailable ({err}); \
                 falling back to yfinance for OpenBB-backed routes."
            );
            register_unavailable(app);
            return None;
        }
    };

    let (mut rx, child) = match sidecar.spawn() {
        Ok(parts) => parts,
        Err(err) => {
            diag_eprintln!(
                "[openbb-mcp] failed to spawn subprocess: {err}; falling back to yfinance."
            );
            register_unavailable(app);
            return None;
        }
    };
    // Managed at once so an app exit during the bind wait still reaps it.
    app.manage(OpenbbMcpProcess(Mutex::new(Some(child))));

    // Drain the child's stdout/stderr so its pipes never block. Mirrors the
    // main sidecar's drain. Spawn the drain BEFORE the port-bind probe so
    // any startup error messages from the child are surfaced.
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    diag_println!("[openbb-mcp] {}", String::from_utf8_lossy(&line));
                }
                CommandEvent::Stderr(line) => {
                    diag_eprintln!("[openbb-mcp] {}", String::from_utf8_lossy(&line));
                }
                _ => {}
            }
        }
    });
    Some(port)
}

/// Wait for the child :fn:`start` spawned to bind ``port``; on a timeout kill
/// it and register openbb-mcp unavailable. Runs after the main sidecar spawn:
/// until the bind, a sidecar call fails fast and marks the provider down until
/// its next successful call.
pub fn supervise(app: &AppHandle, port: u16) {
    // Probe the claimed port — `Command::spawn` returns success the moment
    // the OS creates the process, NOT when the child actually binds. The
    // openbb-mcp-server bootstrap can take several seconds (loading
    // openbb-platform extensions + a cold PyInstaller `_MEI*` extraction),
    // and historically (Phase 8 finding UC1-openbb-mcp-not-listening) was
    // observed to bind on some boots and not others when the flat 15s budget
    // was exceeded under Windows file-lock contention. The longer per-attempt
    // budget + one retry below cover the observed worst case while keeping
    // a fast boot near-instant (the wait short-circuits on first connect).
    let bound = wait_for_port_with_retries(
        port,
        MCP_PORT_WAIT_SECS,
        MCP_PORT_WAIT_ATTEMPTS,
        |attempt, total| {
            diag_eprintln!(
                "[openbb-mcp] not bound on 127.0.0.1:{port} after attempt {attempt}/{total} \
                 ({MCP_PORT_WAIT_SECS}s); cold PyInstaller extraction may be slow — retrying."
            );
        },
    );
    if !bound {
        diag_eprintln!(
            "[openbb-mcp] subprocess did not bind to 127.0.0.1:{port} within \
             {MCP_PORT_WAIT_SECS}s x {MCP_PORT_WAIT_ATTEMPTS} attempts; treating as \
             unavailable. /fundamentals + /macro + /screener + /earnings + \
             analyst-rating routes will fall back to yfinance or 501. \
             Check the bundled binary for a startup deadlock (Phase 8 \
             finding UC1-openbb-mcp-not-listening; Phase 9 residual: cold-boot \
             bind latency — see BLOCKERS.md)."
        );
        kill(app);
        register_unavailable(app);
        return;
    }

    app.manage(OpenbbMcpPort(port));

    diag_println!("[openbb-mcp] subprocess healthy on 127.0.0.1:{port}");
}

/// Kill the openbb-mcp subprocess if it is still running. Idempotent.
///
/// Called from the Tauri ``RunEvent::Exit`` handler in ``lib.rs`` so the
/// child is reaped on app shutdown alongside the main sidecar.
pub fn kill(app: &AppHandle) {
    if let Some(state) = app.try_state::<OpenbbMcpProcess>() {
        // Take the child in its own statement so the guard drops before kill().
        let child = state.0.lock().unwrap().take();
        if let Some(child) = child {
            let _ = child.kill();
        }
    }
}
