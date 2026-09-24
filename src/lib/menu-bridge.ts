import { applyLayoutMode, MENU_PAYLOAD_TO_MODE } from "@/lib/layout-templates";
import { useWorkspaceStore } from "@/store/workspace";

/**
 * macOS menu-bar bridge (003) — the native Layout menu (built in `lib.rs`,
 * macOS-only) labels its items Fundamental / Technical / Macro / Compare / Reset
 * and emits `vysted://menu-layout` with a historical template id, mapped once to
 * its layout mode by `MENU_PAYLOAD_TO_MODE`. A menu mode is a
 * DETERMINISTIC "switch to this cockpit": `applyLayoutMode` CLEARS the grid and
 * tiles exactly that mode's panel set (NOT the agent's additive, fit-downgraded
 * arrange — Bug-4: "Fundamental" was collapsing to a single brief panel). A user
 * menu click is direct (no diff gate). Outside a Tauri webview (static export /
 * browser) it's a no-op — the dynamic import of the Tauri event API simply fails.
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
        const api = useWorkspaceStore.getState().dockviewApi;
        if (!api) {
          console.warn("[menu-bridge] no dockview api yet — layout not applied");
          return;
        }
        const mode = MENU_PAYLOAD_TO_MODE[template];
        if (template === "default") {
          useWorkspaceStore.getState().resetToDefaultLayout();
        } else if (mode) {
          applyLayoutMode(api, mode);
          console.info(`[menu-bridge] applied layout mode → ${mode}`);
        } else {
          console.warn(`[menu-bridge] unknown layout payload → ${template}`);
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
