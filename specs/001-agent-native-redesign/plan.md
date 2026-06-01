# Implementation Plan: Pass B — Agent-Native Research Layer

**Branch**: `001-agent-native-redesign` | **Date**: 2026-06-01 | **Spec**:
[`spec.md`](./spec.md) (Pass-B stories US11–US17, FR-060–FR-111, SC-016–SC-025) | **Research**:
[`docs/redesign/PASS_B_RESEARCH.md`](../../docs/redesign/PASS_B_RESEARCH.md)

> **Status:** phased plan for operator review. **No implementation in this window.** The build is a
> separate, operator-initiated window. `tasks.md` (the granular `/speckit-tasks` breakdown) is the first
> step of that build window, per phase — it is **not** produced here.

## Summary

Pass B turns Vysted Terminal into a BYOK, local-first, agent-native competitor to Perplexity Finance —
better because the agent ("JARVIS") **builds the research workspace**. Six pillars: (A) locale-native
data + symbol resolution + multi-source fallback, (B) fast + deep research with the B+A output (a
composed cockpit **and** a synthesized cited brief), (C) three-tier web search (native / BYOK / local),
(D) JARVIS capability-completeness + smart-arrangement + resourcefulness, (E) `/` and `@` commands, (F)
multi-portfolio truth (the `get_portfolio` fix). The technical approach **piggybacks the four Pass-A
seams** (capability catalog, provider registry, model registry, region) + the Pass-A.2.0 multi-portfolio
store + the JARVIS host-actions/autonomy — extending them by **config + adapters**, not rebuilds.

## Technical Context

**Language/Version**: Python 3.13 (sidecar), TypeScript strict + React 19 / Next.js 16 static export
(frontend), Rust (Tauri 2.x core — **not touched** by Pass B). **Primary Dependencies**: FastAPI,
dockview, lightweight-charts v5.2.0, Zustand, Framer Motion; new (build-time): an India data lib
(jugaad-data / nsepython), a resolver (bundled NSE/BSE + SEC masters + Twelve Data/yfinance search), Exa
SDK (BYOK), SearXNG (external/local). **Storage**: sidecar SQLite (`data_cache`, `runs_store`) + the
workspace blob; **no new persistence model**. **Testing**: pytest (sidecar), vitest (frontend), the
tauri-mcp rig (live app), `pnpm ci-local` + `smoke-test-sidecars.mjs` (pre-tag). **Target Platform**:
Tauri desktop (Win/macOS/Linux). **Project Type**: desktop app (Rust core + Next.js UI + Python
sidecar). **Performance Goals**: fast research ≤15s typical (SC-018); deep research budget-bounded
(rounds 3 / wall 120s, SC-021). **Constraints**: local-first, BYOK, loopback-only; **§6.5 + Tier-1
LOCKED files byte-for-byte untouched**; correctness-non-negotiable (never wrong data).

## Constitution Check

_GATE: passes. Re-check after each phase._

- **I. Agent at the center / hands on the wheel** — Pass B deepens it (research builds the cockpit;
  every capability stays hand-reachable, FR-090). ✅
- **II. One capability catalog, many consumers** — all new tools (resolve_symbol, set_chart_indicators,
  compare, research, deep_research) register **once** in `catalog.py` and auto-project to copilot + MCP
  (FR-090/020). ✅
- **III. Safety layered & non-negotiable** — every Pass-B mutation rides the diff/accept gate; AUTO only
  for UI/layout/chart/watchlist; orders never auto-apply; deep-research spend bounded by BudgetGuard
  (FR-072/094, SC-025). §6.5 untouched. ✅
- **IV. Local-first, BYOK, private** — search tiers ride the user's own keys; local tier keeps data on
  the machine; secrets in the keychain (FR-080–084). ✅
- **V. Extensible by contract** — data sources + search backends are marketplace plugins under the one
  extension model (FR-064/080); `types/plugin.ts` untouched. ✅
- **VI. Verification is the product** — provenance on every value, citations on every web claim, brief
  step-logged (FR-065/074/075). ✅
- **VII. Minimal-dark, density + progressive disclosure** — `/@` surface + brief panel honor the
  keyboard-first, panel-composable model (FR-100/074). ✅
