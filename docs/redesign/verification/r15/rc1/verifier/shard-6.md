# RC1 adversarial sample verifier, shard 6 (rc1-vshard-6)

Candidate `81fbfe910d472ecd154fa62e42d86bce213a697e` (`git rev-parse HEAD` in the read-only scratch worktree `rc1-4c6dfe8-fix-int`). Every command below ran against that checkout.

- **Own sidecar:** booted from the candidate source on :52606, data dir `scratchpad/rc1-data-rc1-vshard-6` (a copy of `rc1-seed-data`). Its sleep pid 89358 was killed at the end and :52606 is down.
- **Local model:** llama3.1:8b through Ollama, each call run under `/tmp/vysted-r15-ollama.lock`.
- **vy.py:** its port guard refuses non-GET calls outside 52100-52399. Agent runs on :52606 therefore used a direct `curl POST /agents/copilot/invoke` with the same body shape; no keyed provider and no spend.
- **Excluded:** nothing under `r15/rc1/` other than my own files and no VERDICTS was read.

## Verdicts

| id | verdict | one line |
|---|---|---|
| R15-RELEASE-006 | holds | Gate and builder read the same `spec.stale`. A new --add-data dir with a file newer than the binary flips the builder's `isStale` AND the gate. |
| R15-CODE-PLATFORM-026 | holds | The ensure scripts are 14-16 line runners over `SIDECAR_SPECS`. A 4th row added only in `sidecar-specs.mjs` is gated with no other edit ("sidecar binary missing"). |
| R15-CODE-PLATFORM-027 | holds | A copy under "dir with space %20", cwd /tmp, scans 372 files. A missing target exits 1, an injected `gap-[7px] p-9` exits 1 with 2 violations, and a tokens.css-only scan exits 1. |
| R15-CODE-AGENT-009 | holds | ast: `invoke_agent` is 101 lines. Phase tests pass (17). `_auto_publish_event` and `_prepare_run` option scrub can be unit-called directly without a fake provider. |
| R15-LIFECYCLE-024 | holds | All 7 DBs go from user_version 0 to 1. Fresh case: build marker `0.6.9-fresh` produces `backups/0.6.9-fresh` (every db, keystore 0600), and a portfolio.db at v5 is left at 5 with the newer-build warning. |
| R15-AGENT-007 | holds (caveat) | Fresh scenario (HDFCBANK) graded `[]` live on llama3.1:8b. The doctored `{}` input fails with "called without required ['symbol']". pass^k math checks out. Caveat: the live Anthropic/Gemini pass is operator-attended (D-B11-10), and no documented release gate runs the eval. |
| R15-LIFECYCLE-026 | holds | 5-min light soak (8 GETs/60 s): 5.80 s CPU = 1.9% including request work. A 5 s `sample` puts the loop thread at 3992/4001 in kevent. |
| R15-DATA-071 | **refuted (not_certified)** | The fall-through is fixed (SUNRAJDI 2y goes bse to yfinance, 207 bars). But with no complete lane the partial series is served and nothing surfaces the flag: the chart and price_data drop it. |
| R15-LEAD-013 | holds | The pack diffs to 0 missing / 0 extra against live Wikipedia (503 rows fetched today). `/screener/universe?id=sp500` has BXP/NVR/UDR/MRSH/FISV and no MMC/WBA/JNPR/HES/K/FI/IPG/HOLX. There is a 180-day staleness test. |
| R15-DATA-079 | holds | BANKNIFTY (312 contracts, 235 with OI) and HDFCBANK (62) as_of 2026-09-25. Four contracts match NSE's directly fetched UDiFF F&O bhavcopy field for field (OI, chg OI, vol, settle, close). The agent lane calls `option_chain`. |
| R15-UI-087 | holds | The fallback set equals the sidecar's classified provider-failure codes. Live bogus keys on openai/deepseek/openrouter emit `code=auth` (in the set). Palette options and start layout have consumers. Settings are global-scoped, so a named layout load cannot clobber startLayout. |
| R15-UI-085 | **refuted (not_certified)** | The tsx grep is clean. But dockview hidden-panel tab titles in inactive groups still render in charcoal-600 through `globals.css:355`: 2.08:1 on #101010, under the 3:1 floor. |
| R15-UI-091 | holds | Fresh combos: (15m, equity) gives ema:9, ema:21, vwap, rsi. (1h, crypto) and (5m, crypto) give ema:50, ema:200, vwap:week, rsi. BTC/USDT 1h serves EMA(50), EMA(200) and VWAP(week). HDFCBANK's week VWAP resets on the first bar of each week. The chart seeds on untouched panels. |
| R15-CODE-PLATFORM-023 | holds | Fresh 3-holding INR portfolio (INFY 0.5, HDFCBANK 0.3, ITC 0.2) vs ^NSEI, 257 aligned days. metrics.ts run under node matches an independent Python `statistics` reference to at most 4.4e-16 on vol, Sharpe, Sortino, maxDD, Calmar, VaR95, beta and the correlation matrix. |

