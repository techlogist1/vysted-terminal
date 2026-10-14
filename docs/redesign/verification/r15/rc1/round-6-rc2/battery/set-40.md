# set-40 batch-10/W1-runtime-backtest (rc1-battery-12, candidate ace7dd76)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-050 | in-process _split_system_and_messages on 3 system msgs + tool turn (raw: raw/set-40/R15-AGENT-050.txt) | persona block has cache_control, terminal preamble separate later block uncached, last tool_result cache_control set | holds |
| R15-LEAD-018 | replay tests/fixtures/llm/nemotron_cot.jsonl (24 reasoning, 1 echo content chunk) through ReasoningSplitter (live free lane not re-run; no key) (raw: raw/set-40/R15-LEAD-018.txt) | thinking len 296, answer len 0 (echo dropped) | holds |
| R15-CODE-PLATFORM-029 | engine from source: buy 10 every bar, 4 flat bars @100, cap 100000 (raw: raw/set-40/R15-CODE-PLATFORM-029.txt) | totalReturn -4e-05, final equity 99996, one merged lot of 40 (was -3.0%) | holds |
| R15-LIFECYCLE-015 | backtest_store put x3 -> list_runs, reset (restart), then 39 runs (raw: raw/set-40/R15-LIFECYCLE-015.txt) | newest-first True; after restart list newest-first True, get(oldest) found; 3 json files; get(oldest) found after 39 runs | holds |
| R15-UI-010 | live POST /backtest/run mean_reversion window 0 / -5 / '' / 1000000 on :52352 (raw: raw/set-40/R15-UI-010.txt) | 422 '`window` must be between 5 and 200' / '`window` must be an integer'; /backtest/strategies advertises minimum 5 maximum 200 | holds |
| R15-UI-011 | source probe of pinned vitest nodes (GUI repro) (raw: raw/set-40/R15-UI-011.txt) | BacktestPanel.test.tsx:261 'swaps Run for Stop...' and :499 'Stop aborts the live stream...' exist; AbortController + Stop button in BacktestPanel.tsx | ci_pinned |
