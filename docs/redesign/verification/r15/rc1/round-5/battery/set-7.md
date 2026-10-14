# Set 7 — batch-3/W3-llm-adapters-and-errors (regression battery shard 14)

Sidecar: candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98, port 52354.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-004 | pinned `tests/test_llm_anthropic.py::test_stream_chat_tool_use_carries_streamed_input` (real anthropic SDK + `httpx.MockTransport` replaying `content_block_start input:{}` → `input_json_delta` fragments → `content_block_stop`, the register's own repro shape) | PASSED. `tool_use` event carries `input={"symbol":"RELIANCE.NS"}` (accumulated from `content_block_stop`, not the empty `content_block_start`). Source: `_translate_event` in `services/llm/anthropic.py` now branches on `content_block_stop` for `tool_use`, not `content_block_start`. | holds |
| R15-AGENT-005 | in-process `services.llm.native_search.native_search_available` for groq `llama-3.3-70b-versatile`, groq `compound`, gemini `gemini-2.5-pro`, gemini `gemini-3-pro` (code-level check — no funded Groq/Gemini key this shard, matching the batch's own method) | `llama-3.3-70b-versatile`: False (with and without function tools). `compound`: True (both). `gemini-2.5-pro`: False with function tools, True one-shot (no function tools) — keeps `google_search` for the one-shot case. `gemini-3-pro`: True (both). | holds |
| R15-AGENT-018 | pinned `tests/test_llm_ollama.py::test_leaked_text_tool_call_is_rescued` + `::test_leaked_json_for_a_tool_not_offered_stays_text` (the register's own leaked `write_note` JSON + not-offered-name repro) | Both PASSED. Leaked JSON for an offered tool is rescued into a real `tool_use` with a `leaked_…` id; JSON naming a tool not in the offered set stays text. | holds |
| R15-UI-008 / R15-CODE-AGENT-003 | live `POST /llm/keys/validate` with a fake key for `openrouter`, `gemini`, `xai` | All three: `{"ok":false,"reason":"invalid",...}` — Gemini no longer reports a transport error, matches cert. Positive control (real keys validate true) not independently re-run this shard — no safe in-scope path to read a real key without risking printing it; the negative control is the entry's actual defect surface and matches exactly. | holds |

COVERAGE: 4/4 ids raw; no raw: none.
