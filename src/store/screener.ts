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

import { getSidecarBaseUrl, sidecarGet } from "@/lib/sidecar-client";

import type {
  ScreenerCriterion,
  ScreenerRequest,
  ScreenerResult,
  ScreenerUniverse,
  ScreenerUniverseId,
} from "../../types/screener";

export type ScreenerStatus = "idle" | "loading" | "ready" | "error";

interface ScreenerState {
  // --- editable draft -------------------------------------------------
  universe: ScreenerUniverseId;
  customSymbols: string;
  criteria: ScreenerCriterion[];

  // --- last-run cache -------------------------------------------------
  lastResult: ScreenerResult | null;
  status: ScreenerStatus;
  error: string | null;

  // --- universes ------------------------------------------------------
  universeMeta: Record<string, ScreenerUniverse>;
  universeStatus: Record<string, ScreenerStatus>;

  // --- public API -----------------------------------------------------
  setUniverse: (id: ScreenerUniverseId) => void;
  setCustomSymbols: (raw: string) => void;
  setCriteria: (criteria: ScreenerCriterion[]) => void;
  addCriterion: (criterion: ScreenerCriterion) => void;
  removeCriterion: (index: number) => void;
  updateCriterion: (index: number, criterion: ScreenerCriterion) => void;
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
  lastResult: null,
  status: "idle",
  error: null,
  universeMeta: {},
  universeStatus: {},

  setUniverse: (id) => set({ universe: id }),
  setCustomSymbols: (raw) => set({ customSymbols: raw }),
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

  runScreener: async (limit = 200) => {
    const { universe, customSymbols, criteria } = get();
    set({ status: "loading", error: null });
    const req: ScreenerRequest = {
      universe,
      criteria,
      limit,
      ...(universe === "custom" ? { custom_symbols: parseCustomSymbols(customSymbols) } : {}),
    };
    try {
      const result = await postJson<ScreenerRequest, ScreenerResult>("/screener/run", req);
      set({ lastResult: result, status: "ready", error: null });
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
    }
  },

  __resetForTests: () =>
    set({
      universe: "sp500",
      customSymbols: "",
      criteria: DEFAULT_CRITERIA,
      lastResult: null,
      status: "idle",
      error: null,
      universeMeta: {},
      universeStatus: {},
    }),
}));
