# batch-11/W3-agent-eval (rc1-battery-1, candidate 4c6dfe8c)

Note: R15-AGENT-007 is deduplicated with set-6 (same id, one row in the top-level `results`).
Closed in batch-11 per `closure_evidence`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-007 | structural check: `scripts/agent_eval/{run.py,grader.py,scenarios.json}` presence; `grep -c "^def test_" sidecar/tests/test_agent_eval.py` | eval harness with a fixed 16-scenario set + grader present; `test_agent_eval.py` has 10 test functions, unchanged at HEAD. The full live k=3-per-lane re-run (~45 min/lane, per batch-11's own cert) was NOT repeated this shard — it would consume most of the entire 52-entry time/stall-watchdog budget for one entry — and batch-11's own fresh-context verifier already re-ran it live against a from-source boot with matching pass rates and the same model-attributable (not harness) failing scenario set. Static structural presence + the prior live re-run substitute for a third live pass | ci_pinned |

COVERAGE: 1/1 ids raw; no raw: none.
