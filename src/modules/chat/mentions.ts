/**
 * `@`-mention surface for the chat composer (FR-101, SC-023).
 *
 * Typing ``@`` in the composer opens an inline picker over four LAYERS of
 * mention tokens:
 *
 *   1. **surfaces** — `@chart` `@news` `@filings` `@terminal`: pin the agent's
 *      attention to a workspace surface (the lead maps the token to that panel's
 *      live context).
 *   2. **scopes** — `@watchlist` `@portfolio`: widen the agent's scope to a
 *      local corpus (the tracked symbols / a portfolio's holdings).
 *   3. **agents** — `@analyst` `@quant`: a `promptPrefix` reroutes the turn
 *      ("[Act as a fundamental analyst] …") without switching the active agent.
 *   4. **instruments** — `@AAPL` / `@GOLDBEES`: DYNAMIC, resolved live against
 *      the read-only `/resolve` route, locale-aware (NSE for an IN session).
 *
 * The first three are STATIC (declared below); the instrument layer is resolved
 * at type-time. This module is pure and presentational-free — `matchMention`
 * and `resolveMention` are pure functions (one async network call), and the
 * keyboard-nav + composer wiring live in the lead-owned `ChatSidebar`.
 */

import { sidecarGet } from "@/lib/sidecar-client";
import type { Region } from "@/lib/region";

/** The layer a mention belongs to — drives the badge in the picker. */
export type MentionKind = "instrument" | "surface" | "scope" | "agent";

/** A single mention entry surfaced in the inline picker. */
export interface MentionDef {
  /** The full token including the leading `@` (e.g. `"@chart"`, `"@AAPL"`). */
  token: string;
  /** Which layer it belongs to (drives the badge + sort band). */
  kind: MentionKind;
  /** Primary label shown in the picker row. */
  label: string;
  /** Optional secondary line (e.g. an instrument's company name). */
  description?: string;
  /**
   * For agent mentions: text prepended to the composed prompt so the turn is
   * rerouted without switching the active agent (the lead consumes this).
   */
  promptPrefix?: string;
}

/**
 * The static mention catalog — surfaces, scopes, and agents. The instrument
 * layer (`@TICKER`) is NOT here; it is resolved live in `resolveMention`. Order
 * is the stable "empty query" order shown right after the user types `@`.
 */
export const STATIC_MENTIONS: MentionDef[] = [
  // --- surfaces -----------------------------------------------------------
  {
    token: "@chart",
    kind: "surface",
    label: "Chart",
    description: "Pin the chart panel's current symbol + timeframe as context.",
  },
  {
    token: "@news",
    kind: "surface",
    label: "News",
    description: "Pin the latest news feed as context.",
  },
  {
    token: "@filings",
    kind: "surface",
    label: "Filings",
    description: "Pin the SEC/regulatory filings surface as context.",
  },
  {
    token: "@terminal",
    kind: "surface",
    label: "Terminal",
    description: "Pin the whole terminal workspace state as context.",
  },
  // --- scopes -------------------------------------------------------------
  {
    token: "@watchlist",
    kind: "scope",
    label: "Watchlist",
    description: "Scope the question to your tracked symbols.",
  },
  {
    token: "@portfolio",
    kind: "scope",
    label: "Portfolio",
    description: "Scope the question to your active portfolio's holdings.",
  },
  // --- agents (promptPrefix routing) -------------------------------------
  {
    token: "@analyst",
    kind: "agent",
    label: "Analyst",
    description: "Answer as a fundamental analyst.",
    promptPrefix: "[Act as a fundamental analyst] ",
  },
  {
    token: "@quant",
    kind: "agent",
    label: "Quant",
    description: "Answer as a quantitative analyst.",
    promptPrefix: "[Act as a quantitative analyst] ",
  },
];

/**
 * Decide whether the inline mention picker should be open for the caret
 * position and, if so, the bare query under the cursor.
 *
 * A mention token is the run of non-whitespace characters ending at the caret
 * whose first character is `@`. The picker is open while that token has no
 * embedded whitespace (once the user types a space the mention is complete).
 * `@` alone opens the picker with an empty query (the full static list).
 *
 * Pure: it inspects only the text the user has typed up to `caret`, so a `@` in
 * the middle of an already-typed word still resolves against the token boundary.
 */
export function matchMention(input: string, caret: number): { open: boolean; query: string } {
  const pos = Math.max(0, Math.min(caret, input.length));
  const before = input.slice(0, pos);
  // The token under the caret is the trailing run with no whitespace.
  const tokenMatch = /(\S*)$/.exec(before);
  const token = tokenMatch ? tokenMatch[1] : "";
  if (!token.startsWith("@")) {
    return { open: false, query: "" };
  }
  const query = token.slice(1);
  // A whitespace inside the token would have ended it above; an `@` further in
  // (e.g. an email) shouldn't trigger — require the `@` to start the token.
  if (query.includes("@")) {
    return { open: false, query: "" };
  }
  return { open: true, query };
}

/** Prefix matches outrank substring matches; shorter labels break the tie. */
function scoreStatic(def: MentionDef, query: string): number | null {
  if (query.length === 0) {
    return 0;
  }
  const haystack = def.token.slice(1).toLowerCase();
  const idx = haystack.indexOf(query);
  if (idx < 0) {
    return null;
  }
  const band = idx === 0 ? 1000 : 0;
  return band - idx * 10 - haystack.length;
}

