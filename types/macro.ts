/**
 * Vysted Terminal — Phase 6 macro data contracts.
 *
 * Hand-maintained TypeScript mirror of the Pydantic models in
 * ``sidecar/models/macro_extended.py``. When a Pydantic model changes, update
 * the matching interface here in the same commit (see CLAUDE.md Gotchas).
 *
 * Phase 1 shipped a minimal ``MacroSeries`` shape in ``types/data.ts``;
 * Phase 6 extends that with provider routing, series discovery, and
 * frequency / seasonality metadata that the FRED + ECB + IMF + World
 * Bank upstream paths all carry. The Phase 1 shape stays exported from
 * ``data.ts`` for backwards compatibility with any consumer that already
 * imports it; the Macro panel and the agent tools consume the extended
 * shape from this file.
 */

import type { MacroObservation } from "./data";

// ---------------------------------------------------------------------------
// Provider identity
// ---------------------------------------------------------------------------

/** Discriminator for the four macro upstreams supported in v0.6.0. */
export type MacroProvider = "fred" | "ecb" | "imf" | "world-bank";

/** Frequency labels common across the four providers. ``"other"`` covers
 * irregular schedules (e.g. ECB monetary policy decisions). */
export type MacroFrequency = "daily" | "weekly" | "monthly" | "quarterly" | "annual" | "other";

/** Whether the series is seasonally adjusted, not adjusted, or not applicable
 * (e.g. a rate observation). FRED + ECB + IMF expose this; World Bank does
 * not, so ``null`` is allowed. */
export type SeasonalAdjustment = "seasonally-adjusted" | "not-adjusted" | "not-applicable" | null;

// ---------------------------------------------------------------------------
// Series shape (extended)
// ---------------------------------------------------------------------------

/**
 * An economic / macro time series with provider-aware metadata. Phase 6
 * extension over ``MacroSeries`` in ``types/data.ts``:
 *  - ``provider`` is the narrow ``MacroProvider`` literal, not a free
 *    string — wire-level type-safety lands.
 *  - ``frequency``, ``last_updated``, ``seasonal_adjustment`` are new
 *    metadata fields populated where the upstream exposes them.
 *  - ``source_url`` lets the UI link out to the upstream's own page for
 *    that series (FRED's series page, ECB's data portal, etc.).
 */
export interface MacroSeriesExtended {
  series_id: string;
  title: string;
  units: string | null;
  observations: MacroObservation[];
  provider: MacroProvider;
  frequency: MacroFrequency | null;
  last_updated: string | null;
  seasonal_adjustment: SeasonalAdjustment;
  source_url: string | null;
  notes: string | null;
}

// ---------------------------------------------------------------------------
// Discovery (search + catalog)
// ---------------------------------------------------------------------------

/**
 * One result from ``/macro/search?q=`` — a candidate series the picker
 * surfaces. Score is provider-specific (FRED returns a popularity score;
 * ECB / IMF / WB use string-match ranking) and is normalised to a 0–1 float
 * by the sidecar before returning.
 */
export interface MacroSearchResult {
  provider: MacroProvider;
  series_id: string;
  title: string;
  frequency: MacroFrequency | null;
  units: string | null;
  score: number;
}

/**
 * One entry in a provider's curated catalog — e.g. FRED's most-popular
 * series, ECB's published dataflows, World Bank's WDI indicators. Used by
 * the picker's "Featured" tab.
 */
export interface MacroCatalogEntry {
  provider: MacroProvider;
  series_id: string;
  title: string;
  category: string | null;
  frequency: MacroFrequency | null;
  units: string | null;
}

/** Per-provider catalog payload returned by ``/macro/catalog?provider=``. */
export interface MacroCatalog {
  provider: MacroProvider;
  entries: MacroCatalogEntry[];
}
