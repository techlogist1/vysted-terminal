# batch-9/W1-agent-runtime (rc1-battery-7)

Candidate `4c6dfe8c`. Own sidecar on `:52347`. 5 certified entries re-run (authoritative
entry list per `battery/INDEX.json` / batch-9 `PLAN.md` — the task's copied entry list for
this set (`AGENT-046, AGENT-091, AGENT-094, AGENT-096, AGENT-098`) does not match any real
batch-9 entry: AGENT-091 is a real, but `open` (not `fixed`/certified) register entry, and
AGENT-094/096/098 do not exist in the register at all — treated as a harness transcription
error, logged in notes, worked from the authoritative batch-9 W1 roster instead).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-046 | `vy.py invoke copilot "Research NVDA briefly." --provider ollama --model llama3.1:8b --autonomy auto` | live tool_call_id minted: `call_d3e57f53da70430e969eca0e3137e1c5` (not `''`); the auto-brief id is `call_d3e57f…__autobrief`, unique per run — matches cert exactly | holds |
| R15-CODE-AGENT-008 | same run: `publish_brief` tool_use payload | `structured` keys exactly `{price, fundamentals, derived, news, filings}`, each with real decoded provider data (NVDA fundamentals, price) — matches cert's payload-variant decode shape | holds |
| R15-RESEARCH-027 | same run: research engine timing | engine ran ~7s wall (44.8s→51.8s markers) with "filings timed out after 6s — dropped" / "pulled 3/4 data sources" — same 6s-timeboxed-leg mechanism the cert describes (news timed out in the cert's run; filings timed out in this fresh case), well under the 15s FR-070 target | holds |
| R15-CODE-AGENT-005 | `POST /llm/chat` `{provider:openrouter, model:inclusionai/ling-3.0-flash-vl:free, api_key:<fake>, options:{depth:"deep", brandNewComposerControl:true}}` | SSE `error` frame: `code:"auth"`, "The OpenRouter API key was rejected" (401 "User not found") — no `TypeError` from the unknown `depth`/`brandNewComposerControl` keys | holds |
| R15-LIFECYCLE-025 | DB-inserted `custom:macro-hawk-r7` with `tools=["price_data","macro","news"]`; `GET /custom-agents` then `PUT` with the same tools | GET returns tools unchanged (`macro` present, unresolved); PUT returns **200** with tools `["price_data","macro_series","news"]` — `macro` resolved, no 422 | holds |

Raw output: `battery/raw/set-35/*`.
