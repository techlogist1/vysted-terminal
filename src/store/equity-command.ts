/**
 * Equity-overview command channel — the host's direct "open this company" path.
 *
 * The mirror of `chart-command` for the Equity Overview panel: a symbol surface
 * anywhere (a screener row, a watchlist entry, a brief `$CASHTAG` chip, a command-
 * palette result, a peer chip) issues `loadSymbol(symbol)` and the Equity Overview
 * panel — which has no other external-injection path — consumes it via a `useEffect`
 * keyed on `seq`, so "click any company anywhere → the full overview" works without
 * the click having to reach into the panel's local state. `seq` bumps on every
 * issue so re-opening the SAME symbol still re-triggers the consumer.
 *
 * Platform-neutral (pure Zustand) — no OS/path assumptions, so a later Windows
 * build inherits it unchanged.
 */

import { create } from "zustand";

interface EquityCommandState {
  /** Most recent "open this company" command from the host. `seq` bumps on every
   *  issue so an equal symbol still re-triggers the panel's consumer effect.
   *  `highlightMetric` (R7, the learner flow) names a fundamentals metric the
   *  panel should scroll to and pulse once loaded — e.g. "pe_ratio" when the
   *  agent answers "what is a P/E ratio? show me on Tata Steel". */
  command: { symbol: string; seq: number; highlightMetric?: string } | null;
  /** Host → Equity Overview: load (and surface) a company's overview. */
  loadSymbol: (symbol: string, highlightMetric?: string) => void;
}

export const useEquityCommandStore = create<EquityCommandState>((set) => ({
  command: null,
  loadSymbol: (symbol, highlightMetric) =>
    set((state) => ({
      command: { symbol, seq: (state.command?.seq ?? 0) + 1, highlightMetric },
    })),
}));

/** Test helper: reset the equity-command store. */
export function resetEquityCommandStoreForTests(): void {
  useEquityCommandStore.setState({ command: null });
}
