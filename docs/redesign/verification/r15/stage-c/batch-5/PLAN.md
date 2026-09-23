# R15 Stage C: Batch 5 Plan (19 highs, plus 37 mediums in the four named areas)

- **Base:** branch `004-r4-experience-rebuild` at `2edcae974425f45b2008e30410e9dbd7116ec505` (batch 4 merged, L24). D81 is merged: nothing here re-adds trading, orders, brokers or a paper account.
- **Author:** batch planner (Opus). I opened the code at each cited line before writing a row. Each mechanism follows the corrected verdict (refuter correction, batch-4 reopen note), not the raw claim. Line numbers are at base.
- **Queue at base (after adjudication):** 0 critical, 25 high, 242 medium, 207 low.
- **Selection:** 56 open entries = 19 highs + 37 mediums.
  - Highs first. 19 of the 25 open highs are taken. The other 6 are in §4 with the reason: live-eval or GUI proof, a feature that depends on this batch's engine work, or a provider lane that collides with two writers.
  - The mediums are all in the four named areas except `CODE-PLATFORM-018/019/020`, `CODE-AGENT-012` and `LEAD-003`. Those five are class-mates of a selected high or share its file and seam.
  - Class rule (a class is a shared root cause, not a shared label). Joined as class-mates: `CODE-PLATFORM-019` (with 004: engine control flow); `CODE-PLATFORM-018` (with 005: the QuantLib date race is reachable from off-loop nodes only with the lock); `RESEARCH-014` (with `AGENT-026`: `finish_reason` carried but never acted on); `AGENT-048` (with `AGENT-025`: untimed LLM round-trips); `UI-054` (with `AGENT-031`: notice matched by prose); `AGENT-052` and `CODE-FRONTEND-015` (with `AGENT-051`: focused identity keyed two ways); `DATA-097` and `DATA-057` (with `DATA-017`: post-snapshot and ghost master rows); `DATA-064` (with `LEAD-011`: the `in_eod_only` mis-reason both name); `DATA-063` (with `DATA-064`: empty-series handling on sibling routes); `DATA-067` (with `DATA-032`: fabricated fields on the same earnings constructors).
  - §5 lists the label-mates and neighbours not taken and why.
- **proposed_not_defect:** none. Every selected entry reproduces as corrected at base. No entry in the four areas is adjudicated away.
- **Models:** all five sets are opus. None is purely mechanical: each carries a data-provider, runtime, safety-adjacent or persistence judgement (see §1).

---

## 0. The 56 entries

| # | Entry | Sev | Root-cause class | Writer |
|---|---|---|---|---|
| 1 | R15-DATA-020 | high | cross-feed pairing compares only free text (residual: templated NSE text vs BSE subject) | W1 |
| 2 | R15-DATA-023 | high | SHP parser ignores the pledge declaration; no pledge field | W1 |
| 3 | R15-DATA-024 | high | no bulk/block/SAST lane | W1 |
| 4 | R15-DATA-025 | high | corporate actions NSE-only and future-dividend-only; no route, model or capability | W1 |
| 5 | R15-DATA-056 | med | SHP FII/DII leg left null when the filed institutions total makes it derivable | W1 |
| 6 | R15-AGENT-060 | med | stale English provenance note contradicts the typed split fields | W1 |
| 7 | R15-AGENT-062 | med | price_data cut to 90 bars with no marker | W1 |
| 8 | R15-AGENT-058 | med | market_overview turns a news outage into `headlines: []` | W1 |
| 9 | R15-CODE-RESEARCH-001 | med | deep-research wall clamp and schema predate the profile walls | W1 |
| 10 | R15-DATA-074 | med | announcements cached only in the router, not the service | W1 |
| 11 | R15-DATA-026 | high | statements annual-only and absent from the catalog (capability W1, route/provider W2) | W1 + W2 |
| 12 | R15-DATA-017 | high | bundled masters without NSE Emerge and no refresh; live search blocked by generic fuzzy hits | W2 |
| 13 | R15-DATA-057 | med | expired RE line in the BSE master ranks above the bank | W2 |
| 14 | R15-DATA-097 | med | a successful empty live search cached forever | W2 |
| 15 | R15-LEAD-011 | high | `_yahoo_symbol` suffixes caret index symbols | W2 |
| 16 | R15-DATA-064 | med | 30m lookback past Yahoo's intraday cap; `in_eod_only` for any empty IN series | W2 |
| 17 | R15-DATA-063 | med | /indicators lacks the empty-series downgrade | W2 |
| 18 | R15-DATA-015 | high | 52w pair: the high reads ok when the low proved the provider window short | W2 |
| 19 | R15-DATA-037 | high | ccxt drops `range_`, fetches a fixed 200 bars | W2 |
| 20 | R15-LEAD-009 | med | earnings/ratings cache keys lack the resolved listing | W2 |
| 21 | R15-DATA-072 | med | Yahoo breaker never hears a history/statement success | W2 |
| 22 | R15-AGENT-020 | high | notes are write-only for the agent (handler W3, catalog declaration W1) | W3 (+ W1 decl) |
| 23 | R15-AGENT-040 | med | history is a silent 10-message prose window | W3 |
| 24 | R15-AGENT-026 | med | done frame always finalised as success (truncated / empty) | W3 |
| 25 | R15-RESEARCH-014 | med | same (Anthropic 4096 cap; synthesis truncation) | W3 |
| 26 | R15-AGENT-025 | med | untimed provider stream and planner pre-pass; no heartbeat or stall watchdog | W3 |
| 27 | R15-AGENT-048 | med | same (tool-arg repair: uncapped, untimed, unmetered) | W3 |
| 28 | R15-AGENT-033 | med | staged host actions narrated as done; nothing corrects it | W3 |
| 29 | R15-AGENT-031 | med | runtime notices matched by a drifted prose regex | W3 |
| 30 | R15-UI-054 | med | same (live instance) | W3 |
| 31 | R15-AGENT-051 | med | preamble names charts[0] as focused | W3 |
| 32 | R15-AGENT-052 | med | bus keys (`chart-chart`, `equity`) never match dockview focus ids | W3 |
| 33 | R15-CODE-FRONTEND-015 | med | focused symbol derived three ways | W3 |
| 34 | R15-CODE-PLATFORM-004 | high | `logic.branch` cannot branch (no skip state; truthy-string set dead) | W4 |
| 35 | R15-CODE-PLATFORM-019 | med | wave-barrier scheduling; no per-node timeout | W4 |
| 36 | R15-CODE-PLATFORM-005 | high | QuantLib process-global evaluation date raced | W4 |
| 37 | R15-CODE-PLATFORM-018 | med | quant nodes/tools price on the event loop | W4 |
| 38 | R15-CODE-AGENT-001 | high | wildcard CORS, no Origin validation on the sidecar and /mcp | W4 |
| 39 | R15-CODE-AGENT-012 | med | invoke_agent MCP tool publishes `api_key` as an argument | W4 |
| 40 | R15-AGENT-059 | med | MCP list tools turn a failing route into an empty list | W4 |
| 41 | R15-CODE-PLATFORM-020 | med | one invalid saved workflow 500s the whole list | W4 |
| 42 | R15-LEAD-001 | high | MCP subprocess requirements unpinned (fastmcp/mcp/httpx) | W4 |
| 43 | R15-LIFECYCLE-008 | high | no persisted log, no diagnostics | W4 |
| 44 | R15-LEAD-003 | med | persisted cache rows outlive a correctness fix | W4 |
| 45 | R15-DATA-110 | high | no seeded US snapshot; a throttled cold sp500 run skips 100% | W5 |
| 46 | R15-UI-055 | med | evaluated-nothing run shown as "no stocks passed" | W5 |
| 47 | R15-UI-056 | med | screener stream error frame discarded | W5 |
| 48 | R15-CODE-DATA-004 | med | region-aware default universe never wired | W5 |
| 49 | R15-CODE-DATA-006 | med | run-completion protocol copied three times | W5 |
| 50 | R15-LIFECYCLE-017 | med | enrichment catch-all at DEBUG; progress only on success | W5 |
| 51 | R15-LIFECYCLE-020 | med | US-only warm loop at boot whatever the region | W5 |
| 52 | R15-UI-045 | med | operator change rebuilds the criterion and drops the value | W5 |
| 53 | R15-DATA-028 | high | earnings default universe is ten US mega-caps; no market-wide India calendar | W5 |
| 54 | R15-DATA-032 | high | proxy statistics written into typed estimate fields | W5 |
| 55 | R15-DATA-067 | med | fiscal quarter inferred from the report month | W5 |
| 56 | R15-LEAD-010 | high | SEC `get_filing` resolves metadata from an unfiltered 40-filing window | W5 |

---

## 1. File ownership: five disjoint sets

A file belongs to exactly one writer. A writer that needs a change in another writer's file does not make it; it goes to `issues[]` with the exact line. "Import only" means read the symbol, never edit the file.

