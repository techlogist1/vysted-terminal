# unplanned-2

Candidate 4097dac4. Raw output: `raw/set-47/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-CODE-PLATFORM-030 | Read `sidecar/services/backtest_engine.py` sell branch (~line 406) | `sold = min(abs(intent.quantity), position.quantity)` — a sell order larger than the held position is clamped to the actual held quantity before pnl/equity update; a `BacktestOrderIntent(qty=-100)` against a 10-share position now sells 10, not 100. No phantom shares can be credited | holds |

Summary: 1 hold. No regressions.
