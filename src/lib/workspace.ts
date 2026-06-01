/**
 * Workspace serialization — `.vysted-workspace` save/load.
 *
 * A workspace captures two things: the dockview panel layout and the modules
 * `enabled` map. Serialising both means reloading a workspace restores not just
 * which panels are open and where, but which modules are active. The sidecar
 * owns the files (`/workspace` endpoints); this module is the frontend half —
 * it builds the payload from the live stores and applies a loaded payload back
 * onto them.
 *
 * The shape is deliberately open: `SerializedWorkspace` carries the two fields
 * the platform needs plus an index signature so a future phase can add keys
 * without a sidecar change (the sidecar stores the body opaquely).
 */

import type { DockviewApi, SerializedDockview } from "dockview";

import { applyDefaultLayout } from "@/config/default-layout";
import { collectPanelComponents } from "@/lib/module-registry";
import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { useAgentDockStore } from "@/store/agent-dock";
import { useAgentModeStore } from "@/store/agent-mode";
import { type AgentAutonomy, isAgentAutonomy, useAgentAutonomyStore } from "@/store/agent-autonomy";
import { useChartDrawingsStore } from "@/store/chart-drawings";
import { useKeybindingsStore } from "@/store/keybindings";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useModelSelectionStore } from "@/store/model-selection";
import { useModulesStore } from "@/store/modules";
import { type SearchSettingsBundle, useSearchSettingsStore } from "@/store/search-settings";
import { type SettingsBundle, useSettingsStore } from "@/store/settings";
import { type SymbolEntry, useSymbolsStore } from "@/store/symbols";
import { type Portfolio, usePortfoliosStore } from "@/store/portfolios";
import { AUTOSAVE_LAYOUT_NAME, useWorkspaceStore } from "@/store/workspace";
import type { LLMProviderId } from "../../types/ai";
import { type AgentMode, isAgentMode } from "../../types/agent-modes";
import type { WorkspaceDrawings } from "../../types/drawings";

/** The serialised form of a workspace, persisted as a `.vysted-workspace` file. */
export interface SerializedWorkspace {
  /** Workspace name — also the file name on the sidecar. */
  name: string;
  /** The dockview layout, as produced by `DockviewApi.toJSON()`. */
  layout: SerializedDockview;
  /** The modules `enabled` map at save time. */
  enabledModules: Record<string, boolean>;
  /**
   * Per-chart-panel drawings collection (Phase 2). Optional for backward
   * compatibility with workspaces saved before drawings shipped.
   */
  chartDrawings?: WorkspaceDrawings;
  /**
   * The default AI provider the chat sidebar uses. Persisted here so the
   * Settings "Set default" choice survives a relaunch (it was in-memory-only
   * and reset to "anthropic" every launch — regression-95 BUG-7). Optional for
   * workspaces saved before this shipped.
   */
  defaultProviderId?: LLMProviderId;
  /**
   * The user's tracked watchlist. Persisted so a customised watchlist survives
   * a relaunch (it was in-memory-only and reset to the default set every launch
   * — Phase 10 customizability). Optional for workspaces saved before this.
   */
  watchlist?: SymbolEntry[];
  /**
   * The user's named portfolios + the active one. Persisted so manually tracked
   * holdings survive a relaunch (frontend-managed, no broker sync). Optional for
   * blobs saved before multi-portfolio shipped (absent → one empty default).
   */
  portfolios?: { list: Portfolio[]; activeId: string };
  /**
   * The active agent mode (Ask / Edit / Build / Delegate). Persisted so a
   * cockpit reopens in the mode the user left it in (FR-003). Optional for
   * workspaces saved before this shipped.
   */
  agentMode?: AgentMode;
  /**
   * The agent AUTONOMY mode (ask / auto) — orthogonal to agentMode. Persisted so
   * a user who turned on auto-apply keeps it across a relaunch. Optional for older
   * blobs (absent → the default `ask` gate).
   */
  autonomyMode?: AgentAutonomy;
  /**
   * The agent dominant-column geometry (collapsed + width in px) so the
   * agent-first layout (FR-001) survives a relaunch. Optional for older blobs.
   */
  agentDock?: { collapsed: boolean; width: number };
  /**
   * Per-provider model overrides (FR-004). Optional for older blobs; the
   * per-provider defaults apply when absent.
   */
  modelOverrides?: Partial<Record<LLMProviderId, string>>;
  /**
   * Trust marker for {@link modelOverrides}. Blobs written before this existed
   * captured the then-current default as a pseudo-override (the `llama3.1:8b`
   * shadowing bug); on restore those are treated as untrusted and dropped once,
   * reverting to live defaults. Restored only when this equals the current
   * {@link MODEL_OVERRIDES_VERSION}.
   */
  modelOverridesV?: number;
  /**
   * Remappable-keybinding overrides (FR-038/FR-039), keyed by action id. Only
   * the user's remaps persist — the immutable default keymap is not stored.
   * Optional for older blobs (no overrides → defaults apply).
   */
  keybindingOverrides?: Record<string, string>;
  /**
   * The local preferences bundle (FR-037, SC-011): default agent, provider
   * preference order, palette behaviour, starter-cockpit composition, panel
   * defaults, theme knobs. NEVER carries secrets. Optional for older blobs.
   */
  settings?: SettingsBundle;
  /**
   * The three-tier web-search preference (FR-080/083/084): the active tier +
   * the local SearXNG URL. NEVER carries the BYOK Exa key (keychain-only).
   * Optional for older blobs (absent → native tier, autodetect SearXNG).
   */
  searchSettings?: SearchSettingsBundle;
  /** Open to future-phase additions; the sidecar stores the body opaquely. */
  [key: string]: unknown;
}

