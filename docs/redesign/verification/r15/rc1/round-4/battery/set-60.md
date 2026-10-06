# batch-12/W5-agent-runtime (rc1-battery-21, set-60)

Candidate sha 1006c6da694ede5776c3dabbd27b305aeb56b5ad. Sidecar :52361.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-092 | Live delegate runs through `POST /agents/copilot/runs` (llama3.1:8b via the local-model lock), same `write_note` prompt as the cert: (a) `budget.maxTokens=1000`; (b) default budget control | (a) run `59dd1ebe...`: `status:"error"`, `detail:"token ceiling 1000 reached (7611 used)"`, `host_actions: []` — the undispatched `write_note` from the halted round is NOT persisted. (b) control run `343dcc13...`: `status:"done"`, `host_actions: [{name:"write_note", input:{...}}]` — a normally-completed round still dispatches, so the fix causes no regression. Matches the batch-12 certification exactly. | holds |

COVERAGE: 1/1 ids raw.