| Writer | Model | Source files | Tests |
|---|---|---|---|
| **W1 `india-disclosures-agent-surface`** | opus | **`sidecar/services/agent_tools/catalog.py` (sole owner)**, `agent_tools/__init__.py`, `agent_tools/disclosure_tools.py`, `agent_tools/price_data.py`, `agent_tools/market_overview.py`, `agent_tools/deep_research.py`, `agent_tools/research.py` (docstring only), `agent_tools/fundamentals.py` (new statements handler), new `agent_tools/*.py` modules W1 creates, `sidecar/services/corporate_disclosures.py`, `sidecar/services/nse_provider.py`, `sidecar/services/bse_provider.py`, `sidecar/services/dividend_actions.py` (only if needed), `sidecar/routers/disclosures.py`, `sidecar/models/announcements.py`, **`types/data.ts` (sole owner)**, `sidecar/agents/*.json` (only if an allow-list needs a new id) | `test_capability_catalog.py`, `test_mcp_catalog_parity.py` (run; edit only for a derived change), `test_corporate_disclosures.py`, `test_nse_provider.py`, `test_bse_provider.py`, `test_disclosure_tools.py`, `test_price_data*.py`, `test_market_overview*.py`, `test_deep_research*.py`, `test_fundamentals_tool.py`, new `test_b5_india_*.py`, fixtures under `sidecar/tests/fixtures/{nse,bse}/` (add only) |
| **W2 `resolver-market-data`** | opus | `sidecar/services/symbol_resolver.py`, `sidecar/services/resolver_masters/*` (JSON masters, `regenerate_bse_master.py`, new `regenerate_nse_master.py`), `sidecar/services/yfinance_provider.py`, `sidecar/services/provider_health.py` (only if needed), `sidecar/services/provider_registry.py`, `sidecar/services/ccxt_provider.py`, `sidecar/services/openbb_mcp_provider.py` (statements period only, only if needed), `sidecar/services/correctness_gate.py`, `sidecar/routers/fundamentals.py`, `sidecar/routers/earnings.py`, `sidecar/routers/history.py`, `sidecar/routers/indicators.py`, `sidecar/routers/crypto.py` | `test_symbol_resolver*.py`, `test_resolve*.py` (not `test_resolve_symbol_tool.py`), `test_yfinance*.py`, `test_provider_registry*.py`, `test_ccxt*.py`, `test_correctness_gate.py`, `test_fundamentals.py`, `test_earnings_router*.py`, `test_history.py`, `test_indicators*.py`, `test_crypto*.py`, new `test_b5_market_*.py` |
| **W3 `agent-runtime-chat`** | opus | `sidecar/services/agent_runtime.py`, `sidecar/services/llm/*.py` and `llm/model_registry.json`, `sidecar/models/llm.py`, `sidecar/services/research/models.py` (step kinds only), `sidecar/services/research/deep.py` + `iter.py` (synthesis truncation note only), `src/modules/chat/ChatSidebar.tsx`, `streaming.ts`, `context-provider.ts`, `message-notices.ts`, `SuggestionChips.tsx`, `src/store/chat-history.ts`, `src/components/PanelHost.tsx`, `src/modules/chart/ChartPanel.tsx`, `src/modules/equity-overview/EquityOverviewPanel.tsx`, `src/modules/backtest/BacktestResultView.tsx` (the three: bus key only), `types/panel-context.ts`, `types/ai.ts` | `test_agent_runtime*.py`, `test_llm_*.py`, `test_oneshot*.py`, `test_tool_loop_e2e.py`, `test_b3_runtime_*.py`, `test_b4_runtime_*.py`, new `test_b5_runtime_*.py`, vitest: `streaming.test.ts`, `ChatSidebar.test.tsx`, `chat-history.test.ts`, `message-notices.test.ts`, `context-provider.test.ts`, `SuggestionChips.test.tsx`, `PanelHost*.test.tsx` |
| **W4 `platform-workflow-boundary`** | opus | `sidecar/services/workflow_engine.py`, `workflow_nodes/__init__.py`, `workflow_nodes/builtin.py`, `workflow_nodes/quant_nodes.py`, `sidecar/models/workflow.py`, `sidecar/routers/workflow.py`, `sidecar/services/workflow_store.py`, `types/workflow.ts`, `src/store/workflow.ts`, `src/modules/node-editor/*` (skipped status and Load-dialog rows only), `sidecar/services/quant/*.py`, `sidecar/routers/quant.py` (only if needed), `agent_tools/quant_tools.py`, `sidecar/app.py`, `sidecar/routers/mcp.py`, `sidecar/services/mcp_server.py`, `sidecar/services/data_cache.py`, `sidecar/main.py`, `sidecar/routers/system.py` + new `sidecar/services/diagnostics.py`, `sidecar/openbb_mcp_subprocess/requirements.txt`, `sidecar/sec_edgar_mcp_subprocess/requirements.txt`, `scripts/ensure-openbb-mcp-sidecar.mjs`, `scripts/ensure-sec-edgar-mcp-sidecar.mjs`, `src-tauri/src/lib.rs`, `src-tauri/src/openbb_mcp.rs`, `src-tauri/src/sec_edgar_mcp.rs`, new `src-tauri/src/diag_log.rs`, `src/components/SettingsPanel.tsx` | `test_workflow_*.py`, `test_quant*.py`, `test_mcp_server.py`, `test_app*.py`, `test_data_cache.py`, `test_system*.py`, new `test_b5_platform_*.py`, Rust `#[cfg(test)]` in the touched crates, vitest: `workflow.test.ts`, node-editor tests, `SettingsPanel*.test.tsx` |
| **W5 `screener-earnings-sec`** | opus | `sidecar/services/screener.py`, `sidecar/routers/screener.py`, `sidecar/services/fundamentals_seed.py`, `sidecar/services/screener_universes/*` (new US seed pack, `regenerate_fundamentals_seed.py`), `sidecar/services/fundamentals_store.py` (only if needed), `sidecar/models/screener.py` + `types/screener.ts` (only if needed, mirrored together), `src/store/screener.ts`, `src/modules/screener/*.tsx`, `sidecar/services/earnings_provider.py`, `sidecar/models/earnings.py`, `types/earnings.ts`, `src/modules/earnings/*.tsx`, `agent_tools/earnings_tools.py`, `sidecar/services/sec_filings_provider.py`, `sidecar/routers/sec_filings.py`, `src/store/sec.ts`, `src/modules/sec/SecFilingsPanel.tsx` (only if needed) | `test_screener*.py` (not `test_screener_tools.py`), `test_fundamentals_seed*.py`, `test_earnings_provider.py`, `test_earnings_tools*.py`, `test_sec_filings_provider.py`, `test_sec_filings_router.py`, new `test_b5_screener_*.py`, vitest: `screener.test.ts`, `ScreenerPanel.test.tsx`, `ScreenerResultsTable.test.tsx`, `ScreenerCriteriaBuilder*.test.tsx`, `EarningsCalendarPanel.test.tsx`, `EpsEstimateGrid*.test.tsx`, `sec.test.ts` |

No writer edits `CLAUDE.md`, `src-tauri/tauri.conf.json`, `.github/`, `LICENSE*`, `types/plugin.ts`, `r15-fanout.js`, `docs/`, `CHANGELOG.md` or the register. Unowned, import only: `sidecar/config.py`, `sidecar/services/research/semantics.py` (`_RANGE_TOLERANCE`), `sidecar/services/research/range_check.py`, `sidecar/services/research/depth.py`, `sidecar/services/locale.py`, `sidecar/services/witness.py`, `sidecar/models/fundamentals.py` (**nobody edits it this batch**), `src/store/notes.ts`, `src/lib/host-actions.ts`, `src/lib/export-artifact.ts`, `src/store/settings.ts`.

### 1.1 Cross-writer contracts

- **C1 statements period (W2 provides, W1 consumes; DATA-026).**
  - W2: `provider_registry.get_income_statement(symbol, region=None, period="annual")`, `get_balance_sheet(...)` and `get_cash_flow(...)` gain `period: Literal["annual", "quarterly"] = "annual"`. Quarterly `periods` are ISO period-end dates (`"2026-06-30"`); annual labels are unchanged (the fiscal year). No model field is added (the existing `FinancialStatement` carries both). The three routes take `?period=quarterly`.
  - W1: the capability id is `financial_statements`, input `{symbol, statement: "income"|"balance"|"cashflow", period: "annual"|"quarterly" (default "annual")}`, `read_handler`, domain `fundamentals`. Its handler calls the three registry functions with `period=`. W1's tests monkeypatch them; the integrator runs one unmocked check after both merge.
- **C2 notes read (W1 declares, W3 implements; AGENT-020).**
  - W1 declares `read_notes`: `kind="per_invocation"`, `read_only=True`, domain `workspace`, input `{scope: string}` ("'global' or a symbol, e.g. 'BDL'"). Description: "Read the user's own notes (their thesis) for a scope. Call it before write_note with mode 'replace', and whenever the user refers to their notes, thesis or plan for a stock."
  - W3: `_build_local_tools` answers it from `snapshot.by_source["__notes__"]` = `{"general": str, "bySymbol": {SYM: str}}`, which `ChatSidebar`/`context-provider` send. Notes do **not** ride `__terminal__`, so `get_terminal_state` stays compact. Wire names are exactly `read_notes`, `scope`, `__notes__`, `general`, `bySymbol`.
