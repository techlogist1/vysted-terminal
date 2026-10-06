# rc1-battery-6 working log

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98. Sidecar :52346 (own data copy
rc1-round-5-data-rc1-battery-6), sleep-wrapper pid 39658, worker pid 39661.

## set-14 (batch-4/W5-panels-screener) — done
9/9 hold. See battery/set-14.md.

## set-47 (batch-11/W1-scripts-build) — done
5/5 hold (live node script runs, no full builds). See battery/set-47.md.

## set-51 (batch-11/W5-data-reference) — done
1/1 holds (sp500.json direct read at candidate sha). See battery/set-51.md.

## set-64 (batch-17/W1-one) — done
1/1 holds (in-process agent_runtime._release_point/_units repro). See battery/set-64.md.

## Summary
16/16 entries hold. 0 regressed, 0 ci_pinned-only-blocked, 0 needs_gui, 0 blocked_env.
findings/rc1-battery-6.json is [] (no regressions/new defects found).

COVERAGE: 16/16 ids raw across all 4 sets; no raw: none.
