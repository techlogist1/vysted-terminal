# R15 Stage C: Batch 10 Plan (0 high, 56 mediums; 0 proposed not-a-defect)

- **Base:** branch `004-r4-experience-rebuild` at `6b91b8fa07ea673257517f5ae7e1167f7a5d9db5` (batch-9 adjudication `6b91b8f`; Stage D docs-wave commits before it are docs-only). D81 is merged (feat(d81), `a122dbf6`), so nothing here re-adds trading, orders, brokers or a paper account.
- **Author:** the batch planner (Opus). I opened the code each row names at this base. Mechanisms follow the corrected verdicts: the batch-9 "not certified" notes and the D81 moot-notes, not the raw claims. Line numbers are at base.
- **Queue at base:** 0 critical, 2 high, 86 medium, 207 low open (88 high+medium). Every one of the 88 is either selected (56), deferred with a reason (32), or proposed not-a-defect (0).
- **Selection: 56 entries in 8 writer sets (4 opus, 4 sonnet).** Each writer set covers at least one of the operator's four areas, except for the docs and dead-code rows that ride a set already owning their files.
  - **Carried from batch 9 (not certified):**
    - `AGENT-082`: the footer leg.
    - `AGENT-088`: symbols over 10 characters, and base-to-suffixed.
    - `UI-027`: resolved-chord conflicts.
    - `RESEARCH-028`: the `has_results` ordering, and the Settings chip.
    - `AGENT-063`: the Bitcoin alias.
    - `DATA-048`: the ROCE panel row.
    - `DATA-054`: basis is hard-coded.
    - `DATA-055`: listing date vs first-trade date; since-listing.
    - `DATA-061`: cause-less upstream errors leak.
    - `DATA-068`: the analyst `as_of`.
    - `UI-018`: Screener and Marketplace Remove.
    - `UI-028`: rho.
    - `UI-032`: search is still dead.
  - **Named deferrals from batch 9, now taken:**
    - `AGENT-053`, `UI-084`, `CODE-PLATFORM-021`, `CODE-AGENT-009`, `CODE-AGENT-013`, `AGENT-083`, `AGENT-084`, `RESEARCH-030`, `AGENT-050`, `UI-091`, `CODE-RESEARCH-004`, `UI-048`.
    - The plugin-lifecycle class: `CODE-PLATFORM-012`/`013`/`014` + `AGENT-057`.
    - `CODE-PLATFORM-072` + `DATA-077`, `DATA-053`/`071`, `DATA-096`, `UI-024`.
    - The backtest set, the screener formula, docs drift, `DATA-095`, `DATA-087`, `CROSS-PLATFORM-003`, `CODE-PLATFORM-017`, `LEAD-018`, `LEAD-013`.
- **Why 56, not 60:** the 32 left are Tier-4 (11), operator-attended live lanes (3), L features with no decision (8), or whole script/store classes that would collide with a set here (10). None can be taken without splitting a class or a file (§4).
- **Class rule:** a class is a shared root cause, not a shared label. Each class below is kept whole in one writer.
  - `CODE-PLATFORM-012` + `013` + `014` + `AGENT-057` (W8): plugin on/off has no single lifecycle owner. Toggle, configure, bootstrap and agent sync each mutate a different store and never confirm the result.
  - `CODE-PLATFORM-029` + `030` (W1): the engine keys cash on the intent quantity, not the held position.
  - `LIFECYCLE-015` + `UI-010` + `UI-011` (W1): the run lifecycle has no persistence, validation or cancel owner.
  - `DATA-048` + `054` + `055` (W3): the Fundamentals profile labels values it did not derive.
  - `DATA-053` + `DATA-071` (W3): the BSE lane returns thin data as if complete; the Quote/OHLCV contract has no field to say otherwise.
  - `DATA-096` + `DATA-068` sidecar leg (W3): the fundamentals/analyst routes bypass `data_cache` meta.
  - `UI-048` + `UI-091` (W6): chart defaults are hard-coded constants in three places.
  - `CODE-PLATFORM-072` + `DATA-077` (W7): marketplace data-source rows are hand-written, not derived from `provider_registry`.
  - `RESEARCH-028` + `CODE-RESEARCH-004` (W5): the SearXNG manager's state and its docstrings describe routing that is not the live path.
  - `DOCS-016` + `017` + `018` (W4): CURRENT_STATE hand-snapshots of derived facts.
  - `DOCS-004` + `005` + `DATA-078` + `CODE-PLATFORM-024` (W6): BLUEPRINT/PDD promise text never reconciled.
- **proposed_not_defect:** none. Every selected entry's residual reproduces at base (spot-checked below per row).

---

## 0. The 56 entries

| # | Entry | Mechanism (one line) | Writer |
|---|---|---|---|
| 1 | R15-AGENT-050 | Anthropic system is one string, no `cache_control`; preamble folded into it; sent tool results mutated | W1 |
| 2 | R15-CODE-AGENT-009 | `invoke_agent` `agent_runtime.py:1658-2194` (~536 lines) owns pre-loop resolution inline | W1 |
| 3 | R15-LEAD-018 | nemotron CoT arrives in `content`; no adapter splits reasoning-in-content | W1 |
| 4 | R15-CODE-PLATFORM-029 | `backtest_engine.py:352-370` "add to existing" assigns a fresh `_OpenPosition` | W1 |
| 5 | R15-CODE-PLATFORM-030 | `:392` credits `abs(intent.quantity)`, `:412` pops regardless | W1 |
| 6 | R15-LIFECYCLE-015 | `backtest_store.py` OrderedDict LRU cap 32, insertion-order list | W1 |
| 7 | R15-UI-010 | `strategy-picker.tsx` `pickFields` (:102) drops min/max; sidecar never validates | W1 |
| 8 | R15-UI-011 | BacktestPanel holds no AbortController; no Stop | W1 |
| 9 | R15-CODE-AGENT-013 | `internal` never False, stored `mcp` overwritten (:1657), `_cap` re-declares defaults, two identical projections | W2 |
| 10 | R15-AGENT-083 | MCP surface projects `read_handler` only; spec FR-020-022/US5 promise parity | W2 |
| 11 | R15-RESEARCH-030 | no transcript capability; `corporate_disclosures.py:362` buckets transcripts as analyst_meet | W2 |
| 12 | R15-AGENT-084 | no drawing host action; no hand-action inventory | W2 |
| 13 | R15-CODE-PLATFORM-021 | POST/PUT/DELETE `/portfolio/positions` + `portfolio_db` writers have no caller | W2 |
| 14 | R15-DATA-048 | ROCE in contract, no `metrics.ts` row | W3 |
| 15 | R15-DATA-054 | `yfinance_provider.py:840-850` hard-codes `basis="consolidated"` for .NS/.BO | W3 |
| 16 | R15-DATA-055 | `listing_date` = Yahoo `firstTradeDateMilliseconds` (data start); panel says 52w on a 38-day listing | W3 |
| 17 | R15-DATA-053 | BSE header path reads absent volume keys; Quote has no OHLC | W3 |
| 18 | R15-DATA-071 | `_MAX_COLD_DOWNLOADS=8` returns ≤8 bars as the full range; registry stops on non-empty | W3 |
| 19 | R15-DATA-096 | income/balance/cashflow/ratings uncached; `data_cache` never evicts, SQLite on loop | W3 |
| 20 | R15-DATA-068 | analyst routes (in `routers/fundamentals.py`) carry no `as_of` | W3 (sidecar) + W7 (UI) |
| 21 | R15-LEAD-024 | WEO projection years unlabelled on `MacroObservation` | W3 |
| 22 | R15-DATA-061 | `errors.provider_error_response` (:116) treats cause-less as authored → WB/openbb raw text | W4 |
| 23 | R15-DATA-087 | `routers/macro.py:90-100` provider-less dispatch by region | W4 |
| 24 | R15-CROSS-PLATFORM-003 | `hardware_fit.detect_device` → `_detect_fallback` 8 GiB on Windows, no `estimated` | W4 |
| 25 | R15-RESEARCH-025 | `screener_formula._is_boolean` root-only; bools float()ed | W4 |
| 26 | R15-LEAD-013 | `screener_universes/sp500.json` drifted (delisted names, missing BXP/NVR/UDR) | W4 |
| 27 | R15-DATA-095 | `_migrate` ALTERs a 3-tuple; vocab declared in 4 places; SQL identifier interpolated | W4 |
| 28 | R15-DOCS-016 | CURRENT_STATE §0.5/§3.10/§4 "live mutations"; no named auto-applied constant | W4 |
| 29 | R15-DOCS-017 | CURRENT_STATE §3.3 screener: AND-only, sp500 top 100 | W4 |
| 30 | R15-DOCS-018 | CURRENT_STATE §3.3 routing by asset class | W4 |
| 31 | R15-AGENT-082 | `ChatSidebar.tsx:976` `spendUsd: 0`; `streaming.ts` ignores `spend_usd` | W5 |
| 32 | R15-AGENT-088 | `slash-commands.ts:46` shape caps at 10 chars; no base→suffixed resolution | W5 |
| 33 | R15-UI-027 | `keybindings.ts:236` `conflicts()` groups raw strings; `matchesEvent` shift-lenient; wrong hint copy | W5 |
| 34 | R15-RESEARCH-028 | `_apply_quality` (:427) tests `has_results` before `unresponsive`; no Settings "degraded" | W5 |
| 35 | R15-AGENT-063 | `news_provider._aliases` BTC/USDT → [BTC/USDT, BTC], no "Bitcoin" | W5 |
| 36 | R15-CODE-PLATFORM-017 | transform.code: mathjs client vs Python ast server | W5 |
| 37 | R15-CODE-RESEARCH-004 | ~150 lines search locale/autodetect/metadata with no production caller; stale docstrings | W5 |
| 38 | R15-UI-048 | chart defaults (SPY 1d, indicators) are constants; no prefs slice | W6 |
| 39 | R15-UI-091 | `_suggested_indicators` ignores timeframe/asset; no `ema:N`, no week VWAP; `indicator-presets.ts` unwired | W6 |
| 40 | R15-LEAD-026 | `routers/history.py` `_empty_series_reason` (:29) None for unknown symbol | W6 |
| 41 | R15-UI-024 | `notes/slash-commands.ts:46` toggleTaskList, no TaskList; menus not keyboard; wikilink plain text | W6 |
| 42 | R15-DOCS-004 | PDD claims RATIFIED; dead sections still cited in source | W6 |
| 43 | R15-DOCS-005 | BLUEPRINT ~38 modules vs 22 registered | W6 |
| 44 | R15-DATA-078 | BLUEPRINT alpha_vantage fallback does not exist | W6 |
| 45 | R15-CODE-PLATFORM-024 | BLUEPRINT §3.1 "Rust fs access" unimplemented; export is Blob download | W6 |
| 46 | R15-AGENT-053 | `context-provider.captureTerminalState` branches only chart/watchlist/portfolio | W7 |
| 47 | R15-UI-032 | sec-edgar-mcp `search_companies` swallows every exception → [] | W7 |
| 48 | R15-UI-028 | rho shown per unit rate | W7 |
| 49 | R15-UI-018 | ScreenerPanel delete + Marketplace Remove are one-click | W7 |
| 50 | R15-CODE-PLATFORM-072 | `lib/marketplace.ts` CATALOG_ROWS hand-write keys/ranks | W7 |
| 51 | R15-DATA-077 | no marketplace row for the keyless India lanes; vendor deferral unrecorded | W7 |
| 52 | R15-CODE-PLATFORM-012 | `PluginManagerPanel.tsx:171-180` calls runtime directly | W8 |
| 53 | R15-CODE-PLATFORM-013 | plugins.db `enabled` vs workspace `enabledModules['plugin:x']` | W8 |
| 54 | R15-CODE-PLATFORM-014 | `configure` (:253) → `enablePlugin`, `loadPlugin` (:195) returns early | W8 |
| 55 | R15-AGENT-057 | `plugin-agents.ts` POST/DELETE never check `response.ok` | W8 |
| 56 | R15-UI-084 | dock clamp 1200 px, no maximize | W8 |

