# set-50: batch-11/W3-agent-eval

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-007 | repo search for runner/grader/pass^k (the entry's design repro) + deterministic grader run in candidate venv; live k=3 harness run not repeated | scripts/agent_eval/{run.py,grader.py,scenarios.json} exist; 16 scenarios; grade(good)=[]; grade with tool input {} fails 'price_data called without required [symbol]'; pass_hat_k computes (0.5 on a 2-scenario sample); test_llm_anthropic.py:207 input_json_delta wire-shape fixture exists | holds |

COVERAGE: 1/1 ids raw (set-50); no raw: none
