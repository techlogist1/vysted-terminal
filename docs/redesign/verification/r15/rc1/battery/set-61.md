# batch-12/W6-w6 (set-61)

Candidate 4c6dfe8c. Own sidecar :52342, data dir rc1-data-battery-2. Raw output: `raw/set-61/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-AGENT-027 | In-process (candidate venv): `services.errors.humanize(provider, exc, detail=body)` on the cert's original repro rows + all 4 fresh cases + the ollama connect/timeout/DNS class checks | openai 429 "credit balance exhausted" -> `insufficient_credit`; gemini 400 "exceeds the maximum number of tokens allowed" -> `context_overflow`; openrouter 403 "does not have any credits" -> `insufficient_credit`; together 404 "model_decommissioned" -> `model_not_found`; ollama ConnectError -> `ollama_not_running`/"Ollama is not running."; ollama ReadTimeout -> `ollama_not_running`/"Ollama is not responding." (distinct message, no internet/network copy); a real DNS ConnectError to openai (non-ollama) -> `network`/"Could not reach OpenAI — check your network." All match batch-12's cert exactly. (First pass passed the body text via the exception's own message instead of `detail=`, which `str(exc)` does not carry for an `httpx.HTTPStatusError` — corrected using the `detail=` kwarg the real call sites use.) | holds |
| R15-DATA-114 | Live: 3 consecutive `GET /quant/option/chain/NIFTY`, timed | All 3 calls: HTTP 200, `as_of: 2026-09-25` (cached day, no live market data for today at request time). Call 1: 0.70s (cold, one NSE probe); calls 2/3: 0.04s each — a single probe of "today", then served from cache, not re-probed 3x. Matches the certified fix exactly. | holds |

Summary: 2 holds, 0 regressions. AGENT-027's first probe used a test-construction shortcut (embedding the body in the exception message rather than the `detail=` kwarg) that doesn't match how `humanize()` actually reads a provider body; corrected and re-run, all classifications matched the cert.