(DATA-068 counts once; 57 rows minus 1 = 56.)

---

## 1. File ownership: eight disjoint sets

A file belongs to exactly one writer. Test files follow their subject. New tests go in new files wherever the owned test file belongs to someone else. Anything outside your list goes to `issues[]` with the exact line.

- **W1 `runtime-backtest` (opus):**
  - `sidecar/services/agent_runtime.py`, `sidecar/services/llm/{anthropic,openai,ollama}.py`.
  - `sidecar/services/{backtest_engine,backtest_store,backtest_strategies}.py`, `sidecar/models/backtest.py`, `sidecar/routers/backtest.py`, `types/backtest.ts`.
  - `src/modules/backtest/{strategy-picker,BacktestPanel,BacktestResultView}.tsx`, `src/store/backtest.ts`.
  - Tests: `test_agent_runtime.py`, `test_b3_runtime_*`/`test_b4_*`/`test_b5_runtime_*` (only if an extraction moves a patched symbol; never weakened), `test_llm_anthropic.py`, `test_llm_openai.py`, `test_llm_ollama.py`, `test_backtest_*.py`.
  - New tests: `test_runtime_prepass.py`, `test_reasoning_split.py`, `test_backtest_store.py`, fixtures under `sidecar/tests/fixtures/llm/`.
  - Vitest for the backtest module/store.
- **W2 `catalog-hostactions` (opus):**
  - `sidecar/services/agent_tools/{catalog,schemas,disclosure_tools}.py`, `sidecar/services/mcp_server.py`, `sidecar/services/research/disclosures.py`, `sidecar/services/corporate_disclosures.py` (transcript category only).
  - `sidecar/agents/{copilot,researcher}.json` (tools lists only).
  - `sidecar/routers/portfolio.py`, `sidecar/services/portfolio_db.py`, `sidecar/models/portfolio.py`, `sidecar/models/__init__.py` (portfolio line only).
  - `src/lib/host-actions.ts`, `src/store/chart-drawings.ts`, `types/drawings.ts`, `src/modules/chat/PlanView.tsx` (label case only).
  - Docs: `docs/MCP_INTEGRATION.md`, `specs/001-agent-native-redesign/spec.md` (FR-020-022/US5 only).
  - Tests: `test_capability_catalog.py`, `test_mcp_catalog_parity.py`, `test_mcp_server.py`, `test_disclosure_tools.py`, `test_research_disclosures.py`, `test_corporate_disclosures.py`, `test_portfolio.py`, `host-actions*.test.ts`, new `src/lib/hand-action-inventory.test.ts`.
- **W3 `fundamentals-bse-cache` (opus):**
  - `sidecar/services/yfinance_provider.py`, `sidecar/models/{fundamentals,market,analyst_extended}.py`, `types/data.ts` (sole owner), `types/analyst.ts`.
  - `src/modules/equity-overview/{EquityOverviewPanel.tsx,metrics.ts}`.
  - `sidecar/services/resolver_masters/{regenerate_nse_master.py,nse_instruments.json}`, `sidecar/services/symbol_resolver.py` (master-row read only), `sidecar/services/screener_universe_india.py` and `enrich_nse_sectors.py` (row-shape tolerance only).
  - `sidecar/services/bse_provider.py`, `sidecar/services/exchange_financials.py` (read; basis accessor only).
  - `sidecar/routers/fundamentals.py`, `sidecar/services/data_cache.py`, `sidecar/services/analyst_ratings_extended.py`.
  - `sidecar/services/macro/imf_provider.py`, `src/modules/macro/MacroChart.tsx`.
  - Tests: `test_yfinance_provider.py`, `test_fundamentals*.py`, `test_bse_provider.py`, `test_data_cache.py`, `test_analyst_*.py`, `test_macro_providers.py` (IMF cases), `test_symbol_resolver.py`, and the matching vitest.
- **W4 `screener-routes-statedocs` (sonnet):**
  - `sidecar/services/errors.py`, `sidecar/routers/macro.py`.
  - `sidecar/services/hardware_fit.py`, `src/lib/hardware-fit.ts`, `src/components/OnboardingFlow.tsx` (estimated chip only).
  - `sidecar/services/screener_formula.py`, `sidecar/services/fundamentals_store.py`, `sidecar/models/screener.py`, `types/screener.ts`, `sidecar/services/yahoo_batch_provider.py`.
  - `sidecar/services/screener_universes/{sp500.json,regenerate_fundamentals_seed.py}`, new `sidecar/services/screener_universes/regenerate_sp500.py`.
  - `docs/CURRENT_STATE.md`, `types/proposed-change.ts` (additive constant), `src/store/agent-autonomy.ts` (header comment).
  - Tests: `test_errors.py`, `test_macro_router.py`, `test_hardware_fit.py`, `test_screener_formula.py`, `test_fundamentals_store.py`, `test_screener*.py`, `test_fundamentals_seed.py`, new `test_sp500_universe.py`, new `types/proposed-change.test.ts` (or under `src/`).
- **W5 `chat-search-workflow` (sonnet):**
  - `src/modules/chat/{ChatSidebar.tsx,streaming.ts,slash-commands.ts,AgentsRail.tsx}`, `src/store/chat-history.ts`.
  - `src/store/keybindings.ts`, `src/components/SettingsPanel.tsx`.
  - `sidecar/services/searxng_manager.py`, `sidecar/services/agent_tools/web_search.py`, `sidecar/services/search/{base,searxng,registry,breaker,scrub,__init__}.py` (dead ranges + docstrings only), `src/modules/research/BriefPanel.tsx`.
  - `sidecar/services/news_provider.py`.
  - `src/modules/node-editor/{code-node.ts,code-node-run.ts,NodeEditorPanel.tsx}`, `sidecar/services/workflow_nodes/code_node.py`.
  - Tests: `test_searxng_*.py`, `test_web_search.py`, `test_search_{registry,breaker,scrub}.py`, `test_news*.py`, `test_workflow_builtin_nodes.py`, and the matching vitest.
- **W6 `chart-notes-blueprint` (sonnet):**
  - `src/store/settings.ts`, `src/modules/chart/{ChartPanel.tsx,toolbar.tsx}`, `src/lib/indicator-presets.ts`.
  - `sidecar/services/research/fast.py` (`_suggested_indicators` only), `sidecar/services/indicators.py`, `sidecar/routers/indicators.py`, `sidecar/routers/history.py`.
  - `src/modules/notes/*`, `package.json` + `pnpm-lock.yaml` (the tiptap list dep only).
  - Docs: `docs/BLUEPRINT.md` (not §2), `docs/redesign/PRODUCT_DESIGN_DECISIONS.md`, plus comment lines in `src/app/globals.css`, `styles/tokens.css`, `src/store/workspace.ts`.
  - Tests: `test_indicators.py`, `test_research_fast.py` (suggested-indicator cases), `test_history.py`, notes/chart/settings vitest, new `src/lib/design-doc-citations.test.ts`.
