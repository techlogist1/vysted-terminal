# rc1 gate round 5 — adversarial sample verifier, shard 4 (rc1-vshard-4, Opus)

Candidate: `633f844071d972b337f4c3526d86555c80df0568` (read-only worktree `scratchpad/rc1-round-5-9bc600e-fix-int`, HEAD confirmed).
Own sidecar `:52604` (data copy `scratchpad/rc1-round-5-data-rc1-vshard-4`). In-process checks ran from `<worktree>/sidecar` as
`PYTHONPATH=. VYSTED_DATA_DIR=<scratch>/vshard4-r5/inproc-data ./.venv/bin/python3 <scratch>/vshard4-r5/<probe>.py`.
Probe scripts and raw outputs: `scratchpad/vshard4-r5/` (session scratch). Log: `logs/rc1-vshard-4.md`. Findings: `findings/rc1-vshard-4.json`.

Result: **21 holds, 3 refuted (not certified): R15-LEAD-023, R15-DATA-073, R15-UI-058.** 0 inconclusive.
Environment: Yahoo rate-limited (YFRateLimitError) for part of the window; keyless web engines flaky (DDG intermittent, Brave 429, Mojeek 403).

## Verdicts

| id | verdict | own repro at candidate | fresh variant |
|---|---|---|---|
| R15-DATA-086 | holds | dead proxy (`HTTPS_PROXY=127.0.0.1:9`): `ProviderError kind=network`, no cache row written | live "unemployment" 25 rows, "gdp per capita" 7 rows, all real hits (score 0.75), no curated padding |
| R15-LIFECYCLE-019 | holds | MockTransport 503 → block page → ReadTimeout → ok: 4 attempts, lane loaded; a second schedule adds no request | all attempts fail → lane `unavailable`, `gave_up_on` 2026-09-27, log names exc type; live `/resolve` GUJGASLTD→GUJENERGY `rename_lane: available` |
| R15-LIFECYCLE-022 | holds | UDiFF primary 404 + live legacy body (25 Sep 2026): 2926 rows, RELIANCE close 1226.0, no empty markers | both hosts 404 over a 20-day walk: only 2026-09-14 (table holiday) marked; WARNING names the URL |
| R15-CODE-AGENT-004 | holds | real `genai` UsageMetadata, thinking + tool-use-prompt counted: in 1450 / out 9500 | None-valued first chunk: no TypeError, totals unchanged |
| R15-CODE-AGENT-007 | holds | registry edit + reload: dispatch == registry == PROVIDER_INFO for deepseek/xai/openrouter | — (adjacent: research-lane literals, below) |
| R15-CODE-AGENT-016 | holds | `_schema.json` defaultProvider enum == `model_registry.provider_ids()` | an agent file with defaultProvider openrouter loads via `_discover_specs` (count 14, degraded []) |
| R15-CODE-AGENT-005 | holds | live `POST :52604/llm/chat` deepseek + openai, options `{depth, someNewKey, reasoningMode, temperature}`, fake key → provider 401 (reached HTTP, no TypeError) | log: `dropped unsupported LLM option key(s): depth, reasoningMode, someNewKey` |
| R15-CODE-AGENT-008 | holds | `brief_for`: iter→deep/deep, heavy→deep/heavy, research-model ultra→deep/heavy, each carrying its sources | live Ollama agent run auto-published `…__autobrief` (fast/quick; 0 sources because the keyless web round timed out at 8 s — honest) |
| R15-LIFECYCLE-025 | holds | stored row `['price_data','macro','news','macro']` PUT 200 → `macro_series` | `_resolve_tool_surface` maps `macro`→`macro_series`, reports `no_such_tool_v07` as retired. Minor: GET `/custom-agents` still echoes raw `macro` |
| R15-CROSS-PLATFORM-002 | holds | full pytest with `-X warn_default_encoding`: no test-file encoding warnings except a subprocess `text=True` (ASCII pgrep) | product-side `services/hardware_fit.py:114` warning is outside this entry's claim (3779 passed, 1 failed = the flaky test below) |
| R15-DATA-094 | holds | live `/news` with a fake NewsAPI key: header `x-news-sources: rss=ok;newsapi=unauthorized`; `/news/sources/status` `{"newsapi":"unauthorized"}` | no key → `absent`; the fake key never appears in the sidecar log; panel badges via `fetchNewsSourcesStatus` |
| R15-LIFECYCLE-018 | holds | wedged docker (3 s) during boot `warm_detect`: two concurrent first calls share ONE derivation (one `docker version`) | later call 0.0000 s, 0 subprocesses. Nit: `web_search.py` comments still say "instant … no network probe" |
| **R15-LEAD-023** | **refuted** | see below | |
| R15-DATA-052 | holds | ELCIDIN.NS / NAPEROL.NS → Financial Services / Investment Company (resolver source) | WPIL.NS / AXON with `""` → None + meta `unavailable`; KAYNES → Industrials. Minor: meta.provider still `yfinance` for the resolver-sourced sector |
| R15-DATA-069 | holds | code reads `currentPriceTarget/priorPriceTarget`; series titled "Mean of targets revised that day (…)", n per point | live AAPL price-target-history 972 rows, 0 null targets; `/ratings/individual` 60 rows, 0 null `current_price_target` |
| **R15-DATA-073** | **refuted** | see below | |
| R15-LIFECYCLE-021 | holds | nse_direct get_quote patched to raise: RELIANCE/INFY/TCS served by `nse`, fallthrough count 3 | `/health` quote → `ccxt (nse, bse, yfinance fallback; nse_direct failing)`; StatusChrome `useNseUnreachable` threshold 3/600 s |
| R15-UI-051 | holds | Bond/Option/Greeks render via `formatMoney`/`formatOptionPrice` + displayCurrency (default = region currency), no literal `$` | vitest `src/modules/quant` green |
| R15-UI-016 | holds | single dispatcher (`registerAction`/`resolveKeyboardAction`), every action id has a handler incl. `agent.mode.*` | vitest keybindings/CommandPalette green. Nit: stale MODULE_COMMAND_BINDINGS comment |
| R15-UI-052 | holds | OnboardingFlow 232-242/690 + OnboardingBanner:69 copy corrected | (adjacent: SettingsPanel privacy copy, below) |
| **R15-UI-058** | **refuted** | see below | |
| R15-LEAD-018 | holds | `test_nemotron_reasoning_echo_stays_out_of_the_answer` (live-capture fixture) + reasoning tests: 4 passed | splitter probe: `<think>` split across chunks → answer "Answer: 42", thinking "secret plan"; echo-only → "" (adjacent: echo-then-answer, below) |
| R15-LIFECYCLE-015 | holds | 40 results put, cache reset (restart): `backtest_summary` on the OLDEST run → ok | `GET /backtest/runs` 40 ids newest-first after an LRU `get()`; `GET /backtest/runs/{oldest}` 200; `..%2F..` → 404 |
| R15-UI-010 | holds | live `POST :52604/backtest/run` mean_reversion window 0 / -5 / "" → 422 `"\`window\` must be between 5 and 200"` / same / `"must be an integer"` | 3.5, 1e999, true → 422 "must be an integer"; 20 → 200 stream. Frontend keeps the 422 detail (`store/backtest.ts`), ParamsForm clamps on blur |

