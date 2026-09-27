# Set — batch-17/W1-one-writer-set (rc1-battery-6)

Candidate: `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Own sidecar `:52346` (seed-data copy
`rc1-round-4-data-rc1-battery-6`), reused for the whole shard.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-031 | Pinned test `tests/test_tool_call_rescue.py` (register's exact llama3.1:8b sify-1 raw-output shape is what this module's dedicated regression test reproduces; two of its cases are named for this id directly, `test_tool_call_rescue.py:81,98`). Code trace: `services/llm/tool_call_rescue.py` now owns held-chunk buffering + marker detection + replay as one unit, replacing the ad hoc splice previously in `_guard_ratio_claims`. | 8/8 passed, including the two R15-LEAD-031-named cases. | ci_pinned (test_tool_call_rescue.py) |

Raw files: `battery/raw/set-68/R15-LEAD-031.txt`.

COVERAGE: 1/1 ids raw; no raw: none.
