"use client";

import { useEffect } from "react";
import { MotionConfig } from "framer-motion";
import { LayoutGrid, PanelLeftClose, PanelLeftOpen, Save, Settings2 } from "lucide-react";

import { AgentDock } from "@/components/AgentDock";
import { CommandPalette } from "@/components/CommandPalette";
import { OnboardingBanner } from "@/components/OnboardingBanner";
import { PanelHost } from "@/components/PanelHost";
import { useDesktopNotificationBridge } from "@/lib/desktop-notification";
import { initDevMcpBridge } from "@/lib/dev-mcp-bridge";
import { bootstrapPlugins } from "@/lib/plugin-bootstrap";
import { autosaveLayout } from "@/lib/workspace";
import { cn } from "@/lib/utils";
import { EASE_INSTRUMENT } from "@/lib/motion";
import { vystedModules } from "@/modules";
import { DisclaimerFlow, OrderConfirmationDialog } from "@/modules/safety";
import { WorkspaceDialog } from "@/modules/platform/WorkspaceDialog";
import { useWorkspaceDialog } from "@/modules/platform/workspace-dialog-store";
import { useAgentDockStore } from "@/store/agent-dock";
import { useAgentModeStore } from "@/store/agent-mode";
import { useAgentAutonomyStore } from "@/store/agent-autonomy";
import { useAppStore } from "@/store/app";
import { useCommandPalette } from "@/store/command-palette";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useModelSelectionStore } from "@/store/model-selection";
import { useModulesStore } from "@/store/modules";
import { useSearchSettingsStore } from "@/store/search-settings";
import { useSymbolsStore } from "@/store/symbols";
import { usePortfoliosStore } from "@/store/portfolios";
import { useWorkspaceStore } from "@/store/workspace";
import { StatusChrome } from "@/components/StatusChrome";