## Refutations (not certified)

### R15-LEAD-023 — refuted
Claim: "_quote_time has no no-time fallback … raises instead of pricing with an unknown as-of"; fix_shape/acceptance: "an empty-history, no-metadata-time symbol returns a priced quote instead of raising".
Command (`<worktree>/sidecar`): `PYTHONPATH=. VYSTED_DATA_DIR=<scratch>/vshard4-r5/inproc-data ./.venv/bin/python3 <scratch>/vshard4-r5/lead023.py` (fake ticker: price present, no `regularMarketTime`, empty 5d history).
Output:
```
provider-level AXON ProviderError: yfinance quote failed for 'AXON': Yahoo returned a price with no trade time kind None
registry AXON -> ProviderError yfinance quote failed for 'AXON': Yahoo returned a price with no trade time
registry ZZZT -> ProviderError yfinance quote failed for 'ZZZT': Yahoo returned a price with no trade time
```
The quote still raises; no priced quote, no unknown-as-of flag. Before the fix (`cd54947f^`) the IndexError was already caught by `get_quote`'s `except Exception` into a ProviderError, so the user-visible behaviour is unchanged; only the message text differs. `docs/redesign/DECISIONS.md` D-B9-2 ("never a synthesized timestamp") reframes the entry — that is a lead decision that rejects the fix_shape, so it needs the lead to adjudicate (close as won't-fix-by-decision, or deliver a priced quote with `as_of: null`), not a certification.

