# Set: batch-3/W3-llm-adapters-and-errors (set-7) — candidate ace7dd76, sidecar :52344

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-004 | real anthropic SDK + httpx.MockTransport replaying tool-use SSE (input:{} start, input_json_delta fragments) through AnthropicProvider.stream_chat | 'tool_use get_quote {symbol: RELIANCE.NS}', second block 'news {symbol: TCS.NS, limit: 5}', then done tool_use (was {}) | holds |
| R15-AGENT-005 | native_search_available for gemini-2.5-pro, groq llama-3.3-70b, xai, groq/compound, gemini-3 (code-level, as the original repro; no Gemini/Groq key) | False with function tools for gemini-2.5-pro / groq llama / xai (local web_search kept); True for groq/compound and gemini-3-*; one-shot gemini-2.5-pro True | holds |
| R15-AGENT-018 | replay the ORIGINAL evidence delta text of composer-chat 13 and 14 through OllamaProvider.stream_chat (fake client) | 13 -> tool_use write_note {note: ...} id leaked_*; 14 -> tool_use screener_run {criteria: ...}; control not-offered name stays text. Leaked JSON still streams as delta before tool_use in case 14 (batch-3 issue 8, known residual) | holds |
| R15-UI-008 | POST /llm/keys/validate with fake openrouter key; direct openrouter /models vs /key with fake bearer | ok:false reason invalid 'OpenRouter rejected this key.' (models 200, key 401 still as in entry) | holds |
| R15-CODE-AGENT-003 | POST /llm/keys/validate with fake openrouter, gemini, xai keys | all three ok:false reason invalid '<Provider> rejected this key.' (gemini/xai no longer 'transport error') | holds |

COVERAGE: 5/5 ids raw; no raw: none
