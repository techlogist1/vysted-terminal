/**
 * SEC EDGAR filings store — Zustand state for the SecFilingsPanel.
 *
 * Phase 6 / v0.6.0 Teammate F. Mirrors the existing data-fetch store
 * pattern (see `src/store/backtest.ts`) — per-identifier caching plus a
 * single active selection driven by the panel's symbol field.
 *
 * Cached state:
 *
 *   - `filingsByIdentifier[identifier]` — last loaded filings list
 *     response for one CIK/symbol + a form-type filter scoped key.
 *   - `filingDetailByAccession[accession]` — full `FilingDetail` once
 *     the user has opened a filing.
 *   - `insiderByIdentifier[identifier]` — last loaded insider response
 *     for one issuer + a form scope.
 *
 * The frozen empty references at module scope are the v0.5.0 selector
 * pattern (precedent: `src/store/agents.ts`). Selectors that return a
 * sub-collection MUST return a stable identity on miss so React's
 * `useSyncExternalStore` doesn't loop on a referential-equality check.
 */

import { create } from "zustand";

import { getSidecarBaseUrl, sidecarGet } from "@/lib/sidecar-client";

import type {
  FilingDetail,
  FilingFormType,
  FilingsListResponse,
  InsiderTransactionsResponse,
} from "../../types/sec";

// ---------------------------------------------------------------------------
// Wire shapes — mirror the FastAPI router schemas
// ---------------------------------------------------------------------------

interface SearchResultRow {
  cik: string;
  name: string;
  ticker: string | null;
}

interface SearchResponse {
  results: SearchResultRow[];
}

// ---------------------------------------------------------------------------
// Frozen empty references — stable identities for the selectors
// ---------------------------------------------------------------------------

const EMPTY_FILINGS: Readonly<FilingsListResponse> = Object.freeze({
  cik: "",
  company_name: "",
  symbol: null,
  filings: [],
});

const EMPTY_INSIDER: Readonly<InsiderTransactionsResponse> = Object.freeze({
  cik: "",
  issuer_name: "",
  transactions: [],
});

const EMPTY_SEARCH: ReadonlyArray<SearchResultRow> = Object.freeze([]);

// ---------------------------------------------------------------------------
// State types
// ---------------------------------------------------------------------------

export type SecLoadStatus = "idle" | "loading" | "ready" | "error";

interface SecState {
  /** Most recently rendered identifier (panel-level "active symbol"). */
  activeIdentifier: string | null;
  /** Map identifier+form -> filings response. */
  filingsByIdentifier: Record<string, FilingsListResponse>;
  filingsStatus: SecLoadStatus;
  filingsError: string | null;

  /** Map accession -> full filing detail. */
  filingDetailByAccession: Record<string, FilingDetail>;
  filingDetailStatus: SecLoadStatus;
  filingDetailError: string | null;
  /** Accession currently displayed in the FilingViewer. */
  activeAccession: string | null;

  /** Map identifier+form -> insider response. */
  insiderByIdentifier: Record<string, InsiderTransactionsResponse>;
  insiderStatus: SecLoadStatus;
  insiderError: string | null;

  /** Recent company-search results. */
  searchResults: ReadonlyArray<SearchResultRow>;
  searchStatus: SecLoadStatus;

  // Actions
  setActiveIdentifier: (identifier: string | null) => void;
  loadFilings: (identifier: string, formType?: FilingFormType) => Promise<void>;
  loadFilingDetail: (accession: string, identifier: string) => Promise<void>;
  setActiveAccession: (accession: string | null) => void;
  loadInsider: (identifier: string, form?: "3" | "4" | "5") => Promise<void>;
  searchCompanies: (query: string) => Promise<void>;
  clearSearch: () => void;
  /** Test-only — hard reset. */
  __resetForTests: () => void;
}

// ---------------------------------------------------------------------------
// Cache key helpers
// ---------------------------------------------------------------------------

function filingsKey(identifier: string, formType: FilingFormType | undefined): string {
  return `${identifier.toUpperCase()}::${formType ?? "all"}`;
}

