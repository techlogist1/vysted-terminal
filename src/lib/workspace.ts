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
import { applyResearchSpaceLayout } from "@/lib/layout-templates";
import { collectPanelComponents } from "@/lib/module-registry";
import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { useChartCommandStore } from "@/store/chart-command";
import { useAgentDockStore } from "@/store/agent-dock";
import { useAgentModeStore } from "@/store/agent-mode";
import { type BriefBundle, useBriefStore } from "@/store/brief";
import { type NotesBundle, useNotesStore } from "@/store/notes";
import { type AgentAutonomy, isAgentAutonomy, useAgentAutonomyStore } from "@/store/agent-autonomy";
import { useChartDrawingsStore } from "@/store/chart-drawings";
import { useKeybindingsStore } from "@/store/keybindings";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useModelSelectionStore } from "@/store/model-selection";
import { useModulesStore } from "@/store/modules";
import { useResearchSpacesStore } from "@/store/research-spaces";
import { type SearchSettingsBundle, useSearchSettingsStore } from "@/store/search-settings";
import { type SavedScreen, deserializeSavedScreens, useScreenerStore } from "@/store/screener";
import { type SettingsBundle, useSettingsStore } from "@/store/settings";
import { type SymbolEntry, useSymbolsStore } from "@/store/symbols";
import { type Portfolio, usePortfoliosStore } from "@/store/portfolios";
import { AUTOSAVE_LAYOUT_NAME, useWorkspaceStore } from "@/store/workspace";
import type { LLMProviderId } from "../../types/ai";
import { type AgentMode, coerceAgentMode } from "../../types/agent-modes";
import type { WorkspaceDrawings } from "../../types/drawings";
import type { WorkspaceResearchSpaces } from "../../types/research-space";

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
   * holdings survive a relaunch (frontend-managed, hand-entered). Optional for
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
   * The web-search preference bundle (R9 two-tier): the authoritative research
   * tier (`tier_a` Unlimited Local / `tier_b` hosted research model), the
   * optional custom SearXNG URL, and the Tier B per-stop research models.
   * Older blobs (pre-R8 `tier`, R7/R8 `t1_local`/`t2_searxng`/`t3_hosted` +
   * `exaDirect`/`hostedEngine`) migrate on restore via the store's `setAll`
   * (hosted/Exa selections land on tier_b only when an OpenRouter key is
   * configured, else tier_a). NEVER carries a BYOK key (keychain-only).
   * Optional for older blobs (absent → tier_a).
   */
  searchSettings?: SearchSettingsBundle;
  /**
   * The most recent research brief JARVIS produced (FR-074). Non-secret research
   * output, so it rides the blob and survives a relaunch. `null`/absent when no
   * brief has been produced yet.
   */
  brief?: BriefBundle;
  /** In-app research notes (per-stock + general) — ride the blob like the brief
   * so they persist with a named workspace / per-stock research space (003). */
  notes?: NotesBundle;
  /**
   * TYPED research-space marker (S-19): the symbol this workspace researches,
   * present iff the workspace IS a research space. Replaces the fragile
   * `"Research: "` name-prefix detection — `isResearchSpace`/`researchSymbolOf`
   * read this field first and fall back to the prefix only for OLD blobs that
   * pre-date it. Absent on a non-research workspace.
   */
  researchSymbol?: string;
  /**
   * Per-research-space DURABLE agent memory (chat transcript + a short
   * prior-research summary), keyed by research-space workspace name. Rides the
   * blob so the copilot "remembers" what it researched in a space across a
   * relaunch (`src/store/research-spaces.ts`). Optional for older blobs.
   */
  researchSpaces?: WorkspaceResearchSpaces;
  /** The screener's saved screens. Optional for older blobs (absent → none). */
  savedScreens?: SavedScreen[];
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
 *
 * v3 (003 R3): the keyless default model is now the non-thinking, served
 * deepseek/deepseek-v4-flash (registry single source of truth). Any persisted
 * pre-R3 override (e.g. a captured minimax/minimax-m3) is dropped on load so the
 * workspace adopts the current default instead of shadowing it.
 */
