# batch-3/W3-llm-adapters-and-errors — shard rc1-battery-12

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-004 | Standalone script (real Anthropic SDK + httpx.MockTransport) replaying documented tool-use SSE shape through `AnthropicProvider.stream_chat` | `tool_use get_quote {'symbol': 'RELIANCE.NS'}` — accumulated args, not `{}` | holds |
| R15-AGENT-005 | In-process `native_search_available()` calls for Groq default model, Groq Compound, Gemini default model, Gemini 3, xAI | Groq default / Gemini default / xAI all `False` (local web_search kept); Groq Compound / Gemini 3 `True` | holds |
| R15-AGENT-018 | In-process replay of register's leaked-JSON evidence text through `tool_call_rescue.rescue_leaked_tool_call` (ollama.py's end-of-stream rescue path) | `write_note`/`screener_run` leaked JSON rescued to `tool_use` with unique `leaked_*` id; not-offered name stays unrescued (`None`) | holds |
| R15-UI-008 | Live `POST /llm/keys/validate` on own sidecar (:52352) with fake OpenRouter key from register repro | `{"ok":false,"reason":"invalid","detail":"OpenRouter rejected this key."}` | holds |
| R15-CODE-AGENT-003 | Live `POST /llm/keys/validate` with fake Gemini + xAI keys | Both `{"ok":false,"reason":"invalid",...}`, no "transport error" string | holds |

COVERAGE: 5/5 ids raw; no raw: none.