## Refutations (not_certified)

### R15-DATA-071: the partial flag has no consumer
- **Claim left unfixed:** the title's "silently ... as if that were the year" and the repro's "The chart renders 8 points as if that were the year" still hold whenever no lane is complete.
- **Command:** `cd <worktree>/sidecar && ./.venv/bin/python3 scratchpad/vshard6/bse_cold.py`. It points `bse_provider._cache_dir` at an empty temp dir, then calls `bse_provider.get_history` and `provider_registry.get_history`. Checkout 81fbfe91.
- **Output excerpt:**
  ```
  bse direct cold 1y 1d: bars=8 partial=True coverage_start=2026-09-16
  provider yfinance failed for ohlcv, falling through: yfinance history rate-limited for 'TUTIALKA.BO': Too Many Requests
  registry: provider=bse bars=16 partial=True first=2026-09-03 last=2026-09-25
  SUNRAJDI.BO bse direct cold 6mo 1wk: bars=5 partial=True ... registry: provider=bse bars=6 partial=True
  ```
- **Where the flag stops:** `grep -rn '\.partial\|coverage_start' src` (non-test) hits only ScreenerPanel.tsx. ChartPanel.tsx:460-500 calls `toCandlestickData(series)` and sets provider and freshness only. price_data.py:81-90 returns bars and `bars_available` with no partial or coverage_start.
- **What does hold:** when a complete lane exists, the fall-through works live: `/history/SUNRAJDI.BO?range=2y` returns provider yfinance, 207 bars, partial false.

### R15-UI-085: charcoal-600 is still a readable foreground via CSS
- **Claim left unfixed:** readable labels in #484848 below the 3:1 floor.
- **Command:** `grep -n "charcoal-600" src/app/globals.css` gives `:355 --dv-inactivegroup-hiddenpanel-tab-color: var(--color-charcoal-600, #4a443a);`. In `node_modules/.pnpm/dockview-core@6.2.2/.../dist/styles/dockview.css`, the rule `.dv-groupview.dv-inactive-group > .dv-tabs-and-actions-container .dv-tabs-container > .dv-tab.dv-inactive-tab { color: var(--dv-inactivegroup-hiddenpanel-tab-color) }` applies it as tab text.
- **Contrast:** the tab strip background is charcoal-925 #101010, and the ratio is 2.08:1. The tertiary token charcoal-500 would give 5.51:1.
- **Why the test missed it:** design-contrast.test.ts only greps unprefixed tsx `text-charcoal-600/700` classes.
- **Scope:** these tabs are clickable (not disabled), so they are readable labels under the design's own floor.

## Adjacent (new, not refutations)
- **medium (near R15-UI-091):** indicator params other than `ema:N` and `vwap:week|session` are silently dropped. On the live sidecar, `rsi:7` returns 'RSI(14)', `sma:50` returns 'SMA(20)', and `ema:abc` returns 'EMA(20)'. Meanwhile `indicatorByKey('rsi:7')` labels the chip 'RSI 7' and host-actions accepts it as known.
- **low (near R15-DATA-079):** option_chain answers `expiry:'nearest'` with the raw "Invalid isoformat string: 'nearest'" and does not list the expiries. llama3.1:8b retried identically and gave up.