function insiderKey(identifier: string, form: "3" | "4" | "5" | undefined): string {
  return `${identifier.toUpperCase()}::${form ?? "all"}`;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useSecStore = create<SecState>((set) => ({
  activeIdentifier: null,
  filingsByIdentifier: {},
  filingsStatus: "idle",
  filingsError: null,

  filingDetailByAccession: {},
  filingDetailStatus: "idle",
  filingDetailError: null,
  activeAccession: null,

  insiderByIdentifier: {},
  insiderStatus: "idle",
  insiderError: null,

  searchResults: EMPTY_SEARCH,
  searchStatus: "idle",

  setActiveIdentifier: (identifier) => {
    set({ activeIdentifier: identifier });
  },

  loadFilings: async (identifier, formType) => {
    if (!identifier) return;
    set({ filingsStatus: "loading", filingsError: null });
    try {
      const params: Record<string, string | number | undefined> = {
        limit: 40,
      };
      // Heuristic: identifier all-digit => CIK, otherwise => symbol.
      if (/^\d+$/.test(identifier)) {
        params.cik = identifier;
      } else {
        params.symbol = identifier.toUpperCase();
      }
      if (formType) {
        params.form_type = formType;
      }
      const response = await sidecarGet<FilingsListResponse>("/sec/filings", params);
      const key = filingsKey(identifier, formType);
      set((state) => ({
        filingsByIdentifier: { ...state.filingsByIdentifier, [key]: response },
        filingsStatus: "ready",
        filingsError: null,
        activeIdentifier: identifier,
      }));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "filings fetch failed";
      set({ filingsStatus: "error", filingsError: message });
    }
  },

  loadFilingDetail: async (accession, identifier) => {
    if (!accession) return;
    set({ filingDetailStatus: "loading", filingDetailError: null });
    try {
      const detail = await sidecarGet<FilingDetail>(
        `/sec/filings/${encodeURIComponent(accession)}`,
        { identifier },
      );
      set((state) => ({
        filingDetailByAccession: {
          ...state.filingDetailByAccession,
          [accession]: detail,
        },
        filingDetailStatus: "ready",
        filingDetailError: null,
        activeAccession: accession,
      }));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "filing-detail fetch failed";
      set({ filingDetailStatus: "error", filingDetailError: message });
    }
  },

  setActiveAccession: (accession) => {
    set({ activeAccession: accession });
  },

  loadInsider: async (identifier, form) => {
    if (!identifier) return;
    set({ insiderStatus: "loading", insiderError: null });
    try {
      const params: Record<string, string | number | undefined> = { limit: 50 };
      if (form) {
        params.form = form;
      }
      const response = await sidecarGet<InsiderTransactionsResponse>(
        `/sec/insider/${encodeURIComponent(identifier)}`,
        params,
      );
      const key = insiderKey(identifier, form);
      set((state) => ({
        insiderByIdentifier: { ...state.insiderByIdentifier, [key]: response },
        insiderStatus: "ready",
        insiderError: null,
      }));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "insider fetch failed";
      set({ insiderStatus: "error", insiderError: message });
    }
  },

  searchCompanies: async (query) => {
    const trimmed = query.trim();
    if (!trimmed) {
      set({ searchResults: EMPTY_SEARCH, searchStatus: "idle" });
      return;
    }
    set({ searchStatus: "loading" });
    try {
      const response = await sidecarGet<SearchResponse>("/sec/filings/search", {
        q: trimmed,
        limit: 10,
      });
      set({ searchResults: response.results, searchStatus: "ready" });
    } catch {
      set({ searchResults: EMPTY_SEARCH, searchStatus: "error" });
    }
  },

  clearSearch: () => {
    set({ searchResults: EMPTY_SEARCH, searchStatus: "idle" });
  },

  __resetForTests: () => {
    set({
      activeIdentifier: null,
      filingsByIdentifier: {},
      filingsStatus: "idle",
      filingsError: null,
      filingDetailByAccession: {},
      filingDetailStatus: "idle",
      filingDetailError: null,
      activeAccession: null,
      insiderByIdentifier: {},
      insiderStatus: "idle",
      insiderError: null,
      searchResults: EMPTY_SEARCH,
      searchStatus: "idle",
    });
  },
}));

// ---------------------------------------------------------------------------
// Stable-identity selectors
// ---------------------------------------------------------------------------

/** Select the filings response for an identifier+form, or the frozen empty. */
export function selectFilings(
  identifier: string | null,
  formType: FilingFormType | undefined,
): Readonly<FilingsListResponse> {
  if (!identifier) return EMPTY_FILINGS;
  const key = filingsKey(identifier, formType);
  return useSecStore.getState().filingsByIdentifier[key] ?? EMPTY_FILINGS;
}

/** Select the FilingDetail for an accession, or `null` on miss. */
export function selectFilingDetail(accession: string | null): FilingDetail | null {
  if (!accession) return null;
  return useSecStore.getState().filingDetailByAccession[accession] ?? null;
}

/** Select the insider response for an identifier+form, or the frozen empty. */
export function selectInsider(
  identifier: string | null,
  form: "3" | "4" | "5" | undefined,
): Readonly<InsiderTransactionsResponse> {
  if (!identifier) return EMPTY_INSIDER;
  const key = insiderKey(identifier, form);
  return useSecStore.getState().insiderByIdentifier[key] ?? EMPTY_INSIDER;
}

/**
 * Open the SEC EDGAR canonical URL for a filing in the user's default browser
 * via the Tauri shell.
 */
export async function openEdgarUrl(url: string): Promise<void> {
  // Lazy import — vitest-side mocks can stub it. In a non-Tauri context
  // (e.g. plain `pnpm dev`), fall back to window.open.
  try {
    const mod = await import("@tauri-apps/plugin-shell");
    await mod.open(url);
  } catch {
    if (typeof window !== "undefined") {
      window.open(url, "_blank", "noopener,noreferrer");
    }
  }
}

/**
 * Re-export the base URL helper for tests that want to assert the URLs
 * the store hit (sidecarGet uses it internally).
 */
export const _internal_getSidecarBaseUrl = getSidecarBaseUrl;
