# set-59 — batch-12/W6-error (rc1-battery-1, gate round 5)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. In-process repro of `services.errors.humanize()`
against the candidate's sidecar venv, with synthetic exceptions matching the register's and the
batch-12 verifier's exact repro shapes (status codes / message bodies), plus one live `ConnectError`
to a closed port for the Ollama case.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-027 | `humanize('openai', 429 "credit balance ... too low")` / `humanize('openai', 429 "Rate limit reached")` / `humanize('openai', 400 "maximum context length")` / `humanize('groq', 413 "Request too large")` / `humanize('ollama', ConnectError, live closed-port connect)` / `humanize('gemini', 400 API_KEY_INVALID)` / `humanize('xai', 400 bad key)` / `humanize('together', 404 model_decommissioned)` / `humanize('openrouter', 402 no-credit)` | `insufficient_credit` / `rate_limit` / `context_overflow` / `context_overflow` / `ollama_not_running` ("Ollama is not running.") / `auth` (Gemini key rejected) / `auth` (xAI key rejected) / `model_not_found` / `provider_402` — each distinct message+action, none collapsed to the register's old "try again"/"check your network" catch-all. The register's OpenAI no-credit-429 vs plain-rate-limit-429 distinction (the entry's headline defect) still resolves to two different codes | holds |

COVERAGE: 1/1 ids raw; no raw: (none).
