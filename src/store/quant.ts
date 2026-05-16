/**
 * Quant store — Phase 6 (Teammate Q).
 *
 * Lightweight Zustand store that holds the last result from each
 * QuantLib pricing endpoint plus an error / loading channel per surface.
 * The panels render directly off the slice; tests inject a mocked
 * sidecar base URL the same way Phase 5 stores do.
 */

import { create } from "zustand";

import { getSidecarBaseUrl } from "@/lib/sidecar-client";

import type {
  BondPricingRequest,
  BondPricingResult,
  GreeksRequest,
  GreeksResult,
  OptionPricingRequest,
  OptionPricingResult,
  YieldCurveRequest,
  YieldCurveResult,
} from "../../types/quant";

export type QuantStatus = "idle" | "loading" | "ready" | "error";

interface QuantState {
  // Option pricing
  lastOptionPricing: OptionPricingResult | null;
  optionStatus: QuantStatus;
  optionError: string | null;
  priceOption: (req: OptionPricingRequest) => Promise<OptionPricingResult>;

  // Greeks dashboard
  lastGreeks: GreeksResult | null;
  greeksStatus: QuantStatus;
  greeksError: string | null;
  computeGreeks: (req: GreeksRequest) => Promise<GreeksResult>;

  // Bond pricing
  lastBondPricing: BondPricingResult | null;
  bondStatus: QuantStatus;
  bondError: string | null;
  priceBond: (req: BondPricingRequest) => Promise<BondPricingResult>;

  // Yield curve
  lastYieldCurve: YieldCurveResult | null;
  yieldCurveStatus: QuantStatus;
  yieldCurveError: string | null;
  bootstrapYieldCurve: (req: YieldCurveRequest) => Promise<YieldCurveResult>;
}

/**
 * Tiny ``fetch``-based POST helper. Mirrors the pattern used by
 * ``src/store/safety.ts`` — the sidecar base URL is resolved once via
 * Tauri's ``get_sidecar_port`` command (cached by ``sidecar-client``).
 */
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
      // body was not JSON — keep the status text
    }
    throw new Error(`POST ${path} failed (${response.status}): ${detail}`);
  }
  return (await response.json()) as TRes;
}

export const useQuantStore = create<QuantState>((set) => ({
  lastOptionPricing: null,
  optionStatus: "idle",
  optionError: null,

  priceOption: async (req) => {
    set({ optionStatus: "loading", optionError: null });
    try {
      const result = await postJson<OptionPricingRequest, OptionPricingResult>(
        "/quant/option/price",
        req,
      );
      set({
        lastOptionPricing: result,
        optionStatus: "ready",
        optionError: null,
      });
      return result;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "option pricing failed";
      set({ optionStatus: "error", optionError: message });
      throw err;
    }
  },

  lastGreeks: null,
  greeksStatus: "idle",
  greeksError: null,

  computeGreeks: async (req) => {
    set({ greeksStatus: "loading", greeksError: null });
    try {
      const result = await postJson<GreeksRequest, GreeksResult>("/quant/option/greeks", req);
      set({ lastGreeks: result, greeksStatus: "ready", greeksError: null });
      return result;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Greeks computation failed";
      set({ greeksStatus: "error", greeksError: message });
      throw err;
    }
  },

  lastBondPricing: null,
  bondStatus: "idle",
  bondError: null,

  priceBond: async (req) => {
    set({ bondStatus: "loading", bondError: null });
    try {
      const result = await postJson<BondPricingRequest, BondPricingResult>(
        "/quant/bond/price",
        req,
      );
      set({ lastBondPricing: result, bondStatus: "ready", bondError: null });
      return result;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "bond pricing failed";
      set({ bondStatus: "error", bondError: message });
      throw err;
    }
  },

  lastYieldCurve: null,
  yieldCurveStatus: "idle",
  yieldCurveError: null,

  bootstrapYieldCurve: async (req) => {
    set({ yieldCurveStatus: "loading", yieldCurveError: null });
    try {
      const result = await postJson<YieldCurveRequest, YieldCurveResult>("/quant/yield-curve", req);
      set({ lastYieldCurve: result, yieldCurveStatus: "ready", yieldCurveError: null });
      return result;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "yield curve bootstrap failed";
      set({ yieldCurveStatus: "error", yieldCurveError: message });
      throw err;
    }
  },
}));

/** Test-only — reset all four slices to their initial idle state. */
export function resetQuantStoreForTests(): void {
  useQuantStore.setState({
    lastOptionPricing: null,
    optionStatus: "idle",
    optionError: null,
    lastGreeks: null,
    greeksStatus: "idle",
    greeksError: null,
    lastBondPricing: null,
    bondStatus: "idle",
    bondError: null,
    lastYieldCurve: null,
    yieldCurveStatus: "idle",
    yieldCurveError: null,
  });
}