const MODEL_OVERRIDES_VERSION = 3;

/**
 * One persisted slice of the workspace blob: what it writes, how it restores,
 * and which store change schedules an autosave. {@link PERSISTED_SLICES} is the
 * single registry — the payload, the restore and the autosave triggers all
 * iterate it, so a slice added here persists, restores and autosaves together.
 */
export interface PersistedSlice {
  /** The blob key this slice owns (`read` may also write a companion key). */
  key: string;
  read: () => Partial<SerializedWorkspace>;
  restore: (workspace: SerializedWorkspace) => void;
  /** Subscribe `onChange` to the change that must be persisted; returns the unsubscribe. */
  subscribe: (onChange: () => void) => () => void;
}

/** A `subscribe` that fires when any of the picked store fields changes identity. */
function onChange<S>(
  store: { subscribe: (listener: (state: S, previous: S) => void) => () => void },
  ...fields: ((state: S) => unknown)[]
): PersistedSlice["subscribe"] {
  return (notify) =>
    store.subscribe((state, previous) => {
      if (fields.some((field) => field(state) !== field(previous))) {
        notify();
      }
    });
}

/**
 * Every persisted slice, in restore order: the per-space memory archive
 * restores before the research marker so entering a space finds its transcript.
 */
export const PERSISTED_SLICES: readonly PersistedSlice[] = [
  {
    // Restored before the layout so the panel components a layout references
    // resolve against the module set that was active when it was saved.
    key: "enabledModules",
    read: () => ({ enabledModules: useModulesStore.getState().enabled }),
    restore: (workspace) => useModulesStore.getState().setEnabledMap(workspace.enabledModules),
    subscribe: onChange(useModulesStore, (s) => s.enabled),
  },
  {
    key: "chartDrawings",
    read: () => ({ chartDrawings: useChartDrawingsStore.getState().snapshot() }),
    restore: (workspace) =>
      useChartDrawingsStore.getState().replaceAll(workspace.chartDrawings ?? { byPanel: {} }),
    subscribe: onChange(useChartDrawingsStore, (s) => s.byPanel),
  },
  {
    key: "defaultProviderId",
    read: () => ({ defaultProviderId: useLLMProvidersStore.getState().defaultProviderId }),
    restore: (workspace) => {
      if (workspace.defaultProviderId) {
        useLLMProvidersStore.getState().setDefaultProviderId(workspace.defaultProviderId);
      }
    },
    subscribe: onChange(useLLMProvidersStore, (s) => s.defaultProviderId),
  },
  {
    // Older blobs lack it (or carry an empty list) — keep the default set.
    key: "watchlist",
    read: () => ({ watchlist: useSymbolsStore.getState().entries }),
    restore: (workspace) => {
      if (Array.isArray(workspace.watchlist) && workspace.watchlist.length > 0) {
        useSymbolsStore.getState().setEntries(workspace.watchlist);
      }
    },
    subscribe: onChange(useSymbolsStore, (s) => s.entries),
  },
  {
    // Older blobs lack it — keep the empty default portfolio.
    key: "portfolios",
    read: () => ({
      portfolios: {
        list: usePortfoliosStore.getState().portfolios,
        activeId: usePortfoliosStore.getState().activeId,
      },
    }),
    restore: (workspace) => {
      if (workspace.portfolios && Array.isArray(workspace.portfolios.list)) {
        usePortfoliosStore
          .getState()
          .setAll(workspace.portfolios.list, workspace.portfolios.activeId);
      }
    },
    subscribe: onChange(
      usePortfoliosStore,
      (s) => s.portfolios,
      (s) => s.activeId,
    ),
  },
  {
    // A legacy mode ("ask"/"edit"/"build") folds into the single inferred
    // "agent" surface (Track B); only restore when a value is set.
    key: "agentMode",
    read: () => ({ agentMode: useAgentModeStore.getState().mode }),
    restore: (workspace) => {
      if (workspace.agentMode !== undefined) {
        useAgentModeStore.getState().setMode(coerceAgentMode(workspace.agentMode));
      }
    },
    subscribe: onChange(useAgentModeStore, (s) => s.mode),
  },
  {
    key: "autonomyMode",
    read: () => ({ autonomyMode: useAgentAutonomyStore.getState().autonomy }),
    restore: (workspace) => {
      if (isAgentAutonomy(workspace.autonomyMode)) {
        useAgentAutonomyStore.getState().setAutonomy(workspace.autonomyMode);
      }
    },
    subscribe: onChange(useAgentAutonomyStore, (s) => s.autonomy),
  },
  {
    key: "agentDock",
    read: () => ({
      agentDock: {
        collapsed: useAgentDockStore.getState().collapsed,
        width: useAgentDockStore.getState().width,
      },
    }),
    restore: (workspace) => {
      if (workspace.agentDock && typeof workspace.agentDock === "object") {
        useAgentDockStore.getState().setCollapsed(Boolean(workspace.agentDock.collapsed));
        if (typeof workspace.agentDock.width === "number") {
          useAgentDockStore.getState().setWidth(workspace.agentDock.width);
        }
      }
    },
    subscribe: onChange(
      useAgentDockStore,
      (s) => s.collapsed,
      (s) => s.width,
    ),
  },
  {
    // Restored ONLY from a blob written with the current trust marker; legacy
    // blobs (no `modelOverridesV`) captured the then-default as a
    // pseudo-override (the `llama3.1:8b` shadowing bug) and are dropped once,
    // reverting to live defaults. The version gate already discharges that
    // legacy risk, so a current blob restores `trusted` — verbatim, WITHOUT the
    // static known-model prune that would otherwise silently drop a model the
    // user picked from the LIVE catalog.
    key: "modelOverrides",
    read: () => ({
      modelOverrides: useModelSelectionStore.getState().overrides,
      modelOverridesV: MODEL_OVERRIDES_VERSION,
    }),
    restore: (workspace) => {
      if (
        workspace.modelOverridesV === MODEL_OVERRIDES_VERSION &&
        workspace.modelOverrides &&
        typeof workspace.modelOverrides === "object"
      ) {
        useModelSelectionStore.getState().setOverrides(workspace.modelOverrides, { trusted: true });
      }
    },
    subscribe: onChange(useModelSelectionStore, (s) => s.overrides),
  },
  {
    // `setOverrides` normalises on the way in; older blobs keep the defaults.
    key: "keybindingOverrides",
    read: () => ({ keybindingOverrides: useKeybindingsStore.getState().overrides }),
    restore: (workspace) => {
      if (workspace.keybindingOverrides && typeof workspace.keybindingOverrides === "object") {
        useKeybindingsStore.getState().setOverrides(workspace.keybindingOverrides);
      }
    },
    subscribe: onChange(useKeybindingsStore, (s) => s.overrides),
  },
  {
    // `setAll` merges over the seed so a partial blob can't strip a field.
    key: "settings",
    read: () => ({ settings: useSettingsStore.getState().toBundle() }),
    restore: (workspace) => {
      if (workspace.settings && typeof workspace.settings === "object") {
        useSettingsStore.getState().setAll(workspace.settings);
      }
    },
    subscribe: onChange(
      useSettingsStore,
      (s) => s.defaultAgentId,
      (s) => s.region,
      (s) => s.deepResearchBackend,
    ),
  },
  {
    // `setAll` MIGRATES any pre-R9 blob (legacy `tier`, R7/R8 tier ids,
    // exaDirect) into the two-tier vocabulary, then merges over the seed; a
    // legacy hosted/Exa selection confirms the OpenRouter key asynchronously
    // and demotes to tier_a when none is configured.
    key: "searchSettings",
    read: () => ({ searchSettings: useSearchSettingsStore.getState().toBundle() }),
    restore: (workspace) => {
      if (workspace.searchSettings && typeof workspace.searchSettings === "object") {
        useSearchSettingsStore.getState().setAll(workspace.searchSettings);
      }
    },
    subscribe: onChange(
      useSearchSettingsStore,
      (s) => s.researchTier,
      (s) => s.searxngUrl,
      (s) => s.researchModels,
    ),
  },
  {
    // `fromBundle` validates the shape and always restores archived. `null` is
    // a valid "no brief" bundle, so guard on the key's presence, not truthiness.
    key: "brief",
    read: () => ({ brief: useBriefStore.getState().toBundle() }),
    restore: (workspace) => {
      if ("brief" in workspace) {
        useBriefStore.getState().fromBundle((workspace.brief ?? null) as BriefBundle);
      }
    },
    subscribe: onChange(useBriefStore, (s) => s.brief),
  },
  {
    key: "notes",
    read: () => ({ notes: useNotesStore.getState().toBundle() }),
    restore: (workspace) => {
      if ("notes" in workspace) {
        useNotesStore.getState().fromBundle((workspace.notes ?? null) as NotesBundle);
      }
    },
    subscribe: onChange(
      useNotesStore,
      (s) => s.general,
      (s) => s.bySymbol,
      (s) => s.focusSymbol,
    ),
  },
  {
    // `deserializeSavedScreens` drops malformed entries from a garbled blob.
    key: "savedScreens",
    read: () => ({ savedScreens: useScreenerStore.getState().savedScreens }),
    restore: (workspace) => {
      if (Array.isArray(workspace.savedScreens)) {
        useScreenerStore
          .getState()
          .setSavedScreens(deserializeSavedScreens(JSON.stringify(workspace.savedScreens)));
      }
    },
    subscribe: onChange(useScreenerStore, (s) => s.savedScreens),
  },
  {
    // The durable per-space agent-memory archive (S-19).
    key: "researchSpaces",
    read: () => ({ researchSpaces: useResearchSpacesStore.getState().snapshot() }),
    restore: (workspace) => {
      if (workspace.researchSpaces && typeof workspace.researchSpaces === "object") {
        useResearchSpacesStore
          .getState()
          .replaceAll(workspace.researchSpaces as WorkspaceResearchSpaces);
      }
    },
    subscribe: onChange(useResearchSpacesStore, (s) => s.byName),
  },
  {
    // TYPED research-space marker (only on a research space). Restoring it
    // swaps the live chat transcript: archive the space being left, restore
    // the one being entered — keyed by the CANONICAL space name so a renamed
    // workspace file (or the `__autosave__` slot) still resolves its memory.
    key: "researchSymbol",
    read: () => {
      const researchSymbol = useWorkspaceStore.getState().researchSymbol;
      return researchSymbol ? { researchSymbol } : {};
    },
    restore: (workspace) => {
      const prevSymbol = useWorkspaceStore.getState().researchSymbol;
      const nextSymbol = researchSymbolOf(workspace);
      useResearchSpacesStore
        .getState()
        .switchSpace(
          prevSymbol ? { name: researchSpaceName(prevSymbol), symbol: prevSymbol } : null,
          nextSymbol ? { name: researchSpaceName(nextSymbol), symbol: nextSymbol } : null,
        );
      useWorkspaceStore.getState().setResearchSymbol(nextSymbol);
    },
    subscribe: onChange(useWorkspaceStore, (s) => s.researchSymbol),
  },
];

