# rc1-datapack — gate round 5 log

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98` confirmed at
`.../scratchpad/rc1-round-5-cand` before starting.

1. Copy tree `.../scratchpad/rc1-round-5-pack` created with `scripts/r15/collect_battery.py`
   + `docs/redesign/verification/r15/battery/manifest.json`, both copied from the candidate
   worktree (never edited it).
2. Own data dir `.../scratchpad/rc1-round-5-data-datapack` = `cp -R` of
   `rc1-round-5-seed-data` (keyless isolated-profile snapshot).
3. Own sidecar booted from the candidate worktree's `sidecar/` source, port 52313, detached
   (`sleep 86400 | .venv/bin/python3 main.py --host 127.0.0.1 --port 52313 --data-dir <data>`),
   sleep pid 18783. `/health` ok within 5s.
4. Collector run from the copy tree: `python3 scripts/r15/collect_battery.py --port 52313
   --force`, detached, polled over ~12 minutes of wall time (multiple `run_in_background`
   sleep + tail cycles). All 24 manifest names collected; Yahoo circuit breaker opened
   mid-run and rate-limited a handful of `fundamentals`/`ratings` calls (429) — recorded as
   environmental, not filed as product findings (see DATAPACK.md).
5. Copied the 24 output JSONs to
   `docs/redesign/verification/r15/rc1/round-5/battery/collected/` (never touched the census
   baseline dir).
6. Re-diffed the battery-relevant fixed register entries (DATA-053, DATA-055, DATA-008,
   LEAD-004, LEAD-051, DATA-003) against the fresh collected JSONs, plus an automated scan
   of every census `match`-status field across all 24 names (148 string-valued fields with a
   numeric/identifier token) looking for a match→blank/wrong flip. Zero regressions found;
   all apparent numeric drift was as-of skew (market cap / TTM revenue moving with price and
   filings) or the 429 noise from step 4.
7. Wrote `DATAPACK.md` + `datapack.json` under `r15/rc1/round-5/`.
8. Stopped own sidecar: `kill 18783` (sleep pid) — watchdog exited the worker cleanly.

No findings filed (findings/rc1-datapack.json = `[]`).
