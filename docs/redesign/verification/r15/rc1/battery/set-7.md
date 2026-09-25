# batch-3/W3-llm-adapters-and-errors (set-7)

Candidate sha 4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a. Own sidecar 127.0.0.1:52341 for the
live endpoint check; in-process python calls into `sidecar/services/` for the pure-function
adapters, using the candidate's own `.venv`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-004 | `sidecar/tests/test_llm_anthropic.py:242` `test_stream_chat_tool_use_carries_streamed_input` — the original repro used a real-SDK-plus-MockTransport script (`anth_proof.py`) that no longer exists (scratch, removed with the batch-3 worktree); this committed test exercises the identical mechanism (a `content_block_start` tool_use with `input:{}` followed by `input_json_delta` fragments). Not executed (no pytest run per task constraint). | Read the test body at HEAD: asserts the adapter's translated `tool_use` event carries the fully-accumulated input dict, not `{}`. | ci_pinned (test_llm_anthropic.py) |
| R15-AGENT-005 | In-process: `services.llm.native_search.native_search_available(provider, model, with_function_tools=...)` for groq/llama-3.3-70b-versatile, groq/compound, gemini-2.5-pro (with and without function tools), gemini-3-pro-preview. | `False` for Groq's plain model, `True` for `groq/compound`; `False` for Gemini 2.5-pro alongside function tools, `True` for Gemini 3 alongside function tools, `True` for Gemini 2.5-pro with no function tools (one-shot `google_search` grounding). All 5 match the certified per-model gating exactly. | holds |
| R15-AGENT-018 | In-process: `services.llm.tool_call_rescue.rescue_leaked_tool_call()` replayed on the original captured leaked JSON — a bare `write_note` object and a prose-plus-`screener_run` object, both against the offered-tools set; plus a fresh case with a name not offered. | Both leaked calls rescued into real `LLMToolUseEvent`s with the correct name/args (`write_note` scope=NVDA, `screener_run` criteria=[]); the not-offered name stayed `None` (never rescued). | holds |
| R15-UI-008 | Live `POST /llm/keys/validate` on the candidate's own sidecar (:52341) with a fake key, for `openrouter`, `gemini`, `xai`. | All three return `{"ok":false,"reason":"invalid","detail":"<Provider> rejected this key."}` — Gemini is classified `invalid`, never `unreachable`/transport-error (the original defect). | holds |
| R15-CODE-AGENT-003 | same live check as UI-008 (shared mechanism — the `validate_key()` classification path) | same | holds |
| R15-AGENT-027 | In-process: `services.errors.humanize()` replayed on 8 captured/fresh error bodies: OpenAI 429 credit, OpenAI/Groq/Anthropic context-overflow 400/413, Ollama connection-refused, Gemini/xAI 400 bad-key, OpenRouter 429 free-pool-busy (`upstream_provider_shared_pool`/`:free` marker). | All 8 map to the exact certified `code`: `insufficient_credit`, `context_overflow` (x3), `ollama_not_running`, `auth` (x2), `free_pool_busy`. | holds |

## Notes
- No regressions found in this set. No new defects found.
- AGENT-004's original scratch script (`anth_proof.py`) is gone (never committed); the
  committed `test_llm_anthropic.py` test covers the identical mechanism 1:1, so `ci_pinned`
  is the honest verdict rather than reconstructing a bespoke MockTransport repro from scratch.