/**
 * Build the serialised workspace body from the live stores — the SINGLE source
 * for both explicit save ({@link serializeWorkspace}) and {@link autosaveLayout}.
 * Throws if the dockview layout has not mounted yet.
 */
function buildWorkspacePayload(name: string): SerializedWorkspace {
  const api = useWorkspaceStore.getState().dockviewApi;
  if (!api) {
    throw new WorkspaceError("The panel layout is not ready yet.");
  }
  // If the active workspace is a research space, fold the LIVE chat transcript
  // into its durable per-space memory BEFORE snapshotting, so the saved blob
  // captures the conversation the user has had in this space (S-19). Keyed by
  // the CANONICAL research-space name, not the file `name` — the autosave slot
  // persists under `__autosave__` but a space's memory must converge on the
  // same key as its explicit save.
  const researchSymbol = useWorkspaceStore.getState().researchSymbol;
  if (researchSymbol) {
    useResearchSpacesStore.getState().saveSpace(researchSpaceName(researchSymbol), researchSymbol);
  }
  const workspace: SerializedWorkspace = { name, layout: api.toJSON(), enabledModules: {} };
  for (const slice of PERSISTED_SLICES) {
    Object.assign(workspace, slice.read());
  }
  return workspace;
}

/**
 * Capture the current workspace from the live stores: the dockview layout plus
 * every {@link PERSISTED_SLICES} slice. Throws if the dockview layout has not
 * mounted yet.
 */
