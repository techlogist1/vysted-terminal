# R15 Stage C: Batch 7 Plan (3 highs, 49 mediums, 3 class-mate lows; 0 proposed not-a-defect)

- **Base:** branch `004-r4-experience-rebuild` at `1a19d26c6297bc48521913ba333d81b9b4ecf9f5` (batch 6 merged at `5e14731`, the quant-pool leak fix `831d52b`, the batch-7 adjudication `1a19d26`). D81 is merged: nothing here re-adds trading, orders, brokers or a paper account.
- **Author:** batch planner (Opus). Every row below was written after opening the code it names at this base. Mechanisms follow the corrected verdicts (batch-6 not-certified notes, refuter corrections), not the raw claims. Line numbers are at base.
- **Queue at base:** 0 critical, 6 high, 194 medium, 208 low.
- **Selection: 55 entries in 5 writer sets.**
  - **38 carried from batch 6.** Batch 6 planned 60 and delivered 22 because the 3-minute stall watchdog killed its agents (run-state L26). Its plan's mechanisms were re-confirmed here at `1a19d26`; where the code moved (AGENT-046's per-turn mint, RESEARCH-024's runtime half, DATA-090's `.bak`, UI-036's per-row badge) the residual is stated instead.
  - **Highs.** 3 of the 6 open highs are taken: `DATA-014`, `DATA-027`, `AGENT-023`. The other 3 are in §4 (funded live lanes; packaged cold launch).
  - **New this batch (17):** `LEAD-005`; `AGENT-074` (low); `UI-031` + `CODE-FRONTEND-017` + `UI-026`; `CODE-FRONTEND-019` + `DATA-090` + `UI-046`; `RESEARCH-033` (low) + `RESEARCH-038` (low); `AGENT-044` + `AGENT-045`; `UI-017`; `UI-034` + `UI-035` + `UI-036` + `UI-037`. Every entry taken is in the four named areas except `CODE-PLATFORM-018` (verify-only) and `CODE-PLATFORM-021` (the last open member of the certified write-only-ledger class).
  - **Why 55, not 60.** Five writers at about 11 entries is the capacity batches 2 to 5 proved (40/40, 38/40, 45/52, 48/58). The next candidates in the named areas each collide with a file a set here owns (§4).
- **Class rule.** A class is a shared root cause, not a shared label. Taken together:
  - `DATA-014` + `DATA-027` + `DATA-076`: no independent India witness; Yahoo is checked against Yahoo. `LEAD-004` rides the same exchange lane (cadence from filed periods).
  - `DATA-050` + `DATA-060`: out-of-coverage reported as a 502 upstream failure.
  - `AGENT-035` + `LIFECYCLE-013`: provider and model never persisted for a resume.
  - `AGENT-037` + `AGENT-038`: the breach flag is decoupled from loop control. `AGENT-074` (low) is the same `on_round_usage` callback (it drops the resolved provider), taken so that contract changes once.
  - `RESEARCH-019` + `DATA-075` + `RESEARCH-033` (low): research fetch/explorer failures are filtered out instead of becoming error steps.
  - `RESEARCH-022` + `RESEARCH-023`: one marker list does two jobs. `RESEARCH-038` (low) is the same breaker-accounting block (`record_failure` per attempt), which 022's new failure path would otherwise make worse.
  - `RESEARCH-024` + `UI-038`: the source contract drops the date and overloads `domain`.
  - `AGENT-044` + `AGENT-045`: a model-supplied symbol bypasses the one resolution policy.
  - `UI-031` + `CODE-FRONTEND-017` + `UI-026`: a response for a superseded request is committed (no request generation / candidates not tied to their query).
  - `UI-034` + `UI-035`: the portfolio edit/delete target is stale after a portfolio switch.
  - `CODE-FRONTEND-019` + `DATA-090` + `UI-046`: workspace persistence failures and reserved names are masked (one file pair, `workspace.ts` / `workspace_store.py`).
- **Label-mates not taken (different root cause):** `AGENT-049` (native-search metering), `CODE-PLATFORM-057`/`-066` (keychain sleep; code-node CPU bounds), `UI-024` (notes editor), `DATA-111`/`RESEARCH-039` (parser drift canary; impersonate lane drops a 429), `AGENT-078` (layout rAF), `UI-028` (Greeks units).
- **proposed_not_defect:** none. `CODE-PLATFORM-018` is not "not a defect": its fix already landed on base (`831d52b`); it is listed under W3 as verify-only so the verifier certifies it.
- **Models:** all five sets are opus. Each carries a data-provider, runtime, persistence, research-funnel or agent-write judgement.

---

## 0. The 55 entries

| # | Entry | Sev | Root-cause class | Writer |
|---|---|---|---|---|
| 1 | R15-DATA-014 | high | residual DAL leg: the only revenue witness is Yahoo's own statement | W1 |
| 2 | R15-DATA-027 | high | no exchange-filed IN fundamentals lane; yfinance is the de-facto primary | W1 |
| 3 | R15-DATA-076 | med | growth check is Yahoo against Yahoo | W1 |
| 4 | R15-LEAD-004 | med | TTM "half-yearly" label counts Yahoo columns, not the filing cadence | W1 |
| 5 | R15-LEAD-015 | med | quarterly gap unmarked; annual labels year (yfinance) vs ISO (openbb) | W1 |
| 6 | R15-DATA-050 | med | results calendar NSE-only; BSE-only/SME name gets 502 | W1 |
| 7 | R15-DATA-060 | med | non-Indian instrument gets 502; no ADR 20-F ownership lane | W1 |
| 8 | R15-LEAD-005 | med | yfinance `get_quote` stamps `timestamp=_utcnow()` | W1 |
| 9 | R15-CODE-AGENT-010 | med | no run state machine | W2 |
| 10 | R15-AGENT-034 | med | empty budget box becomes no ceiling; no server floor | W2 |
| 11 | R15-AGENT-037 | med | breach flag cannot stop tool dispatch or the next request | W2 |
| 12 | R15-AGENT-038 | med | a completed final round touching a ceiling is recorded as error | W2 |
| 13 | R15-AGENT-074 | low | `on_round_usage` prices with the requested, not the resolved, provider | W2 |
| 14 | R15-AGENT-036 | med | checkpoint invariant broken by its own writer | W2 |
| 15 | R15-AGENT-035 | med | resume/answer run with provider, model and key all None | W2 |
| 16 | R15-LIFECYCLE-013 | med | same root (live: Ollama model swapped on resume) | W2 |
| 17 | R15-LIFECYCLE-012 | med | no startup reconciliation; checkpoint only at exit | W2 |
| 18 | R15-UI-040 | med | client store decides which runs exist; cancel optimistic | W2 |
| 19 | R15-CODE-AGENT-011 | med | pause/answer plane has no trigger | W2 |
| 20 | R15-AGENT-039 | med | delegate runs with no plan and no activity stream | W2 |
| 21 | R15-AGENT-046 | med | residual: minted ids unique per turn only; a late ack grounds a later run | W2 |
| 22 | R15-AGENT-023 | high | no scheduler, trigger or outbound action | W3 |
| 23 | R15-CODE-PLATFORM-018 | med | **verify-only**: fixed on base at `bdc7f0e` + `831d52b` | W3 |
| 24 | R15-UI-020 | med | drawings keyed by panel only; chart state not persisted | W3 |
| 25 | R15-UI-022 | med | drawing input side half-built (snap to close, off-bar, Text, dead Lock) | W3 |
| 26 | R15-UI-023 | med | indicator series race the price load; catch never clears | W3 |
| 27 | R15-UI-031 | med | Equity Overview `doLoad` has no sequence guard | W3 |
| 28 | R15-CODE-FRONTEND-017 | med | SEC/earnings stores commit a stale response | W3 |
| 29 | R15-UI-026 | med | watchlist rows are a fetch snapshot; Enter takes a stale candidate | W3 |
| 30 | R15-CODE-FRONTEND-019 | med | autosave ignores non-2xx and swallows errors | W3 |
| 31 | R15-DATA-090 | med | corrupt workspace read as missing, then overwritten (and `.bak` takes the corrupt copy) | W3 |
| 32 | R15-UI-046 | med | reserved `__autosave__` listed and `__` names accepted | W3 |
| 33 | R15-RESEARCH-019 | med | visit failures collapse to None, no step | W4 |
| 34 | R15-DATA-075 | med | BSE PDF gets one attempt, no AttachHis | W4 |
| 35 | R15-RESEARCH-033 | low | a crashed ULTRA explorer is dropped with no step | W4 |
| 36 | R15-RESEARCH-020 | med | result cap hand-copied into 4 backends; SearXNG ignores `numResults` | W4 |
| 37 | R15-RESEARCH-021 | med | KSE index-tail regex eats "TICKER 200 DMA" | W4 |
| 38 | R15-RESEARCH-022 | med | block page recorded as success before filtering | W4 |
| 39 | R15-RESEARCH-023 | med | footer markers applied per SERP result | W4 |
| 40 | R15-RESEARCH-038 | low | failure recorded per attempt, so one bad search benches DDG | W4 |
| 41 | R15-RESEARCH-024 | med | residual C4 half: Citation/web rows carry no `domain`/`published_at` | W4 |
| 42 | R15-UI-038 | med | `domain` carries "host (via Sonar)"; `hostOf` prefers it | W4 |
| 43 | R15-UI-092 | med | out-of-range citation markers deleted, not flagged | W4 |
| 44 | R15-RESEARCH-026 | med | brief has a shadow money formatter | W4 |
| 45 | R15-AGENT-043 | med | a malformed screener leaf is silently dropped | W5 |
| 46 | R15-AGENT-041 | med | no pre-image, no undo; applied rows vanish | W5 |
| 47 | R15-AGENT-032 | med | transcript writes "Applied:" before the outcome | W5 |
| 48 | R15-UI-017 | med | missing key leaves an orphaned user turn | W5 |
| 49 | R15-CODE-PLATFORM-021 | med | residual: sidecar POST/PUT/DELETE ledger routes still live | W5 |
| 50 | R15-AGENT-044 | med | `add_to_watchlist` adds whatever the model invents | W5 |
| 51 | R15-AGENT-045 | med | `compare_symbols` never resolves a guessed ticker | W5 |
| 52 | R15-UI-034 | med | edit survives a portfolio switch; Save writes nothing | W5 |
| 53 | R15-UI-035 | med | memoised columns close over the first portfolio's delete | W5 |
| 54 | R15-UI-036 | med | residual: prices fetched once, no refresh; totals have no as-of | W5 |
| 55 | R15-UI-037 | med | "Cost basis" never says per share | W5 |

