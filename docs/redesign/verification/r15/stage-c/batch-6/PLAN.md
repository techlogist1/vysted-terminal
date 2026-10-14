# R15 Stage C: Batch 6 Plan (5 highs, 54 mediums, 1 proposed not-a-defect)

- **Base:** branch `004-r4-experience-rebuild` at `bc03be5b0e9819a546c4c219bfe1878b3c5d5667` (batch 5 merged, L25). D81 is merged: nothing here re-adds trading, orders, brokers or a paper account.
- **Author:** batch planner (Opus). I opened the code at each cited line before writing a row. Each mechanism follows the corrected verdict (refuter correction, batch-5 not-certified note), not the raw claim. Line numbers are at base.
- **Queue at base (after adjudication):** 0 critical, 8 high, 214 medium, 208 low.
- **Selection:** 60 open entries: 5 highs, 54 mediums, and `UI-041`, which is proposed as not a defect (§5).
  - **Highs.** 5 of the 8 open highs are taken: `DATA-014`, `DATA-017`, `DATA-027`, `AGENT-023` and `LEAD-012`. The other 3 are in §4 with the reason. `AGENT-007` and `AGENT-017` need funded live lanes. `LIFECYCLE-001` needs proof from a packaged cold launch, which is GUI work.
  - **Mediums.** All are in the four named areas except `CODE-PLATFORM-018` (reopened in batch 5: `to_thread` does not release QuantLib's GIL), `CODE-PLATFORM-021` and `CODE-PLATFORM-022`. The last two are class-mates of `CODE-FRONTEND-012` and `DATA-089`: the write-only sidecar positions ledger.
  - **Three batch-5 carry-overs are finished here.** `DATA-017`'s SME index leg goes to W1. `AGENT-052`, with `AGENT-051` and `CODE-FRONTEND-015` whose live effect waits on it, goes to W3. `CODE-PLATFORM-018` goes to W3.
  - **Class rule.** A class is a shared root cause, not a shared label. These are taken together:
    - `DATA-014` + `DATA-027` + `DATA-076`: no independent India witness exists, because Yahoo is checked against Yahoo.
    - `DATA-050` + `DATA-060`: out-of-coverage is reported as a 502 upstream failure.
    - `AGENT-035` + `LIFECYCLE-013`: provider and model are never persisted for a resume.
    - `AGENT-037` + `AGENT-038`: the breach flag is decoupled from loop control.
    - `AGENT-051` + `AGENT-052` + `CODE-FRONTEND-015`: the bus keys are not the dockview ids.
    - `CODE-FRONTEND-012` + `DATA-089` + `CODE-PLATFORM-021` + `CODE-PLATFORM-022`: the dead positions-ledger write path.
    - `CODE-FRONTEND-009` + `CODE-FRONTEND-010`: a cast hides a store-API mismatch.
    - `RESEARCH-022` + `RESEARCH-023`: one marker list does two jobs, in `keyless.py`.
    - `RESEARCH-024` + `UI-038`: the source contract overloads `domain` and drops the date.
    - `RESEARCH-019` + `DATA-075`: the visit/PDF fetch collapses every failure to `None`.
  - **Neighbours not taken.** Label-mates with a different root cause, and neighbours not taken for capacity, are in §4.
- **proposed_not_defect:** one entry, `UI-041` (§5). It is in the four areas, so it needs the verifier's fresh concurrence.
- **Models:** all five sets are opus. None is purely mechanical: each carries a data-provider, runtime, persistence, packaging or research-funnel judgement.

---

## 0. The 60 entries

| # | Entry | Sev | Root-cause class | Writer |
|---|---|---|---|---|
| 1 | R15-DATA-017 | high | residual: NSE corporate endpoints hard-code `index=equities`, so SME filings read as empty | W1 |
| 2 | R15-DATA-014 | high | residual DAL leg: the only witness is Yahoo's own statement | W1 |
| 3 | R15-DATA-027 | high | no exchange-filed IN fundamentals lane; yfinance is the de-facto primary | W1 |
| 4 | R15-DATA-076 | med | growth check is Yahoo against Yahoo | W1 |
| 5 | R15-DATA-050 | med | results calendar is NSE-only; a BSE-only name gets 502 | W1 |
| 6 | R15-DATA-060 | med | a non-Indian instrument gets 502 instead of "not applicable"; no 20-F ownership lane | W1 |
| 7 | R15-LEAD-004 | med | TTM "half-yearly" label counts Yahoo columns, not the filing cadence | W1 |
| 8 | R15-LEAD-015 | med | a quarterly statement gap goes unmarked; period labels differ by provider | W1 |
| 9 | R15-AGENT-034 | med | an empty budget box becomes no ceiling; no server floor | W2 |
| 10 | R15-AGENT-035 | med | resume/answer run with provider, model and key all None | W2 |
| 11 | R15-LIFECYCLE-013 | med | same root (live: Ollama model swapped on resume) | W2 |
| 12 | R15-AGENT-036 | med | checkpoint invariant ("first user turn = prompt") broken by its own writer | W2 |
| 13 | R15-AGENT-037 | med | breach flag cannot stop tool dispatch or the next request | W2 |
| 14 | R15-AGENT-038 | med | a completed final round that touches a ceiling is recorded as error | W2 |
| 15 | R15-AGENT-039 | med | delegate runs with no plan and no activity stream | W2 |
| 16 | R15-CODE-AGENT-010 | med | no run state machine | W2 |
| 17 | R15-CODE-AGENT-011 | med | pause/answer plane has no trigger (dead) | W2 |
| 18 | R15-LIFECYCLE-012 | med | no startup reconciliation; checkpoint only at exit | W2 |
| 19 | R15-UI-040 | med | client store decides which runs exist; cancel is optimistic | W2 |
| 20 | R15-AGENT-046 | med | tool-call ids not unique (Ollama `''`, Gemini per-round index); ledger never pops | W2 |
| 21 | R15-LEAD-014 | med | tool-arg repair accepts a schema echo | W2 |
| 22 | R15-AGENT-023 | high | no scheduler, trigger or outbound action | W3 |
| 23 | R15-CODE-PLATFORM-018 | med | reopened: QuantLib holds the GIL, so `to_thread` still freezes the loop | W3 |
| 24 | R15-LEAD-012 | high | build venvs use whatever `python3` is on PATH | W3 |
| 25 | R15-AGENT-052 | med | publishers key the bus `chart-${id}` / `equity` / `backtest-panel` | W3 |
| 26 | R15-AGENT-051 | med | same class (runtime half already landed; certifies with 052) | W3 |
| 27 | R15-CODE-FRONTEND-015 | med | same class (single derivation landed; certifies with 052) | W3 |
| 28 | R15-UI-020 | med | drawings keyed by panel only; chart state not persisted | W3 |
| 29 | R15-UI-021 | med | global Backspace/Delete deletes the selected drawing, even a locked one | W3 |
| 30 | R15-UI-022 | med | drawing input side half-built (snap to close, off-bar, Text, dead Lock) | W3 |
| 31 | R15-UI-023 | med | indicator series race the price load; catch never clears | W3 |
| 32 | R15-CODE-RESEARCH-002 | med | `snapshot_structured` gather lacks `return_exceptions` | W4 |
| 33 | R15-RESEARCH-017 | med | ULTRA heavy branch has no fallback | W4 |
| 34 | R15-RESEARCH-018 | med | researcher bucket is region-blind and matches `sec` as a substring | W4 |
| 35 | R15-RESEARCH-012 | med | floor omits `sub_question`, so results banding is off | W4 |
| 36 | R15-RESEARCH-016 | med | one guard controls both the floor fetch and the citation record | W4 |
| 37 | R15-RESEARCH-019 | med | visit failures collapse to None, with no step | W4 |
| 38 | R15-DATA-075 | med | BSE PDF gets a single attempt, no AttachHis | W4 |
| 39 | R15-RESEARCH-020 | med | result cap hand-copied into 4 backends; SearXNG ignores `numResults` | W4 |
| 40 | R15-RESEARCH-021 | med | KSE index-tail regex eats "TICKER 200 DMA" | W4 |
| 41 | R15-RESEARCH-022 | med | block page recorded as success before filtering | W4 |
| 42 | R15-RESEARCH-023 | med | footer markers applied per SERP result | W4 |
| 43 | R15-RESEARCH-024 | med | Citation/ResearchSource drop the date; domain is `'web'` (runtime mapping half: W2) | W4 (+W2) |
| 44 | R15-UI-038 | med | `domain` carries "host (via Sonar)"; `hostOf` prefers it | W4 |
| 45 | R15-UI-092 | med | out-of-range citation markers deleted, not flagged | W4 |
| 46 | R15-RESEARCH-026 | med | brief has a shadow money formatter | W4 |
| 47 | R15-CODE-FRONTEND-011 | med | describe and apply parse inputs independently | W5 |
| 48 | R15-CODE-FRONTEND-007 | med | proposal target re-resolved at accept | W5 |
| 49 | R15-CODE-FRONTEND-009 | med | `save_screen` cast: saves the on-screen draft | W5 |
| 50 | R15-CODE-FRONTEND-010 | med | `write_screener_filters run:true` never runs | W5 |
| 51 | R15-AGENT-043 | med | a malformed screener leaf is silently dropped | W5 |
| 52 | R15-AGENT-042 | med | published holdings carry no id; ambiguous lot picks the first | W5 |
| 53 | R15-AGENT-041 | med | no pre-image, no undo; applied rows vanish | W5 |
| 54 | R15-AGENT-032 | med | transcript writes "Applied:" before the apply outcome | W5 |
| 55 | R15-DATA-088 | med | `normalizeHolding` coerces garbage to 0; no sign checks | W5 |
| 56 | R15-CODE-FRONTEND-012 | med | agent portfolio writes sync to a write-only sidecar ledger | W5 |
| 57 | R15-DATA-089 | med | same class (`h-<uuid>` becomes undefined; PUT/DELETE 405 swallowed) | W5 |
| 58 | R15-CODE-PLATFORM-021 | med | same class (corrected: GET is now the legacy-import source, keep it) | W5 |
| 59 | R15-CODE-PLATFORM-022 | med | same class (dead typed client in `portfolios.ts`) | W5 |
| 60 | R15-UI-041 | med | **proposed not a defect** (§5) | — |

---

## 1. File ownership: five disjoint sets

Each file belongs to exactly one writer. If a writer needs a change in another writer's file, it does not make the change. It puts the change in `issues[]` with the exact line. "Import only" means the writer may read the symbol but never edits the file.

| Writer | Model | Source files | Tests |
|---|---|---|---|
| **W1 `india-exchange-data`** | opus | `sidecar/services/nse_provider.py`, `bse_provider.py`, `corporate_disclosures.py`, `provider_registry.py`, `correctness_gate.py`, `growth_check.py`, `yfinance_provider.py`, new `services/exchange_financials.py`, new `services/sec_ownership.py`, `services/research/semantics.py` (only if the growth witness label needs it), `sidecar/routers/disclosures.py`, `sidecar/routers/fundamentals.py`, `services/agent_tools/disclosure_tools.py`, `sidecar/models/announcements.py`, `sidecar/models/fundamentals.py` (only if a field is unavoidable), **`sidecar/models/__init__.py` (sole)**, **`types/data.ts` (sole)** | `test_nse_provider.py`, `test_bse_provider.py`, `test_corporate_disclosures.py`, `test_disclosures*.py`, `test_disclosure_tools.py`, `test_correctness_gate.py`, `test_fundamentals.py`, `test_growth_check*.py`, `test_provider_registry*.py`, `test_yfinance*.py`, new `test_b6_exchange_*.py`, fixtures under `sidecar/tests/fixtures/{nse,bse,sec}/` (add only) |
| **W2 `delegate-runs-runtime`** | opus | `sidecar/services/run_manager.py`, `runs_store.py`, `budget_guard.py`, `sidecar/routers/runs.py`, `sidecar/models/run.py`, **`sidecar/services/agent_runtime.py` (sole)**, `services/action_ledger.py`, `sidecar/routers/agents.py` (ack model only, if needed), `services/llm/openai.py`, `llm/ollama.py`, `llm/gemini.py` (only if needed), **`services/agent_tools/catalog.py` (sole)**, `sidecar/agents/*.json` (`ask_user` allow-list only), `src/lib/delegate-runs.ts`, `src/store/agent-runs.ts`, `src/modules/chat/AgentsRail.tsx`, `src/modules/chat/BudgetConfig.tsx` | `test_run_manager.py`, `test_runs_router.py`, `test_runs_store.py`, `test_budget_guard.py`, `test_agent_runtime*.py`, `test_tool_loop_e2e.py`, `test_llm_openai*.py`, `test_llm_ollama*.py`, `test_llm_gemini*.py`, `test_action_ledger*.py`, `test_agents_router.py`, `test_capability_catalog.py` / `test_mcp_catalog_parity.py` (run; edit only for a derived change), new `test_b6_runs_*.py`, vitest: `delegate-runs.test.ts`, `agent-runs.test.ts`, `AgentsRail.test.tsx`, `BudgetConfig*.test.tsx` |
| **W3 `unattended-platform-chart`** | opus | **`sidecar/app.py` (sole)**, `sidecar/main.py`, new `services/workflow_scheduler.py`, `services/workflow_store.py`, `services/workflow_engine.py` (only if needed), `services/workflow_nodes/__init__.py`, `workflow_nodes/builtin.py`, `workflow_nodes/quant_nodes.py`, `sidecar/routers/workflow.py`, `sidecar/models/workflow.py`, `types/workflow.ts`, `services/quant/*.py` (new `pool.py`), `sidecar/routers/quant.py`, `services/agent_tools/quant_tools.py`, `sidecar/tests/fixtures/workflow_node_types.json`, `src/modules/node-editor/*`, `src/store/workflow.ts`, `src/app/page.tsx`, `scripts/ensure-sidecar.mjs`, `scripts/ensure-openbb-mcp-sidecar.mjs`, `scripts/ensure-sec-edgar-mcp-sidecar.mjs`, new `scripts/build-python.mjs`, `src/modules/chart/ChartPanel.tsx`, `src/modules/chart/drawings/*`, `src/store/chart-drawings.ts`, `types/drawings.ts`, `src/lib/workspace.ts`, `src/modules/equity-overview/EquityOverviewPanel.tsx` (bus key only), `src/modules/backtest/BacktestResultView.tsx` (bus key only), `src/modules/chat/context-provider.ts` (only if needed) | `test_workflow_*.py`, `test_quant*.py`, new `test_b6_scheduler*.py`, `test_b6_quant_pool.py`, vitest: node-editor tests, `workflow.test.ts`, `ChartPanel*.test.tsx`, `chart-drawings.test.ts`, `workspace.test.ts`, **`panel-context-publishers.test.tsx` (sole)**, `context-provider.test.ts`, `SuggestionChips.test.tsx` |
| **W4 `research-funnel`** | opus | `sidecar/services/research/{fast,deep,iter,disclosures,relevance,models,sonar,perplexity}.py`, `sidecar/services/search/{base,searxng,ddg,brave,mojeek,keyless,extract}.py`, `services/agent_tools/deep_research.py`, `services/agent_tools/web_search.py`, **`types/brief.ts` (sole)**, `src/lib/brief-ingest.ts`, `src/modules/research/brief-blocks.tsx`, `src/lib/format.ts` (additive only) | `test_research_*.py`, `test_search_*.py`, `test_deep_research*.py`, `test_web_search*.py`, `test_keyless*.py`, `test_research_relevance.py`, new `test_b6_research_*.py`, fixtures (add only), vitest: `brief-ingest.test.ts`, `brief-blocks*.test.tsx`, `format.test.ts` |
| **W5 `host-actions-portfolio`** | opus | `src/lib/host-actions.ts`, `src/store/proposed-changes.ts`, `types/proposed-change.ts`, `src/modules/chat/ProposedChangesReview.tsx`, `src/modules/chat/ChatSidebar.tsx`, `src/store/portfolios.ts`, `src/store/screener.ts`, `src/modules/portfolio/PortfolioPanel.tsx`, `src/modules/portfolio/api.ts` (docstring only), `sidecar/routers/portfolio.py`, `sidecar/services/portfolio_db.py` | vitest: `host-actions.test.ts`, `proposed-changes.test.ts`, `ProposedChangesReview.test.tsx`, `ChatSidebar.test.tsx`, `portfolios.test.ts`, `screener.test.ts`, `PortfolioPanel*.test.tsx`; pytest: `test_portfolio.py` |

**Out of bounds for every writer:** `CLAUDE.md`, `src-tauri/tauri.conf.json`, `.github/`, `LICENSE*`, `types/plugin.ts`, `r15-fanout.js`, `docs/`, `CHANGELOG.md`, the register.

**Unowned, import only:**
- `sidecar/config.py`, `services/locale.py`, `services/symbol_resolver.py`, `services/sec_filings_provider.py`, `services/errors.py`
- `services/research/depth.py`, `src/lib/sidecar-client.ts`, `src/store/panel-context.ts`
- `src/store/llm-providers.ts`, `src/lib/keychain*.ts`, `src/store/notes.ts`, `src/store/workspace.ts`, `src/components/PanelHost.tsx`

### 1.1 Cross-writer contracts

- **C1: `corporate_disclosures.get_announcements_cached(symbol, limit)` is frozen (W1 owns it, W3 imports it; AGENT-023).**
  - Name, signature and return shape stay. W3's announcement-phrase trigger reads it and nothing else in the module.
- **C2: `growth_check.get_quarterly_yoy(listing)` is frozen (W1 owns it, W4's `fast.py` calls it).**
  - W1 may add fields to the returned dataclass. It may not rename or remove `revenue_growth`, `earnings_growth`, `mrq` or `prior`.
- **C3: disclosure out-of-coverage shape (W1; DATA-050/060).**
  - Routes answer 200 with the existing envelope plus `coverage: "covered" | "venue_not_covered" | "not_applicable"` and a human `note`.
  - A real upstream failure stays 502.
  - Agent tools return `ok: true` with the same `coverage`/`note`, so W4's `gather_floor` (which already reads `ok`) needs no change.
  - The model and the `types/data.ts` mirror change in the same W1 commit.
- **C4: web rows carry `domain` and `published_at` (W4 provides, W2 consumes; RESEARCH-024).**
  - W4 makes every `Citation` and web-result row the research tool returns carry `domain` (a bare host, never "web" or "via …") and `published_at` (ISO or null).
  - W2 changes the one FAST-run mapping in `agent_runtime._auto_publish_event` (`agent_runtime.py:1250-1262`) to forward `domain` (falling back to the URL host, never `"web"`) and `published_at`.
  - Neither side imports a new symbol, so each branch stays green alone. RESEARCH-024 certifies only after both merge.
- **C5: `ask_user` (W2 internal; CODE-AGENT-011).**
  - Catalog: `kind="per_invocation"`, `read_only=True`, domain `agents`, input `{question: string}`.
  - The runtime offers it only when `mode == "delegate"` and strips it otherwise, even when an allow-list names it.
  - It is not projected to MCP (`per_invocation` is not projected today; W2 asserts this in the parity test).
  - W2 is the only writer that edits the catalog this batch.
- **C6: `models/__init__.py` and `types/data.ts` have one owner: W1.**
  - W3 imports its schedule models from `models.workflow` directly.
  - W5 leaves `models/portfolio.py` and the `Position`/`PositionInput` mirrors untouched. `PositionInput` becoming unused goes to `issues[]` for a same-commit mirror deletion next batch.
- **C7: `app.py` and `main.py` are W3's.**
  - W2's startup reconciliation (LIFECYCLE-012) runs where `runs_store` first opens its database in the process, not in the lifespan.
  - W3 adds `workflow_scheduler.start()`/`stop()` and the quant pool `shutdown()` to the lifespan, and `multiprocessing.freeze_support()` to `main.py`.
- **C8: `panel-context-publishers.test.tsx` is W3's.**
  - Its `"equity"` assertions encode the AGENT-052 defect, so W3 corrects them.
  - W5 puts its AGENT-042 publish test in `PortfolioPanel*.test.tsx`, which it owns.
  - The now-stale `deletePosition: vi.fn()` key in that mock factory is harmless. W3 leaves it, and W5 lists it in `issues[]`.
- **C9: the sidecar positions ledger keeps `GET /portfolio/positions` (W5; corrected CODE-PLATFORM-021).**
  - `src/lib/workspace.ts:864-890` (W3's file) imports that ledger once for a session that never saved portfolios (R15-LIFECYCLE-009).
  - W5 deletes only the write path. W3 does not touch the legacy import.

---

## 2. Per-writer entries (mechanism, then fix, test and files)

### W1: `india-exchange-data` (opus, 8 entries, 3 highs)

**R15-DATA-017 (residual: SME filings read as a silent empty).**
- **Mechanism (batch-5 not-certified note, confirmed).** `nse_provider._fetch_corporate_list` (`nse_provider.py:592-599`) and `get_sast_disclosures` (`:676`) send `index=equities` for every symbol. NSE serves Emerge (SM-series) filings only under `index=sme`. Since batch 5 the master knows SUMAX etc. (`symbol_resolver.is_nse_emerge`, `symbol_resolver.py:504-509`), so the old 502 became a 200 with 0 rows.
- **Fix.** One `_corporate_index(bare)` that returns `"sme"` when `symbol_resolver.is_nse_emerge(bare)`, else `"equities"`. Every corporates call uses it: announcements, event calendar, shareholding master, corporate actions and SAST. Check the historicalOR `series` param (`:380`, `["EQ"]`) for SM names while there. If it is also wrong, fix it in the same helper commit, otherwise record in `issues[]`.
- **Test.** Capture live NSE `index=sme` payloads (add-only fixtures). The fix is written against SUMAX announcements. Pin on QUALIANCE's shareholding master, a different endpoint and name. Negative: a main-board name still sends `index=equities`.
- **Files.** `nse_provider.py`, `test_nse_provider.py`, fixtures.

**R15-DATA-027 + R15-DATA-014 (DAL leg) + R15-DATA-076: one class (no independent India witness).**
- **Mechanism.**
  - `provider_registry` serves IN `fundamentals`/statements/ratings from openbb-mcp (rank 10, all-null shells for IN, D72) and yfinance (rank 50) only (`provider_registry.py:131-142,174,192,207-221`). `nse_direct`/`nse`/`bse` serve quote and ohlcv.
  - `revenue_ttm` is `info.totalRevenue` verbatim (`yfinance_provider.py:504`). `correctness_gate.reconcile_revenue` (`correctness_gate.py:556-606`) checks it only against the same provider's annual statement and margin (`apply_witnesses`, `:794-812`, `check_revenue` requires `yfinance_served`).
  - For DAL (BSE-only, pack P2) Yahoo's own FY26 statement agrees with the wrong 2.76 cr TTM, so no Yahoo witness can see it (reopen note).
  - `growth_check` (`growth_check.py:1-40`) recomputes growth from `yf.Ticker(...).quarterly_income_stmt`: the same provider.
- **Fix.**
  - New `services/exchange_financials.py` reads exchange-filed quarterly results: NSE financial-results / results-comparison for NSE listings (index per `_corporate_index`), BSE results for BSE listings. Probe live and record the observed endpoints and shapes in the module docstring, as the NSE/BSE modules do.
  - It returns period-end-dated quarterly rows: revenue (total income), net profit, EPS, and basis `standalone|consolidated`, with venue, filing date and URL.
  - Register it for IN `fundamentals` above yfinance. It serves only the fields it has: `revenue_ttm`/`net_income_ttm` as the sum of four filed quarters (only when four exist), EPS TTM, and MRQ-YoY growth. Each field's `field_meta` carries provider `nse`/`bse`, the basis and the as-of. yfinance fills every other field and remains the flagged fallback (spec.md:817).
  - Extend the existing openbb→yfinance field-enrichment merge (`provider_registry.py:245-300`); do not add a second merge.
  - When both an exchange figure and a Yahoo scalar exist and diverge beyond the existing 30% band, the exchange figure is served and the Yahoo value is disclosed in the field's flag reason.
  - `growth_check` gains the exchange witness: a divergence between Yahoo's growth scalar and the exchange-computed MRQ-YoY surfaces through the existing semantics conflict path.
- **Test.**
  - Add-only fixtures captured live for DAL (BSE-only), FUSION (NSE) and COCHINSHIP.
  - DATA-014 is written against DAL: `revenue_ttm` becomes the filed four-quarter sum (screener.in ≈9.97 cr) with provider `bse`.
  - The class case the fix was not written against is FUSION: exchange ≈1,699 cr, Yahoo's 858 cr is disclosed.
  - A registry test shows that an IN fundamentals request tries the exchange lane first and that a US symbol never does.
  - DATA-076: a captured fixture where Yahoo's growth scalar and the exchange-computed MRQ-YoY disagree surfaces a conflict; one where they agree does not.
- **Files.** New `exchange_financials.py`, `provider_registry.py`, `correctness_gate.py`, `growth_check.py`, `yfinance_provider.py` (only if the merge needs a hook), `models/fundamentals.py` + `types/data.ts` (only if a field is unavoidable; same commit), tests, fixtures.

**R15-LEAD-004 (TTM cadence label).**
- **Mechanism.** `reconcile_revenue` labels "annual, not trailing-4Q" whenever fewer than four of Yahoo's quarterly columns fall inside 330 days (`correctness_gate.py:596-604`). Yahoo's IN quarterly frames skip quarters (LEAD-015's DHANBANK gap), so a quarterly filer is labelled half-yearly.
- **Fix.** Derive the cadence from the filed periods. Use the exchange lane's period ends when present, else the median gap between Yahoo's period ends (about 91 days means quarterly, about 182 half-yearly). A quarterly cadence with a missing column is labelled "trailing figure spans a provider gap", never "half-yearly".
- **Test.** JONJUA (half-yearly) keeps its label. DHANBANK (quarterly with a Yahoo gap) is not labelled half-yearly.
- **Files.** `correctness_gate.py`, `test_correctness_gate.py`.

**R15-LEAD-015 (statement gap and labels).**
- **Mechanism.** Quarterly statements are passed through with the provider's own columns. DHANBANK 2025-09-30 is absent with no marker. openbb labels annual periods with ISO dates, yfinance with years.
- **Fix.** Normalise at the registry, where every provider routes. Period labels become ISO period-end dates for both annual and quarterly (the batch-5 D-B5-6 quarterly convention, extended to annual). A missing expected quarter between two present ones becomes an explicit gap period with null values and a gap flag.
  - This changes the annual label format, so grep every consumer of `FinancialStatement.periods` (routes, `agent_tools/fundamentals.py`, frontend statement tables, the screener seed) and list any that parse a bare year in `issues[]`.
  - If the change is unsafe for a consumer outside W1's files, keep the annual format and do the gap marker only, recording the reason.
- **Test.** A DHANBANK-shaped fixture yields a gap row for 2025-09-30. A mixed-provider annual pair yields one label format.
- **Files.** `provider_registry.py`, `routers/fundamentals.py` (only if needed), models + `types/data.ts` if a gap flag field is needed (same commit), tests.

**R15-DATA-050 + R15-DATA-060: one class (out-of-coverage reported as a 502).**
- **Mechanism.**
  - `corporate_disclosures.get_results_calendar` (`corporate_disclosures.py:592-615`) calls only `nse_provider.get_results_calendar`, so a BSE-only or SME name raises. `get_announcements` raises "not a known … instrument" for any non-NSE/BSE symbol (`:504-516`).
  - `routers/disclosures.py:64-150` maps every `ProviderError` to 502.
  - An ADR (SIFY) has no ownership lane at all.
- **Fix.**
  - Add a BSE results/board-meeting lane (BSE's forthcoming-results / board-meeting feed for the scrip code, merged with NSE for dual listings, deduped by date and purpose).
  - Give every disclosure route and tool the C3 `coverage`/`note`: `not_applicable` for a non-Indian instrument and `venue_not_covered` for a venue with no feed. Transport and upstream failures stay 502.
  - Add `services/sec_ownership.py`. For a US-listed ADR it finds the latest 20-F through `sec_filings_provider.list_filings`/`get_filing_sections` (import only) and parses the Major Shareholders item into holder, percentage and as-of rows. It serves them on the shareholding route and tool as `provider: "sec-20f"`. It is a disclosed lane, not a merge with the Indian SHP.
- **Test.**
  - JONJUA/DAL (BSE-only) results fixtures give 200 with events. ELCIDIN gets its BSE Q1 FY27 filing.
  - AAPL shareholding gives 200 `not_applicable`.
  - The 20-F lane is written against SIFY. Pin on a second ADR fixture (e.g. INFY or WIT, whichever files a 20-F with a major-shareholders table) as the case not written against.
  - A transport failure is still 502.
- **Files.** `corporate_disclosures.py`, `bse_provider.py`, new `sec_ownership.py`, `routers/disclosures.py`, `agent_tools/disclosure_tools.py`, `models/announcements.py` + `types/data.ts` (same commit), `models/__init__.py`, tests, fixtures.

### W2: `delegate-runs-runtime` (opus, 13 entries plus the runtime half of RESEARCH-024)

**R15-AGENT-034 (unbounded by omission).**
- **Mechanism (refuter-corrected).** An empty box becomes `undefined` (`BudgetConfig.tsx:41-44`). JSON drops it (`delegate-runs.ts:120-125`). `RunBudget` ceilings are Optional with no floor (`models/run.py:53-59`). `BudgetGuard.breach` skips `None` (`budget_guard.py:158-172`). `asyncio.timeout(None)` is a no-op (`run_manager.py:145-152`). Truly unbounded needs all four boxes cleared; 0 and negatives abort instantly.
- **Fix.**
  - Server floor in `launch_run`: every `None` ceiling is filled from one server default equal to the client's `DEFAULT_DELEGATE_BUDGET` (120k tokens, $1, 600 s, 12 steps), and `Field(gt=0)`.
  - The client falls back to the default on an empty box and never sends 0.
- **Test.** POST a run with `{}` budget: the guard carries all four defaults. `max_steps: 0` gets 422.
- **Files.** `models/run.py`, `run_manager.py`, `BudgetConfig.tsx`, tests.

**R15-AGENT-035 + R15-LIFECYCLE-013 (resume loses config).**
- **Mechanism.**
  - `resume_run` spawns with `provider=None, model=None` (`run_manager.py:~460-470`). `runs_store._PERSISTED_OPTION_KEYS = ("research_depth", "region")` (`runs_store.py:81`).
  - The resume and answer routes accept no key (`routers/runs.py:113-135`, `RunAnswerRequest` has only `answer`).
  - Cost is reset to `RunCost()` on resume.
  - `resumeDelegateRun` has no caller.
- **Fix.**
  - Persist `provider` and `model` (never the key) at launch.
  - Resume and answer take the BYOK key in a request header (never the body, never persisted, never echoed).
  - Cost accumulates across resumes.
  - Add a Resume control on an `error` row in `AgentsRail`, which reads the provider key the way the launch path does.
- **Test.** Launch with openrouter/model X, breach, resume: `invoke_agent` gets the launch-time provider/model and the header key. Cost after resume is at least cost before. A router test shows the key never appears in any response or the DB.
- **Files.** `runs_store.py`, `run_manager.py`, `routers/runs.py`, `models/run.py`, `delegate-runs.ts`, `AgentsRail.tsx`, tests.

**R15-AGENT-036 (checkpoint order).**
- **Mechanism.**
  - `_drive_run` writes the history and then the prompt (`run_manager.py:127-129`).
  - `resume_run` takes "the first user turn" as the prompt (`:437-452`).
  - `answer_run` appends the answer as a raw dict (`:391-396`).
  - So an answer puts the original prompt after it, and a second answer makes the first answer the prompt.
  - Tool results are never checkpointed.
- **Fix.** The checkpoint becomes `{prompt, turns[]}` (a versioned JSON object; an old list-shaped row is read as legacy). An answer is sent as the new prompt, with the prior turns plus the original prompt as history. Checkpoint tool steps as `[tool name → one-line result]` turns so a resume sees what ran.
- **Test.** launch → pause → answer → pause → answer: the provider receives prompt, turns and answers in order (the P1a/P1b scenario).
- **Files.** `run_manager.py`, `runs_store.py`, tests.

**R15-AGENT-037 + R15-AGENT-038 (breach decoupled from control flow).**
- **Mechanism.**
  - `_on_round_usage` only sets a flag (`run_manager.py:133-140`). `invoke_agent` calls it at the `LLMDoneEvent` and then `break`s to tool dispatch without yielding (`agent_runtime.py:2015-2024`), so the round's tools run and the next request is sent.
  - `breach()` uses `>=` (`budget_guard.py:168-171`), and `breach_reason` wins even when the generator finished (`run_manager.py:~183-195`).
  - `breach_reason` also carries agent error text: one variable, two meanings.
- **Fix.**
  - `on_round_usage` returns whether the run may continue. `invoke_agent` honours `False` before dispatching pending tools: it yields the round's terminator with a budget notice and returns.
  - `run_manager` keeps `breach_reason` and `agent_error` separate.
  - A turn that ended with a final answer (no pending tools) is `done` even when it touched a ceiling; the detail notes the ceiling.
  - N steps means exactly N provider rounds.
- **Test.** `max_tokens=1000` with a 100k-token tool round gives exactly one provider call and status `error` with the reason. A one-shot answer with `max_steps=1` is `done`. `max_steps=1` with a tool round gives one provider call and `error`.
- **Files.** `agent_runtime.py`, `run_manager.py`, `budget_guard.py`, tests.

**R15-AGENT-039 (plan and activity).**
- **Mechanism.** `_planner_enabled` is True only for `mode == "agent"` (`agent_runtime.py:120-122`). The driver flattens tool events to `"[tool_use name]"` (`run_manager.py:~163-172`). The run wire has no activity (`delegate-runs.ts:61-69`). The rail shows tokens and $ only (`AgentsRail.tsx:94-108`).
- **Fix.**
  - A delegate launch runs the existing `decompose` pre-pass inside the detached task.
  - A compound prompt with more than one step parks the run in a new `planned` status with the plan persisted, until the user presses Start (or Discard) in the rail (`POST /runs/{id}/start`). A non-compound prompt starts directly.
  - The run row persists a typed `activity` list (`{tool, status, summary}`, capped) written per tool event. The rail renders the plan and the activity.
  - Mirror the status and fields in `delegate-runs.ts`/`agent-runs.ts`.
- **Test.** A compound delegate launch returns a run in `planned` with steps. Start runs it. `GET /runs/{id}` lists activity rows for a scripted tool round. A vitest shows the rail renders the plan and Start.
- **Files.** `agent_runtime.py`, `run_manager.py`, `runs_store.py`, `routers/runs.py`, `models/run.py`, `delegate-runs.ts`, `agent-runs.ts`, `AgentsRail.tsx`, tests.

**R15-CODE-AGENT-010 (state machine).**
- **Mechanism.** `cancel_run`/`pause_run` check nothing (`run_manager.py:~335-370`). `resume_run` checks only a live task. `update_run` writes any status (`runs_store.py:265-320`). The router classifies by substring (`routers/runs.py:130-135`) and maps the same error to 404 in answer and 409 in resume. A test pauses a completed run (`test_run_manager.py:258-266`).
- **Fix.** One transition table (including `planned` and `paused`) enforced in the store as a conditional UPDATE. `rowcount == 0` raises a typed `RunStateError` (409); an unknown run raises `RunNotFound` (404). No substring matching. Replace the test that pauses a completed run with one on a running run, and give the reason in the commit.
- **Test.** cancel, resume and pause on a `done` run each give 409 and leave the row unchanged.
- **Files.** `runs_store.py`, `run_manager.py`, `routers/runs.py`, tests.

**R15-CODE-AGENT-011 (dead pause plane): wire it (C5).**
- **Mechanism.** `pause_run` has no production caller (`run_manager.py:~355-370`) and no route or capability. Status `paused`, the `question` column, `answer_run`, the answer route and the rail's answer form never execute. Also dead: `resumeDelegateRun` (given a caller by AGENT-035), `clearFinished` (drops `paused`), `active_run_ids`, `RunLaunchResponse`.
- **Fix.**
  - Add `ask_user` per C5. When the delegate driver sees an `ask_user` tool_use it checkpoints, sets `paused` with the question, and ends the task; `answer_run` resumes with AGENT-036's order.
  - Add `ask_user` to the allow-list of every first-party agent JSON that can be delegated.
  - Delete `active_run_ids` and `RunLaunchResponse`. `clearFinished` keeps `paused`.
  - Correct the module docstring.
- **Test.**
  - A scripted delegate round that calls `ask_user` pauses the run with the question. Answering resumes it, and the provider sees the answer.
  - Catalog parity stays green, and a new assertion shows `ask_user` is absent from the MCP projection and from foreground (`mode="agent"`) tool sets.
- **Files.** `catalog.py`, `agent_runtime.py`, `run_manager.py`, `sidecar/agents/*.json`, `models/run.py`, `agent-runs.ts`, tests.

**R15-LIFECYCLE-012 (durability row-deep).**
- **Mechanism.** No startup sweep exists: a `running` row survives a restart forever. The checkpoint is written only on terminal exits (`run_manager.py:~180-230`), and the `CancelledError` path writes no status.
- **Fix.**
  - At the first store open in a process (C7, not the lifespan), rows in `running`, `planned` or an in-flight `paused` state whose task cannot exist become `error` with "interrupted by sidecar restart". Keep a genuinely paused run (question outstanding) paused: it is resumable by design.
  - Write the checkpoint inside `_on_round_usage`, which already writes cost.
- **Test.** Insert a `running` row, open the store in a fresh process state: the row is `error` with that detail. A run cancelled mid-round has a non-null checkpoint and resumes.
- **Files.** `runs_store.py`, `run_manager.py`, tests.

**R15-UI-040 (client owns server truth).**
- **Mechanism.** The rail is in-memory. The poller skips sidecar runs without a local mirror (`delegate-runs.ts:~196-200`). Cancel is optimistic, and its `response.ok` is never read (`:~287-297`).
- **Fix.** `adoptSidecarRuns()`: on rail mount, `GET /runs` and adopt `running|planned|paused` rows into the store, then `ensurePolling()`. Durable cancel is pessimistic: the row flips on `ok`, else it shows "cancel failed — retry".
- **Test.** Vitest: boot adoption of a sidecar-only running run; a failed cancel leaves the run running with the retry message.
- **Files.** `delegate-runs.ts`, `agent-runs.ts`, `AgentsRail.tsx`, tests.

**R15-AGENT-046 (tool-call identity).**
- **Mechanism (corrected at base).**
  - The leak rescue already mints `leaked_<uuid>` (`tool_call_rescue.py:113`). Still broken:
    - Ollama emits `''` (`ollama.py:235`).
    - Gemini emits `f"{name}_{index}"` per stream (`gemini.py:167`).
    - The auto-publish id derives from the provider id (`agent_runtime.py:1222,1316`).
  - `action_ledger.get` never consumes (`action_ledger.py:91`).
  - The frontend skips acking an empty id (`host-actions.ts:1540`).
- **Fix.**
  - In one place in `invoke_agent`, where tool-use events arrive, mint `call_<uuid>` whenever the provider's id is empty or already seen in this conversation. The assistant tool-use turn, the tool-result turn and every derived id (`__autobrief`, `auto-backtest-`) then use the minted id.
  - The ledger read that grounds a result consumes the ack. The ack wait keeps a non-consuming peek.
  - No frontend change is needed: minted ids are never empty.
- **Test.** Two Ollama rounds, each with a host action carrying `''`, give distinct non-empty ids, and both acks resolve `applied`. A prior `__autobrief` ack does not confirm a new brief.
- **Files.** `agent_runtime.py`, `action_ledger.py`, tests.

**R15-LEAD-014 (repair accepts a schema echo).**
- **Mechanism.** `_repair_tool_args` (`llm/openai.py:498-560`) accepts any parsed dict that passes `jsonschema.validate`. The tool's own schema echoed back (`{"type": "object", "properties": {…}}`) validates for any tool with no `required` keys and no `additionalProperties: false`.
- **Fix.** Reject a repair reply whose top-level keys are JSON-Schema keywords (`type`, `properties`, `required`, `additionalProperties`, `$schema`, `description`) that are not the tool's own property names, or that equals the sent schema. Return `None`, so the existing invalid-args sentinel carries the failure.
- **Test.** The fix is written against the `price_data` schema echo. Pin on a tool with no required fields, whose echo validates today (the case not written against).
- **Files.** `llm/openai.py`, `test_llm_openai*.py`.

**RESEARCH-024: runtime half (C4).**
- **Fix.** Forward `domain` (falling back to the URL host) and `published_at` in `_auto_publish_event`'s FAST mapping (`agent_runtime.py:1253-1262`).
- **Test.** A FAST payload row with `published_at` and a URL yields a dated, host-labelled source.
- **Files.** `agent_runtime.py`, `test_agent_runtime*.py`.

### W3: `unattended-platform-chart` (opus, 10 entries, 2 highs)

**R15-AGENT-023 (high: nothing runs unattended).**
- **Mechanism (refuter-confirmed).**
  - The only run starts are `POST /workflow/run` (`routers/workflow.py:39`) and `POST /agents/{id}/runs`.
  - No scheduler or trigger exists (`find sidecar -iname '*schedul*'` is empty).
  - The only output nodes are `action.log` and `action.notify_desktop` (`workflow_nodes/__init__.py`, `node-registry.ts:135-149`).
- **Fix.**
  - `services/workflow_scheduler.py`: one asyncio loop, started and stopped in the app lifespan (C7). It runs while the app is open, and that ceiling is stated in the UI copy.
  - Schedules are persisted in a `schedules` table of the workflow DB: id, workflow_id, trigger, enabled, last_fired_at, last_seen key, last status and detail.
  - Two triggers:
    - `interval` (every N ≥ 5 minutes).
    - `announcement` (symbol + phrase): it polls C1, fires once per new matching announcement, and hands the announcement to the run as input.
  - A fire runs the saved workflow through the same engine path `POST /workflow/run` uses, with the batch-5 per-node timeout. It never overlaps its own previous run and records the outcome.
  - New `action.webhook` node: POSTs `{workflow, node, value}` JSON to a user URL, https only (plus `http://localhost`), with a 10 s timeout and the result `{status_code}` or an error.
  - The URL is a secret, per BYOK.
    - It is stored in the OS keychain.
    - The node config holds only a `secret_ref`.
    - The renderer registers ref→URL with the sidecar in process memory through a request header, at boot (`page.tsx`) and on save.
    - The sidecar never persists, logs or echoes it; a list route returns refs only.
  - Add `/workflow/schedules` CRUD, with a models + `types/workflow.ts` mirror in the same commit.
  - Add a Schedule control in the node editor for the current saved workflow: create, enable, delete, last fired and status.
  - Register the node in `BUILTIN_NODE_SPECS`, `node-registry.ts` and the shared fixture.
- **Test.**
  - Fake clock: an interval schedule fires once when due and not again before the next interval.
  - An announcement trigger fires once per new matching item (fixture feed) and not on a repeat poll.
  - The webhook node posts to an `httpx.MockTransport` stub with the resolved URL.
  - The URL never appears in the DB, a response or a log record (caplog).
  - Vitest: the Schedule control creates an interval schedule.
- **Files.** New `workflow_scheduler.py`, `workflow_store.py`, `routers/workflow.py`, `models/workflow.py`, `types/workflow.ts`, `workflow_nodes/__init__.py`, `builtin.py`, the fixture, `node-editor/*`, `store/workflow.ts`, `page.tsx`, `app.py`, tests.

**R15-CODE-PLATFORM-018 (reopened: the GIL).**
- **Mechanism (batch-5 verifier).** The quant nodes and tools call `asyncio.to_thread` (`quant_nodes.py:52-85`, `quant_tools.py:54-98`), but QuantLib's SWIG calls hold the GIL. A 20k-step binomial node blocked `/health` for 6.4 s. The sync `/quant` routes (`routers/quant.py:36-70`) block the same way.
- **Fix.**
  - `services/quant/pool.py`: `async run_quant(fn, req)` over a lazily created `ProcessPoolExecutor` with the `spawn` context and a small worker count. Nodes, tools and the four routes (made async) all route through it. The in-process lock stays as the per-worker guard.
  - Add `multiprocessing.freeze_support()` first in `main.py`'s entry, and a pool `shutdown()` in the lifespan `finally`.
  - Record the ceiling with a `ponytail:` comment: a running pricing cannot be cancelled mid-flight; a node timeout abandons the result.
- **Test.** `run_quant` executes the pricer in a different PID (deterministic, and pins the mechanism). The integrator does the live check against the **built** binary: a 20k-step binomial node while `/health` stays under 1 s.
- **Files.** `services/quant/pool.py`, `quant_nodes.py`, `quant_tools.py`, `routers/quant.py`, `main.py`, `app.py`, tests.

**R15-LEAD-012 (high: interpreter not pinned).**
- **Mechanism.** The three ensure scripts create their venvs with a bare `python3` (`ensure-sidecar.mjs:98`, `ensure-openbb-mcp-sidecar.mjs:108`, `ensure-sec-edgar-mcp-sidecar.mjs:98`), and only when the venv is missing. On this machine `python3` is 3.14 (`/opt/homebrew/bin/python3.13` exists). Nothing asserts the version.
- **Fix.**
  - One `scripts/build-python.mjs` exporting `resolveBuildPython()`, used by all three scripts:
    - It honours `VYSTED_PYTHON`, else tries `python3.13`, else `py -3.13` on Windows.
    - It verifies `sys.version_info[:2] == (3, 13)`.
    - If no 3.13 is found, it fails with a message naming the fix.
  - An existing venv whose interpreter is not 3.13 is recreated.
- **Test.** No committed test: the repo keeps no scripts tests (see `CODE-PLATFORM-028`). The proof is the integrator's clean `--force` build log showing 3.13 for all three venvs.
- **Files.** New `scripts/build-python.mjs` and the three ensure scripts.

**R15-AGENT-052 + R15-AGENT-051 + R15-CODE-FRONTEND-015: one class (bus keys are not dockview ids).**
- **Mechanism (batch-5 not-certified notes, confirmed).**
  - Publishers key the bus `chart-${panelId}` (`ChartPanel.tsx:885,912`), `"equity"` (`EquityOverviewPanel.tsx:691`) and `"backtest-panel"` (`BacktestResultView.tsx:424,437`).
  - `PanelHost` focuses the dockview ids (`PanelHost.tsx:187`: `chart`, `equity-overview`, `backtest`).
  - `focusedSymbolFromBus` (`context-provider.ts:224-234`) and the runtime's focused-chart pick (`agent_runtime.py:418-424`, landed in batch 5) look up by dockview id, so both miss.
- **Fix.** Every publisher keys the bus by its dockview panel id: the chart's `panelId` itself, the Equity Overview's and the Backtest's own panel api id. Unregister under the same key. Check that `captureTerminalState`'s `source.startsWith("chart")` still matches every chart id; change `context-provider.ts` only if not.
- **Test.**
  - Correct `panel-context-publishers.test.tsx`'s `"equity"` assertions (they encode the defect; give the reason in the commit).
  - The fix is written against Equity Overview. Pin on a two-chart case not written against: chart-2 focused on INFY gives a snapshot `focusedSymbol` of INFY and a preamble chart of INFY.
- **Files.** `ChartPanel.tsx`, `EquityOverviewPanel.tsx`, `BacktestResultView.tsx`, `context-provider.ts` (only if needed), tests.

**R15-UI-020 (drawings keyed by panel only).**
- **Mechanism.** `DrawingSpec` has `panelId` but no symbol or timeframe (`types/drawings.ts:82-97`). The store is `byPanel` (`chart-drawings.ts`). Chart symbol, timeframe and indicators are not in `SerializedWorkspace`.
- **Fix.**
  - `DrawingSpec` gains `symbol` and `timeframe`. The selector filters on them.
  - Older blobs' drawings are adopted as belonging to the restored symbol and timeframe.
  - Persist `{symbol, timeframe, indicators, compare}` per chart panel in the workspace blob, per the CLAUDE.md rule: `serializeWorkspace` + `autosaveLayout`, a guarded restore, and a `page.tsx` subscription.
- **Test.** Store: a RELIANCE drawing is not returned for TCS. Workspace: round-trip, plus an older blob without the fields restores.
- **Files.** `types/drawings.ts`, `chart-drawings.ts`, `ChartPanel.tsx`, `workspace.ts`, `page.tsx`, tests.

**R15-UI-021 (global delete).**
- **Mechanism.** A window `keydown` deletes `selectedDrawingId` on Backspace/Delete anywhere (`ChartPanel.tsx:696-702`), locked or not.
- **Fix.** Bail when the target is an input, a textarea or contentEditable, or outside the chart container. Skip locked drawings.
- **Test.** Backspace in an input with a drawing selected keeps it. A locked drawing survives Delete.
- **Files.** `ChartPanel.tsx`, tests.

**R15-UI-022 (drawing input side).**
- **Mechanism (refuter-confirmed).** Anchors snap to the bar close. A click past the last bar commits an invisible drawing. Text always reads "label". Lock guards nothing because there is no drag-edit.
- **Fix.**
  - Resolve price with `coordinateToPrice(y)` and time with `coordinateToTime`, or the logical index off-bar.
  - Add an inline text prompt for Text.
  - Lock stops being dead without building drag-edit: a locked drawing refuses keyboard delete (UI-021) and its row's delete button is disabled. Drag-edit is not built. Record this.
- **Test.** ChartPanel click-path tests: the anchor price equals the clicked coordinate's price; an off-bar click places a visible drawing; Text takes the typed label; a locked drawing's delete button is disabled.
- **Files.** `ChartPanel.tsx`, `drawings/*`, tests.

**R15-UI-023 (indicator race).**
- **Mechanism.** Price and indicator effects race on shared refs (`ChartPanel.tsx:349,403,425-429,573-579`). The indicator catch never clears the series. Parabolic SAR reads whatever candles are cached.
- **Fix.** Clear the indicator series at the start of each load and in the catch. Render indicators only for the committed `{symbol, timeframe}` candle set, keyed by a load generation.
- **Test.** `/indicators` rejects after a symbol change: no overlay series remain.
- **Files.** `ChartPanel.tsx`, tests.

### W4: `research-funnel` (opus, 15 entries)

**R15-CODE-RESEARCH-002 (gather not isolated).**
- **Mechanism.** `snapshot_structured`'s leg gather (`fast.py:323-331`) has no `return_exceptions`, so one leg without its own try/except breaks every research path.
- **Fix.** `return_exceptions=True`, and coerce any exception to `None` with a debug log before the folds.
- **Test.** Monkeypatch one cross-check to raise: a result comes back with that leg absent.
- **Files.** `fast.py`, tests.

**R15-RESEARCH-017 (ULTRA fallback parity).**
- **Mechanism.** The heavy branch of `_run_loop` (`deep_research.py:293-312`) has no try/except. The iter branch (`:313-330`) falls back to `deep.run_deep_research` with a note.
- **Fix.** Give the heavy branch the same try/except, fallback and note. Deleting or extracting `run_deep_research` is CODE-RESEARCH-003 (next batch).
- **Test.** A raising `run_heavy_research` stub still yields a published single-pass brief with the fallback note.
- **Files.** `deep_research.py`, tests.

**R15-RESEARCH-018 (EDGAR for Indian targets).**
- **Mechanism.** The researcher bucket (`deep.py:829-842`) matches `"sec"` as a substring ("sector", "second") and is region-blind, so an Indian target queries `sec_filings_list`.
- **Fix.** Use `relevance.is_india_target`: India filings sub-questions go to `corporate_announcements`. Match `sec` as a whole word.
- **Test.** An India target's filings sub-question never selects `sec_filings_list`, and "sector outlook" does not match the filings bucket.
- **Files.** `deep.py`, tests.

**R15-RESEARCH-012 (floor not results-first).**
- **Mechanism.** `gather_floor` (`disclosures.py:135-160`) calls `announcement_rows(...)` without `sub_question`. Results banding in `announcement_rows` (`:196-245`) is conditional on it.
- **Fix.** The floor passes `sub_question="results"`, so the results filing ranks first.
- **Test.** 5 newer procedural items and 1 older results item: the results filing is row 1.
- **Files.** `research/disclosures.py`, tests.

**R15-RESEARCH-016 (ULTRA floor never cited).**
- **Mechanism.** `iter.py:364-380`: one guard (`structured.get("disclosures") is None`) controls both the fetch and `_record_web`. ULTRA's pre-seeded snapshot trips it.
- **Fix.** Fetch only when absent, but always record the floor rows once.
- **Test.** An ULTRA run over a stub floor lists the floor rows in `brief.sources`.
- **Files.** `iter.py`, tests.

**R15-RESEARCH-019 + R15-DATA-075: one class (fetch failures collapse to None).**
- **Mechanism.** `visit_for_research` (`extract.py:706-731`) narrows every `fetch_page` outcome to `str|None`, so a 403, an SSRF block or an unsupported type vanishes and no step records it. `_default_pdf_fetch` (`:278`) makes exactly one attempt for bseindia hosts and never tries AttachHis.
- **Fix.**
  - A small `VisitResult(text, reason)`. The research loop records `ResearchStep(status="error", detail=reason)` for a failed visit.
  - For bseindia PDFs, a bounded retry with backoff, and AttachHis when AttachLive 404s.
- **Test.** `fetch_page` returns "HTTP 403": the run's steps include that error. A flaky stub server that fails once then succeeds returns the PDF. A 404 on AttachLive falls to AttachHis.
- **Files.** `extract.py`, `deep.py`/`iter.py` (step record), tests.

**R15-RESEARCH-020 (result cap drift).**
- **Mechanism.** The cap rule is hand-copied into four backends (`mojeek.py:133`, `brave.py:141`, `ddg.py:379`, `searxng.py:262`). SearXNG reads only `maxResults` and never slices.
- **Fix.** One `result_limit(options)` in `base.py` beside `DEFAULT_CITATION_LIMIT`. Delete the copies. Slice in `searxng.py`.
- **Test.** Parametrised over the four backends: `numResults=3` gives at most 3 results and citations.
- **Files.** `search/base.py`, `searxng.py`, `ddg.py`, `brave.py`, `mojeek.py`, tests.

**R15-RESEARCH-021 (index-tail false negative).**
- **Mechanism.** `index_tail = r"[\s-]?\d{2,3}(?![a-z0-9])"` (`relevance.py:415`) reads "BAJFINANCE 200 DMA" as an index name.
- **Fix.** Require a contiguous or hyphenated suffix (drop `\s`), and gate the check behind `_foreign_shadow`.
- **Test.** The fix is written against "BAJFINANCE 200 DMA breakout", which is kept. Pin on "BAJFINANCE 52-week high" (kept, not written against). "KSE-100" is still dropped for a KSE-shadowed target.
- **Files.** `relevance.py`, `test_research_relevance.py`.

**R15-RESEARCH-022 + R15-RESEARCH-023: one class (one marker list, two jobs).**
- **Mechanism.** In `KeylessBackend.search` (`keyless.py:170-176`), `breaker.record_success()` and `any_engine_answered = True` run before `_filter_results`. So a 200 CAPTCHA page resets the breaker and "found nothing" replaces "rate-limited". `LOW_QUALITY_MARKERS` (`:77-92`, including "all rights reserved") is applied per paragraph in `extract.py:233` (correct) and per SERP result in `:109` (destructive).
- **Fix.**
  - Split the list: footer and consent markers stay paragraph-level for `extract.py`. Only interstitial markers ("verify you are a human", "unusual traffic", "access denied", "are you a robot") act at result level, where they are the block-page signal.
  - Filter before recording success. Non-empty rows that filter to zero on interstitial markers call `record_failure()`, note "blocked (challenge page)", and do not set `any_engine_answered`. An all-blocked chain raises the typed rate-limited error.
- **Test.** The stub repro counts a breaker failure, and the all-blocked chain raises rate-limited. A Route Mobile IR row with "All rights reserved" is kept.
- **Files.** `keyless.py`, `extract.py`, tests.

**R15-RESEARCH-024 + R15-UI-038: one class (source contract).**
- **Mechanism.**
  - `Citation` is `{url, title, excerpt}` (`search/base.py:46-57`). `ResearchSource` has no date (`research/models.py:56-71`).
  - The FAST auto-publish labels the domain `"web"` (W2's `agent_runtime.py:1259`).
  - Sonar and Perplexity put `"host (via Perplexity Sonar)"` in `domain`, and `hostOf` prefers `domain` (`brief-ingest.ts:250-259`), so every Sonar citation badges as web.
- **Fix.**
  - `Citation` and `ResearchSource` gain `published_at`. `domain` is always a bare host. Provenance ("via Perplexity Sonar") moves to its own `provider` field.
  - The `types/brief.ts` mirror changes in the same commit.
  - `hostOf` prefers the URL host and falls back to `domain` only when the URL does not parse.
  - The source rail shows the date.
  - C4 is the runtime half (W2).
- **Test.**
  - A SearXNG row with `publishedDate` yields a dated, host-labelled `ResearchSource`.
  - A Sonar-shaped source badges by its URL host, e.g. a sec.gov filing is a filing.
- **Files.** `search/base.py`, the four backends (date passthrough), `web_search.py`, `research/models.py`, `deep.py`/`iter.py` (source recorder), `sonar.py`, `perplexity.py`, `types/brief.ts`, `brief-ingest.ts`, tests.

**R15-UI-092 (broken citations deleted).**
- **Mechanism.** `sanitizeCitationMarkers(brief.markdown, sources.length)` (`brief-ingest.ts:~398,593`) deletes out-of-range `[n]`, and `brief-blocks.tsx:1091` strips them.
- **Fix.** Keep an out-of-range marker as an inert flagged `[?]` titled "citation not in sources", and show a broken-citation count in the Sources header.
- **Test.** `[47]` against 21 sources keeps a flagged marker, with count 1.
- **Files.** `brief-ingest.ts`, `brief-blocks.tsx`, tests.

**R15-RESEARCH-026 (shadow formatter).**
- **Mechanism.** `brief-blocks.tsx:55-101` re-implements number and money formatting (en-US grouping, no currency), so the brief and Equity Overview disagree and an unknown currency reads as bare.
- **Fix.** Delete the local formatters and route through `src/lib/format.ts` with the instrument currency. An unknown currency is stated, not defaulted.
- **Test.** A null-currency metric renders the explicit unknown form. An INR market cap matches Equity Overview's string.
- **Files.** `brief-blocks.tsx`, `format.ts` (additive only), tests.

### W5: `host-actions-portfolio` (opus, 13 entries)

**R15-CODE-FRONTEND-011 + R15-CODE-FRONTEND-007 (one parsed intent, bound at enqueue).**
- **Mechanism.**
  - `describeHostAction` (`host-actions.ts:639-935`) and `applyHostAction` (`:936-1315`) parse inputs independently (`num()`→0 vs the `positionBody` fallback; raw `getPanel` vs `resolvePanelToken`).
  - The proposal stores raw `{name, input}` (`proposed-changes.ts:95-111`). Accept re-resolves the target through `activePortfolio()` and `resolveHolding()`, with a symbol fallback (`:574-604`).
- **Fix.**
  - One `parse(name, input) → Intent` per action, run once at enqueue and stored on the `ProposedChange` (`types/proposed-change.ts`). Describe and apply both read that intent.
  - Portfolio intents bind `{portfolioId, holdingId}` at parse. Apply acts on exactly that pair and fails honestly if it is gone.
  - Keep the per-action switch where it is simplest; the invariant is "one parse".
- **Test.** A table test: for every `HOST_ACTION_NAMES` entry, the describe label and the apply outcome agree (P6, P7b). The P5 two-portfolio scenario changes A's lot, not B's.
- **Files.** `host-actions.ts`, `proposed-changes.ts`, `types/proposed-change.ts`, tests.

**R15-CODE-FRONTEND-009 + R15-CODE-FRONTEND-010: one class (a cast hides a store-API mismatch).**
- **Mechanism.** The `save_screen` duck-typed cast (`host-actions.ts:1274-1295`) calls the real `saveScreen(name)` (`screener.ts:244,658`), which snapshots the on-screen draft. `write_screener_filters` forwards `run` through a cast (`:1217-1226`) into an `applyFilters` that ignores it (`screener.ts:223,338`). The tests mock both.
- **Fix.** Delete both casts. `save_screen` applies the agent's recipe, then saves. The diff says "replaced" when the name exists. `run: true` chains `runScreener()`. Replace the mock tests with tests against the real store.
- **Test.** Real store: `save_screen {criteria: pe<15}` saves pe<15, and `run: true` fires `runScreener` once.
- **Files.** `host-actions.ts`, `screener.ts`, tests.

**R15-AGENT-043 (silent partial apply).**
- **Mechanism.** `parseScreenerCriterion` returns `null` for gt/lt with a non-number value (`host-actions.ts:360-408`), and the list filters the nulls. The label counts the survivors and acks `applied`.
- **Fix.** The parse returns the rejected leaves with reasons. The label and the ack detail say "Wrote 2 of 3 criteria; dropped roe: value must be a number", so the model can retry.
- **Test.** A 3-criterion call with one bad leaf returns the drop reason in the label and the ack.
- **Files.** `host-actions.ts`, tests.

**R15-AGENT-042 (lot identity).**
- **Mechanism.** `publishedHoldings` omits `id` (`PortfolioPanel.tsx:264-273`); `context-provider.extractHoldings` already passes one through. `resolveHolding` falls back to the first same-symbol lot.
- **Fix.** Publish `id`. An ambiguous symbol (two or more lots, no id) refuses with a named choice instead of picking. The diff names the lot.
- **Test.** Two TCS lots: an update by id changes that lot, and an update by symbol alone refuses.
- **Files.** `PortfolioPanel.tsx`, `host-actions.ts`, tests.

**R15-AGENT-041 (no undo).**
- **Mechanism.** `accept()` applies with no pre-image (`proposed-changes.ts:122-155`). The stored `before` is prose (`host-actions.ts:~790-815`). The review renders only `pending` (`ProposedChangesReview.tsx:27`).
- **Fix.** The apply of each data-write intent (portfolio add/update/delete, note write, save_screen replace, watchlist add/remove, set_region) returns a typed pre-image. Applied changes stay listed for the session with Undo, which restores the pre-image and acks nothing new to the runtime.
- **Test.** Apply `portfolio_delete_position`, then Undo: the holding is restored with its id. A note replace plus Undo restores the text.
- **Files.** `host-actions.ts`, `proposed-changes.ts`, `ProposedChangesReview.tsx`, `types/proposed-change.ts`, tests.

**R15-AGENT-032 (claim before outcome).**
- **Mechanism (refuter-corrected).** `ChatSidebar.tsx:980` (and the slash path `:599`) writes "Applied: …" right after `enqueue()`, which fires `accept()` unawaited. `accept()` can re-pend with a detail. The runtime's own divergence check is fed by the real ack, so the harm is a misleading transcript line.
- **Fix.** `enqueue` and `accept` resolve to `applied | staged | failed`. Both call sites write the step line from that value.
- **Test.** Under AUTO, a failing apply leaves no "Applied:" line.
- **Files.** `ChatSidebar.tsx`, `proposed-changes.ts`, tests.

**R15-DATA-088 (validation at the wrong layer).**
- **Mechanism.** `normalizeHolding` (`portfolios.ts:68-88`) coerces a non-finite quantity or cost to 0 and has no sign checks. The agent path guards only `quantity > 0`.
- **Fix.** Return `null` for a non-finite or ≤0 quantity, or a non-finite or <0 cost.
- **Test.** A corrupt blob with a negative cost and a garbage quantity drops those rows.
- **Files.** `portfolios.ts`, tests.

**R15-CODE-FRONTEND-012 + R15-DATA-089 + R15-CODE-PLATFORM-021 + R15-CODE-PLATFORM-022: one class (write-only ledger).**
- **Mechanism (corrected).**
  - Every agent portfolio write also calls `syncPositionToSidecar` (`host-actions.ts:1316-1387`). `sidecarPositionId("h-…")` becomes `undefined`, so PUT/DELETE hit a collection route and get a swallowed 405, and POSTs accumulate.
  - **Correction to CODE-PLATFORM-021:** `GET /portfolio/positions` now has a reader. It is the one-time legacy import (`workspace.ts:864-890`, `modules/portfolio/api.ts:68`, R15-LIFECYCLE-009), so the GET route and `list_positions` stay.
  - `portfolios.ts` carries a dead typed client (`addPosition`/`updatePosition`/`deletePosition`/`refresh`, about `:225-292`).
- **Fix.**
  - Delete the frontend sync (`syncPositionToSidecar`, `sidecarPositionId`, `portfolioUrl`, `positionBody`), the sidecar POST/PUT/DELETE routes (`routers/portfolio.py:27-47`) and the write functions in `portfolio_db.py`.
  - Delete the dead client in `portfolios.ts`.
  - Rewrite the docstrings to one authority claim: the workspace blob owns holdings, and the ledger is the read-only legacy-import source.
  - Update `test_portfolio.py` to the GET-only surface and `host-actions.test.ts:945`, giving the reason: the tests covered the deleted write path.
- **Test.** Accepting a portfolio write makes no network call (fetch spy). `GET /portfolio/positions` still lists seeded rows. POST gets 405.
- **Files.** `host-actions.ts`, `portfolios.ts`, `modules/portfolio/api.ts` (docstring), `routers/portfolio.py`, `portfolio_db.py`, tests.

---

## 3. Integrator run order and gates

1. Work in a scratch worktree (`git worktree add <scratchpad>/b6-int 004-r4-experience-rebuild`), never the main repo: it holds uncommitted register, CLAUDE.md and ledger edits. Run `git branch --show-current` before every merge.
2. Audit each branch through `origin/worktree-agent-b6-<w1..w5>`:
   - `git merge-base --is-ancestor bc03be5 origin/<branch>` (a stale base means re-dispatch).
   - `git diff --stat bc03be5..origin/<branch>` must touch only that writer's §1 files.
3. Merge `--no-ff` in this order, running that writer's pytest and vitest files after each merge:
   - **W1.** C1/C2/C3 are frozen or additive, and `types/data.ts` and `models/__init__.py` land first.
   - **W4.** Provides C4's row fields.
   - **W2.** Consumes C4 and adds `ask_user`, which changes the catalog count every catalog test derives.
   - **W5.**
   - **W3.** `app.py` and `main.py`; imports C1.
   - After W2 and W4: one FAST research through `invoke_agent` yields a dated, host-labelled source (RESEARCH-024 certification).
4. Gates after all five merge:
   - `export PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH`
   - `ruff format --check sidecar && ruff check sidecar`
   - `pnpm format:check`, `pnpm lint`, `pnpm typecheck`
   - `cargo fmt --check`, clippy `-D warnings` and `cargo test` (no Rust is expected to change; run anyway).
   - `node scripts/ensure-all-sidecars.mjs --force` from clean venvs (`rm -rf sidecar/.venv sidecar/*_mcp_subprocess/.venv` in the scratch worktree only). The log must show Python 3.13 for all three venvs (LEAD-012 proof).
   - `pnpm ci-local` in the background, with the exit code recorded.
   - `node scripts/smoke-test-sidecars.mjs`.
   - **CODE-PLATFORM-018 live check against the built binary:** a 20k-step binomial `quant.price_option` workflow node while `GET /health` is polled. Every `/health` returns in under 1 s, and the pricing returns a value (the frozen spawn pool works).
5. Grep checks:
   - `nse_provider.py` has no literal `{"index": "equities", "symbol"` outside `_corporate_index`.
   - `routers/disclosures.py` still maps `ProviderError` to 502 only for real failures, and `coverage` exists on the disclosure models and in `types/data.ts`.
   - `run_manager.py` has no `provider=None,\n        model=None` in `resume_run`, and no `active_run_ids`. `routers/runs.py` has no `"already running" in str(exc)`.
   - `ollama.py`'s `or ""` id is either gone or overridden by the runtime mint (test-pinned).
   - `ensure-*.mjs` has no bare `"python3"` venv creation.
   - `ChartPanel.tsx` has no `` `chart-${ `` bus key. `EquityOverviewPanel.tsx` has no `source: "equity"`. `BacktestResultView.tsx` has no `"backtest-panel"` bus key.
   - `keyless.py`'s result-level marker list has no "all rights reserved".
   - `relevance.py` has no `r"[\s-]?\d{2,3}`.
   - `brief-blocks.tsx` has no local `formatLarge`/`formatNumber`.
   - `host-actions.ts` has no `syncPositionToSidecar`, no `saveScreen?:` cast and no `as Parameters<typeof screener.applyFilters>[0]`.
   - `portfolios.ts` has no `export function deletePosition`.
   - `ChatSidebar.tsx` writes no `Applied:` before an awaited outcome.
6. Record the §6 decisions in `docs/redesign/DECISIONS.md` and `CHANGELOG.md` at merge. Record LEAD-012's runbook line and CP-018's packaging note. Writers do not edit docs.
7. Certification:
   - `RESEARCH-024` certifies only after W2 and W4 merge.
   - `AGENT-051` and `CODE-FRONTEND-015` certify on AGENT-052's live snapshot (two charts, the second focused).
   - `AGENT-023` records a needs-GUI check for the node-editor Schedule control and the keychain webhook registration if the webview cannot be driven headless. The sidecar side certifies on a fake-clock plus stub-webhook run against the live sidecar.
   - `LEAD-012` certifies on the clean build log.
   - `DATA-014` certifies on live `GET /fundamentals/DAL`: `revenue_ttm` near the filed four-quarter sum, provider `bse`.

---

## 4. Deferred to the next batch (with reason)

**Highs.**
- **`AGENT-007` and `AGENT-017` (one set).** The eval loop and the default-model swap are proven only on live pass^k. OpenRouter's paid balance is negative (DECISIONS_FOR_OPERATOR 2.1), and no Anthropic or Gemini key exists (D35). This is operator-attended.
- **`LIFECYCLE-001`.** Moving the MCP joins and `start_main_sidecar` off Tauri's main thread needs proof from a packaged cold launch (GUI; none this run). A boot regression bricks the app, and the `--onedir` follow-up is Tier-1 (`tauri.conf.json`). This is operator-attended.

**Classes and collisions.**
- **`AGENT-044` + `AGENT-045` (model-symbol-unresolved).** The class seam is the runtime's host-action and tool dispatch (`agent_runtime.py`, W2's sole file, already at 13 entries).
- **`CODE-AGENT-008` (auto-publish layer leak).** It straddles `agent_runtime.py` (W2) and the research tool payload (W4). Take it after C4 lands.
- **`RESEARCH-027` (latency budget).** Same gather as `CODE-RESEARCH-002`; W4 is at capacity.
- **`CODE-RESEARCH-003` (duplicated deep loop).** This batch's `RESEARCH-017` reuses the fallback; delete or extract it next.
- **`RESEARCH-028` + `LIFECYCLE-018` (SearXNG health and hot path).** They need the `app.py` lifespan (W3's this batch).
- **`AGENT-055` + `AGENT-056` (layout templates, destructive arrange default).** They straddle `host-actions.ts` (W5), `store/workspace.ts` and `catalog.py` (W2).
- **`CODE-FRONTEND-019`, `DATA-090`, `UI-046` (workspace persistence).** `workspace.ts` is W3's this batch for UI-020. Capacity.
- **`UI-034` + `UI-035` (portfolio-switch stale target).** `PortfolioPanel.tsx` is W5's this batch. Capacity.
- **`UI-026`, `UI-031`, `CODE-FRONTEND-017`.** Stale responses in three different components (different mechanisms from UI-023). Capacity.
- **`CODE-PLATFORM-017` (two `transform.code` evaluators).** Same engine W3 extends. Capacity.
- **`AGENT-061` + `DATA-061` (ProviderError.kind flattened).** It spans `app.py` (W3) and many routers.
- **`DATA-081` + `UI-053` (slash symbol in a path param).** `ChartPanel.tsx` is W3's.
- **Error-layer cluster (next batch as one writer).** `UI-012`, `UI-014`, `LIFECYCLE-010`, `LIFECYCLE-011`, `CODE-PLATFORM-011`, `UI-013`, `UI-015` + `UI-030`: the `sidecar-client.ts`/`streaming.ts`/retry-hook seam.

## 5. proposed_not_defect (needs the verifier's fresh concurrence; ui-panels area)

- **`R15-UI-041`.**
  - The removed-trading half is moot (a122dbf6, recorded in the entry's note).
  - The open question was whether the rewritten terms disclose licence terms, data accuracy and AI-output caveats. `src/modules/safety/DisclaimerFlow.tsx:28-35` now states:
    - not investment advice;
    - no brokerage connection and no orders;
    - "Market data may be delayed, incomplete or wrong";
    - "AI-generated analysis can be wrong";
    - the PolyForm Strict 1.0.0 or commercial licence line.
  - Nothing remains to fix in code. The copy is the operator's Tier-4 review item (DECISIONS_FOR_OPERATOR 3.2), not a defect. The sibling `UI-044` (the hydrate has no catch) is a different mechanism and stays open.

## 6. Tier-3 decisions (the integrator records them; none is Tier-4)

- **D-B6-1.** Exchange-filed quarterly results are the IN primary for the fields they carry (TTM revenue and profit from four filed quarters, EPS, MRQ-YoY growth). They overlay yfinance field by field, with provider, basis and as-of. yfinance is the flagged fallback.
- **D-B6-2.** A TTM's cadence label comes from the filed periods, never from a count of provider columns.
- **D-B6-3.** Out-of-coverage disclosures answer 200 with `coverage` + `note`. BSE results join NSE. An ADR's major shareholders come from its latest 20-F as a disclosed lane.
- **D-B6-4.** NSE Emerge corporate endpoints use `index=sme`.
- **D-B6-5.** Statement periods are ISO period-end labels. A missing expected quarter is an explicit gap row.
- **D-B6-6.** Delegate budgets have a server floor (the default budget), with every ceiling > 0.
- **D-B6-7.** Run transitions are enforced in the store (409 on an illegal transition). Provider and model persist. Resume and answer take the key in a header. Cost accumulates.
- **D-B6-8.** The checkpoint is `{prompt, turns[]}`, written per round. Orphaned rows become `error` at the first store open.
- **D-B6-9.** A breach stops the loop before tool dispatch. A final answer wins over a touched ceiling. N steps means N provider rounds.
- **D-B6-10.** A compound delegate prompt is planned and waits for Start in the rail. The run row carries a typed activity list.
- **D-B6-11.** FR-028 self-pause is an `ask_user` capability offered only in delegate mode and not projected to MCP. Dead exports are removed.
- **D-B6-12.** The rail adopts sidecar runs on mount. Durable cancel is pessimistic.
- **D-B6-13.** The runtime owns tool-call identity (it mints a uuid for an empty or duplicate id). Acks are consumed once.
- **D-B6-14.** Tool-arg repair rejects a schema echo.
- **D-B6-15.** A sidecar-resident scheduler (runs while the app is open) fires saved workflows on an interval or on an announcement phrase. `action.webhook` posts to a user URL held as a BYOK secret: keychain to process memory through a header, never persisted or logged.
- **D-B6-16.** QuantLib pricing runs in a spawn process pool (`freeze_support` in `main.py`). A running pricing cannot be cancelled mid-flight.
- **D-B6-17.** Build venvs are pinned to Python 3.13 (`VYSTED_PYTHON` override). A venv on another minor version is rebuilt.
- **D-B6-18.** Panel-context bus keys are dockview panel ids.
- **D-B6-19.** Drawings belong to `{symbol, timeframe}`. Chart state persists in the workspace blob. Drawing keys are scoped to the chart. Lock guards deletion (keyboard and button); drag-edit is not built.
- **D-B6-20.** Research changes:
  - Structured legs are isolated.
  - ULTRA falls back like DEEP.
  - India targets never query EDGAR.
  - The floor is results-first and always cited.
  - Visit failures are steps. BSE PDFs retry and fall back to AttachHis.
  - The result cap has one helper.
  - Block pages are engine failures, and footer markers are paragraph-only.
  - Sources carry `published_at` and a bare host, with provenance in its own field.
  - The brief uses `lib/format`.
  - Broken citations are flagged, not deleted.
- **D-B6-21.** Host actions are parsed once into a bound intent that describe and apply share. Data writes keep a typed pre-image with session Undo. Screener drops are reported. `save_screen` saves the agent's recipe, and `run: true` runs. An ambiguous lot refuses. The transcript writes the apply outcome.
- **D-B6-22.** The sidecar positions ledger is the read-only legacy-import source. Its write routes and the frontend sync are deleted.

## 7. Writer ground rules

1. **Worktree.** Work in your own isolated worktree and branch (`worktree-agent-b6-<w1..w5>`). First run `git reset --hard bc03be5b0e9819a546c4c219bfe1878b3c5d5667` and confirm it with `git log -1`. Push after each concrete deliverable.
2. **Commits.** One focused commit per entry or per root-cause group: conventional, no emojis, ending with the session's attribution trailer.
3. **Tests.**
   - Tests go only where the repo keeps them (`sidecar/tests`, `src/**/*.test.ts(x)`, `src-tauri` tests), one focused test per pinned behaviour.
   - Where a class is involved, pin the case the fix was not written against, as named above.
   - Never delete, skip or weaken a test. If a test encodes the defect, fix it and give the reason in the commit body.
   - Never special-case code to satisfy a test.
   - Scratch scripts never become tests. Live captures become fixtures (add only), never live calls in a test.
4. **Checks before committing.**
   - Export the PATH line from §3 first.
   - Before every Python commit: `ruff format <files> && ruff format --check sidecar && ruff check sidecar`.
   - Before every TypeScript push: `pnpm format:check`, `pnpm typecheck`, `pnpm lint` and your vitest files.
   - Run long suites in the background; never pipe them through `head`/`tee` in the foreground.
5. **Scope.**
   - Touch only your §1 files, and honour C1 to C9 exactly: names, signatures and wire strings. A needed change elsewhere goes into `issues[]` with the exact line.
   - No refactoring beyond the entry, and no flags or defensive code for cases that cannot happen. Anything odd outside your entries goes to `issues[]`.
6. **Hard limits.**
   - Never re-add trading.
   - Never touch `CLAUDE.md`, `src-tauri/tauri.conf.json`, `.github/`, `LICENSE*`, `types/plugin.ts`, `r15-fanout.js`, `docs/` or the register.
   - Read no `R15_BRIEF*.md` and nothing under `r15/local/`.
   - No GUI.
   - Never print, log or commit a secret. This includes W3's webhook URLs and W2's resume key.
