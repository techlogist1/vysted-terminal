/**
 * Screener store — Phase 6 (Teammate Sc, lead-completed in v0.6.1).
 *
 * Lightweight Zustand store holding:
 *   - The last screener result (rows + evaluated/result counts + duration).
 *   - The current criteria draft the builder edits before "Run".
 *   - The selected universe id + custom_symbols (for ``"custom"``).
 *   - A loading/error channel.
 *
 * Network paths are thin — every call POSTs through ``sidecar-client``'s
 * cached base URL. The panel reads off the slice directly; tests mock the
 * sidecar via the standard fixture pattern (mirror ``src/store/quant.ts``).
 */

import { create } from "zustand";

import { compileScreenerExpr } from "@/lib/screener-expr";
import { getSidecarBaseUrl, sidecarGet } from "@/lib/sidecar-client";

import type {
  CriterionGroup,
  ScreenerCriterion,
  ScreenerProgressFrame,
  ScreenerRequest,
  ScreenerResult,
  ScreenerUniverse,
  ScreenerUniverseId,
} from "../../types/screener";

/** Strip empty sub-groups so a serialized tree never carries dead nodes that
 * the server would treat as "matches everything". Returns null when the whole
 * tree collapses to nothing (→ fall back to the flat criteria path). */
function pruneGroup(group: CriterionGroup): CriterionGroup | null {
  const criteria = group.criteria
    .map((c) => ("combinator" in c ? pruneGroup(c) : c))
    .filter((c): c is ScreenerCriterion | CriterionGroup => c !== null);
  if (criteria.length === 0) {
    return null;
  }
  return { combinator: group.combinator, criteria };
}

/** Does the editable tree carry real NESTING (a sub-group)? A flat group of
 * leaves is expressible via the simple criteria+combinator path, so we only
 * switch to the `group` wire field when nesting is actually present. */
function hasNestedGroup(group: CriterionGroup | null): boolean {
  if (!group) {
    return false;
  }
  return group.criteria.some((c) => "combinator" in c);
}

export type ScreenerStatus = "idle" | "loading" | "ready" | "error";

/** Top-level combinator the builder applies across its flat criteria list:
 * "and" = match ALL, "or" = match ANY. Maps to the `group` boolean tree. */
export type ScreenerCombinator = "and" | "or";

/** One saved screen — persisted by the store, wired to workspace by the lead. */
export interface SavedScreen {
  name: string;
  universe: ScreenerUniverseId;
  criteria: ScreenerCriterion[];
  group?: CriterionGroup | null;
  formula?: string;
  combinator: ScreenerCombinator;
}

// Serialization helpers — EXPORTED so the lead can wire them into workspace.ts.
export function serializeSavedScreens(screens: SavedScreen[]): string {
  return JSON.stringify(screens);
}

export function deserializeSavedScreens(raw: string | null | undefined): SavedScreen[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (s): s is SavedScreen =>
        s !== null &&
        typeof s === "object" &&
        typeof (s as Record<string, unknown>).name === "string" &&
        typeof (s as Record<string, unknown>).universe === "string",
    );
  } catch {
    return [];
  }
}

// In-flight universe fetches, deduped by id. Two concurrent loadUniverse(id)
// calls both missed the cache and fired duplicate requests (Phase 9.5); a
// module-level map (the store is a singleton) coalesces them without changing
// the state shape / test mocks.
const _inFlightUniverses = new Map<string, Promise<ScreenerUniverse | null>>();

// AbortController for the active streaming run. Module-level (singleton store)
// so cancelRun() can abort without threading it through state.
let _runAbortController: AbortController | null = null;

interface ScreenerState {
  // --- editable draft -------------------------------------------------
  universe: ScreenerUniverseId;
  customSymbols: string;
  criteria: ScreenerCriterion[];
  /** How the flat criteria combine: "and" = match ALL (default), "or" = ANY. */
  combinator: ScreenerCombinator;
  /** Advanced nested AND/OR tree edited by the recursive group editor. When it
   * carries real nesting it SUPERSEDES the flat criteria/combinator on run
   * (the server already evaluates the tree). `null` → simple flat mode. */
  group: CriterionGroup | null;
  /** Whether the builder is in advanced (nested group) mode vs simple flat. */
  advanced: boolean;
  /** Custom formula (the shared restricted grammar, `src/lib/screener-expr.ts`
   * ⇄ `sidecar/services/screener_formula.py`). Sent on the request and
   * evaluated SERVER-SIDE per universe member, AND-combined with the criteria.
   * Empty = no-op. Rows missing a referenced field land in the skip ledger. */
  formula: string;