/** The static mentions matching `query` (fuzzy), ranked prefix-first. */
function staticMatches(query: string): MentionDef[] {
  const lc = query.toLowerCase();
  if (lc.length === 0) {
    return [...STATIC_MENTIONS];
  }
  return STATIC_MENTIONS.map((def) => ({ def, score: scoreStatic(def, lc) }))
    .filter((e): e is { def: MentionDef; score: number } => e.score !== null)
    .sort((a, b) => b.score - a.score)
    .map((e) => e.def);
}

/** One instrument row from the read-only `/resolve` route. */
interface ResolveInstrument {
  symbol: string;
  name: string;
  exchange: string;
  region: string;
  asset_class: string;
  yahoo_symbol: string;
  confidence: number;
}

/** The `/resolve` response shape (mirrors `sidecar/routers/resolve.py`). */
interface ResolveResponse {
  ok: boolean;
  query: string;
  region: string;
  resolved: ResolveInstrument | null;
  needs_disambiguation: boolean;
  candidates: ResolveInstrument[];
}

/**
 * A query "looks like" an instrument lookup once it is at least two characters —
 * shorter than that the candidate set is noise and the static mentions are what
 * the user is reaching for. We never gate on character class: an Indian ETF like
 * `GOLDBEES` and a US ticker like `AAPL` both flow through, and a free-text name
 * fragment ("apple") is a legitimate resolve query too.
 */
function looksLikeInstrument(query: string): boolean {
  return query.trim().length >= 2;
}

/** Map a resolved instrument row to a picker mention. */
function instrumentMention(row: ResolveInstrument): MentionDef {
  return {
    token: `@${row.symbol}`,
    kind: "instrument",
    label: `${row.symbol} · ${row.exchange}`,
    description: row.name,
  };
}

/**
 * Resolve the mentions to show for a picker `query`, locale-aware.
 *
 * Returns the static matches (surfaces / scopes / agents) PLUS, when the query
 * looks like an instrument lookup, live instrument matches from the read-only
 * `/resolve` route — the resolved best instrument first, then its ranked
 * candidates, de-duplicated by symbol. `region` is the active session region
 * (read from `useSettingsStore` by the caller) and routes resolution
 * locale-first (e.g. NSE for an IN session). A resolve failure degrades to just
 * the static matches — a flaky network never empties the picker.
 */
export async function resolveMention(query: string, region: Region): Promise<MentionDef[]> {
  const statics = staticMatches(query);
  if (!looksLikeInstrument(query)) {
    return statics;
  }

  let instruments: MentionDef[] = [];
  try {
    const res = await sidecarGet<ResolveResponse>("/resolve", { q: query, region });
    if (res.ok) {
      const seen = new Set<string>();
      const rows: ResolveInstrument[] = [];
      if (res.resolved) {
        rows.push(res.resolved);
      }
      for (const candidate of res.candidates) {
        rows.push(candidate);
      }
      for (const row of rows) {
        const key = row.symbol.toUpperCase();
        if (seen.has(key)) {
          continue;
        }
        seen.add(key);
        instruments.push(instrumentMention(row));
      }
    }
  } catch {
    // A resolve failure (network/sidecar) must never empty the picker — fall
    // back to the static matches alone.
    instruments = [];
  }

  // Static matches stay on top (surfaces/scopes/agents are the discoverable
  // verbs); resolved instruments follow, so a ticker that also prefix-matches a
  // static word never buries it.
  return [...statics, ...instruments];
}

/** The agent mentions that carry a `promptPrefix` reroute (computed once). */
const AGENT_MENTIONS = STATIC_MENTIONS.filter((m) => m.kind === "agent" && m.promptPrefix);

/**
 * Apply `@analyst` / `@quant` prompt-prefix routing to a composed message.
 *
 * Scans `input` for any agent-mention token present as a WHOLE word, strips that
 * token from the text, and prepends its `promptPrefix` so the turn is rerouted
 * ("[Act as a fundamental analyst] …") without switching the active agent
 * (FR-101). Multiple agent mentions stack their prefixes in catalog order. A
 * message with no agent mention is returned untouched, so this is safe to run on
 * every send. The surface/scope/instrument mentions are LEFT in the text — the
 * lead's context layer consumes those tokens in place; only the agent layer
 * rewrites the prompt.
 */
export function applyMentionPrefixes(input: string): string {
  let body = input;
  const prefixes: string[] = [];
  for (const mention of AGENT_MENTIONS) {
    // Match the token only as a standalone word (`@analyst`, not `@analysts`),
    // case-insensitively, anywhere in the message. Escape `@` is unnecessary; the
    // token boundary is whitespace/string-edge, since `@` itself starts a token.
    const token = mention.token;
    const pattern = new RegExp(`(^|\\s)${token}(?=\\s|$)`, "gi");
    if (pattern.test(body)) {
      prefixes.push(mention.promptPrefix!);
      // Drop the token, collapsing the now-doubled whitespace it leaves behind.
      body = body
        .replace(new RegExp(`(^|\\s)${token}(?=\\s|$)`, "gi"), "$1")
        .replace(/\s{2,}/g, " ");
    }
  }
  if (prefixes.length === 0) {
    return input;
  }
  return `${prefixes.join("")}${body.trim()}`;
}
