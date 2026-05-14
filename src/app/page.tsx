"use client";

import { useEffect } from "react";

import { CommandPalette } from "@/components/CommandPalette";
import { PanelHost } from "@/components/PanelHost";
import { vystedModules } from "@/modules";
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
  }, []);

  return (
    <main className="bg-charcoal-950 h-screen w-screen overflow-hidden">
      <CommandPalette />
      <PanelHost />
    </main>
  );
}
