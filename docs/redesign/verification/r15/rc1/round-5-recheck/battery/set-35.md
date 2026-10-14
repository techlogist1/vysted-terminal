# set-35 (rc1-battery-7) — batch-9/W1-agent-runtime

Candidate: `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. Live-tested against this shard's
own sidecar (`:52347`); the two Ollama-model entries used the shared local-model
lock (mkdir-based, held for the duration, released via a trap on exit/kill).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-046 | `vy.py invoke copilot "Set the chart symbol to AAPL." --provider ollama --model llama3.1:8b --autonomy auto` | `tool_call_id` minted (`call_b45e32...`, non-empty), `tool_result ok:true`, assistant confirms directly ("Your chart for AAPL is now displayed") — no "dispatched_unconfirmed"/"pending confirmation" narration | holds |
| R15-CODE-AGENT-008 | `vy.py invoke copilot "Research NVDA briefly." --provider ollama --model llama3.1:8b --autonomy auto` | research ran to completion (search/tool/synthesize steps, "6 web source(s)", "pulled 4/4 data sources"), auto-published `publish_brief` (`__autobrief` id) with structured `query/symbol/mode/depth/execution` payload, final text states only real figures | holds |
| R15-CODE-AGENT-005 | `curl -X POST /llm/chat` with `provider:openrouter`, a fake `api_key`, and an unscrubbed composer option key (`options.depth`) | clean 401 auth-error SSE frame, no TypeError from the unhandled kwarg | holds |
| R15-LIFECYCLE-025 | direct sqlite insert of a legacy `custom:macro-hawk` row (`tools_json` still carrying the pre-rename `"macro"` id, bypassing today's API validator, matching the register's own repro method) + `GET`/`PUT /custom-agents/custom:macro-hawk` + in-process `schemas.openai_tools(...)` | GET returns `tools_json` unchanged; `schemas.openai_tools` resolves `"macro"` -> `"macro_series"`; PUT now returns 200 (not the pre-fix 422), persisting the resolved id — matches batch-9/VERDICTS.md's own certification exactly | holds |

Port-squat note: this shard's assigned port 52347 was found already bound by a
stale orphaned earlier-round process (PID 47234, cwd `rc1-round-5-cand/sidecar`,
started 14:48, PPID 1 — not round-5-recheck) before this role's own sidecar boot.
Verified via `lsof`+`ps`, killed it, rebooted this shard's own sidecar (sleep pid
69255) on the correct recheck candidate + data dir; `/health` reconfirmed ok. All
probes above ran against the confirmed-correct sidecar (CODE-AGENT-005's first
probe, taken against the stray process, was re-run and produced the identical
result).

Raw output for every id: `battery/raw/set-35/<id>.txt`.
