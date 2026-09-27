# rc1-vshard-2 working log (gate round 4)
- 2026-09-26T23:40:14Z candidate worktree HEAD = 68d5573aff9a579af084dcbb124843f2aecff6e8 (checked)
- 2026-09-26T23:40:14Z own sidecar booted from worktree source on :52602, data dir scratchpad/rc1-round-4-data-rc1-vshard-2 (copy of seed), sleep pid 33988, /health ok v0.8.0
- 2026-09-26T23:40:14Z observed at boot: Yahoo v7 quote + getcrumb returning 429 (shared IP, many sidecars) -- upstream condition to account for in data repros
- 2026-09-27T00:06:53Z verdicts recorded for 20 ids (raw per id in verifier/shard-2-raw/); refuted: DATA-063, DATA-015, LIFECYCLE-020, LEAD-014, CODE-FRONTEND-015, UI-021; 14 hold
- 2026-09-27T00:06:53Z LIFECYCLE-020 live: POST /screener/run nifty50 curl-timed out at 110 s under Yahoo 429 (upstream throttle, not a 5xx); the verdict rests on the warm path recording into the shared circuit (code + live log), not on that timeout
- 2026-09-27T00:06:53Z findings/rc1-vshard-2.json written (6 not-certified/regression + 3 low new_defect adjacents); report verifier/shard-2.md written
- 2026-09-27T00:07:00Z sidecar stopped (kill 33988, the sleep pid only); :52602 no longer answers
