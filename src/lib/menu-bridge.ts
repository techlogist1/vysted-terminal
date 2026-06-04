import { fitLayoutTemplate, type LayoutTemplate } from "@/lib/layout-templates";
import { useWorkspaceStore } from "@/store/workspace";

/**
 * macOS menu-bar bridge (003) — the native Layout menu (built in `lib.rs`,
 * macOS-only) emits `vysted://menu-layout` with a layout-template id; this applies
 * it to the live dockview, viewport-fit-aware (the same path the agent's
 * arrange_layout uses). A user menu click is direct (no diff gate). Outside a
 * Tauri webview (static export / browser) it's a no-op — the dynamic import of the
 * Tauri event API simply fails and we swallow it.
 */
const TEMPLATES: ReadonlySet<string> = new Set([
  "research-cockpit",
  "single-focus",
  "macro-scan",
  "compare",
]);

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
        if (template === "default") {
          useWorkspaceStore.getState().resetToDefaultLayout();
        } else if (TEMPLATES.has(template)) {
          fitLayoutTemplate(api, template as LayoutTemplate);
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