/** Thrown when a workspace operation cannot complete. */
export class WorkspaceError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "WorkspaceError";
  }
}

/**
 * Bumped when {@link SerializedWorkspace.modelOverrides} trust semantics change.
 * See the field doc — gates the one-time drop of legacy captured overrides.
 */
const MODEL_OVERRIDES_VERSION = 1;

/**
 * Build the serialised workspace body from the live stores — the SINGLE source
 * for both explicit save ({@link serializeWorkspace}) and {@link autosaveLayout}
 * so a newly-added field can never half-persist (autosave-only or save-only).
 * Throws if the dockview layout has not mounted yet.
 */
function buildWorkspacePayload(name: string): SerializedWorkspace {
  const api = useWorkspaceStore.getState().dockviewApi;
  if (!api) {
    throw new WorkspaceError("The panel layout is not ready yet.");
  }
  return {
    name,
    layout: api.toJSON(),
    enabledModules: useModulesStore.getState().enabled,
    chartDrawings: useChartDrawingsStore.getState().snapshot(),
    defaultProviderId: useLLMProvidersStore.getState().defaultProviderId,
    watchlist: useSymbolsStore.getState().entries,
    portfolios: {
      list: usePortfoliosStore.getState().portfolios,
      activeId: usePortfoliosStore.getState().activeId,
    },
    agentMode: useAgentModeStore.getState().mode,
    autonomyMode: useAgentAutonomyStore.getState().autonomy,
    agentDock: {
      collapsed: useAgentDockStore.getState().collapsed,
      width: useAgentDockStore.getState().width,
    },
    modelOverrides: useModelSelectionStore.getState().overrides,
    modelOverridesV: MODEL_OVERRIDES_VERSION,
    keybindingOverrides: useKeybindingsStore.getState().overrides,
    settings: useSettingsStore.getState().toBundle(),
    searchSettings: useSearchSettingsStore.getState().toBundle(),
  };
}

/**
 * Capture the current workspace from the live stores: the dockview layout plus
 * the modules `enabled` map plus per-chart-panel drawings. Throws if the
 * dockview layout has not mounted yet.
 */
export function serializeWorkspace(name: string): SerializedWorkspace {
  return buildWorkspacePayload(name);
}

/**
 * Apply a loaded workspace back onto the live stores: restore the modules
 * `enabled` map, then the dockview layout, then the active workspace name.
 * Throws if the dockview layout has not mounted yet. Drawings (Phase 2) are
 * restored last and only when the loaded workspace carries them so older
 * workspaces still apply cleanly.
 */
