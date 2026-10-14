# batch-10/W1-runtime-backtest (rc1-battery-18, candidate 9bc600ec)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-050 | `pytest tests/test_llm_anthropic.py -v`; static check of `_split_system_and_messages` | 12/12 pass incl. `test_request_carries_the_cache_breakpoints`, `test_cached_system_block_is_stable_across_turns`; source confirms `cache_control` on `system_blocks[0]` and on the last tool_result block | holds |
| R15-CODE-PLATFORM-029 | `pytest tests/test_backtest_engine.py -v`; source check of the buy path | 18/18 pass incl. `test_flat_market_pyramiding_ends_at_capital_minus_fees`; buy now merges into a weighted-average position instead of overwriting | holds |
| R15-CODE-PLATFORM-030 | same run; source check of the sell path | `test_flat_market_oversell_closes_the_held_quantity_once` and `test_partial_sell_keeps_the_rest_at_the_original_average` pass; `sold = min(abs(intent.quantity), position.quantity)` reconciles against held size | holds |
| R15-LEAD-018 | live `python3 scripts/r15/vy.py invoke copilot "is NVDA a good long-term hold? Think step by step" --provider openrouter --model nvidia/nemotron-3-super-120b-a12b:free --port 52358`; `pytest tests/test_reasoning_split.py -v` | live run: 238 thinking events tracked separately from 463 delta events, 0 hits for "produce final"/"the user asks" across the whole transcript, final answer is one clean paragraph; fixture test 4/4 pass | holds |
| R15-LIFECYCLE-015 | `pytest tests/test_backtest_store.py -v` | 4/4 pass: `test_a_result_survives_a_restart`, `test_the_33rd_run_leaves_the_first_readable`, `test_list_is_newest_first_even_after_an_old_run_is_read`, `test_a_non_uuid_run_id_never_names_a_file`; source confirms JSON persisted under `<data-dir>/backtests/<run_id>.json`, the LRU is now a cache not the only copy | holds |
| R15-UI-010 | live `GET /backtest/strategies`; `POST /backtest/run` with `window` 0/-5/""/1000000 on own sidecar (:52358) | strategies schema carries `minimum`/`maximum`; all 4 bad values return HTTP 422 with the exact certified messages ("`window` must be between 5 and 200", "`window` must be an integer") | holds |
| R15-UI-011 | static source check of `BacktestPanel.tsx`/`backtest.ts` (no live/GUI repro possible for this role) | one `AbortController` shared by Run/Retry, `handleStop` aborts it, a Stop button is wired; `startRun` now takes and uses `{signal}`; pinned vitest (`BacktestPanel.test.tsx:244,482`) present on candidate | ci_pinned |

COVERAGE: 7/7 ids raw; no raw: none.
