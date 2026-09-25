import { useEffect } from "react";
import { MotionConfig } from "framer-motion";
import {
  LayoutGrid,
  Maximize2,
  Minimize2,
  PanelLeftClose,
  PanelLeftOpen,
  Save,
  Settings2,
} from "lucide-react";

import { AgentDock } from "@/components/AgentDock";
import { CommandPalette } from "@/components/CommandPalette";
import { OnboardingBanner } from "@/components/OnboardingBanner";
import { OnboardingFlow } from "@/components/OnboardingFlow";
import { PanelHost } from "@/components/PanelHost";
import { useDesktopNotificationBridge } from "@/lib/desktop-notification";
import { initDevMcpBridge } from "@/lib/dev-mcp-bridge";
import { executeCommand } from "@/lib/commands";
import { getSecret, KEYCHAIN_NAMESPACES, migrateDevKeystore } from "@/lib/keychain";
import { initMenuBridge } from "@/lib/menu-bridge";
import { bootstrapPlugins } from "@/lib/plugin-bootstrap";
import { wireAutosaveTriggers } from "@/lib/workspace";
import { cn } from "@/lib/utils";
import { EASE_INSTRUMENT } from "@/lib/motion";
import { vystedModules } from "@/modules";
import { DisclaimerFlow } from "@/modules/safety";
import { WorkspaceDialog } from "@/modules/platform/WorkspaceDialog";
import { useWorkspaceDialog } from "@/modules/platform/workspace-dialog-store";
import { useAgentDockStore } from "@/store/agent-dock";
import { useAppStore } from "@/store/app";
import { useCommandPalette } from "@/store/command-palette";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useModelCatalogStore } from "@/store/model-catalog";
import {
  formatBinding,
  getRegisteredAction,
  resolveKeyboardAction,
  useKeybindingsStore,
} from "@/store/keybindings";
import { useModulesStore } from "@/store/modules";
import { usePluginsStore } from "@/store/plugins";
import { useProviderKeysStore } from "@/store/provider-keys";
import { registerSavedWebhooks } from "@/store/workflow";
import { useWorkspaceStore } from "@/store/workspace";
import { StatusChrome } from "@/components/StatusChrome";