  // --- last-run cache -------------------------------------------------
  lastResult: ScreenerResult | null;
  status: ScreenerStatus;
  error: string | null;
  /** R10 (D40): live streaming progress from /screener/run/stream. Null when idle. */
  progress: Pick<ScreenerProgressFrame, "phase" | "done" | "total" | "detail"> | null;

  // --- universes ------------------------------------------------------
  universeMeta: Record<string, ScreenerUniverse>;
  universeStatus: Record<string, ScreenerStatus>;

  // --- saved screens --------------------------------------------------
  savedScreens: SavedScreen[];

  // --- public API -----------------------------------------------------
  setUniverse: (id: ScreenerUniverseId) => void;
  setCustomSymbols: (raw: string) => void;
  setCombinator: (combinator: ScreenerCombinator) => void;
  setCriteria: (criteria: ScreenerCriterion[]) => void;
  /** Restore the default starter criteria and clear the formula + nested group
   *  (the "Reset filters" affordance on the no-results empty state). */
  resetCriteria: () => void;
  addCriterion: (criterion: ScreenerCriterion) => void;
  removeCriterion: (index: number) => void;
  updateCriterion: (index: number, criterion: ScreenerCriterion) => void;
  /** Replace the advanced nested tree (the recursive group editor's model). */
  setGroup: (group: CriterionGroup | null) => void;
  setAdvanced: (advanced: boolean) => void;
  setFormula: (formula: string) => void;
  /** Write a full filter set at once (the agent's `write_screener_filters`
   * host action lands here). Sets criteria, the optional nested group, the
   * optional universe/limit, and clears the formula (the agent owns criteria;
   * the user keeps their custom formula). `formula` overrides the formula field
   * when provided. When `run` is true, the caller MUST follow up with runScreener()
   * (the host-action path is responsible for chaining). */
  applyFilters: (input: {
    criteria: ScreenerCriterion[];
    group?: CriterionGroup | null;
    universe?: ScreenerUniverseId;
    formula?: string;
    run?: boolean;
  }) => void;
  runScreener: (limit?: number) => Promise<ScreenerResult | null>;
  /** Cancel the in-flight streaming run (if any). Disconnecting aborts the
   * server-side engine per the R10 SSE contract. */
  cancelRun: () => void;
  loadUniverse: (id: ScreenerUniverseId) => Promise<ScreenerUniverse | null>;
  /** Save the current filter set under a name. Replaces any existing screen with
   * the same name. */
  saveScreen: (name: string) => void;
  /** Delete a saved screen by name. */
  deleteScreen: (name: string) => void;
  /** Load a saved screen into the active draft (restores universe, criteria,
   * group, formula, combinator). Does NOT auto-run. */
  loadScreen: (name: string) => void;
  __resetForTests: () => void;
}

/** Default starter criteria — populated state for first-run demo + tests. */
const DEFAULT_CRITERIA: ScreenerCriterion[] = [
  { field: "pe_ratio", operator: "lt", value: 20 },
  { field: "market_cap", operator: "gt", value: 100_000_000_000 },
  { field: "sector", operator: "eq", value: "Technology" },
];

async function postJson<TReq, TRes>(path: string, body: TReq): Promise<TRes> {
  const base = await getSidecarBaseUrl();
  const response = await fetch(new URL(path, base).toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const parsed = (await response.json()) as { detail?: string };
      if (parsed.detail) {
        detail = parsed.detail;
      }
    } catch {
      // Body was not JSON — keep status text.
    }
    throw new Error(`POST ${path} failed (${response.status}): ${detail}`);
  }
  return (await response.json()) as TRes;
}

function parseCustomSymbols(raw: string): string[] {
  return raw
    .split(/[,\s]+/)
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean);
}

