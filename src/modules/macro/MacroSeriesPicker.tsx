"use client";

import { useEffect, useMemo, useState } from "react";
import { SearchX } from "lucide-react";

import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { selectCatalog, selectSearchResults, useMacroStore } from "@/store/macro";

import type { MacroProvider } from "../../../types/macro";

const PROVIDERS: ReadonlyArray<{ id: MacroProvider; label: string }> = [
  { id: "fred", label: "FRED" },
  { id: "ecb", label: "ECB" },
  { id: "imf", label: "IMF" },
  { id: "world-bank", label: "World Bank" },
];

interface Props {
  provider: MacroProvider;
  onProviderChange: (provider: MacroProvider) => void;
  onSelect: (provider: MacroProvider, seriesId: string) => void;
}

/**
 * Macro series picker — provider tabs + search input + Featured catalog list.
 *
 * - Provider tabs swap which upstream the picker queries.
 * - The search input runs against ``/macro/search?q=&provider=`` and shows
 *   up to 25 ranked results.
 * - When no query is entered the Featured tab renders the curated catalog
 *   for the selected provider (FRED's most-popular series, ECB's monetary
 *   policy + ICP set, IMF's headline national accounts series, the WB
 *   WDI headline indicators).
 * - Clicking any result calls :prop:`onSelect`, which the panel uses to
 *   load + render the series.
 */
export function MacroSeriesPicker({ provider, onProviderChange, onSelect }: Props) {
  const [query, setQuery] = useState("");
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const search = useMacroStore((s) => s.search);
  const loadCatalog = useMacroStore((s) => s.loadCatalog);
  const results = useMacroStore((s) => selectSearchResults(s, provider, query));
  const catalog = useMacroStore((s) => selectCatalog(s, provider));

  // Pull the catalog whenever the active provider changes (cached after
  // first load). All setState calls are inside async callbacks — never
  // synchronously in the effect body, avoiding the set-state-in-effect lint.
  useEffect(() => {
    if (catalog) return; // already cached — nothing to do
    let cancelled = false;
    loadCatalog(provider)
      .then(() => {
        if (!cancelled) setCatalogError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setCatalogError(err instanceof Error ? err.message : "Failed to load featured series");
      });
    return () => {
      cancelled = true;
    };
  }, [provider, loadCatalog, catalog]);

  // Debounce the search so we do not fire one request per keystroke.
  useEffect(() => {
    if (!query.trim()) return;
    const handle = window.setTimeout(() => {
      void search(provider, query.trim(), 25);
    }, 200);
    return () => window.clearTimeout(handle);
  }, [provider, query, search]);

  const visibleRows = useMemo(() => {
    if (query.trim()) {
      return results.map((r) => ({
        provider: r.provider,
        series_id: r.series_id,
        title: r.title,
        sub: [r.frequency, r.units].filter(Boolean).join(" • "),
      }));
    }
    if (!catalog) return [];
    return catalog.entries.map((e) => ({
      provider: e.provider,
      series_id: e.series_id,
      title: e.title,
      sub: [e.category, e.frequency, e.units].filter(Boolean).join(" • "),
    }));
  }, [query, results, catalog]);

  return (
    <div
      className="border-charcoal-800 flex shrink-0 flex-col gap-2 border-b p-3"
      data-testid="macro-picker"
    >
      <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Macro provider">
        {PROVIDERS.map((p) => {
          const active = p.id === provider;
          return (
            <Button
              key={p.id}
              variant={active ? "default" : "outline"}
              size="sm"
              role="tab"
              aria-selected={active}
              onClick={() => onProviderChange(p.id)}
              data-testid={`macro-provider-${p.id}`}
            >
              {p.label}
            </Button>
          );
        })}
      </div>

      <input
        type="text"
        placeholder={`Search ${provider} series… (or browse Featured)`}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="border-charcoal-700 bg-charcoal-850 text-charcoal-100 placeholder:text-charcoal-500 rounded-control text-body focus-visible:border-charcoal-500 h-8 border px-3 outline-none"
        data-testid="macro-search-input"
      />

      <div
        className="border-charcoal-800 bg-charcoal-950 flex max-h-48 flex-col overflow-y-auto rounded-none border md:max-h-72"
        role="listbox"
        aria-label="Macro series results"
      >
        {visibleRows.length === 0 ? (
          query.trim() ? (
            <EmptyState
              dense
              icon={SearchX}
              headline="No matching series"
              hint={`No results for "${query.trim()}" on ${provider}.`}
            />
          ) : catalogError ? (
            <div className="flex items-center justify-between gap-3 px-3 py-2">
              <span className="text-negative text-caption min-w-0 truncate" title={catalogError}>
                Could not load featured series.
              </span>
              <Button
                type="button"
                size="xs"
                variant="ghost"
                onClick={() => {
                  setCatalogError(null);
                  loadCatalog(provider).catch((err: unknown) => {
                    setCatalogError(
                      err instanceof Error ? err.message : "Failed to load featured series",
                    );
                  });
                }}
              >
                Retry
              </Button>
            </div>
          ) : !catalog ? (
            // Row-shaped pulse skeleton for the catalog fetch window.
            <div className="flex animate-pulse flex-col" data-testid="macro-catalog-skeleton">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="border-charcoal-900 flex flex-col gap-1 border-b px-3 py-2">
                  <div className="bg-charcoal-800 h-3 w-1/2 rounded-none" />
                  <div className="bg-charcoal-800 h-2 w-1/3 rounded-none" />
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              dense
              icon={SearchX}
              headline="No featured series"
              hint="This provider has no curated catalog — search above instead."
            />
          )
        ) : (
          visibleRows.map((row) => (
            <button
              key={`${row.provider}:${row.series_id}`}
              type="button"
              onClick={() => onSelect(row.provider, row.series_id)}
              className="border-charcoal-900 hover:bg-charcoal-800 border-b px-3 py-1.5 text-left"
              data-testid={`macro-result-${row.series_id}`}
            >
              <div className="text-charcoal-100 text-caption">{row.title}</div>
              <div className="text-charcoal-500 text-caption">
                {row.series_id}
                {row.sub ? ` — ${row.sub}` : ""}
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
