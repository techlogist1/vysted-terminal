# Pass B — research grounding (2026 reality, verified)

_The citable ground for the Pass-B spec. Produced by a 42-agent research workflow
(8 web-research + 2 codebase-seam + ~32 adversarial verification agents,
refute-by-default) on 2026-06-01, branch `001-agent-native-redesign`. Every load-bearing
factual claim was independently fact-checked; corrections the verifiers caught are flagged
**[corrected]** inline. Confidence is noted where it matters. This doc grounds the spec's
data-source, search-tier, research-engine, indicator, and command-surface decisions so the
spec cites reality, not guesses._

> Read with `EXTENSION_SEAMS.md` (the Pass-A seams Pass B plugs into) and the live spec
> (`specs/001-agent-native-redesign/spec.md`). Where this doc names an "open question," it
> feeds the spec's **Open Product Decisions (Pass B)** and the clarify round.

---

## Pillar A — Locale-native data + resolution + fallback

### A.1 The GOLDBEES root cause — yfinance is unsafe for India

- **yfinance intermittently reports valid NSE/BSE tickers as "possibly delisted; no price
  data found"** — including large-caps (ITC.NS, RELIANCE.NS), not just ETFs — from a
  datetime type-mismatch in its timezone-detection logic. GitHub issue
  [#2612](https://github.com/ranaroussi/yfinance/issues/2612), **closed "not planned"**
  (won't-fix). ETFs (GOLDBEES, NIFTYBEES) are disproportionately hit because Yahoo's Indian-ETF
  data is thin. _Confidence 5._
- **yfinance also returns silently-wrong OHLC for NSE** (e.g. TATASTEEL.NS high 138.46 vs
  actual 141.25), issue [#2055](https://github.com/ranaroussi/yfinance/issues/2055), also
  **won't-fix**. Silent wrong data is the worst failure mode for a correctness-critical
  terminal. _Confidence 4._
- **Verdict for the spec:** yfinance stays the **US** keyless default but is **not trusted
  for any `.NS`/`.BO` ticker** without a correctness gate. For India it is, at best, a
  gated last-resort fallback — never the primary.

### A.2 The recommended India source stack (keyless-first, BYOK-upgradeable)

| Tier                       | Source                            | Keyless?                            | Serves                                                                    | Notes                                                                                                                          |
| -------------------------- | --------------------------------- | ----------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Keyless EOD (primary)      | **NSE/BSE Bhavcopy** daily CSV    | ✅ free, no rate limit              | EOD OHLCV, all equities + ETFs (incl GOLDBEES/NIFTYBEES)                  | Authoritative; **T+1 only**                                                                                                    |
| Keyless wrapper            | **jugaad-data 0.33.1** (Mar 2026) | ✅                                  | NSE EQ historical, indices, F&O, live quotes                              | Wraps the **new** NSE site + caching; actively maintained                                                                      |
| Keyless richer             | **nsepython 2.97** (May 2025)     | ✅                                  | + option chains, historical PE/PB                                         | Dual local/server editions                                                                                                     |
| BYOK live/intraday         | **Angel One SmartAPI**            | ✅ free (no monthly fee)            | NSE/BSE/NFO/BFO/MCX, 8000 candles/call, ~5.5y daily                       | **[confirmed]** genuinely free; needs Angel demat acct                                                                         |
| BYOK live/intraday         | **Dhan DhanHQ**                   | ✅ free                             | 5y intraday, 10 req/s data                                                | Liberal limits                                                                                                                 |
| BYOK live/intraday         | **Zerodha Kite Connect**          | ₹500/mo **[corrected — was ₹2000]** | 10y intraday, all instruments                                             | Richest single source for Zerodha users                                                                                        |
| Global keyed (dual-locale) | **EODHD**                         | $19.99/mo All-World EOD             | GOLDBEES.NSE/NIFTYBEES.NSE/SILVERBEES.NSE confirmed; +fundamentals $59.99 | **[corrected]** real coverage, but the **demo token can't verify NSE** (6 fixed symbols only) — needs a real key to smoke-test |
| Global keyed               | **Twelve Data**                   | paid (even basic time-series)       | GOLDBEES on XNSE confirmed                                                | Free tier 8 req/min, no time-series                                                                                            |
| ❌ avoid                   | **Alpha Vantage**                 | —                                   | —                                                                         | **Dropped NSE ~Jul 2020, still absent 2026** (BSE partial via security-code). Do not use for India.                            |

- **India fundamentals/filings:** no official screener.in API (scraping is fragile).
  **FinEdge API** (finedgeapi.com) is a confirmed dedicated NSE/BSE fundamentals API (P&L,
  balance sheet, cash flow, shareholding) — **paid/keyed, no confirmed free tier**. Free
  corporate filings via NSE's public `corporate-filings-actions` JSON endpoint (cookie/session
  fragile).
- **India news RSS (verified working):** Economic Times Markets
  (`economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms`), ET Stocks
  (`/markets/stocks/rssfeeds/2146842.cms`), LiveMint (`livemint.com/rss/news`). Business
  Standard RSS 403s on direct fetch. **Moneycontrol dropped first-party RSS** — use
  **Zerodha Pulse** (`pulse.zerodha.com`) as the aggregator.

### A.3 Symbol resolution + multi-source fallback

- **Two separable sub-problems:** (1) free-text/name → `(ticker, exchange, region,
asset_class)` resolution (query-time lookup), (2) fault-tolerant prioritized data fetch.
  Conflating them is the design trap.
- **Resolver (3-stage ranked fan-out, keyless-first):** Stage 1 — bundled, cached masters:
  SEC `company_tickers.json` (US, ~10k, 24h cache) + a **locally bundled NSE/BSE instruments
  master CSV** (refresh weekly) in an in-process fuzzy index ("Tata Steel" → TATASTEEL).
  Stage 2 — live keyless: **Twelve Data `/symbol_search`** (free 8 req/min, returns
  `mic_code`+country+type, explicit XNSE/XBOM) → **yfinance.Search** (keyless, global,
  `.NS`/`.BO`). Stage 3 — keyed: FMP search → **OpenFIGI** mapping (**[corrected]** uses its
  own `exchCode` **IS** (NSE) / **IB** (BSE), composite **IN** — **not** ISO MIC
  `XNSE`/`XBOM`) → Alpha Vantage `SYMBOL_SEARCH` (25 req/day, `matchScore` useful for
  disambiguation only).
- **Fallback orchestration (OpenBB model):** per-endpoint priority list, user-overridable;
  walk the list on missing-key / empty / error. Layer: **retry** (exp backoff, ≤3, on
  429/5xx) → **circuit breaker** (trip after ~5 fails/60s, 60s cooldown, half-open probe) →
  **stale-serve of last resort** (always tagged `{provider, cached_at, is_stale}` + a UI
  staleness badge — never silently served as live).
- **Correctness gate (reject → advance to next provider) when:** empty/null array, price
  ≤ 0, timestamp older than an exchange-calendar-aware freshness threshold, **returned symbol
  ≠ resolved ticker**, required numeric field returned as `"N/A"`/absent. Anomalous
  price jumps (>2× / <0.5× prior close, no corporate-action flag) → surface a data-quality
  **warning** alongside the value, don't silently reject. Use exchange trading calendars
  (bundled JSON or `pandas-market-calendars`) so weekend/holiday closes aren't falsely rejected.
- **Verified free-tier facts:** Twelve Data 8 req/min (~800 credits/day); Alpha Vantage 25
  req/day; Finnhub international (incl NSE) is **paid-only**. All **[confirmed]**.

---

## Pillar B — Research engine (FAST + DEEP, B+A output)

### B.1 The named pattern — dexter

- **`virattt/dexter`** confirmed: **[corrected]** a **TypeScript** autonomous financial-research
  agent, **~26.7k★** (passed ~24k at its May 2026 trending peak), four agents — **Planning →
  Action → Validation → Answer** — decomposes a ticker/company question into per-ticker
  structured API calls (`get_income_statements`, etc. via the **Financial Datasets API**) plus
  web search, runs a validation self-check after each tool call, logs every step to JSONL
  scratchpads, terminates via explicit step limits + loop-detection guards. This is the closest
  existing shape to Vysted's FAST loop.

### B.2 FAST loop (default, on) — commit

`resolve symbol → parallel structured pull (price/quote, fundamentals, recent-filings digest,
news headlines — 3–5 sidecar tool handlers in parallel) → ONE web-search round (1–3 queries)
→ single-pass LLM synthesis → BriefPanel + panel-arrangement commands.`
**Target ≤15s** (structured 2–5s, web 3–5s, synthesis 5–8s). No reflection/re-query loop.
Termination: fixed (one planning pass, one synthesis). The planning pass decides which panels
to open + which tools to call; the answer pass writes the cited brief + emits arrange commands.
Step-log a JSON record per tool call.

### B.3 DEEP loop (opt-in, "go deeper") — commit

LangGraph-style hierarchical loop, bounded by **two budget axes wired to the existing
BudgetGuard**: `max_rounds` (default **3**, max 5) and `wall_clock_seconds` (default **120**,
max **300**). Shape: `plan_research_brief (what's unanswered?) → parallel researchers
(≤3 concurrent, ≤5 tool calls each) → compress_research (citation-preserving summary) →
supervisor_reflect (coverage met? gaps?) → re-enter if under budget else final_report`.
**Coverage floor:** ≥1 source each for price/quote, fundamentals, news, web context, then the
supervisor may declare complete. **FlashResearch guarantee** (arXiv 2510.05145, **[corrected]**
renamed "ParallelResearch", ICLR 2026 workshop; ~**1.51×** speedup vs GPT-Researcher baseline):
on a hard wall-clock cutoff, **synthesize immediately** from gathered context — abort→synthesize,
never abort→error. (GPT-Researcher defaults **[corrected]** depth=2, **breadth=3** (not 4),
~$0.40/run o3-mini, ~5 min.)

### B.4 BYOK deep-research backend (optional)

**Perplexity `sonar-deep-research`** is the only callable pay-as-you-go deep-research API
**[confirmed]**: opened 2025-03-07, OpenAI-compatible, $2/$8 per M in/out + $3/M reasoning +
$5/1k searches, 128k ctx, ~21 searches/run, returns `citations[]`. Offer as an **opt-in DEEP
backend** gated by a keychain `PERPLEXITY_API_KEY`; **never auto-select the paid path** — show
estimated cost before starting. Native path is better for structured financials (Perplexity has
no SEC/XBRL tool access); Perplexity path is simpler/cheaper for broad questions. OpenAI o3
deep-research and Gemini Deep Research exist only as product features, **not** callable APIs at
parity.

### B.5 Output shape (B+A) — BriefPanel

Research **builds the workspace** AND drops a **synthesized written brief** (Perplexity-style):
markdown body with **`[n]` inline citation chips** (click → scroll source tray) + a collapsible
**sources tray** (index, favicon, title link, domain badge, supporting snippet) + a metadata
header (topic, timestamp, **mode badge FAST|DEEP**, source count, **est. cost USD**) + a dev
**step-log tray** ({step, tool_id, latency_ms, status}). The brief is **one of the panels JARVIS
arranges** — a real dockview slot (composability), not (decision pending) a slide-in drawer. Step
records persist to the existing `runs_store` SQLite (a `steps` column) so progress streams live.

---

## Pillar C — Web search, three tiers of freedom

### C.1 Tier 1 — native, on the user's existing key (the thesis, corrected)

**[corrected]** "ride your existing key" is real for **5 of 9** providers, but it is
**"billable to your key," not free** — every native provider charges a per-search fee on top
of tokens.

| Provider                      | Native server-side search? | Name                                          | Per-search cost **[confirmed]**                | Citations?                                                       |
| ----------------------------- | -------------------------- | --------------------------------------------- | ---------------------------------------------- | ---------------------------------------------------------------- |
| Anthropic                     | ✅                         | `web_search` tool (`max_uses` cap)            | **$10 / 1k**                                   | ✅ `url`+`cited_text`                                            |
| OpenAI                        | ✅                         | `web_search` (Responses API)                  | **$10 / 1k + ~8k input tok/search**            | ✅ `url_citation`                                                |
| Google Gemini                 | ✅                         | `google_search` grounding                     | **$35/1k (2.5) / $14/1k (3)**                  | ✅ `groundingChunks`; **ToS: must render Search-Suggestions UI** |
| Groq                          | ✅ (Compound)              | Compound system                               | per-search                                     | sources embedded in text (least explicit)                        |
| xAI Grok                      | ✅                         | Live Search                                   | per-search                                     | ✅ `citations[]`                                                 |
| DeepSeek                      | ❌                         | —                                             | —                                              | **No native search API** (2026) **[confirmed]**                  |
| Ollama (local)                | ❌ server-side             | (Ollama.com cloud web-search REST, free tier) | —                                              | —                                                                |
| Qwen / Llama (via OpenRouter) | ❌ native                  | OpenRouter wraps with Exa                     | $0.005/call (OpenRouter, not the model vendor) | normalized to `url_citation`                                     |

- **Design:** two-tier dispatch — if the active backend is Anthropic/OpenAI/Gemini/Groq-Compound/xAI,
  use native search (pass `user_location` from the locale setting; normalize all citation shapes
  to `{url,title,excerpt}`). For DeepSeek/Ollama/bare-Qwen/Llama, **fall through** to a BYOK search
  plugin or OpenRouter's Exa plugin — with an **honest prompt** ("your model has no native search;
  add an Exa/Brave key or switch routes"), never surprise routing/cost.
- **Caps:** Anthropic supports `max_uses: N`; OpenAI/xAI don't — enforce a loop-level counter in
  the agent runtime to stop runaway per-search billing during multi-round research.

### C.2 Tier 2 — BYOK search APIs (market consolidated hard in 2025–26)

- **Market events:** **[confirmed]** Microsoft **retired Bing Search API 2025-08-11 (HTTP 410)**;
  **Brave gutted its free tier** Feb 2026 ($5/1k, $5/mo credit, attribution req); **Nebius
  acquired Tavily** (Feb 2026, ≤$400M); **Elastic acquired Jina** (Oct 2025).
- **Best-in-class = Exa** for a finance research agent: WebWalker multi-hop **81% vs Tavily 71%**
  (Exa's own benchmark — vendor-sourced, not independent), p95 **1.4–1.7s vs Tavily 3.8–4.5s**,
  dedicated **financial-reports / news** categories + 1200-domain filter + date filter,
  **$10 free credits** (~2k searches), Anthropic MCP server, native OpenRouter integration.
- **Alternates:** **Tavily** (1000 free credits/mo no-card, most-used in LangChain — many users
  have a key; Nebius roadmap risk) and **Linkup** (€0.005/call ≈ 30% cheaper than Tavily, $20/mo
  free credit, native MCP). **You.com** competitive after a Mar 2026 cut ($5/1k, full-page
  content) but lower retrieval quality.
- **Do NOT default-ship:** Perplexity **Sonar** (no free tier, double-reasoning waste — JARVIS
  already reasons), **Serper** (raw SERP, no extraction — supplement only), **Brave** (gutted),
  **Bing** (dead).
- **Locale-native search:** Exa/Tavily support domain allow-lists → US profile {Yahoo Finance,
  SEC EDGAR, Bloomberg, Reuters, WSJ}, IN profile {NSEIndia, BSEIndia, Moneycontrol, ET, SEBI};
  first-class in the plugin config schema (`{locale, preferredDomains, blockedDomains}`).

### C.3 Tier 3 — local / private (nothing leaves the machine)

- **SearXNG** is the only realistic option (Python/Flask metasearch, 70+ engines, JSON API,
  ~150–600MB RAM, already integrated in LiteLLM/Open WebUI). **Bundling into the PyInstaller
  sidecar is fragile** (Redis/Valkey + uwsgi). Pragmatic v1: **auto-detect `localhost:8080`** +
  **"bring your own SearXNG URL"** config; a Docker-Compose one-click ("Start local search",
  needs Docker/OrbStack) is the next step, not v1-mandatory.

### C.4 The plugin contract for search

Each search backend is a **marketplace plugin** implementing a common interface
`search(query, options) → { results: [{url,title,snippet,publishedAt}], citations: string[] }`
(model Cursor/OpenCode: the agent calls `search()` through the interface, never a vendor SDK
directly). Exa REST, Tavily REST, Linkup MCP, SearXNG JSON all conform without core changes.

---

## Pillar D — JARVIS capability completeness + smart defaults + resourcefulness

### D.1 Default indicator sets (per asset class) — research-backed taste

| Asset class / timeframe | Price-pane defaults                                                                           | Oscillator pane                | One-click (not default)                                                                    |
| ----------------------- | --------------------------------------------------------------------------------------------- | ------------------------------ | ------------------------------------------------------------------------------------------ |
| Equity, daily           | SMA(50) + SMA(200) + volume histogram                                                         | RSI(14) 30/70                  | MACD(12,26,9), Bollinger(20,2), VWAP, ATR-in-tooltip                                       |
| Equity, intraday (<1D)  | EMA(9) + EMA(21) + **session VWAP** (09:30 ET US / **09:15 IST NSE** — locale-aware) + volume | RSI(14)                        | MACD                                                                                       |
| ETF / index             | SMA(50) + SMA(200) + **RS-line vs benchmark** + volume                                        | RSI(14)                        | sector-breadth (% > 50-DMA)                                                                |
| Crypto (perp, daily/4h) | EMA(50) + EMA(200) + **UTC-week-anchored VWAP** + volume                                      | RSI(14) (opt 40–80 bull-range) | **OI histogram** + **funding-rate bars** (±0.05/±0.1% lines) — gated on a derivatives feed |

- **[corrected]** VWAP is widely used but **not >40% "primary" institutional benchmark** (that's
  implementation-shortfall/arrival-price); VWAP is one-of-many, <40%. Standard VWAP **resets at
  session open and is undefined for daily/weekly/monthly** — hence the week-anchor substitute for
  crypto. _Don't over-claim VWAP in copy._
- **lightweight-charts v5.2.0** (Apr 2026) **[confirmed]**: multi-pane via `addPane`/`removePane`/
  `addSeries(..., paneIndex)`; **no built-in indicator math** (canvas only) — the sidecar's 49
  server-computed indicators push `{time,value}` arrays down the chart-command channel; frontend
  only `setData()`. Clean teardown via `removeSeries(ref)` / `removePane(index)`. The
  `deepentropy/lightweight-charts-indicators` lib (446 indicators, v5-native) exists if any
  client-side need arises. **Palette must come from `chart-theme.ts`, never CSS vars** (canvas
  can't read them).

### D.2 Named layout templates (the arrange_layout "taste")

1. **single-focus** — full-width chart + stats ribbon (quick "show me AAPL").
2. **research-cockpit** (flagship) — chart 60% left; fundamentals/key-stats top-right;
   news/filings bottom-right; **brief panel** below. The "research NVDA" deep-dive.
3. **compare** — dual chart side-by-side, shared time axis, relative-performance overlay
   ("NVDA vs AMD"). _(Needs a shared time-axis lock across dockview panels — implementation
   cost to evaluate.)_
4. **macro-scan** — sector heatmap + rotation quadrant + chart + screener ("what's leading today").

The agent picks by query intent: ticker → research-cockpit, "compare X vs Y" → compare, broad
market → macro-scan. This is the fix for the "opened everything in one tile" failure.

### D.3 Resourcefulness / never-dead-ends (the GOLDBEES principle)

The fallback chain (A.3) + correctness gate (A.3) + honest-unavailable surfacing is the spec's
answer to the dead-end: try resolver → try data providers in preference order → on total failure
emit a **human message with the reason** ("GOLDBEES is NSE-listed but no configured source served
it; add an Angel One/EODHD key or enable jugaad-data"), **never raw JSON, never wrong data**.

### D.4 The differentiator (beats Perplexity Finance)

- **Perplexity Finance (mid-2026):** aggregates 40+ sources (FMP, S&P, Quartr, FactSet, LSEG,
  Coinbase, Unusual Whales, Polymarket), locale-aware (US **and India** native — Nifty/Sensex/BSE
  transcripts), watchlists, earnings hub, SEC citations, Plaid portfolio, TradingView chart.
  **[corrected]** Max ($200/mo) added OHLCV/candlestick + **SMA + compare + date-range** charts
  (Dec 2025 changelog). Agent API `finance_search` $5/1k. **Cannot:** custom indicators beyond SMA,
  live DCF/Monte-Carlo, bulk structured export, continuous monitoring/alerts, multi-panel
  persistent workspace; it is insight-only, ephemeral chat, cloud.
- **OpenBB Workspace** generative UI **[corrected]** (Apr/May 2026) — copilot additively
  manipulates a dashboard from NL (add widgets/tabs/params), but enterprise/cloud-first, not
  BYOK/local/open.
- **Fincept Terminal** — the closest open/BYOK competitor: AGPL C++/Qt6 desktop, 37 personas, 100+
  connectors, node editor, **16 broker integrations (incl Zerodha + Angel One [confirmed])**, BYOK
  LLM. Weakness: complex UI, Yahoo/Polygon data reliability. **Vysted must be categorically better
  on:** MCP-as-universal-tool-layer, the agent _assembling_ the cockpit, data correctness/provenance,
  and locale-native depth.
- **The edge (commit):** structured provider data (real filings/financials, **provenance on every
  number** — the gap Daloopa raised $47M to fix; structured grounding gives **[confirmed] up to
  71pp** retrieval-accuracy lift vs web-sourced) **fused with web context** in one cited brief, in a
  **terminal that builds itself**, **locale-native**, **local-first + BYOK + open-source**. The
  "near-superintelligent / anticipatory" feel = orchestrated sequencing of context-aware tool calls
  (brief already written, chart already set, filing already open).

---

## Pillar E — `/` slash + `@` mention command surfaces

- **Universal precedent (Cursor, OpenCode, Claude Code, Continue, Zed, Windsurf):** `/command`
  encodes **intent**, `@mention` encodes **scope**; both are inline fuzzy-autocomplete pickers, no
  modal. Commands resolve to markdown templates in a project-local folder; `$ARGUMENTS`/`$1` capture
  args. **[corrected]** Cursor's custom slash commands use **no** YAML frontmatter (Claude
  Code/OpenCode do). **[corrected]** OpenCode `@` is **overloaded** — file/context attach **and**
  subagent routing (not routing-only). **[corrected]** Continue's `@docs` is **deprecated** for
  Context7 MCP. **[corrected]** Bloomberg **ASKB ~125k beta** users (not 200k), validates the
  workflow-invocation pattern.
- **Recommended slash set (11):** `/research <q>` (flagship — full cockpit + brief), `/deep <q>`
  (deep mode), `/compare <a> <b> [c]`, `/chart <ticker> [tf] [ind…]`, `/screener <nl-criteria>`,
  `/watch <ticker> [note]` (locale-aware), `/portfolio`, `/layout <name>`, `/export [fmt]`,
  `/sources` (provenance panel — critical for BYOK trust), `/clear` (wipe convo + ephemeral panels,
  keep watchlist/portfolio).
- **Recommended `@` set (4 layers, 9 types):** instruments `@TICKER` / `@INDEX` (locale-aware,
  autocomplete from watchlist+recents then live search, shows `[exch: price chg%]`); surfaces
  `@chart` / `@news` / `@filings` / `@terminal`; scopes `@watchlist` / `@portfolio`; agents
  `@analyst` / `@quant` (sub-specialist routing, OpenCode pattern).
- **Grammar rule (non-negotiable):** `/cmd` + `@entity` are orthogonally composable
  (`/compare @AAPL @MSFT`). Never make tickers into slash commands.
- **Skip (clutter):** `/edit` `/refactor` `/explain` (coding idioms), sub-field mentions
  (`@volume`/`@pe`), `/alert` `/notify` (need a persistent notification service — defer).
- **Storage (if custom commands ship):** `.vysted/commands/*.md` (project) + `~/.vysted/commands/*.md`
  (global), frontmatter `{description, panels, locale, model, argument-hint}`.

---

## Pillar F — Multi-portfolio + the get_portfolio fix

- **State (Pass A.2.0):** the multi-portfolio store (`src/store/portfolios.ts`) is the source of
  truth — named portfolios, holdings `{symbol, quantity, costBasis, assetClass}`, persisted in the
  workspace blob. The fabricated `+107.69%` demo portfolio is gone.
- **The divergence (codebase-confirmed):** the agent's `get_portfolio` reads the **request-scoped
  context snapshot** (`agent_runtime.py:331`, `(terminal or {}).get("portfolio")`) — i.e. whatever
  the frontend published. The context-provider extracts only `positionCount` + `totalValue`
  (`context-provider.ts:69–73`), and **the portfolio panel does not yet publish its holdings to the
  panel-context bus** (`panel-context.ts`). So the agent's explicit portfolio read can be empty/thin
  vs the real UI portfolio. _(The Pass A.2.0 report framed this as "get_portfolio reads sidecar
  SQLite"; the live code reads the request snapshot — either way, the agent can answer from a
  portfolio that isn't the one on screen.)_
- **The fix (operator fork — see clarify):** make the agent read the **real multi-portfolio store**.
  Cleanest: the portfolio panel **publishes its active-portfolio holdings to the panel-context bus**
  → `context-provider` extracts the full holdings array → `get_portfolio` returns it. Zero
  divergence, single source of truth (the frontend store), no sidecar SQLite mirror. Alternatives:
  mirror manual holdings into sidecar SQLite too, or add a `/agent/portfolio` route.

---

## Codebase seams (confirmed clean — what Pass B touches)

**Sidecar:**

- `agent_tools/catalog.py` — **greenfield** for new tools: add `_cap(id=…, domain=…,
read_only=…, kind=…)` entries (add `research` + `indicators` to the `Domain` literal ~:34);
  auto-projects to `TOOL_SCHEMAS` + allow-list + MCP. Handlers in `agent_tools/<tool>.py`;
  wire `register()` in `registry_v0_6_0.py`.
- `provider_registry.py` — **~15-line refactor** to add `region: frozenset[str]` to
  `ProviderDeclaration` + thread a `region` param (default `"US"`) through `_candidates` /
  `_resolve_*` / public accessors; append an `nse` provider. Provenance already preserved.
- `config.py` — **add `get_region()`** (the one missing sidecar piece; frontend region setting
  already exists).
- `news_provider.py` (`_MARKET_RSS_FEEDS` → region-keyed dict), `screener.py` (region-keyed
  universe default; `nifty50.json` already ships), `macro/macro_router.py` (region param) — all
  small, data-shaped refactors.

**Frontend:**

- `lib/host-actions.ts` — add `set_chart_indicators` to `HOST_ACTION_NAMES` + describe/apply
  cases; extend `arrange_layout` with `template_name`. Routes through the existing diff/accept gate
  (`proposed-changes.ts`; orders hard-excluded at line ~79). `kind='chart'`/`'panel'` → obeys
  ASK/AUTO autonomy correctly with no gate change.
- `store/chart-command.ts` — add `selectedIndicators` + `setIndicators()` (mirrors `loadSymbol`);
  `ChartPanel.tsx:750–775` already publishes `activeIndicators` to the bus.
- `store/panel-context.ts` + `modules/chat/context-provider.ts` — **portfolio panel must publish
  holdings to the bus**; extend the extract to carry the holdings array → fixes `get_portfolio`.
- `modules/chat/ChatSidebar.tsx` + `slash-commands.ts` + `store/command-palette.ts` — the `/` parser
  - palette corpus are the seams for the Pass-B slash/@ surface (palette already fuzzy-ranks
    commands/panels/symbols/agents).
- `lib/region.ts` + `store/settings.ts` + `lib/format.ts` — region read seam; needs a **Settings UI
  region picker** + currency application in `formatMoney` (currently hardcoded USD).

---

## Open product decisions surfaced (→ clarify round)

1. **v1 locale scope** — US + India both deep, or US-first / +GLOBAL.
2. **India data default** — keyless (jugaad-data/Bhavcopy) pre-installed vs require a BYOK
   broker/EODHD key; yfinance India policy.
3. **get_portfolio fix approach** — publish store→bus (recommended) / mirror to SQLite / new route.
4. **Web-search default tier** — native-on-key + honest fallback (recommended) / require BYOK Exa /
   local-first; surface per-search cost.
5. **BYOK search default pick** — Exa (recommended) / Tavily / Linkup.
6. **Local Tier-3 search** — BYO SearXNG URL + autodetect (recommended v1) / Docker one-click / defer.
7. **Deep-research depth + trigger** — FAST default + `/deep` & "go deeper", rounds 3 / wall 120s
   (recommended) / always-ask / auto-detect by complexity.
8. **Perplexity Sonar deep backend** — optional opt-in (recommended) / native-only / defer.
9. **Research output layout** — research-cockpit template + brief as a dockview panel (recommended) /
   brief as a drawer; which templates ship.
10. **Slash/@ command set** — ship curated 11+9 (recommended); custom `.vysted/commands` v1 or v2;
    `@analyst`/`@quant` real sub-agents vs prompt-prefix routing.
11. **JARVIS posture v1** — prompt-driven assembly (recommended, lower failure surface) vs fully
    anticipatory pre-loading.
12. **Constitution amendment** — add a "Locale-Native & Correct, Everywhere" principle (locale-native
    - correctness-non-negotiable + resourcefulness/never-dead-end)? MINOR bump, operator-ratified.

_Recommendations are research-grounded defaults; the operator ratifies each at clarify._
