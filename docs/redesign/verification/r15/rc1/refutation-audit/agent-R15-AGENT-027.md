# R15-AGENT-027 refutation audit (group agent)

HEAD: `6741387b`. In-process, no keys, no network (realistic SDK exception objects built from httpx.Response / google.genai ClientError).

## Entry and certification
- Entry: humanize() classified by status alone. Stated legs: OpenAI no-credit 429 and OpenRouter free shared-pool 429 -> 'wait a minute'; invalid Gemini/xAI keys (400) -> 'try again'; invalid model ids (400) -> 'try again'; context overflow (400/413) -> 'try again'; stopped Ollama -> 'check your network'; user_id leaked in detail. Root cause text includes "network copy is provider-agnostic". Fix shape: a (provider, status, body-substring) table.
- Certified stage-c/batch-3/VERDICTS.md:126 (every captured body mapped correctly).

## Verifier refutation (rc1-verifier:8 re-confirming rc1-vshard-0:5, evidence inproc-refutations.txt)
gemini 400 "input token count exceeds the maximum number of tokens allowed" -> unknown 'Try again'; groq 400 "model ... has been decommissioned" -> unknown; xai 403 "team doesn't have any credits yet" -> auth 'Re-enter the API key'; ollama httpx.ReadTimeout -> network 'Check your internet connection'.

## Commands and output at HEAD
`cd sidecar && .venv/bin/python $SCRATCH/refaudit-agent/agent027.py`
```
## ENTRY REPRO (as stated)
openai 429 'credit balance exhausted' (plain exc)          -> code=insufficient_credit | Your OpenAI account is out of credit or quota. | Add credit or check your plan, or switch provider in Settings.
openai 429 SDK insufficient_quota body                     -> code=insufficient_credit | Your OpenAI account is out of credit or quota. | Add credit or check your plan, or switch provider in Settings.
openai 400 'maximum context length'                        -> code=context_overflow | The conversation is too long for this OpenAI model. | Start a new chat or pick a model with a larger context window.
groq 413                                                   -> code=context_overflow | The conversation is too long for this Groq model. | Start a new chat or pick a model with a larger context window.
ollama ConnectError all attempts failed                    -> code=ollama_not_running | Ollama is not running. | Start Ollama (open the app or run `ollama serve`), then try again.
gemini ClientError 400 API_KEY_INVALID                     -> code=auth | The Google Gemini API key was rejected — check it in Settings. | Re-enter the API key in Settings.
xai BadRequestError 400 Incorrect API key                  -> code=auth | The xAI API key was rejected — check it in Settings. | Re-enter the API key in Settings.
openrouter 400 not a valid model ID                        -> code=model_not_found | The requested model is not available on OpenRouter — pick another model. | Choose a different model in Settings.
openrouter 429 :free shared pool                           -> code=free_pool_busy | OpenRouter's free-model pool is busy right now. | Try again shortly, or pick a paid model in Settings.
   user_id scrubbed in detail: True | True
## VERIFIER REFUTATION CASES (rc1-verifier:8 / rc1-vshard-0:5)
gemini ClientError 400 input token count exceeds max       -> code=unknown | Something went wrong with Google Gemini. | Try again or switch provider in Settings.
groq BadRequestError 400 model decommissioned              -> code=unknown | Something went wrong with Groq. | Try again or switch provider in Settings.
xai PermissionDeniedError 403 no credits                   -> code=auth | The xAI API key was rejected — check it in Settings. | Re-enter the API key in Settings.
ollama httpx.ReadTimeout (slow local load)                 -> code=network | Could not reach Ollama — check your network. | Check your internet connection and try again.
```
`cd sidecar && .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_errors.py`
```
47 passed in 0.07s
```

## Reasoning
- Every body the entry captured now maps to the right next step (insufficient_credit, free_pool_busy, auth, model_not_found, context_overflow, ollama_not_running, user_id redacted). The entry's own repro does not reproduce.
- The verifier's four cases all reproduce at HEAD, and three of them are stated legs of the entry, just with provider phrasings the marker lists miss:
  - context overflow (entry leg "context overflow (400/413) say 'try again'"): Gemini's real 400 wording "The input token count (N) exceeds the maximum number of tokens allowed (M)" contains none of the markers at `sidecar/services/errors.py:288` ("context length", "context_length", "maximum context", "context window", "too long") -> falls to the generic 'unknown' fallback (errors.py:522-527).
  - invalid model id (entry leg "invalid model ids (400) say 'try again'"): Groq's real 400 `code: model_decommissioned` "has been decommissioned and is no longer supported" misses the markers at errors.py:272.
  - no-credit (entry leg "OpenAI no-credit 429 says 'wait a minute'"): xAI answers no-credit with 403; the credit rule at errors.py:263-264 only covers statuses {400, 429}, so the 403 falls to the status branch at errors.py:411-417 -> auth 'Re-enter the API key' (a valid key the user is told to replace).
  - Ollama ReadTimeout (entry root cause "network copy is provider-agnostic"): the class heuristic at errors.py:454-460 still says "check your network / internet connection" for a local daemon that is just slow to load a model. The entry's specific leg (stopped Ollama / connection refused) is fixed; this is the remaining provider-agnostic part.
- The provider bodies for the verifier legs come from the verifier (no keys here to elicit them live); the Gemini, Groq and xAI wordings match those providers' documented/well-known error bodies. The verdict does not depend on live elicitation: humanize() is a pure function of (provider, exception).

## Classification: partial
The fix holds for the entry's stated repro bodies, but the same defect (status-or-narrow-marker classification giving an unworkable next step) remains for stated parts of the class: context overflow, invalid model, no-credit, and Ollama's provider-agnostic network copy.

Acceptance test (sidecar/tests/test_errors.py, new parametrized `test_provider_bodies_get_a_workable_next_step`):
- `humanize("gemini", genai_errors.ClientError(400, {"error":{"code":400,"message":"The input token count (1200000) exceeds the maximum number of tokens allowed (1048576).","status":"INVALID_ARGUMENT"}})).code == "context_overflow"`
- `humanize("groq", openai.BadRequestError(<400, {"error":{"message":"The model `mixtral-8x7b-32768` has been decommissioned and is no longer supported...","code":"model_decommissioned"}}>)).code == "model_not_found"`
- `humanize("xai", openai.PermissionDeniedError(<403, {"error":"Your newly created team doesn't have any credits yet..."}>)).code == "insufficient_credit"`
- `h = humanize("ollama", httpx.ReadTimeout("timed out"))`: `"internet" not in h.action.lower()` and `"network" not in h.message.lower()` (e.g. code "ollama_slow" / "Ollama is taking too long - the model may still be loading").
- Keep the existing rows green (OpenAI 429 credit, OpenRouter :free 429, Gemini/xAI 400 bad key, 400 context, Groq 413, Ollama connection refused).
