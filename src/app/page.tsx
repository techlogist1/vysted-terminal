"use client";

import { useEffect } from "react";

import { CommandPalette } from "@/components/CommandPalette";
import { PanelHost } from "@/components/PanelHost";
import { useDesktopNotificationBridge } from "@/lib/desktop-notification";
import { bootstrapPlugins } from "@/lib/plugin-bootstrap";
import { vystedModules } from "@/modules";
import { WorkspaceDialog } from "@/modules/platform/WorkspaceDialog";
import { useAppStore } from "@/store/app";
import { useCommandPalette } from "@/store/command-palette";
import { useModulesStore } from "@/store/modules";

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
    void bootstrapPlugins().then((dispose) => {
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
    return () => {
      unsubscribeEnabled();
      unsubscribeModules();
      teardown?.();
    };
  }, []);

  return (
    <main className="bg-charcoal-950 h-screen w-screen overflow-hidden">
      <CommandPalette />
      <WorkspaceDialog />
      <PanelHost />
    </main>
  );
}
