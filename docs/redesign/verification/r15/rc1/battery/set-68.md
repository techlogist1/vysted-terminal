# batch-17/W1-w1

Candidate `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`. Own sidecar `:52346`. Raw output: `raw/set-68/`.

Per the LEAD NOTE for this run: R15-LEAD-030 is adjudicated (`DECISIONS_FOR_OPERATOR.md` §4.9),
`status: blocked_tier4`, fresh verifier concurred at batch-23 (`LEAD-030-CONCURRENCE.md`), the
stop rule fired at its 8th failure (batch-22), and it gets **no further fix round**. This shard
does not attempt to re-litigate or re-fabricate it live — no local-model call was made for this
entry, so the shared Ollama lock was never needed here. The only check performed is a source-level
confirmation that nothing has silently changed since the batch-23/24 adjudication.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-LEAD-030 | read `DECISIONS_FOR_OPERATOR.md` §4.9 (the adjudicated disposition); grep `sidecar/services/agent_runtime.py` `_judge_clause` for the errored-gate the §4.9 "bounded ninth fix" (explicitly "not built this run") would have removed | the candidate's own HEAD commit message (`4c6dfe8c`) states "LEAD-035 blocked_tier4 under the three-failure rule... gate round 2 in flight", confirming this candidate IS the one built for this exact adjudication; `_judge_clause`'s docstring still describes rule 1 firing "when every call of the turn failed" (i.e. still gated on an errored call, matching §4.9's note that the errored-gate removal was never built) — no drift from the adjudicated state, nothing silently fixed or silently regressed | holds |

Summary: 1/1 holds (adjudicated state confirmed unchanged via source, no fix round attempted per LEAD NOTE). No new instance of "a local-model figure with no ok tool call behind it" was independently sought or found this shard (none of this shard's other sets exercised the agent-chat live-model path); had one been found, it would be logged as a note under this existing blocked_tier4 entry rather than a new fix round, per the LEAD NOTE.

COVERAGE: 1/1 ids raw.
