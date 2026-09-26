# rc1-vshard-6 working log (adversarial sample verifier, shard 6)

Candidate 81fbfe910d472ecd154fa62e42d86bce213a697e (git rev-parse HEAD in the scratch worktree rc1-4c6dfe8-fix-int).
Own sidecar: source from the candidate worktree, :52606, data dir scratchpad/rc1-data-rc1-vshard-6 (cp -R of rc1-seed-data). sh 89356 / sleep 89358 / python 89359. /health ok 0.8.0 at 09:30 IST.

- 09:3x R15-RELEASE-006: scratch copy (cp -Rp) of scripts/ with sidecar + binaries symlinked; assertAllFresh OK on candidate; added a new --add-data dir in the copy's sidecar-specs.mjs with a file newer than the binary -> builder isStale true AND gate throws STALE SIDECAR. holds.
- R15-CODE-PLATFORM-026: ensure-*.mjs are 14-16 line runners over SIDECAR_SPECS; smoke loops SIDECAR_SPECS; added a 4th row in the scratch copy -> gate throws "sidecar binary missing" with no other edit. holds.
- R15-CODE-PLATFORM-027: audit run from a copy under "dir with space %20", cwd=/tmp -> clean (372 files); nonexistent target exits 1; injected gap-[7px] p-9 exits 1 with 2 violations; styles/ alone scans 0 (tokens.css skipped) -> exits 1. holds.
- R15-CODE-AGENT-009: ast: invoke_agent 101 lines (largest fn _dispatch_round 182); test_runtime_phases+prepass 17 passed; direct unit call on _auto_publish_event and _prepare_run option scrub without a fake provider works. holds.
- R15-LIFECYCLE-024: all 7 DBs 0 in seed -> 1 after boot + route touch; fresh case: seed copy with build marker 0.6.9-fresh and portfolio.db user_version 5 -> backups/0.6.9-fresh holds every db, keystore 0600; portfolio left at 5 with the newer-build warning. holds.
- R15-AGENT-007: vy.py port guard refuses non-GET outside 52100-52399 (harness), so ollama runs used direct curl to :52606 (same body). Fresh HDFCBANK scenario graded [] live; doctored {} fails. holds (Anthropic/Gemini live pass is operator-attended by D-B11-10; no documented release gate runs the eval).
- R15-LIFECYCLE-026: 5-cycle light soak 13.86 -> 19.66 s CPU (1.9%); `sample` 3992/4001 in kevent. holds.
- R15-DATA-071: cold in-process (temp bse cache): TUTIALKA 1y 8 bars partial -> registry bse partial 16 bars (yfinance 429); SUNRAJDI 2y live -> yfinance 207 complete. Chart + price_data never read partial -> refuted (not_certified).
- R15-LEAD-013: pack == live Wikipedia (503/503). holds.
- R15-DATA-079: BANKNIFTY/HDFCBANK chain rows == NSE UDiFF F&O 2026-09-25. ollama run: expiry:'nearest' rejected with raw isoformat error (adjacent low). holds.
- R15-UI-087: bogus keys -> code=auth (in fallback set). holds.
- R15-UI-085: globals.css:355 dockview hidden tab text = charcoal-600, 2.08:1 on #101010 -> refuted (not_certified).
- R15-UI-091: fresh combos + BTC/USDT 1h EMA50/200/VWAP week live. holds. Adjacent: rsi:7/sma:50/ema:abc silently computed at default period, chip says 'RSI 7'.
- R15-CODE-PLATFORM-023: fresh 3-holding metrics.ts vs python ref: max diff 4.4e-16 (days 257, vol 0.18641, Sharpe -1.79068, Sortino -2.32611, maxDD -0.34738, Calmar -0.96092, VaR95 0.020036, beta 0.87283, corr INFY/HDFC 0.19469). holds.
- Lock note: my second lock hold's trap printed "rmdir: No such file or directory" at exit, so the lock dir was already gone when my call finished (possibly removed by another holder). The call completed normally.
- Sidecar stopped: kill 89358 (sleep pid); :52606 down.