export function deserializeWorkspace(workspace: SerializedWorkspace): void {
  const api = useWorkspaceStore.getState().dockviewApi;
  if (!api) {
    throw new WorkspaceError("The panel layout is not ready yet.");
  }
  // Restore the enabled map first so the panel components a layout references
  // resolve against the same module set that was active when it was saved.
  // Snapshot it so a throwing `fromJSON` (corrupt/truncated blob) rolls the
  // module set back instead of leaving it half-applied (regression-95 BUG-5).
  const prevEnabled = useModulesStore.getState().enabled;
  useModulesStore.getState().setEnabledMap(workspace.enabledModules);
  try {
    api.fromJSON(workspace.layout);
  } catch (error) {
    useModulesStore.getState().setEnabledMap(prevEnabled);
    throw error;
  }
  useWorkspaceStore.getState().setName(workspace.name);
  if (workspace.chartDrawings) {
    useChartDrawingsStore.getState().replaceAll(workspace.chartDrawings);
  } else {
    useChartDrawingsStore.getState().replaceAll({ byPanel: {} });
  }
  // Restore the persisted default AI provider (older workspaces lack it).
  if (workspace.defaultProviderId) {
    useLLMProvidersStore.getState().setDefaultProviderId(workspace.defaultProviderId);
  }
  // Restore the persisted watchlist (older workspaces lack it — keep the
  // default set in that case).
  if (Array.isArray(workspace.watchlist) && workspace.watchlist.length > 0) {
    useSymbolsStore.getState().setEntries(workspace.watchlist);
  }
  // Restore named portfolios (older blobs lack them — keep the empty default).
  if (workspace.portfolios && Array.isArray(workspace.portfolios.list)) {
    usePortfoliosStore.getState().setAll(workspace.portfolios.list, workspace.portfolios.activeId);
  }
  // Restore the agent mode / dock geometry / model overrides (older blobs lack
  // them — keep the defaults). Guarded so a corrupt value can't seed garbage.
  if (isAgentMode(workspace.agentMode)) {
    useAgentModeStore.getState().setMode(workspace.agentMode);
  }
  if (isAgentAutonomy(workspace.autonomyMode)) {
    useAgentAutonomyStore.getState().setAutonomy(workspace.autonomyMode);
  }
  if (workspace.agentDock && typeof workspace.agentDock === "object") {
    useAgentDockStore.getState().setCollapsed(Boolean(workspace.agentDock.collapsed));
    if (typeof workspace.agentDock.width === "number") {
      useAgentDockStore.getState().setWidth(workspace.agentDock.width);
    }
  }
  // Restore model overrides ONLY from a blob written with the current trust
  // marker; legacy blobs (no `modelOverridesV`) captured the then-default as a
  // pseudo-override (the `llama3.1:8b` shadowing bug) and are dropped once,
  // reverting to live defaults. `setOverrides` additionally prunes any model no
  // longer offered for its provider.
  if (
    workspace.modelOverridesV === MODEL_OVERRIDES_VERSION &&
    workspace.modelOverrides &&
    typeof workspace.modelOverrides === "object"
  ) {
    useModelSelectionStore.getState().setOverrides(workspace.modelOverrides);
  }
  // Restore remappable-keybinding overrides + the preferences bundle (older
  // blobs lack them — keep the defaults). `setOverrides` normalises on the way
  // in; `setAll` merges over the seed so a partial blob can't strip a field.
  if (workspace.keybindingOverrides && typeof workspace.keybindingOverrides === "object") {
    useKeybindingsStore.getState().setOverrides(workspace.keybindingOverrides);
  }
  if (workspace.settings && typeof workspace.settings === "object") {
    useSettingsStore.getState().setAll(workspace.settings);
  }
  // Restore the web-search preference (older blobs lack it — keep the native
  // default). `setAll` merges over the seed so a partial blob can't strip a
  // field and a garbled tier falls back.
  if (workspace.searchSettings && typeof workspace.searchSettings === "object") {
    useSearchSettingsStore.getState().setAll(workspace.searchSettings);
  }
}

/** Build the sidecar `/workspace` URL, optionally for a single named workspace. */
async function workspaceUrl(name?: string): Promise<string> {
  const base = await getSidecarBaseUrl();
  const path = name === undefined ? "/workspace" : `/workspace/${encodeURIComponent(name)}`;
  return new URL(path, base).toString();
}

/** List the names of every workspace saved on the sidecar. */
export async function listWorkspaces(): Promise<string[]> {
  const response = await fetch(await workspaceUrl());
  if (!response.ok) {
    throw new WorkspaceError(`Could not list workspaces (HTTP ${response.status}).`);
  }
  try {
    return (await response.json()) as string[];
  } catch {
    throw new WorkspaceError("Could not parse the workspace list response (malformed JSON).");
  }
}

/**
 * Serialise the current workspace under `name` and persist it on the sidecar,
 * overwriting any existing workspace with the same name.
 */
export async function saveWorkspace(name: string): Promise<void> {
  const trimmed = name.trim();
  if (!trimmed) {
    throw new WorkspaceError("A workspace name is required.");
  }
  const workspace = serializeWorkspace(trimmed);
  const response = await fetch(await workspaceUrl(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: trimmed, workspace }),
  });
  if (!response.ok) {
    throw new WorkspaceError(`Could not save workspace "${trimmed}" (HTTP ${response.status}).`);
  }
  // Mark the just-saved layout active so it shows the "active" badge, matching
  // loadWorkspace's behaviour (regression-95 BUG-4).
  useWorkspaceStore.getState().setName(trimmed);
}

