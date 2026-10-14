# batch-6/W2-delegate-runs-runtime

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-014 | In-process, real `TOOL_SCHEMAS` + `OpenAIProvider._repair_tool_args`, `oneshot.complete_with_usage` mocked to return controlled reply text (same approach as batch-6's `b6v_repair.py`) | 8 tools with no required keys, all 8 would have leaked a full schema echo pre-fix; post-fix 0 of 8 leak; a fenced-JSON echo and a prose-wrapped echo are also rejected (`None`); legit args (`{"symbols":["AAPL"]}`) still pass through | holds |

COVERAGE: 1/1 ids raw; no raw: none.
