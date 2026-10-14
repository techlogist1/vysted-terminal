// Dev-only bridge for the tauri-plugin-mcp test-automation rig
// (DaveDev42/tauri-plugin-mcp). Initializes the in-webview JS bridge that the
// `tauri-mcp` MCP server drives over a loopback socket — snapshot, click, fill,
// and console/network log capture.
//
// Hard dev-only guarantee: the dynamic `import("tauri-plugin-mcp")` sits behind
// a `process.env.NODE_ENV === "production"` early-return. Next.js inlines
// `process.env.NODE_ENV` and dead-code-eliminates the branch in the
// static-export production build, so the `tauri-plugin-mcp` devDependency
// (absent from release installs) is never referenced or bundled. The Rust
// plugin that answers this bridge is likewise compiled out of release builds
// via the Cargo `dev-tools` feature.

import { useAgentAutonomyStore } from "@/store/agent-autonomy";
import { useAgentModeStore } from "@/store/agent-mode";
import { useChartCommandStore } from "@/store/chart-command";
import { useChartSyncBus } from "@/store/chart-sync";
import { useChatHistoryStore } from "@/store/chat-history";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useModelCatalogStore } from "@/store/model-catalog";
import { useModelSelectionStore } from "@/store/model-selection";
import { useProposedChangesStore } from "@/store/proposed-changes";
import { useSettingsStore } from "@/store/settings";
import { useSymbolsStore } from "@/store/symbols";

export function initDevMcpBridge(): void {
  if (process.env.NODE_ENV === "production") return;
  if (typeof window === "undefined") return;
  // Dev-only: expose the agent act-path stores so the rig can drive + inspect
  // them deterministically (verify the chart-command channel, the autonomy
  // auto-apply, and the diff gate without round-tripping an LLM). Same NODE_ENV
  // strip + `dev-tools` guard as the bridge below — never in the production export.
  (window as unknown as { __vystedStores?: unknown }).__vystedStores = {
    chartCommand: useChartCommandStore,
    autonomy: useAgentAutonomyStore,
    proposedChanges: useProposedChangesStore,
    // Pass B B1: let the rig set region + seed watchlist symbols via
    // evaluate_script (region header + locale-native data verification).
    settings: useSettingsStore,
    symbols: useSymbolsStore,
    // JARVIS sprint: the agent-surface stores, so the rig can verify the live
    // research activity trace (Track A) and the inferred-intent mode (Track B)
    // deterministically — without round-tripping a (weak local) tool-calling LLM.
    chatHistory: useChatHistoryStore,
    agentMode: useAgentModeStore,
    // JARVIS sprint 2 (Track 4): the provider/model stores, so the rig can verify
    // the default-provider/model persistence round-trip (set default → autosave →
    // reload → still default) end-to-end without driving the UI selects.
    llmProviders: useLLMProvidersStore,
    modelSelection: useModelSelectionStore,
    modelCatalog: useModelCatalogStore,
    // R4 Bug-3: the cross-chart sync bus, so the rig can deterministically inject
    // a malformed visible-range broadcast (NaN / inverted from>to) at a subscribed
    // chart and confirm the guard prevents the lightweight-charts throw + React
    // error overlay — the exact crash input, against the REAL chart.
    chartSync: useChartSyncBus,
  };
  void import("tauri-plugin-mcp")
    .then(({ initMcpBridge }) => initMcpBridge())
    .catch((err) => {
      // Expected outside the Tauri webview (e.g. a plain browser at :3000).
      console.warn("[mcp] dev bridge init skipped:", err);
    });
}