export const useScreenerStore = create<ScreenerState>((set, get) => ({
  universe: "sp500",
  customSymbols: "",
  criteria: DEFAULT_CRITERIA,
  combinator: "and",
  group: null,
  advanced: false,
  formula: "",
  lastResult: null,
  status: "idle",
  error: null,
  progress: null,
  universeMeta: {},
  universeStatus: {},
  savedScreens: [],

  setUniverse: (id) => set({ universe: id }),
  setCustomSymbols: (raw) => set({ customSymbols: raw }),
  setCombinator: (combinator) => set({ combinator }),
  setCriteria: (criteria) => set({ criteria }),
  resetCriteria: () =>
    set({ criteria: DEFAULT_CRITERIA, group: null, advanced: false, formula: "" }),
  addCriterion: (criterion) => set((state) => ({ criteria: [...state.criteria, criterion] })),
  removeCriterion: (index) =>
    set((state) => ({
      criteria: state.criteria.filter((_, i) => i !== index),
    })),
  updateCriterion: (index, criterion) =>
    set((state) => {
      const next = [...state.criteria];
      next[index] = criterion;
      return { criteria: next };
    }),
  setGroup: (group) => set({ group }),
  setAdvanced: (advanced) => set({ advanced }),
  setFormula: (formula) => set({ formula }),
  applyFilters: ({ criteria, group, universe, formula }) =>
    set((state) => ({
      criteria,
      group: group ?? null,
      advanced: hasNestedGroup(group ?? null),
      // A flat group from the agent collapses to the simple combinator so the
      // simple builder reflects it; a nested one drives advanced mode.
      combinator: group && group.combinator === "or" && !hasNestedGroup(group) ? "or" : "and",
      universe: universe ?? state.universe,
      // `formula` overrides when provided; omitting it leaves the user's own formula.
      ...(formula !== undefined ? { formula } : {}),
    })),

  runScreener: async (limit = 200) => {
    const {
      universe,
      customSymbols,
      criteria,
      combinator,
      group: editTree,
      advanced,
      formula,
    } = get();
    // Pre-flight the formula against the SAME grammar the server enforces —
    // an unparseable formula is an honest inline failure (with the caret
    // column), never a wasted round-trip to a 422.
    const trimmedFormula = formula.trim();
    if (trimmedFormula) {
      const compiled = compileScreenerExpr(trimmedFormula);
      if (!compiled.ok) {
        set({
          status: "error",
          error: `Formula: ${compiled.error} (col ${compiled.position + 1})`,
        });
        return null;
      }
    }
    // Abort any in-flight run before starting a new one.
    _runAbortController?.abort();
    const controller = new AbortController();
    _runAbortController = controller;
    set({ status: "loading", error: null, progress: null });
    // Three shapes for the boolean tree, in precedence:
    //   1. ADVANCED nested tree (the recursive group editor) — pruned, supersedes
    //      everything when it carries real nesting (server evaluates it).
    //   2. flat "or" — a flat OR group over the simple criteria list.
    //   3. flat "and" (default) — no `group`, the back-compat flat criteria path.
    // `criteria` stays populated either way so older readers + the
    // matched-criteria index column still resolve.
    let group: CriterionGroup | undefined;
    const pruned = advanced && editTree ? pruneGroup(editTree) : null;
    if (pruned && hasNestedGroup(pruned)) {
      group = pruned;
    } else if (combinator === "or") {
      group = { combinator: "or", criteria: [...criteria] };
    }
    const req: ScreenerRequest = {
      universe,
      criteria,
      limit,
      ...(group ? { group } : {}),
      // The formula rides the request and is evaluated SERVER-SIDE per
      // universe member (R7 Pillar 3) — rows missing a referenced field come
      // back itemized in the skip ledger, never silently dropped.
      ...(trimmedFormula ? { formula: trimmedFormula } : {}),
      ...(universe === "custom" ? { custom_symbols: parseCustomSymbols(customSymbols) } : {}),
    };
    // --- Attempt streaming via POST /screener/run/stream (R10 D40) ----------
    // Falls back to the unary endpoint on 404 (older sidecar builds). Disconnect
    // (cancel) aborts the server-side engine per the SSE contract.
    const base = await getSidecarBaseUrl();
    const streamUrl = new URL("/screener/run/stream", base).toString();
    let streamResponse: Response;
    try {
      streamResponse = await fetch(streamUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
        signal: controller.signal,
      });
    } catch {
      if (controller.signal.aborted) {
        set({ status: "idle", progress: null });
        _runAbortController = null;
        return null;
      }
      // Network error before we even got a response — fall through to unary.
      streamResponse = new Response(null, { status: 503 });
    }
    if (streamResponse.status === 404) {
      // Older sidecar: fall back to unary /screener/run.
      try {
        const result = await postJson<ScreenerRequest, ScreenerResult>("/screener/run", req);
        set({ lastResult: result, status: "ready", error: null, progress: null });
        _runAbortController = null;
        return result;
      } catch (err: unknown) {
        if (controller.signal.aborted) {
          set({ status: "idle", progress: null });
        } else {
          const message = err instanceof Error ? err.message : "screener run failed";
          set({ status: "error", error: message, progress: null });
        }
        _runAbortController = null;
        return null;
      }
    }
    if (!streamResponse.ok) {
      let detail = streamResponse.statusText;
      try {
        const parsed = (await streamResponse.json()) as { detail?: string };
        if (parsed.detail) detail = parsed.detail;
      } catch {
        // Not JSON — keep status text.
      }
      set({
        status: "error",
        error: `POST /screener/run/stream failed (${streamResponse.status}): ${detail}`,
        progress: null,
      });
      _runAbortController = null;
      return null;
    }
    // Consume the stream: newline-delimited JSON frames.
    //   {"event":"progress","phase":"sweep","done":850,"total":2100,"detail":"sweeping quotes 850/2,100"}
    //   {"event":"result", ...ScreenerResult fields...}
    const body = streamResponse.body;
    if (!body) {
      set({ status: "error", error: "Stream body was empty", progress: null });
      _runAbortController = null;
      return null;
    }
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalResult: ScreenerResult | null = null;
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        if (controller.signal.aborted) break;
        buffer += decoder.decode(value, { stream: true });
        // Process all complete lines in the buffer.
        const lines = buffer.split("\n");
        // The last element may be an incomplete line — keep it in the buffer.
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          let frame: Record<string, unknown>;
          try {
            frame = JSON.parse(trimmed) as Record<string, unknown>;
          } catch {
            // Partial or malformed frame — skip.
            continue;
          }
          if (frame.event === "progress") {
            set({
              progress: {
                phase: String(frame.phase ?? ""),
                done: Number(frame.done ?? 0),
                total: Number(frame.total ?? 0),
                detail: String(frame.detail ?? ""),
              },
            });
          } else if (frame.event === "result") {
            // The result frame carries the full ScreenerResult fields inline.
            // Strip the envelope key so the shape matches ScreenerResult exactly.
            const { event: _e, ...resultFields } = frame;
            finalResult = resultFields as unknown as ScreenerResult;
          }
        }
      }
    } catch (readErr) {
      if (!controller.signal.aborted) {
        const message = readErr instanceof Error ? readErr.message : "stream read failed";
        set({ status: "error", error: message, progress: null });
        _runAbortController = null;
        return null;
      }
    } finally {
      reader.releaseLock();
    }
    if (controller.signal.aborted) {
      set({ status: "idle", progress: null });
      _runAbortController = null;
      return null;
    }
    if (!finalResult) {
      set({ status: "error", error: "Stream ended without a result frame", progress: null });
      _runAbortController = null;
      return null;
    }
    set({ lastResult: finalResult, status: "ready", error: null, progress: null });
    _runAbortController = null;
    return finalResult;
  },

  cancelRun: () => {
    _runAbortController?.abort();
    _runAbortController = null;
    set({ status: "idle", progress: null, error: null });
  },

  loadUniverse: async (id) => {
    if (id === "custom") {
      return null;
    }
    const cached = get().universeMeta[id];
    if (cached) {
      return cached;
    }
    // Coalesce concurrent loads of the same id onto one request (Phase 9.5).
    const existing = _inFlightUniverses.get(id);
    if (existing) {
      return existing;
    }
    const request = (async (): Promise<ScreenerUniverse | null> => {
      set((state) => ({
        universeStatus: { ...state.universeStatus, [id]: "loading" },
      }));
      try {
        const payload = await sidecarGet<ScreenerUniverse>("/screener/universe", {
          id,
        });
        set((state) => ({
          universeMeta: { ...state.universeMeta, [id]: payload },
          universeStatus: { ...state.universeStatus, [id]: "ready" },
        }));
        return payload;
      } catch {
        set((state) => ({
          universeStatus: { ...state.universeStatus, [id]: "error" },
        }));
        return null;
      } finally {
        _inFlightUniverses.delete(id);
      }
    })();
    _inFlightUniverses.set(id, request);
    return request;
  },

  saveScreen: (name) => {
    const { universe, criteria, group, formula, combinator } = get();
    const screen: SavedScreen = {
      name,
      universe,
      criteria,
      group: group ?? null,
      formula: formula || undefined,
      combinator,
    };
    set((state) => ({
      savedScreens: [
        // Replace any existing screen with the same name.
        ...state.savedScreens.filter((s) => s.name !== name),
        screen,
      ],
    }));
  },

  deleteScreen: (name) => {
    set((state) => ({
      savedScreens: state.savedScreens.filter((s) => s.name !== name),
    }));
  },

  loadScreen: (name) => {
    const screen = get().savedScreens.find((s) => s.name === name);
    if (!screen) return;
    set({
      universe: screen.universe,
      criteria: screen.criteria,
      group: screen.group ?? null,
      formula: screen.formula ?? "",
      combinator: screen.combinator,
      advanced: hasNestedGroup(screen.group ?? null),
    });
  },

  __resetForTests: () =>
    set({
      universe: "sp500",
      customSymbols: "",
      criteria: DEFAULT_CRITERIA,
      combinator: "and",
      group: null,
      advanced: false,
      formula: "",
      lastResult: null,
      status: "idle",
      error: null,
      progress: null,
      universeMeta: {},
      universeStatus: {},
      savedScreens: [],
    }),
}));
