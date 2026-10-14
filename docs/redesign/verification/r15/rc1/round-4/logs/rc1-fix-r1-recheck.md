# rc1-fix-r1-recheck working log (gate round 4, fix round 1 recheck)

- 2026-09-26T23:34:29Z candidate worktree HEAD = 68d5573aff9a579af084dcbb124843f2aecff6e8 (checked). No prior attempt of this role found.
- Own sidecar :52336 from the candidate worktree source, data dir scratchpad/rc1-round-4-data-rc1-fix-r1-recheck (copy of the round-4 seed), sleep pid 30720 / python pid 30721. Log: logs/rc1-fix-r1-recheck-sidecar.log. /health ok 0.8.0.
- failure-inducer:1/:2 exact repros re-run live: fix-r1/recheck/failure-inducer-live.txt (all 404 not_found).
- fresh variants (other malformed chars on fundamentals subroutes, unknown plausible US/BSE symbols on all four subroutes): fix-r1/recheck/failure-inducer-fresh.txt (all 404).
- controls (real tickers, a real no-coverage ratings symbol, index, dashed, ampersand): fix-r1/recheck/failure-inducer-controls.txt (200). EURUSD=X 404 is pre-existing (.NS appended under the IN session; same 404 on the shared :52152) and outside these entries -> filed as a low.
- battery-14:1 resolver: fix-r1/recheck/battery-14-resolve.txt; fresh same-class collisions found by scanning former_names.json vs current names (Bajaj Auto, Gujarat Fluorochemicals, Kirloskar Oil Engines, Max India, Sundaram Clayton, Tata Motors) all resolve to the current-name holder; former-name-only queries (Iifl Wealth Management, Birla 3M) still resolve.
- 2026-09-26T23:34:29Z Ollama lock acquired; scenarios:1 exact repro running (scen1-msft-ask-local.jsonl).
- scenarios:1 runs: MSFT local t1 (the model called publish_brief itself, staged notice fired), MSFT local t2 (research + autobrief, staged notice fired, the model said "proposed"), INFY hosted ask (autobrief only, notice fired, "proposed"), Kirloskar hosted ask ("proposed"), TCS hosted auto control (no staged notice; "did not confirm the publish" read-back unchanged). Hosted spend under $0.02 total, logged by vy.py.
- battery-14:1 exact local KPIT run: resolved to KPITTECH; the model's text over-claimed "at the top of the cockpit" while the staged notice fired -> residual low rc1-fix-r1-recheck:2.
- Each Ollama call ran under /tmp/vysted-r15-ollama.lock, released by trap (3 holds, no lock_timeout).
- 2026-09-26T23:39:02Z own sidecar stopped (kill of sleep pid 30720 only). RECHECK.md written: 4/4 fixed.
