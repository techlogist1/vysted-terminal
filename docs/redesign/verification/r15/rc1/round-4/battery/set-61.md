# batch-12/W6-error-copy-markers-option-chain-negative-probe (rc1-battery-24)

Candidate: 1006c6da694ede5776c3dabbd27b305aeb56b5ad. Own sidecar :52364.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-AGENT-027 | in-process `errors.humanize()` on the register's rows (OpenAI 429 credit-exhausted, OpenAI 400 context-length, Groq 413, a real `httpx.ConnectError` for Ollama) + batch-12's fresh cases (Gemini 400 token-count, OpenRouter 403 no-credits, "together" 404 model_decommissioned, a DNS-failure ConnectError to a non-Ollama provider) | OpenAI 429 -> insufficient_credit; OpenAI 400 -> context_overflow; Groq 413 -> context_overflow; Ollama ConnectError -> ollama_not_running "Ollama is not running."; Gemini 400 -> context_overflow; OpenRouter 403 -> insufficient_credit; together 404 -> model_not_found; non-Ollama DNS failure -> network "check your network" — all match batch-12's certified mapping, no row falls back to a wrong/generic next-step | holds |
| R15-DATA-114 | live: 3 consecutive `GET /quant/option/chain/NIFTY` against the candidate sidecar | all 200; call 1 = 0.79s (cold probe), calls 2 and 3 = 0.04s each (served from cache, no re-probe); as_of stayed a single cached day (2026-09-25) across all three, no 502 | holds |

COVERAGE: 2/2 ids raw; no raw: none.
