# set-81: lows-P2/fundamentals-profile (rc1-battery-23, candidate ace7dd76)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LIFECYCLE-030 | in-process: IN region, start_warm_fundamentals, wait past sweep first cycle, count seed_india_store calls | calls = 1 | holds |
| R15-LIFECYCLE-031 | in-process: slow boot seed, stop_warm_fundamentals | _seed_task retained, cancelled=True, handle cleared | holds |
| R15-LIFECYCLE-032 | in-process: _crawl_once with upsert_info raising for 1 of 3 symbols | returns fetched=2, no raise, WARNING "1 of 3 symbols failed" | holds |
| R15-LEAD-020 | in-process transient miss then success; live 3x /fundamentals/TCS | call2 stays None within negative TTL, re-fetches past TTL; live provider=yfinance x3 stable | holds |

COVERAGE: 4/4 ids raw; no raw: none
