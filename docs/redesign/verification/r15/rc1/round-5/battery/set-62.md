# batch-14/W1-agent-runtime — rc1-battery-4 (round 5)

Candidate: 9bc600ece2ce6343a6aa48f130d7620b1466bb98. Sidecar :52344.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-AGENT-033 | (a) direct `GET /quant/option/chain/AAPL?expiry=nearest` control probe; (b) in-process `grader.grade()` probe (candidate `.venv`, `scripts/agent_eval/grader.py`) with synthetic tool_use/tool_result event streams | (a) 422 `date_from_datetime_parsing`, same shape as the original repro's underlying error. (b) errored-tool-result case includes `"option_chain errored: invalid argument: Invalid isoformat string: 'nearest'"` in the failures list (correctly fails the trial); a later-ok retry of the same tool omits the "errored:" failure (recovers); a legacy stream with no `tool_result` frames also omits it (grades as before) — the exact three controls the batch-14 verifier used | holds |

COVERAGE: 1/1 ids raw; no raw: none.
