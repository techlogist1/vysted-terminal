/**
 * Shared live ticker autocomplete — the ONE wiring between text inputs and the
 * sidecar's fast `/resolve/autocomplete` route (masters-only, network-free on
 * the sidecar side, locale-ranked).
 *
 * Until R7 nothing in the UI called this route: typing a company name
 * ("Route Mobile") into the watchlist or palette found nothing even though the
 * resolver knew the listing at 0.98 confidence. Consumers: the watchlist
 * add-symbol input, the ⌘K palette's live symbol rows.
 */

import { useEffect, useRef, useState } from "react";

import { sidecarGet } from "@/lib/sidecar-client";
import { useSettingsStore } from "@/store/settings";

export interface SymbolCandidate {
  symbol: string;
  name: string;
  exchange: string;
  region: string;
  asset_class: string;
  yahoo_symbol: string;
  confidence: number;
}

interface AutocompleteResponse {
  query: string;
  region: string;
  candidates: SymbolCandidate[];
}

const DEBOUNCE_MS = 140;

/** Imperative fetch (palette + tests). Failure degrades to an empty list. */
export async function fetchSymbolCandidates(
  query: string,
  region: string,
  limit = 8,
): Promise<SymbolCandidate[]> {
  const q = query.trim();
  if (q.length < 2) {
    return [];
  }
  try {
    const res = await sidecarGet<AutocompleteResponse>("/resolve/autocomplete", {
      q,
      region,
      limit: String(limit),
    });
    return res.candidates ?? [];
  } catch {
    return [];
  }
}

/**
 * Debounced hook with a stale-response guard: only the latest in-flight
 * query's result lands, so fast typing never paints out-of-order candidates.
 */
export function useSymbolAutocomplete(query: string, limit = 8): SymbolCandidate[] {
  const region = useSettingsStore((s) => s.region);
  const [candidates, setCandidates] = useState<SymbolCandidate[]>([]);
  const seq = useRef(0);

  useEffect(() => {
    const q = query.trim();
    const mySeq = ++seq.current;
    if (q.length < 2) {
      // Defer the clear a tick: a synchronous setState inside an effect body
      // triggers cascading renders (lint rule); the seq guard keeps it correct.
      const clear = setTimeout(() => {
        if (seq.current === mySeq) {
          setCandidates([]);
        }
      }, 0);
      return () => clearTimeout(clear);
    }
    const timer = setTimeout(() => {
      void fetchSymbolCandidates(q, region, limit).then((rows) => {
        if (seq.current === mySeq) {
          setCandidates(rows);
        }
      });
    }, DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [query, region, limit]);

  return candidates;
}