- **C3 NSE helpers are frozen (W1 owns, W5 imports; DATA-028).** `nse_provider._get_json(path, params, referer)` and `nse_provider._EVENT_CALENDAR_PATH` keep their names, signatures and behaviour. W5 imports them for the market-wide event calendar (the precedent is `earnings_provider`'s existing import of `_yahoo_symbol`).
- **C4 region in the upcoming cache key (W2; DATA-028 + LEAD-009).** W5 makes `earnings_provider.get_upcoming`'s default universe region-aware. W2 folds the request region into the `/earnings/upcoming` cache key whenever the watchlist is empty.
- **C5 `_yahoo_symbol` and membership signatures are frozen (W2).** `yfinance_provider._yahoo_symbol(symbol) -> str`, `symbol_resolver.is_nse_symbol` / `is_bse_symbol` / `bse_scrip_code` keep their signatures. Their behaviour changes (caret passthrough, Emerge `-SM.NS`, refreshed membership) reach W1's disclosure gates and W5's earnings lane by import. That is intended.
- **C6 `types/data.ts` has one owner: W1.** W2 adds no model field (C1). A writer that finds a field unavoidable puts it in `issues[]`.
- **C7 `data_cache.py` is W4's.** W1 (DATA-074) and W2 (LEAD-009) call `data_cache.get/set` only. W4 adds `data_cache.ensure_build(version)` and calls it from `app.py`'s lifespan.
- **C8 `app.py` is W4's.** W5's LIFECYCLE-020 keeps `screener.start_warm_precompute()` / `stop_warm_precompute()` names and signatures (the lifespan calls them) and changes only what they do.
- **C9 notices are typed (W3 internal).** Every runtime notice (`_publish_divergence_notices`, the new staged-action notice, the truncation and compaction notices) is an `LLMResearchStepEvent` with `step_kind="notice"`. The frontend branches on the kind, never on copy.
- **C10 catalog edits.** W1 makes every catalog edit this batch: the three India capabilities, `financial_statements`, `read_notes`, the `shareholding_pattern` and `price_data` descriptions, and the research `wall_seconds` schema. Tool counts in tests are derived from the catalog, so no other writer edits a count.

---

## 2. Per-writer entries (mechanism, then fix, test and files)

### W1: `india-disclosures-agent-surface` (opus, 10 entries plus the catalog halves of DATA-026 and AGENT-020)

**R15-DATA-020 (residual: cross-feed pairing sees only free text).**
- **Mechanism (batch-4 not-certified note).** `_pair_cross_feed` (`corporate_disclosures.py:368-405`) pairs an NSE and a BSE item only on word overlap >= `_PAIR_MIN_OVERLAP` (0.6, `:324`) within `_PAIR_WINDOW` (10 min). NSE's templated text ("HDFC Bank Limited has informed the Exchange about Schedule of meet") shares under 60% of its words with BSE's subject ("Announcement under Regulation 30 (LODR)-Analyst / Investor Meet - Intimation"), and a boilerplate BSE body ("Enclosed") scores 0 (`_overlap`, `:360-365`). Live at the batch-4 target: HDFCBANK still has about 15 same-filing pairs within 10 minutes, TCS about 10, and HDFCBANK's merged top 5 holds three duplicate pairs.
- **Fix.** Both feeds carry a structured category: NSE `desc` and BSE `CATEGORYNAME`/`SUBCATNAME` (captured in `_nse_row_to_announcement` / `_bse_row_to_announcement`). Add one small canonical-category map (analyst/investor meet, credit rating, press release, newspaper publication, board meeting, results, general updates, and so on) built from the categories seen in live feeds. A pair also qualifies when both items map to the same canonical category inside `_PAIR_WINDOW` on the same IST day **and** each is the only such candidate for the other in that window. Best-first, pair-once selection is unchanged. Keep the text-overlap rule.
- **Test.** Capture live HDFCBANK and TCS rows (NSE + BSE, 40 per lane) into new fixtures (add only). The fix is written against the HDFCBANK schedule-of-meet pairs. Pin on TCS (the case not written against: the 09-05 HyperVault press release and the 09-17 newspaper publication collapse to one row each). Negative: two different same-category filings of one company inside the window stay two rows.
- **Files.** `corporate_disclosures.py`, `test_corporate_disclosures.py`, new fixtures.

**R15-DATA-023 (promoter pledge).**
- **Mechanism.** `ShareholdingPattern` (`models/announcements.py:98-160`) has no encumbrance field. `parse_shp_xbrl` (`bse_provider.py:794-859`) reads only `ShareholdingAsAPercentageOfTotalNumberOfShares` per category member (`_SHP_CATEGORY`, `:690-697`). The only "pledge" in the Python tree is the catalog's announcement-category prose (`catalog.py:713`). A filed "pledge: No" and an untracked pledge are indistinguishable.
- **Fix.** Parse the SEBI SHP pledge/encumbrance declaration for the promoter category (the encumbered-share concepts in Table II; confirm the exact concept names on a live filing) inside the same XBRL pass. Add `promoter_pledged_percent` (pledged or encumbered shares as a percent of promoter holding) and `promoter_pledge_basis` to `ShareholdingPattern`: `"filed"` when the filing states it (including an explicit 0), `None` when the filing carries no declaration. Never infer 0. It rides the BSE lane natively and the NSE-master pattern through `_merge_bse_split` (`corporate_disclosures.py:673`), the way the FII/DII split does. Mirror in `types/data.ts`. The four-quarter trend is the `patterns` list.
- **Test.** A full SHP XBRL fixture with a non-zero promoter pledge yields the percent. CSL and DAL filings (explicit zero) yield `0.0` / `"filed"`. The case not written against: a filing without the declaration yields `None`, not `0.0`.
- **Files.** `bse_provider.py`, `corporate_disclosures.py`, `models/announcements.py`, `types/data.ts`.

**R15-DATA-024 (bulk, block and SAST deals).**
- **Mechanism.** `grep -rniE 'bulk.?deal|block.?deal|\bsast\b'` over `sidecar/ src/ types/` returns nothing. `routers/disclosures.py` serves only `/announcements`, `/results` and `/shareholding` (`:44`, `:74`, `:95`), while the US analogue `sec_insider_transactions` ships.
- **Fix.** One lane, `get_deals(symbol, kind=None)`, over the public exchange feeds: NSE bulk and block deals and SAST (Reg 29) disclosures, plus BSE bulk/block where the scrip is BSE-only. Model `ExchangeDeal {symbol, kind: "bulk"|"block"|"sast", date, party, side, quantity, price, value, percent_after, exchange, source_url}` (fields the feeds do not carry stay `None`). Route `GET /disclosures/deals?symbol=&kind=`. Capability `exchange_deals` (read_handler, domain `filings`, `untrusted_text=False`). Use the existing NSE throttle/session (`_get_json`) and BSE `_http_get`/`_bse_get_json` seams; honour the lane-error contract of `get_announcements` (a failing applicable lane lands in `errors`; all failing raises). Mirror in `types/data.ts`.
- **Test.** One recorded fixture per feed (NSE bulk, NSE block, NSE SAST; add only) parses to typed rows. Route and tool return them. The case not written against: a BSE-only scrip goes through the BSE feed.
- **Files.** `nse_provider.py`, `bse_provider.py`, `corporate_disclosures.py`, `routers/disclosures.py`, `models/announcements.py`, `catalog.py`, `disclosure_tools.py`, `types/data.ts`.

**R15-DATA-025 (corporate actions).**
- **Mechanism.** `nse_provider.get_corporate_actions` (`:632-642`) exists, but its only consumer, `dividend_actions.get_declared_unpaid_dividend`, keeps future-dated dividends only. No BSE lane, route, model or capability exists. A BSE-only name (JONJUA) gets nothing; bonuses, splits, rights and past dividends with record/ex/payment dates are invisible.
- **Fix.** `get_corporate_actions(symbol)` merges NSE (`get_corporate_actions`) and BSE (`BseIndiaAPI` CorporateAction feed by scrip code) into `CorporateAction {symbol, kind: "dividend"|"bonus"|"split"|"rights"|"buyback"|"other", purpose (verbatim), ratio, amount_per_share, ex_date, record_date, payment_date, exchange}`. Ratio and amount are parsed from the purpose line, and `None` when absent. Dedup a dual-listed action by `(kind, ex_date)`. Route `GET /disclosures/corporate-actions?symbol=`. Capability `corporate_actions`. `dividend_actions` reads the merged lane, so BSE-only names get the declared-unpaid leg. The dividend event dates live on these rows (D-B5-1); `Fundamentals` is not touched. Mirror in `types/data.ts`.
- **Test.** JONJUA fixture: two 2026 bonuses (5:40 record 2026-01-23; 7:24 record 2026-09-04) as typed rows. ELCIDIN: the Rs 25 final dividend with its dates. The case not written against: a dual-listed name's NSE and BSE rows for one dividend collapse to one.
- **Files.** `nse_provider.py`, `bse_provider.py`, `corporate_disclosures.py`, `dividend_actions.py`, `routers/disclosures.py`, `models/announcements.py`, `catalog.py`, `disclosure_tools.py`, `types/data.ts`.

**R15-DATA-056 (derivable FII/DII left null).**
- **Mechanism (refuter-corrected: systemic, not CREST-only).** `_shp_summary_from_categories` (`bse_provider.py:862-904`) sets `dii`/`fii` only when the XBRL carries that member but derives `institutions_percent` regardless, so a nil category the filing omits stays null next to a known total (CREST DII null with institutions == FII; VERTEX both null with institutions 0.0; TTC FII null with institutions == DII).
- **Fix.** Derive the missing leg as `institutions - present_leg` when the total is known, the result is >= 0 within rounding and only one leg is missing. Both legs are 0 when the total is 0. Label it with `split_basis: "derived"` (a new optional field; `"filed"` otherwise). Do the derivation where the row is assembled, after the SHP summary cache is read (`get_shareholding`, `:711-751`), so summaries cached before the fix benefit too.
- **Test.** Written against CREST. Pin VERTEX (both legs 0 from a 0 total) and TTC (FII 0 from institutions == DII) as the cases not written against. Negative: both legs missing with a non-zero total stay `None`.
- **Files.** `bse_provider.py`, `models/announcements.py`, `types/data.ts`.

**R15-AGENT-060 (stale provenance note).**
- **Mechanism.** `_shareholding_pattern` (`disclosure_tools.py:67-89`) appends a hard-coded note (`:85-88`) saying the FII/DII split "lives in each quarter's linked xbrl_url filing". The catalog description (`catalog.py:741-747`) says the same, while the payload carries `fii_percent`/`dii_percent`/`split_source`.
- **Fix.** Delete the note: the typed `source`/`split_source`/`split_as_of` (and the new `split_basis`) carry provenance. Rewrite the description: NSE or BSE listings; promoter, public, FII/DII/institutions split and promoter pledge per quarter, newest first.
- **Test.** A RELIANCE payload with `split_source "BSE"` carries no `note` key; the description names FII/DII and pledge.
- **Files.** `disclosure_tools.py`, `catalog.py`.

**R15-AGENT-062 (silent 90-bar cut).**
- **Mechanism.** `range_` defaults to `"6mo"` (`price_data.py:39`), about 126 daily bars; `recent_bars = list(series.bars)[-90:]` (`:59`); the payload carries no count or window.
- **Fix.** Keep the cap (prompt budget). Return `bars_returned`, `bars_available` and `window_start` (the first returned bar) and state the 90-bar cap in the catalog description.
- **Test.** `range=6mo` on a 126-bar stub returns `bars_returned 90`, `bars_available 126` and the 91st-from-last timestamp as `window_start`. The case not written against: `range=1mo` (under the cap) returns equal counts.
- **Files.** `price_data.py`, `catalog.py`.

**R15-AGENT-058 (news outage reads as "no headlines").**
- **Mechanism.** `_headlines` (`market_overview.py:80-90`) catches every exception, including `fetch_news`'s `ProviderError("all news sources failed")`, and returns `[]`. `_market_overview` returns `ok: true` with no failure field. `fetch_news` never returns empty, so `[]` always means an outage.
- **Fix.** `_headlines` returns `(items, error)`; the payload carries `headlines_error` next to `headlines: []` when the feed failed.
- **Test.** `fetch_news` raising yields `headlines_error` and `ok: true` (the indices still resolve).
- **Files.** `market_overview.py`.

**R15-CODE-RESEARCH-001 (deep-research wall cut).**
- **Mechanism.** `run_deep_brief` clamps `wall = _clamp(wall_seconds, 30, 300, profile.wall_seconds)` (`deep_research.py:482`), so an explicit ULTRA 360 becomes 300, while `depth.PROFILES` gives deep 180 and ultra 360. The research capability schema advertises `wall_seconds` default 120, range 30-300 (`catalog.py:421-424`), so a model following it gives the heavy panel `max(60, 120-90)` = 60 s.
- **Fix.** Clamp the ceiling at `max(300, profile.wall_seconds)`. The catalog schema carries no default (the profile decides) and its description states the range from `depth.PROFILES` (import only). Drop the stale numbers from the docstrings in `deep_research.py` and `research.py` (`:195-198`).
- **Test.** `run_deep_brief(q, depth="ultra", wall_seconds=profile.wall_seconds)` keeps the full budget. The schema's stated maximum is >= every profile's wall. The case not written against: DEEP with no `wall_seconds` uses 180.
- **Files.** `deep_research.py`, `research.py`, `catalog.py`.

**R15-DATA-074 (announcements cache at the wrong layer).**
- **Mechanism.** Only the router wraps `get_announcements` in `data_cache` (15 min, `routers/disclosures.py:44-71`). The agent tool calls it straight through `to_thread` (`disclosure_tools.py:50`), and every research `gather_floor` and disclosure researcher goes through the tool, re-fetching the full NSE history (about 2.8 MB for RELIANCE) plus BSE each time.
- **Fix.** One async `corporate_disclosures.get_announcements_cached(symbol, exchange, limit)` (data_cache + `to_thread`, same key and TTL) used by the router and the tool. The router keeps its error mapping.
- **Test.** Two tool calls for one symbol hit the lane fetchers once. The case not written against: a router call followed by a tool call also fetches once.
- **Files.** `corporate_disclosures.py`, `routers/disclosures.py`, `disclosure_tools.py`.

**R15-DATA-026, capability half (C1).**
- **Fix.** Add `financial_statements` (C1) with a handler in `agent_tools/fundamentals.py` returning `{symbol, statement, period, periods, lines}`, capping periods at the newest 8 and saying so in the payload. Add a cue word ("revenue over", "quarterly", "statement", "cash flow", "balance sheet") to `DOMAIN_CUES["fundamentals"]` only if fundamentals is not always-on (it is always-on today, so no change).
- **Test.** Catalog parity passes. With the registry monkeypatched, `period="quarterly"` reaches `get_income_statement(..., period="quarterly")` and the payload carries ISO period labels.
- **Files.** `catalog.py`, `agent_tools/fundamentals.py`.

**R15-AGENT-020, declaration half (C2).** Declare `read_notes` exactly as C2. No handler here.

Run `test_capability_catalog.py` and `test_mcp_catalog_parity.py` after the catalog edits.

### W2: `resolver-market-data` (opus, 11 entries including the route/provider half of DATA-026)

**R15-DATA-017, R15-DATA-097 and R15-DATA-057 (one class: the master is a frozen snapshot with no live rung that works).**
- **Mechanism.**
  - `is_nse_symbol` / `is_bse_symbol` (`symbol_resolver.py:404-416`) are dict lookups into bundled masters (NSE: 2,675 EQ/ETF rows, no Emerge, no generation stamp; BSE: generated 2026-06-09). Every disclosure lane (`corporate_disclosures.py` gates) and `nse_provider._require_nse` gate on them before any network call, so JNPR, DHOOTTRANS and SUMAX 502.
  - `_yahoo_symbol` (`yfinance_provider.py:97-137`) maps an unknown bare IN ticker to `<sym>.NS`; Yahoo serves NSE Emerge names as `-SM.NS` (SUMAX-SM.NS).
  - The live `yfinance.Search` rung runs only when the banded scan returns nothing (`symbol_resolver.py:792-800`), so six generic "Engineering Ltd" fuzzy hits block it for "Sumax Engineering Limited".
  - `DATA-097`: `_live_lookup` (`:1131-1200`) caches a successful empty search under `(query, region)` for the sidecar's life (LRU of 128, no timestamp).
  - `DATA-057` (refuter-corrected): the bundled BSE master carries the expired rights-entitlement line `DHAN-RE` (group `R`, ISIN `INE680A20011`, the only group-R row) as equity, and fuzzy ranking puts it above DHANBANK.
- **Fix.**
  1. New `resolver_masters/regenerate_nse_master.py` builds `nse_instruments.json` from the exchange lists (`EQUITY_L.csv`, `SME_EQUITY_L.csv`, the ETF list) with type `EQ`/`SM`/`ETF` and a `_generated` stamp. Regenerate both masters. `regenerate_bse_master.py` drops group `R` / rights-entitlement ISINs.
  2. The loaders (`_nse_master`, `_bse_master`) also skip RE lines, so an old bundled master is clean too.
  3. Runtime refresh: the first master load schedules (off the hot path, on a background thread) a daily fetch of the same exchange lists into `<data-dir>/resolver_masters/`, and the loaders union the refreshed file with the bundled one. Membership never does network I/O at call time. No calendar-based test that fails when the bundled file ages (D-B5-7).
  4. `_yahoo_symbol` maps an NSE master row of type `SM` to `<sym>-SM.NS` (C5; confirm the suffix live on SUMAX).
  5. The live search also runs when the best banded hit is `BAND_FUZZY` and shares no distinctive (non-generic, non-suffix) token with the query; its rows join the candidates.
  6. `_live_lookup` stores `(monotonic stamp, rows)`; an empty result expires after a few minutes, and a non-empty one stays in the LRU.
- **Test.**
  - A refreshed-list fixture containing JNPR and SUMAX (`SM`) makes `is_nse_symbol` true for both, and `_yahoo_symbol("SUMAX")` returns `"SUMAX-SM.NS"` under IN.
  - DHOOTTRANS through the disclosures gate no longer raises "not a known NSE/BSE instrument" (a `corporate_disclosures` call with the lane fetch stubbed).
  - "Sumax Engineering Limited" with `_live_lookup` stubbed returns the live row among the candidates. The case not written against: another generic-token name, e.g. "Vertex Securities Limited" (confirm a real name that fuzzes only on generic tokens).
  - `DATA-097`: a time-travel test where an empty live result is re-queried after expiry.
  - `DATA-057`: "Dhanalakshmi Bank" leads with DHANBANK and DHAN-RE is absent. The case not written against: `is_bse_symbol("DHAN-RE")` is false.
- **Files.** `symbol_resolver.py`, `resolver_masters/*`, `yfinance_provider.py`.

**R15-LEAD-011 and R15-DATA-064 (one class on the `in_eod_only` reason; plus the caret and 30m mechanisms).**
- **Mechanism.**
  - `_yahoo_symbol("^NSEI")` under IN falls through the dot-free branch to `"^NSEI.NS"` (`yfinance_provider.py:126-131`); Yahoo serves `^NSEI` unsuffixed, so index history is empty (and `market_overview`'s IN index quotes fail with it).
  - `_TIMEFRAME_MAP["30m"] = ("30m", "3mo")` (`:70-78`) exceeds Yahoo's 60-day intraday window, so every 30m request is empty.
  - `_empty_series_reason` (`routers/history.py:16-28`) returns `in_eod_only` for any empty series in an IN context: a 30m miss, a caret index, DAL's no-trade year and an unknown symbol all get "BSE/NSE serve end-of-day only".
- **Fix.**
  - A leading `^` returns the symbol unchanged before the IN branch.
  - `"30m": ("30m", "1mo")`.
  - `_empty_series_reason(symbol, timeframe)` returns `in_eod_only` only for an intraday timeframe on a known IN listing (master member or `.NS`/`.BO`); otherwise `None`, which keeps the chart's generic copy. No new reason string, so `ChartPanel.tsx` is untouched.
- **Test.** `_yahoo_symbol("^NSEI")` under IN is `"^NSEI"`. The case not written against: `"^BSESN"`. 30m history for a stubbed provider requests a period within 60 days. The empty-series reason is `None` for a daily DAL series and for an unknown symbol, and `in_eod_only` for a 5m RELIANCE.NS series.
- **Files.** `yfinance_provider.py`, `routers/history.py`.

**R15-DATA-063 (sibling route without the downgrade).**
- **Mechanism.** `routers/indicators.py:64` calls `provider_registry.get_history` bare, so `EmptySeriesError` becomes a 502 while `/history` returns 200 empty for the same symbol.
- **Fix.** Catch `EmptySeriesError` and return an empty indicators payload with the same typed reason (`_empty_series_reason`).
- **Test.** An empty-series symbol returns 200 with no values from `/indicators`.
- **Files.** `routers/indicators.py`.

**R15-DATA-015 (residual: the 52w high reads ok beside a flagged low).**
- **Mechanism (batch-4 note).** `reconcile_52w_range` (`correctness_gate.py:697-755`) flags each bound independently against research's 10% `_RANGE_TOLERANCE` (imported from `research/semantics.py`). ELCIDIN's low (102,210 vs 87,003) is flagged, but the high 137,000 vs the exchange 144,500 (5.2%) is served `ok`, although both bounds come from the same provider window the low proved truncated.
- **Fix.** When either bound is flagged, flag the other as well, with a reason that names the shared window ("… the provider's 52-week window is shorter than the exchange range's; kept, flagged"). The tolerance is unchanged. Disclose, never substitute.
- **Test.** ELCIDIN two-venue bars: both bounds flagged. The case not written against: a synthetic where only the **high** exceeds tolerance flags the low too; a pair within tolerance on both sides stays `ok`.
- **Files.** `correctness_gate.py`.

**R15-DATA-037 (crypto range dropped).**
- **Mechanism.** The ccxt declaration's `ohlcv` lambda binds `range_` and drops it (`provider_registry.py:122-124`); `ccxt_provider.get_ohlcv` has no range and fetches `limit=200` (`ccxt_provider.py:88-107`); `/crypto/history` takes no range (`routers/crypto.py:44-47`).
- **Fix.** `get_ohlcv(exchange, symbol, timeframe, range_=None)` turns `range_` into `since` (the same range vocabulary and per-timeframe defaults as `_TIMEFRAME_MAP`) and pages `fetch_ohlcv` from `since` to now. The lambda forwards `range_`; `/crypto/history` takes `range`.
- **Test.** A stub exchange returns bars from `since`: `1mo` and `1y` spans differ and `5y` pages beyond one call.
- **Note.** The in-app crypto chart still cannot load a slash pair through `/history/BTC%2FUSDT` (DATA-081, deferred, §4). Certify on `/crypto/history?range=` and `provider_registry.get_history(..., asset_class="crypto")`.
- **Files.** `ccxt_provider.py`, `provider_registry.py`, `routers/crypto.py`.

**R15-DATA-026, route and provider half (C1).**
- **Mechanism.** The three routes (`routers/fundamentals.py:184-199`) are single annual routes. `_statement_lines` labels periods by `col.year` (`yfinance_provider.py:514-521`), which would collide four quarters into one label.
- **Fix.** C1: yfinance quarterly frames (`quarterly_income_stmt`, `quarterly_balance_sheet`, `quarterly_cashflow`) labelled by ISO period end. The registry passes `period` and serves quarterly only from providers that support it (openbb-mcp only if its tool takes a period; otherwise it is skipped for quarterly). The routes take `?period=quarterly`.
- **Test.** A DHANBANK-shaped quarterly frame fixture: the route returns four ISO period-end labels, and the annual route is unchanged.
- **Files.** `yfinance_provider.py`, `provider_registry.py`, `routers/fundamentals.py`, `openbb_mcp_provider.py` (only if needed).

**R15-LEAD-009 (cache keys without the listing).**
- **Mechanism.** `earnings:{normalized}:…` (`routers/earnings.py:88,107,126`) and `ratings:{normalized}:…` (`routers/fundamentals.py:217,236,255`) key on the raw bare symbol, while DATA-029 made resolution region-dependent (IN: INFY.NS; US: the ADR).
- **Fix.** Key on the resolved listing, `_yahoo_symbol(normalized)`. The upcoming key adds the region when the watchlist is empty (C4).
- **Test.** The same bare symbol under IN then US within the TTL calls the provider twice with different listings. The case not written against: a ratings route.
- **Files.** `routers/earnings.py`, `routers/fundamentals.py`.

**R15-DATA-072 (breaker never closes on success).**
- **Mechanism.** `provider_health.record_success(YAHOO)` is called only in `get_quote` (`yfinance_provider.py:337`) and `get_fundamentals` (`:414`); `get_history`, the three statements and `get_analyst_rating` never call it, so history successes neither close the breaker nor reset `consecutive_throttles`.
- **Fix.** Record success on every Yahoo call path that returns data, including the new quarterly functions.
- **Test.** After three throttles open the breaker, a successful `get_history` closes it. The case not written against: a successful statement call.
- **Files.** `yfinance_provider.py`.

### W3: `agent-runtime-chat` (opus, 12 entries including the handler half of AGENT-020)

**R15-AGENT-020 (notes are write-only; C2).**
- **Mechanism (refuter-corrected).** `write_note` is a host action into `src/store/notes.ts`. No capability, snapshot field or preamble line reads notes back: `captureTerminalState` (`context-provider.ts:216-329`) has no notes, and `_render_terminal_preamble` (`agent_runtime.py:381-448`) renders none. Research-space memory does carry `claims`; the notes gap is the real one.
- **Fix.** `ChatSidebar`/`context-provider` send `__notes__` (C2), each note capped at a fixed size with a truncation marker. `_build_local_tools` (`agent_runtime.py:1376-1440`) answers `read_notes(scope)` with the full (capped) text, or an explicit empty. The preamble adds one line listing the scopes that hold a note, plus the focused symbol's note excerpt (a few hundred characters).
- **Test.** A snapshot with `bySymbol.BDL = "exit if promoter pledge > 20%"`: `read_notes({"scope": "BDL"})` returns it; the preamble names BDL under notes. The case not written against: `scope "global"` returns `general`. Vitest: `captureTerminalState` plus the send path includes `__notes__` from the notes store.
- **Files.** `agent_runtime.py`, `context-provider.ts`, `ChatSidebar.tsx`, `types/ai.ts`.

**R15-AGENT-040 (silent 10-message window).**
- **Mechanism.** The client sends `messages.filter(user|assistant).slice(-10)` as prose only (`ChatSidebar.tsx:752-756`); `_coerce_history` drops everything but string user/assistant turns and caps at 10 again (`agent_runtime.py:474-486`). `toolSteps` and `error` stored per message (`chat-history.ts:38-60`) never re-enter history. No marker or meter is shown.
- **Fix.** Deterministic, no extra LLM call:
  - The client sends the whole thread within a character budget; each assistant turn carries its `toolSteps` and `error` as a compact trailer.
  - `_coerce_history` keeps the newest turns verbatim within a budget and folds older turns into one "Earlier in this conversation" message: each older user ask (truncated), each tool step, and each failure verbatim. It is a separate, stable message placed before the recent turns (so AGENT-050's cache breakpoints can land on it later).
  - When folding happens, the runtime emits a `notice` (C9), and the transcript renders an "older turns summarised" marker.
  - The composer shows a context meter from the last `done` usage against the adapter's `context_window` where known (batch-4 `LLMProvider.context_window`), else the token count alone.
- **Test.** A 7-turn thread whose turn 1 says "I only care about FY26 guidance vs delivery for BDL": the provider request on turn 7 contains that sentence inside the summary. The case not written against: a turn-2 tool failure ("corporate_announcements: BSE lane failed") appears in the summary on turn 8. Vitest: the marker renders on a `notice` of the compaction kind.
- **Files.** `agent_runtime.py`, `ChatSidebar.tsx`, `chat-history.ts`, `streaming.ts`.

**R15-AGENT-026 and R15-RESEARCH-014 (one class: `finish_reason` carried but never acted on).**
- **Mechanism.**
  - Adapters forward `finish_reason` (Anthropic `stop_reason` at `anthropic.py:110,142-146`; OpenAI `openai.py:785-787`). `streaming.ts:363` parses `finishReason`, but the `done` branch hands `onDone` only usage. `invoke_agent` special-cases only `content_filter` (`agent_runtime.py:1736-1747`), and a provider close without a terminator is patched to a bare `LLMDoneEvent` (`:1750-1758`).
  - `DEFAULT_MAX_TOKENS = 4_096` (`anthropic.py:37`) is the only value sent.
  - `oneshot.complete` returns partial text on a `max_tokens` finish, so a deep synthesis renders truncated as final.
  - The refuter narrows the chat case to: a clean EOF without `finish_reason`, a 200 non-SSE body, and a zero-text, zero-tool round (the common one).
- **Fix.**
  - In the runtime, next to `content_filter`: `length`/`max_tokens` yields a truncation `notice`; a round that ends with no terminator, or with zero text and zero tool calls, yields `LLMErrorEvent(code="empty_response" | "truncated")`, so the Retry row renders.
  - `onDone` receives `finishReason`.
  - Anthropic `max_tokens` defaults to the model's output ceiling from `model_registry.json` (add the per-model value there).
  - `oneshot.complete_with_usage` surfaces the finish reason; the deep synthesis (`research/deep.py`, and `iter.py` if it synthesises) adds an "answer truncated" note to the brief's `note` when it was cut.
- **Test.** Replay the three junk shapes and a `max_tokens` finish through the runtime with a scripted provider: each produces a notice or an error frame. A synthesis stub cut at `max_tokens` puts the note on the brief. The case not written against: a Gemini/Ollama `length` finish.
- **Files.** `agent_runtime.py`, `llm/anthropic.py`, `llm/model_registry.json`, `llm/oneshot.py`, `research/deep.py`, `research/iter.py`, `streaming.ts`, `ChatSidebar.tsx`, `chat-history.ts`.

**R15-AGENT-025 and R15-AGENT-048 (one class: untimed LLM round-trips).**
- **Mechanism.**
  - `AsyncOpenAI(..., max_retries=0)` has no timeout (`openai.py:327-331`), so the SDK's 600 s read timeout governs.
  - The planner pre-pass awaits `oneshot.complete` with no `timeout` before the first frame (`agent_runtime.py:1623-1628`).
  - `_repair_tool_args` (`openai.py:479-520`) runs one serial, untimed oneshot per failing call, and its usage never reaches the round's usage.
  - `streaming.ts` has no idle timer; the runtime emits no heartbeat.
- **Fix.**
  - An explicit connect/idle timeout on every adapter client, generous on Ollama for a local model load.
  - `timeout=` on the planner call.
  - The runtime emits a lightweight heartbeat frame (new `LLMHeartbeatEvent`, mirrored in `streaming.ts`/`types/ai.ts`) while waiting on a provider or a tool.
  - `streaming.ts` gets a stall watchdog that ends the stream with a "the provider went quiet" error and Retry when no frame arrives within the idle budget.
  - Repairs are capped per round, each carries a timeout (the `NATIVE_SEARCH_ONESHOT_TIMEOUT_S` pattern), and their usage is added to the round's usage.
- **Test.** A hanging provider stub yields an error frame within the idle budget. The planner times out and the turn proceeds. Five failing calls make at most N repairs, each timed, with their usage in the round total. Vitest: the watchdog fires on silence and does not fire while heartbeats arrive.
- **Files.** `llm/openai.py`, `llm/anthropic.py`, `llm/gemini.py`, `llm/ollama.py`, `llm/oneshot.py`, `models/llm.py`, `agent_runtime.py`, `streaming.ts`, `types/ai.ts`.

**R15-AGENT-033 (staged action narrated as done).**
- **Mechanism.** Under ASK, the host-action result says `awaiting_user_review` (`agent_runtime.py:1428-1436`), but the runtime post-checks only publish divergence, so "I've set BDL on your chart" stands.
- **Fix.** At end of stream, when any host action this turn returned `awaiting_user_review`, emit one deterministic `notice` (C9): "Staged for your review: <action summaries>".
- **Test.** An ASK drive with `set_chart_symbol` yields the staged notice. The case not written against: an AUTO drive yields none.
- **Files.** `agent_runtime.py`.

**R15-AGENT-031 and R15-UI-054 (one class: a cross-process contract held by English copy).**
- **Mechanism.** `DIVERGENCE_RE = /did not confirm the publish|kept the previous, richer brief/i` (`message-notices.ts:57`) no longer matches the runtime's "kept the brief already on screen" or "reported the publish failed" (`agent_runtime.py:1238-1250`), which ride `step_kind="engine"` (`:1256`). Each suite pins its own copy.
- **Fix.** C9: the runtime emits the three divergence lines with `step_kind="notice"`; `isDivergenceNotice` becomes a kind check; the regex is deleted. Add `"notice"` to the step-kind vocabulary (`research/models.py`) if it is enumerated. The old test pinning the stale copy encodes the defect: fix it and say why in the commit.
- **Test.** Python: all three divergence branches emit `step_kind "notice"`. Vitest: a notice-kind step whose copy the old regex never knew renders as a transcript chip, not a trace row.
- **Files.** `agent_runtime.py`, `research/models.py`, `message-notices.ts`, `ChatSidebar.tsx`.

**R15-AGENT-051, R15-AGENT-052 and R15-CODE-FRONTEND-015 (one class: focused identity keyed two ways, derived three ways).**
- **Mechanism.**
  - `PanelHost` sets `focusedSource` to the dockview id (`chart`, `equity-overview`), but publishers key the bus `chart-${panelId}` → `chart-chart` (`ChartPanel.tsx:881-885`), `equity` (`EquityOverviewPanel.tsx:691`) and `backtest-panel` (`BacktestResultView.tsx:424`).
  - `SuggestionChips` (`:48-66`) and the `ChatSidebar` badge look up `lastEventBySource[focusedSource]` and never find it.
  - `captureTerminalState` finds a focused chart only by `panelId === focusedPanel` (`context-provider.ts:275-278`) and otherwise falls back to `charts[0]`.
  - `_render_terminal_preamble` always renders `charts[0]` as "Focused chart" (`agent_runtime.py:411-414`).
- **Fix.**
  - Every publisher keys the bus by its dockview id (`props.api.id`).
  - One exported `focusedSymbolFromBus(bus, focusedSource)` in `context-provider.ts` is used by the badge, the chips and the snapshot.
  - The snapshot's `focusedSymbol` comes from the focused panel whatever its kind (a focused Equity Overview on INFY yields INFY).
  - The preamble renders the chart whose `panelId` matches `focusedPanel` and names a focused non-chart panel's symbol.
- **Test.** Use the real `default-layout` ids through `setFocusedSource`. A focused Equity Overview publishing INFY while the chart shows SPY: badge, chips and snapshot all say INFY. Python: a two-chart snapshot with the second focused renders the second symbol. The case not written against: a focused Backtest view.
- **Files.** `PanelHost.tsx`, `ChartPanel.tsx`, `EquityOverviewPanel.tsx`, `BacktestResultView.tsx`, `types/panel-context.ts`, `context-provider.ts`, `SuggestionChips.tsx`, `ChatSidebar.tsx`, `agent_runtime.py`.

### W4: `platform-workflow-boundary` (opus, 11 entries)

**R15-CODE-PLATFORM-004 and R15-CODE-PLATFORM-019 (one class: engine control flow).**
- **Mechanism.**
  - `_is_truthy` returns `... in _TRUTHY_STRINGS or bool(value.strip())` (`builtin.py:205-208`), so any non-empty string is truthy and "false"/"no"/"0"/"off" route true.
  - The engine has only ok/error, and a `None` output is an ordinary output, so a node on the un-taken port runs (`workflow_engine.py:210-280`).
  - The ready set is recomputed only after `asyncio.gather` of a whole wave, so a slow node stalls unrelated dependants, and handlers are awaited without `wait_for` (`:366-367`). The MCP `run_workflow` tool awaits the engine with no bound.
- **Fix.**
  - `_is_truthy` maps the falsy strings (`false`, `no`, `0`, `off`, `""`) to False and the truthy set to True, else Python truthiness.
  - `logic.branch` emits a `SKIP` sentinel on the un-taken port. A node whose every input edge carries `SKIP` is recorded `skipped` (new `NodeRunResult.status` and a `node-skipped` event) and propagates skip. Mirror in `types/workflow.ts`; the store and editor render skipped nodes.
  - Schedule with `asyncio.wait(FIRST_COMPLETED)` so each completion releases its own dependants.
  - Wrap each handler in `asyncio.wait_for(node_timeout)` (default above `flow.sleep`'s 300 s cap, overridable per node config), producing a node error. `run_workflow` inherits the bound.
- **Test.** `notify_desktop` on the false port does not run, and its status is `skipped`. The string cases route false. The case not written against: a node two hops below a skipped node is skipped too. A(slow)/B(fast)/C<-B: C starts before A ends. A hung handler ends the node in error at the timeout.
- **Files.** `builtin.py`, `workflow_engine.py`, `models/workflow.py`, `types/workflow.ts`, `src/store/workflow.ts`, node-editor status rendering.

**R15-CODE-PLATFORM-005 and R15-CODE-PLATFORM-018 (one class: QuantLib's process-global date).**
- **Mechanism (refuter-corrected).**
  - `set_evaluation_date` writes `ql.Settings.instance().evaluationDate` (`quant/_common.py:34-41`) and is called by every engine before a lazy `NPV()` (`:57`); `bonds.py:52` and `yield_curve.py:70` write it directly.
  - The four `/quant` routes are sync `def` (threadpool), and a two-thread probe priced a valid call at 0.0 in 1,413 of 3,000 runs.
  - The quant agent tools (`quant_tools.py:53,66,79,97`) and workflow nodes (`quant_nodes.py:46-85`) price synchronously on the event loop.
- **Fix.** One module-level `threading.Lock` in `_common.py`, held from setting the date through the result for every public engine entry: `options.price`, `greeks.compute_greeks`, `bonds.price_bond`, `yield_curve.bootstrap_curve` and the Monte Carlo entry points (a small decorator applied at each). The quant tools and nodes `await asyncio.to_thread(...)`. Mark the global lock with a `ponytail:` ceiling comment.
- **Test.** The two-thread probe (different valuation dates) as a pytest: no 0.0 and each result matches its serial price. The case not written against: a bond and a yield-curve bootstrap on overlapping threads. A long binomial pricing through the workflow node does not block a concurrent coroutine (the loop still ticks).
- **Files.** `quant/_common.py`, `quant/options.py`, `quant/greeks.py`, `quant/bonds.py`, `quant/yield_curve.py`, `quant/monte_carlo.py`, `quant_tools.py`, `quant_nodes.py`.

**R15-CODE-AGENT-001 (wildcard CORS; no Origin check).**
- **Mechanism.** `CORSMiddleware(allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])` app-wide (`app.py:283-288`), justified by the loopback bind (`routers/mcp.py:13-14`). Any browser page can drive `/mcp/` (invoke_agent included) and every REST route.
- **Fix.** Explicit allow-list: `tauri://localhost`, `http://tauri.localhost`, `https://tauri.localhost` (the Tauri 2 webview origins), and `http://localhost:5173` / `http://127.0.0.1:5173` (the Vite dev server, `vite.config.ts:15`). A small ASGI middleware rejects a request whose `Origin` header is present and not listed with 403 before routing; it covers the `/mcp` mount. No `Origin` (local processes, MCP stdio/HTTP clients) passes. Update the comment at `app.py:281-282`.
- **Test.** `Origin: https://evil.example` gives 403 on `POST /mcp/` and on a REST GET; `tauri://localhost` gives 200; no Origin gives 200.
- **Certification note.** The packaged webview's Origin is a GUI fact. The verifier records a needs-GUI check (open the app, confirm panels load) if it cannot observe the header.
- **Files.** `app.py`, `routers/mcp.py`.

**R15-CODE-AGENT-012 (key through a third-party model's context).**
- **Mechanism.** `invoke_agent(agent_id, prompt, api_key=None)` (`mcp_server.py:182-197`) is published as the tool's input schema, and the value rides the POST body.
- **Fix.** Drop the parameter. Take a key from an `X-Vysted-Api-Key` request header on the `/mcp` HTTP request when present (the client's own config, never the model's context); otherwise use the runtime's normal resolution. Never log it.
- **Test.** The `tools/list` schema for invoke_agent has no `api_key`. A header key reaches the invoke body (stubbed route).
- **Files.** `mcp_server.py`.

**R15-AGENT-059 (MCP list tools swallow failures).**
- **Mechanism (refuter-corrected trigger).** `list_agents` / `list_workflows` / `list_runs` (`mcp_server.py:168-180`, `:297-313`, `:350-364`) catch `httpx.HTTPError`, including `raise_for_status` on an in-process 5xx, and return an empty list.
- **Fix.** Return `{ok: false, error}` on any `HTTPError`, the policy the file already uses at `:116-122`.
- **Test.** A 500 from `/agents` yields `ok: false`. The case not written against: `list_runs`.
- **Files.** `mcp_server.py`.

**R15-CODE-PLATFORM-020 (one bad saved row kills the list).**
- **Mechanism.** `list_workflows` validates every row in one comprehension against `extra="forbid"` models (`workflow_store.py:57-63`); `spec.version` is stored but never checked, and `types/workflow.ts`'s "engine refuses unknown majors" is unimplemented.
- **Fix.** Validate per row: invalid rows are logged at WARNING and returned as `unreadable: [{id, name, reason}]` beside `workflows` in `GET /workflow/saved` (additive; mirrored in `types/workflow.ts`; the Load dialog lists them as "can't be opened by this version"). Loading a spec whose version major differs raises a named error.
- **Test.** Insert one bad row: the rest list and the bad row appears under `unreadable`. An unknown major is rejected on load.
- **Files.** `workflow_store.py`, `models/workflow.py`, `routers/workflow.py`, `types/workflow.ts`, node-editor Load dialog.

**R15-LEAD-001 (unpinned MCP subprocess deps).**
- **Mechanism.** `sidecar/openbb_mcp_subprocess/requirements.txt` pins only `openbb-*`, and `sec_edgar_mcp_subprocess/requirements.txt` only `sec-edgar-mcp==1.0.8`. A fresh venv resolves fastmcp 4.x / an httpx2-based mcp, and `--copy-metadata=httpx` fails (`ensure-openbb-mcp-sidecar.mjs:169`, `ensure-sec-edgar-mcp-sidecar.mjs:149`).
- **Fix.** Pin the known-good freeze from the batch-3 integrator: `fastmcp==3.3.1`, `fastmcp-slim==3.3.1` (if resolved), `mcp==1.27.1`, `httpx==0.28.1`, where each subprocess pulls them. Before PyInstaller, each ensure recipe checks every `--copy-metadata` target is installed and fails naming the missing package.
- **Test.** No unit test (build recipe). The integrator proves it with a clean-venv `node scripts/ensure-all-sidecars.mjs --force` in the scratch worktree.
- **Files.** Both `requirements.txt`, both ensure scripts.

**R15-LIFECYCLE-008 (no persisted log, no diagnostics).**
- **Mechanism.** The sidecar and MCP drains `println!`/`eprintln!` only (`lib.rs:225-238`, `openbb_mcp.rs:125-136`, `sec_edgar_mcp.rs:130`); `main.rs` sets `windows_subsystem="windows"` (no console); the sidecar sets only uvicorn's log level (`main.py:125-129`). Nothing persists, and Settings shows only the version.
- **Fix.**
  - `diag_log.rs`: a size-capped rotating file `<data-dir>/logs/vysted.log` (one rotated backup), written by one `log_line(tag, line)` that every drain and `[vysted]` message calls beside its existing print. Std only; no new plugin.
  - The sidecar configures logging once in `main.py` (timestamped records to stderr, which the drain captures).
  - `GET /system/diagnostics` returns version, the status-endpoint JSON (`/health`, provider health, MCP status) and a redacted log tail: `services/diagnostics.py` strips query strings, key-like tokens and public IPs, and drops symbol, prompt, brief and note text.
  - Settings gets "Copy diagnostics": fetch, show the bundle in a preview, then copy (the `BriefPanel` clipboard pattern).
- **Test.** Rust: a drained line lands in the file, and rotation keeps the cap. Pytest: the redactor strips a canary query string, a canary key and an IP. Vitest: the preview renders before the copy.
- **Files.** `src-tauri/src/lib.rs`, `openbb_mcp.rs`, `sec_edgar_mcp.rs`, new `diag_log.rs`, `sidecar/main.py`, `routers/system.py`, new `services/diagnostics.py`, `SettingsPanel.tsx`.

**R15-LEAD-003 (persisted cache outlives a fix).**
- **Mechanism.** `data_cache` rows (SQLite in the data dir) are served until their TTL (up to 24 h) across an upgrade: the batch-2 fabricated SEC rows, and the batch-3 verifier's pre-fix SIL shareholding split.
- **Fix.** `data_cache.ensure_build(version)` stores the build version in a meta row and clears the cache when it differs. `app.py`'s lifespan calls it with `app.version` (C7).
- **Test.** The same version keeps a row; a different version misses it. The case not written against: a second call with the new version keeps rows written after the switch.
- **Files.** `data_cache.py`, `app.py`.

### W5: `screener-earnings-sec` (opus, 12 entries)

**R15-DATA-110 (no seeded US snapshot).**
- **Mechanism (refuter).** The screener already serves stale and seed rows with a basis label (`_field_serving`, `_finalize`, `screener.py:634-870`), but the only seed pack is India (`fundamentals_seed.py:37`). From a Yahoo-throttled IP, a cold sp500 run evaluates 0 of 506 (100% `rate_limited`) and "meets" the latency bar only by failing fast.
- **Fix.** Extend `regenerate_fundamentals_seed.py` to write a US pack (`us_fundamentals_seed.json.gz`, the sp500 universe, the same row shape and per-row `seed_as_of`). `fundamentals_seed` loads both packs, and the store seeds from both. A throttled cold run then evaluates from seed rows labelled `snapshot` with their as-of (the existing ladder), and the result header shows the snapshot age. Build the pack from a live warm store; if Yahoo throttles the build, say so in `issues[]` rather than ship a partial pack.
- **Test.** With the Yahoo batch and per-symbol calls raising `rate_limited` and a seeded tmp store: `skipped_count / total < 5%`, and every evaluated row carries `as_of` and basis `snapshot`. The warm path makes zero network calls (asserted by the stubs, not by a wall-clock check; see D-B5-26).
- **Files.** `screener_universes/regenerate_fundamentals_seed.py`, new US pack, `fundamentals_seed.py`, `fundamentals_store.py` (only if seeding needs it).

**R15-UI-055 (evaluated-nothing shown as "no stocks passed").**
- **Mechanism.** `partial = state.partial and bool(skip_details)` (`screener.py:855`) is true only for a budget cut. The table picks its empty state on `rows.length` (`ScreenerResultsTable.tsx:539`), so a run that evaluated 0 blames the filters, and the throttle line claims cached values it does not show.
- **Fix.** `partial` is also true when `evaluated_count < total` with non-budget skips. The table chooses "Nothing could be screened — the data provider is throttled; retry in a moment" on `evaluated_count === 0`. The throttle line shows only when snapshot rows exist.
- **Test.** Sidecar: all symbols `rate_limited` gives `partial: true`, `evaluated_count 0`. Table: that result renders the throttled copy, not "loosen a threshold".
- **Files.** `screener.py`, `ScreenerResultsTable.tsx`, `ScreenerPanel.tsx`.

**R15-UI-056 and R15-CODE-DATA-006 (the store's stream protocol).**
- **Mechanism.** `processFrame` (`store/screener.ts:535-560`) handles only `progress` and `result`, so an `error` frame falls through to "Stream ended without a result frame" (`:598`). The unary fallback and completion sequence is copied three times (`:401-442`, `:551-564`), and the superseded-run guard is held only by a comment (`:30-36`).
- **Fix.** One local `finish(patch)` (guarded by `isCurrent()`, clears the controller) and one `runUnary()` used by all three paths. `processFrame` handles `error` by finishing with `status "error"` and the server's message, and stops reading.
- **Test.** An error frame puts its message in `store.error`. Run A's late fallback does not touch run B's `lastResult` or `status`.
- **Files.** `src/store/screener.ts`.

**R15-CODE-DATA-004 (region default never wired).**
- **Mechanism.** The store initialises `universe: "sp500"` (`store/screener.ts:290`); `default_universe_for_region` (`screener.py:115-117`) has no caller while the router docstring (`routers/screener.py:74-77`) says it ships.
- **Fix.** The sidecar exposes the default for the request region (reuse an existing universes route if one lists universes; otherwise a small `GET /screener/default-universe`). The store adopts it on first mount unless the user or a saved screen already chose a universe. Correct the docstring. No TS copy of the map.
- **Test.** Vitest: IN region gives `nifty50`; US keeps `sp500`; a restored saved screen is not overridden.
- **Files.** `routers/screener.py`, `screener.py`, `store/screener.ts`.

**R15-LIFECYCLE-017 (enrichment failures hidden).**
- **Mechanism.** `except (TimeoutError, Exception)` logs at DEBUG and returns before `emit` (`screener.py:1024-1036`), so a code bug reads as missing fields and the progress bar stalls.
- **Fix.** Catch `(TimeoutError, ProviderError)` as expected; log anything else at WARNING with the type. Move `done += 1` and the throttled `emit` into a `finally`.
- **Test.** A stub adapter raising `AttributeError` logs a WARNING and progress reaches m/m.
- **Files.** `screener.py`.

**R15-LIFECYCLE-020 (US warm loop at boot).**
- **Mechanism.** `_WARM_UNIVERSES = ("sp500",)` (`screener.py:149`), and the lifespan starts the loop unconditionally (`app.py:127-134`), spending the shared Yahoo circuit on 506 US symbols on an India-first install.
- **Fix.** `start_warm_precompute()` arms the loop (C8); the first screener request starts it with that request region's default universe (`default_universe_for_region`), and a later request from another region switches the target. No boot-time sweep.
- **Test.** No warm cycle before a request. After an IN request the loop warms `nifty50`, not `sp500`.
- **Files.** `screener.py`, `routers/screener.py`.

**R15-UI-045 (operator change drops the value).**
- **Mechanism.** Both editors rebuild a fresh criterion on an operator change (`ScreenerCriteriaBuilder.tsx:161-171`, `CriterionGroupEditor.tsx:175-179`): P/E<8 becomes 0–100 on `between` and 20 on the way back.
- **Fix.** One helper carries the current scalar through (`between` seeds `{min: v, max: v}`; back to a scalar keeps `min`), used by both editors.
- **Test.** `P/E < 8` → `between` gives 8–8 → `<` gives 8. The case not written against: the nested-group editor.
- **Files.** `ScreenerCriteriaBuilder.tsx`, `CriterionGroupEditor.tsx`.

**R15-DATA-028 (US default earnings universe).**
- **Mechanism (refuter-corrected).** `_DEFAULT_UNIVERSE` is ten US mega-caps (`earnings_provider.py:66-77`), used by the panel route and the `earnings_upcoming` tool when no watchlist is given. The India results calendar is per-symbol (`corporate_disclosures.get_results_calendar`), so registering it would still not answer "which Indian companies report this week".
- **Fix.** In an IN region with no watchlist, `get_upcoming` reads NSE's market-wide event calendar (`_get_json(_EVENT_CALENDAR_PATH, {"index": "equities", "from_date": …, "to_date": …}, referer)`, C3; confirm the params live), keeps results/financial-results purposes in the window and maps them to `EarningsEvent` (`provider "nse"`, currency INR, estimates null). The US default is unchanged. The catalog description needs no edit.
- **Test.** An event-calendar fixture (market-wide) under IN yields Indian names in the window. US still yields the US list. The case not written against: a board meeting whose purpose is not results is excluded.
- **Files.** `earnings_provider.py`.

**R15-DATA-032 and R15-DATA-067 (one class: fabricated fields on the earnings constructors).**
- **Mechanism.**
  - `EarningsEstimateDetail` sets `eps_estimate_median=eps_mean` and `revenue_estimate_median=rev_mean`, `eps_estimate_stddev=(high-low)/4` on the detail and every calendar event, and `revenue_analyst_count` = the EPS count (`earnings_provider.py:244-260`, `:425-452`). `analyst_count` defaults to 0. Live at batch 4: INFY median == mean == 19.58006, stddev 0.2825 == (20.33-19.20)/4.
  - `_fiscal_period_for` (`:98-121`) labels the calendar quarter of the **report** month, so every event, estimate and history row is a quarter late (JPM October Q3 → Q4; INFY FY27 Q2 → Q4).
- **Fix.**
  - Median, stddev and `revenue_analyst_count` are `None` unless the provider supplies them (the revenue count from the revenue-estimate frame's `numberOfAnalysts`). `estimate_analyst_count` is `int | None`.
  - `fiscal_period` becomes optional and is `None` unless the provider supplies the period (D-B5-27); `_fiscal_period_for` is deleted.
  - Mirror in `types/earnings.ts`. `EpsEstimateGrid` and `EarningsCalendarPanel` render "—" and sort nulls last.
  - Tests that pin the proxies encode the defect: fix them and say why.
- **Test.** The INFY-shaped payload yields null median and stddev. A revenue frame with its own count is used. JPM and INFY events carry `fiscal_period null`. The case not written against: a history row.
- **Files.** `earnings_provider.py`, `models/earnings.py`, `types/earnings.ts`, `EpsEstimateGrid.tsx`, `EarningsCalendarPanel.tsx`, `earnings_tools.py` (only if it reshapes the fields).

**R15-LEAD-010 (SEC viewer 404s a listed 10-K).**
- **Mechanism.** `get_filing` resolves metadata with `get_recent_filings(limit=40)` and no `form_type` (`sec_filings_provider.py:588-592`), so a heavy Form-4/144 filer's annual reports fall outside the window and 404.
- **Fix.** `get_filing(accession, cik_or_symbol, form_type=None)`: with a form hint, look it up in the form-filtered list; without one, or on a miss, look it up in the upstream's widest recent window. The route takes an optional `form_type` query param, and `store/sec.ts` passes the row's form type when opening a filing.
- **Test.** An AAPL-shaped payload with the 10-K at position 60 of the unfiltered list resolves with the hint and without it. The case not written against: a 10-Q.
- **Files.** `sec_filings_provider.py`, `routers/sec_filings.py`, `src/store/sec.ts`.

---

## 3. Integrator run order and gates

1. Work in a scratch worktree (`git worktree add <scratchpad>/b5-int 004-r4-experience-rebuild`), never the main repo (it has uncommitted register, CLAUDE.md and decisions edits). Run `git branch --show-current` before every merge.
2. Audit each branch through `origin/worktree-agent-b5-<w1..w5>`: `git merge-base --is-ancestor 2edcae9 origin/<branch>` (a stale base means re-dispatch) and `git diff --stat 2edcae9..origin/<branch>` touching only its §1 files.
3. Merge `--no-ff` in this order:
   - **W2** (provides C1's `period`, C4's upcoming key and C5's symbol behaviour).
   - **W1** (the catalog: `financial_statements` consumes C1; declares `read_notes`; C3 frozen).
   - **W4** (`data_cache.ensure_build` and the Origin middleware; independent of the rest).
   - **W5** (imports C3 and C5).
   - **W3** (completes C2).
   After each merge run that writer's pytest and vitest files. After W1+W2, run one unmocked `financial_statements` quarterly call. After W1+W3, drive `read_notes` once through `invoke_agent` with a `__notes__` snapshot.
4. Gates after all five merge:
   - `export PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH`
   - `ruff format --check sidecar && ruff check sidecar`
   - `pnpm format:check`, `pnpm lint`, `pnpm typecheck`
   - `cargo fmt --check`, clippy `-D warnings` and `cargo test` (W4's Rust)
   - A clean-venv `node scripts/ensure-all-sidecars.mjs --force` (LEAD-001 proof; also rebuilds the main sidecar for W5's new `.json.gz`, which the staleness gate ignores, RELEASE-005, deferred)
   - `pnpm ci-local` in the background with the exit code recorded
   - `node scripts/smoke-test-sidecars.mjs`
5. Grep checks:
   - `builtin.py` has no `or bool(value.strip())`;
   - `app.py` has no `allow_origins=["*"]`;
   - `invoke_agent` in `mcp_server.py` has no `api_key` parameter, and no `return {"agents": []}` / `{"workflows": []}` / `{"runs": []}` remains;
   - `sec_filings_provider.py` has no `"limit": 40`;
   - `earnings_provider.py` has no `eps_estimate_median=eps_mean`, no `/ 4.0` and no `_fiscal_period_for`;
   - `screener.py` has no `_WARM_UNIVERSES: … = ("sp500",)` and no `except (TimeoutError, Exception)` in enrichment;
   - `disclosure_tools.py` has no "lives in each quarter's linked xbrl_url";
   - `message-notices.ts` has no `DIVERGENCE_RE`;
   - `ChatSidebar.tsx` has no `.slice(-10)` on the history send; `_coerce_history` has no `out[-10:]`;
   - `anthropic.py` has no `DEFAULT_MAX_TOKENS = 4_096`;
   - `ChartPanel.tsx` has no `` `chart-${ `` bus key; `EquityOverviewPanel.tsx` has no `source: "equity"`; `BacktestResultView.tsx` has no `"backtest-panel"`;
   - the ccxt `ohlcv` lambda forwards `range_`.
6. Record the §6 decisions in `docs/redesign/DECISIONS.md` and `CHANGELOG.md` at merge. Writers do not edit docs.
7. Certification:
   - `DATA-026` certifies only after W1 and W2 merge; `AGENT-020` only after W1 and W3.
   - `CODE-AGENT-001` records a needs-GUI check if the webview Origin cannot be observed headless.
   - `LEAD-001` certifies on the clean-venv build log.
   - `DATA-037` certifies on `/crypto/history?range=` and the registry (the chart's slash-path 404 is DATA-081).
   - `DATA-110` certifies live only if the US pack shipped whole.

---

## 4. Deferred to the next batch

- **`AGENT-007` + `AGENT-017` (one set).** An eval loop (scenario set, grader, pass^k per lane, recorded wire cassettes) plus a default-model swap proven on it. `AGENT-017`'s acceptance test is `AGENT-007`'s portfolio-write scenario. Both need live multi-lane runs with spend, and no Anthropic or Gemini key is funded (D35). This is process plus live evidence, not a code fix a writer can pin here.
- **`AGENT-023`.** Scheduler, trigger nodes (clock and announcement phrase-watch) and an outbound webhook node. It depends on this batch's W4 engine semantics: an unattended alert must fire only on the taken branch (`CODE-PLATFORM-004`) and must not hang (`CODE-PLATFORM-019`). The webhook credential needs a decided home: the sidecar cannot read the keychain, and BYOK forbids persisting a secret. Next batch, as a dedicated opus set after W4 merges.
- **`DATA-014` (DAL leg) + `DATA-027` (one set).** Both need an exchange-filed financials lane (NSE results-comparison / BSE results) ranked above yfinance. Yahoo's own DAL statement agrees with the wrong TTM, so no Yahoo witness can see it. Feature-size provider work that collides with W1 (`nse_provider`/`bse_provider`) and W2 (`provider_registry`, `correctness_gate`) this batch.
- **`LIFECYCLE-001`.** Moving both MCP joins and `start_main_sidecar` off Tauri's main thread plus late MCP port attach. The proof is a packaged-app cold launch (GUI; none this run), and a boot regression bricks the app. The `--onedir` follow-up is Tier-1 (`tauri.conf.json`). Recommend an operator-attended batch.
- **`DATA-050` + `DATA-060` (one class: out-of-coverage reported as a 502 upstream failure).** Closing it needs a BSE per-symbol results lane and a SEC 20-F major-shareholders lane. W1 already carries three new India lanes. Next batch together.
- **`DATA-081` + `UI-053` (one class: `%2F` decoded before routing, so a slash id never matches a path param).** `DATA-081` also threads asset class between panels through `ChartPanel.tsx` (W3's file this batch).
- **`AGENT-044` + `AGENT-045` (one class: a model-supplied symbol is never resolved before use).** The class seam is the runtime's host-action and tool dispatch (`agent_runtime.py`, W3's file, already at 12 entries).
- **`AGENT-061` + `DATA-061` (ProviderError.kind flattened by consumers).** `DATA-061` spans `app.py` (W4), `yfinance_provider.py` and three routers (W2) and the chart; one set next batch.
- **`AGENT-050`.** Anthropic prompt caching. Capacity (W3 carries 12 entries). No Anthropic key exists to prove a cache hit live (D35). W3's AGENT-040 summary is a separate, stable message so the breakpoints can land later.
- **`RELEASE-005` + `RELEASE-006` (+ `CODE-PLATFORM-026`).** One class: the build-input truth is encoded twice. It is a scripts refactor; the integrator force-rebuilds instead (§3.4).

## 5. Label-mates and neighbours not taken (different root cause)

- **`DATA-058`, `DATA-059`, `UI-039`, `LIFECYCLE-019`, `CODE-DATA-002`, `CODE-DATA-003`, `DATA-051`** (resolver). Fuzzy band ordering, the former-name alias index, autocomplete skipping rename/enrich, the rename-lane failure latch, the memo, the payload drift and board/face value. Each is a separate mechanism in `symbol_resolver.py` beside DATA-017's master/live-rung fix. Capacity: W2 carries DATA-017 and DATA-026.
- **`DATA-065`** (period-start freshness on 1wk/1mo). A different freshness input from DATA-064's empty-series reason.
- **`DATA-079`, `DATA-080`** (`missing-india-signal` label). OI/options chain and segment data are separate lanes from pledge, deals and actions.
- **`CODE-PLATFORM-017`** (two `transform.code` evaluators). A separate node-editor mechanism; W4 capacity.
- **`AGENT-059`'s neighbours `AGENT-058`/`AGENT-063`.** `AGENT-058` is taken (W1, its own seam); `AGENT-063` (news scoring in the route) is a layer move in the news lane, not W1's files this batch.
- **`UI-036`** (portfolio prices never refresh), **`CODE-FRONTEND-017`** (stale-response races in the SEC/earnings stores), **`UI-032`** (SEC company search). Different mechanisms in the panels W5 touches.

## 6. Tier-3 decisions (the integrator records them; none is Tier-4)

- **D-B5-1 India exchange lanes.** Promoter pledge rides `ShareholdingPattern` (`"filed"` 0 vs `None` = not declared). Bulk/block/SAST is one `/disclosures/deals` route plus `exchange_deals`. Corporate actions is one `/disclosures/corporate-actions` route plus `corporate_actions`. Dividend event dates live on the action rows; `Fundamentals` is unchanged.
- **D-B5-2 Cross-feed pairing** also accepts a same-canonical-category pair inside the dissemination window when it is the unique candidate.
- **D-B5-3 SHP legs** are derived from the filed institutions total when unambiguous, labelled `derived`, at read time.
- **D-B5-4 The announcements cache** lives in `corporate_disclosures` (router, agent and research share it).
- **D-B5-5 Deep-research wall** clamps to the profile's own ceiling; the schema carries no fixed default.
- **D-B5-6 Statements** take `period=annual|quarterly` (ISO period ends for quarterly), reached by the agent through one `financial_statements` capability; no model field.
- **D-B5-7 Resolver masters** include NSE Emerge (`SM` to Yahoo `-SM.NS`), exclude RE lines, and are refreshed from the exchange lists daily at runtime (unioned with the bundled file). No calendar time-bomb test: a test that fails on a date with no code change would redden CI spontaneously. Empty live results expire. The live search runs when the fuzzy best shares no distinctive token.
- **D-B5-8 A 52-week pair** is flagged together when either bound diverges.
- **D-B5-9 Caret index symbols** pass through `_yahoo_symbol`; `in_eod_only` is only for intraday timeframes on known IN listings.
- **D-B5-10 Crypto OHLCV** honours range with `since` plus pagination.
- **D-B5-11 Earnings and ratings caches** key on the resolved listing (plus region for the default universe).
- **D-B5-12 The persisted data cache** is cleared when the sidecar version changes.
- **D-B5-13 Notes are readable by the agent** through `read_notes(scope)` (per-invocation) and a notes index in the preamble. Notes ride `__notes__`, not `__terminal__`.
- **D-B5-14 Conversation memory** is a budgeted verbatim window plus one deterministic summary of older turns (asks, tool steps, failures), with a visible marker and a context meter.
- **D-B5-15 Truncated or empty answers are never success.** A length finish gives a notice; a missing terminator or zero output gives an error frame with Retry. Anthropic `max_tokens` comes from the model's ceiling, and a truncated synthesis notes it on the brief.
- **D-B5-16 Every LLM round-trip is bounded.** Adapter idle timeouts, a planner timeout, heartbeat frames, a frontend stall watchdog, and repair calls that are capped, timed and metered.
- **D-B5-17 Runtime notices are typed** (`step_kind "notice"`). Staged host actions get a deterministic notice under ASK.
- **D-B5-18 One focus identity:** the bus is keyed by dockview id, one `focusedSymbolFromBus`, and the preamble names the focused panel.
- **D-B5-19 Workflow control flow:** a `skipped` state with SKIP propagation, falsy strings, `FIRST_COMPLETED` scheduling and a per-node timeout.
- **D-B5-20 One QuantLib lock** covers date-to-result; the quant tools and nodes run off the loop.
- **D-B5-21 Origin allow-list** (Tauri origins plus the Vite dev origin). A present, unlisted Origin gets 403 before routing; no Origin passes. This hardens the sidecar boundary without changing the layer model.
- **D-B5-22 invoke_agent over MCP takes no `api_key` argument** (a header, or the sidecar's normal resolution). The MCP list tools report `ok: false` on failure.
- **D-B5-23 MCP subprocess dependencies are pinned**, and the ensure recipes name a missing copy-metadata target.
- **D-B5-24 Diagnostics:** a rotating local log under `<data-dir>/logs`, timestamped sidecar logging, and a Settings preview-then-copy of a redacted bundle. Nothing leaves the machine unless the user pastes it.
- **D-B5-25 Saved workflows:** unreadable rows are listed as unreadable, not fatal; the version major is checked on load.
- **D-B5-26 Screener:** a US seed pack; `evaluated_count` drives the empty state; the stream's error frame reaches the panel; the region default comes from the sidecar; the warm loop is lazy and region-following; enrichment bugs are logged at WARNING. The warm-latency target is verified by measurement, not a wall-clock unit test.
- **D-B5-27 Earnings:** no proxy statistics; `fiscal_period` is null unless the provider supplies it; the IN default universe is NSE's market-wide event calendar.
- **D-B5-28 SEC `get_filing`** resolves an accession with the form hint, then the upstream's widest window.

---

## 7. Writer ground rules

1. Work in your own isolated worktree and branch (`worktree-agent-b5-<w1..w5>`). First run `git reset --hard 2edcae974425f45b2008e30410e9dbd7116ec505` and confirm with `git log -1`. Push after each concrete deliverable.
2. One focused commit per entry or per root-cause group, conventional, no emojis, ending with the session's attribution trailer.
3. Tests only where the repo keeps them (`sidecar/tests`, `src/**/*.test.ts(x)`, `src-tauri` tests), one focused test per pinned behaviour. Where a class is involved, pin the case the fix was not written against, as named above. Never delete, skip or weaken a test; if a test encodes the defect, fix it and give the reason in the commit body. Never special-case code to satisfy a test. Scratch scripts never become tests. Live captures become fixtures (add only), never live calls in a test.
4. Before every Python commit: `ruff format <files> && ruff format --check sidecar && ruff check sidecar`. Before every TypeScript push: `pnpm format:check`, `pnpm typecheck`, `pnpm lint` and your vitest files. W4 also runs `cargo fmt`, clippy `-D warnings` and `cargo test`. Export the PATH line from §3 first.
5. Touch only your §1 files. Honour C1 to C10 exactly: names, signatures and wire strings. A needed change elsewhere goes into `issues[]` with the exact line.
6. No refactoring beyond the entry, and no flags or defensive code for cases that cannot happen. Anything odd outside your entries goes to `issues[]`.
7. Never re-add trading. Never touch `CLAUDE.md`, `src-tauri/tauri.conf.json`, `.github/`, `LICENSE*`, `types/plugin.ts`, `r15-fanout.js`, `docs/` or the register. Read no `R15_BRIEF*.md` and nothing under `r15/local/`. No GUI. Never print, log or commit a secret.
8. Run long commands (pytest suites, sidecar builds, `ci-local`) in the background; never pipe them through `head`/`tee` in the foreground.