export function serializeWorkspace(name: string): SerializedWorkspace {
  return buildWorkspacePayload(name);
}

/**
 * Apply a loaded workspace back onto the live stores. The non-layout slices
 * are restored FIRST and never depend on the dockview layout applying, so a
 * layout that cannot be restored never costs the user their data
 * (R15-LIFECYCLE-002). Then the dockview layout is applied — unless it
 * references a panel component that is not registered (a removed panel, or a
 * plugin panel that registers async), in which case the layout is skipped and
 * this returns false so the caller can apply the default layout. Throws if the
 * dockview layout has not mounted yet, or if `fromJSON` itself throws (the
 * non-layout slices are already restored by then).
 */
export function deserializeWorkspace(workspace: SerializedWorkspace): boolean {
  const api = useWorkspaceStore.getState().dockviewApi;
  if (!api) {
    throw new WorkspaceError("The panel layout is not ready yet.");
  }
  useWorkspaceStore.getState().setName(workspace.name);
  for (const slice of PERSISTED_SLICES) {
    slice.restore(workspace);
  }
  // An unknown component would throw mid-`fromJSON` (dockview instantiates panel
  // content eagerly) and half-mutate the grid — skip the layout instead.
  if (layoutReferencesUnknownComponent(workspace.layout)) {
    return false;
  }
  api.fromJSON(workspace.layout);
  migrateLegacyLayout(api);
  return true;
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

/**
 * Load a saved workspace from the sidecar and apply it to the live stores. A
 * layout that references an unregistered panel falls back to the default layout;
 * the workspace's data slices are restored either way.
 */
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
  if (!deserializeWorkspace(workspace)) {
    const api = useWorkspaceStore.getState().dockviewApi;
    if (api) {
      api.clear();
      applyDefaultLayout(
        api,
        new Set(
          useModulesStore
            .getState()
            .enabledPanels()
            .map((panel) => panel.id),
        ),
      );
    }
  }
}

