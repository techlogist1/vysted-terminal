# RC1 gate round 5 — adversarial verifier shard 6 (rc1-vshard-6, Opus)

Candidate 633f844071d972b337f4c3526d86555c80df0568 (worktree `rc1-round-5-9bc600e-fix-int`, `git rev-parse HEAD` checked). Own sidecar from that source on :52606, data dir = cp -R of `rc1-round-5-seed-data`; in-process probes with the worktree venv; shared :52152 used only for one read-only agent-eval trial (Ollama lock held). Working log: `logs/rc1-vshard-6.md`; raw: `verifier/shard-6-raw/`.

| id | verdict | evidence (short) |
|---|---|---|
| R15-LIFECYCLE-024 | **refuted** | Backup half of the title still reproduces on the entry's own repro dir shape. The build marker (`data_cache` `meta.build`) was introduced at ca25a5ca (24 Sep); the 19-Sep build (7969d087) and v0.8.0 have no `meta` table. On such a dir `ensure_build` logs "cache written by an unversioned build - cleared", deletes the 38 cache rows and takes **no** `backups/` copy (it backs up only when a build row exists; control with `meta.build=0.7.9-prior` backs up). So the first upgrade from every shipped build is un-backed-up. The user_version half holds: all 7 DBs go 0 -> 1 on touch. Raw: `shard-6-raw/LIFECYCLE-024.txt`. |
| R15-CODE-AGENT-009 | holds | ast: `invoke_agent` 101 lines (entry ~400); phases `_dispatch_round` 193, `_consume_round` 155, `_prepare_run` 143, directly tested (test_runtime_phases 9, test_runtime_prepass 8); targeted pytest 87 passed. |
| R15-AGENT-007 | holds | Harness (run.py/grader.py/16 scenarios) present; Anthropic test streams `input:{}` + `input_json_delta` through the real SDK; Gemini SSE cassettes. Fresh wire case (text + zero-arg tool + nested-args tool) parses whole. Live ollama llama3.1:8b trial `disclosures-tcs` PASS (corporate_announcements TCS.NS); grader fails the same stream with symbol swapped / tool renamed / done removed. Anthropic/Gemini live pass stays operator-attended (D-B11-10). |
| R15-LIFECYCLE-026 | holds | `sample` 5 s: main thread 3875/3899 in `uv__io_poll`/kevent. Light-load soak (8 GETs / 60 s, screener warm armed): 2.65 s CPU over 217 s = 1.2%. |
| R15-DATA-071 | holds | Cold cache (tmp dir) fresh BSE-only scrips AMBIT, HAWAENG: BSE lane 7 / 24 bars `partial: true` with coverage_start; registry falls through to yfinance 236 / 233 bars, 1y complete. |
| R15-LEAD-013 | holds | sp500.json 503 names, BXP/NVR/UDR present, named delisted absent; fresh diff vs live Wikipedia constituents (27 Sep 16:37 IST): 0 missing, 0 extra; 180-day staleness test present. Adjacent below. |
| R15-DATA-079 | holds | `/quant/option/chain` NIFTY/BANKNIFTY/TCS/SBIN served from nse-fo-bhavcopy 2026-09-25; BANKNIFTY/TCS/SBIN cross-checked row-by-row against the NSE UDiFF F&O bhavcopy fetched directly: 0 mismatches on OI, chg-OI, volume, settle, close, underlying. |
| R15-UI-087 | holds | Fallback in ChatSidebar send path on PROVIDER_FAILURE_CODES before any model event, ordered by `providerOrder`, notice names both; start layout via PanelHost.applyStartLayout; palette options consumed in CommandPalette. Code + test presence only (vitest not run in the read-only worktree; GUI unexercised). |
| R15-CODE-PLATFORM-025 | holds | BLUEPRINT.md:249/:322 scope multi-window/pop-out to v1.0 roadmap; 1 window in tauri.conf.json, no WebviewWindowBuilder; no other doc claims multi-window. |
| R15-UI-085 | holds | No readable `text-charcoal-600/700/800` in src/plugins tsx (only `disabled:` variants); no CSS `color:` on those tokens; design-contrast.test.ts present. |
| R15-UI-091 | holds | `/indicators/suggested` 5m/15m/1h equity -> ema:9, ema:21, vwap; crypto 1d/4h -> ema:50, ema:200, vwap:week; ChartPanel seeds from it. Fresh: BTC/ETH default 1y EMA(200) populated; VWAP(week) resets to the bar typical price each Monday; RELIANCE.NS 5m ema:9/21 computed. |
| R15-DATA-115 | holds | `/history/AMAL.BO?range=1y` -> bse 255 bars (AMAL.NS -> nse_direct 29). Fresh: RELIANCE.BO/INFY.BO history, /quotes/AMAL.BO, batch quotes, /indicators/AMAL.BO -> bse; intraday/weekly/5y .BO -> yfinance .BO, never nse_direct. |

## Adjacent

- **medium, near R15-LEAD-013 (cf. R15-LEAD-044):** the sp500 screen serves S&P 500 member **PTC** as "PTC India Limited", INR, market cap 45.9e9, price 155.09 — a mixed-entity row (its peg_ratio 1.3113 is PTC Inc.'s seed value). The bare `PTC` row in `fundamentals_cache.db` was cross-written by a pre-LEAD-044 build (yfinance, 26 Sep 21:32 IST); the candidate serves it on a stale/snapshot run and nothing repairs it — the build-change clear covers `data_cache` only, and the boot seed-pack apply leaves it. Profiles screened under IN before 5dbc1813 keep such rows. The run's coverage also reads "spans INR, USD". Raw: `shard-6-raw/adjacent-sp500-PTC.txt`.

## Harness note

While this shard held `/tmp/vysted-r15-ollama.lock` (16:45 IST), the lock dir disappeared and rc1-vshard-7/rc1-vshard-8 Ollama calls ran at the same time (another holder's EXIT trap rmdir'd the shared dir). This only caused contention; the trial passed.
