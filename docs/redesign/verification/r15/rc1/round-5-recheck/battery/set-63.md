# batch-14/W1-agent-runtime-ratio-guard-clas (rc1-battery-1, round-5-recheck)

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. Own sidecar `127.0.0.1:52341`,
data dir `rc1-round-5-recheck-data-rc1-battery-1`. Raw output: `raw/set-63/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-CODE-AGENT-033 | (1) Live `vy.py invoke copilot "Call the option_chain tool for AAPL with expiry nearest." --provider ollama --model llama3.1:8b` — confirms the runtime emits a `tool_result` frame immediately after `tool_use` in the live SSE stream (`[44.5s] tool_use option_chain` -> `[45.9s] tool_result ... ok:true`). (2) In-process direct call `services.agent_tools.quant_tools._option_chain({"symbol":"AAPL","expiry":"nearest"})` — reproduces the tool-level bug the cert's original repro used. (3) `scripts/agent_eval/grader.grade()` called directly against the reconstructed event shape (`tool_use option_chain(expiry='nearest')` -> `tool_result ok=false error="invalid argument: Invalid isoformat string: 'nearest'"`). | This run's live llama3.1:8b call omitted the `expiry` arg entirely (small-model non-determinism — it called `option_chain({"symbol":"AAPL"})` and got `ok:true`), so it did not itself reproduce the exact error path, but it did confirm the tool_result-immediately-after-tool_use framing the fix depends on. The direct in-process call confirms `option_chain` still errors identically to the cert's original repro: `ok: False, error: "invalid argument: Invalid isoformat string: 'nearest'"`. Feeding that exact event pair into `grader.grade()` reproduces the cert's finding verbatim: `["option_chain errored: invalid argument: Invalid isoformat string: 'nearest'", ...]` — a fail. Controls: an `ok=true` result grades clean (no "errored" entry); an errored call followed by an `ok` retry of the same tool also grades clean (no "errored" entry, matching "a tool whose LAST result errored failed the trial") — both match the cert's stated controls. | holds |

Summary: 1 holds, 0 ci_pinned, 0 regressions. `test_runtime_phases`/`test_agent_eval`/`test_mcp_server` (the cert's pinned suite) not re-run here — owned by the heavy/vitest+pytest lane; the grader's OWN logic and the underlying tool bug were re-proven live/in-process per this shard's mandate (never run vitest/pytest suites).

COVERAGE: 1/1 ids raw; no raw: none.