---

## 1. File ownership: five disjoint sets

Each file belongs to exactly one writer. A change needed in another writer's file is not made: it goes to `issues[]` with the exact line. "Import only" means read the symbol, never edit the file.

| Writer | Model | Source files | Tests |
|---|---|---|---|
| **W1 `india-exchange-data`** | opus | new `sidecar/services/exchange_financials.py`, new `sidecar/services/sec_ownership.py`, `services/nse_provider.py`, `bse_provider.py`, `corporate_disclosures.py`, `correctness_gate.py`, `growth_check.py`, `yfinance_provider.py`, `openbb_mcp_provider.py` (period labels only), `provider_registry.py`, `routers/disclosures.py`, `routers/fundamentals.py`, `services/agent_tools/disclosure_tools.py`, `services/agent_tools/fundamentals.py` (one overlay call only; see C9), `sidecar/models/announcements.py`, `models/fundamentals.py`, `models/market.py` (only if LEAD-005 needs a nullable time), **`sidecar/models/__init__.py` (sole)**, **`types/data.ts` (sole)** | `test_nse_provider.py`, `test_bse_provider.py`, `test_corporate_disclosures.py`, `test_disclosures*.py`, `test_disclosure_tools.py`, `test_correctness_gate.py`, `test_fundamentals.py`, `test_fundamentals_tool.py`, `test_growth_check*.py`, `test_provider_registry*.py`, `test_yfinance*.py`, new `test_b7_exchange_*.py`, fixtures under `sidecar/tests/fixtures/{nse,bse,sec}/` (add only) |
| **W2 `delegate-runs-runtime`** | opus | `services/run_manager.py`, `runs_store.py`, `budget_guard.py`, `routers/runs.py`, `models/run.py`, **`services/agent_runtime.py` (sole)**, `services/action_ledger.py`, **`services/agent_tools/catalog.py` (sole)**, `sidecar/agents/*.json` (`ask_user` allow-list only), `src/lib/delegate-runs.ts`, `src/store/agent-runs.ts`, `src/modules/chat/AgentsRail.tsx`, `src/modules/chat/BudgetConfig.tsx` | `test_run_manager.py`, `test_runs_router.py`, `test_runs_store.py`, `test_budget_guard.py`, `test_agent_runtime*.py`, `test_tool_loop_e2e.py`, `test_action_ledger*.py`, `test_agents_router.py`, `test_capability_catalog.py` / `test_mcp_catalog_parity.py` (edit only for the derived `ask_user` change), new `test_b7_runs_*.py`, vitest `delegate-runs.test.ts`, `agent-runs.test.ts`, `AgentsRail*.test.tsx`, `BudgetConfig*.test.tsx` |
| **W3 `unattended-chart-workspace`** | opus | new `services/workflow_scheduler.py`, `services/workflow_store.py`, `services/workflow_engine.py` (only if needed), `services/workflow_nodes/__init__.py`, `workflow_nodes/builtin.py`, `routers/workflow.py`, `models/workflow.py`, `types/workflow.ts`, **`sidecar/app.py` (sole)**, `sidecar/tests/fixtures/workflow_node_types.json`, `src/modules/node-editor/*`, `src/store/workflow.ts`, `src/app/page.tsx`, `src/lib/keychain.ts` (additive namespace only), `src/modules/chart/ChartPanel.tsx`, `src/modules/chart/drawings/*`, `src/store/chart-drawings.ts`, `types/drawings.ts`, `src/lib/workspace.ts`, `src/store/workspace.ts`, `src/modules/platform/WorkspaceDialog.tsx`, `src/components/StatusChrome.tsx` (the not-saving badge only), `sidecar/services/workspace_store.py`, `sidecar/routers/workspace.py`, `src/modules/equity-overview/EquityOverviewPanel.tsx`, `src/modules/equity-overview/api.ts`, `src/store/sec.ts`, `src/store/earnings.ts`, `src/modules/sec/SecFilingsPanel.tsx`, `src/modules/earnings/EarningsCalendarPanel.tsx`, `src/modules/watchlist/WatchlistPanel.tsx`, `src/lib/symbol-autocomplete.ts` | `test_workflow_*.py`, new `test_b7_scheduler*.py`, `test_workspace*.py`, `test_b6_quant_pool.py` (run only), vitest: node-editor tests, `workflow.test.ts`, `ChartPanel*.test.tsx`, `chart-drawings.test.ts`, `workspace.test.ts`, `WorkspaceDialog*.test.tsx`, `EquityOverviewPanel*.test.tsx`, `sec.test.ts`, `earnings.test.ts`, `WatchlistPanel*.test.tsx`, `symbol-autocomplete.test.ts` |
| **W4 `research-funnel`** | opus | `sidecar/services/search/{base,searxng,ddg,brave,mojeek,keyless,extract,breaker}.py`, `services/agent_tools/web_search.py`, `services/agent_tools/deep_research.py`, `services/research/{deep,iter,models,relevance,sonar,perplexity}.py`, **`types/brief.ts` (sole)**, `src/lib/brief-ingest.ts`, `src/modules/research/brief-blocks.tsx`, `src/modules/research/BriefPanel.tsx` (source-rail date / broken count only), `src/lib/format.ts` (additive only) | `test_research_*.py`, `test_search_*.py`, `test_deep_research*.py`, `test_web_search*.py`, `test_keyless*.py`, `test_b6_research_funnel.py`, new `test_b7_research_*.py`, fixtures (add only), vitest `brief-ingest.test.ts`, `brief-blocks*.test.tsx`, `BriefPanel*.test.tsx`, `format.test.ts` |
| **W5 `agent-writes-portfolio`** | opus | `src/lib/host-actions.ts`, `src/store/proposed-changes.ts`, `types/proposed-change.ts`, `src/modules/chat/ProposedChangesReview.tsx`, `src/modules/chat/ChatSidebar.tsx`, `src/store/portfolios.ts`, `src/store/symbols.ts` (only if needed), `src/modules/portfolio/PortfolioPanel.tsx`, `src/components/DataBadges.tsx` (only if needed), `src/modules/portfolio/api.ts` (docstring only), `sidecar/routers/portfolio.py`, `sidecar/services/portfolio_db.py`, `sidecar/services/agent_tools/compare_symbols.py` | vitest `host-actions.test.ts`, `proposed-changes.test.ts`, `ProposedChangesReview.test.tsx`, `ChatSidebar*.test.tsx`, `portfolios.test.ts`, `PortfolioPanel*.test.tsx`; pytest `test_portfolio.py`, `test_compare_symbols*.py` |

**Out of bounds for every writer:** `CLAUDE.md`, `src-tauri/tauri.conf.json`, `.github/`, `LICENSE*`, `types/plugin.ts`, `r15-fanout.js`, `docs/`, `CHANGELOG.md`, the register.

**Unowned, import only:** `sidecar/config.py`, `services/locale.py`, `services/symbol_resolver.py`, `services/resolution_policy.py`, `services/sec_filings_provider.py`, `services/errors.py`, `services/research/fast.py`, `services/research/disclosures.py`, `services/research/semantics.py`, `services/screener.py`, `services/fundamentals_warm.py`, `services/quant/*`, `sidecar/main.py`, `src/lib/sidecar-client.ts`, `src/lib/streaming.ts`/`src/modules/chat/streaming.ts`, `src/store/panel-context.ts`, `src/store/llm-providers.ts`, `src/store/provider-keys.ts`, `src/components/PanelHost.tsx`, `src/components/SettingsPanel.tsx`, `src-tauri/**`.

### 1.1 Cross-writer contracts

