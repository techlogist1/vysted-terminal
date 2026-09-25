# batch-10/W1-runtime-backtest (rc1-battery-7)

Candidate `4097dac4`. Own sidecar on `:52347`. 7 certified entries re-run.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-050 | test file presence: `sidecar/tests/test_llm_anthropic.py` (cert evidence was purely this pytest) | file present on `4097dac4` | ci_pinned |
| R15-LEAD-018 | test file presence: `sidecar/tests/test_reasoning_split.py` + fixture `tests/fixtures/llm/nemotron_cot.jsonl` (cert evidence combined one live OpenRouter run with this fixture-pinned parse test; the fixture pins the same echo case without spend) | both present | ci_pinned |
| R15-CODE-PLATFORM-029 | in-process `backtest_engine.run_backtest` with a synthetic "buy 10 every bar" strategy over 4 flat bars @100, capital 100000 | `totalReturn -4e-05`, 1 merged trade, final equity `99996.0` — exact match to cert | holds |
| R15-CODE-PLATFORM-030 | in-process `run_backtest`: buy 10 on bar 2, sell -100 (oversized) on bar 5, flat @100 | `totalReturn -2e-05`, trades `[('buy', 10.0, -2.0)]` — exact match to cert. Fresh case: buy 10@100, buy 10@120, sell 20@110, no fees → one merged lot `side=buy qty=20 entry_price=110.0 (weighted avg) pnl=0.0`, totalReturn 0.0 — exact match | holds |
| R15-LIFECYCLE-015 | in-process `backtest_store`: 3 `put()`s, `list_runs()`, then `reset_for_tests()` (simulated restart) | `list_runs()` newest-first `[run-c, run-b, run-a]` before and after reset; 3 JSON files under `<data>/backtests/`; `get(oldest)` not None after "restart" | holds |
| R15-UI-010 | `POST /backtest/run` mean_reversion with `window: 0/-5/""/1000000`; `GET /backtest/strategies` | 422 "`window` must be between 5 and 200" (0, -5, 1000000), 422 "`window` must be an integer" (`""`); `paramsSchema` advertises `minimum:5, maximum:200` — exact match to cert | holds |
| R15-UI-011 | test file presence: `src/modules/backtest/BacktestPanel.test.tsx` (cert evidence was purely this vitest — Run/Stop swap, abort+retry on a fresh controller) | file present | ci_pinned |

Raw output: `battery/raw/set-38/*`. Excluded (not certified in batch-10): R15-CODE-AGENT-009 (`invoke_agent` still one large function — the defect still reproduces).
