# rc1-battery-6 working log

Role: REGRESSION BATTERY shard 6. Candidate 4097dac4.
Own sidecar: 127.0.0.1:52346, sleep pid 19283, data dir rc1-data-rc1-battery-6 (from rc1-seed-data).
Shared stack: :52152 (candidate source, read-only) + :52153 openbb-mcp + :52154 sec-edgar-mcp.

## Sets
batch-8: W1(set-28) W2(set-29) W3(set-30) W4(set-31) W5(set-32) - entries derived from stage-c/batch-8/VERDICTS.md (per-entry evidence section).
unplanned-1..13 (set-46..58) - entries given explicitly by task.


## Final status

All 18 assigned sets complete (28,29,30,31,32,46,47,48,49,50,51,52,53,54,55,56,57,58).
Sidecar stopped: killed sleep pid 19283, worker pid 19284 confirmed exited.
60 entries verdicted: 0 regressed, 1 low-severity new_defect logged (R15-DOCS-017 partial doc gap).
Findings: docs/redesign/verification/r15/rc1/findings/rc1-battery-6.json
