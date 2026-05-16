//! Global kill-switch shortcut — BLUEPRINT §6.5 #5, Tauri side.
//!
//! The kill switch's "reachable in <2 seconds from any UI state" promise is
//! load-bearing: the user may be in any panel, with focus anywhere, when an
//! emergency happens. A purely in-window toolbar button works while the
//! Vysted window is focused; an OS-wide keyboard shortcut works even when
//! the user has tabbed away to another application. This module registers
//! that OS-wide shortcut.
//!
//! When the shortcut fires the handler emits a Tauri event
//! ``kill-switch:requested`` with payload ``{"firedBy": "user-keyboard"}``.
//! The frontend's :mod:`useSafetyStore` is the listener; it issues the
//! ``POST /safety/kill-switch`` against the sidecar (which broadcasts to
//! every broker adapter via the kill-switch bus, returns the p50/p95/max
//! ack times). Splitting the responsibility — Rust owns the OS surface,
//! frontend owns the HTTP call — keeps the Rust side dependency-free of
//! reqwest/httpx and matches how the v0.4.0 keychain wrapper splits
//! responsibility between Rust (OS API) and frontend (caller logic).
//!
//! The shortcut is ``CmdOrCtrl+Shift+K`` — out-of-the-way enough that an
//! accidental fire is unlikely, prominent enough that a stressed user can
//! find it.

use tauri::plugin::TauriPlugin;
use tauri::{AppHandle, Emitter, Runtime};
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutState};

/// The OS-wide keyboard shortcut Vysted registers for the kill switch.
///
/// ``CmdOrCtrl+Shift+K`` matches the operator brief's "keyboard shortcut"
/// requirement (BLUEPRINT §6.5 #5). The shortcut is OS-wide — it fires even
/// when the Vysted window does not have focus, which is the load-bearing
/// property for emergency reachability.
pub fn kill_switch_shortcut() -> Shortcut {
    Shortcut::new(
        Some(Modifiers::SHIFT | Modifiers::SUPER | Modifiers::CONTROL),
        Code::KeyK,
    )
}

/// Build the global-shortcut plugin with the kill-switch handler bound.
///
/// Called from ``lib.rs`` setup. The handler emits a ``kill-switch:requested``
/// Tauri event payload that the frontend listens for via
/// ``listen("kill-switch:requested", ...)``. Errors registering the shortcut
/// (already taken by another app, OS permission denied) are logged and
/// degrade gracefully — the toolbar button still fires the kill switch
/// directly through the sidecar HTTP endpoint.
pub fn build_plugin<R: Runtime>() -> TauriPlugin<R> {
    tauri_plugin_global_shortcut::Builder::new()
        .with_handler(|app, shortcut, event| {
            if shortcut != &kill_switch_shortcut() {
                return;
            }
            // Fire only on Press to avoid double-firing on Release.
            if event.state() != ShortcutState::Pressed {
                return;
            }
            if let Err(err) = emit_kill_switch_requested(app, "user-keyboard") {
                eprintln!("[kill_switch] failed to emit Tauri event: {err}");
            }
        })
        .build()
}

/// Register the kill-switch shortcut after the app launches.
///
/// Called from ``lib.rs`` setup AFTER the plugin is registered. If the OS
/// refuses to register (shortcut already taken, lack of permission, etc.)
/// we log and continue — the toolbar button is the always-available
/// fallback.
pub fn register_shortcut<R: Runtime>(app: &AppHandle<R>) {
    let shortcut = kill_switch_shortcut();
    match app.global_shortcut().register(shortcut) {
        Ok(()) => println!("[kill_switch] registered global shortcut Cmd/Ctrl+Shift+K"),
        Err(err) => eprintln!(
            "[kill_switch] global shortcut registration failed ({err}); \
             toolbar button still works"
        ),
    }
}

/// Programmatically emit the same kill-switch event the shortcut would.
///
/// Exposed as a Tauri command so the frontend can fire-test the path from
/// a developer console without actually triggering the OS shortcut. The
/// production trigger is the global shortcut + the toolbar button (which
/// goes straight to the sidecar HTTP endpoint).
#[tauri::command]
pub fn kill_switch_emit(app: AppHandle, fired_by: String) -> Result<(), String> {
    emit_kill_switch_requested(&app, &fired_by).map_err(|e| e.to_string())
}

fn emit_kill_switch_requested<R: Runtime>(app: &AppHandle<R>, fired_by: &str) -> tauri::Result<()> {
    let payload = serde_json::json!({ "firedBy": fired_by });
    app.emit("kill-switch:requested", payload)
}