/**
 * One-time hygiene over a freshly-restored layout (R7): old saved blobs can
 * carry (a) duplicate chart panels minted before the singleton fix (ids like
 * `chart-<ts>-<rand>` alongside the canonical `chart`) — the "persistent
 * duplicate Chart tab" — and (b) a bare `screener` panel id from the era when
 * the arrange templates drifted from the module's registered `screener-panel`
 * id, which would make every future arrange/open mint a second screener.
 * Removing the ghosts here means the very next autosave persists the clean
 * layout and the migration self-retires.
 */
function migrateLegacyLayout(api: DockviewApi): void {
  for (const panel of [...api.panels]) {
    const component = (panel as { view?: { contentComponent?: string } }).view?.contentComponent;
    const isChartDupe = component === "chart-panel" && panel.id !== "chart";
    const isLegacyScreener =
      panel.id === "screener" && api.getPanel("screener-panel") !== undefined;
    if (isChartDupe || isLegacyScreener) {
      try {
        api.removePanel(panel);
      } catch {
        // A half-restored ghost that won't remove is left in place — never
        // fail the whole restore over hygiene.
      }
    }
  }
}

/**
 * True when the serialized layout references a panel component id that is not
 * currently registered. dockview instantiates panel content eagerly during
 * `fromJSON`, so an unknown component (e.g. a plugin panel whose module
 * registers asynchronously after `handleReady`, or a panel that was removed from
 * the product) throws synchronously and half-mutates the grid. We detect that
 * up-front and skip the layout cleanly.
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
 * The saved data slices (holdings, watchlist, notes, …) are restored even when
 * the saved layout is not, so the next autosave never overwrites them with
 * defaults. Returns true when the saved layout was restored.
 *
 * Autosave is a no-op until this settles (R15-LIFECYCLE-003): every slice the
 * restore writes fires its autosave trigger, and a save mid-restore would
 * persist a half-restored blob.
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
    return await restoreSession(api, enabledPanelIds, isLive);
  } finally {
    // A replaced api's restore is superseded by the live api's own restore,
    // which settles the gate when it finishes.
    if (isLive()) {
      restoreSettled = true;
    }
  }
}

async function restoreSession(
  api: DockviewApi,
  enabledPanelIds: Set<string>,
  isLive: () => boolean,
): Promise<boolean> {
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
      const layoutRestored = deserializeWorkspace(workspace);
      // The reserved slot's name is internal — present the restored cockpit
      // under the neutral "default" name, not "__autosave__".
      useWorkspaceStore.getState().setName("default");
      if (layoutRestored) {
        return true;
      }
      // The saved layout references a component that is not registered — the
      // data slices are already restored; fall through to the default layout.
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

/** Trailing-edge window that coalesces a burst of changes into one autosave. */
const AUTOSAVE_DEBOUNCE_MS = 500;

