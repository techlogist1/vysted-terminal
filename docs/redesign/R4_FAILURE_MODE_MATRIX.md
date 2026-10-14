# Vysted R4 — Failure-Mode Matrix (per surface)

> **Status:** Spec — the per-surface state contract the build implements and the verification gate
> checks. Pairs with `R4_DESIGN_LANGUAGE.md` §6/§9 (the shared state primitives) and the master spec
> §2 (coherence) / §5 (graceful states everywhere).
> **Source:** the R4 recon interaction-states audit (`C6`) + the bug dossier (`C7`).
> **The rule R4 enforces:** _every interactive element and every data surface specifies — and visibly
> renders — its full state set._ A panel that silently shows `—` or a raw error is a defect, not a
> gap. **Market-session awareness is 0% covered today and is the single biggest hole.**

---

## 1. The state contract (the columns every surface answers)

**Interaction states (every interactive element):** `default · hover · active/pressed · focus-visible ·
disabled · loading`. (Specified in design doc §6; not repeated per-surface below.)

**Data-surface states (every panel that shows market/agent data):**

| State                | Definition                               | Required treatment                                                                                                                                                                           |
| -------------------- | ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **empty**            | no data yet / nothing configured         | `<EmptyState>` with a "try this" affordance where relevant — never a blank panel                                                                                                             |
| **loading**          | fetch in flight >300ms                   | `<Skeleton>` shimmer (house durations), not a blocking spinner                                                                                                                               |
| **error**            | fetch failed                             | `<ErrorState>` inline, near the cause, with a **recovery path** (Retry / what unlocks it) — never raw JSON, never color-only                                                                 |
| **stale**            | cache-served / after-hours / EOD         | `<StalenessBadge>` (`live·stale·eod`) — labeled, never shown as live                                                                                                                         |
| **paper/synthetic**  | non-live broker / simulated              | `<ProvenanceBadge>` (`paper·synthetic·mode·provider`) — FR-041/065                                                                                                                           |
| **market-closed**    | session not open for the symbol's locale | `<MarketClosedBadge>` — `Open · Pre-market · After-hours · Closed · last close @ <time>` (NEW, §3)                                                                                           |
| **symbol-not-found** | query didn't resolve                     | `<NotFoundState symbol>` — honest "couldn't resolve {symbol}; did you mean … / it may be newly-listed/delisted" + what would unlock it — never a silent `—`, never raw JSON (Principle VIII) |
| **disambiguation**   | resolved to >1 instrument                | a choice affordance (RELIANCE.NS vs .BO vs ADR), locale-ranked — never silently pick wrong (Pass-B edge case)                                                                                |

---

## 2. Master coverage matrix (current → R4 requirement)

`✅` covered · `◧` partial · `❌` missing/silent · `—` n/a. "R4" = must be covered after the build.