- **W7 `panels-marketplace` (sonnet):**
  - `src/modules/chat/context-provider.ts`, `types/panel-context.ts`.
  - `src/modules/{earnings/EarningsCalendarPanel,analyst-ratings/AnalystRatingsPanel,sec/SecFilingsPanel,news/NewsFeedPanel,screener/ScreenerPanel,macro/MacroPanel}.tsx`, `src/store/{analyst-ratings,sec}.ts`, `sidecar/services/sec_filings_provider.py`.
  - `src/modules/quant/{GreeksDashboard,OptionPricerPanel,units}.ts(x)`.
  - `src/modules/marketplace/MarketplacePanel.tsx`, `src/lib/marketplace.ts`, `types/marketplace.ts`, `sidecar/services/provider_registry.py` (additive accessor only), new `sidecar/routers/data_sources.py`, `sidecar/app.py` (include line only).
  - Tests: `test_sec_filings_provider.py`, `test_provider_registry.py` (new cases), new `test_data_sources_router.py`, and the matching vitest.
- **W8 `plugins-dock` (opus):**
  - `src/components/PluginManagerPanel.tsx`, `src/lib/{plugin-runtime,plugin-bootstrap,plugin-agents}.ts`, `src/store/marketplace.ts`, `sidecar/services/plugins_store.py`, `sidecar/routers/{plugins,custom_agents}.py`.
  - `src/lib/workspace.ts`, `src/store/agent-dock.ts`, `src/components/AgentDock.tsx`, `src/app/page.tsx`, `src/components/PanelHost.tsx` (hidden prop only).
  - Tests: `test_plugins.py`, `test_custom_agents_router.py`, `plugin-runtime.test.ts`, `workspace*.test.ts`, `agent-dock*.test.ts`.

**Contracts (frozen; a writer codes against them, the integrator checks them):**

- **C5, C6 and C10-C14 carry over unchanged.**
  - C10: the SearXNG `"degraded"` state and `searxng_degraded` reason. W5 now makes it reachable.
  - C11: `spend_usd` on the done frame is already in the sidecar; W5 parses it.
  - C12: the Fundamentals fields.
  - C13: `get_with_meta`. W3 keeps its signature.
- **C15 (W8 → W7):**
  - `src/store/marketplace.ts` keeps every public action name and signature (`enable`, `disable`, `configure`, `remove`, `install`). Only the internals change.
  - MarketplacePanel (W7) keeps calling them unchanged.
- **C16 (W3 → W7):**
  - The analyst envelopes (ratings, price-target-history, individual targets) gain `as_of: datetime | None` from `get_with_meta`.
  - `types/analyst.ts` mirrors it as `as_of?: string | null`.
  - W7 renders the chip and store TTL against that optional field, so its branch is green without W3.
- **C17 (W3):**
  - `Quote` gains optional `open`, `high`, `low`, `prev_close`.
  - `OHLCVSeries` gains `partial: bool = False` plus `coverage_start: date | None`.
  - `MacroObservation` gains `is_projection: bool = False`.
  - `Fundamentals.listing_date` means the exchange listing date: the NSE master DATE OF LISTING, else null. A new `first_trade_date` carries the Yahoo value.
  - `basis` is derived or null, never defaulted.
  - `types/data.ts` is mirrored in the same commit. All fields are additive or optional.
- **C18 (W2):**
  - New host action `add_chart_drawing{kind: "trendline"|"horizontal-line", points: [{time, price}], panelId?}`, kind `chart`, applied via `useChartDrawingsStore.addDrawing`.
  - New read capability `earnings_call_transcript{symbol, quarter?}` → `{symbol, filing_date, url, text, source}`.
- **C19 (W7):** new `GET /data-sources` → `[{id, label, serves: [model_key], regions, asset_classes, credentials: [..], keyless: bool}]`, read from the `provider_registry` declarations. It is additive.
- **C20 (W4):** `types/proposed-change.ts` exports `AUTO_APPLIED_KINDS` (readonly tuple) and `autoApplies` reads it. CURRENT_STATE quotes that constant by name.

---

## 2. Per-writer entries (mechanism → fix → test → files)

### W1: `runtime-backtest` (opus)

