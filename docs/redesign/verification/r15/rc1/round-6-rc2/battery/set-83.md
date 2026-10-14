# lows-P2/llm-adapters (set-83), shard rc1-battery-7, candidate ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-AGENT-019 | POST /llm/keys/validate with unreachable base_url (openai, anthropic; fake key) | detail "Could not reach OpenAI - check your network. Check your internet connection and try again." (sentence + action, no SDK repr/URL) | holds |
| R15-CODE-AGENT-021 | design: key-transport docstrings in routers/llm.py + services/llm/base.py | llm.py:61-64 now states header on GET /llm/models, body on the POSTs "never the query"; no "never the body" claim left in llm files; test_no_llm_route_echoes_the_key exists | holds |

COVERAGE: 2/2 ids raw; no raw: none