| Surface                                                 | empty           | loading     | error            | stale   | mkt-closed | not-found                   | R4 net-new work                                                                       |
| ------------------------------------------------------- | --------------- | ----------- | ---------------- | ------- | ---------- | --------------------------- | ------------------------------------------------------------------------------------- |
| **Agent composer / chat** (`ChatSidebar.tsx`)           | ✅              | ✅ stream   | ◧                | —       | —          | —                           | error recovery on send-fail; no-provider → onboarding (FR edge)                       |
| **⌘K palette** (`CommandPalette.tsx`)                   | ◧               | ◧ async     | ❌               | —       | —          | ◧                           | empty/zero-result state; async symbol-fetch loading; group headers                    |
| **Watchlist** (`WatchlistPanel.tsx`)                    | ✅ `333`        | ✅ skeleton | ✅ +Retry        | ◧ badge | ❌         | ❌ bad ticker → `—` forever | **mkt-closed badge; not-found affordance**                                            |
| **Chart** (`ChartPanel.tsx`)                            | ◧               | ✅          | ✅ (shows `502`) | ◧       | ❌         | ◧ empty-series→error        | **502→clean empty (C7 Bug-2); mkt-closed; date-crash guard (Bug-3)**                  |
| **Equity Overview** (`EquityOverviewPanel.tsx`)         | ✅ CTA chips    | ✅ skeleton | ✅ +Retry        | ◧       | ❌         | ✅ `348/600`                | **mkt-closed; the AI-narrative section (master §4.5)**                                |
| **News** (`NewsFeedPanel.tsx`)                          | ✅ +key hint    | ✅ skeleton | ✅ auto-retry×12 | ◧       | —          | —                           | sentiment empty handling on no-articles                                               |
| **Screener builder** (`ScreenerCriteriaBuilder.tsx`)    | ✅              | —           | ◧                | —       | —          | —                           | invalid-criterion inline validation; formula-error state (master §4.3)                |
| **Screener results** (`ScreenerResultsTable.tsx`)       | ✅ `267`        | ◧           | ❌               | —       | —          | —                           | **skip-ledger (C7/C3: 242/506 silent!); col-overlap fix (Bug-1); per-row stale**      |
| **Research brief** (`brief-blocks.tsx`/`BriefPanel`)    | ◧               | ✅ step-log | ◧                | ◧       | —          | —                           | **0-source floor message; mode-badge fix (S-6); sources-rail trust UX (master §4.4)** |
| **Notes** (`NotesPanel.tsx`)                            | ◧ textarea      | —           | ❌ save-fail     | —       | —          | —                           | save-error/`isSaving` state; rebuild as editor (master §4.2)                          |
| **Portfolio** (`portfolio`)                             | ✅ one-empty    | ✅          | ✅               | ◧ paper | ❌         | —                           | mkt-closed on positions; paper/synthetic badge parity                                 |
| **Macro** (`macro`)                                     | ✅ "No results" | ✅          | ◧                | ◧       | —          | ◧ series-not-found          | shared not-found                                                                      |
| **Quant / Backtest** (`quant`/`backtest`)               | ◧               | ✅          | ◧                | —       | —          | ◧                           | result-empty + compute-error states                                                   |
| **SEC filings** (`sec`)                                 | ◧               | ✅          | ◧                | —       | —          | ◧                           | no-filings + fetch-error                                                              |
| **Earnings** (`earnings`)                               | ◧               | ✅          | ◧                | ◧       | —          | ◧                           | no-earnings + stale                                                                   |
| **Analyst ratings** (`analyst-ratings`)                 | ◧               | ✅          | ◧                | —       | —          | ◧                           | no-coverage state                                                                     |
| **Settings** (`SettingsPanel.tsx`)                      | —               | ◧ models    | ◧ key-test       | —       | —          | —                           | model-list load/error; key-test feedback                                              |
| **First-run** (`OnboardingFlow.tsx`)                    | —               | ◧           | ◧                | —       | —          | —                           | **teach-the-agent state (master §5.1) — today teaches keys, not power**               |
| **Broker connect** (`broker-connect`)                   | ✅              | ✅          | ✅               | ◧ paper | —          | —                           | disconnected/expired-token state; paper badge                                         |
| **Marketplace / Plugin mgr** (`PluginManagerPanel.tsx`) | ✅              | ✅          | ◧                | —       | —          | —                           | install/enable/incompatible-version state                                             |
| **Proposed-changes bar** (`ProposedChangesReview.tsx`)  | —               | —           | ✅ re-pend       | —       | —          | —                           | apply-failure detail (exists); keep                                                   |
| **Agents rail** (`AgentDock.tsx`)                       | ✅              | ✅ run      | ✅               | —       | —          | —                           | budget-breach abort reason (FR-026); cost-so-far                                      |

**Systemic gaps R4 closes (the through-lines):**

1. **market-closed: 0% → covered** via the locale-aware session signal (§3) consumed by every
   price/quote surface.
2. **symbol-not-found: inconsistent → one shared `<NotFoundState>`** — watchlist's silent `—` is the
   worst offender (FR: never a dead `—`).
3. **no shared primitives → the §9 primitive set** so states are themed/specified once, not
   hand-rolled 20× (the biggest structural debt).
4. **silent skip-accounting → visible ledgers** — the screener dropping 242/506 with no surface is a
   correctness-of-presentation bug (Principle VIII): every skipped/failed item is itemized.

---

## 3. Market-session awareness (NEW subsystem — the load-bearing gap)

A grep found **no** market-open/closed/after-hours logic in `src/`. R4 adds a **locale-aware market
session signal** (US + India first-class, Principle VIII): given a symbol's exchange/locale, compute
`session ∈ {open, pre, after, closed}` + `last_close_at`. Every price/quote surface consumes it:

- `open` → no badge (live, optionally a quiet "live" dot).
- `pre`/`after` → `Pre-market` / `After-hours` badge; price labeled extended-hours.
- `closed` → `Market closed · last close <time, locale tz>` — a weekend/holiday price is **never**
  shown as if live.
- Combines with `<StalenessBadge>`: a cache-served close after hours is both `stale` and `closed`.

This is consumed by: chart, watchlist, equity-overview, portfolio, the research brief's price metric,
and any quote chip. IST for IN symbols, ET for US (locale-correct formatting, Principle VIII).

---

## 4. The four named bugs as failure-mode requirements (from C7)

These are the brief's explicit bugs, framed as states the matrix forbids:

| Bug                               | Current failure                                                                                                                                    | Root cause (file:line)                                                                                                                                   | R4 state requirement                                                                                                                                                | Visual proof                                                                                                                                                                                            |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Bug-1 screener column overlap** | header `<th>` collides → renders **"SECTOMARKET CAP"**; whole-table width budget unsound at narrow widths (672px fixed + 35% pct can't fit <700px) | `ScreenerResultsTable.tsx:313` (`<th>` has `whitespace-nowrap`, **no** `truncate/overflow-hidden`); fixed-px+% colgroup (`:161-178`, `table-fixed :305`) | a **responsive** table: every column truncates (`<th>` too); narrow panel **horizontal-scrolls** below a `min-width` threshold — columns never collide at any width | screenshot the **header row** at 1920×1080 **and** at a narrow (<700px) dockview split; SECTOR↔MARKET CAP must have a visible gap                                                                       |
| **Bug-2 "502 empty series"**      | a transient all-providers-empty history surfaces as a scary **HTTP 502** in the chart                                                              | `correctness_gate.py:100` raises on empty series → `app.py:247` maps `ProviderError`→502                                                                 | either a brief **retry/backoff** for transient empties, or downgrade all-empty→**clean 200-empty** so the chart shows "No price data" not "(502)"                   | stub provider `bars=[]`; assert `/history`→200-empty (or retry); chart shows the empty state                                                                                                            |
| **Bug-3 "date-change crash"**     | timeframe switch (there is **no** date picker) can throw a React error overlay                                                                     | `ChartPanel.tsx:672-674` unguarded `setVisibleRange({from,to})` under synced timeframe change; `:659` `!` non-null on a remounting series ref            | guard `setVisibleRange` (validate finite + `from<to`, try/catch); null-check `candleSeriesRef.current` instead of `!`                                               | Playwright **trusted events**: two synced charts, rapid 1d↔1m toggle, assert no error overlay (rig/chrome-devtools cannot inject these)                                                                 |
| **Bug-4 macOS Layout menu**       | (fixed in code R3)                                                                                                                                 | `lib.rs:325-338` `Builder::on_menu_event` (moved from `setup()`); `menu-bridge.ts:26-41`                                                                 | menu click switches dockview mode end-to-end                                                                                                                        | **native Computer Use / human click** of each of the 5 Layout items; app log shows `[menu] layout '<mode>' → emitted` + dockview re-arranges (rig/chrome-devtools cannot synthesize native menu clicks) |

---

## 5. Cross-cutting failure modes (app-level, not panel-level)

| Failure                                               | Required behavior                                                                                      | Anchor                                                                |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------- |
| **Sidecar not yet bound / connecting**                | shell shows a connecting state; data panels retry; never block boot or panic                           | edge-cases spec; boot `.expect()` already hardened (CURRENT_STATE §0) |
| **MCP cold-bind (~30s)**                              | MCP-backed features fall back / degrade; the shell stays usable                                        | CLAUDE.md deferred; `MCP_PORT_WAIT_SECS`                              |
| **No provider key configured**                        | first agent use routes to onboarding, never silent-fails against an absent local model                 | FR (US1 edge); `ChatSidebar.tsx:324` `requiresKey`                    |
| **Kill-switch active / read-only / paper**            | any order proposal is **blocked + explained**; the surface goes _still + red_ (no glow, design doc §5) | §6.5; FR-011/012                                                      |
| **Yahoo rate-limit (429) mid-fetch**                  | per-symbol timeout fails _fast_ (6–8s not 30s) + retry-with-jitter; **skip is itemized, never silent** | C3 perf fix; `screener.py:387`                                        |
| **Model swapped mid-conversation**                    | conversation context preserved (agent path already does; raw-chat path must too — FR)                  | C4; `ChatSidebar.tsx:574`                                             |
| **Deep-research budget exhausted mid-loop**           | abort→**synthesize immediately** from gathered context with a stated reason; never a bare timeout      | FR-072; BudgetGuard                                                   |
| **Symbol resolves to multiple instruments**           | locale-rank; below confidence threshold → **disambiguation choice**, never silently wrong              | Pass-B edge; `symbol_resolver.py`                                     |
| **All data sources fail for a symbol**                | honest "unavailable + what would unlock it"; never raw JSON, never a fabricated value                  | Principle VIII; FR-062                                                |
| **Workspace blob from older version / unknown panel** | restore skips to bundled default, never corrupts the grid (preserve current guard)                     | `workspace.ts:372-381`                                                |

---

## 6. Acceptance (how the gate proves the matrix is satisfied)

- A scripted pass drives **each surface** in the master matrix into each of its required states and a
  **Quartz screenshot** captures the rendered pixels (DOM assertion insufficient — design doc §12).
- **market-closed** is demonstrated on a weekend/after-hours capture for chart + watchlist +
  equity-overview (US and IN symbol).
- **symbol-not-found** is demonstrated by entering a bad ticker into the watchlist and the chart →
  `<NotFoundState>`, not `—`/`502`.
- The four named bugs each have the visual proof in their row (§4) saved as evidence.
- The screener returns a **skip ledger** (`N ok · M skipped: x delisted, y timeout`) — never a silent
  drop — on a full S&P 500 run.
