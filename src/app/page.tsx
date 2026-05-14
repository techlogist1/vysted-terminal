"use client";

import { useEffect } from "react";

import { CommandPalette } from "@/components/CommandPalette";
import { PanelHost } from "@/components/PanelHost";
import { vystedModules } from "@/modules";
import { WorkspaceDialog } from "@/modules/platform/WorkspaceDialog";
import { useAppStore } from "@/store/app";
import { useCommandPalette } from "@/store/command-palette";
import { useModulesStore } from "@/store/modules";

export default function Page() {
  useEffect(() => {
    // Register the module registry, seed the command palette from the enabled
    // modules, and connect to the Python sidecar. Runs once on mount — which is
    // also why `PanelHost` only mounts dockview after this point, keeping the
    // static-export build SSR-safe.
    useModulesStore.getState().registerModules(vystedModules);
    useCommandPalette.getState().setCommands(useModulesStore.getState().enabledCommands());
    void useAppStore.getState().connectSidecar();

    // Keep the cmd+K command list in sync with the module toggles: when the
    // `enabled` map changes (Settings panel, or a loaded workspace), refresh the
    // palette so a disabled module's commands disappear and a re-enabled
    // module's reappear. Subscribing to the `enabled` slice keeps this cheap.
    const unsubscribe = useModulesStore.subscribe((state, previous) => {
      if (state.enabled !== previous.enabled) {
        useCommandPalette.getState().setCommands(useModulesStore.getState().enabledCommands());
      }
    });
    return unsubscribe;
  }, []);

  return (
    <main className="bg-charcoal-950 h-screen w-screen overflow-hidden">
      <CommandPalette />
      <WorkspaceDialog />
      <PanelHost />
    </main>
  );
}