- **VIII. Locale-Native & Correct, Everywhere** _(new, v1.1.0)_ — the McDonald's principle + correctness
  gate + never-dead-end are the spine of Phases B1/B2 (FR-060–065/093). ✅

**No Locked decision is reversed; no Tier-1 LOCKED file is touched.** Any pillar that appears to require
touching a LOCKED file is a stop-and-surface (none identified — all seams are host-side / catalog /
provider-registry, confirmed by `PASS_B_RESEARCH.md` §"Codebase seams").

## Safety invariant (applies to EVERY phase — hard gate)

Before each phase merges, the audit must hold: §6.5 `test_safety_end_to_end.py` **9/9**; `types/plugin.ts`,
`types/safety.ts`, `types/broker.ts`, the safety/broker/audit/kill-switch models, `broker_base.py`,
`kill_switch.rs`, `tauri.conf.json`, CI — **byte-for-byte untouched** (git diff empty); no
`place_/submit_/execute_order` or `auto_approve` introduced (grep); brokers stay read-only; the rig stays
dev-only. A phase that would breach this **stops and surfaces** to the operator.

## Phase plan (6 phases — each independently rig-verifiable, with a gate)

Order is dependency-correct: data correctness first (everything rests on it), then the cockpit-building
substrate, then search, then the research engine that composes them, then the command UX, then the
portfolio fix + hardening. Each phase ships full-scope (no "phase 2" TODOs) and is gated on the rig +
`ci-local`.

### Phase B1 — Locale-native data foundation (Pillar A) · US11

**Goal:** correct, locale-shaped, never-wrong data with multi-source fallback — GOLDBEES/Tata Steel work
for an IN user; US data is unaffected.

**Covers:** FR-060–FR-065 · SC-017, SC-019 (partial).

**Seams / work:**

- `sidecar/config.py` — add `get_region()` (the one missing sidecar piece; reads the region the frontend
  already sends in the context snapshot / a settings value).
- `sidecar/services/provider_registry.py` (~lines 98–231) — add `region: frozenset[str]` to
  `ProviderDeclaration`; thread a `region` param (default `"US"`) through `_candidates`/`_resolve_*`/the
  public accessors; preserve provenance + fall-through-on-`ProviderError` (already present).
- **New** `sidecar/services/india_provider.py` — keyless jugaad-data / NSE-Bhavcopy adapter
  (`get_quote`/`get_history`/`get_fundamentals`, `provider="nse"`, INR/IST aware), declared
  `region={"IN"}`, rank above gated yfinance for IN. Ships as a **pre-installed data plugin** (FR-064).
- **New** symbol-resolution layer — bundled NSE/BSE + SEC `company_tickers.json` masters + a keyless live
  lookup (Twelve Data `/symbol_search` → yfinance.Search), locale-ranked, cached; a `resolve_symbol`
  capability (catalog, read-only).
- **New** correctness gate — reject empty/non-positive/stale/mismatched responses (exchange-calendar
  aware) → advance to next provider; stale/synthetic labeled (FR-063/041). yfinance gated for `.NS`/`.BO`.
- `news_provider.py` (`_MARKET_RSS_FEEDS` → region-keyed dict incl. ET/LiveMint), `screener.py`
  (region default: IN→nifty50, already ships), `macro/macro_router.py` (region param) — region-key the
  supporting tables.
- `src/lib/format.ts` — apply `regionConfig(region).currency` (currently hardcoded USD); `src/store/settings.ts`
  — surface a Settings region picker.

**Gate (rig + tests):** with region=IN, the basket {GOLDBEES, TATASTEEL, NIFTYBEES, RELIANCE} loads
correct quotes/history from a locale source (or an honest "unavailable + why"); with region=US, {AAPL,
MSFT, SPY} unaffected; every value carries provenance; **0 raw-JSON dead-ends, 0 wrong/stale-as-live**
(SC-017/019). pytest (registry/resolver/gate) green; `ci-local` green; sidecar smoke-test green;
**§6.5 audit 9/9, Tier-1 LOCKED diff empty**.

### Phase B2 — JARVIS capability completeness + smart arrangement (Pillar D) · US15