/** How long the layout restore waits on plugin bootstrap before going ahead. */
const PLUGINS_READY_FALLBACK_MS = 15_000;

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

    // One-time dev-keystore migration (R9): in a dev build, copy existing
    // secrets from the OS keychain into the git-ignored local keystore so
    // `tauri dev` never reads the keychain again — no per-cdhash SecurityAgent
    // dialog. The one migration read may raise ONE final dialog; idempotent and
    // a pure no-op in release. Re-probe provider keys after so migrated keys
    // show immediately. Best-effort: never throws into boot.
    void migrateDevKeystore().then(() => {
      void useProviderKeysStore.getState().refresh();
      // Hand every saved workflow's keychain-held webhook URL to the sidecar's
      // process memory so a scheduled fire can deliver (R15-AGENT-023).
      // Best-effort: a missing URL leaves that node to error honestly.
      registerSavedWebhooks((ref) => getSecret(KEYCHAIN_NAMESPACES.workflowWebhook(ref))).catch(
        (error: unknown) => console.warn("[workflow] webhook registration failed", error),
      );
    });

    // Warm the default provider's LIVE model catalog up front so the model pickers
    // are populated from the full live list (e.g. OpenRouter's hundreds) before the
    // user ever opens a dropdown — otherwise the first open can briefly show the
    // small static fallback while the fetch is in flight. Idempotent + cached; the
    // default-provider subscription below re-warms it when the restore changes it.
    void useModelCatalogStore
      .getState()
      .fetchCatalog(useLLMProvidersStore.getState().defaultProviderId);

    // Dev-only: bring up the tauri-plugin-mcp in-webview bridge so the local
    // test-automation rig (snapshot / click / console + network capture) can
    // drive the real app. No-op in the production static export (dead-stripped)
    // and harmless outside the Tauri webview.
    initDevMcpBridge();

    // macOS Layout menu bridge (003) — applies the native menu's layout-mode
    // selection to the live cockpit. No-op outside a Tauri webview.
    const disposeMenu = initMenuBridge();

    let teardown: (() => void) | null = null;
    let alive = true;
    // PanelHost restores the saved layout only once plugin modules have
    // registered. ponytail: a fixed fallback so a hung bootstrap (e.g. a slow
    // cold sidecar) can't hold the cockpit empty; a plugin panel saved in the
    // layout is lost only when bootstrap outlives it.
    const pluginsReadyFallback = setTimeout(
      () => usePluginsStore.getState().setPluginsReady(true),
      PLUGINS_READY_FALLBACK_MS,
    );
    void bootstrapPlugins()
      .then((dispose) => {
        if (!alive) {
          dispose();
          return;
        }
        teardown = dispose;
        useCommandPalette.getState().setCommands(useModulesStore.getState().enabledCommands());
      })
      .finally(() => {
        // Settled either way (a failed bootstrap has nothing more to register).
        if (alive) {
          clearTimeout(pluginsReadyFallback);
          usePluginsStore.getState().setPluginsReady(true);
        }
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
    // Every persisted workspace slice autosaves through one registry (the
    // dockview layout's own trigger is wired by PanelHost after the restore).
    const unwireAutosave = wireAutosaveTriggers();
    // Warm the newly-default provider's live catalog (e.g. after a workspace
    // restore flips the seed `ollama` to the persisted `openrouter`) so the
    // Settings/HUD model pickers show the full live list without a load-window
    // gap on the static fallback.
    const unsubscribeDefaultProvider = useLLMProvidersStore.subscribe((state, previous) => {
      if (state.defaultProviderId !== previous.defaultProviderId) {
        void useModelCatalogStore.getState().fetchCatalog(state.defaultProviderId);
      }
    });
    return () => {
      alive = false;
      clearTimeout(pluginsReadyFallback);
      usePluginsStore.getState().setPluginsReady(false);
      unsubscribeEnabled();
      unsubscribeModules();
      unwireAutosave();
      unsubscribeDefaultProvider();
      disposeMenu();
      teardown?.();
    };
  }, []);

  // The one keydown dispatcher (R15-UI-016 / R15-CODE-FRONTEND-016):
  // `resolveKeyboardAction` picks the `DEFAULT_KEYBINDINGS` id whose EFFECTIVE
  // (remap-aware) binding matches the event; this then fires either a
  // registered shell-action handler (`registerAction` — `palette.open`,
  // `agent.mode.*`, `agent.toggle`, `changes.*`, each owned by its component)
  // or, for a module command id (`chart.open`, `platform.save-workspace`, …),
  // the module's own command handler via `executeCommand` — the same path the
  // palette uses. A default with neither is a dead entry and is silently
  // skipped (there are none after this migration).
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const typing =
        !!target &&
        (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable);

      const resolved = resolveKeyboardAction(event, typing);
      if (!resolved) {
        return;
      }
      const registered = getRegisteredAction(resolved.actionId);
      if (registered) {
        event.preventDefault();
        registered();
        return;
      }
      const command = useModulesStore
        .getState()
        .enabledCommands()
        .find((c) => c.id === resolved.actionId);
      if (command) {
        event.preventDefault();
        executeCommand(command);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const openPalette = useCommandPalette((state) => state.setOpen);
  const openPanel = useWorkspaceStore((state) => state.openPanel);
  const openSaveLayout = useWorkspaceDialog((state) => state.openSave);
  const toggleAgent = useAgentDockStore((state) => state.toggleCollapsed);
  const agentCollapsed = useAgentDockStore((state) => state.collapsed);
  const agentMaximized = useAgentDockStore((state) => state.maximized);
  const toggleAgentMaximized = useAgentDockStore((state) => state.toggleMaximized);
  const agentChord = formatBinding(useKeybindingsStore((s) => s.bindingFor("agent.toggle")));
  const paletteChord = formatBinding(useKeybindingsStore((s) => s.bindingFor("palette.open")));

  return (
    <MotionConfig reducedMotion="user" transition={{ ease: EASE_INSTRUMENT }}>
      <main className="bg-charcoal-950 flex h-full w-full flex-col overflow-hidden">
        <CommandPalette />
        <WorkspaceDialog />
        {/* Header fascia. The agent toggle, palette, and save controls sit left;
          the live status chrome (sidecar / provider / running agents) and the
          settings entry sit right. */}
        <header className="bg-charcoal-925 relative flex h-12 shrink-0 items-center gap-4 px-4">
          {/* Mark-only brand — no text wordmark (Cursor/Linear-minimal). The
              accessible name lives on the mark; the document title carries "Vysted". */}
          <div className="flex items-center select-none" aria-label="Vysted" title="Vysted">
            <span aria-hidden="true" className="rounded-control bg-charcoal-200 size-3" />
          </div>
          <div className="bg-charcoal-700 mx-1 h-5 w-px" aria-hidden="true" />
          <button
            type="button"
            onClick={toggleAgent}
            aria-pressed={!agentCollapsed}
            className={cn(
              "text-caption flex items-center gap-2 transition-colors",
              agentCollapsed
                ? "text-charcoal-400 hover:text-lume"
                : "text-charcoal-100 hover:text-lume",
            )}
            aria-label={agentCollapsed ? "Show agent panel" : "Hide agent panel"}
            title={`${agentCollapsed ? "Show" : "Hide"} agent panel (${agentChord})`}
          >
            {agentCollapsed ? (
              <PanelLeftOpen className="h-4 w-4" />
            ) : (
              <PanelLeftClose className="h-4 w-4" />
            )}
            Agent
          </button>
          {agentCollapsed ? null : (
            <button
              type="button"
              onClick={toggleAgentMaximized}
              aria-pressed={agentMaximized}
              className="text-charcoal-400 hover:text-lume transition-colors"
              aria-label={agentMaximized ? "Restore the cockpit" : "Maximize the agent"}
              title={agentMaximized ? "Restore the cockpit" : "Maximize the agent"}
            >
              {agentMaximized ? (
                <Minimize2 className="h-4 w-4" />
              ) : (
                <Maximize2 className="h-4 w-4" />
              )}
            </button>
          )}
          <button
            type="button"
            onClick={() => openPalette(true)}
            className="text-charcoal-300 hover:text-lume text-caption flex items-center gap-2 transition-colors"
            aria-label="Open command palette"
          >
            <LayoutGrid className="h-4 w-4" />
            Open panel
            <kbd className="border-charcoal-700 text-charcoal-500 rounded-control text-micro border px-1 py-0.5">
              {paletteChord}
            </kbd>
          </button>
          <button
            type="button"
            onClick={openSaveLayout}
            className="text-charcoal-300 hover:text-lume text-caption flex items-center gap-2 transition-colors"
            aria-label="Save layout"
          >
            <Save className="h-4 w-4" />
            Save layout
          </button>
          <div className="flex-1" />
          <StatusChrome />
          <button
            type="button"
            onClick={() => openPanel("settings")}
            className="text-charcoal-400 hover:text-lume hover:bg-charcoal-800 rounded-control flex size-8 items-center justify-center transition-colors"
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
        {/* The first-launch research terms, mounted at the shell so they are
          reachable regardless of layout. */}
        <DisclaimerFlow />
        {/* First-run onboarding (Track 2). Renders AFTER the first-launch terms (it
          sequences on `firstLaunchTosAcked`), is dismissible, and shows once —
          the terminal works keyless, so this is an upgrade, not a gate. */}
        <OnboardingFlow />
      </main>
    </MotionConfig>
  );
}