- **C1: `corporate_disclosures.get_announcements_cached(symbol, limit)` is frozen** (W1 owns, W3 imports for the announcement trigger). Name, signature and return shape stay.
- **C2: `growth_check.get_quarterly_yoy(listing)` is frozen** (W1 owns; `research/fast.py`, which nobody edits, calls it). W1 may add fields to `QuarterlyYoY` (e.g. `source`); it may not rename or remove `revenue_growth`, `earnings_growth`, `mrq`, `prior`.
- **C3: disclosure out-of-coverage shape** (W1). A non-Indian instrument and a venue with no feed are answered, not raised: the service returns the normal envelope with `coverage: "covered" | "venue_not_covered" | "not_applicable"` and a human `note`; routes answer 200; agent tools answer `ok: true` with the same fields, so `research/disclosures.gather_floor` (reads `ok`) needs no change. A real transport/upstream failure stays `ProviderError` → 502. Model and `types/data.ts` mirror in the same commit.
- **C4: web rows carry `domain` and `published_at`** (W4). The runtime half already consumes `row.get("domain")` and `row.get("published_at")` from `web.citations`/`web.results` (`agent_runtime.py:1253-1264`, landed `26ea55c`). W4 emits exactly those snake_case keys on every `web_search` citation and result row: `domain` a bare host (never `"web"`, never "via …"), `published_at` ISO or null. No W2 change is needed; RESEARCH-024 certifies on W4 alone.
- **C5: `ask_user`** (W2 internal). Catalog `kind="per_invocation"`, `read_only=True`, domain `agents`, `mcp=False`, input `{question: string}`. The runtime offers it only when `mode == "delegate"` and strips it otherwise. W2 is the only catalog editor this batch.
- **C6: `models/__init__.py` and `types/data.ts` have one owner: W1.** W3 imports its schedule models from `models.workflow` directly. W2's run wire lives in `models/run.py` + `delegate-runs.ts` (both W2). W5 leaves `models/portfolio.py`, `PositionInput` and its `types/data.ts` mirror untouched (their removal goes to `issues[]` for a same-commit mirror deletion next batch).
- **C7: `app.py` is W3's.** W2's startup reconciliation (LIFECYCLE-012) runs at the first `runs_store` connection in the process, not in the lifespan. W3 adds `workflow_scheduler.start()`/`stop()` to the lifespan.
- **C8: the sidecar positions ledger keeps `GET /portfolio/positions`** (W5; corrected CODE-PLATFORM-021). `src/lib/workspace.ts` (W3) imports it once for a legacy session via `modules/portfolio/api.ts:65-70`. W5 deletes only the write routes and write functions; W3 does not touch the legacy import.
- **C9: `agent_tools/fundamentals.py`** is W1's this batch, for one change only: the IN exchange overlay call (D-B7-1). `_canonicalize` in it is frozen (W5's `compare_symbols` imports it). `_classify_reason` (AGENT-061) is out of scope (§4).
- **C10: `symbol-autocomplete.ts`** is W3's (UI-026). `fetchSymbolCandidates` keeps its name and signature.

---

## 2. Per-writer entries (mechanism, then fix, test and files)

### W1: `india-exchange-data` (opus, 8 entries, 2 highs)

**Priority order:** DATA-014/027/076 + LEAD-004 (one lane) → DATA-050/060 → LEAD-015 → LEAD-005.

**R15-DATA-027 + R15-DATA-014 (DAL leg) + R15-DATA-076: one class (no independent India witness). R15-LEAD-004 rides the same lane.**
- **Mechanism (confirmed at base).**
  - Only openbb-mcp (rank 10, all-null IN shells) and yfinance (rank 50) serve `fundamentals`/statements/ratings; `nse_direct`/`nse`/`bse` serve quote and ohlcv only (`provider_registry.py:131-221`, the `:174`/`:192` comments say so).
  - `revenue_ttm` is Yahoo's `totalRevenue`. `correctness_gate.reconcile_revenue` (`:551-606`) checks it against the same provider's annual statement and margin, and only when `yfinance_served` (`apply_witnesses`, `:807-850`). DAL's Yahoo FY statement agrees with the wrong 2.76 cr (reopen note), so no Yahoo witness can see it.
  - `growth_check` recomputes from Yahoo's `quarterly_income_stmt` (`growth_check.py:113-150`): same provider.
  - LEAD-004: the "half-yearly filer" label fires when fewer than four of **Yahoo's** quarterly columns fall inside 330 days (`correctness_gate.py:596-604`); Yahoo's IN frames skip quarters, so a quarterly filer is labelled half-yearly.
  - **Why not a registry rank.** `get_fundamentals` resolves with `accept=_fundamentals_screener_complete` (`provider_registry.py:493-512`): a partial result without screener-grade fields is kept only as fallback and the walk moves on, so a rank-5 exchange provider serving revenue/EPS alone would be discarded. And the bulk callers (`screener.py:550,1037`, `fundamentals_warm.py:346`) would hit NSE/BSE once per universe symbol behind the 1 req/s NSE throttle (DATA-066).
