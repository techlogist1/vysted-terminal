/**
 * Brief claims — the deterministic stated-value ledger (R13 JARVIS 3a).
 *
 * When a research brief publishes, {@link extractBriefClaims} reads the figures
 * straight off `brief.structured` metric cards (headline price + key valuation
 * scalars + every labeled derived metric) — NO LLM parsing — and
 * {@link recordBriefClaims} appends them to the active research space's bounded
 * claims ledger. A later turn whose figure materially contradicts a prior claim
 * can then be reconciled openly (the preamble surfaces the prior values), instead
 * of silently switching.
 *
 * Claims are scoped to a research space (they ride the existing research-space
 * context path); outside a research space nothing is recorded.
 */

import { researchSpaceName } from "@/lib/workspace";
import { useResearchSpacesStore } from "@/store/research-spaces";
import { useWorkspaceStore } from "@/store/workspace";

import type { ResearchBriefData } from "../../types/brief";
import type { ResearchSpaceClaim } from "../../types/research-space";

/** A finite numeric field of a leg's `data` object, or `undefined`. */
function num(obj: unknown, key: string): number | undefined {
  if (typeof obj !== "object" || obj === null) {
    return undefined;
  }
  const value = (obj as Record<string, unknown>)[key];
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

/** True when a value is a `BriefDerivedValue` carrying a real numeric figure. */
function isDerivedValue(value: unknown): value is { value: number; label: string } {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const v = value as { value?: unknown; label?: unknown };
  return typeof v.value === "number" && Number.isFinite(v.value) && typeof v.label === "string";
}

/**
 * Extract the stated figures from a published brief, DETERMINISTICALLY (no LLM):
 * the headline price, the key raw valuation scalars (P/E, market cap, EPS), and
 * every labeled non-null derived metric. Returns `[]` when the brief names no
 * symbol or carries no structured data — a claim is never fabricated.
 */
export function extractBriefClaims(brief: ResearchBriefData): ResearchSpaceClaim[] {
  const symbol = (brief.symbol ?? "").trim().toUpperCase();
  if (!symbol) {
    return [];
  }
  const statedAt = typeof brief.createdAt === "number" ? brief.createdAt : Date.now();
  const claims: ResearchSpaceClaim[] = [];
  const seen = new Set<string>();
  const push = (metric: string, value: number | undefined): void => {
    if (value === undefined || seen.has(metric)) {
      return;
    }
    seen.add(metric);
    claims.push({ symbol, metric, value, statedAt });
  };

  const structured = brief.structured;
  if (!structured) {
    return claims;
  }
  // Headline price.
  const price = structured.price?.ok ? structured.price.data : undefined;
  push("Price", num(price, "price"));
  // Key raw valuation scalars.
  const fund = structured.fundamentals?.ok ? structured.fundamentals.data : undefined;
  push("P/E", num(fund, "pe_ratio"));
  push("Market cap", num(fund, "market_cap"));
  push("EPS", num(fund, "eps"));
  // Every labeled, non-null derived metric (disciplined labels + bases).
  const derived = structured.derived?.ok ? structured.derived.data : undefined;
  if (derived && typeof derived === "object") {
    for (const [key, entry] of Object.entries(derived)) {
      if (key === "conflicts") {
        continue;
      }
      if (isDerivedValue(entry)) {
        push(entry.label, entry.value);
      }
    }
  }
  return claims;
}

/**
 * Record a published brief's stated figures into the ACTIVE research space's
 * claims ledger (R13 JARVIS 3a). No-op outside a research space — claims ride the
 * research-space context path (3b), so ambient copilot turns record nothing.
 * Fire-and-forget-safe: never throws.
 */
export function recordBriefClaims(brief: ResearchBriefData): void {
  const researchSymbol = useWorkspaceStore.getState().researchSymbol;
  if (!researchSymbol) {
    return;
  }
  const claims = extractBriefClaims(brief);
  if (claims.length === 0) {
    return;
  }
  useResearchSpacesStore.getState().recordClaims(researchSpaceName(researchSymbol), claims);
}