**Goal:** the agent can do every obvious action by name, arranges a thoughtful cockpit on its own (not
one tile), and is resourceful (never dead-ends — wired to B1 fallback).

**Covers:** FR-090–FR-094 · SC-016 (arrangement), SC-022, SC-025.

**Seams / work:**

- `sidecar/services/agent_tools/catalog.py` — add capabilities: `set_chart_indicators`, `compare_symbols`,
  `resolve_symbol` (B1), and confirm completeness for arrange/close/focus/timeframe/fundamentals/filings/
  news/portfolio (most exist). Add `indicators` domain if missing. Handlers + `registry_v0_6_0.py` wiring.
  Auto-projects to TOOL_SCHEMAS + allow-list + MCP (FR-090/020).
- `src/lib/host-actions.ts` — add `set_chart_indicators` to `HOST_ACTION_NAMES` + describe/apply cases;
  extend `arrange_layout` with **named templates** (`template_name`: single-focus / research-cockpit /
  compare / macro-scan) → real dockview re-tiling honoring the primary-vs-rail placement policy.
- `src/store/chart-command.ts` — add `selectedIndicators` + `setIndicators(symbol, keys)` (mirrors
  `loadSymbol`); `ChartPanel` reports selected indicators back to the store for the before-diff.
- **Default-indicator presets** per asset class (equity daily SMA50/200+vol+RSI14; intraday EMA9/21+
  session-VWAP locale-anchored; ETF +RS-line; crypto EMA50/200+week-VWAP+RSI, OI/funding if feed) —
  server-computed indicators pushed down the chart-command channel; canvas palette from `chart-theme.ts`.
- **Resourcefulness:** the agent surfaces B1's honest-unavailable message (never raw JSON) on total
  failure; arrange picks a template by query intent.

**Gate (rig):** capability-completeness audit (every enumerated action reachable by agent **and** hand,
SC-022); "set up NVDA" → research-cockpit template with default indicators (not one tile, SC-016);
GOLDBEES handled by fallthrough/honest message (no raw JSON); every mutation gated, orders never
auto-apply, §6.5 9/9 (SC-025). vitest (host-actions/chart-command) + pytest (catalog parity) green.

### Phase B3 — Web search, three tiers of freedom (Pillar C) · US14

**Goal:** grounded web search on the user's own key by default; honest fallback; BYOK + local tiers.

**Covers:** FR-080–FR-084 · SC-020.

**Seams / work:**

- **Search-backend interface** (a marketplace search-source plugin shape): `search(query, options) →
{results:[{url,title,snippet,publishedAt}], citations:[]}` — the agent calls this, never a vendor SDK.
- **Native tier dispatch** in the agent runtime: detect the active provider's native web search
  (Anthropic `web_search` / OpenAI Responses `web_search` / Gemini `google_search` / xAI Live Search /
  Groq Compound), ride the user's existing key, **normalize all citation shapes** to `{url,title,excerpt}`,
  enforce a **per-run search cap**. Pass `user_location` from the region setting.
- **Honest fallback:** DeepSeek / local Ollama / bare Qwen-Llama → prompt the user + route to a configured
  BYOK/local backend; never silent-fail or fabricate (FR-082).
- **BYOK tier:** ship **Exa** as the default backend plugin (finance/news categories, locale-aware domain
  allow-lists US vs IN); Tavily/Linkup as alternates. Key in the keychain.
- **Local tier:** SearXNG plugin — autodetect `localhost:8080` + a configurable URL (no bundling).
- Gemini ToS: render the Search-Suggestions entry-point when displaying grounding.

**Gate (rig):** with a native-capable model, a grounded query returns normalized citations on the user's
key (cost-cap honored); with a non-native model, an honest prompt + the configured backend runs; locale
domain preferences apply; local tier keeps data on-machine — **0 silent failures, 0 fabricated context**
(SC-020). vitest (citation normalizer / dispatch) green; **§6.5 audit 9/9, Tier-1 LOCKED diff empty**.

### Phase B4 — Research engine: fast + deep + B+A output (Pillar B) · US12, US13

**Goal:** "research X" composes a coherent cockpit + a synthesized cited brief; "go deeper" runs a
bounded multi-round loop. (Depends on B1 data, B2 arrange/indicators, B3 search.)

