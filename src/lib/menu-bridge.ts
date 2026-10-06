import { dispatchLayoutMenuCommand } from "@/store/command-palette";

/**
 * macOS menu-bar bridge (003) — the native Layout menu (built in `lib.rs`,
 * macOS-only) labels its items Fundamental / Technical / Macro / Compare / Reset
 * and emits `vysted://menu-layout` with a historical template id. A menu mode is
 * a DETERMINISTIC "switch to this cockpit": `dispatchLayoutMenuCommand` CLEARS
 * the grid and tiles exactly that mode's panel set (NOT the agent's additive,
 * fit-downgraded arrange — Bug-4: "Fundamental" was collapsing to a single
 * brief panel). It's the SAME dispatch the command palette's layout-mode
 * commands use (R15-CROSS-PLATFORM-004) — the menu is one more caller, not a
 * separate implementation, so Windows/Linux (no native menu) reach the
 * identical deterministic modes via the palette. A user menu click is direct
 * (no diff gate). Outside a Tauri webview (static export / browser) it's a
 * no-op — the dynamic import of the Tauri event API simply fails.
 */
export function initMenuBridge(): () => void {
  let unlisten: (() => void) | null = null;
  let alive = true;

  void (async () => {
    try {
      const { listen } = await import("@tauri-apps/api/event");
      const dispose = await listen<string>("vysted://menu-layout", (event) => {
        const template = event.payload;
        // Observable so a native-menu click is confirmable in the app console
        // (the operator's ratifying click should log this line).
        console.info(`[menu-bridge] received vysted://menu-layout → ${template}`);
        if (dispatchLayoutMenuCommand(template)) {
          console.info(`[menu-bridge] applied layout payload → ${template}`);
        } else {
          console.warn(`[menu-bridge] unknown layout payload or no dockview api → ${template}`);
        }
      });
      if (alive) {
        unlisten = dispose;
        console.info("[menu-bridge] listening for vysted://menu-layout");
      } else {
        dispose();
      }
    } catch {
      // Not in a Tauri webview (or no menu) — nothing to listen to.
    }
  })();

  return () => {
    alive = false;
    unlisten?.();
  };
}
