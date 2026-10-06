# R15 Stage C: Batch 9 Plan (1 high, 44 mediums; 0 proposed not-a-defect)

- **Base:** branch `004-r4-experience-rebuild` at `c1f0fea7122cfd008a887bc2b115c56c28c8423b` (batch-9 adjudication `a288397`, then the docs-only sha record `c1f0fea`; no code differs from batch-8's merge `68bb7aa4`). D81 is merged (`a122dbf6`, feat(d81)), so nothing here re-adds trading, orders, brokers or a paper account.
- **Author:** the batch planner (Opus). I wrote every row after opening the code it names at this base. Mechanisms follow the corrected verdicts (the batch-8 not-certified notes and refuter corrections), not the raw claims. Line numbers are at base.
- **Queue at base:** 0 critical, 3 high, 114 medium, 205 low open. The operator's four named areas are preferred: ui-panels, agent-chat, research-search and data-smallcaps. Every selected entry carries at least one of them.
- **Selection: 45 entries in 5 writer sets (2 opus, 3 sonnet).**
  - **High:** `LEAD-022` is taken. `AGENT-007` and `AGENT-017` stay deferred because they are operator-attended funded live lanes (§4).
  - **Carried from batch 8 (not certified or undelivered):** `AGENT-046`, `CODE-AGENT-008`, `RESEARCH-027` (residual: the price and fundamentals legs are not time-boxed), `DATA-061` (residual: kind=None leaks raw text), `UI-053` (residual: the IMF catalog ids are dead upstream), `UI-015` (residual: Earnings and Screener flatten the error).
  - **The lead's named priorities:** RESEARCH-028 + LIFECYCLE-018; the fundamentals-profile set DATA-048/054/055/052 + LEAD-016; the keybinding class UI-016/027/086 + CODE-FRONTEND-016; AGENT-049; LIFECYCLE-021/025; DATA-062/065/066/068; UI-018/028/051; CODE-AGENT-005; CROSS-PLATFORM-004.
  - **Taken from the lead's list but deferred for cause:** `AGENT-053` (panel files split across three writers), `UI-084` (workspace-blob persistence), `CODE-PLATFORM-021` (portfolio fork, a store-truth decision; no writer has capacity at opus).
- **Why 45, not 60:** five writers at 7-10 entries, each with one or two large entries, is what batches 2-8 delivered (batch 8 certified 39 of 47). Every other candidate collides with a file a set here owns, needs a decision, or is Tier-4 (§4).
- **Class rule:** a class is a shared root cause, not a shared label. The classes taken together:
  - `UI-016` + `CODE-FRONTEND-016` + `UI-027` + `UI-086`: the keybindings store is a lookup table with no dispatcher, so a binding is honoured, recorded and displayed by whichever component chose to.
  - `RESEARCH-028` + `LIFECYCLE-018`: the SearXNG manager's health is a one-bit probe, taken lazily on the research hot path.
  - `DATA-048` + `DATA-054` + `DATA-055` + `DATA-052`: the Fundamentals profile is a Yahoo `info` pass-through with no derivation, basis, period or classification check.
  - `DATA-066` + `DATA-062`: the /quotes batch is a positional fan-out of per-symbol to_thread calls behind a sleep-holding global throttle.
  - `UI-028` + `UI-051`: the quant panels render engine values with no display convention (units, currency).
  - `AGENT-049` + `AGENT-082` (sidecar leg): the one price table in `budget_guard` prices only metered-run tokens.
- **proposed_not_defect:** none. Every selected entry reproduces at base.

---

## 0. The 45 entries

| # | Entry | Sev | Mechanism (one line) | Writer |
|---|---|---|---|---|
| 1 | R15-AGENT-046 | med | tool_call_id unique only per invocation (`seen_call_ids` resets); ledger is process-global, TTL 600 s | W1 |
| 2 | R15-CODE-AGENT-008 | med | runtime decodes research payload variants (C6 `brief` never built) | W1 |
| 3 | R15-RESEARCH-027 | med | price/fundamentals legs un-time-boxed; 2/5 cold NORMAL runs over 15 s | W1 |
| 4 | R15-CODE-AGENT-005 | med | /llm/chat denylist vs agent-path allowlist | W1 |
| 5 | R15-LIFECYCLE-025 | med | persisted tool id `macro` has no alias; `_known()` drops silently | W1 |
| 6 | R15-AGENT-049 | med | native web search uncapped off Anthropic and unpriced | W1 |
| 7 | R15-AGENT-082 | med | foreground spend never priced (sidecar leg W1, footer leg W5) | W1 + W5 |
| 8 | R15-RESEARCH-028 | med | `_probe_health` ignores `unresponsive_engines`; nudge keyed on backend only | W2 (+W5 Settings leg) |
| 9 | R15-LIFECYCLE-018 | med | docker derivation lazily on the hot path; flag set before await | W2 |
| 10 | R15-AGENT-063 | med | news scoring and tagging in the router; tool path unscored | W2 |
| 11 | R15-DATA-094 | med | NewsAPI key "configured" with no probe; 401 swallowed | W2 |
| 12 | R15-UI-033 | med | marketplace `configure()` has no error path | W2 |
| 13 | R15-UI-083 | med | brief export is clipboard-only | W2 |
| 14 | R15-CROSS-PLATFORM-002 | med | sidecar tests read fixtures with the platform-default encoding | W2 |
| 15 | R15-UI-050 | med | Notes slash-menu two-line rows in fixed `h-8` | W2 |
| 16 | R15-UI-032 | med | SEC company search has no UI; the provider returns (and caches) empty | W2 |
| 17 | R15-DATA-048 | med | ROCE absent; ROE/D-E/EPS/PE/mcap/growth single-provider pass-through | W3 |
| 18 | R15-DATA-054 | med | no consolidation basis on Fundamentals | W3 |
| 19 | R15-DATA-055 | med | no listing date, 52w leg dates or forward-PE horizon | W3 |
| 20 | R15-DATA-052 | med | `sector=""` counts as ok; India sector map never overrides Yahoo | W3 |
| 21 | R15-LEAD-022 | high | `_yahoo_symbol` dot-to-dash mangles foreign suffixes (BHP.AX → BHP-AX) | W3 |
| 22 | R15-LEAD-023 | med | `_quote_time` IndexError on an empty 5d frame | W3 |
| 23 | R15-LEAD-016 | med | `reported_date` is the fiscal quarter end | W3 |
| 24 | R15-DATA-068 | med | earnings/analyst envelopes and stores carry no as-of or TTL | W3 |
| 25 | R15-DATA-069 | med | price-target provider reads dead `PriceTarget` columns | W3 |
| 26 | R15-UI-015 | med | Earnings/Screener flatten the error, so it is retried as transient | W3 |
| 27 | R15-DATA-061 | med | kind=None keeps `str(exc)` as detail (raw library text) | W4 |
| 28 | R15-DATA-066 | med | nse_direct throttle sleeps inside worker threads under a global lock | W4 |
| 29 | R15-DATA-062 | med | batch results suffix-stripped and positional; failures vanish | W4 |
| 30 | R15-LIFECYCLE-021 | med | registry fall-throughs uncounted; health tracks only Yahoo | W4 |
| 31 | R15-DATA-065 | med | weekly/monthly freshness from the period-start timestamp | W4 |
| 32 | R15-DATA-073 | med | holiday tables end 2026-12-25; no regenerator or expiry test | W4 |
| 33 | R15-UI-053 | med | all 8 IMF catalog ids are dead upstream (IFS SDMX 2.1 204/404) | W4 |
| 34 | R15-UI-028 | med | Greeks shown in QuantLib units, unlabelled; a backend comment is false | W4 |
| 35 | R15-UI-051 | med | Option pricer hard-codes `$` (Bond fixed in DATA-100) | W4 |
| 36 | R15-UI-016 | med | no global keydown dispatcher; palette hard-codes Mod+K | W5 |
| 37 | R15-CODE-FRONTEND-016 | med | 6 advertised defaults have no handler | W5 |
| 38 | R15-UI-027 | med | recorder never emits `mod`; conflicts compare raw strings | W5 |
| 39 | R15-UI-086 | med | palette rows never show their binding | W5 |
| 40 | R15-CROSS-PLATFORM-004 | med | layout modes only in the macOS menu | W5 |
| 41 | R15-UI-018 | med | destructive actions are one unconfirmed click | W5 |
| 42 | R15-UI-058 | med | settings export covers 3 fields; import reports ok for any JSON | W5 |
| 43 | R15-DATA-092 | med | Region hint says "Defaults to United States", formatting only | W5 |
| 44 | R15-AGENT-088 | med | a bare ticker always pays an LLM round-trip | W5 |
| 45 | R15-UI-052 | med | onboarding promises keyless web research and absolute privacy | W5 |

---

## 1. File ownership: five disjoint sets

A file belongs to exactly one writer. Test files follow their subject, and new tests go in new files where an owned test file is someone else's. Anything outside your list goes to `issues[]`.

- **W1 `agent-runtime` (opus):**
  - Sidecar: `sidecar/services/agent_runtime.py`, `sidecar/services/agent_tools/research.py`, `sidecar/services/research/fast.py`, `sidecar/services/research/deep.py` (brief shape only), `sidecar/services/action_ledger.py`.
  - LLM adapters and routes: `sidecar/services/llm/{__init__,openai,gemini,ollama,native_search,tool_call_rescue}.py` (OpenRouter rides `openai.py`), `sidecar/routers/llm.py`, `sidecar/routers/agents.py`, `sidecar/models/llm.py`.
  - Budget and registry: `sidecar/services/budget_guard.py`, `sidecar/services/model_registry.py`, `sidecar/config/model_registry.json`.
  - Custom agents and catalog: `sidecar/models/custom_agent.py`, `sidecar/services/agent_tools/{catalog,schemas}.py`.
  - Tests: `test_agent_runtime.py`, `test_research_fast.py`, `test_research_tools.py`, `test_llm_router.py`, `test_llm_gemini.py`, `test_llm_openai.py`, `test_native_search.py`, `test_budget_guard.py`, `test_capability_catalog.py`, `test_mcp_catalog_parity.py`, `test_custom_agents_router.py`, plus new `test_tool_call_identity.py`.
- **W2 `research-search-news` (sonnet):**
  - Search: `sidecar/services/searxng_manager.py`, `sidecar/services/agent_tools/web_search.py`, `sidecar/app.py` (lifespan line only).
  - News: `sidecar/services/news_provider.py`, `sidecar/routers/news.py`, `sidecar/services/agent_tools/news_tool.py`.
  - SEC: `sidecar/services/sec_filings_provider.py`, `src/modules/sec/SecFilingsPanel.tsx`, `src/store/sec.ts`, `types/sec.ts`.
  - Marketplace and news panel: `src/store/marketplace.ts`, `src/modules/marketplace/MarketplacePanel.tsx`, `src/modules/news/NewsFeedPanel.tsx` (source-status badge only).
  - Brief and notes: `src/modules/research/BriefPanel.tsx`, `src/lib/export-artifact.ts` (read; edit only if a settle hook is missing), `src/modules/notes/NotesPanel.tsx`.
  - Tests:
    - Sidecar: `test_searxng_manager.py`, `test_web_search.py`, `test_news.py`, `test_news_tool.py`, `test_sec_filings_provider.py`.
    - Frontend: `BriefPanel.test.tsx`, `store/marketplace.test.ts`, `SecFilingsPanel.test.tsx`, `store/sec.test.ts`, `NotesPanel.test.tsx`.
    - The CROSS-PLATFORM-002 encoding files: `test_search_extract.py`, `test_nse_provider.py` (encoding lines only; W4 adds its NSE tests in new files), `test_corporate_disclosures.py`, `test_bse_provider.py`, `test_no_tradesa.py`, `test_b5_india_deals.py`, `test_b6_quant_pool.py`, `test_b7_exchange_disclosures.py`, `test_b7_exchange_financials.py`, `test_backtest_custom.py`, `test_dividend_actions.py`, `test_fundamentals_seed.py`, `test_workflow_node_contract.py`, plus new `test_tests_encoding.py`.
- **W3 `fundamentals-identity-earnings` (sonnet):**
  - Fundamentals and identity: `sidecar/services/yfinance_provider.py`, `sidecar/models/fundamentals.py`, `types/data.ts` (sole owner), `src/modules/equity-overview/EquityOverviewPanel.tsx`, `sidecar/services/resolver_masters/{india_sector_map.json,regenerate_india_sectors.py}`, `sidecar/services/symbol_resolver.py` (sector-map read only), `sidecar/models/screener.py` (debt-free case).
  - Earnings: `sidecar/services/earnings_provider.py`, `sidecar/models/earnings.py`, `sidecar/routers/earnings.py`, `types/earnings.ts`, `sidecar/services/agent_tools/earnings_tools.py` (only if the field split needs it).
  - Analyst: `sidecar/services/analyst_ratings_extended.py`, `sidecar/models/analyst_extended.py`, `types/analyst.ts`.
  - Cache: `sidecar/services/data_cache.py` (additive `get_with_meta` only).
  - Frontend: `src/store/{earnings,analyst-ratings,screener}.ts`, `src/modules/earnings/{EarningsCalendarPanel,EarningsSurpriseChart}.tsx`, `src/modules/analyst-ratings/{AnalystRatingsPanel,PriceTargetTimeline}.tsx`, `src/modules/screener/ScreenerPanel.tsx`.
  - Tests: `test_yfinance_provider.py`, `test_fundamentals.py`, `test_india_sector_map.py`, `test_symbol_resolver.py`, `test_earnings_*.py`, `test_research_nodes.py` (fixture field only), `test_analyst_ratings_extended.py`, `test_analyst_extended_router.py`, `test_data_cache.py`, `test_screener.py`, and the matching vitest files.
- **W4 `market-lanes-errors-quant` (opus):**
  - Errors: `sidecar/services/errors.py`.
  - NSE lane and quotes: `sidecar/services/nse_provider.py`, `sidecar/routers/quotes.py`, `src/modules/watchlist/{api.ts,WatchlistPanel.tsx}`.
  - Registry and health: `sidecar/services/provider_registry.py`, `sidecar/services/provider_health.py`, `sidecar/routers/system.py` (provider-health route only), `src/components/StatusChrome.tsx`.
  - History and calendars: `sidecar/routers/history.py`, `sidecar/services/locale.py`, new `sidecar/services/resolver_masters/regenerate_holidays.py`.
  - Macro: `sidecar/services/macro/imf_provider.py`, `src/modules/macro/MacroPanel.tsx`, `src/store/macro.ts`.
  - Quant: `src/modules/quant/{GreeksDashboard,OptionPricerPanel}.tsx`, new `src/modules/quant/units.ts`, `sidecar/services/quant/{options,greeks}.py` (comments only).
  - Tests: `test_errors.py`, `test_provider_error_mapper.py`, `test_quotes.py`, `test_provider_registry.py`, `test_provider_health.py`, `test_history.py`, `test_locale.py`, `test_macro_providers.py`, `test_macro_router.py`, the new `test_nse_throttle.py` + `test_provider_fallthrough.py`, and the vitest files for those panels.
- **W5 `frontend-shell` (sonnet):**
  - Keybindings and palette: `src/store/keybindings.ts`, `src/components/CommandPalette.tsx`, `src/store/command-palette.ts`, `src/lib/menu-bridge.ts`.
  - Agent shell and chat: `src/modules/chat/{ChatSidebar.tsx,slash-commands.ts,streaming.ts}`, `src/components/AgentDock.tsx`, `src/app/page.tsx`, `src/lib/chat-history.ts`.
  - Settings: `src/components/SettingsPanel.tsx`, `src/store/{settings,search-settings}.ts`, `src/lib/region.ts`.
  - Destructive-action sites: `src/modules/agent-builder/AgentBuilderPanel.tsx`, `src/modules/platform/WorkspaceDialog.tsx`, `src/modules/portfolio/PortfolioPanel.tsx`, `src/lib/keychain.ts` (read), new `src/components/ConfirmButton.tsx`.
  - Onboarding: `src/components/{OnboardingFlow,OnboardingBanner}.tsx`.
  - Tests: the matching vitest files.

**Contracts (frozen; a writer codes against them, the integrator checks them):**
- **C5, C6 carry over from batch 8 unchanged.**
  - C5: the data-route error body is `{"detail": <sentence>, "code", "action"}`.
  - C6: the research tool result carries `brief`, which is exactly the snake_case dict today's `_auto_publish_event` builds, including `web_reason` and `backend`. The runtime publishes it verbatim, and the frontend `briefFromInput` is unchanged.
- **C10 (W2 → W1 brief, W5 Settings).** `searxng_manager.snapshot()["state"]` gains `"degraded"`: the container answers, but every engine is unresponsive or a run of 3 probes returns empty. `reason` carries the engine sentence (e.g. "google, duckduckgo: CAPTCHA") in `error` AND `degraded` states. When degraded, `web_search` does not route through SearXNG; it takes the keyless fallback with `backend: "keyless-fallback"` and `reason: "searxng_degraded"`. That reason reaches the brief as `web_reason` through C6 unchanged.
- **C11 (W1 → W5).** `LLMDoneEvent` gains `spend_usd: float | None`, set from `budget_guard.estimate_spend_usd` for a priced model with usage, otherwise `None`. Both `/agents/{id}/invoke` and `/llm/chat` done frames carry it. `streaming.ts` (W5) parses it to `spendUsd?: number`.
- **C12 (W3; W1 reads through the fundamentals tool, no code change).** `Fundamentals` gains these additive fields: `roce`, `basis: "consolidated"|"standalone"|null`, `listing_date`, `fifty_two_week_high_date`, `fifty_two_week_low_date`, `forward_pe_fiscal_year`. A derived ratio carries `FieldMeta.provider = "derived"` with a `basis_note` naming its formula. `types/data.ts` is mirrored in the same commit.
- **C13 (W3).**
  - `EarningsHistoryEntry` gains `period_end: date` (the fiscal quarter end, now the sort key). `reported_date` becomes `date | None` and is the actual announcement date from `get_earnings_dates`, never the period end.
  - The earnings and analyst envelopes gain `as_of: datetime | None` from `data_cache.get_with_meta`.
  - `types/earnings.ts` and `types/analyst.ts` are mirrored.
- **C14 (W4).**
  - /quotes keeps its shape. Each returned quote's `symbol` is the REQUESTED spelling (the route stamps it), and the client treats a requested symbol absent from a completed batch as "unavailable", never as loading.
  - `/system/provider-health` gains `fallthroughs: [{provider, model_key, count, last_error, last_at}]` (additive).

---

## 2. Per-writer entries (mechanism, then fix, test and files)

### W1: `agent-runtime` (opus: agent runtime tool-call identity + budget-ceiling state machine; AGENT-046 and CODE-AGENT-008 went undelivered three times)

**Priority order:** AGENT-046 → CODE-AGENT-008 → RESEARCH-027 → CODE-AGENT-005 → LIFECYCLE-025 → AGENT-082 sidecar leg → AGENT-049. Push after each.

**R15-AGENT-046: a tool call's identity is unique only per invocation.**
- **Mechanism.**
  - `agent_runtime.py:2043` `seen_call_ids: set[str] = set()` is per `invoke_agent`, and `:2085-2087` re-mints only an empty or already-seen id.
  - Gemini mints `f"{name}_{index}"` per stream, so `set_chart_symbol_0` recurs in every run.
  - `action_ledger` is process-global (TTL 600 s, `get` does not pop), so a turn-1 ack grounds turn 2's action as applied.
  - The auto-brief id is `f"{tool_call_id}__autobrief"`.
- **Fix.** The runtime owns identity: it mints `call_<uuid4hex>` for EVERY tool call, whatever the provider sent. It already builds both the tool-use turn and the result turn, so pairing holds. The auto-brief id is minted the same way. `action_ledger.take` (pop) is the read on the confirm path.
- **Test.** Written against the cross-run case, not the Ollama one: two `invoke_agent` turns with a fake Gemini adapter emitting `set_chart_symbol_0` both times; a late ack for turn 1 does not ground turn 2. Plus a prior `__autobrief` ack does not confirm a new brief.
- **Files:** `agent_runtime.py`, `action_ledger.py`, new `test_tool_call_identity.py`.

**R15-CODE-AGENT-008: the runtime decodes the research payload (C6).**
- **Mechanism.** `_auto_publish_event` (`:1206-1345`) decodes `web.citations|results`, `excerpt|snippet`, `web_available` top-level vs nested, `note`/`web_reason`, and `_LOOP_TO_MODE_DEPTH` (`:1157-1179`). The research tool returns no `brief`.
- **Fix.** Build the brief dict in `agent_tools/research.py` (next to `_stamp_execution`, `:101-138`) for FAST, DEEP and ITER, then publish `result["brief"]` verbatim. Delete the decoding and `_LOOP_TO_MODE_DEPTH` from the runtime, and keep only the auto-publish trigger.
- **Test.** For each engine's recorded payload, the published brief has non-empty `sources` and the correct `mode`/`depth`. Pin: a payload whose web round used `results` + `snippet` (the variant the runtime special-cased) still yields sources.
- **Files:** `agent_runtime.py`, `agent_tools/research.py`, `research/fast.py`, `research/deep.py`.

**R15-RESEARCH-027: the leading legs are not time-boxed.**
- **Mechanism.** `fast.py:288-291` `asyncio.gather(_safe_call(price_data), _safe_call(fundamentals))` has no timeout. Only the witnesses use `_WITNESS_LEG_TIMEOUT_S = 6.0` (`:90`, `:341`), so a throttled Yahoo stalls the whole gather.
- **Fix.** Wrap both leading legs in the same `asyncio.wait_for` budget. A timed-out leg is marked `timed_out` in the step log (latency_ms stamped) and the brief publishes without it. Keep the web round concurrent.
- **Test.** A price stub sleeping 20 s → the FAST path returns under 8 s with that leg marked timed out and the fundamentals leg intact.
- **Files:** `research/fast.py`, `test_research_fast.py`.

**R15-CODE-AGENT-005: two option filters with opposite policies.**
- **Mechanism.** `routers/llm.py:126-130` uses a 4-name denylist, and `agent_runtime.py:110` `_ADAPTER_OPTION_KEYS` is an allowlist (`:2006`).
- **Fix.** Move `_ADAPTER_OPTION_KEYS` plus `scrub_adapter_options()` into `services/llm/__init__.py`, call it from both paths, and delete both local filters.
- **Test.** POST `/llm/chat` with `{depth: "deep", someNewKey: 1}` against a fake adapter → only allowlisted kwargs arrive.
- **Files:** `llm/__init__.py`, `routers/llm.py`, `agent_runtime.py`, `test_llm_router.py`.

**R15-LIFECYCLE-025: a renamed tool id orphans stored agents.**
- **Mechanism.** `Capability.aliases` exists but nothing reads it. `custom_agent` validation and `_known()` drop or 422 on `macro`.
- **Fix.** Resolve persisted ids through `catalog` aliases (add `macro` → `macro_series`) in the custom-agent validator and in `_known()`. An id that is still unknown is logged, and a one-time notice ("tool X is no longer available") reaches the stream.
- **Test.** A stored agent with `macro` gets `macro_series` in its tool schemas and PUTs cleanly. Class pin: a second alias added only in the test catalog resolves the same way.
- **Files:** `models/custom_agent.py`, `agent_tools/catalog.py`, `agent_tools/schemas.py`, `agent_runtime.py`, `test_capability_catalog.py`, `test_custom_agents_router.py`.

**R15-AGENT-082 (sidecar leg) + R15-AGENT-049: one price table, priced everywhere.**
- **Mechanism.**
  - `LLMDoneEvent` (`models/llm.py:226`) has no spend field, and `budget_guard.estimate_spend_usd` (`:85`) is used only by durable runs.
  - `opts["web_search_max_uses"]` (`agent_runtime.py:1941`) is honoured only by Anthropic. Native searches are counted and priced nowhere.
- **Fix.**
  - C11: stamp `spend_usd` on both done frames.
  - Add `search_usd_per_1k` per model in `model_registry.json`, fold it into `cost()`, count native searches from each adapter's citation/usage metadata per round, and stop sending the native web-search option once the run total reaches `_WEB_SEARCH_CAP`.
- **Test.**
  - pytest: the done event carries `spend_usd` for a priced model and `None` for an unpriced one.
  - A fake native-search round reporting 3 searches increments the counter and the cost. After the cap, the adapter kwargs carry no search option. Class pin: exercise the cap on the OpenRouter provider through `openai.py`, the case not written against (the fix is authored on the OpenAI provider).
- **Files:** `models/llm.py`, `routers/agents.py`, `routers/llm.py`, `agent_runtime.py`, `budget_guard.py`, `model_registry.json`, `model_registry.py`, `llm/{openai,gemini,native_search}.py`, `test_budget_guard.py`, `test_native_search.py`.

### W2: `research-search-news` (sonnet)

**Priority order:** RESEARCH-028 + LIFECYCLE-018 → AGENT-063 → DATA-094 + UI-033 → UI-032 → UI-083 → CROSS-PLATFORM-002 → UI-050.

**R15-RESEARCH-028 + R15-LIFECYCLE-018: the SearXNG health is a one-bit probe taken on the hot path.**
- **Mechanism.**
  - `_probe_health` (`searxng_manager.py:190-208`) returns True for any `results` list, including an empty one with every engine in `unresponsive_engines`.
  - `ready_base_url_detected()` (`:366-383`) sets `_hot_path_detected = True` before the awaited `refresh()`, which is the race, and derives Docker lazily inside the first research request.
  - `app.py` lifespan (`:103-175`) never starts it.
  - `BriefPanel.tsx:686-689` keys the nudge on `backend === "keyless-fallback"` alone.
- **Fix.**
  - C10: the probe returns a state (`ready|degraded|down`) with the engine reasons, and `_set` keeps `reason` for `degraded`.
  - Kick the one-shot derivation off from the lifespan as a background task (`asyncio.create_task`, cancelled in the existing `finally` via `shutdown()`). Set the hot-path flag only after `refresh()` completes, and keep a lock.
  - `web_search` maps degraded to the keyless fallback with `reason: "searxng_degraded"`.
  - The BriefPanel nudge reads "SearXNG is running but its search engines are blocked" when `webReason === "searxng_degraded"`, and keeps the setup nudge otherwise.
- **Test.**
  - A canned all-CAPTCHA SearXNG JSON → state `degraded` with the engine names.
  - Empty-results x3 → `degraded`.
  - Two concurrent `ready_base_url_detected()` calls → one derivation.
  - `BriefPanel.test.tsx`: `webReason: "searxng_degraded"` renders the running-but-blocked copy, not "set up".
- **Files:** `searxng_manager.py`, `web_search.py`, `app.py` (one lifespan line), `BriefPanel.tsx`, tests.

**R15-AGENT-063: enrichment in the router.**
- **Mechanism.** `routers/news.py:94`, `:150-167` scores and tags, while `news_tool._news` (`:26-46`) returns raw `fetch_news` items. `_tag_symbols` needs the literal `BTC/USDT`.
- **Fix.** Add `news_provider.enrich(items, symbols, aliases)` for scoring, tagging and the requested-symbol filter, and call it from both the route and the tool. Normalise symbols (strip `/USDT`, `.NS`, `.BO` to the base) before tagging.
- **Test.** Tool items carry `sentiment` and `symbols`, and `symbols=BTC/USDT` returns tagged items. Class pin: `RELIANCE.NS` tags.
- **Files:** `news_provider.py`, `routers/news.py`, `news_tool.py`, `test_news.py`, `test_news_tool.py`.

**R15-DATA-094 + R15-UI-033: a credential is "configured" without proof, and saving can fail silently.**
- **Mechanism.** `marketplace.ts` `isConfigured` means only "the secret is present". `configure()` loops `await setSecret` unguarded, and `_fetch_newsapi_resilient` returns `[]` on 401 after retries.
- **Fix.**
  - `configure()` wraps the write loop, persists `grantedSecretIds` only for written secrets, and surfaces the error in the form's `validationError`.
  - For NewsAPI, probe once through a new GET `/news/sources/status` that takes the key as a header (`X-NewsAPI-Key`, never the body, never echoed). A 401 rejects the save with "NewsAPI rejected this key".
  - `/news` adds the response header `X-News-Sources: rss=ok;newsapi=unauthorized|ok|absent`, and NewsFeedPanel badges a non-ok NewsAPI.
- **Test.**
  - Store test with `setSecret` rejecting → the error is shown and the grant is not persisted.
  - pytest: a fake 401 key → the status reports `unauthorized`, and the key never appears in the body or logs.
- **Files:** `marketplace.ts`, `MarketplacePanel.tsx`, `NewsFeedPanel.tsx`, `news_provider.py`, `routers/news.py`, tests.

**R15-UI-032: SEC company search is dead end to end.**
- **Mechanism.** `sec_filings_provider.search_companies` (`:686-716`) decodes `results|companies` keys and caches an EMPTY list for `_FILINGS_INDEX_TTL`. `store/sec.ts` `searchCompanies` has no UI.
- **Fix.**
  - Read the installed sec-edgar-mcp server's `search_companies` return shape, decode it, and never cache an empty result.
  - Add a debounced autocomplete on the SecFilingsPanel symbol field, following the EquityOverview pattern.
  - Keep the reason on failure: this is UI-015's sec leg, already correct.
- **Test.**
  - A live-shaped fixture of the MCP result → `Apple` gives CIK `0000320193`.
  - An empty result is not cached.
  - Panel test: typing shows the suggestions.
- **Files:** `sec_filings_provider.py`, `SecFilingsPanel.tsx`, `store/sec.ts`, `types/sec.ts` (if the row type needs it), tests.

**R15-UI-083: brief export is clipboard-only.**
- **Fix.**
  - Restore "Save .md" via `saveTextArtifact`, and "Save PDF" / "Save PNG" via `savePdfArtifact` / `savePngArtifact` after the brief has settled: await the streaming-done flag and the reveal animation's end, so BRIEF-2 cannot recur.
  - Hand the decision row to the integrator (writers do not edit docs).
- **Test.** All three export actions exist, and the PDF call waits while the brief is streaming.
- **Files:** `BriefPanel.tsx`, test.

**R15-CROSS-PLATFORM-002: platform-default encoding in tests.**
- **Fix.** Add `encoding="utf-8"` to every text-mode `read_text()`, `write_text()` and `open()` in the §1 test files.
- **Test.** New `test_tests_encoding.py`: an AST scan of `sidecar/tests/*.py` fails on any text-mode call without `encoding`. It is the class pin, and it covers files nobody wrote the fix against.
- **Files:** as in §1.

**R15-UI-050:**
- **Fix.** Replace `h-8` with `min-h-8 py-1` on the two-line rows at `NotesPanel.tsx:390`.
- **Test.** A render test: no fixed `h-8` on the two-line rows.

### W3: `fundamentals-identity-earnings` (sonnet)

**Priority order:** LEAD-022 → LEAD-023 → DATA-052 → DATA-048 → DATA-054 → DATA-055 → LEAD-016 → DATA-068 → DATA-069 → UI-015.

**R15-LEAD-022: foreign exchange suffixes are mangled (high).**
- **Mechanism.** `_yahoo_symbol` (`yfinance_provider.py:160-203`) ends in `s.replace(".", "-")`, which is right for `BRK.B` and wrong for `BHP.AX`, `0700.HK`, `7203.T` and `VOD.L`.
- **Fix.** Pass through when the suffix is in a known Yahoo exchange-suffix set: AX, HK, T, L, TO, V, DE, PA, AS, SW, MI, MC, KS, KQ, SS, SZ, TW, TWO, SI, JK, BK, KL, NZ, SA, MX, JO, ST, OL, CO, HE, IR, VI, BR, LS, WA, IS, TA. None of these is a US share-class letter, so `BRK.B` keeps its dash.
- **Test.** `BHP.AX`, `0700.HK`, `VOD.L` pass through, and `BRK.B` gives `BRK-B`. Class pin: `SHOP.TO`.
- **Files:** `yfinance_provider.py`, `test_yfinance_provider.py`.

**R15-LEAD-023: the no-trade-time terminal case crashes.**
- **Mechanism.** `_quote_time` (`:421-438`) indexes `history(period="5d").index[-1]` on an empty frame. That is reachable because FastInfo falls back to `regularMarketPrice`.
- **Fix (Tier-3, D-B9-2).** An empty frame raises `ProviderError("Yahoo returned a price with no trade time", kind=None)`, so the registry falls through. Never `now()` (LEAD-005).
- **Test.** A stub with a price and an empty 5d frame → ProviderError, and the registry tries the next provider.

**R15-DATA-052: sector and industry are unchecked.**
- **Mechanism.** `sector=info.get("sector")` lets `""` through as ok. `symbol_resolver._india_sector_map()` (`:375`) is never consulted for fundamentals, and the map omits NAPEROL and has nulls for ELCIDIN (it is regenerated top-N by market cap).
- **Fix.**
  - Treat `""` as unavailable.
  - For IN names, prefer the sector-map record (`sector_source` labelled) over Yahoo.
  - Extend `regenerate_india_sectors.py` to cover every master symbol missing from the map (ComHeadernew per scrip, throttled), then regenerate.
- **Test.** ELCIDIN has non-empty sectors or an explicit `unavailable`. NAPEROL reads Financial Services.

**R15-DATA-048 + R15-DATA-054 + R15-DATA-055: the profile is a pass-through (C12).**
- **Mechanism.** `get_fundamentals` (`:502-600`) copies `info` fields. There is no `roce`, basis, listing date or 52w dates, and `fetched_at` is stamped uniformly.
- **Fix.**
  - Add a derived-ratio leg in the provider (never the router), from the statements the provider already fetches:
    - ROE = NI / equity
    - ROCE = EBIT / (total assets − current liabilities)
    - D/E = total debt / equity (0.0 when debt is reported 0)
    - EPS = NI / shares
    - P/E = price / EPS
    - market cap = price × master shares
    - revenue growth from consecutive annual periods
  - Each derived ratio is used only when Yahoo omits the value and is labelled `derived`.
  - `basis`: `consolidated` when Yahoo's statements are the consolidated set (IN), else `null`.
  - `listing_date` comes from `firstTradeDateMilliseconds`, and the panel labels the range "since listing" when history is under 52 weeks.
  - The 52w leg dates come from the 1y history argmax/argmin.
  - `forward_pe_fiscal_year` is set from the estimate period when Yahoo supplies it.
  - `models/screener.py`: a derived D/E of 0 for a debt-free name is a value, not `missing_field`.
  - EquityOverviewPanel renders ROCE, the basis chip and the since-listing label.
- **Test.** Fixtures for ELCIDIN (ratios derived), CREST (`basis: consolidated`), a listing under 52 weeks (label) and a debt-free screener row that passes a `debt_to_equity < 0.5` screen. Class pin: CHTR, a US name, derives ROCE the same way.
- **Files:** `yfinance_provider.py`, `models/fundamentals.py`, `types/data.ts`, `EquityOverviewPanel.tsx`, `models/screener.py`, tests.

**R15-LEAD-016: `reported_date` is the period end (C13).**
- **Mechanism.** `earnings_provider.get_history` (`:344-378`) uses the `earnings_history` index, which is the quarter end, as `reported_date`. The register's `files: []` is wrong: the code lives here.
- **Fix.** Add `period_end` = the index. Set `reported_date` = the nearest `get_earnings_dates()` date within 0-120 days after `period_end`, else `None`, and sort by `period_end`. Update `EarningsSurpriseChart.tsx`, the store and the tests to read `period_end` for the axis.
- **Test.** A fixture where both exist → they differ, and `reported_date` is the announcement date.

**R15-DATA-068: no as-of anywhere.**
- **Fix.**
  - Add `data_cache.get_with_meta(key, ttl) -> (value, fetched_at) | None`, additive: other callers are untouched.
  - The earnings and analyst routes stamp `as_of`.
  - `store/earnings.ts` and `store/analyst-ratings.ts` hold `{payload, fetchedAt}` with a 15-minute TTL and a `refresh(symbol)`. The panels render an as-of chip and a Refresh button (the NewsFeedPanel `refreshNonce` precedent).
- **Test.** A store TTL test (stale → refetch) and a route test (`as_of` present on a cache hit and equal to the original fetch time).

**R15-DATA-069: dead price-target columns.**
- **Mechanism.** `analyst_ratings_extended.get_price_target_history` (`:256-330`) reads `PriceTarget`/`Target`, while yfinance ships `currentPriceTarget`/`priorPriceTarget`.
- **Fix.** Map the live columns. The Individual table's Target reads `currentPriceTarget`. PriceTargetTimeline labels its series "mean of targets revised that day" with `n` per point.
- **Test.** A live-shape fixture gives more than one point and a non-null individual target.

**R15-UI-015 (residual): two panels still flatten the error.**
- **Mechanism.** `EarningsCalendarPanel.tsx:131` and `ScreenerPanel.tsx:119` throw `new Error(<string>)`, so `isTransientSidecarFailure` sees a non-`SidecarError` and retries a deterministic 502.
- **Fix.** The stores keep the `SidecarError` (`upcomingError` becomes the error object with `.message` for display), and the panels re-throw it (the MacroPanel precedent).
- **Test.** Vitest: a 502 from the earnings load → one attempt and the error state. Class pin on Screener.

### W4: `market-lanes-errors-quant` (opus: DATA-066 is a concurrency/throttle redesign; DATA-061 and UI-053 failed certification twice; UI-053 needs live IMF investigation)

**Priority order:** DATA-061 → DATA-066 + DATA-062 → LIFECYCLE-021 → UI-053 → DATA-065 → DATA-073 → UI-028 + UI-051.

**R15-DATA-061 (residual): kind=None leaks library text.**
- **Mechanism.** `errors.provider_error_response` (`:76-83`) returns `sentence or str(exc)`, and for `None` the sentence is `None`. Live examples:
  - World Bank: `APIError: JSON decoding error (https://…)`.
  - `/history/XYZ%2FABC`: `'Response' object has no attribute 'get'`.
  - IMF: `404 Client Error`, reported as a 502.
- **Fix (D-B9-1, all in `errors.py`).**
  - When `kind is None`, classify from `exc.__cause__`: an HTTP status 404 → `not_found`; 429 → `rate_limited`; `requests`/`httpx` connection or timeout errors → `network`.
  - An unclassified error that wraps a `__cause__` gets the generic sentence "The data provider returned an unexpected response.", and the raw text goes to `logger.warning` only.
  - A ProviderError with NO `__cause__` keeps its own message: it is the provider's authored sentence, e.g. "FRED needs a free API key".
- **Test.**
  - A macro provider raising `ProviderError(...) from HTTPError(404)` → 404 `not_found`.
  - A wrapped `AttributeError` → 502 with the generic sentence, and no `'Response' object` in the body.
  - Class pin on a route the fix was not written against: a `/fundamentals` provider wrapping a `requests.ConnectionError` → 503.
- **Files:** `errors.py`, `test_provider_error_mapper.py`, `test_errors.py`.

**R15-DATA-066 + R15-DATA-062: the batch is a throttled positional fan-out (C14).**
- **Mechanism.**
  - `nse_provider._Throttle.wait()` (`:172-259`) calls `time.sleep` under a `threading.Lock` inside `asyncio.to_thread` workers (`quotes.py:80-84`), so 20 IN names take about 23 s and hold executor threads.
  - Nothing caches EOD closes.
  - `get_quote` returns `Quote(symbol=bare)`, and failures are filtered out of the list.
  - WatchlistPanel polls every 5 s (`:24`).
- **Fix.**
  - Serve IN EOD quotes from an in-process cache keyed on (symbol, session date) that is valid until the next session close (`locale` calendar).
  - Throttle only real upstream calls, with the wait computed under the lock and the sleep outside it.
  - The route stamps `quote.symbol = requested`.
  - The client marks absent requested symbols "unavailable".
  - The panel polls on an EOD cadence (60 s) when every row is IN and the market is closed.
- **Test.**
  - A 20-symbol warm batch completes in under 1 s with a stubbed upstream.
  - `RELIANCE.NS` round-trips its spelling.
  - An unresolvable symbol renders "unavailable".
  - Class pin: a BSE `.BO` symbol keeps its spelling too.
- **Files:** `nse_provider.py`, `quotes.py`, `watchlist/api.ts`, `WatchlistPanel.tsx`, new `test_nse_throttle.py`, `test_quotes.py`, `WatchlistPanel.test.tsx`.

**R15-LIFECYCLE-021: fall-throughs are invisible.**
- **Fix.**
  - Count fall-throughs per (provider, model_key) in `_resolve_sync`/`_resolve_async` and expose them on `/system/provider-health` (C14).
  - `/health`'s primary comes from recent success.
  - StatusChrome shows one quiet notice ("NSE data unreachable - serving BSE") at 3 or more consecutive fall-throughs within 10 minutes.
- **Test.** 3 consecutive `nse_direct` ProviderErrors surface with a count of 3. Class pin: a yfinance → openbb fall-through is counted the same way.

**R15-UI-053 (residual): the IMF catalog is dead upstream.**
- **Fix (D-B9-3).** Probe live (curl, no key) the SDMX 3.0 dataflows that answer 200. Replace `_FEATURED` with verified live ids, and point the provider at the endpoint that serves them. Drop any row with no live equivalent and say so in the commit; if no India series is live, the catalog carries none. Update `MacroPanel.tsx:22`'s default. Record the probe output in the commit body.
- **Test.** A router test with the new default id routes to the provider. A recorded-shape fixture parses. The certification is live.

**R15-DATA-065:**
- **Fix.** For `1wk`/`1mo`, freshness asks whether the last bar's PERIOD contains the most recent session. Normalise nse_direct's period-end stamps to period start.
- **Test.** A current-month bar dated the 1st → fresh; last month's → stale.

**R15-DATA-073:**
- **Fix (D-B9-4).** Add the missing 2026 BSE non-session days. Add `regenerate_holidays.py` (NSE holiday-master API), alongside the other masters.
- **Test.** `max(_NSE_HOLIDAYS) >= Dec 1 of the current year`, so it fails in January until regenerated; NSE publishes the next year's list in December, so a 12-month-ahead assertion cannot be satisfied honestly today.

**R15-UI-028 + R15-UI-051: quant display conventions.**
- **Mechanism.**
  - `OptionPricerPanel.tsx:525` renders `${price}`, and `:559-560` shows raw vega and theta.
  - The Greeks dashboard is the same.
  - `options.py:146` claims "the panel divides by 100".
- **Fix.**
  - New `quant/units.ts` `toMarketUnits({vega, theta})`: vega/100 "per 1 vol pt", theta/365 "per day". Both panels use it.
  - The Option pricer takes the Bond pricer's display-currency select (DATA-100 precedent).
  - Correct the backend comments.
- **Test.** A helper unit test, and a panel render test showing the units and no `$` under region IN.

### W5: `frontend-shell` (sonnet)

**Priority order:** the keybinding class → CROSS-PLATFORM-004 → AGENT-082 footer → RESEARCH-028 Settings leg → UI-018 → UI-058 → AGENT-088 → DATA-092 → UI-052.

**R15-UI-016 + R15-CODE-FRONTEND-016 + R15-UI-027 + R15-UI-086: one dispatcher.**
- **Mechanism.**
  - Only `AgentDock.tsx:70-71` reads `bindingFor` + `matchesEvent`.
  - `CommandPalette.tsx:77` hard-codes meta/ctrl+K, and `ChatSidebar.tsx:561-574` hard-codes alt digits and mod+enter/backspace.
  - `platform.*`, `chart.open`, `watchlist.open`, `news.open` and `portfolio.open` (`keybindings.ts:108-150`) have no keydown path, although their palette commands exist (`modules/platform/index.ts:47-75`).
  - `SettingsPanel.comboFromEvent` (`:1367-1382`) never emits `mod`, and `conflicts()` groups raw strings.
- **Fix.**
  - Add `registerAction(id, handler)` to the keybindings store, plus one `window` keydown listener mounted in `page.tsx`. It resolves every binding via `bindingFor` + `matchesEvent` with an exact modifier match and skips text inputs, except for actions flagged `global`.
  - Module command ids dispatch through the existing module command handlers. `palette.open`, `agent.*` and `changes.*` register from their owners; delete the literal handlers.
  - Delete any default that still has no handler after the migration.
  - `comboFromEvent` emits `mod` for the platform-primary modifier, and `conflicts()` compares resolved chords.
  - `PaletteItemRow` renders the resolved binding as `<kbd>`.
- **Test.**
  - Iterate `DEFAULT_KEYBINDINGS`: each id has a registered handler and fires on its chord.
  - A remapped `palette.open` fires only on the new chord.
  - Recording Cmd+K on mac gives `mod+k`, and `meta+k` vs `mod+k` is reported as a conflict.
  - A palette row shows the remapped chord.
- **Files:** `keybindings.ts`, `CommandPalette.tsx`, `ChatSidebar.tsx`, `AgentDock.tsx`, `page.tsx`, `SettingsPanel.tsx`, `command-palette.ts`, tests.

**R15-CROSS-PLATFORM-004:**
- **Fix.** Register the five menu-bridge modes as palette commands calling `applyLayoutMode` / `resetToDefaultLayout` directly, and make `menu-bridge.ts` dispatch the same commands.
- **Test.** The palette contains every `MENU_PAYLOAD_TO_MODE` id, and invoking one calls `applyLayoutMode`.

**R15-AGENT-082 (footer leg, C11):**
- **Fix.** `streaming.ts` parses `spend_usd`. The finished assistant message stores `{inputTokens, outputTokens, spendUsd}` (`chat-history.ts`), and its footer renders "1.2k tok · ~$0.004", or tokens only when `spendUsd` is null.
- **Test.** Vitest on the parse and on the footer render.

**R15-RESEARCH-028 (Settings leg, C10):**
- **Fix.** The SearXNG row renders `degraded` as "Running, engines blocked: <reason>" and states that research falls back to keyless.
- **Test.** A `SettingsPanel.test.tsx` case.

**R15-UI-018:**
- **Fix.** One `ConfirmButton` (an inline two-step confirm: first click arms "Confirm delete?" for 4 s, second click acts), applied at every site:
  - `AgentBuilderPanel.tsx:545`
  - `WorkspaceDialog.tsx:289`
  - `PortfolioPanel.tsx:556` and `:745`
  - SettingsPanel "Reset to default" and key removal (`:510`)
  - Delete errors route through `extractSidecarDetail`, and `handleRemove` (`:418`) catches and shows the reason inline.
- **Test.** At each site, a single click does not delete. Class pin: the portfolio holding row.

**R15-UI-058:**
- **Fix.**
  - SettingsExport v2 carries `settings`, `searchSettings`, the default provider/model, `enabledModules` and keybinding overrides.
  - Import reports ok only when a recognised section applied. It merges over the CURRENT state (not `seed()`) and rejects unknown action ids.
- **Test.** An export/import round-trip preserves region and remaps. `{}` reports "Nothing recognised".

**R15-DATA-092:**
- **Fix.** The hint is derived from `DEFAULT_REGION` and states what region controls (resolver market, calendar, macro/news providers, screener universe). `regionConfig` falls back to `DEFAULT_REGION`, not `REGIONS[0]` (`region.ts:48`).
- **Test.** A render test.

**R15-AGENT-088:**
- **Fix.** `parseSlashCommand` classifies a lone `@?TICKER` found in the known set (watchlist + `useSymbolsStore` resolved) as the `/chart` action. Anything else stays raw.
- **Test.** `AAPL` and `@RELIANCE` give the chart action; `AAPL earnings?` stays raw; an unknown `ZZZZ` stays raw.

**R15-UI-052:**
- **Fix.** Remove "web research" from the keyless claims (`OnboardingFlow.tsx:241`, `:680`, `ChatSidebar.tsx:815`). The privacy line becomes "Your keys, notes and portfolio stay on this machine; market data and web searches go to public providers." (`:232`). Drop "fully private… offline" (`:260`) in favour of "runs on your machine; market data still comes from public providers".
- **Test.** A copy test on the strings.

---

## 3. Integrator run order and gates

**Stall rule (all roles).**
- No single tool call runs longer than ~120 s.
- `pnpm ci-local`, full pytest/vitest, cargo, PyInstaller builds and sidecar boots start detached (`nohup … &` or `run_in_background`) and are polled with separate short calls (`sleep 60; tail -n 5 <log>`).
- Never an `until`/`sleep` loop inside one call.
- Emit a tool call at least every 2 minutes.

1. Work in a scratch worktree (`git worktree add <scratchpad>/b9-int 004-r4-experience-rebuild`), never the main repo: it holds uncommitted `CLAUDE.md` and ledger edits.
2. Audit each branch through `origin/worktree-agent-batch-9-<Wn>-<name>`:
   - `git merge-base --is-ancestor c1f0fea7 origin/<branch>`; a stale base means re-dispatch.
   - `git diff --stat c1f0fea7..origin/<branch>` must touch only that writer's §1 files.
3. Merge `--no-ff` in this order, running that writer's tests (detached) after each:
   - **W3** (`types/data.ts`, fundamentals, earnings): run `test_yfinance_provider.py`, `test_fundamentals*.py`, `test_earnings_*.py`, `test_research_nodes.py`, `test_screener*.py`, `pnpm typecheck`.
   - **W4** (errors, lanes, macro, quant): run every `test_*_router.py`, `test_quotes.py`, `test_history.py`, `test_locale.py`, `test_provider_*.py`.
   - **W1** (runtime): run `test_agent_runtime*.py`, `test_agents_router.py`, `test_llm_*.py`, `test_capability_catalog.py`, `test_mcp_catalog_parity.py`, `test_mcp_server.py`, `test_research_*.py`, `test_b5_*`, `test_b6_*`, `test_budget_guard.py`.
   - **W2** (search, news, SEC, brief): run `test_searxng_*.py`, `test_web_search.py`, `test_news*.py`, `test_sec_*.py`, `test_tests_encoding.py` (this must run after W3/W4/W1 so it sees their new tests too).
   - **W5** last (frontend shell): full vitest.
   - **No integrator code edits**, except that if `test_tests_encoding.py` flags a new test file written by another writer, add `encoding="utf-8"` there in the W2 merge commit and name it.
4. Gates after all five (export `PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH` first; run everything long detached):
   - `ruff format --check sidecar && ruff check sidecar`.
   - `pnpm format:check`, `pnpm lint`, `pnpm typecheck`.
   - `node scripts/ensure-all-sidecars.mjs --force` (W3 regenerates `india_sector_map.json`; it rides the existing masters `--add-data`).
   - `pnpm ci-local` with the exit code recorded.
   - `node scripts/smoke-test-sidecars.mjs`.
5. Grep checks:
   - `agent_runtime.py` has no `in seen_call_ids` and no `_LOOP_TO_MODE_DEPTH`.
   - `routers/llm.py` has no local option denylist.
   - `errors.py` never returns `str(exc)` as `detail` for an exception with a `__cause__`.
   - `yfinance_provider.py` has no bare `.index[-1]` in `_quote_time`.
   - `CommandPalette.tsx` and `ChatSidebar.tsx` contain no `metaKey ||` literal chord checks.
   - `keybindings.ts` has no default without a handler.
   - `OnboardingFlow.tsx` has no "web research run" or "Nothing leaves this computer".
   - `searxng_manager._probe_health` reads `unresponsive_engines`.
6. Record the §6 decisions and the UI-083 decision row in `docs/redesign/DECISIONS.md` and `CHANGELOG.md` at merge.
7. Certification notes (one fresh verifier):
   - `AGENT-046`: a two-turn live or scripted Gemini-style run.
   - `CODE-AGENT-008`: a live FAST run whose tool result carries `brief` with sources.
   - `RESEARCH-027`: 5 cold NORMAL runs, all at or under 15 s, or the timed-out leg is shown.
   - `DATA-061`: live `/macro/GDP` (the WB decode error) returns no library text; `/history/XYZ%2FABC` likewise.
   - `UI-053`: a live IMF series returns 200 with points.
   - `DATA-066`: a 20-name IN watchlist warm batch.
   - `LEAD-022`: live `/quotes/BHP.AX`.
   - `RESEARCH-028`: a canned probe (engines are not blockable on demand); record live state as observed.
   - Keybindings and confirm flows are vitest-certified, and the GUI feel is recorded as needs-GUI.

---

## 4. Deferred (with reason)

- **Operator-attended funded live lanes:** `AGENT-007` (high), `AGENT-017` (high).
- **Tier-4, surface to the operator:** `DOCS-003`, `AGENT-064`, `CODE-PLATFORM-015`, `CODE-PLATFORM-071`, `DOCS-015`, `CODE-PLATFORM-010`, `CODE-FRONTEND-013`, `UI-044`, `CODE-PLATFORM-073`, `CROSS-PLATFORM-001`, `DOCS-002`. These cover CI, Tier-1 files, licensing, the §6.5 safety scope and core architecture.
- **Collisions with a set here:**
  - `AGENT-053`: its panels are split across W2 (SEC, News), W3 (Earnings, Analyst) and W5 (chat context).
  - `UI-084`: AgentDock and page.tsx are W5's, and workspace-blob persistence is risk-adjacent (next batch at opus).
  - `CODE-AGENT-009`: refactoring `invoke_agent` collides with W1's five fixes.
  - `CODE-AGENT-013`, `AGENT-083`, `AGENT-084`, `RESEARCH-030`, `DATA-080`, `UI-059`, `DATA-079`: `catalog.py` is W1's.
  - `AGENT-050`: `agent_runtime.py` is W1's.
  - `UI-091`: `fast.py` is W1's.
  - `CODE-RESEARCH-004`: `searxng_manager.py` is W2's.
  - `UI-085`: BriefPanel is W2's, CommandPalette W5's.
  - `UI-048`, `UI-087`: `settings.ts`/SettingsPanel are W5's.
  - `CODE-PLATFORM-012`/`013`/`014`: the plugin-lifecycle class; `marketplace.ts` is W2's, and the class is kept whole.
  - `CODE-PLATFORM-072`: `marketplace.ts`.
  - `AGENT-057`: plugin-agents sync; kept with the plugin class.
  - `DATA-053`, `DATA-071`: `types/data.ts` is W3's and `models/market.py` pairs with W4's quotes; kept together next batch.
  - `DATA-096`: `data_cache.py` is W3's.
  - `DATA-077`: `provider_registry`/`history` are W4's.
  - `LIFECYCLE-026`: `provider_registry` is W4's.
  - `UI-024`: NotesPanel is W2's.
  - `CODE-PLATFORM-021`: a portfolio store-truth decision; PortfolioPanel is W5's.
  - `CODE-PLATFORM-023`: PortfolioPanel.
  - `DATA-087`: `routers/macro.py`, and FR-060's provider-less default needs a decision; not a named area.
  - `CROSS-PLATFORM-003`: `routers/system.py` is W4's.
- **Needs a decision or a capture:** `DATA-059` (alias index source), `CODE-PLATFORM-017` (which evaluator is canonical), `LEAD-018` (no live capture), `LEAD-013` (sp500 pack regeneration run).
- **Capacity (next batch):**
  - The backtest set: `CODE-PLATFORM-029`/`030`, `LIFECYCLE-015`, `UI-010`, `UI-011`.
  - The screener formula and docs drift: `RESEARCH-025`, `DOCS-004`, `DOCS-005`, `DOCS-016`, `DOCS-017`, `DOCS-018`, `DATA-078`.
  - The build scripts: `CODE-PLATFORM-024`/`025`/`026`/`027`/`028`, `RELEASE-005`/`006`/`007`.
  - Also: `DATA-095`, `LIFECYCLE-024`, `UI-047`, `UI-088`.

## 5. proposed_not_defect

None. Every selected entry reproduces at base.

## 6. Tier-3 decisions (the integrator records them; none is Tier-4)

- **D-B9-1:** the kind=None mapping classifies from `__cause__`. A wrapped unclassified error gets a generic sentence, with the raw text in the log only. An authored ProviderError with no cause keeps its sentence.
- **D-B9-2:** a Yahoo price with no trade time is a ProviderError (registry falls through), never a synthesized timestamp.
- **D-B9-3:** the IMF catalog carries only live-verified ids; a row with no live equivalent is dropped, not faked.
- **D-B9-4:** the holiday expiry test asserts coverage to Dec 1 of the current year, because NSE publishes next year's list in December.
- **D-B9-5:** tool-call identity is always runtime-minted (provider ids are never trusted for pairing or acks).
- **D-B9-6:** a derived ratio fills a value only where Yahoo omits it, labelled `derived` with its formula; it never overrides a provider value.
- **D-B9-7:** `reported_date` becomes nullable, and `period_end` is the sort key.
- **D-B9-8:** a degraded SearXNG routes research to the keyless fallback with reason `searxng_degraded`.
- **D-B9-9:** keybinding defaults with no handler after the dispatcher migration are deleted, not left advertised.
- **D-B9-10:** the brief export restores MD/PDF/PNG with a settle wait (SC-035), recorded in DECISIONS.md.

## 7. Writer ground rules

1. **Worktree.**
   - Work in your own isolated worktree and branch `worktree-agent-batch-9-<Wn>-<name>`.
   - First run `git reset --hard c1f0fea7122cfd008a887bc2b115c56c28c8423b` and confirm with `git log -1`.
   - Never the main worktree.
   - Push after each concrete deliverable.
   - On a restart, read your branch log and continue.
2. **Stall rule.** No tool call longer than ~120 s. Long runs are detached and polled in separate short calls.
3. **Commits.** One focused commit per entry or root-cause group, conventional, no emojis, ending with the session's attribution trailer.
4. **Tests.**
   - Tests go only where the repo keeps them: `sidecar/tests`, `src/**/*.test.ts(x)`.
   - Where a class is involved, pin the case the fix was not written against (named above).
   - Never delete, skip or weaken a test to get green. A test that encodes the defect is fixed with the reason in the commit.
   - Never special-case code to satisfy a test.
   - Live captures become add-only fixtures, never live calls in a test.
5. **Checks before committing.**
   - Export the PATH line from §3.
   - Python: `ruff format <files> && ruff format --check sidecar && ruff check sidecar`.
   - TypeScript: `pnpm format:check`, `pnpm typecheck`, `pnpm lint` and your vitest files.
6. **Scope.**
   - Touch only your §1 files and honour C5, C6 and C10-C14 exactly.
   - A needed change elsewhere goes into `issues[]` with the exact line.
   - No refactoring beyond the entry and no defensive code for cases that cannot happen.
   - Pre-existing oddities go to `issues[]`.
7. **Hard limits.**
   - Never re-add trading.
   - Never touch `CLAUDE.md`, `src-tauri/tauri.conf.json`, `.github/`, `LICENSE*`, `types/plugin.ts`, `r15-fanout.js`, `docs/` or the register.
   - Read no `R15_BRIEF*.md` and nothing under `r15/local/`.
   - No GUI.
   - Never print, log or commit a secret (NewsAPI keys in tests are fake).