/** False until the launch restore settles; autosave is a no-op before then. */
let restoreSettled = false;
let autosaveTimer: ReturnType<typeof setTimeout> | null = null;
let autosaveInFlight = false;
let autosaveQueued = false;

/**
 * Schedule a save of the current cockpit to the reserved autosave slot. A
 * no-op until the launch restore settles; debounced (trailing edge) so a burst
 * of changes coalesces into one write, and single-flight so two saves never
 * race each other to the sidecar — a change during a save queues one more.
 * Best-effort: a transient sidecar failure is swallowed (the next change
 * retries) and the active workspace name is left unchanged.
 */
export function autosaveLayout(): void {
  if (!restoreSettled) {
    return;
  }
  if (autosaveTimer !== null) {
    clearTimeout(autosaveTimer);
  }
  autosaveTimer = setTimeout(() => {
    autosaveTimer = null;
    void flushAutosave();
  }, AUTOSAVE_DEBOUNCE_MS);
}

async function flushAutosave(): Promise<void> {
  if (autosaveInFlight) {
    autosaveQueued = true;
    return;
  }
  if (!useWorkspaceStore.getState().dockviewApi) {
    return;
  }
  autosaveInFlight = true;
  try {
    const payload = buildWorkspacePayload(AUTOSAVE_LAYOUT_NAME);
    await fetch(await workspaceUrl(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: AUTOSAVE_LAYOUT_NAME, workspace: payload }),
    });
  } catch {
    // Best-effort autosave; ignore transient failures.
  } finally {
    autosaveInFlight = false;
    if (autosaveQueued) {
      autosaveQueued = false;
      void flushAutosave();
    }
  }
}

/**
 * Wire every {@link PERSISTED_SLICES} trigger to {@link autosaveLayout} (the
 * dockview layout's own trigger is wired by PanelHost). Returns the teardown.
 */
export function wireAutosaveTriggers(): () => void {
  const unsubscribes = PERSISTED_SLICES.map((slice) => slice.subscribe(autosaveLayout));
  return () => unsubscribes.forEach((unsubscribe) => unsubscribe());
}

/** Test helper: back to the pre-restore state (autosave gated, nothing pending). */
export function resetWorkspacePersistenceForTests(): void {
  if (autosaveTimer !== null) {
    clearTimeout(autosaveTimer);
  }
  autosaveTimer = null;
  restoreSettled = false;
  autosaveInFlight = false;
  autosaveQueued = false;
}

