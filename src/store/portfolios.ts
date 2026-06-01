"use client";

import { create } from "zustand";

/**
 * Multi-portfolio store.
 *
 * The user can keep several NAMED portfolios and switch between them, manually
 * tracking holdings (symbol / quantity / cost basis / asset class) — useful when
 * a broker (e.g. HDFC) has no API. There is NO broker auto-sync: every holding
 * is hand-entered. The default is a SINGLE EMPTY portfolio (never fabricated
 * demo data) so a fresh install reads as a clean empty state.
 *
 * Holdings live here (frontend) and persist in the workspace blob
 * (`src/lib/workspace.ts`, the same seam the watchlist uses), NOT the sidecar
 * SQLite — so they survive a relaunch and need no network round-trip. P&L is
 * computed by joining each holding to a live quote in the panel.
 */

export type AssetClass = "equity" | "crypto";

/** A single manually tracked holding. */
export interface Holding {
  id: string;
  symbol: string;
  quantity: number;
  costBasis: number;
  assetClass: AssetClass;
  note?: string;
}

/** A named bag of holdings. */
export interface Portfolio {
  id: string;
  name: string;
  holdings: Holding[];
}

/** The fields the add/edit form supplies (the store assigns the id). */
export interface HoldingInput {
  symbol: string;
  quantity: number;
  costBasis: number;
  assetClass: AssetClass;
  note?: string;
}

const DEFAULT_PORTFOLIO_NAME = "Portfolio";
/** Stable id for the seed portfolio so a fresh blob restores predictably. */
const DEFAULT_PORTFOLIO_ID = "default";

/** Crypto-strong id where available, with a non-secure-context fallback. */
function genId(prefix: string): string {
  try {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
      return `${prefix}-${crypto.randomUUID()}`;
    }
  } catch {
    /* fall through to the non-crypto id */
  }
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}-${Date.now().toString(36)}`;
}

function makeEmptyPortfolio(name: string = DEFAULT_PORTFOLIO_NAME, id?: string): Portfolio {
  return { id: id ?? genId("pf"), name: name.trim() || DEFAULT_PORTFOLIO_NAME, holdings: [] };
}

/** Coerce an arbitrary (possibly corrupt-blob) holding to a valid one, or drop it. */
function normalizeHolding(raw: unknown): Holding | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const h = raw as Record<string, unknown>;
  const symbol = typeof h.symbol === "string" ? h.symbol.trim().toUpperCase() : "";
  if (symbol === "") {
    return null;
  }
  const quantity = Number(h.quantity);
  const costBasis = Number(h.costBasis);
  const note = typeof h.note === "string" && h.note.trim() !== "" ? h.note.trim() : undefined;
  return {
    id: typeof h.id === "string" && h.id !== "" ? h.id : genId("h"),
    symbol,
    quantity: Number.isFinite(quantity) ? quantity : 0,
    costBasis: Number.isFinite(costBasis) ? costBasis : 0,
    assetClass: h.assetClass === "crypto" ? "crypto" : "equity",
    note,
  };
}

interface PortfoliosState {
  portfolios: Portfolio[];
  activeId: string;
  /** Create a new empty portfolio, make it active, and return its id. */
  createPortfolio: (name: string) => string;
  /** Rename a portfolio (empty name is ignored). */
  renamePortfolio: (id: string, name: string) => void;
  /** Delete a portfolio; never drops below one (a fresh empty one replaces the last). */
  deletePortfolio: (id: string) => void;
  /** Switch the active portfolio. */
  setActive: (id: string) => void;
  /** Append a holding to a portfolio. */
  addHolding: (portfolioId: string, input: HoldingInput) => void;
  /** Patch an existing holding. */
  updateHolding: (portfolioId: string, holdingId: string, input: HoldingInput) => void;
  /** Remove a holding. */
  removeHolding: (portfolioId: string, holdingId: string) => void;
  /** Replace the whole set — used to restore a persisted blob (guards corruption). */
  setAll: (portfolios: Portfolio[], activeId?: string) => void;
}

export const usePortfoliosStore = create<PortfoliosState>((set) => ({
  portfolios: [makeEmptyPortfolio(DEFAULT_PORTFOLIO_NAME, DEFAULT_PORTFOLIO_ID)],
  activeId: DEFAULT_PORTFOLIO_ID,

  createPortfolio: (name) => {
    const id = genId("pf");
    set((state) => ({
      portfolios: [...state.portfolios, makeEmptyPortfolio(name, id)],
      activeId: id,
    }));
    return id;
  },

  renamePortfolio: (id, name) =>
    set((state) => {
      const trimmed = name.trim();
      if (trimmed === "") {
        return state;
      }
      return {
        portfolios: state.portfolios.map((p) => (p.id === id ? { ...p, name: trimmed } : p)),
      };
    }),

  deletePortfolio: (id) =>
    set((state) => {
      const remaining = state.portfolios.filter((p) => p.id !== id);
      // Never drop to zero — a portfolio panel always has at least one bag.
      if (remaining.length === 0) {
        const fresh = makeEmptyPortfolio();
        return { portfolios: [fresh], activeId: fresh.id };
      }
      const activeId = state.activeId === id ? remaining[0].id : state.activeId;
      return { portfolios: remaining, activeId };
    }),

  setActive: (id) =>
    set((state) => (state.portfolios.some((p) => p.id === id) ? { activeId: id } : state)),

  addHolding: (portfolioId, input) =>
    set((state) => {
      const holding = normalizeHolding({ ...input, id: genId("h") });
      if (!holding) {
        return state;
      }
      return {
        portfolios: state.portfolios.map((p) =>
          p.id === portfolioId ? { ...p, holdings: [...p.holdings, holding] } : p,
        ),
      };
    }),

  updateHolding: (portfolioId, holdingId, input) =>
    set((state) => {
      const next = normalizeHolding({ ...input, id: holdingId });
      if (!next) {
        return state;
      }
      return {
        portfolios: state.portfolios.map((p) =>
          p.id === portfolioId
            ? { ...p, holdings: p.holdings.map((h) => (h.id === holdingId ? next : h)) }
            : p,
        ),
      };
    }),

  removeHolding: (portfolioId, holdingId) =>
    set((state) => ({
      portfolios: state.portfolios.map((p) =>
        p.id === portfolioId ? { ...p, holdings: p.holdings.filter((h) => h.id !== holdingId) } : p,
      ),
    })),

  setAll: (portfolios, activeId) =>
    set(() => {
      const cleaned: Portfolio[] = (Array.isArray(portfolios) ? portfolios : [])
        .filter((p) => p && typeof p === "object")
        .map((p) => ({
          id: typeof p.id === "string" && p.id !== "" ? p.id : genId("pf"),
          name:
            typeof p.name === "string" && p.name.trim() !== ""
              ? p.name.trim()
              : DEFAULT_PORTFOLIO_NAME,
          holdings: (Array.isArray(p.holdings) ? p.holdings : [])
            .map(normalizeHolding)
            .filter((h): h is Holding => h !== null),
        }));
      if (cleaned.length === 0) {
        const fresh = makeEmptyPortfolio(DEFAULT_PORTFOLIO_NAME, DEFAULT_PORTFOLIO_ID);
        return { portfolios: [fresh], activeId: fresh.id };
      }
      const valid = activeId && cleaned.some((p) => p.id === activeId) ? activeId : cleaned[0].id;
      return { portfolios: cleaned, activeId: valid };
    }),
}));