**Covers:** FR-070–FR-075 · SC-016 (brief), SC-018, SC-019, SC-021.

**Seams / work:**

- **Fast loop** (dexter-shaped Plan→Action→Validate→Answer, single pass): resolve → parallel structured
  pull (price/fundamentals/filings/news via existing catalog handlers) → one web round (B3) → synthesis →
  `arrange_layout('research-cockpit')` + `set_chart_indicators` (B2) + a **BriefPanel**. Target ≤15s.
  New `research` capability (catalog, read-only).
- **Deep loop** (LangGraph-style, opt-in `/deep` + "go deeper"): plan → parallel researchers (≤3) →
  compress → reflect → re-enter or final; coverage floor (≥1 source each: price/fundamentals/news/web);
  **bounded by BudgetGuard** (rounds 3/max 5, wall 120s/max 300s) — first breach **abort→synthesize**
  (FlashResearch pattern), never a bare timeout. Reuse `run_manager`/`runs_store`/`budget_guard`.
- **BYOK deep backend:** Perplexity `sonar-deep-research` as an **opt-in-per-run** path (keychain key,
  estimated cost shown first, never auto-selected; citations "via Perplexity").
- **BriefPanel** (new dockview panel + companion): markdown body with inline `[n]` citation chips → a
  collapsible sources tray (favicon/title/domain/snippet) + a metadata header (mode FAST|DEEP, source
  count, cost) + a dev **step-log tray**. Step records persist to `runs_store` (a `steps` column).

**Gate (rig):** "research NVDA" → research-cockpit cockpit + a BriefPanel with ≥3 cited sources, every
structured number provenance-tagged, in ≤15s (SC-016/018/019); a deep run satisfies coverage **or** aborts
at budget and **still** synthesizes a brief (SC-021); the Perplexity path is opt-in + cost-shown. pytest
(loops/budget) + vitest (BriefPanel) green.

### Phase B5 — `/` and `@` command surface (Pillar E) · US16

**Goal:** a clean, fast slash + mention grammar in the agent panel.

**Covers:** FR-100–FR-102 · SC-023.

**Seams / work:**

- `src/modules/chat/slash-commands.ts` + `ChatSidebar.tsx` — the curated slash set (`/research /deep
/compare /chart /screener /watch /portfolio /layout /export /sources /clear`), each dispatching to the
  B2/B4 capabilities (mutations still ride the diff/accept gate).
- **@-mention surface** (inline fuzzy picker): instruments `@TICKER`/`@INDEX` (locale-aware via B1 resolver,
  showing `[exchange: price chg%]`), surfaces `@chart`/`@news`/`@filings`/`@terminal`, scopes
  `@watchlist`/`@portfolio`, sub-specialists `@analyst`/`@quant` (prompt-prefix routing to existing
  personas in v1). Reuse `command-palette.ts` fuzzy ranking + the corpus builder.
- Composition: `/cmd @entity` resolves intent + scope together; a ticker is never a slash command.

**Gate (rig):** `/` picker fuzzy + keyboard-nav, each command executes; `@TICKER` resolves locale-aware to
the correct instrument and injects context; `@panel`/`@scope` inject correctly; `/compare @AAPL @MSFT`
composes (SC-023). vitest (parser/picker) green; **§6.5 audit 9/9, Tier-1 LOCKED diff empty**.

### Phase B6 — Multi-portfolio truth + polish + verification (Pillar F + cross-cutting) · US17

**Goal:** the agent reads the real portfolio; final hardening; full SC verification.

**Covers:** FR-110, FR-111 · SC-024; final sweep of SC-016–SC-025.

**Seams / work:**