/** Prefix every per-stock research space's name carries, so they're recognisable
 *  in the Load Workspace list (e.g. "Research: NVDA"). */
export const RESEARCH_SPACE_PREFIX = "Research: ";

/** The saved-workspace name for a given ticker's research space. */
export function researchSpaceName(symbol: string): string {
  return `${RESEARCH_SPACE_PREFIX}${symbol.trim().toUpperCase()}`;
}

/**
 * The symbol a workspace researches, or `null` when it is not a research space.
 *
 * TYPED-FIELD FIRST (S-19): a blob with the explicit {@link
 * SerializedWorkspace.researchSymbol} field returns that symbol directly — robust
 * against a rename of the workspace. BACK-COMPAT FALL-BACK: an OLD blob that
 * pre-dates the field is still recognised by its `"Research: "` name prefix, and
 * the symbol is recovered from the suffix. A blank suffix is treated as "not a
 * research space" so a literal `"Research: "` can't masquerade as one.
 */
export function researchSymbolOf(
  workspace: Pick<SerializedWorkspace, "name" | "researchSymbol">,
): string | null {
  const typed = workspace.researchSymbol;
  if (typeof typed === "string" && typed.trim()) {
    return typed.trim().toUpperCase();
  }
  if (typeof workspace.name === "string" && workspace.name.startsWith(RESEARCH_SPACE_PREFIX)) {
    const suffix = workspace.name.slice(RESEARCH_SPACE_PREFIX.length).trim();
    return suffix ? suffix.toUpperCase() : null;
  }
  return null;
}

/** True when a workspace is a research space (typed field, prefix fall-back). */
export function isResearchSpace(
  workspace: Pick<SerializedWorkspace, "name" | "researchSymbol">,
): boolean {
  return researchSymbolOf(workspace) !== null;
}

/**
 * Create a per-stock RESEARCH SPACE for `symbol` and persist it as a named
 * workspace ("Research: TICKER"). A research space is a dedicated cockpit that
 * bundles one ticker's research surface — the chart (symbol loaded), the equity
 * overview + the synthesised brief, and a Notes scratchpad scoped to the ticker —
 * saved so the user can return to it from Load Workspace.
 *
 * Builds the layout SYNCHRONOUSLY (so the save captures it), pushes the symbol
 * through the always-consumed chart-command channel, scopes the Notes panel, then
 * saves. Throws (WorkspaceError) on a missing symbol or an unmounted layout.
 */
export async function createResearchSpace(rawSymbol: string): Promise<string> {
  const symbol = rawSymbol.trim().toUpperCase();
  if (!symbol) {
    throw new WorkspaceError("A ticker is required for a research space.");
  }
  const api = useWorkspaceStore.getState().dockviewApi;
  if (!api) {
    throw new WorkspaceError("The panel layout is not ready yet.");
  }
  const name = researchSpaceName(symbol);
  // Archive the transcript of any space we're leaving, then start this new
  // space with a clean transcript (S-19 per-space memory). Marking the store's
  // typed research symbol BEFORE the save makes `buildWorkspacePayload` emit the
  // `researchSymbol` field + initialise this space's memory entry.
  const leaving = (() => {
    const prevSymbol = useWorkspaceStore.getState().researchSymbol;
    return prevSymbol ? { name: researchSpaceName(prevSymbol), symbol: prevSymbol } : null;
  })();
  useResearchSpacesStore.getState().switchSpace(leaving, { name, symbol });
  useWorkspaceStore.getState().setResearchSymbol(symbol);
  // Clean, dedicated research layout (chart + overview + brief + notes).
  applyResearchSpaceLayout(api);
  // Load the symbol into the chart (always-consumed channel — the chart panel,
  // just added, picks it up on mount) and scope the Notes panel to the ticker.
  useChartCommandStore.getState().loadSymbol(symbol);
  useNotesStore.getState().setFocusSymbol(symbol);
  // Persist as a named workspace so it shows up in Load Workspace. `saveWorkspace`
  // serialises the live layout we just built and marks it active.
  await saveWorkspace(name);
  return name;
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
