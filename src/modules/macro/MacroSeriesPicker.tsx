"use client";

import { useEffect, useMemo, useState } from "react";

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
  const search = useMacroStore((s) => s.search);
  const loadCatalog = useMacroStore((s) => s.loadCatalog);
  const results = useMacroStore((s) => selectSearchResults(s, provider, query));
  const catalog = useMacroStore((s) => selectCatalog(s, provider));

  // Pull the catalog whenever the active provider changes (cached after
  // first load).
  useEffect(() => {
    void loadCatalog(provider);
  }, [provider, loadCatalog]);

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
      className="border-charcoal-800 flex flex-col gap-2 border-b p-3"
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
        className="border-charcoal-700 bg-charcoal-900 text-charcoal-100 placeholder:text-charcoal-500 rounded-md border px-2.5 py-1.5 font-mono text-[12px] focus:border-amber-600 focus:outline-none"
        data-testid="macro-search-input"
      />

      <div
        className="border-charcoal-800 bg-charcoal-950 flex max-h-48 flex-col overflow-y-auto rounded-md border"
        role="listbox"
        aria-label="Macro series results"
      >
        {visibleRows.length === 0 ? (
          <div className="text-charcoal-500 px-3 py-2 text-[11px]">
            {query.trim()
              ? `No results for "${query.trim()}" on ${provider}.`
              : "Loading featured series…"}
          </div>
        ) : (
          visibleRows.map((row) => (
            <button
              key={`${row.provider}:${row.series_id}`}
              type="button"
              onClick={() => onSelect(row.provider, row.series_id)}
              className="border-charcoal-900 hover:bg-charcoal-800 border-b px-3 py-1.5 text-left"
              data-testid={`macro-result-${row.series_id}`}
            >
              <div className="text-charcoal-100 font-mono text-[12px]">{row.title}</div>
              <div className="text-charcoal-500 font-mono text-[10px]">
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
