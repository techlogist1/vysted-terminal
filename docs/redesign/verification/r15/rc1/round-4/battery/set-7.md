# batch-3/W3-llm-adapters-and-errors

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`, sidecar `127.0.0.1:52353`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-004 | In-process real `anthropic` SDK + `httpx.MockTransport` replaying documented tool-use SSE (content_block_start input:{} -> input_json_delta fragments -> content_block_stop), same shape as the original `anth_proof.py` | `tool_use` event carries `input={'symbol': 'RELIANCE.NS'}`, not `{}` | holds |
| R15-AGENT-005 | In-process `native_search_available` for groq/gemini per-model gating | groq `llama-3.3-70b-versatile`=False, `groq/compound`=True; gemini `gemini-2.5-pro` (with function tools)=False, `gemini-3-pro`=True; one-shot `gemini-2.5-pro` (no function tools)=True. No Groq/Gemini/xAI key funded, same as original certification (code-level) | holds |
| R15-AGENT-018 | In-process `rescue_leaked_tool_call` replaying the ORIGINAL evidence text verbatim (the leaked `write_note` JSON from `composer-chat/13-multiturn-t4-note.jsonl`) | leaked JSON rescued into a real `tool_use` (`name=write_note`, args preserved); a name not offered stays text; `ollama.py` source confirms it calls the shared `rescue_leaked_tool_call` (not the OpenAI-only path) | holds |
| R15-UI-008 | Live `POST /llm/keys/validate` with fake OpenRouter/Gemini/xAI keys | OpenRouter: `{"ok":false,"reason":"invalid","detail":"OpenRouter rejected this key."}` (was previously `ok:true`) | holds |
| R15-CODE-AGENT-003 | Same live probe as UI-008 | Gemini: `{"ok":false,"reason":"invalid",...}` (was "transport error"); xAI: `{"ok":false,"reason":"invalid",...}` (was "transport error") | holds |
| R15-RESEARCH-010 | In-process `run_research_model_brief("research Bharat Electronics", api_key=<canary fake OpenRouter key>)` — live OpenRouter HTTP call, real 401 | `{"ok": False, "message": "OpenRouter rejected the request — check that your OpenRouter API key is valid and active."}`, and an `engine` step with `status="error"` carrying the same message reaches the trace (was: 2 "ok" steps + "done", no error, model fabricated "Wikipedia, Forbes, Bloomberg") | holds |

Note: positive-key controls (real OpenRouter/OpenAI/DeepSeek keys still validate true) were not
re-run — no real key was read or printed in this shard; the negative (rejected-key) path fully
covers the register's regression class and is the more consequential direction.

COVERAGE: 6/6 ids raw; no raw: none.
