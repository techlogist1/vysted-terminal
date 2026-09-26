# rc1-battery-6 working log (fresh run, candidate 4c6dfe8c)

NOTE: found stale set-30..34.md / findings from a PRIOR run at a different candidate
(4097dac4) covering DIFFERENT entries (batch-8 W3/W4/W5 + batch-9 W1/W2 under the
rc1-battery-6/7 labels). Those do not match this task's assigned entries or candidate
sha, so they are treated as unrelated leftovers, not a restart of this exact role, and
are being overwritten per this run's explicit set/entry list.

Candidate: 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2
Own sidecar: 127.0.0.1:52346, sleep pid 8339, data dir rc1-data-rc1-battery-6 (from rc1-seed-data)
Shared stack: :52152 (candidate source, read-only) + :52153 openbb-mcp + :52154 sec-edgar-mcp

## Sets assigned
- batch-8/W1-sidecar-lifecycle-transport -> set-30.md (7 entries)
- batch-8/W2-provider-readiness-host-actions -> set-31.md (9 entries)
- batch-8/W3-data-error-honesty -> set-32.md (6 entries)
- batch-8/W4-resolver-exchange-lanes -> set-33.md (11 entries)
- batch-8/W5-agent-runtime-research -> set-34.md (6 entries; 3 of the 6 IDs given,
  R15-RESEARCH-068/070/072, do not exist anywhere in the register or verification tree
  -- grep confirmed zero hits repo-wide; register's RESEARCH ids stop at -042. Recorded
  as blocked_env (not a product defect; a task-data issue) rather than invented.)
- batch-17/W1-w1 -> set-68.md (1 entry: R15-LEAD-030, governed by LEAD NOTE: blocked_tier4,
  no fix round, only log a new instance under the existing entry if found)


## Final status

All 6 assigned sets complete (30, 31, 32, 33, 34, 68) — 40 ids total.
Sidecar stopped: killed sleep pid 8339.

Tally: 36 holds, 1 needs_gui (R15-LIFECYCLE-001, register status), 3 blocked_env
(R15-RESEARCH-068/070/072 — do not exist in the register or verification tree; a
task-data issue, not a candidate defect). 0 regressed, 0 ci_pinned.

Findings: docs/redesign/verification/r15/rc1/findings/rc1-battery-6.json — [] (no
regressions, no new defects; every checked entry matched its documented register
state exactly, several with stronger evidence than the original certification, e.g.
DATA-090's quarantine+`.bak` serve observed live, DATA-043's mixed-currency top-K
page observed live matching the pinned acceptance test verbatim).

R15-LEAD-030 (set-68) handled per the LEAD NOTE: adjudicated blocked_tier4, no fix
round attempted, no local-model call made (Ollama lock never needed for this shard).

COVERAGE (overall): 40/40 ids raw (37 real repros with raw probe output + 3
non-existence confirmations for RESEARCH-068/070/072, each with its own raw file).

(worker pid 8342 outlived the sleep-pid stdin-close by a few seconds — a plain
`kill` finished it; confirmed gone via `ps -p 8342`.)