export default function Page() {
  // Bridge workflow ``action.notify_desktop`` intents to the OS notification
  // API. Safe no-op outside the Tauri webview.
  useDesktopNotificationBridge();

  useEffect(() => {
    // Register the module registry, seed the command palette from the enabled
    // modules, and connect to the Python sidecar. Runs once on mount — which is
    // also why `PanelHost` only mounts dockview after this point, keeping the
    // static-export build SSR-safe.
    useModulesStore.getState().registerModules(vystedModules);
    useCommandPalette.getState().setCommands(useModulesStore.getState().enabledCommands());
    void useAppStore.getState().connectSidecar();

    // Dev-only: bring up the tauri-plugin-mcp in-webview bridge so the local
    // test-automation rig (snapshot / click / console + network capture) can
    // drive the real app. No-op in the production static export (dead-stripped)
    // and harmless outside the Tauri webview.
    initDevMcpBridge();

    let teardown: (() => void) | null = null;
    let alive = true;
    void bootstrapPlugins().then((dispose) => {
      if (!alive) {
        dispose();
        return;
      }
      teardown = dispose;
      useCommandPalette.getState().setCommands(useModulesStore.getState().enabledCommands());
    });

    const unsubscribeEnabled = useModulesStore.subscribe((state, previous) => {
      if (state.enabled !== previous.enabled) {
        useCommandPalette.getState().setCommands(useModulesStore.getState().enabledCommands());
      }
    });
    const unsubscribeModules = useModulesStore.subscribe((state, previous) => {
      if (state.modules !== previous.modules) {
        useCommandPalette.getState().setCommands(useModulesStore.getState().enabledCommands());
      }
    });
    // Persist UI state that does NOT move the dockview layout (so the layout
    // autosave wouldn't catch it): the watchlist, the agent mode, the agent
    // dock geometry, and per-provider model overrides all ride the workspace
    // blob (see `src/lib/workspace.ts`).
    const unsubscribeSymbols = useSymbolsStore.subscribe((state, previous) => {
      if (state.entries !== previous.entries) {
        void autosaveLayout();
      }
    });
    const unsubscribePortfolios = usePortfoliosStore.subscribe((state, previous) => {
      if (state.portfolios !== previous.portfolios || state.activeId !== previous.activeId) {
        void autosaveLayout();
      }
    });
    const unsubscribeAgentMode = useAgentModeStore.subscribe((state, previous) => {
      if (state.mode !== previous.mode) {
        void autosaveLayout();
      }
    });
    const unsubscribeDock = useAgentDockStore.subscribe((state, previous) => {
      if (state.collapsed !== previous.collapsed || state.width !== previous.width) {
        void autosaveLayout();
      }
    });
    const unsubscribeModels = useModelSelectionStore.subscribe((state, previous) => {
      if (state.overrides !== previous.overrides) {
        void autosaveLayout();
      }
    });
    // The default provider (FR-038) rides the blob (serializeWorkspace captures it)
    // but, like the model overrides above, it does not move the dockview layout —
    // so it needs its own autosave trigger or "set DeepSeek as default" is lost on
    // relaunch (the default-provider-not-persisting bug).
    const unsubscribeDefaultProvider = useLLMProvidersStore.subscribe((state, previous) => {
      if (state.defaultProviderId !== previous.defaultProviderId) {
        void autosaveLayout();
      }
    });
    const unsubscribeAutonomy = useAgentAutonomyStore.subscribe((state, previous) => {
      if (state.autonomy !== previous.autonomy) {
        void autosaveLayout();
      }
    });
    // The web-search tier + SearXNG URL (FR-080/083/084) ride the blob but do not
    // move the dockview layout, so they need their own autosave trigger or a tier
    // change is lost on relaunch (same pattern as model overrides above).
    const unsubscribeSearch = useSearchSettingsStore.subscribe((state, previous) => {
      if (state.tier !== previous.tier || state.searxngUrl !== previous.searxngUrl) {
        void autosaveLayout();
      }
    });
    return () => {
      alive = false;
      unsubscribeEnabled();
      unsubscribeModules();
      unsubscribeSymbols();
      unsubscribePortfolios();
      unsubscribeAgentMode();
      unsubscribeDock();
      unsubscribeModels();
      unsubscribeDefaultProvider();
      unsubscribeAutonomy();
      unsubscribeSearch();
      teardown?.();
    };
  }, []);

  const openPalette = useCommandPalette((state) => state.setOpen);
  const openPanel = useWorkspaceStore((state) => state.openPanel);
  const openSaveLayout = useWorkspaceDialog((state) => state.openSave);
  const toggleAgent = useAgentDockStore((state) => state.toggleCollapsed);
  const agentCollapsed = useAgentDockStore((state) => state.collapsed);

  return (
    <MotionConfig reducedMotion="user" transition={{ ease: EASE_INSTRUMENT }}>
      <main className="bg-charcoal-950 flex h-full w-full flex-col overflow-hidden">
        <CommandPalette />
        <WorkspaceDialog />
        {/* Header fascia. The agent toggle, palette, and save controls sit left;
          the live status chrome (sidecar / provider / running agents) and the
          settings entry sit right. */}
        <header className="bg-charcoal-925 relative flex h-9 shrink-0 items-center gap-3 px-3">
          <div className="flex items-center gap-2 select-none">
            <span aria-hidden="true" className="size-2 rounded-[2px] bg-amber-400" />
            <span className="text-charcoal-100 font-serif text-[17px] leading-none font-semibold tracking-[0.01em]">
              VYSTED
            </span>
            <span className="hud-label mt-px leading-none">Terminal</span>
          </div>
          <div className="bg-charcoal-700 mx-1 h-4 w-px" aria-hidden="true" />
          <button
            type="button"
            onClick={toggleAgent}
            aria-pressed={!agentCollapsed}
            className={cn(
              "flex items-center gap-1.5 font-mono text-xs transition-colors",
              agentCollapsed
                ? "text-charcoal-400 hover:text-lume"
                : "text-amber-300 hover:text-amber-200",
            )}
            aria-label={agentCollapsed ? "Show agent panel" : "Hide agent panel"}
            title={agentCollapsed ? "Show agent panel (⌘B)" : "Hide agent panel (⌘B)"}
          >
            {agentCollapsed ? (
              <PanelLeftOpen className="h-3.5 w-3.5" />
            ) : (
              <PanelLeftClose className="h-3.5 w-3.5" />
            )}
            Agent
          </button>
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
          <StatusChrome />
          <button
            type="button"
            onClick={() => openPanel("settings")}
            className="text-charcoal-400 hover:text-lume hover:bg-charcoal-800 flex size-6 items-center justify-center rounded-md transition-colors"
            aria-label="Open settings"
            title="Settings"
          >
            <Settings2 className="h-4 w-4" />
          </button>
          <div
            className="tick-rule pointer-events-none absolute inset-x-0 bottom-0"
            aria-hidden="true"
          />
        </header>
        <OnboardingBanner />
        <div className="min-h-0 flex-1">
          <AgentDock>
            <PanelHost />
          </AgentDock>
        </div>
        {/* §6.5 surfaces mounted at the shell so they are reachable regardless of
          layout: the agent-proposed order confirm dialog (FR-011) and the
          layered first-launch disclaimer (§6.5 #8). */}
        <OrderConfirmationDialog />
        <DisclaimerFlow />
      </main>
    </MotionConfig>
  );
}
