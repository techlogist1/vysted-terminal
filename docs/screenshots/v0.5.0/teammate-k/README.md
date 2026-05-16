# Teammate K — v0.5.0 populated screenshots

Captured via chrome-devtools MCP against `pnpm dev` (port 3002) +
`sidecar/main.py --port 8765`, with a window-level Tauri-internals
stub returning the sidecar port from `invoke("get_sidecar_port")`.

## Files

| File                                   | Resolution  | Subject                                                  |
| -------------------------------------- | ----------- | -------------------------------------------------------- |
| `backtest-panel-1920x1080.png`         | 1920 × 1080 | BacktestPanel with a completed Mean Reversion run on SPY |
| `backtest-panel-2560x1440.png`         | 2560 × 1440 | Same, re-captured at the higher resolution               |
| `strategy-critic-stream-1920x1080.png` | 1920 × 1080 | Chat sidebar with the pre-filled Strategy Critic prompt  |
| `strategy-critic-stream-2560x1440.png` | 2560 × 1440 | Same, re-captured at the higher resolution               |

## Run conditions

- **Strategy:** `mean_reversion` with default params
  (`window=20`, `entry_z=-2.0`, `exit_z=0.0`, `position_size=100`).
- **Universe:** `SPY`, 2024-01-01 → 2025-12-31.
- **Result:** total return -1.04%, Sharpe -0.16, Sortino -0.06,
  Calmar -0.11, Max DD -4.47%, win rate 61.1%, 18 closed trades.
- **Provider:** yfinance via the v0.5.0 `services.bar_loader`
  production loader. No mocked data — real SPY daily bars from
  the live yfinance API.

## Strategy Critic prompt

The "Open in Strategy Critic" button on the result view dropped the
following slash-command into the chat composer's transcript:

> `/agent strategy_critic Please critique my latest backtest (run id 0b6620b7-cdfc-4961-bc2c-13af9b7b2c42). Use the backtest_summary tool to load the run and apply your 9-section framework.`

The chat sidebar's panel-context header reads "CONTEXT: 6 PANELS
ACTIVE", confirming the new BacktestPanel context publisher is
registered and the focused-panel snapshot is reaching the chat
composer. The Strategy Critic agent is registered in the picker as
"AI Strategy Critic".

A full agent stream against the real LLM is not captured here — that
requires an API key on the keychain (BYOK) which the worktree does
not carry. The unit-level proof of the agent_runtime + tool-dispatch
round-trip lives in
`sidecar/tests/test_strategy_critic_e2e.py::test_strategy_critic_use_case_2_end_to_end`.
