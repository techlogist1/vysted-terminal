# LS-3 — failure at the app's edge (own sidecars only)

Raw: `LS-3/edge-probes.txt` (closed-port / garbage upstream / malformed / oversized / unicode probes on my :52825) and `LS-3/kill-probes.txt` (kills of my own processes).

**Edge probes (all pass):**
- Ollama/OpenAI base URL on a closed local port: clean SSE error frames (`ollama_not_running`, `network`) with an action; validate `ok:false unreachable`; `/llm/models` falls back to the registry list with an honest source note.
- Garbage-speaking upstream: error frame `code unknown`, no raw bytes; validate `unreachable`.
- Malformed JSON / wrong types on invoke and ack: 422 with field paths; unknown ack status 422.
- 30 MB workspace save 200; 20 MB chat body handled (error frame, no crash).
- Unknown / Devanagari / emoji / traversal symbols: 404 `not_found` or 429 with a sentence; traversal workspace name `../../escape` stored percent-encoded inside `workspaces/` (`_path_for`), not outside it.
- Health 200 after the whole battery.

**Kill my openbb-mcp mid-request** (worker 26575 + its stdin sleep, two calls in flight on :52825): the sidecar survives (health 200); `/fundamentals/AAPL` falls back to yfinance with real data; the in-flight `/fundamentals/NVDA/income` returned 200 with empty `periods`/`lines` and no reason after 60.9 s, and `/macro/GDP?provider=oecd` answers 502 `provider_error` "Retry" both before and after the kill (openbb-mcp already reported `failing` in /health before the kill). Both are the R15-DATA-061 class (blocked_tier4, DECISIONS 4.19: empty-200 and 'Retry' misclassification) -> attached, not re-filed. The research-mid-flight variant was not run: it needs a local-model turn and openbb-mcp was already failing on this instance, so it could not isolate the kill.

**Kill my main sidecar mid-request:**
- SIGTERM to my python-run sidecar (:52398) with an SSE chat held open by a blackhole upstream: the listener closes at once, but graceful shutdown waits for the held stream; the client saw HTTP 200 and no frame until its own 30 s cap, then the process exited once the upstream closed. The Ollama adapter's idle timeout is 300 s (`LOCAL_IDLE_TIMEOUT_S`), so a hung local upstream would end in an error frame after 5 min — slow, by design for local models, not filed.
- SIGKILL to my bundle sidecar worker (:52829) with an SSE chat in flight: the client connection dropped immediately (curl rc 18, partial transfer), the bootloader exited too, port closed, no orphans. The chat UI has a dedicated "The stream ended before the answer finished." path (`src/modules/chat/streaming.ts:173`), the workflow store names a mid-run crash, and the screener store reports "Sidecar unreachable".
- A first attempt at :52820 was not mid-request (both curls ran in the foreground before the kill; recorded as a correction in kill-probes.txt); its kill result (process gone, port closed, no children) still holds.
- My main-data :52825 stayed healthy through every kill of a sibling instance.

VERDICT LS-3: pass
