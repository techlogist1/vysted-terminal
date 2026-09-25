"use client";

import { create } from "zustand";

/**
 * Multi-portfolio store.
 *
 * The user can keep several NAMED portfolios and switch between them, manually
 * tracking holdings (symbol / quantity / cost basis / asset class). Every holding
 * is hand-entered. The default is a SINGLE EMPTY portfolio (never fabricated
 * demo data) so a fresh install reads as a clean empty state.
 *
 * Holdings live here (frontend) and persist in the workspace blob
 * (`src/lib/workspace.ts`, the same seam the watchlist uses) — the blob owns
 * holdings, for the panel and the agent alike. The sidecar positions ledger is
 * only the read-once legacy-import source ({@link seedDefaultPortfolio}). P&L
 * is computed by joining each holding to a live quote in the panel.
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

/** The largest quantity a hand-entered holding can hold — big enough for any
 *  real lot, small enough to catch a fat-fingered extra zero (e.g. 1e20). */
export const MAX_HOLDING_QUANTITY = 1e12;

export interface HoldingValidation {
  valid: boolean;
  /** Which field to blame, for a field-specific form/agent message. */
  field?: "symbol" | "quantity" | "costBasis";
  message?: string;
}

/**
 * The one rule set every writer shares (the panel form, the agent path via
 * addHolding/updateHolding, and blob restore via normalizeHolding): a
 * non-empty symbol, a finite quantity in (0, {@link MAX_HOLDING_QUANTITY}],
 * and a finite, non-negative cost basis. Takes raw (possibly string, possibly
 * blank/missing) values so a blank cost is rejected as blank, never coerced
 * to 0 by `Number("")`. Each failure names its field.
 */
export function validateHolding(raw: {
  symbol?: unknown;
  quantity?: unknown;
  costBasis?: unknown;
}): HoldingValidation {
  const symbol = typeof raw.symbol === "string" ? raw.symbol.trim() : "";
  if (symbol === "") {
    return { valid: false, field: "symbol", message: "Symbol is required" };
  }
  if (raw.quantity === "" || raw.quantity === null || raw.quantity === undefined) {
    return { valid: false, field: "quantity", message: "Quantity is required" };
  }
  const quantity = Number(raw.quantity);
  if (!Number.isFinite(quantity)) {
    return {
      valid: false,
      field: "quantity",
      message: `Quantity must be a plain number (got "${String(raw.quantity)}")`,
    };
  }
  if (quantity <= 0) {
    return { valid: false, field: "quantity", message: "Quantity must be greater than 0" };
  }
  if (quantity > MAX_HOLDING_QUANTITY) {
    return { valid: false, field: "quantity", message: "Quantity is too large" };
  }
  if (raw.costBasis === "" || raw.costBasis === null || raw.costBasis === undefined) {
    return { valid: false, field: "costBasis", message: "Avg cost per share is required" };
  }
  const costBasis = Number(raw.costBasis);
  if (!Number.isFinite(costBasis)) {
    return {
      valid: false,
      field: "costBasis",
      message: `Avg cost must be a plain number (got "${String(raw.costBasis)}")`,
    };
  }
  if (costBasis < 0) {
    return { valid: false, field: "costBasis", message: "Avg cost cannot be negative" };
  }
  return { valid: true };
}

/** Coerce an arbitrary (possibly corrupt-blob) holding to a valid one, or drop
 *  it — via {@link validateHolding}, the same rules as the panel form, for
 *  every caller (restore, the agent, the form). Garbage is dropped, never
 *  coerced to a plausible 0. */
function normalizeHolding(raw: unknown): Holding | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const h = raw as Record<string, unknown>;
  if (!validateHolding(h).valid) {
    return null;
  }
  const symbol = (h.symbol as string).trim().toUpperCase();
  const quantity = Number(h.quantity);
  const costBasis = Number(h.costBasis);
  const note = typeof h.note === "string" && h.note.trim() !== "" ? h.note.trim() : undefined;
  return {
    id: typeof h.id === "string" && h.id !== "" ? h.id : genId("h"),
    symbol,
    quantity,
    costBasis,
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
  /** Append a holding to a portfolio; its new id, or null when the input is invalid. */
  addHolding: (portfolioId: string, input: HoldingInput) => string | null;
  /** Replace an existing holding's fields (not a partial merge); false when
   *  the input is invalid or that portfolio holds no such holding (nothing
   *  changes either way). */
  updateHolding: (portfolioId: string, holdingId: string, input: HoldingInput) => boolean;
  /** Remove a holding. */
  removeHolding: (portfolioId: string, holdingId: string) => void;
  /** Replace the whole set — used to restore a persisted blob (guards corruption). */
  setAll: (portfolios: Portfolio[], activeId?: string) => void;
}

export const usePortfoliosStore = create<PortfoliosState>((set, get) => ({
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

  addHolding: (portfolioId, input) => {
    const holding = normalizeHolding({ ...input, id: genId("h") });
    if (!holding) {
      return null;
    }
    set((state) => ({
      portfolios: state.portfolios.map((p) =>
        p.id === portfolioId ? { ...p, holdings: [...p.holdings, holding] } : p,
      ),
    }));
    return holding.id;
  },

  updateHolding: (portfolioId, holdingId, input) => {
    const next = normalizeHolding({ ...input, id: holdingId });
    const target = get()
      .portfolios.find((p) => p.id === portfolioId)
      ?.holdings.some((h) => h.id === holdingId);
    if (!next || !target) {
      return false;
    }
    set((state) => ({
      portfolios: state.portfolios.map((p) =>
        p.id === portfolioId
          ? { ...p, holdings: p.holdings.map((h) => (h.id === holdingId ? next : h)) }
          : p,
      ),
    }));
    return true;
  },

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

/**
 * Replace every portfolio with the default one holding `holdings` — the
 * one-time import of the legacy sidecar positions ledger (R15-LIFECYCLE-009).
 */
export function seedDefaultPortfolio(holdings: HoldingInput[]): void {
  usePortfoliosStore.getState().setAll(
    [
      {
        id: DEFAULT_PORTFOLIO_ID,
        name: DEFAULT_PORTFOLIO_NAME,
        holdings: holdings.map((holding) => ({ ...holding, id: genId("h") })),
      },
    ],
    DEFAULT_PORTFOLIO_ID,
  );
}