## Fresh-case evidence (holds)
- **RELEASE-006:** scratch `cp -Rp` of scripts/ with sidecar/ and binaries symlinked. The baseline `assertAllFresh` is OK. After adding `[join(ROOT,"extra"),"extra"]` to MAIN_ADD_DATA with a newer file: `builder isStale: true`, and `GATE THREW: STALE SIDECAR`.
- **CODE-PLATFORM-026:** a 4th SPECS row gives `rows: ...,vysted-fourth-sidecar` and `GATE THREW: sidecar binary missing`.
- **CODE-PLATFORM-027:** candidate run gives `design-token audit clean (372 files)` (exit 0). A copy under "dir with space %20" gives the same. `nope` exits 1 ("scanned 0 files ... refusing"). The injected fixture exits 1. A win32 simulation of the old ROOT gives `\C:\Users\Lokavya%20S\...`, and the new ROOT gives `C:\Users\Lokavya S\vysted-terminal`.
- **CODE-AGENT-009:**
  - Largest functions: `_dispatch_round` 182, `_consume_round` 155, `_prepare_run` 143, `invoke_agent` 101.
  - `pytest tests/test_runtime_phases.py tests/test_runtime_prepass.py` gives 17 passed.
  - A direct call with ok plus brief returns `publish_brief c1__autobrief`; not-ok and garbage return None.
  - `_prepare_run` leaves adapter opts `['temperature']` and drops `deep_research_backend` and `web_search_tier`.
- **LIFECYCLE-024:** `data dir backed up to .../backups/0.6.9-fresh before the upgrade`. The backup holds all 7 dbs, notes, workspaces, searxng and resolver_masters, with the keystore at 0o600. `schema_version: database is at version 5, newer than this build's 1; left untouched`. `migrateWorkspace` never downgrades a newer blob (workspace.ts:210-222).
- **AGENT-007:**
  - Trial: `price_data {symbol: HDFCBANK.NS, range: 1mo}` ok. The answer "₹735.6" matches `/history` last close 735.6.
  - Grades: `grade live: []`. Doctored: `["price_data called without required ['symbol']: {}", "no price_data call ..."]`.
  - `test_llm_anthropic.py:199-207` now feeds `input: {}` plus `input_json_delta` (the real wire shape).
- **LIFECYCLE-026:** ps TIME 0:13.86 at cycle 1 and 0:19.66 at the end (5 cycles of 60 s). The idle gaps between cycles were 0.05, 0.46 and 0.93 s of CPU. The main thread sat at 3992/4001 in `uv__io_poll`/kevent.
- **LEAD-013:** Wikipedia constituents table parsed to 503 rows, with `missing from pack: []` and `extra in pack: []`.
- **DATA-079:**
  - Route: BANKNIFTY 29-Sep 45000 PE has OI 131340, chg -38460, vol 4565, settle 0.55.
  - NSE `BhavCopy_NSE_FO_0_0_0_20260925_F_0000.csv.zip`: identical. The same holds for HDFCBANK 740 CE (OI 20125300, chg -539500) and 560 PE.
- **UI-087:**
  - `PROVIDER_FAILURE_CODES` (streaming.ts:69-76) is a subset of the codes errors.py emits.
  - Live bogus keys give openai/deepseek/openrouter `code=auth`.
  - The settings slice is `scope: "global"` (workspace.ts:485), so `loadWorkspace` does not restore it.
  - Residual: `provider_idle` (a hung provider, 180 s) is not a fallback trigger. This is a design choice per the streaming.ts comment, and not filed.
- **UI-091:** live `/indicators/suggested` and `/indicators` outputs are as stated in the verdict table. ChartPanel.tsx:422-448 seeds while the panel is untouched.
- **CODE-PLATFORM-023:** the fresh-case numbers are tabulated in the working log. No split artifacts: the largest daily moves are real events, e.g. ITC -9.7% on 2026-01-01.