/** Load a saved workspace from the sidecar and apply it to the live stores. */
export async function loadWorkspace(name: string): Promise<void> {
  const trimmed = name.trim();
  if (!trimmed) {
    throw new WorkspaceError("A workspace name is required.");
  }
  const response = await fetch(await workspaceUrl(trimmed));
  if (!response.ok) {
    throw new WorkspaceError(`Could not load workspace "${trimmed}" (HTTP ${response.status}).`);
  }
  let workspace: SerializedWorkspace;
  try {
    workspace = (await response.json()) as SerializedWorkspace;
  } catch {
    throw new WorkspaceError(`Could not parse workspace "${trimmed}" (malformed JSON).`);
  }
  deserializeWorkspace(workspace);
}

/**
 * True when the serialized layout references a panel component id that is not
 * currently registered. dockview instantiates panel content eagerly during
 * `fromJSON`, so an unknown component (e.g. a plugin panel whose module
 * registers asynchronously after `handleReady`) throws synchronously and
 * half-mutates the grid. We detect that up-front and skip cleanly to default.
 * An unreadable layout shape is treated as "unknown" so we conservatively
 * skip-to-default rather than risk the throw.
 */
function layoutReferencesUnknownComponent(layout: SerializedDockview): boolean {
  const known = new Set(Object.keys(collectPanelComponents(useModulesStore.getState().modules)));
  const panels = (layout as { panels?: Record<string, { contentComponent?: string }> }).panels;
  if (!panels || typeof panels !== "object") {
    return true;
  }
  return Object.values(panels).some(
    (panel) => panel?.contentComponent !== undefined && !known.has(panel.contentComponent),
  );
}

/**
 * Restore the auto-saved "last session" cockpit if one exists, else apply the
 * bundled default layout. Called once on launch from PanelHost; this is what
 * makes a customised cockpit survive a relaunch (Track C). Never throws — a
 * failed restore falls back to the default so the app always boots usable.
 * Returns true when a saved session was restored.
 *
 * The fetch below awaits a Tauri IPC + localhost round-trip. Under
 * StrictMode/HMR the dockview api can be disposed and replaced while we wait,
 * so re-check that THIS api is still the live one before every mutation —
 * touching a disposed api throws `element.parentElement is null`.
 */
export async function restoreLastSessionOrDefault(
  api: DockviewApi,
  enabledPanelIds: Set<string>,
): Promise<boolean> {
  const isLive = () => useWorkspaceStore.getState().dockviewApi === api;
  try {
    const response = await fetch(await workspaceUrl(AUTOSAVE_LAYOUT_NAME));
    if (!isLive()) {
      return false; // api was disposed/replaced during the fetch
    }
    if (response.ok) {
      const workspace = (await response.json()) as SerializedWorkspace;
      if (!isLive()) {
        return false;
      }
      // Skip to default if the saved layout references a component not yet
      // registered (plugin panels register async) — that would throw mid-
      // `fromJSON` and corrupt the grid for the fallback below.
      if (layoutReferencesUnknownComponent(workspace.layout)) {
        applyDefaultLayout(api, enabledPanelIds);
        return false;
      }
      deserializeWorkspace(workspace);
      // The reserved slot's name is internal — present the restored cockpit
      // under the neutral "default" name, not "__autosave__".
      useWorkspaceStore.getState().setName("default");
      return true;
    }
  } catch (error) {
    // Restore failed — log (Track A discipline) then fall through to default.
    console.warn("[workspace] session restore failed; using default layout.", error);
  }
  if (!isLive()) {
    return false;
  }
  // Re-base the fallback on a clean grid so a partial `fromJSON` can't leave a
  // corrupt grid under `addPanel`.
  api.clear();
  applyDefaultLayout(api, enabledPanelIds);
  return false;
}

/**
 * Persist the current cockpit to the reserved autosave slot. Best-effort: a
 * transient sidecar failure is swallowed (the next layout change retries) and
 * the active workspace name is left unchanged. No-op before the layout mounts.
 */
export async function autosaveLayout(): Promise<void> {
  const api = useWorkspaceStore.getState().dockviewApi;
  if (!api) {
    return;
  }
  try {
    const payload = buildWorkspacePayload(AUTOSAVE_LAYOUT_NAME);
    await fetch(await workspaceUrl(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: AUTOSAVE_LAYOUT_NAME, workspace: payload }),
    });
  } catch {
    // Best-effort autosave; ignore transient failures.
  }
}

/** Delete a saved workspace from the sidecar. */
export async function deleteWorkspace(name: string): Promise<void> {
  const trimmed = name.trim();
  if (!trimmed) {
    throw new WorkspaceError("A workspace name is required.");
  }
  const response = await fetch(await workspaceUrl(trimmed), { method: "DELETE" });
  if (!response.ok) {
    throw new WorkspaceError(`Could not delete workspace "${trimmed}" (HTTP ${response.status}).`);
  }
}
