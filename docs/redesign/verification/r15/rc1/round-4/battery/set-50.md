# batch-11/W3-agent-eval (rc1-battery-14, set-50)

Candidate sha 1006c6da694ede5776c3dabbd27b305aeb56b5ad. Sidecar :52354.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-007 | (1) `pytest sidecar/tests/test_agent_eval.py` (harness+grader unit mechanism, no live model). (2) Scoped live re-run: `scripts/agent_eval/run.py --lane ollama --model llama3.1:8b --k 1 --max-minutes 8 --only price-aapl,ask-chart-indicator,missing-param-portfolio,sec-filings-aapl` against the candidate sidecar (see rationale for the k=1/4-scenario scope in `logs/rc1-battery-14.md` — the original cert was a 45-min k=3 x 16-scenario run, out of this shard's time budget). | (1) 19 passed. (2) price-aapl PASS (68.9s), ask-chart-indicator PASS (53.6s), missing-param-portfolio FAIL — "forbidden tool called: portfolio_add_position" (model guessed/supplied a cost basis instead of asking, so the not-yielded-when-null gate never triggers — matches the cert's named failing set exactly), sec-filings-aapl FAIL — model sent `'10-K, 10-Q'` as one comma-joined string instead of the enum, correctly rejected by the tool-arg validator (also in the cert's named failing set). pass_hat_1 = 0.5 (2/4), all four failure/pass outcomes land on the SAME scenarios and for the SAME model-quality reasons the batch-11 certification named. | holds (harness mechanism intact; the same known ollama model-quality failures reproduce on the same scenarios — no new mechanism break) |

COVERAGE: 1/1 ids raw in this set.
