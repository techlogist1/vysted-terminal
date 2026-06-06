"use client";

import { useMemo } from "react";

import { sendToAgent } from "@/store/agent-command";
import { usePanelContextBus } from "@/store/panel-context";
import { cn } from "@/lib/utils";

/**
 * Teach-the-agent "try this" chips — the Perplexity-style capsules below the
 * composer in the empty state (PRODUCT_DESIGN_DECISIONS §8). They make the
 * agent's capabilities legible on first run: a click fills + submits the
 * composer through the SAME single send path the chat owns (`sendToAgent` →
 * the agent-command bus → `handleSend`), so a chip never re-implements
 * provider/key resolution or the §6.5 gate.
 *
 * Context-aware: when a chart/panel is focused on a symbol, the first chips
 * are scoped to it ("Research $NVDA"); otherwise a static finance-relevant
 * set is shown. The static defaults always render.
 */

/** A single suggestion: the visible label and the prompt actually dispatched. */
interface Suggestion {
  label: string;
  prompt: string;
}

/** The always-available finance defaults (shown when no symbol is focused). */
const DEFAULT_SUGGESTIONS: readonly Suggestion[] = [
  { label: "Research $NVDA", prompt: "Research $NVDA — thesis, valuation, and the key risks." },
  {
    label: "Compare AAPL vs MSFT",
    prompt: "Compare $AAPL vs $MSFT on growth, margins, and valuation.",
  },
  {
    label: "Scan today's movers",
    prompt: "Scan today's biggest movers and tell me what's driving them.",
  },
  {
    label: "Summarize my portfolio P&L",
    prompt: "Summarize my portfolio's P&L and flag the biggest contributors.",
  },
];

/** Pull the focused symbol off the panel-context bus, mirroring `describeContext`
 *  in ChatSidebar — a chart/equity panel publishes `{ symbol }` or `{ ticker }`. */
function useFocusedSymbol(): string | null {
  const focusedSource = usePanelContextBus((s) => s.focusedSource);
  const lastEventBySource = usePanelContextBus((s) => s.lastEventBySource);
  return useMemo(() => {
    if (!focusedSource) {
      return null;
    }
    const event = lastEventBySource[focusedSource];
    const payload = event?.payload;
    if (payload && typeof payload === "object") {
      const obj = payload as Record<string, unknown>;
      if (typeof obj.symbol === "string" && obj.symbol) {
        return obj.symbol.toUpperCase();
      }
      if (typeof obj.ticker === "string" && obj.ticker) {
        return obj.ticker.toUpperCase();
      }
    }
    return null;
  }, [focusedSource, lastEventBySource]);
}

/** Symbol-scoped chips, prepended when a panel is focused on an instrument. */
function symbolSuggestions(symbol: string): Suggestion[] {
  return [
    {
      label: `Research $${symbol}`,
      prompt: `Research $${symbol} — thesis, valuation, and the key risks.`,
    },
    {
      label: `What moved $${symbol} today?`,
      prompt: `What moved $${symbol} today? Summarize the catalysts.`,
    },
  ];
}

export function SuggestionChips() {
  const symbol = useFocusedSymbol();

  // Context-aware ordering: lead with the focused-symbol chips, then fill the
  // row with the static defaults that don't duplicate them. The defaults are
  // always present, so the row is never empty.
  const suggestions = useMemo<Suggestion[]>(() => {
    if (!symbol) {
      return [...DEFAULT_SUGGESTIONS];
    }
    const scoped = symbolSuggestions(symbol);
    const taken = new Set(scoped.map((s) => s.label));
    const filler = DEFAULT_SUGGESTIONS.filter((s) => !taken.has(s.label));
    return [...scoped, ...filler].slice(0, 4);
  }, [symbol]);

  return (
    <div
      aria-label="Suggested prompts"
      className="flex w-full max-w-xs flex-col items-stretch gap-2"
    >
      {suggestions.map((s) => (
        <button
          key={s.label}
          type="button"
          onClick={() => sendToAgent(s.prompt)}
          title={s.prompt}
          className={cn(
            "border-charcoal-700 bg-charcoal-850 text-charcoal-300",
            "text-body w-full rounded-md border px-3 py-2 text-left transition-colors",
            "hover:border-charcoal-600 hover:text-charcoal-100 hover:bg-charcoal-800",
            "focus-visible:ring-1 focus-visible:ring-amber-400 focus-visible:outline-none",
          )}
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}