- **`get_portfolio` fix (ratified approach):** the **portfolio panel publishes its active-portfolio
  holdings to the panel-context bus** (`src/store/panel-context.ts` — mirror `ChartPanel`'s publish);
  `src/modules/chat/context-provider.ts` extends the extract to carry the full holdings array;
  `get_portfolio` (`agent_runtime.py`) returns the active portfolio from the real store
  (`src/store/portfolios.ts`). No sidecar SQLite mirror. Switch/create/edit → agent read follows.
- **Polish:** empty/loading/error states for every new surface (BriefPanel, search config, resolver
  disambiguation); reduced-motion; locale currency everywhere; staleness/provenance badges.
- **Verification:** full rig pass of SC-016–SC-025 with **populated** state at 1920×1080 + 2560×1440;
  `pnpm ci-local` + `smoke-test-sidecars.mjs` green; §6.5 audit 9/9; Tier-1 LOCKED diff empty.

**Gate (rig):** with ≥2 portfolios, the agent's portfolio read **equals** the active UI portfolio across
create/switch/edit, **0 divergence** (SC-024); the full Pass-B SC suite passes on the live app; all hard
gates green.

## Phasing notes & dependencies

```
B1 (data) ──► B2 (capabilities/arrange) ──► B4 (research) ──► B5 (/@ commands) ──► B6 (portfolio + polish)
                         ▲                      ▲
                         └──────── B3 (search) ─┘   (B3 can run in parallel with B2; B4 needs both)
```

- **B1 is the prerequisite for everything** (correct data). **B3 (search)** can be built in parallel with
  **B2 (capabilities)**; **B4 (research)** needs B1 + B2 + B3. **B5** needs B2 + B4. **B6** is independent
  (the portfolio fix) + the closing verification.
- Each phase is **full-scope** (no half-ships), **rig-verifiable**, and gated on `ci-local` + the §6.5
  audit. The lead (Opus) owns the catalog/host-action/safety-adjacent work and reviews every diff; Sonnet
  for mechanical JSX/tokens/boilerplate; Haiku for high-volume scanning (per CLAUDE.md model assignment).
- **`tasks.md`** (the granular `/speckit-tasks` breakdown) is generated **per phase at build time**, not
  in this window.

## Project Structure (artifacts this feature adds)

```text
specs/001-agent-native-redesign/
├── spec.md          # extended this window (Pass B: US11–17, FR-060–111, SC-016–025)
├── plan.md          # this file
└── tasks.md         # NOT created here — first step of the build window, per phase

docs/redesign/
├── PASS_B_RESEARCH.md        # 42-agent verified grounding (data/search/research/indicators/commands)
├── PASS_B_BUILD_HANDOFF.md   # fresh-window kickoff (this window)
└── PASS_B_TELEMETRY.md       # running agent/phase tally

sidecar/  (Pass-B additions — config + adapters, no refactor of the seam shape)
├── config.py                         # + get_region()
├── services/provider_registry.py     # + region field/param (~15 lines)
├── services/india_provider.py        # NEW — keyless NSE/BSE adapter
├── services/symbol_resolver.py       # NEW — resolver + masters + correctness gate
├── services/agent_tools/             # + resolve_symbol, set_chart_indicators, compare, research, deep_research
└── services/research/                # NEW — fast + deep loops, BriefPanel payloads, step log

src/  (frontend Pass-B additions)
├── lib/host-actions.ts               # + set_chart_indicators, arrange_layout named templates
├── store/chart-command.ts            # + selectedIndicators / setIndicators
├── store/panel-context.ts            # portfolio panel publishes holdings (get_portfolio fix)
├── modules/research/BriefPanel.tsx   # NEW — cited brief panel
├── modules/chat/                     # + slash set, @-mention surface
└── lib/search/                       # NEW — search-backend interface + native dispatch + Exa/SearXNG plugins
```

**Structure Decision:** Pass B is **additive** to the existing three-process desktop app — config +
adapters + new catalog capabilities + new panels/host-actions. No layer-model change, no sidecar-boundary
change, no LOCKED-file change. This is the `EXTENSION_SEAMS.md` thesis realized: plug in via config + an
adapter, not a refactor.

## Complexity Tracking

_No constitution violations. No new project, no new persistence model, no LOCKED-file change._ The one
non-trivial new dependency surface is the India data lib + the resolver masters (build-time bundle size +
the keyless-source reliability caveat in `PASS_B_RESEARCH.md` §A) — mitigated by the correctness gate
(FR-063) and the preference-ordered fallback (FR-062). The crypto OI/funding sub-panes (FR-092) degrade
gracefully if no derivatives feed is configured.