- **Fix (D-B7-1).**
  - New `services/exchange_financials.py`: `async get_filed_periods(symbol) -> FiledPeriods | None` reads exchange-filed results — NSE financial-results (index per the existing `_corporate_index`) for NSE listings, BSE results for BSE-only listings. Probe live (curl_cffi where httpx is 403'd) and record the observed endpoints/shapes in the module docstring, as the NSE/BSE modules do. Each row: period end, period length (quarter/half), revenue (total income), net profit, EPS, basis `standalone|consolidated`, venue, filing date, URL. Cached per listing (reuse `correctness_gate._cached_witness` or `data_cache`, 24 h).
  - One overlay, `correctness_gate.apply_exchange_financials(f) -> Fundamentals` (never raises; no-op for non-IN or when the lane returns nothing): sets `revenue_ttm`/`net_income_ttm` to the sum of the filed periods covering the latest 12 months (four quarters, or two halves for a half-yearly filer), EPS TTM, and MRQ-YoY growth when the prior-year period exists; `field_meta` carries provider `nse`/`bse`, the basis, the as-of (latest period end) and the cadence. When Yahoo's scalar diverges beyond the existing 30% band, the exchange figure is served and Yahoo's value is disclosed in that field's reason. Yahoo fills every other field and stays the flagged fallback (spec.md:817).
  - Called from the two single-name seams only: `apply_witnesses` (GET `/fundamentals`, company narrative) and the agent `fundamentals` tool after its fetch (C9), so chat and research (which reach fundamentals through that tool) see the same figure as the panel. Bulk screener/warm paths are untouched.
  - LEAD-004: `reconcile_revenue`'s cadence label comes from the filed periods when the lane answered (half-yearly only when the exchange periods are halves); without the lane, from the median gap between Yahoo's period ends (about 91 days = quarterly). A quarterly filer with a missing Yahoo column is labelled "trailing figure spans a provider gap", never "half-yearly".
  - DATA-076: `get_quarterly_yoy` prefers the exchange-filed quarters for an IN listing and records `source` (C2, additive); Yahoo's frame is the labelled within-provider fallback. A divergence between Yahoo's growth scalar and the exchange MRQ-YoY then surfaces through the existing semantics conflict path (`revenue_growth_computed`).
- **Test.**
  - Add-only fixtures captured live for DAL (BSE-only), FUSION (NSE), JONJUA (half-yearly SME) and one US symbol.
  - DATA-014 is written against DAL: `GET /fundamentals/DAL` serves `revenue_ttm` equal to the filed-period sum (screener.in ≈9.97 cr) with provider `bse`. The class case not written against: FUSION (NSE lane) serves ≈1,699 cr and discloses Yahoo's 858 cr.
  - DATA-027: the agent `fundamentals` tool for an IN symbol calls the exchange lane (stub) and its value wins with the provider label; a US symbol never calls it; the screener bulk path never calls it.
  - LEAD-004: JONJUA keeps "half-yearly"; a DHANBANK-shaped quarterly filer with a Yahoo gap does not get it.
  - DATA-076: a fixture where Yahoo's growth scalar and the exchange MRQ-YoY disagree produces a semantics conflict; an agreeing one does not.
  - Replace the DAL stub in `test_fundamentals.py:455-457` (it stubs an annual the provider does not have; the reopen note says so) — give the reason in the commit.
- **Files.** new `exchange_financials.py`, `correctness_gate.py`, `growth_check.py`, `agent_tools/fundamentals.py` (one call), `models/fundamentals.py` + `types/data.ts` (only if a field is unavoidable; same commit), tests, fixtures.

**R15-DATA-050 + R15-DATA-060: one class (out-of-coverage reported as 502).**
- **Mechanism.** `get_results_calendar` (`corporate_disclosures.py:592`) calls only the NSE lane. Every non-NSE/BSE symbol raises "not a known … instrument" (`:516`, `:768`, `:929`, `:982`). `routers/disclosures.py:64-151` maps every `ProviderError` to 502. An ADR has no ownership lane.
- **Fix (C3, D-B7-3).**
  - A BSE results/board-meeting lane (BSE forthcoming-results / board-meeting feed by scrip code), merged with NSE for dual listings, deduped by date and purpose.
  - Out-of-coverage is answered, not raised (C3): `not_applicable` for a non-Indian instrument, `venue_not_covered` for a venue with no feed. Transport failures stay 502.
  - New `services/sec_ownership.py`: for a US-listed ADR, the latest 20-F via `sec_filings_provider.list_filings`/`get_filing_sections` (import only), parse Item 6.E Major Shareholders into `{holder, percent, as_of}` rows, served on the shareholding route and tool as `provider: "sec-20f"` — a disclosed lane, never merged with the Indian SHP.
- **Test.** JONJUA/DAL/ELCIDIN results give 200 with events (ELCIDIN's BSE Q1 FY27 filing present). AAPL shareholding gives 200 `not_applicable`. The 20-F lane is written against SIFY; pin on a second 20-F filer with a major-shareholders table (INFY or WIT) as the case not written against. A transport failure is still 502.
- **Files.** `corporate_disclosures.py`, `bse_provider.py`, new `sec_ownership.py`, `routers/disclosures.py`, `agent_tools/disclosure_tools.py`, `models/announcements.py` + `types/data.ts` (same commit), `models/__init__.py`, tests, fixtures.

**R15-LEAD-015 (statement gap and labels).**
- **Mechanism.** yfinance labels annual periods by year (`yfinance_provider.py:528-533`), openbb by ISO `period_ending` (`openbb_mcp_provider.py:435-441`). A missing quarter between two present ones (DHANBANK 2025-09-30) is passed through silently.
- **Fix (D-B7-4).** Normalise in the registry's statement getters (`provider_registry.get_income_statement`/`get_balance_sheet`/`get_cash_flow`, `:515-553`), where every provider routes: annual labels become ISO period-end dates for both providers; a missing expected quarter becomes an explicit gap period with null values and a gap flag. Grep every consumer of `.periods` first (`EquityOverviewPanel.tsx:560,586`, `correctness_gate._latest_annual`, agent tools, the screener seed) — if one parses a bare year and is outside W1's files, keep the annual format, ship the gap marker only, and record why.
- **Test.** A DHANBANK-shaped fixture yields a gap row for 2025-09-30. A yfinance annual and an openbb annual share one label format.
- **Files.** `provider_registry.py`, `yfinance_provider.py`/`openbb_mcp_provider.py` (labels only if normalised at source instead), `models/fundamentals.py` + `types/data.ts` if a gap flag field is needed (same commit), tests.

**R15-LEAD-005 (quote as-of is now()).**
- **Mechanism.** `yfinance_provider.get_quote` builds `Quote(timestamp=_utcnow())` (`:356`) from `fast_info`, which carries no trade time, so an after-hours or illiquid last print reads as fresh. The fundamentals path already dates price fields by `regularMarketTime` (`_stamp_price_trade_time`, `:274-285`).
- **Fix.** Stamp the quote with the provider's last-trade time (the last bar's timestamp or `regularMarketTime`); when neither exists, the time is unknown with a reason, never now(). If `Quote.timestamp` must become nullable, change `models/market.py` + `types/data.ts` in the same commit and check the freshness labeller.
- **Test.** A closed-market fixture whose last trade is yesterday yields that time and an `eod`/stale freshness, not "live".
- **Files.** `yfinance_provider.py`, `models/market.py` + `types/data.ts` (only if nullable), tests.

### W2: `delegate-runs-runtime` (opus, 13 entries)

**Priority order:** CODE-AGENT-010 → AGENT-034 → AGENT-037/038/074 → AGENT-036 → AGENT-035/LIFECYCLE-013 → LIFECYCLE-012 → UI-040 → CODE-AGENT-011 → AGENT-039 → AGENT-046.

**R15-CODE-AGENT-010 (state machine).**
- **Mechanism.** `cancel_run`/`pause_run` check nothing (`run_manager.py:317-354`); `resume_run` checks only a live task (`:402-406`); `update_run` writes any status (`runs_store.py:265`); the router maps by substring (`routers/runs.py:130-135`) and the same error to 404 in answer, 409 in resume. A test pauses a completed run (`test_run_manager.py`).
- **Fix.** One transition table (including `planned` and `paused`) enforced in the store as a conditional `UPDATE … WHERE id=? AND status IN (…)`; `rowcount == 0` raises a typed `RunStateError` (409), an unknown run `RunNotFound` (404). No substring matching. Replace the test that pauses a completed run with one on a running run; give the reason in the commit.
- **Test.** cancel, resume and pause on a `done` run each give 409 and leave the row unchanged.
- **Files.** `runs_store.py`, `run_manager.py`, `routers/runs.py`, tests.

**R15-AGENT-034 (unbounded by omission).**
- **Mechanism.** An empty box becomes `undefined` (`BudgetConfig.tsx:42-43`), JSON drops it, `RunBudget` ceilings are Optional with no floor (`models/run.py:53-59`), `BudgetGuard.breach` skips `None` (`budget_guard.py:157-176`), `asyncio.timeout(None)` is a no-op (`run_manager.py:151`).
- **Fix.** Server floor in `launch_run`: every `None` ceiling is filled from one server default equal to the client's `DEFAULT_DELEGATE_BUDGET` (`BudgetConfig.tsx:7`); `Field(gt=0)`. The client falls back to the default on an empty box.
- **Test.** POST with `{}` budget → the guard carries all four defaults; `max_steps: 0` → 422.
- **Files.** `models/run.py`, `run_manager.py`, `BudgetConfig.tsx`, tests.

**R15-AGENT-037 + R15-AGENT-038 + R15-AGENT-074 (the `on_round_usage` contract).**
- **Mechanism.** `_on_round_usage` only sets a flag (`run_manager.py:133-140`); `invoke_agent` calls it at the round's done event (`agent_runtime.py:2026-2027`) and proceeds to tool dispatch without yielding, so the round's tools run and the next request is sent. `breach()` uses `>=` (`budget_guard.py:165-175`) and `breach_reason` wins over natural completion; it also carries agent error text (one variable, two meanings). AGENT-074: the callback receives the resolved model but not the resolved provider, so a provider-less launch (and every resume) is priced at the default rate.
- **Fix.** `on_round_usage(usage, model, provider) -> bool` (may continue). `invoke_agent` passes the resolved provider and honours `False` before dispatching pending tools (yields the round terminator with a budget notice and returns). `run_manager` keeps `breach_reason` and `agent_error` separate. A turn that ended with a final answer (no pending tools) is `done` even when it touched a ceiling (the detail notes it). N steps means exactly N provider rounds (`>` for steps).
- **Test.** `max_tokens=1000` with a 100k-token tool round → exactly one provider call, status `error` with the reason. A one-shot answer with `max_steps=1` → `done`. An omitted-provider run on an Opus-default agent prices at the Opus rate (074, the case not written against).
- **Files.** `agent_runtime.py`, `run_manager.py`, `budget_guard.py`, tests.

**R15-AGENT-036 (checkpoint order).**
- **Mechanism.** `_drive_run` writes the history then the prompt (`run_manager.py:127-129`); `resume_run` takes "the first user turn" as the prompt (`:409-424`); `answer_run` appends the answer as a raw dict (`:389-393`). An answer lands before the original prompt; a second answer becomes the prompt. Tool steps are never checkpointed.
- **Fix.** The checkpoint becomes `{prompt, turns[]}` (a legacy list-shaped row is read as legacy). An answer is sent as the new prompt with the prior turns plus the original prompt as history. Tool steps checkpoint as `[tool name → one-line result]` turns.
- **Test.** launch → pause → answer → pause → answer: the provider receives prompt, turns and answers in order.
- **Files.** `run_manager.py`, `runs_store.py`, tests.

**R15-AGENT-035 + R15-LIFECYCLE-013 (resume loses config).**
- **Mechanism.** `resume_run` spawns with `provider=None, model=None` (`run_manager.py:445-456`); `_PERSISTED_OPTION_KEYS = ("research_depth", "region")` (`runs_store.py:81`); resume/answer routes take no key (`routers/runs.py:113-135`); cost resets to `RunCost()` (`run_manager.py:438`); `resumeDelegateRun` (`delegate-runs.ts:323`) has no caller.
- **Fix.** Persist `provider` and `model` (never the key). Resume and answer take the BYOK key in a request header (never body, never persisted, never echoed). Cost accumulates across resumes. A Resume control on an `error` row in `AgentsRail` reads the provider key the way launch does.
- **Test.** Launch with provider/model X, breach, resume: `invoke_agent` gets X and the header key; cost after ≥ cost before; the key appears in no response and no DB row.
- **Files.** `runs_store.py`, `run_manager.py`, `routers/runs.py`, `models/run.py`, `delegate-runs.ts`, `AgentsRail.tsx`, tests.

**R15-LIFECYCLE-012 (durability row-deep).**
- **Mechanism.** No startup sweep: a `running` row survives a restart forever. The checkpoint is written only on terminal exits; the `CancelledError` path writes no status.
- **Fix (C7).** At the first store connection in a process, rows in `running`/`planned` whose task cannot exist become `error` "interrupted by sidecar restart" (a `paused` run with its question outstanding stays paused). Write the checkpoint inside `_on_round_usage`.
- **Test.** Insert a `running` row, reset the store's process state, open it: the row is `error` with that detail. A run cancelled mid-round has a non-null checkpoint and resumes.
- **Files.** `runs_store.py`, `run_manager.py`, tests.

**R15-UI-040 (client owns server truth).**
- **Mechanism.** The rail is in-memory; the poller skips sidecar runs without a local mirror and starts only from launch/resume (`delegate-runs.ts:89-160`); cancel is optimistic and never reads `response.ok` (`:280-297`).
- **Fix.** `adoptSidecarRuns()` on rail mount: `GET /runs`, adopt `running|planned|paused` rows, then `ensurePolling()`. Durable cancel is pessimistic: flip on ok, else "cancel failed — retry". While there, read a 422 array `detail` through the existing `extractSidecarDetail` export (import only) so a launch failure never renders `[object Object]` (the full shared-client fix is CODE-PLATFORM-011, §4).
- **Test.** Vitest: boot adoption of a sidecar-only running run; a failed cancel leaves it running with the retry message.
- **Files.** `delegate-runs.ts`, `agent-runs.ts`, `AgentsRail.tsx`, tests.

**R15-CODE-AGENT-011 (dead pause plane): wire it (C5, D-B7-6).**
- **Mechanism.** `pause_run` (`run_manager.py:336-354`) has no production caller, route or capability; `paused`, `question`, `answer_run`, the answer route and the rail's answer form never run. Also dead: `active_run_ids` (`:461`), `RunLaunchResponse` (`models/run.py`), `clearFinished` drops `paused` (`agent-runs.ts:116`).
- **Fix.** Add `ask_user` per C5. When the delegate driver sees an `ask_user` tool_use it checkpoints, sets `paused` with the question and ends the task; `answer_run` resumes with AGENT-036's order. Add `ask_user` to the allow-list of every first-party agent JSON that can be delegated. Delete `active_run_ids` and `RunLaunchResponse`; `clearFinished` keeps `paused`. Correct the module docstring (its "scope note" says the trigger is deferred).
- **Test.** A scripted delegate round calling `ask_user` pauses with the question; answering resumes and the provider sees the answer. Catalog parity green; a new assertion that `ask_user` is absent from the MCP projection and from `mode="agent"` tool sets.
- **Files.** `catalog.py`, `agent_runtime.py`, `run_manager.py`, `sidecar/agents/*.json`, `models/run.py`, `agent-runs.ts`, tests.

**R15-AGENT-039 (plan and activity).**
- **Mechanism.** `_planner_enabled` (`agent_runtime.py:122`) gates the plan pre-pass (`:1910`) to foreground; the driver flattens tool events to `"[tool_use name]"` (`run_manager.py:166-169`); the run wire has no activity; the rail shows tokens and $ only.
- **Fix.** A delegate launch runs the existing `decompose` pre-pass inside the detached task; a compound prompt (more than one step) parks the run in `planned` with the plan persisted until Start/Discard in the rail (`POST /runs/{id}/start`); a non-compound prompt starts directly. The run row persists a capped typed `activity` list (`{tool, status, summary}`) written per tool event; the rail renders plan and activity. Mirror status and fields in `delegate-runs.ts`/`agent-runs.ts`.
- **Test.** A compound launch returns `planned` with steps; Start runs it; `GET /runs/{id}` lists activity rows for a scripted tool round; a vitest shows the rail renders plan + Start.
- **Files.** `agent_runtime.py`, `run_manager.py`, `runs_store.py`, `routers/runs.py`, `models/run.py`, `delegate-runs.ts`, `agent-runs.ts`, `AgentsRail.tsx`, tests.

**R15-AGENT-046 (residual: cross-run id reuse).**
- **Mechanism (batch-6 not-certified note, confirmed).** `invoke_agent` mints `call_<uuid>` only when the provider id is empty or already in `seen_call_ids` (`agent_runtime.py:1954,1996-1998`), and that set starts empty per invocation. Gemini's per-stream `set_chart_symbol_0` therefore repeats across runs, and the process-global ack ledger (`action_ledger.py`, TTL 600 s) lets a late ack from run 1 ground run 2's action as applied.
- **Fix.** The runtime mints `call_<uuid>` for **every** tool call at that one site (the provider id is never trusted for identity); the assistant tool-use turn, the tool-result turn and every derived id already read `event.tool_call_id`, so they follow. Keep Gemini's name pairing untouched (it pairs by `metadata["name"]`).
- **Test.** The fix is written against the Gemini `name_index` case: two `invoke_agent` turns whose provider emits `set_chart_symbol_0` both times, turn 1's ack arriving late, → turn 2 is not confirmed by turn 1's ack. Pin on an OpenAI-style provider id reused across runs (the case not written against).
- **Files.** `agent_runtime.py`, tests.

### W3: `unattended-chart-workspace` (opus, 11 entries, 1 high)

**Priority order:** AGENT-023 → UI-023/UI-020/UI-022 → UI-031/CODE-FRONTEND-017/UI-026 → CODE-FRONTEND-019/DATA-090/UI-046. CODE-PLATFORM-018 needs no code.

**R15-AGENT-023 (high: nothing runs unattended) (D-B7-7).**
- **Mechanism (confirmed).** The only run starts are `POST /workflow/run` and `POST /agents/{id}/runs`; no scheduler exists (`sidecar/services/` has none); the only output nodes are `action.log` and `action.notify_desktop` (`workflow_nodes/builtin.py:316-338`).
- **Fix.**
  - `services/workflow_scheduler.py`: one asyncio loop started/stopped in the app lifespan (C7). It runs while the app is open; the UI copy says so.
  - Schedules persist in a `schedules` table of the workflow DB (`workflow_store.py`): id, workflow_id, trigger, enabled, last_fired_at, last_seen key, last status/detail.
  - Two triggers: `interval` (every N ≥ 5 minutes) and `announcement` (symbol + phrase): polls C1, fires once per new matching announcement, hands it to the run as input.
  - A fire runs the saved workflow through the same engine path `POST /workflow/run` uses, never overlaps its own previous fire, records the outcome.
  - New `action.webhook` node: POSTs `{workflow, node, value}` JSON to a user URL (https, plus `http://localhost`), 10 s timeout, result `{status_code}` or error.
  - The URL is a BYOK secret: stored in the OS keychain under a new additive namespace in `src/lib/keychain.ts`; the node config holds only a `secret_ref`; the renderer registers ref→URL with the sidecar (process memory only, via a request header) at boot (`page.tsx`) and on save. The sidecar never persists, logs or echoes it; the list route returns refs only.
  - `/workflow/schedules` CRUD with `models/workflow.py` + `types/workflow.ts` mirrored in the same commit; a Schedule control in the node editor for the saved workflow (create, enable, delete, last fired, status); the node registered in `BUILTIN_NODE_SPECS`, `node-registry.ts` and the shared fixture.
- **Test.** Fake clock: an interval schedule fires once when due and not again before the next interval. An announcement trigger fires once per new matching item (fixture feed) and not on a repeat poll. The webhook node posts to an `httpx.MockTransport` stub with the resolved URL. The URL appears in no DB row, response or log record (caplog). Vitest: the Schedule control creates an interval schedule.
- **Files.** new `workflow_scheduler.py`, `workflow_store.py`, `routers/workflow.py`, `models/workflow.py`, `types/workflow.ts`, `workflow_nodes/__init__.py`, `builtin.py`, the fixture, `node-editor/*`, `store/workflow.ts`, `page.tsx`, `keychain.ts`, `app.py`, tests.

**R15-CODE-PLATFORM-018 (verify-only).**
- **State.** The process pool landed at `bdc7f0e` (batch-6 verifier: `/health` max 33 ms during 20k/60k-step pricing, frozen binary included). The residual (orphaned workers on exit) was fixed at `831d52b`: the stdin-EOF watchdog shuts the pool down before `os._exit`, a pool initializer ties workers to the parent, pinned by `test_b6_quant_pool.py`; live proof in run-state L26.
- **Writer action.** None, unless running `test_b6_quant_pool.py` on the base fails. The integrator repeats the stdin-EOF and SIGTERM no-orphan checks on the built binary; the verifier certifies.

**R15-UI-020 (drawings keyed by panel only).**
- **Mechanism.** `DrawingSpec` has `panelId` only (`types/drawings.ts:86`); the store is `byPanel` (`chart-drawings.ts:20-64`); chart symbol/timeframe/indicators are not in `SerializedWorkspace`.
- **Fix.** `DrawingSpec` gains `symbol` and `timeframe`; the selector filters on them; older blobs' drawings are adopted as belonging to the restored symbol/timeframe. Persist `{symbol, timeframe, indicators, compare}` per chart panel in the workspace blob through the existing autosave-trigger registry (`workspace.ts:953 wireAutosaveTriggers`, `PERSISTED_SLICES`) with a guarded restore — no new `page.tsx` subscription needed.
- **Test.** Store: a RELIANCE drawing is not returned for TCS. Workspace: round-trip, and an older blob without the fields restores.
- **Files.** `types/drawings.ts`, `chart-drawings.ts`, `ChartPanel.tsx`, `workspace.ts`, tests.

**R15-UI-022 (drawing input side).**
- **Mechanism.** The click path takes `seriesData.close` first (`ChartPanel.tsx:648-657`), so anchors snap to the bar close; off-bar clicks commit `time: null`; Text always stores `"label"` (`:674`); Lock (`:1093`, `:1576`) guards nothing but the keyboard delete (UI-021).
- **Fix.** Price from `coordinateToPrice(point.y)` always; time from `coordinateToTime`, or the logical index when off-bar; an inline text prompt for Text; a locked drawing's row delete button is disabled. Drag-edit is not built (D-B7-9).
- **Test.** ChartPanel click-path tests: anchor price equals the clicked coordinate's price; an off-bar click places a visible drawing; Text takes the typed label; a locked drawing's delete is disabled.
- **Files.** `ChartPanel.tsx`, `drawings/*`, tests.

**R15-UI-023 (indicator race).**
- **Mechanism.** The price load and the indicator effect (`ChartPanel.tsx:564-600`) are independent effects on shared refs (`indicatorSeriesRef`, `:243`); the indicator catch (`:584-592`) sets the error but never calls `clearIndicatorSeries`; Parabolic SAR reads whatever candles are cached.
- **Fix.** Clear the indicator series at the start of each load and in the catch; render indicators only for the committed `{symbol, timeframe}` candle set, keyed by a load generation.
- **Test.** `/indicators` rejects after a symbol change: no overlay series remain.
- **Files.** `ChartPanel.tsx`, tests.

**R15-UI-031 + R15-CODE-FRONTEND-017 + R15-UI-026: one class (a superseded response is committed).**
- **Mechanism.**
  - `EquityOverviewPanel.doLoad` (`:787-816`) has no sequence guard; a host command mid-load lets the older response win, and its `finally` clears the spinner early (the narrative fetch already has a seq guard).
  - `sec.loadFilings` (`sec.ts:146-175`) commits `activeIdentifier` from the response and a single `filingsStatus`; `earnings.loadUpcoming` (`earnings.ts:81-97`) commits whichever window lands last.
  - `WatchlistPanel` stores a joined snapshot of entries+quotes (`setRows`, `:147,207`), so an added row is missing and a removed one reappears for a poll; `useSymbolAutocomplete` guards out-of-order responses but the candidates are not tied to the draft they were fetched for, so a fast Enter takes the previous query's pick (`:240-247`); polling (`:223`) never backs off or pauses.
- **Fix.** A per-slice request generation (a counter checked before commit) in `doLoad`, `loadFilings` and `loadUpcoming`; `loadFilings` stops writing `activeIdentifier` from the response. The watchlist keeps a `Map<symbol, Quote>` and joins at render; the autocomplete hook returns the query its candidates belong to and Enter accepts a candidate only when that equals the draft; the poll backs off on error and pauses while the document is hidden.
- **Test.** The fix is written against Equity Overview (two loads resolved out of order → the newer wins, spinner stays until it lands). Pin on the earnings window (7-day response landing after the 30-day one is discarded) as the case not written against. Watchlist: add during a poll shows the row immediately; typing "TCS" then Enter before the new candidates land adds TCS, not "TC".
- **Files.** `EquityOverviewPanel.tsx`, `equity-overview/api.ts` (only if an abort is added), `sec.ts`, `earnings.ts`, `SecFilingsPanel.tsx`/`EarningsCalendarPanel.tsx` (only if a status read moves), `WatchlistPanel.tsx`, `symbol-autocomplete.ts`, tests.

**R15-CODE-FRONTEND-019 + R15-DATA-090 + R15-UI-046: one class (persistence failures and reserved names masked).**
- **Mechanism.**
  - `flushAutosave` (`workspace.ts:923-947`) never reads `response.ok` and swallows every exception without a log; `routers/workspace.py` maps only `WorkspaceNotFoundError`/`WorkspaceNameError`.
  - `load_workspace` (`workspace_store.py:113-123`) turns a decode failure into "missing"; the next save then copies the corrupt file over the last good `.bak` (`:98-101`) and overwrites the slot, so the user's portfolios/notes are gone from both.
  - `listWorkspaces` (`workspace.ts:606-617`) returns `__autosave__`; only SettingsPanel filters it (`SettingsPanel.tsx:1615`), `WorkspaceDialog` (`:173`) does not; `saveWorkspace` accepts `__` names.
- **Fix.** Autosave reads `response.ok`, logs, and after 3 consecutive failures sets `lastAutosaveError` on the workspace store, shown as a quiet "not saving" badge in `StatusChrome`; the router maps `OSError` to a detailed 5xx. On decode failure the store renames the file to `<name>.corrupt-<ts>`, restores from `.bak` when that parses, and never copies an unparseable file over `.bak`; a non-dict body is rejected (400). `listWorkspaces` filters reserved names and `saveWorkspace`/`deleteWorkspace` reject them.
- **Test.** Vitest: fetch 500 three times → `lastAutosaveError` set; a later success clears it. Pytest: a truncated file → `.corrupt-*` kept, load serves the `.bak`, the next save leaves `.bak` parseable. `listWorkspaces` hides `__autosave__`; `saveWorkspace("__x")` rejects.
- **Files.** `workspace.ts`, `store/workspace.ts`, `StatusChrome.tsx`, `WorkspaceDialog.tsx` (only if needed), `workspace_store.py`, `routers/workspace.py`, tests.

### W4: `research-funnel` (opus, 12 entries)

**Salvage first.** `docs/redesign/verification/r15/stage-c/batch-7/b6-W4-wip.patch` is the batch-6 W4 writer's uncommitted work (VisitResult, BSE retry + AttachHis, deep/iter failure steps, test updates) saved from `.claude/worktrees/wf_94ccf2b8-e97-6`. It applies cleanly at this base (`git apply --check` passes). Read it, apply what still fits, and verify it like new code: it was never run to green.

**Priority order:** RESEARCH-019/DATA-075/RESEARCH-033 → RESEARCH-022/023/038 → RESEARCH-024/UI-038 → RESEARCH-020 → RESEARCH-021 → UI-092 → RESEARCH-026.

**R15-RESEARCH-019 + R15-DATA-075 + R15-RESEARCH-033: one class (research failures filtered out instead of recorded).**
- **Mechanism.** `visit_for_research` (`extract.py:706-738`) narrows every `fetch_page` outcome to `str | None`, so a 403, an SSRF block or an unsupported type vanishes and no step records it. `_default_pdf_fetch`/`_fetch_pdf_page` (`:278`, `:584`) make one attempt for bseindia hosts and never try AttachHis. `run_heavy_research`'s explorer gather keeps only `isinstance(b, ResearchBrief)` results (`iter.py:1050-1051`), so a raised angle is dropped with no step or log (RESEARCH-033).
- **Fix.** A small `VisitResult(text, reason)`; the research loop records `ResearchStep(status="error", detail=reason)` for each failed visit. bseindia PDFs get a bounded retry with backoff and AttachHis when AttachLive 404s. A crashed explorer emits one error step naming the angle and the exception, and is logged.
- **Test.** `fetch_page` returns "HTTP 403" → the run's steps include that error (written against). A raising explorer stub → a matching error step (the case not written against). A flaky stub failing once then succeeding returns the PDF; a 404 on AttachLive falls to AttachHis.
- **Files.** `extract.py`, `deep.py`, `iter.py`, `deep_research.py` (only if the visit type is threaded there), tests.

**R15-RESEARCH-022 + R15-RESEARCH-023 + R15-RESEARCH-038: one class (one marker list, two jobs; breaker accounting).**
- **Mechanism.** In `KeylessBackend.search`, `breaker.record_success()` and `any_engine_answered = True` run before `_filter_results` (`keyless.py:159-176`), so a 200 CAPTCHA page resets the breaker and "found nothing" replaces "rate-limited". `LOW_QUALITY_MARKERS` (`:77-100`, incl. "all rights reserved") is applied per paragraph in `extract.py` (correct) and per SERP result (destructive). RESEARCH-038: `record_failure` runs per attempt inside `_try_engine` (the comment at `keyless.py:187-188` says so), and attempts-per-engine equals the fail threshold, so one bad search benches DDG for 45 s.
- **Fix.** Split the list: footer/consent markers stay paragraph-level; only interstitial markers ("verify you are a human", "unusual traffic", "access denied", "are you a robot") act on results, where they are the block-page signal. Filter before recording success; rows that filter to zero on interstitial markers record a failure, note "blocked (challenge page)", and do not set `any_engine_answered`; an all-blocked chain raises the typed rate-limited error. Record at most one failure per engine per search.
- **Test.** The stub repro counts one breaker failure and the all-blocked chain raises rate-limited; a Route Mobile IR row with "All rights reserved" is kept; one search failing both attempts leaves the breaker closed.
- **Files.** `keyless.py`, `extract.py`, `breaker.py` (only if the constant moves), tests.

**R15-RESEARCH-024 + R15-UI-038: one class (source contract).**
- **Mechanism.** `Citation` is `{url, title, excerpt}` (`search/base.py:46-57`) and the backends drop the result date; `ResearchSource` has no date (`research/models.py:56-79`). Sonar/Perplexity put "host (via Perplexity Sonar)" in `domain`, and `hostOf` prefers `domain` (`brief-ingest.ts:250-259`), so every Sonar citation badges as web. The runtime half (C4) already forwards `domain`/`published_at` when present.
- **Fix.** `Citation`, the web result rows and `ResearchSource` carry `published_at` and a bare-host `domain` (C4 keys); provenance moves to its own `provider` field; `types/brief.ts` mirrors in the same commit. `hostOf` prefers the URL host and falls back to `domain` only when the URL does not parse. The Sources rail shows the date.
- **Test.** A SearXNG row with `publishedDate` → a dated, host-labelled source through `web_search` and through `_auto_publish_event` (the runtime half, run only). A Sonar-shaped sec.gov source badges as a filing.
- **Files.** `search/base.py`, the four backends (date passthrough), `web_search.py`, `research/models.py`, `deep.py`/`iter.py` (source recorder), `sonar.py`, `perplexity.py`, `types/brief.ts`, `brief-ingest.ts`, `brief-blocks.tsx`/`BriefPanel.tsx` (rail date), tests.

**R15-RESEARCH-020 (result cap drift).**
- **Mechanism.** The cap rule is hand-copied (`mojeek.py:133`, `brave.py:141`, `ddg.py:379`, `searxng.py:262`); SearXNG reads only `maxResults` and never slices.
- **Fix.** One `result_limit(options)` in `base.py` beside `DEFAULT_CITATION_LIMIT`; delete the copies; slice in `searxng.py`.
- **Test.** Parametrised over the four backends: `numResults=3` → at most 3 results and citations.
- **Files.** `base.py`, `searxng.py`, `ddg.py`, `brave.py`, `mojeek.py`, tests.

**R15-RESEARCH-021 (index-tail false negative).**
- **Mechanism.** `index_tail = r"[\s-]?\d{2,3}(?![a-z0-9])"` (`relevance.py:415`) reads "BAJFINANCE 200 DMA" as an index name.
- **Fix.** Require a contiguous or hyphenated suffix (drop `\s`) and gate the check behind `_foreign_shadow`.
- **Test.** Written against "BAJFINANCE 200 DMA breakout" (kept); pin on "BAJFINANCE 52-week high" (kept); "KSE-100" still dropped for a KSE-shadowed target.
- **Files.** `relevance.py`, `test_research_relevance.py`.

**R15-UI-092 (broken citations deleted).**
- **Mechanism.** `brief-ingest.ts` (`:398`) and `brief-blocks.tsx` (`:1091`) strip out-of-range `[n]`.
- **Fix.** Keep an inert flagged `[?]` titled "citation not in sources" and show a broken-citation count in the Sources header.
- **Test.** `[47]` against 21 sources → a flagged marker, count 1.
- **Files.** `brief-ingest.ts`, `brief-blocks.tsx`, `BriefPanel.tsx` (header count, if it lives there), tests.

**R15-RESEARCH-026 (shadow formatter).**
- **Mechanism.** `brief-blocks.tsx:57-101` re-implements number/money formatting (en-US grouping, no currency).
- **Fix.** Delete the local formatters; route through `src/lib/format.ts` with the instrument currency; an unknown currency is stated, never defaulted.
- **Test.** A null-currency metric renders the explicit unknown form; an INR market cap matches Equity Overview's string.
- **Files.** `brief-blocks.tsx`, `format.ts` (additive only), tests.

### W5: `agent-writes-portfolio` (opus, 11 entries)

**Priority order:** AGENT-041 → AGENT-032/UI-017 → AGENT-043 → AGENT-044/045 → UI-034/035 → UI-036/037 → CODE-PLATFORM-021.

**R15-AGENT-041 (no undo).**
- **Mechanism.** `accept()` applies with no pre-image (`proposed-changes.ts:125-170`); the stored `before` is prose (`types/proposed-change.ts:55`); the review lists only `pending` (`ProposedChangesReview.tsx:26`).
- **Fix.** The apply of each data-write intent (portfolio add/update/delete, note write, save_screen replace, watchlist add/remove, set_region) returns a typed pre-image; applied changes stay listed for the session with Undo, which restores the pre-image and acks nothing new to the runtime.
- **Test.** Apply `portfolio_delete_position` then Undo → the holding is back with its id (written against). A note replace + Undo restores the text (not written against).
- **Files.** `host-actions.ts`, `proposed-changes.ts`, `ProposedChangesReview.tsx`, `types/proposed-change.ts`, `portfolios.ts` (only if restore needs an insert-with-id), tests.

**R15-AGENT-032 (claim before outcome).**
- **Mechanism (refuter-corrected).** `ChatSidebar.tsx:980` (and the slash path `:599`) writes "Applied: …" right after `enqueue()`, which fires `accept()` unawaited (`proposed-changes.ts:117`); `accept()` can re-pend with a detail.
- **Fix.** `enqueue`/`accept` resolve to `applied | staged | failed`; both call sites write the line from that value.
- **Test.** Under AUTO, a failing apply leaves no "Applied:" line.
- **Files.** `ChatSidebar.tsx`, `proposed-changes.ts`, tests.

**R15-UI-017 (orphaned user turn).**
- **Mechanism.** `appendUser(prompt)` (`ChatSidebar.tsx:771`) runs before the provider/key resolution; a missing key sets a status line and returns (`:795-801`), leaving a user turn with no reply, error row or Retry.
- **Fix.** Resolve provider/key before `appendUser`; when it fails, no turn is appended and the status line stays (the keyless-onboarding branch, `:802-811`, is UI-013's and unchanged).
- **Test.** No key → no orphan user turn.
- **Files.** `ChatSidebar.tsx`, tests.

**R15-AGENT-043 (silent partial apply).**
- **Mechanism.** `parseScreenerCriterion` returns `null` for a malformed leaf (`host-actions.ts:366-420,443`); the list filters nulls; the label counts survivors and acks applied.
- **Fix.** The parse returns rejected leaves with reasons; the label and ack say "Wrote 2 of 3 criteria; dropped roe: value must be a number".
- **Test.** A 3-criterion call with one bad leaf returns the drop reason in label and ack.
- **Files.** `host-actions.ts`, tests.

**R15-AGENT-044 + R15-AGENT-045: one class (model symbols bypass the one resolution policy) (D-B7-10).**
- **Mechanism.** `add_to_watchlist` applies the raw string (`host-actions.ts:1494-1505`); `compare_symbols._compare_one` sends it straight to `get_quote` (`compare_symbols.py:46-80`). The one policy (`resolution_policy.decide`) is already exposed by `GET /resolve` (`routers/resolve.py:57-125`) and wrapped for tools by `agent_tools/fundamentals._canonicalize` (C9, import only).
- **Fix.** `add_to_watchlist` (equity) resolves through `GET /resolve` before applying: `bound` → add the resolved symbol and say so; `disambiguate` → fail with the candidates; `unresolved` → fail "unresolved name" with any candidates. `compare_symbols` runs each input through `_canonicalize`: a confident bind compares the canonical symbol; a disambiguation or miss makes that symbol's error say "unresolved/ambiguous name: did you mean …" instead of "no quote available". Crypto pairs pass through unchanged.
- **Test.** Written against MAZAGONDOCK: `compare_symbols(['COCHINSHIP','MAZAGONDOCK'])` compares MAZDOCK or names it as the suggestion — never "no quote". Pin on a company name ("Mazagon Dock") through `add_to_watchlist` (not written against): it adds the resolved listing or fails with candidates, never a blank row.
- **Files.** `host-actions.ts`, `compare_symbols.py`, tests.

**R15-UI-034 + R15-UI-035: one class (stale target after a portfolio switch).**
- **Mechanism.** `handleSubmit` ignores `updateHolding`'s boolean (`PortfolioPanel.tsx:341-347`) and `editingId` survives a portfolio switch, so Save writes nothing while the form resets. `holdingColumns` is memoised on layout flags only (`:388-498`, deps suppressed at `:495-497`), so its `handleDelete` closes over the first `active`.
- **Fix.** Clear `editingId` and reset the form when the active portfolio changes or is deleted; show an error when `updateHolding` returns false. The columns read the current handler (a ref or real deps); drop the exhaustive-deps suppression.
- **Test.** Edit then switch then Save → error, nothing silently lost (written against). Switch portfolio then Delete → the holding in the new portfolio is removed (UI-035 replay).
- **Files.** `PortfolioPanel.tsx`, tests.

**R15-UI-036 (residual: no refresh, no as-of).**
- **Mechanism.** The per-row `StalenessBadge` landed (R15-UI-090, `PortfolioPanel.tsx:56-75`). Still: quotes are fetched only when the holding set or the Retry nonce changes (`:190-199`), and totals carry no as-of.
- **Fix.** Bump `quotesNonce` on the Watchlist's interval (cleared on unmount); render an "as of" time on the totals from the oldest quote timestamp.
- **Test.** Advancing the timer refetches; totals show the as-of.
- **Files.** `PortfolioPanel.tsx`, tests.

**R15-UI-037 (cost basis unit).**
- **Mechanism.** The input and column read "Cost basis" (`PortfolioPanel.tsx:536,713-715`) with no per-share cue.
- **Fix.** Label "Avg cost / share" (placeholder "per share"), column "Avg cost".
- **Test.** Render test on the label.
- **Files.** `PortfolioPanel.tsx`, tests.

**R15-CODE-PLATFORM-021 (residual: write-only ledger routes) (C8).**
- **Mechanism.** The frontend sync is gone (certified CODE-FRONTEND-012/DATA-089/CODE-PLATFORM-022). Still live: `POST/PUT/DELETE /portfolio/positions` (`routers/portfolio.py:25-47`) and `portfolio_db.create/update/delete_position` (`:92-150`), with docstrings claiming authority. The only reader is the legacy import (C8).
- **Fix.** Delete the three write routes and the three write functions; rewrite the docstrings to one claim (the workspace blob owns holdings; the ledger is the read-only legacy-import source); correct `modules/portfolio/api.ts:65` prose.
- **Test.** `GET /portfolio/positions` lists rows seeded by direct SQL; POST/PUT/DELETE answer 405. Rewrite `test_portfolio.py`'s write tests into these — they covered the deleted write path; say so in the commit.
- **Files.** `routers/portfolio.py`, `portfolio_db.py`, `modules/portfolio/api.ts` (docstring), `test_portfolio.py`.

---

## 3. Integrator run order and gates

**Stall rule (all roles).** No single tool call may run longer than ~120 s. `pnpm ci-local`, full pytest/vitest, cargo, PyInstaller builds, sidecar boots and soak waits start detached (`nohup <cmd> > <log> 2>&1 &` or `run_in_background`) and are polled with separate short calls (`sleep 60; tail -n 5 <log>`); never an `until … sleep` loop inside one call, never a foreground whole-suite pytest. Emit a tool call at least every 2 minutes.

1. Work in a scratch worktree (`git worktree add <scratchpad>/b7-int 004-r4-experience-rebuild`), never the main repo (it holds uncommitted CLAUDE.md and ledger edits). Run `git branch --show-current` before every merge.
2. Audit each branch through `origin/worktree-agent-batch-7-<W1..W5>-<name>`: `git merge-base --is-ancestor 1a19d26 origin/<branch>` (stale base → re-dispatch) and `git diff --stat 1a19d26..origin/<branch>` touches only that writer's §1 files.
3. Merge `--no-ff` in this order, running that writer's pytest and vitest files (detached) after each:
   - **W1** — `types/data.ts` and `models/__init__.py` land first; C1/C2 are frozen or additive.
   - **W4** — completes C4 against the runtime half already on base.
   - **W2** — adds `ask_user`, which changes every catalog-derived count; run `test_capability_catalog.py`, `test_mcp_catalog_parity.py`, `test_agent_runtime*.py`, `test_agents_router.py`, `test_mcp_server.py`.
   - **W5**.
   - **W3** — `app.py`; imports C1.
4. Gates after all five (export `PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH` first; everything long detached):
   - `ruff format --check sidecar && ruff check sidecar`; `pnpm format:check`, `pnpm lint`, `pnpm typecheck`.
   - `cargo fmt --check`, clippy `-D warnings`, `cargo test` (no Rust is expected to change).
   - `node scripts/ensure-all-sidecars.mjs --force` (all three on Python 3.13), `pnpm ci-local` with the exit code recorded, `node scripts/smoke-test-sidecars.mjs`.
   - **CODE-PLATFORM-018 on the built binary:** a 20k-step binomial pricing while `/health` is polled (every reply < 1 s), then stdin-EOF and SIGTERM exits leave no PPID-1 pool worker (`ps -o pid,ppid,command`).
5. Grep checks:
   - `correctness_gate.py` calls `apply_exchange_financials` from `apply_witnesses`; `agent_tools/fundamentals.py` calls it once; `screener.py`/`fundamentals_warm.py` never do.
   - `routers/disclosures.py` still maps `ProviderError` to 502 only for real failures; `coverage` exists on the disclosure models and in `types/data.ts`.
   - `run_manager.py` has no `provider=None,\n        model=None` in `resume_run`, no `active_run_ids`; `routers/runs.py` has no `"already running" in str(exc)`.
   - `agent_runtime.py` has no `in seen_call_ids` mint condition (every tool call is minted).
   - `ChartPanel.tsx` click path has no `seriesData.close` price source; no `text: "label"` constant.
   - `workspace.ts` `flushAutosave` reads `response.ok`; `workspace_store.py` never copies an unparseable file over `.bak`.
   - `keyless.py`'s result-level marker list has no "all rights reserved"; `relevance.py` has no `r"[\s-]?\d{2,3}`; `brief-blocks.tsx` has no local `formatLarge`/`formatNumber`; `searxng.py`/`ddg.py`/`brave.py`/`mojeek.py` have no private `maxResults`/`numResults` reader.
   - `routers/portfolio.py` has no `@router.post`/`put`/`delete`; `ChatSidebar.tsx` writes no `Applied:` before an awaited outcome.
6. Record the §6 decisions in `docs/redesign/DECISIONS.md` and `CHANGELOG.md` at merge; writers do not edit docs.
7. Certification notes: `DATA-014` certifies on live `GET /fundamentals/DAL` (`revenue_ttm` ≈ the filed-period sum, provider `bse`) and the chat/agent tool path showing the same figure; `AGENT-023` records a needs-GUI check for the node-editor Schedule control and keychain registration if the webview cannot be driven headless — the sidecar side certifies on a fake-clock + stub-webhook run against the live sidecar; `RESEARCH-024` certifies on one FAST research through `invoke_agent` yielding a dated, host-labelled source; `CODE-PLATFORM-018` on step 4's binary check.

---

## 4. Deferred to the next batch (with reason)

**Highs.**
- **`AGENT-007` + `AGENT-017`.** The eval loop and the default-model swap are proven only on live pass^k; the default lanes are unfunded (DECISIONS_FOR_OPERATOR 2.1) and no Anthropic/Gemini key exists (D35). Operator-attended.
- **`LIFECYCLE-001`.** Moving the MCP joins and `start_main_sidecar` off Tauri's main thread needs proof from a packaged cold launch (GUI); the `--onedir` follow-up is Tier-1 (`tauri.conf.json`). Operator-attended.

**Classes that collide with a set here, or exceed capacity.**
- **Error-layer cluster as one writer next batch:** `UI-012`, `UI-014`, `LIFECYCLE-010`, `LIFECYCLE-011`, `CODE-PLATFORM-011`, `UI-013`, `UI-015`, `UI-030`, with `UI-029` (macro catalog swallow) and the provider-key trio `UI-019`/`UI-049`/`UI-057` (same `KeyEntryDialog`/onboarding save path UI-013 reworks). Collides with W2 (`delegate-runs.ts`) and W5 (`ChatSidebar.tsx`); spans `sidecar-client.ts`, `streaming.ts`, `src-tauri/src/lib.rs`.
- **`AGENT-061` + `DATA-061` (ProviderError.kind flattened).** The one mapper lives in `app.py` (W3's) and deletes per-route blocks in W1's routers.
- **`CODE-AGENT-008` + `RESEARCH-027` (auto-publish layer leak; latency budget with an early cockpit publish).** Both need `agent_runtime.py` (W2's sole file).
- **`CODE-RESEARCH-003` (duplicate deep loop).** W4 capacity; deleting `run_deep_research` retires `test_research_deep.py`'s subject and changes the RESEARCH-017 fallback — a deliberate call, not a side edit.
- **`RESEARCH-028` + `LIFECYCLE-018` (SearXNG honesty; hot-path probe).** Need the `app.py` lifespan (W3) and `web_search.py` (W4).
- **`AGENT-055` + `AGENT-056` (layout templates; destructive arrange default).** Straddle `host-actions.ts` (W5), `catalog.py` (W2) and `store/workspace.ts` (W3).
- **`DATA-081` + `UI-053` (slash symbol in a path param).** `ChartPanel.tsx`/`WatchlistPanel.tsx` are W3's; `modules/portfolio/api.ts` is W5's.
- **`CODE-PLATFORM-017` + `CODE-PLATFORM-066` (two transform.code evaluators; server code node CPU bounds).** Needs a Tier-3 grammar decision (`^`, rounding, ternary) and the node editor is W3's this batch for the Schedule control; take together next batch, before scheduled workflows with code nodes are common.
- **`AGENT-049` (native-search metering), `LIFECYCLE-014` (silent partial agent roster).** `agent_runtime.py`/`budget_guard.py` are W2's, at capacity.
- **`AGENT-081` (highlight arg), `AGENT-053` (context-bus coverage).** `host-actions.ts` (W5) + `EquityOverviewPanel.tsx` (W3) and many panel files.
- **Resolver set:** `DATA-058`, `DATA-059`, `LIFECYCLE-019`, `UI-039`, `CODE-DATA-002`, `CODE-DATA-003`, `DATA-051`, `DATA-052` — capacity; `DATA-051` needs `types/data.ts` (W1's).
- **Fundamentals-profile set:** `DATA-048`, `DATA-054`, `DATA-055`, `LEAD-016` — build on this batch's exchange lane (basis, periods from filed results) and need `types/data.ts` (W1's).

## 5. proposed_not_defect

None. Every selected entry reproduces at base (or, for CODE-PLATFORM-018, is fixed on base and awaits certification).

## 6. Tier-3 decisions (the integrator records them; none is Tier-4)

- **D-B7-1.** Exchange-filed results are the IN primary for the fields they carry (TTM revenue/profit from the filed periods covering 12 months, EPS, MRQ-YoY growth), applied as one overlay at the two single-name seams (`apply_witnesses`, the agent `fundamentals` tool) — not as a registry rank, because the acceptor chain discards partial results and the bulk screener/warm paths must not hit NSE/BSE per symbol. yfinance is the flagged fallback; a diverging Yahoo scalar is disclosed.
- **D-B7-2.** A TTM's cadence label comes from the filed periods (or the median period gap), never from a count of provider columns.
- **D-B7-3.** Out-of-coverage disclosures answer 200 with `coverage` + `note`; BSE results join NSE; an ADR's major shareholders come from its latest 20-F as a disclosed lane.
- **D-B7-4.** Statement periods are ISO period-end labels for every provider; a missing expected quarter is an explicit gap row.
- **D-B7-5.** Delegate runs: a server budget floor (every ceiling > 0), transitions enforced in the store (409), provider and model persisted, the resume/answer key in a header, cost accumulated, checkpoint `{prompt, turns[]}` written per round, orphaned rows `error` at first store open, a breach stops before tool dispatch, a final answer wins over a touched ceiling, pricing uses the resolved provider.
- **D-B7-6.** FR-028 self-pause is an `ask_user` capability offered only in delegate mode and not projected to MCP. A compound delegate prompt is planned and waits for Start in the rail; the run row carries a typed activity list. The rail adopts sidecar runs on mount; durable cancel is pessimistic.
- **D-B7-7.** A sidecar-resident scheduler (runs while the app is open) fires saved workflows on an interval or an announcement phrase; `action.webhook` posts to a user URL held as a BYOK secret (keychain → process memory via a header, never persisted or logged).
- **D-B7-8.** The runtime mints every tool-call id; provider ids are never trusted for identity.
- **D-B7-9.** Drawings belong to `{symbol, timeframe}`; chart state persists in the workspace blob; anchors take the clicked coordinate; Lock disables deletion; drag-edit is not built.
- **D-B7-10.** Every model-supplied symbol entry point routes through the one resolution policy (`GET /resolve` for host actions, `_canonicalize` for tools); a non-confident match fails with candidates, never a blank row or "no quote".
- **D-B7-11.** A corrupt workspace is quarantined (`.corrupt-<ts>`) and restored from `.bak`; an unparseable file never overwrites `.bak`; autosave failure is visible after 3 consecutive failures; reserved names are hidden and rejected.
- **D-B7-12.** Research: failed visits/explorers are error steps; BSE PDFs retry and fall back to AttachHis; block pages are engine failures and footer markers are paragraph-only; one failure per engine per search; the result cap has one helper; sources carry `published_at` and a bare host with provenance in its own field; broken citations are flagged, not deleted; the brief uses `lib/format`.
- **D-B7-13.** Applied agent data-writes keep a typed pre-image with session Undo; the transcript writes the apply outcome; the sidecar positions ledger is read-only (legacy import).

## 7. Writer ground rules

1. **Worktree.** Your own isolated worktree and branch `worktree-agent-batch-7-<Wn>-<name>` (e.g. `worktree-agent-batch-7-W1-india-exchange-data`). First `git reset --hard 1a19d26c6297bc48521913ba333d81b9b4ecf9f5` and confirm with `git log -1`. Never the main worktree. Push after each concrete deliverable. If your branch already exists from an earlier attempt (a restart), read its log and continue from it.
2. **Stall rule.** No tool call longer than ~120 s: long pytest/vitest/ruff-over-everything/builds/sidecar boots run detached and are polled in separate short calls. Run your own test files in the foreground only when they finish well inside the limit.
3. **Commits.** One focused commit per entry or root-cause group, conventional, no emojis, ending with the session's attribution trailer.
4. **Tests.** Only where the repo keeps them, one focused test per pinned behaviour; where a class is involved, pin the case the fix was not written against (named above). Never delete, skip or weaken a test; a test that encodes the defect is fixed with the reason in the commit. Never special-case code to satisfy a test. Scratch scripts never become tests. Live captures become add-only fixtures, never live calls in a test.
5. **Checks before committing.** Export the PATH line from §3. Python: `ruff format <files> && ruff format --check sidecar && ruff check sidecar`. TypeScript: `pnpm format:check`, `pnpm typecheck`, `pnpm lint` and your vitest files.
6. **Scope.** Touch only your §1 files and honour C1–C10 exactly (names, signatures, wire keys). A needed change elsewhere goes into `issues[]` with the exact line. No refactoring beyond the entry, no flags or defensive code for cases that cannot happen.
7. **Hard limits.** Never re-add trading. Never touch `CLAUDE.md`, `src-tauri/tauri.conf.json`, `.github/`, `LICENSE*`, `types/plugin.ts`, `r15-fanout.js`, `docs/` or the register. Read no `R15_BRIEF*.md` and nothing under `r15/local/`. No GUI. Never print, log or commit a secret (W2's resume key, W3's webhook URLs).