### R15-DATA-073 — refuted
Claim: "bundled trading-holiday tables end on 2026-12-25 with no regenerator or expiry test"; fix_shape: "a test asserting max(holidays) >= today + 12 months and a regenerator …; add the missing 2026 dates".
Command: `PYTHONPATH=. VYSTED_DATA_DIR=<scratch>/vshard4-r5/inproc-data ./.venv/bin/python3 <scratch>/vshard4-r5/data073.py`
Output:
```
max NSE holiday: 2026-12-25 max US: 2027-12-24
2027-01-26 (Republic Day) trading day IN: True
sessions 2027-01-25..27 IN: 2
```
Delivered: the regenerator (`services/resolver_masters/regenerate_holidays.py`) and the 2026 dates. Not delivered: the NSE table still ends 2026-12-25, and `tests/test_locale.py:82-88` asserts only `max >= Dec 1 of the current year` (D-B9-4), not today + 12 months. So a build cut any day in December 2026 passes CI and ships no 2027 NSE holidays; from 1 Jan 2027 Republic Day counts as a session and freshness lag over-counts — the entry's stated consequence. The fixed-date 2027 holidays (26 Jan, 15 Aug, 2 Oct, 25 Dec) could be bundled now.

### R15-UI-058 — refuted (partial)
Claim includes: "Import reports 'Imported settings.' for any JSON — {} or another app's file"; fix_shape: "import sets 'ok' only when a recognised section applied".
The own repro's `{}` and `{theme:'dark'}` now error, region merges over current, and unknown action ids are rejected — those parts are fixed. But `handleImportFile` (`src/components/SettingsPanel.tsx:2044-2081`) sets `appliedAny = true` whenever a section key is an object, not when anything in it applied.
Command (scratch vitest config rooted at the worktree, cache in scratch; no worktree write):
`cd <worktree> && ./node_modules/.bin/vitest run --config <scratch>/vshard4-r5/ui058/vitest.probe.config.mts`
Output (`<scratch>/vshard4-r5/ui058/result.txt`):
```
PROBE another app {settings:{fontSize:14}} => status="Imported settings. Secrets re-enter via the keychain." stateChanged=false
PROBE only unknown keybinding ids => status="Imported settings. Secrets re-enter via the keychain." stateChanged=false
PROBE empty sections => status="Imported settings. Secrets re-enter via the keychain." stateChanged=false
```
Another app's file with a `settings` object (a common export shape) still reports success with nothing applied. The existing test `SettingsPanel.test.tsx:394-404` pins the green toast on a bundle whose only valid content is rejected.

## Adjacent findings (not refutations)

1. **medium — analyst ratings swallow a Yahoo rate limit into "no coverage"** (near R15-DATA-069). `services/analyst_ratings_extended.py` `_fetch_ratings_sync` catches each accessor's exception (incl. `YFRateLimitError`) to None, so `/fundamentals/{s}/ratings/price-target-history` and `/ratings/individual` return 200 with `[]` while throttled (observed: MSFT `{"history":[]}` during the throttle window, AAPL 972 rows minutes later). The panel shows the empty "firms publish revisions" hint rather than "rate-limited".
2. **medium — Settings privacy copy still over-promises** (near R15-UI-052). `SettingsPanel.tsx:122-123` "Nothing leaves this machine except calls you make to providers you configure" (keyless Yahoo/NSE/BSE/DDG are never configured); `:1324` SearXNG "nothing leaves this machine but the pages it fetches" (queries go to upstream engines).
3. **medium (chain) — flaky `tests/test_research_fast.py::test_fast_web_round_runs_alongside_a_time_boxed_fan_out`** (near R15-CROSS-PLATFORM-002). `_stub_offline_crosschecks` stubs only dividend_actions; the live "earnings quality cross-check" leg sometimes also exceeds 0.5 s, so two legs time out and `(timed_out,) = …` raises `ValueError: too many values to unpack (expected 1)` at `test_research_fast.py:926`. Probe: 5 of 12 runs showed two timed-out legs; the full-suite run's 1 failure was this test.
4. **medium — reasoning echo followed by an answer leaks in full** (near R15-LEAD-018). `services/llm/reasoning_split.py` `_emit`: when held echo text diverges from the reasoning, the whole held echo is released as answer. Probe (`lead018.py`): reasoning R, content `R + "\n\nThe P/E ratio …"` (one chunk or chunked) → visible answer = full chain-of-thought + answer. Also a legitimate short answer that is a prefix of the reasoning ("Yes.") is dropped to "". Live nemotron shape for echo-then-answer not captured (no keyed run), so severity is provisional.
5. **low — OpenRouter chat URL still literal in research lanes** (near R15-CODE-AGENT-007): `services/research/sonar.py:42`, `services/agent_tools/deep_research.py:795` do not read `model_registry.default_base_url_for()`.

## Notes
- The worktree shows `docs/redesign/verification/r15/spend-ledger.jsonl` modified (3 lines from other agents' vy.py runs on :52152); not written by this shard.
- Ollama lock incident (AGENT-008 live run) is in the log: my lock vanished mid-hold and another holder re-created it; I SIGKILLed my wrapper so its trap could not rmdir the other agent's lock.
