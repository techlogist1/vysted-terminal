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

import { runScreenerFormula } from "@/lib/screener-formula-runner";
import { getSidecarBaseUrl, sidecarGet } from "@/lib/sidecar-client";

import type {
  CriterionGroup,
  ScreenerCriterion,
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

// In-flight universe fetches, deduped by id. Two concurrent loadUniverse(id)
// calls both missed the cache and fired duplicate requests (Phase 9.5); a
// module-level map (the store is a singleton) coalesces them without changing
// the state shape / test mocks.
const _inFlightUniverses = new Map<string, Promise<ScreenerUniverse | null>>();

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
  /** Custom client-side post-filter formula (mathjs). Applied to the
   * server-returned matched rows in a Web Worker after a run. Empty = no-op. */
  formula: string;

  // --- last-run cache -------------------------------------------------
  lastResult: ScreenerResult | null;
  /** Server result count BEFORE the custom formula post-filter — surfaced so the
   * UI can show "N of M matched (formula)". Null when no formula was applied. */
  preFormulaCount: number | null;
  /** Inline parse/eval error from the last formula run (no raw stack). */
  formulaError: string | null;
  status: ScreenerStatus;
  error: string | null;

  // --- universes ------------------------------------------------------
  universeMeta: Record<string, ScreenerUniverse>;
  universeStatus: Record<string, ScreenerStatus>;

  // --- public API -----------------------------------------------------
  setUniverse: (id: ScreenerUniverseId) => void;
  setCustomSymbols: (raw: string) => void;
  setCombinator: (combinator: ScreenerCombinator) => void;
  setCriteria: (criteria: ScreenerCriterion[]) => void;
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
   * the user keeps their custom formula). */
  applyFilters: (input: {
    criteria: ScreenerCriterion[];
    group?: CriterionGroup | null;
    universe?: ScreenerUniverseId;
  }) => void;
  runScreener: (limit?: number) => Promise<ScreenerResult | null>;
  loadUniverse: (id: ScreenerUniverseId) => Promise<ScreenerUniverse | null>;
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
  preFormulaCount: null,
  formulaError: null,
  status: "idle",
  error: null,
  universeMeta: {},
  universeStatus: {},

  setUniverse: (id) => set({ universe: id }),
  setCustomSymbols: (raw) => set({ customSymbols: raw }),
  setCombinator: (combinator) => set({ combinator }),
  setCriteria: (criteria) => set({ criteria }),
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
  applyFilters: ({ criteria, group, universe }) =>
    set((state) => ({
      criteria,
      group: group ?? null,
      advanced: hasNestedGroup(group ?? null),
      // A flat group from the agent collapses to the simple combinator so the
      // simple builder reflects it; a nested one drives advanced mode.
      combinator: group && group.combinator === "or" && !hasNestedGroup(group) ? "or" : "and",
      universe: universe ?? state.universe,
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
    set({ status: "loading", error: null, formulaError: null, preFormulaCount: null });
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
      ...(universe === "custom" ? { custom_symbols: parseCustomSymbols(customSymbols) } : {}),
    };
    try {
      const result = await postJson<ScreenerRequest, ScreenerResult>("/screener/run", req);
      // CLIENT-SIDE custom-formula post-filter (FR-122): the server returns the
      // matched set; the mathjs Web Worker drops rows the formula rejects. A
      // blank formula is a no-op. Errors surface inline; no rows silently vanish.
      if (formula.trim()) {
        const filtered = await runScreenerFormula(formula, result.rows);
        const postResult: ScreenerResult = {
          ...result,
          rows: filtered.rows,
          result_count: filtered.rows.length,
        };
        set({
          lastResult: postResult,
          preFormulaCount: result.rows.length,
          formulaError: filtered.error ?? null,
          status: "ready",
          error: null,
        });
        return postResult;
      }
      set({
        lastResult: result,
        preFormulaCount: null,
        formulaError: null,
        status: "ready",
        error: null,
      });
      return result;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "screener run failed";
      set({ status: "error", error: message });
      return null;
    }
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
      preFormulaCount: null,
      formulaError: null,
      status: "idle",
      error: null,
      universeMeta: {},
      universeStatus: {},
    }),
}));
