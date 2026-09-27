# Regression battery — set-49 (batch-11/W3-agent-eval)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Own sidecar on `:52345`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-007 | Live `scripts/agent_eval/run.py --lane ollama --model llama3.1:8b --k 1 --port 52345` (the same harness batch-11 used) against the running candidate sidecar, scenario `price-reliance` | First attempt (2 scenarios, concurrent with other probes hitting the same port) hit a transient `Connection refused` in vy.py's subprocess; traced in-process (same `_http()` code path, no concurrent traffic) it completed a full real agent turn — `market_overview` + `price_data` tool calls, real RELIANCE quote (₹1226.0), coherent answer, 107.4s. A clean single-scenario re-run of the unmodified harness passed: `price-reliance #0 81.7s PASS`, `pass_hat_1: 1.0`. The eval loop, grader and vy.py transport all function correctly end to end on this candidate; the first attempt's failure was a port-contention artifact of my own parallel probing, not reproducible in isolation. `test_agent_eval.py`, `test_llm_anthropic.py`, `test_llm_gemini.py`, `test_gemini_multiround.py` (cited by the batch-11 certification for the Anthropic/Gemini wire-shape half) are present at this sha; not re-run here (pytest suites are the heavy lane's). | holds |

COVERAGE: 1/1 ids raw.
