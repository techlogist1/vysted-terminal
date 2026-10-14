# Gate round 3 — fix round 1 plan (rc1-fix-r1-triage)

Base `01d6920a300b016ab1ad8aa436ee4e4586f8e336` (candidate worktree verified at that sha, 2026-09-26 22:14 IST). Triage by Opus; code read in the candidate worktree, SDK mechanism reproduced directly in its `sidecar/.venv` (no sidecar boot needed; none started).

## Findings to close

| key | decision | writer |
| --- | --- | --- |
| rc1-drive-composer-chat:1 | **real** — root cause located | W1 |
| rc1-drive-research-briefs:1 | **deferred** — the RESEARCH-043 class, adjudicated to the operator (DECISIONS 4.14); filed as a concurrence note | — |

## rc1-drive-composer-chat:1 — real

**Mechanism.** Every key-taking adapter builds its SDK client BEFORE its `try:` in `stream_chat`: `services/llm/openai.py:591` (shared by openai/openrouter/xai/deepseek), `groq.py:126`, `gemini.py:138`, `anthropic.py:161`. Three SDKs raise at construction when the key is absent (probed in the candidate venv): `openai.AsyncOpenAI(api_key=None)` → `OpenAIError: Missing credentials…`, `groq.AsyncGroq` → `GroqError: The api_key client option must be set…`, `genai.Client` → `ValueError: No API key was provided…` (Gemini is exposed too — the record thought not). The exception skips the adapter's own `except … humanize(...)` and lands in the router last-resort guard (`routers/agents.py:106`, `routers/llm.py:167`), whose `error_frame` is deliberately "internal" per R15-AGENT-030 on the premise that adapters humanize their own failures. The premise is right; the adapters break it. Anthropic defers to request time (`TypeError: Could not resolve authentication method…`), inside its try, but `humanize` has no rule for it, so it gets the generic "Something went wrong" line.

**Fix (class, at the adapters — not the routers).** Move the `client = self._client(api_key)` line inside the existing `try:` in each of the four `stream_chat`s. Add ONE `_BODY_RULES` row in `services/errors.py` (any provider, any/no status) with markers `missing credentials`, `api_key client option must be set`, `no api key was provided`, `could not resolve authentication method` → code `auth`, message `No {label} API key is set — add it in Settings.`, action `Add your {label} API key in Settings.`. Router guards and `error_frame` stay unchanged (AGENT-030 holds).

**Acceptance.** With the provider env keys unset (`monkeypatch.delenv`), `stream_chat(..., api_key=None)` on OpenAI, Groq, Gemini and Anthropic each yields exactly one `LLMErrorEvent` with `code == "auth"` and a message naming the provider and Settings, and raises nothing. Live recheck: the record's `vy.py … --provider openai --no-key` and `--provider groq --no-key` repros return the `auth` frame, not `code:"internal"`.

## Writers

### W1 (sonnet) — adapter no-key humanization

Files: `sidecar/services/llm/openai.py`, `sidecar/services/llm/groq.py`, `sidecar/services/llm/gemini.py`, `sidecar/services/llm/anthropic.py`, `sidecar/services/errors.py`, `sidecar/tests/test_errors.py`.

Brief: Mechanism: `stream_chat` in openai.py:591, groq.py:126, gemini.py:138, anthropic.py:161 builds the SDK client before its `try:`; the OpenAI/Groq/Gemini SDKs raise on a missing key at construction, so the error bypasses the adapter's humanize and reaches the router guard's generic `code:"internal"` frame. Fix: move `client = self._client(api_key)` inside the existing try in all four; add one `_BODY_RULES` row in errors.py (any provider/status), markers 'missing credentials', 'api_key client option must be set', 'no api key was provided', 'could not resolve authentication method' -> code 'auth', message 'No {label} API key is set — add it in Settings.', action 'Add your {label} API key in Settings.'. Routers/error_frame untouched. Test (test_errors.py, one parametrized): env keys deleted, each adapter's stream_chat(api_key=None) yields one LLMErrorEvent code 'auth', never raises.

## rc1-drive-research-briefs:1 — deferred (DECISIONS 4.14)

A model-written `[vysted://fundamentals/CGPOWER]` shipping verbatim is a non-`[n]` bracket token passing through the citation net unresolved — exactly the class R15-RESEARCH-043 names (grouped markers / bracketed prose). The lead note for this round orders such reproductions filed as a concurrence note under RESEARCH-043, never a new defect and never a fix round. The candidate deliberately carries the original narrow-`[n]` behaviour after the `1288ec19` revert (`3a674e7c`). Filed: a concurrence bullet appended to DECISIONS 4.14 (the new shape is a useful fourth case for its option (a) tests). Register note under R15-RESEARCH-043 is the lead's to add.

## Not in scope

No entry from the three-failure list (LEAD-028, AGENT-019, CODE-PLATFORM-013, AGENT-010, LEAD-039) and nothing in the local-model figure class is touched.