Opus because the set includes agent-runtime state-machine surgery (CODE-AGENT-009, AGENT-050's stop-mutating-sent-results) and LEAD-018, which needs a live capture and root-causing before any fix.

**Priority:** CODE-AGENT-009 → AGENT-050 → LEAD-018 → 029/030 → LIFECYCLE-015 → UI-010 → UI-011. Push after each.

**R15-CODE-AGENT-009**
- **Mechanism.** `invoke_agent` spans `agent_runtime.py:1658-2194`. Batch 9 already moved brief decoding and the option scrub out. Still inline and untestable without a fake provider: allow-list/read-only resolution (the `_READ_SAFE_PANEL_ACTIONS` filtering), native-search tier selection, and the planner pre-pass.
- **Fix.** Extract three pure or async helpers, with the loop body unchanged:
  - `_resolve_tool_surface(agent, intent, request) -> (tool_ids, read_only)`
  - `_select_native_search(provider, model, request)`
  - `async _plan_prepass(...) -> (plan_event|None, staged_steps)`
- **Test.** New `test_runtime_prepass.py` calls each helper directly:
  - A READ intent strips every data-write id.
  - An unsupported model gets no native search.
  - The pre-pass on a non-planner provider (ollama) yields no plan.
  - All existing runtime suites stay green unmodified.
- **Files:** `agent_runtime.py`, new test.

**R15-AGENT-050**
- **Mechanism.** `anthropic.py:_split_system_and_messages` (:65) joins everything into one `system` string with no `cache_control`. The per-turn terminal preamble and date are folded in, so the prefix changes every turn. The runtime rewrites earlier tool-result content between rounds, which also breaks the prefix.
- **Fix.**
  - Send `system` as blocks: [stable persona+capabilities with `cache_control: {"type":"ephemeral"}`, volatile preamble/date uncached].
  - Put one breakpoint on the last tool_result of each round.
  - Tool results already sent are frozen: the runtime appends, never edits.
- **Test.**
  - The captured request (fake client) carries the breakpoints.
  - Across two turns with different preambles, block 0 is byte-identical.
  - Pin (class case): a round that truncates a long tool result leaves the prior round's message unchanged.
- **Files:** `llm/anthropic.py`, `agent_runtime.py`, `test_llm_anthropic.py`.

**R15-LEAD-018**
- **Mechanism.**
  - `openai.py:680-686` maps `delta.reasoning`/`reasoning_content` to `LLMThinkingEvent`, but nemotron on the free OpenRouter lane leaks CoT into `content`.
  - No adapter handles `<think>…</think>` in content, or an untagged reasoning preamble.
  - Unconfirmed until captured: whether nemotron emits tags, or emits only when OpenRouter's `reasoning` request option is absent.
- **Fix.**
  1. Capture first. Run `scripts/r15/vy.py` against the free nemotron lane (the key stays in-process; spend is logged as $0). Save the SSE chunks as `sidecar/tests/fixtures/llm/nemotron_cot.jsonl`.
  2. If tagged: add one shared streaming splitter (`services/llm/reasoning_split.py`, owned by W1) that routes `<think>` spans across chunk boundaries to `LLMThinkingEvent`. Use it in `openai.py` and `ollama.py`.
  3. If untagged: request `reasoning: {"exclude": false}` for OpenRouter so it lands in `delta.reasoning`. Record which branch applied in the commit.
- **Test.**
  - Replay the captured fixture: the visible content has no CoT and the thinking events carry it.
  - Class pin, not written against: an Ollama `qwen3`-style `<think>` split across 3 chunks.
- **Files:** `llm/openai.py`, `llm/ollama.py`, new `llm/reasoning_split.py`, new `test_reasoning_split.py`, fixture.

**R15-CODE-PLATFORM-029 / 030**
- **Mechanism.**
  - `backtest_engine.py:352-370` replaces the position on a second buy (cash is debited twice, one lot is held).
  - `:392` credits the full intent quantity on a sell, and `:412` pops the position.
- **Fix.**
  - Buy merges into the position: quantity sum, weighted-average entry, fees summed.
  - Sell uses `qty = min(abs(intent.quantity), pos.quantity)`. Credit and PnL are on `qty`, and the position pops only at 0.
- **Test.**
  - Flat-market pyramiding: 3 buys at a constant price → final equity == capital − fees.
  - Flat oversell: sell 2× held → cash == capital − fees, and the position is closed once.
  - Class pin: a partial sell leaves the remaining quantity at the original average.
- **Files:** `backtest_engine.py`, `test_backtest_engine.py`.

**R15-LIFECYCLE-015**
- **Mechanism.** `backtest_store.py` is an in-memory OrderedDict LRU (capacity 32). `list()` returns insertion order, but the docs say newest first.
- **Fix.**
  - Also write each result as JSON under `<data-dir>/backtests/<run_id>.json`, using the same data-dir resolver the other stores use.
  - `get` loads on a miss.
  - `list` returns newest first by `created_at`, reading the directory.
  - Keep the memory LRU as a cache.
- **Test.** New `test_backtest_store.py` (tmp data dir):
  - A result survives re-instantiation.
  - The 33rd run leaves run 1 readable.
  - The list is newest first after a `get()` touches an old run.
- **Files:** `backtest_store.py`, `routers/backtest.py`, new test.

**R15-UI-010**
- **Mechanism.** `strategy-picker.tsx:102` `pickFields` drops `minimum`/`maximum`. The sidecar passes params straight to the strategy, so a raw Python exception becomes the run error.
- **Fix.**
  - Render min/max/step, and clamp on blur (a cleared field falls back to the default).
  - `models/backtest.py` validates params against the strategy's `paramsSchema` and returns a 422 with the sentence "`fast` must be between 2 and 200".
- **Test.**
  - Vitest: 0 → clamped to the minimum; empty → default.
  - Pytest: an out-of-range POST → 422 whose detail names the field.
  - Class pin: a float param given a string.
- **Files:** `strategy-picker.tsx`, `models/backtest.py`, `backtest_strategies.py`, `routers/backtest.py`, `types/backtest.ts`.

**R15-UI-011**
- **Mechanism.** `store/backtest.ts` `startRun(…, signal?)`; no caller passes one.
- **Fix.**
  - The panel holds an `AbortController` per run and passes the signal from Run and Retry.
  - While running, the Run button becomes Stop.
  - On abort, status goes back to idle with the note "Stopped".
- **Test.** A panel vitest: Stop aborts the fetch (the mock sees `signal.aborted`) and the status resets. A Retry after Stop starts a fresh controller.
- **Files:** `BacktestPanel.tsx`, `BacktestResultView.tsx`, `store/backtest.ts`.

### W2: `catalog-hostactions` (opus)

Opus because the set is next to a safety gate: the host-action gate surface, the MCP exposure boundary and catalog projections (Constitution Principle II).

**R15-CODE-AGENT-013**
- **Mechanism (corrected).** `aliases` IS read now (`resolve_tool_ids`, `aliases=("macro",)`), and `default_grant=False` is used (`ask_user`), so those two are moot. What is still dead:
  - `internal` is never False.
  - The stored `mcp` field is overwritten by the rule at `catalog.py:1657`.
  - `_cap` (:199) re-declares every default.
  - `agent_selectable_tool_ids()` equals `internal_tool_ids()`.
- **Fix.**
  - Delete the `internal` field and the stored `mcp` field (derive `mcp` from the one rule as a property).
  - `_cap(id, **overrides)` passes only non-defaults.
  - `agent_selectable_tool_ids` returns `internal_tool_ids()` with one docstring naming why they are equal.
- **Test.** Existing parity tests stay green, plus: constructing a Capability with `mcp=` raises `TypeError`.
- **Files:** `catalog.py`, `test_capability_catalog.py`.

**R15-AGENT-083 (Tier-3, D-B10-1)**
- **Mechanism.** `mcp_capabilities()` projects only `read_handler`. The spec (FR-020-022/US5) promises parity and the same confirmation path.
- **Fix.**
  - Amend the spec FR-020-022/US5 and `docs/MCP_INTEGRATION.md`: the external MCP surface is read-only in 0.9, and host actions stay in-app behind the proposed-changes gate.
  - Exposing writes through a host-side queue is a future operator decision.
- **Test.** `test_mcp_catalog_parity.py`: no capability with `read_only=False` or `kind != "read_handler"` reaches `mcp_capabilities()`, asserted over the live catalog.
- **Files:** `catalog.py` (docstring), spec, `MCP_INTEGRATION.md`, test.

**R15-RESEARCH-030**
- **Mechanism.** No transcript capability. `corporate_disclosures.py:362` maps "earnings call transcript" to `analyst_meet`, and `research/disclosures.py` reaches transcripts only if a sub-question picks them.
- **Fix.**
  - Give transcripts their own category (`earnings_call_transcript`).
  - New handler in `disclosure_tools.py`: take the newest transcript announcement (or the requested quarter), then `search/extract.py` PDF text (used as a library only), then C18's shape with filing date and URL.
  - Register a `read_handler` Capability (projects to TOOL_SCHEMAS and MCP) and add it to `copilot.json` + `researcher.json`.
- **Test.**
  - A handler test on a recorded concall announcement plus a PDF fixture (add-only, under `fixtures/nse` or `bse`) returns text, filing_date and url.
  - A US symbol returns an honest `{available: false, reason}`.
  - The parity tests are updated for the new id.
- **Files:** `disclosure_tools.py`, `corporate_disclosures.py`, `research/disclosures.py`, `catalog.py`, the agents JSON, tests.

**R15-AGENT-084**
- **Mechanism.** `HOST_ACTION_NAMES` (`host-actions.ts:71`) has no drawing action, although `chart-drawings.ts` `addDrawing(panelId, drawing)` exists with trendline and horizontal-line kinds. No inventory of hand actions exists.
- **Fix.**
  - `add_chart_drawing` (C18): catalog `host_action` kind `chart`, a host-actions apply via the drawings store on the active chart panel, and a diff label.
  - Add `HAND_ACTION_INVENTORY` (a table in `host-actions.ts`: hand action → host-action id | `{excluded: reason}`).
- **Test.** New `hand-action-inventory.test.ts`:
  - Every inventory row maps to a `HOST_ACTION_NAMES` member or carries an exclusion reason.
  - Every host action appears in the inventory (both directions).
  - Apply test: `add_chart_drawing` adds exactly one drawing to the target panel, and reject adds none.
- **Files:** `host-actions.ts`, `chart-drawings.ts`, `types/drawings.ts`, `catalog.py`, `copilot.json`, `PlanView.tsx`.

**R15-CODE-PLATFORM-021 (residual)**
- **Mechanism (corrected).** The host-action sync is gone (f37543da) and the docstrings agree. GET `/portfolio/positions` is still read once for the legacy import (`workspace.ts:932-948` via `api.ts fetchLegacyPositions`). POST/PUT/DELETE (`routers/portfolio.py:25-45`) and `portfolio_db.create/update/delete_position` have no caller.
- **Fix.** Delete the three write routes and the three writer functions. Keep GET + list + model.
- **Test.** The `test_portfolio.py` cases for the removed writes are converted, not dropped: POST/PUT/DELETE → 405. A grep test asserts no `src/` fetch uses method POST|PUT|DELETE on `/portfolio`. Log the conversion in the commit.
- **Files:** `routers/portfolio.py`, `portfolio_db.py`, `models/__init__.py` if a re-export dies, `test_portfolio.py`.

### W3: `fundamentals-bse-cache` (opus)

Opus because this is data-source root-causing: the basis derivation source, the listing-date source, and a registry fall-through contract.

**R15-DATA-048 (residual)**
- **Mechanism.** `roce` is on the wire, but `metrics.ts` has an ROE row and no ROCE row, so the panel never renders it.
- **Fix.** Add a ROCE row next to ROE with the same format and derived badge.
- **Test.** A metrics vitest: ROCE renders for a `roce`-bearing fixture and shows "unavailable" when null.
- **Files:** `metrics.ts`, `EquityOverviewPanel.tsx`.

**R15-DATA-054 (residual)**
- **Mechanism.** `yfinance_provider.py:840-850` sets `basis="consolidated"` for every .NS/.BO. This is false for SMR (the BSE intimation says Audited STANDALONE) and for single-entity ICON.
- **Fix.**
  - Derive basis from `exchange_financials` (`:194-208` already parses Consolidated/Standalone from the NSE results filing) through a small accessor.
  - If there is no filing, basis is null. Never default.
  - The panel shows a basis chip only when non-null.
- **Test.**
  - An SMR filing fixture → "standalone".
  - A consolidated fixture → "consolidated".
  - Class pin, not written against: a US symbol → null.
- **Files:** `yfinance_provider.py`, `exchange_financials.py`, `EquityOverviewPanel.tsx`, tests.

**R15-DATA-055 (residual)**
- **Mechanism.** `listing_date` is `firstTradeDateMilliseconds` (NAPEROL 2002-07-01 is the data start). `regenerate_nse_master.py` drops EQUITY_L's `DATE OF LISTING`. The panel shows "52w"/"1Y change" for a 38-day listing.
- **Fix.**
  - Keep DATE OF LISTING as a 4th master column; readers tolerate 3- or 4-tuples. Regenerate `nse_instruments.json`.
  - `listing_date` comes from the master. The Yahoo value moves to `first_trade_date` (C17).
  - The panel labels the range "since listing" and hides "1Y change" when listed under 52 weeks.
- **Test.**
  - The NAPEROL master row gives its real listing date.
  - A fixture listed 38 days ago → panel text "since listing" and no "1Y".
  - Class pin: a BSE-only symbol → `listing_date` null, not the first-trade date.
- **Files:** `regenerate_nse_master.py`, `nse_instruments.json`, `symbol_resolver.py`, `screener_universe_india.py`, `enrich_nse_sectors.py`, `yfinance_provider.py`, `models/fundamentals.py`, `types/data.ts`, `EquityOverviewPanel.tsx`.

**R15-DATA-053**
- **Mechanism.** `bse_provider._quote_from_header` reads `Volume`/`TotalTradedQty`, which the header payload does not have. `Quote` has no OHLC.
- **Fix.**
  - Fill volume and OHLC from the StockTrading call, or from the day's bhavcopy row already used for history.
  - Add the optional `open`/`high`/`low`/`prev_close` (C17).
- **Test.** ICON/AMAL header plus trading fixtures → volume > 0 and OHLC set. Class pin: header-only (the trading call fails) → volume null, not 0.
- **Files:** `bse_provider.py`, `models/market.py`, `types/data.ts`.

**R15-DATA-071**
- **Mechanism.** `_MAX_COLD_DOWNLOADS=8` returns at most 8 bars for a 1y cold request, and the registry stops on a non-empty result.
- **Fix.**
  - When the covered span is under 50% of the requested one, raise `ProviderError(kind="partial")`. The registry already falls through on ProviderError, so the next lane serves.
  - If the result is served anyway (last lane), set `partial=True` + `coverage_start` (C17).
- **Test.**
  - A cold 1y request with the download stub capped → ProviderError. A registry test shows the fall-through reaches the stub lane.
  - Class pin: a 5-day request with 5 bars is not partial.
- **Files:** `bse_provider.py`, `models/market.py`, tests.

**R15-DATA-096**
- **Mechanism.** The income/balance/cashflow/ratings routes (`routers/fundamentals.py`) bypass `data_cache`. `data_cache` has no ceiling and runs SQLite under an asyncio lock on the loop.
- **Fix.**
  - Cache the four at their siblings' TTL.
  - `data_cache` gets a row ceiling (constant, e.g. 20k) with oldest-first eviction, and runs its SQLite via `asyncio.to_thread`.
  - Keep the `get_with_meta` signature (C13).
- **Test.** Eviction at ceiling+1 removes the oldest row. A second income call makes no provider call.
- **Files:** `routers/fundamentals.py`, `data_cache.py`, tests.

**R15-DATA-068 (sidecar leg)**
- **Mechanism.** The analyst routes (ratings, price-target-history, individual targets, in `routers/fundamentals.py`) carry no `as_of`.
- **Fix.** Use `get_with_meta` there and stamp `as_of` (C16), with `models/analyst_extended.py` + `types/analyst.ts`.
- **Test.** A cached call's `as_of` equals the fetch time. A fresh call's `as_of` is within 5 s of now.
- **Files:** `routers/fundamentals.py`, `models/analyst_extended.py`, `analyst_ratings_extended.py`, `types/analyst.ts`.

**R15-LEAD-024**
- **Mechanism.** IMF WEO series run to 2031 with no projection marker.
- **Fix.**
  - Set `is_projection` (C17) from the SDMX response's own marker when present, else the vintage year cutoff (points after the latest actual year).
  - `MacroChart.tsx` draws projected points dashed, with a "projected" legend note.
- **Test.** A WEO fixture: a point after the cutoff is flagged and one before it is not. A vitest checks the legend note appears only when there is a projected point.
- **Files:** `imf_provider.py`, `models/market.py`, `types/data.ts`, `MacroChart.tsx`.

### W4: `screener-routes-statedocs` (sonnet)

**R15-DATA-061 (residual)**
- **Mechanism.** `errors.py:116` `provider_error_response` treats a ProviderError with no `__cause__` as authored, and keeps `str(exc)`. The WB "APIError: JSON decoding error (https://…)" and an openbb 422 are built cause-less, so they leak.
- **Fix.**
  - `detail` is the authored sentence only when the error came from `ProviderError.authored(...)`, a classmethod flag. Everything else gets the generic sentence for its kind, and the raw text is logged.
  - Also validate `provider` on the macro series route.
- **Test.**
  - `/macro/GDP` with a WB stub raising a cause-less decode error → detail with no "APIError", "http" or "JSON".
  - Class pin: an openbb 422 cause-less error on a different route.
  - An authored not_found keeps its sentence.
- **Files:** `errors.py`, `routers/macro.py`, the macro providers' raise sites only if they must call `authored` (`services/macro/*`, except `imf_provider.py`, which W3 owns: log that one to issues[] if needed).

**R15-DATA-087 (Tier-3, D-B10-2)**
- **Mechanism.** A provider-less `GET /macro/{series_id}` dispatches to the region default, so DGS10 under IN 502s.
- **Fix.** A series fetch requires `provider` (422 "provider is required for a series id"). Region defaults stay for catalog discovery. Check the frontend always sends `provider` (grep `src/store/macro.ts`; if not, log to issues[]).
- **Test.** DGS10 with no provider → 422 whose detail names provider. With provider=fred → routed.
- **Files:** `routers/macro.py`, `test_macro_router.py`.

**R15-CROSS-PLATFORM-003**
- **Mechanism.** `hardware_fit.detect_device` routes Windows to `_detect_fallback` (8 GiB), and `to_dict` has no provenance.
- **Fix.**
  - `_detect_windows` via ctypes `GlobalMemoryStatusEx` (no new dependency).
  - `estimated: bool` on the profile: True only from the fallback.
  - `src/lib/hardware-fit.ts` carries it, and OnboardingFlow shows "estimated" next to RAM when true.
- **Test.** Monkeypatched `platform.system="Windows"` plus a ctypes stub → the real RAM value and estimated False. An unknown OS → estimated True. An onboarding vitest checks the chip.
- **Files:** `hardware_fit.py`, `hardware-fit.ts`, `OnboardingFlow.tsx`, tests.

**R15-RESEARCH-025**
- **Mechanism.** `_is_boolean` checks the root only, and `_call`/`_sum`/`_term`/`_factor` float() a bool.
- **Fix.** Give each production an `is_bool` flag (a port of the TS parser). A boolean operand in arithmetic or min/max/abs raises a positioned `FormulaError`.
- **Test.** The three repro formulas → `ok:false` with a position. Class pin, not written against: `abs(roe > 1) + 1`.
- **Files:** `screener_formula.py`, `test_screener_formula.py`.

**R15-LEAD-013**
- **Mechanism.** `sp500.json` is a static list that has drifted.
- **Fix.**
  - New `regenerate_sp500.py`, which fetches current constituents from a public list (Wikipedia/datahub CSV) and rewrites the pack in its existing shape (`id`, `label`, `asset_class`, `snapshot_date`, `source`, symbols) with a fresh `snapshot_date`. Run it once and commit the regenerated pack.
  - A staleness test fails when `snapshot_date` is over 180 days old.
- **Test.** New `test_sp500_universe.py`: BXP, NVR and UDR are present, the known delisted names from the batch-5 note are absent, and the TTL check passes. The shape is unchanged, so `services/screener.py` needs no edit.
- **Files:** `sp500.json`, the new script, test.

**R15-DATA-095**
- **Mechanism.** `fundamentals_store._migrate` (:173) ALTERs a 3-tuple. The vocabulary is declared in `_NUMERIC_FIELDS` (:68), the exporter (`regenerate_fundamentals_seed.py:38`), `ScreenerNumericField` (`models/screener.py:58`) and `types/screener.ts:68`, and has already drifted (`shares_outstanding`). `_criterion_fails_sql` (:662) interpolates the field as an identifier.
- **Fix.**
  - `ScreenerNumericField` is the one declaration. The store and exporter derive from `get_args`.
  - `_migrate` ALTERs every column that `PRAGMA table_info` does not report.
  - `_criterion_fails_sql` asserts the identifier is in the set.
- **Test.**
  - A trimmed-schema DB (only the v1 columns) opens, migrates and screens on `shares_outstanding`.
  - A Python⟷TS parity test (reads `types/screener.ts`).
  - An unknown field → ValueError, never SQL.
- **Files:** `fundamentals_store.py`, `regenerate_fundamentals_seed.py`, `models/screener.py`, `yahoo_batch_provider.py`, `types/screener.ts`, tests.

**R15-DOCS-016 / 017 / 018**
- **Mechanism.**
  - The auto-apply set is correct in code (`types/proposed-change.ts:35` `autoApplies` = panel/chart/watchlist).
  - CURRENT_STATE still calls non-order host actions "live mutations" (§3.10/§4), and hand-counts the write set.
  - §3.3 says the screener is AND-only with an sp500 "top 100", and describes asset-class routing.
- **Fix.**
  - C20 `AUTO_APPLIED_KINDS`, with `autoApplies` reading it.
  - CURRENT_STATE §0.5/§3.10/§4 describe the staged ProposedChange path and quote `AUTO_APPLIED_KINDS`; the write set points to `HOST_ACTION_NAMES`.
  - §3.3 describes nested AND/OR `CriterionGroup`, the real universes and sizes (after the LEAD-013 regeneration), and the preference-rank resolver with the IN chain (from the `provider_registry.py` docstring).
  - The `agent-autonomy.ts` header matches.
- **Test.** A vitest asserts that `PROPOSED_CHANGE_KINDS.filter(autoApplies)` deep-equals `AUTO_APPLIED_KINDS`, and that CURRENT_STATE.md contains each kind in `AUTO_APPLIED_KINDS` on the line that names it.
- **Files:** `docs/CURRENT_STATE.md`, `types/proposed-change.ts`, `agent-autonomy.ts`, new test.

### W5: `chat-search-workflow` (sonnet)

**R15-AGENT-082 (footer leg)**
- **Mechanism.** `ChatSidebar.tsx:976` hard-codes `cost: {spendUsd: 0}`, and `streaming.ts` (~:420) ignores `spend_usd`.
- **Fix.**
  - `streaming.ts` parses `spend_usd` into `spendUsd?: number` (C11).
  - Store it on `ChatMessage.usage` (`chat-history.ts:47`).
  - A finished assistant message's footer shows "N tok · ~$X" (spend hidden when undefined; "$0.00" shown when the model is free).
  - AgentsRail stops hiding finished runs with zero spend.
- **Test.** Streaming parses a done frame with and without `spend_usd`. A footer render test covers both cases.
- **Files:** `streaming.ts`, `ChatSidebar.tsx`, `chat-history.ts`, `AgentsRail.tsx`.

**R15-AGENT-088 (residual)**
- **Mechanism.** `slash-commands.ts:46` `BARE_TICKER_SHAPE` caps a symbol at 10 characters, and `matchBareTicker` does only an exact lookup.
- **Fix.**
  - Widen to `^@?([A-Za-z][A-Za-z0-9.&-]{0,19})$`.
  - Exact known match wins. Otherwise match a unique known symbol whose base (before `.`) equals the token. Two or more matches → raw to the LLM.
- **Test.** `RELIANCE.NS` and bare `RELIANCE` (with `RELIANCE.NS` watched) → chart action. Class pin, not written against: `M&M.NS` and `BAJAJ-AUTO.NS`. `INFY` with both `.NS` and `.BO` known stays raw.
- **Files:** `slash-commands.ts`, its test.

**R15-UI-027 (residual)**
- **Mechanism.**
  - `keybindings.ts:236` `conflicts()` groups raw strings.
  - `matchesEvent` (:451) is shift-lenient, so `mod+p` shadows `shift+mod+p`, and `resolveKeyboardAction` fires only the first match.
  - The `SettingsPanel.tsx:1464` hint says both fire.
- **Fix.**
  - `matchesEvent` is strict on shift for letter keys (lenient only for symbols that need shift).
  - `conflicts()` normalises each combo to a resolved chord (`mod`→platform modifier, sorted modifiers) and groups on that.
  - Hint copy: "only the first binding fires".
- **Test.** `shift+mod+p` beside `mod+p` does not conflict, and both dispatch correctly. `mod+p` vs `meta+p` on mac conflicts. Class pin: `shift+mod+k` vs `mod+k`.
- **Files:** `keybindings.ts`, `SettingsPanel.tsx`, tests.

**R15-RESEARCH-028 (residual)**
- **Mechanism.** `searxng_manager._apply_quality` (:427) tests `probe.has_results` before `unresponsive`, so a "test" probe with results reads ready while real finance queries return 0. `SettingsPanel.tsx:776` `searxngChipMeta` has no "degraded".
- **Fix.**
  - Unresponsive engines covering all engines → degraded, whatever `has_results` says.
  - `web_search` records real-query outcomes into the manager; 3 consecutive empty SearXNG answers → degraded (C10).
  - Settings chip "Degraded — engines blocked (…)".
  - BriefPanel nudge keyed on `web_reason == "searxng_degraded"`.
- **Test.**
  - A canned probe with `has_results` true and all engines unresponsive → degraded.
  - Class pin: 3 empty real queries after a healthy probe → degraded, and `web_search` returns `searxng_degraded`.
  - Vitest for the chip and the nudge.
- **Files:** `searxng_manager.py`, `web_search.py`, `SettingsPanel.tsx`, `BriefPanel.tsx`, tests.

**R15-AGENT-063 (residual)**
- **Mechanism.** `news_provider._aliases("BTC/USDT")` → `["BTC/USDT", "BTC"]`, with no name alias.
- **Fix.** Add a crypto base → name map for the top crypto bases (read from `screener_universes/crypto_top50.json` if it carries names; else a small constant), so tagging matches "Bitcoin".
- **Test.** `BTC/USDT` tags a "Bitcoin options expiry" headline. Class pin: `ETH/USDT` → "Ethereum".
- **Files:** `news_provider.py`, `test_news.py`.

**R15-CODE-PLATFORM-017 (Tier-3, D-B10-3)**
- **Mechanism.** The editor evaluates transform.code with mathjs, and the server with Python ast. They disagree on `round(2.5)`, `^` and ternaries.
- **Fix.**
  - The server evaluator is canonical. The editor runs a transform through the existing workflow run endpoint, and mathjs stays only for the inline syntax check.
  - Drop the client partition restriction and the stale comments.
- **Test.**
  - A shared parity fixture (`round(2.5)`, `2^3`, a ternary), with the server expectations in pytest.
  - A vitest that the editor's run path calls the server and never mathjs `evaluate`.
- **Files:** `code-node.ts`, `code-node-run.ts`, `NodeEditorPanel.tsx`, `code_node.py`, tests.

**R15-CODE-RESEARCH-004**
- **Mechanism.** Verified at base: `locale_domains`, `preferredDomains`, `detect_searxng`, `KNOWN_BACKENDS`, `breaker_status` and `untrusted_context_message` are referenced only by their defining modules, the package re-exports and tests. Production resolves SearXNG via `config.get_searxng_url` / `ready_base_url_detected`.
- **Fix.**
  - Delete `base.py:138-174`, `searxng.py:64-142` and `SearchResponse.metadata`, plus the unused exports.
  - Correct the docstrings at `base.py:20-23`, `searxng.py:18-27` and `searxng_manager.py:40-42`, 204 and 488.
  - Keep `SearchError`, `bare_host`, `wrap_untrusted` and `sanitize_inline` (they have live callers).
- **Test.** New `test_search_exports.py` checks that every name in `services.search.__all__` has a non-test caller in `sidecar/`. Test cases that exercise only a deleted symbol are removed with it and named in the commit. This is not weakening: the subject no longer exists.
- **Files:** the search package files listed, `searxng_manager.py`, tests.

### W6: `chart-notes-blueprint` (sonnet)

**R15-UI-048**
- **Mechanism.** The chart mounts with constants (SPY, 1d, empty indicators).
- **Fix.**
  - Add `chartDefaults: {symbol, timeframe, indicators}` to `SettingsBundle`. It rides the existing settings slice (`toBundle`/`setAll`); older blobs are guarded, and `workspace.ts` needs no edit.
  - The chart toolbar gets "Make default".
  - ChartPanel reads the default at mount when the panel has no saved state.
- **Test.** A settings round-trip keeps `chartDefaults`, and an older blob without it gets the seed. A ChartPanel mount uses the stored default.
- **Files:** `settings.ts`, `ChartPanel.tsx`, `chart/toolbar.tsx`.

**R15-UI-091**
- **Mechanism.** `fast.py` `_suggested_indicators` ignores timeframe and asset class, `indicators.py` has no parametrised EMA or week-anchored VWAP, and `indicator-presets.ts` is unwired.
- **Fix.**
  - Parse `ema:9`-style specs in `indicators.py` and the route.
  - Add `anchor="week"` to `compute_vwap`.
  - `_suggested_indicators(timeframe, asset_class)` returns the FR-092 sets.
  - `indicator-presets.ts` becomes the frontend mirror used for the UI-048 seed, or is deleted. Pick one source and log it.
- **Test.** (equity, 5m) → `ema:9`, `ema:21`. (crypto, 1d) → `ema:50`, `ema:200`, `vwap:week`. The week-VWAP resets on Monday. Class pin: (equity, 1d) → the daily set.
- **Files:** `fast.py`, `indicators.py`, `routers/indicators.py`, `indicator-presets.ts`, `ChartPanel.tsx`.

**R15-LEAD-026**
- **Mechanism.** `routers/history.py:29` `_empty_series_reason` returns None for an unresolvable symbol.
- **Fix.** Return `unknown_symbol` when `symbol_resolver` cannot resolve the symbol at all. The ChartPanel copy is "No such symbol".
- **Test.** `/history/ZZQXNOPE` → reason `unknown_symbol`. Class pin: a resolvable symbol with an empty range keeps its old reason.
- **Files:** `routers/history.py`, `ChartPanel.tsx`, tests.

**R15-UI-024**
- **Mechanism.**
  - `notes/slash-commands.ts:46` calls `toggleTaskList` with no TaskList registered.
  - The suggestion `onKeyDown` hooks (`SlashCommandExtension.ts:75`, `WikiLinkExtension.ts:101`) ignore the arrows and Enter.
  - A wikilink is escaped text.
- **Fix.**
  - `pnpm add @tiptap/extension-list@3.25.0 --offline` (already in the store) and register TaskList/TaskItem, with a toolbar control.
  - ArrowUp/Down/Enter handling in both hooks.
  - A wikilink inline node with a Markdown serializer that emits `[[X]]`; click → `loadSymbolIntoChart`.
  - `getSymbols` reads `getState()`.
  - The slash menu wraps a selection instead of replacing it.
- **Test.** jsdom editor tests: the task command creates a task list, arrows and Enter pick the second item, and a wikilink round-trips through Markdown. Class pin: `[[` over a selection.
- **Files:** `src/modules/notes/*`, `package.json`, `pnpm-lock.yaml`.

**R15-DOCS-004 / DOCS-005 / DATA-078 / CODE-PLATFORM-024 (Tier-3, D-B10-4/5)**
- **Mechanism.**
  - The PDD still claims to be RATIFIED, and `globals.css:199` (§3) and `store/workspace.ts:34,129` (§7) cite sections to verify.
  - BLUEPRINT promises ~38 modules (22 are registered), alpha_vantage (absent) and Rust fs (it is a Blob download).
- **Fix.**
  - A PDD SUPERSEDED banner naming the dead sections and the binding ones. Before labelling §7 (panel placement), read it; it may still be binding.
  - Fix the source comments that cite dead sections.
  - BLUEPRINT (not §2): the module count is 22 in 0.9 with the rest listed as a v1.0 roadmap (D-B10-4); drop alpha_vantage; §3.1 describes the webview download (D-B10-5).
  - The integrator writes the DECISIONS rows.
- **Test.** `design-doc-citations.test.ts`: no file under `src/` or `styles/` cites a PDD section the banner lists as superseded.
- **Files:** `BLUEPRINT.md`, `PRODUCT_DESIGN_DECISIONS.md`, `globals.css`, `tokens.css`, `store/workspace.ts` (comments), new test.

### W7: `panels-marketplace` (sonnet)

**R15-AGENT-053**
- **Mechanism.**
  - `captureTerminalState` branches only on chart*, watchlist and portfolio, so the published backtest, news and equity payloads are dropped.
  - Earnings, analyst, SEC, screener, macro and quant publish nothing.
  - Rendered symbols are not clickable.
- **Fix.**
  - A generic per-source summary in the consumer: `{source, symbol?, summary}` for any published source (≤200 characters).
  - Publish effects in the earnings, analyst, SEC, screener, macro and quant panels.
  - Earnings, analyst and SEC symbol cells become buttons → `loadSymbolIntoChart`.
- **Test.**
  - Publishing a backtest and news summary → the snapshot carries both.
  - Class pin: the macro panel's published series id appears.
  - An earnings row click calls `loadSymbolIntoChart`.
- **Files:** `context-provider.ts`, `types/panel-context.ts`, the six panels.

**R15-UI-032 (residual)**
- **Mechanism.** sec-edgar-mcp 1.0.8 `search_companies` swallows every `edgar.search()` exception into [].
- **Fix.**
  - `sec_filings_provider.search_companies` stops using the MCP search. It resolves a ticker via `get_cik_by_ticker`, and a name via SEC `company_tickers.json` (fetched with the existing SEC User-Agent, cached 24 h in `data_cache`, case-insensitive substring match, top 10).
  - A debounced autocomplete in SecFilingsPanel.
- **Test.** A fixture `company_tickers.json` gives "Apple" → CIK 320193 and "nvidia" → NVDA. Class pin: "Palantir". A panel test covers the debounce.
- **Files:** `sec_filings_provider.py`, `store/sec.ts`, `SecFilingsPanel.tsx`.

**R15-DATA-068 (UI leg)**
- **Fix.** Against C16, the analyst store keeps `{payload, fetchedAt}` with a TTL, plus an as-of chip and Refresh (the NewsFeedPanel `refreshNonce` precedent).
- **Test.** A store TTL test: an expired entry refetches, and the chip renders `as_of`.
- **Files:** `store/analyst-ratings.ts`, `AnalystRatingsPanel.tsx`.

**R15-UI-028 (residual)**
- **Mechanism.** Rho is shown per unit rate.
- **Fix.** `units.ts toMarketUnits` adds rho/100 "per 1% rate", used by both panels.
- **Test.** A helper unit test: 13.5565 → 0.1356. A render test checks the rho label.
- **Files:** `units.ts`, `GreeksDashboard.tsx`, `OptionPricerPanel.tsx`.

**R15-UI-018 (residual)**
- **Mechanism.** ScreenerPanel "Delete saved screen" and Marketplace "Remove" act on one click.
- **Fix.** Wrap both in the existing `ConfirmButton`, then sweep `src/modules` for any other remaining one-click `onClick={…delete|remove…}` and log hits outside W7's files to issues[].
- **Test.** For each site, a single click does not delete and the confirm does.
- **Files:** `ScreenerPanel.tsx`, `MarketplacePanel.tsx`.

**R15-CODE-PLATFORM-072 + R15-DATA-077 (Tier-3, D-B10-6)**
- **Mechanism.**
  - `lib/marketplace.ts` CATALOG_ROWS hand-write `standardModelKeys`/`preferenceRank`, which have no consumer outside the file and have drifted.
  - `provider_registry._PROVIDERS` (:124) is the truth.
  - There is no row for the keyless India lanes.
- **Fix.**
  - An additive `provider_registry.declarations()` plus C19 `GET /data-sources`.
  - The data-source rows are derived at load, falling back to an empty list with an error line when offline, never stale hand rows.
  - Delete the hand-written keys. The India keyless lanes (`nse_direct`/`nse`/`bse`) appear as rows with provenance.
  - The vendor deferral is recorded as D-B10-6.
- **Test.** A parity test: every registry provider has exactly one row whose keys equal its serves set. A vitest checks an India row renders from the fixture.
- **Files:** `provider_registry.py`, `routers/data_sources.py`, `app.py`, `lib/marketplace.ts`, `types/marketplace.ts`, `MarketplacePanel.tsx`.

### W8: `plugins-dock` (opus)

Opus because the set is workspace persistence (the enabled-flag derivation, the maximized dock in the blob) and a lifecycle state machine.

**R15-CODE-PLATFORM-012 / 013 / 014**
- **Mechanism.**
  - `PluginManagerPanel.tsx:171-180` `handleToggle` calls `runtime.loadPlugin`/`unloadPlugin` directly, so nothing is persisted or unbridged.
  - "On" lives in plugins.db `enabled` and in workspace `enabledModules['plugin:x']`.
  - `configure` (`store/marketplace.ts:253`) calls `enablePlugin`, and `loadPlugin` (`plugin-runtime.ts:195`) returns early for an active plugin, so its secrets go stale.
- **Fix.**
  - `PluginRuntime.enable`/`disable` own persist + bridge + agent sync, and the toggle calls the store (C15).
  - `enabledModules['plugin:*']` is derived from runtime state on restore and not persisted, with one shared default.
  - `runtime.reloadPlugin` (unload → load), which `configure` calls.
- **Test.**
  - Toggle off → `enabled:false` persisted and the module unbridged.
  - Restoring a blob with `plugin:x=false` over an enabled plugin keeps it enabled.
  - Configure re-runs `initialize()`: fix the test that locked the no-op and log it.
- **Files:** `PluginManagerPanel.tsx`, `plugin-runtime.ts`, `plugin-bootstrap.ts`, `store/marketplace.ts`, `workspace.ts`, `plugins_store.py`, tests.

**R15-AGENT-057**
- **Mechanism.** `plugin-agents.ts` POST/DELETE never check `response.ok`.
- **Fix.** Non-ok → the runtime's errored event with the detail. 409 → PUT update.
- **Test.** A 422 marks the plugin errored. A changed `systemPrompt` PUTs.
- **Files:** `plugin-agents.ts`, `routers/custom_agents.py` (only if PUT is missing).

**R15-UI-084**
- **Mechanism.** `agent-dock.ts` clamps to 1200 px and there is no maximize.
- **Fix.**
  - Add `maximized` + `restoreWidth` to the store (a command plus a handle double-click).
  - Persist it in the `agentDock` slice (`workspace.ts:367-380`, guarding older blobs).
  - `page.tsx` hides PanelHost (CSS, not unmount, so the dockview state survives).
- **Test.**
  - A store test: maximize → unclamped; restore → the prior width.
  - A blob round-trip test.
  - A render test: the PanelHost is hidden but still mounted.
- **Files:** `agent-dock.ts`, `AgentDock.tsx`, `workspace.ts`, `page.tsx`, `PanelHost.tsx`.

---

## 3. Integrator run order and gates

**Stall rule (all roles).**
- No single tool call runs longer than ~120 s.
- `pnpm ci-local`, full pytest/vitest, cargo, PyInstaller builds and sidecar boots start detached and are polled with separate short calls.
- Never an `until`/`sleep` loop inside one call.
- Emit a tool call at least every 2 minutes.

1. Work in a scratch worktree (`git worktree add <scratchpad>/b10-int 004-r4-experience-rebuild`), never the main repo (it holds uncommitted `CLAUDE.md`, ledger and stage-d edits).
2. Audit each branch through `origin/worktree-agent-batch-10-<Wn>-<name>`:
   - `git merge-base --is-ancestor 6b91b8fa origin/<branch>` (a stale base means re-dispatch).
   - `git diff --stat 6b91b8fa..origin/<branch>` touches only that writer's §1 files.
3. Merge `--no-ff` in this order, running that writer's tests detached after each:
   1. **W3.** Contract owner for `types/data.ts` and `types/analyst.ts`. Run `test_yfinance_provider.py`, `test_fundamentals*.py`, `test_bse_provider.py`, `test_data_cache.py`, `test_analyst_*.py`, `test_macro_providers.py`, `test_symbol_resolver.py`, `test_screener_india.py`, `pnpm typecheck`.
   2. **W4.** Run `test_errors.py`, `test_macro_router.py`, `test_hardware_fit.py`, `test_screener*.py`, `test_fundamentals_store.py`, `test_fundamentals_seed.py`, `test_sp500_universe.py`, the proposed-change vitest.
   3. **W1.** Run `test_agent_runtime*.py`, `test_b3_runtime_*`, `test_b4_*`, `test_b5_runtime_*`, `test_llm_*.py`, `test_runtime_prepass.py`, `test_reasoning_split.py`, `test_backtest_*.py`, backtest vitest.
   4. **W2.** Run `test_capability_catalog.py`, `test_mcp_catalog_parity.py`, `test_mcp_server.py`, `test_agents_router.py`, `test_disclosure_tools.py`, `test_research_disclosures.py`, `test_corporate_disclosures.py`, `test_portfolio.py`, host-actions vitest.
   5. **W8.** Run `test_plugins.py`, `test_custom_agents_router.py`, plugin/workspace/dock vitest.
   6. **W7.** Needs W3 (C16) and W8 (C15). Run `test_sec_filings_provider.py`, `test_provider_registry.py`, `test_data_sources_router.py`, panel/marketplace/quant vitest.
   7. **W6.** Run `test_indicators.py`, `test_research_fast.py`, `test_history.py`, notes/chart/settings vitest, and `pnpm install --frozen-lockfile --offline` to check the lockfile.
   8. **W5** last. Run `test_searxng_*.py`, `test_web_search.py`, `test_search_*.py`, `test_news*.py`, `test_workflow_*.py`, then the full vitest.
   - No integrator code edits. A cross-writer seam break is re-dispatched to its owner.
4. Gates after all eight (export `PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH` first; run everything long detached):
   - `ruff format --check sidecar && ruff check sidecar`.
   - `pnpm format:check`, `pnpm lint`, `pnpm typecheck`.
   - `node scripts/ensure-all-sidecars.mjs --force`. W3 regenerates `nse_instruments.json` and W4 regenerates `sp500.json`; both ride the existing `--add-data`/`--collect-data`, so check they are in the built binary.
   - `pnpm ci-local` with the exit code recorded.
   - `node scripts/smoke-test-sidecars.mjs`.
5. Grep checks:
   - `ChatSidebar.tsx` has no `spendUsd: 0`.
   - `slash-commands.ts` has no `{0,9}`.
   - `searxng_manager._apply_quality` does not test `has_results` before `unresponsive`.
   - `yfinance_provider.py` has no literal `"consolidated"` default.
   - `backtest_engine.py` has no `_OpenPosition(` inside the buy-when-held branch.
   - `catalog.py` has no `internal=` and no stored `mcp=`.
   - `routers/portfolio.py` has no `@router.post|put|delete`.
   - `lib/marketplace.ts` has no `standardModelKeys:` literal.
   - `PluginManagerPanel.tsx` has no `runtime.loadPlugin(` or `unloadPlugin(`.
   - `agent-dock.ts` clamp is bypassed only under `maximized`.
6. Record the §6 decisions in `docs/redesign/DECISIONS.md` + `CHANGELOG.md` at merge. DOCS-004 needs the Warm-Graphite → Pure-Black reversal row, DOCS-005 the module-count row, and DATA-077 the India-vendor deferral row.
7. Tell the Stage D docs wave to run `mode: refresh` after this merge. W4 and W6 edit `docs/CURRENT_STATE.md` and `docs/BLUEPRINT.md`, which the Stage D drafts re-derive.
8. Certification notes (one fresh verifier):
   - **LEAD-018:** a live free nemotron turn via `vy.py` with no CoT in content.
   - **AGENT-050:** a scripted two-turn Anthropic request capture (live only if a funded key is present; otherwise the capture is enough and a live lane is needs-operator).
   - **RESEARCH-028:** a canned probe, plus live state recorded as observed.
   - **UI-032:** live "Apple" → 320193.
   - **DATA-054:** live SMR → standalone.
   - **DATA-055:** live NAPEROL `listing_date` ≠ 2002-07-01.
   - **DATA-061:** live `/macro/GDP` with no library text.
   - **DATA-071:** a cold `/history/<BSE small-cap>?range=1y` shows more than 8 bars or `partial:true`.
   - **LEAD-013:** the pack age.
   - **UI-084, UI-024, UI-048:** vitest-certified; the GUI feel is recorded as needs-GUI.

---

## 4. Deferred (with reason)

- **Operator-attended funded live lanes:**
  - `AGENT-007` (high): the eval loop needs a real-data scenario set and a pass^k per provider on funded keys.
  - `AGENT-017` (high): the default is `deepseek/deepseek-v4-flash` in `model_registry.json`. Swapping it without the AGENT-007 eval would repeat the "default-not-proven" class.
  - `AGENT-049`: the fix was delivered in batch 9 (6b70230), and certifying it needs a live native-search lane.
- **Tier-4 (surface to the operator):** `AGENT-064`, `CODE-FRONTEND-013`, `CODE-PLATFORM-010`, `CODE-PLATFORM-015`, `CODE-PLATFORM-071`, `CODE-PLATFORM-073`, `CROSS-PLATFORM-001`, `DOCS-002`, `DOCS-003`, `DOCS-015`, `UI-044`. They cover the plugin contract, the §6.5 scope, CI and `.github/`, licensing, BLUEPRINT §2/CLAUDE.md, and core architecture.
- **Needs a decision or profiling:**
  - `DATA-059`: the former-name alias index needs a data-source decision; it is large.
  - `LIFECYCLE-026`: needs profiling and a soak, and collides with W7's `provider_registry.py`.
  - `CODE-PLATFORM-023`: portfolio risk analytics, a large feature.
  - `CODE-PLATFORM-025` + `UI-047`: multi-window needs a Tauri window handler and capability changes next to Tier-1 `tauri.conf.json`; large.
- **Collisions with a set here:**
  - `UI-059`, `DATA-079`, `DATA-080`: `catalog.py` is W2's, and each is a large new data capability.
  - `UI-085`: `text-charcoal-600` appears in 20 usages across 12 files owned by W2, W5, W6 and W7.
  - `UI-087`: spans ChatSidebar/SettingsPanel (W5) and the workspace launch restore (W8).
  - `LIFECYCLE-024`: the schema version touches all 8 SQLite stores, which collides with W1, W3, W4 and W8.
  - `UI-088`: the Playwright drag harness; capacity, and there is no GUI in Stage C.
- **Script classes, kept whole, for capacity (next batch):** {`CODE-PLATFORM-026`, `CODE-PLATFORM-028`, `RELEASE-005`, `RELEASE-006`} (the staleness/ensure scripts) and {`CODE-PLATFORM-027`, `RELEASE-007`} (the design-token audit wiring; RELEASE-007 touches CI scripts next to Tier-1 `.github/`).

## 5. proposed_not_defect

None. Every selected residual reproduces at base.

Moot halves are handled inside their entries, not proposed:
- `CODE-AGENT-013` aliases/default_grant are now read.
- `CODE-PLATFORM-021` host sync is already removed.
- `DATA-077` copy half is fixed by D81.
- `AGENT-083` propose_order is moot after D81.

## 6. Tier-3 decisions (the integrator records them; none is Tier-4)

- **D-B10-1:** the external MCP surface is read-only in 0.9. Host actions stay in-app behind the proposed-changes gate, and the spec is amended to say so. Opening it later is an operator decision.
- **D-B10-2:** a macro series fetch requires `provider`. Region defaults drive discovery only.
- **D-B10-3:** transform.code has one canonical evaluator, the server's Python ast. mathjs remains only a syntax check.
- **D-B10-4:** BLUEPRINT states 22 modules shipped in 0.9 and lists the rest as a v1.0 roadmap. This relabels scope honestly; nothing is cut.
- **D-B10-5:** BLUEPRINT §3.1 describes exports as webview downloads. There is no fs capability grant (it would touch Tier-1 capability config).
- **D-B10-6:** marketplace data-source rows derive from `provider_registry` via `GET /data-sources`. The India realtime/intraday vendor is deferred (no keyed vendor chosen).
- **D-B10-7:** `listing_date` means the exchange listing date (NSE master), and Yahoo's value is `first_trade_date`.
- **D-B10-8:** a BSE range covering under 50% of the request is a ProviderError, so the registry falls through. The last lane serves it flagged `partial`.
- **D-B10-9:** backtest results persist as JSON under the data dir, and the list is newest first.
- **D-B10-10:** tool results the runtime has already sent are immutable, so the Anthropic cache prefix stays stable.

## 7. Writer ground rules

1. **Worktree.**
   - Work in your own isolated worktree and branch `worktree-agent-batch-10-<Wn>-<name>`.
   - First run `git reset --hard 6b91b8fa07ea673257517f5ae7e1167f7a5d9db5` and confirm with `git log -1`.
   - Never the main worktree.
   - Push after each concrete deliverable. On a restart, read your branch log and continue.
2. **Stall rule.** No tool call longer than ~120 s. Long runs are detached and polled in separate short calls.
3. **Commits.** One focused commit per entry or root-cause group, conventional, no emojis, ending with the session's attribution trailer.
4. **Tests.**
   - Tests go only where the repo keeps them: `sidecar/tests`, `src/**/*.test.ts(x)`.
   - Pin the class case named above; it is the one the fix was not written against.
   - Never delete, skip or weaken a test to get green. A test that encodes the defect is fixed with the reason in the commit. Cases for deleted dead code are converted or removed with the symbol and named.
   - Never special-case code to satisfy a test.
   - Live captures become add-only fixtures, never live calls in a test.
5. **Checks before committing.**
   - Export the PATH line from §3.
   - Python: `ruff format <files> && ruff format --check sidecar && ruff check sidecar`.
   - TypeScript: `pnpm format:check`, `pnpm typecheck`, `pnpm lint` and your vitest files.
6. **Scope.**
   - Touch only your §1 files and honour C5, C6 and C10-C20 exactly.
   - A needed change elsewhere goes to `issues[]` with the exact line, as do pre-existing oddities.
   - No refactoring beyond the entry.
7. **Docs.** Only W2 (MCP_INTEGRATION.md, the spec FRs), W4 (CURRENT_STATE.md) and W6 (BLUEPRINT.md outside §2, PRODUCT_DESIGN_DECISIONS.md) edit docs, and only those files. Nobody edits DECISIONS.md, CHANGELOG.md or the register.
8. **Hard limits.**
   - Never re-add trading.
   - Never touch `CLAUDE.md`, `src-tauri/tauri.conf.json`, `.github/`, `LICENSE*`, `types/plugin.ts` or `r15-fanout.js`.
   - Read no `R15_BRIEF*.md` and nothing under `r15/local/`.
   - No GUI.
   - Never print, log or commit a secret. `vy.py` reads the key in-process; never echo it.
