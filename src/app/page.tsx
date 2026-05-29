"use client";

import { useEffect } from "react";
import { LayoutGrid, Save, Settings2 } from "lucide-react";

import { CommandPalette } from "@/components/CommandPalette";
import { OnboardingBanner } from "@/components/OnboardingBanner";
import { PanelHost } from "@/components/PanelHost";
import { useDesktopNotificationBridge } from "@/lib/desktop-notification";
import { bootstrapPlugins } from "@/lib/plugin-bootstrap";
import { autosaveLayout } from "@/lib/workspace";
import { vystedModules } from "@/modules";
import { WorkspaceDialog } from "@/modules/platform/WorkspaceDialog";
import { useWorkspaceDialog } from "@/modules/platform/workspace-dialog-store";
import { useAppStore } from "@/store/app";
import { useCommandPalette } from "@/store/command-palette";
import { useModulesStore } from "@/store/modules";
import { useSymbolsStore } from "@/store/symbols";
import { useWorkspaceStore } from "@/store/workspace";

export default function Page() {
  // Bridge workflow ``action.notify_desktop`` intents to the OS
  // notification API. Safe no-op outside the Tauri webview.
  useDesktopNotificationBridge();

  useEffect(() => {
    // Register the module registry, seed the command palette from the enabled
    // modules, and connect to the Python sidecar. Runs once on mount — which is
    // also why `PanelHost` only mounts dockview after this point, keeping the
    // static-export build SSR-safe.
    useModulesStore.getState().registerModules(vystedModules);
    useCommandPalette.getState().setCommands(useModulesStore.getState().enabledCommands());
    void useAppStore.getState().connectSidecar();

    // Bootstrap the plugin runtime: attach it to the store, load bundled
    // plugins, bridge their panels/commands into the module registry, start
    // the health-check loop. The promise resolves to a teardown function that
    // unloads everything when the page unmounts.
    let teardown: (() => void) | null = null;
    let alive = true;
    void bootstrapPlugins().then((dispose) => {
      // If the effect already tore down (StrictMode/HMR/navigation) before this
      // async bootstrap resolved, dispose immediately — otherwise the runtime's
      // 30s health-check interval leaks forever (hunt-race-async Finding 1).
      if (!alive) {
        dispose();
        return;
      }
      teardown = dispose;
      // Refresh the palette once plugins have appended their commands.
      useCommandPalette.getState().setCommands(useModulesStore.getState().enabledCommands());
    });

    // Keep the cmd+K command list in sync with the module toggles: when the
    // `enabled` map changes (Settings panel, or a loaded workspace), refresh the
    // palette so a disabled module's commands disappear and a re-enabled
    // module's reappear. Subscribing to the `enabled` slice keeps this cheap.
    const unsubscribeEnabled = useModulesStore.subscribe((state, previous) => {
      if (state.enabled !== previous.enabled) {
        useCommandPalette.getState().setCommands(useModulesStore.getState().enabledCommands());
      }
    });
    // Also refresh the palette whenever a plugin appends new modules — the
    // `modules` slice changes when `appendModules` runs.
    const unsubscribeModules = useModulesStore.subscribe((state, previous) => {
      if (state.modules !== previous.modules) {
        useCommandPalette.getState().setCommands(useModulesStore.getState().enabledCommands());
      }
    });
    // Persist watchlist edits — add/remove a symbol doesn't change the dockview
    // layout, so the layout-autosave subscription wouldn't catch it; this makes
    // a customised watchlist survive a relaunch (Phase 10 customizability).
    const unsubscribeSymbols = useSymbolsStore.subscribe((state, previous) => {
      if (state.entries !== previous.entries) {
        void autosaveLayout();
      }
    });
    return () => {
      alive = false;
      unsubscribeEnabled();
      unsubscribeModules();
      unsubscribeSymbols();
      teardown?.();
    };
  }, []);

  const openPalette = useCommandPalette((state) => state.setOpen);
  const openPanel = useWorkspaceStore((state) => state.openPanel);
  const openSaveLayout = useWorkspaceDialog((state) => state.openSave);

  return (
    <main className="bg-charcoal-950 flex h-screen w-screen flex-col overflow-hidden">
      <CommandPalette />
      <WorkspaceDialog />
      {/* Header fascia — clean espresso bar with a coral underline. Brand
          wordmark left, controls right. The wordmark is a real lockup: a single
          coral brand pip + a confident Fraunces "VYSTED" in warm cream + a
          subordinate mono "Terminal" descriptor. */}
      <header className="bg-charcoal-925 relative flex h-9 shrink-0 items-center gap-3 px-3">
        <div className="flex items-center gap-2 select-none">
          {/* coral brand pip — the single lit accent in the fascia */}
          <span aria-hidden="true" className="size-2 rounded-[2px] bg-amber-400" />
          <span className="text-charcoal-100 font-serif text-[17px] leading-none font-semibold tracking-[0.01em]">
            VYSTED
          </span>
          <span className="hud-label mt-px leading-none">Terminal</span>
        </div>
        <div className="bg-charcoal-700 mx-1 h-4 w-px" aria-hidden="true" />
        <button
          type="button"
          onClick={() => openPalette(true)}
          className="text-charcoal-300 hover:text-lume flex items-center gap-1.5 font-mono text-xs transition-colors"
          aria-label="Open command palette"
        >
          <LayoutGrid className="h-3.5 w-3.5" />
          Open panel
          <kbd className="border-charcoal-700 text-charcoal-500 rounded border px-1 py-0.5 font-mono text-[10px]">
            ⌘K
          </kbd>
        </button>
        <button
          type="button"
          onClick={openSaveLayout}
          className="text-charcoal-300 hover:text-lume flex items-center gap-1.5 font-mono text-xs transition-colors"
          aria-label="Save layout"
        >
          <Save className="h-3.5 w-3.5" />
          Save layout
        </button>
        <div className="flex-1" />
        <button
          type="button"
          onClick={() => openPanel("settings")}
          className="text-charcoal-300 hover:text-lume flex items-center gap-1.5 font-mono text-xs transition-colors"
          aria-label="Open settings"
        >
          <Settings2 className="h-3.5 w-3.5" />
          Settings
        </button>
        {/* Lit gauge tick-rule along the fascia's bottom edge. */}
        <div
          className="tick-rule pointer-events-none absolute inset-x-0 bottom-0"
          aria-hidden="true"
        />
      </header>
      <OnboardingBanner />
      <div className="min-h-0 flex-1">
        <PanelHost />
      </div>
    </main>
  );
}
