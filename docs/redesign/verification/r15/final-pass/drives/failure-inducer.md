# final-drive-failure-inducer — induced failures at the app's edge, final pass

Head under test `d38b5d1a2487bd52fe8a7e741a3a5266e3206611` (scratch worktree `final-cand`, booted from
source, `sidecar/.venv`). Own sidecar `:52847` (data dir `final-data-final-drive-failure-inducer`, a
`cp -R` of the keyless `final-seed-data`), MCP pair shared read-only `:52801`/`:52802`. Junk provider
stub `:52848` = the census harness `surface/failure-inducer/harness/junk_provider.py` verbatim
(loopback, stdlib). Every induction was on MY process only, by env profile (`fi-final/boot.sh`, same
profiles as the census `harness/boot.sh`): `junk` (`OPENAI_BASE_URL`/`OLLAMA_HOST` -> stub),
`netdown` (`HTTP(S)_PROXY/ALL_PROXY=127.0.0.1:9`, `NO_PROXY` loopback), `nodocker` (stripped `PATH`),
plus corrupt copies of my own data files. Network, Docker, firewall and other ports untouched.

Harness note: `scripts/r15/vy.py:310` refuses non-GET calls outside ports 52100-52399, so it cannot
drive `:52847`. Agent turns used a scratch keyless client (`fi-final/inv.py`: vy's exact
`cmd_invoke` payload and headers, never reads a keystore, fake key `sk-invalid-r15-induced-401` or
none). Evidence: `surface/failure-inducer/final/50-junk-run-vy-portguard.log`. Spend $0 (stub, fake
keys, one local Ollama 404 under the lock). Evidence directory below = `surface/failure-inducer/final/`.

## Scored table (census inducer -> final)

| # | inducer | what the app SAID at d38b5d1a | score | census -> final | evidence |
|---|---|---|---|---|---|
| 01 | 401 bad key (OpenRouter, fake key) | error `auth` "The OpenRouter API key was rejected — check it in Settings." | ok | honest -> honest | `01-401-badkey.txt` |
| 02 | no key (OpenRouter) | error `auth` "No OpenRouter API key is set — add it in Settings." | ok | partial ("Something went wrong") -> ok | `02-nokey.txt` |
| 03 | 402 DeepSeek balance | fake key -> `auth` 401 honest; the 402 balance path needs a real key (not driven by design: no keystore reads); `test_errors.py::test_402_deepseek_balance` passes | partial (unit-pinned only) | honest -> unit-pinned | `03-deepseek-fakekey.txt`, `70-pinned-tests.txt` |
| 05 | network unreachable, LLM (netdown) | error `network` "Could not reach OpenRouter — check your network." in 0.4 s | ok | honest -> honest | `05-network-unreachable-llm.txt` |
| 30 | network unreachable, data routes | `/history`, `/quotes/AAPL`, `/indicators` -> 503 `network` sentence; `/news` -> 502 `provider_error` sentence; batch `/quotes` drops AAPL (documented skip-on-failure, rc1); `/health` green; **`/earnings/AAPL/history` -> 200 `history:[]` in 2 ms, and that empty is cached: after rebooting with the network back it still serves `[]` (as_of = the outage instant) while `:52800` returns rows** | partial | broken -> partial (R15-DATA-061 legs hold; earnings leg = open R15-LEAD-071, attached) | `30-netdown-data-routes.txt`, `31-earnings-outage-cached-empty.txt` |
| 20 | retired / unknown model slug | stub 404 -> `model_not_found` "pick another model"; live OpenRouter with a fake key answers 401 before checking the slug, so slug wording is proven via `humanize` ("is not a valid model ID" -> `model_not_found`) | ok | honest -> honest | `20b-stub-404-model.txt`, `21-nonsense-slug-fakekey.txt`, `60-agent027-humanize-probe.txt` |
| 21 | nonsense slug (400) | `humanize('openrouter', 400 'not a valid model ID')` -> `model_not_found` | ok | misleading -> ok | `60-agent027-humanize-probe.txt` |
| 22 | un-pulled Ollama model (real Ollama, lock held) | `model_not_pulled` "Run `ollama pull qwen9.9:404b-notpulled`, or pick an installed model" | ok | partial -> ok (R15-AGENT-028 holds) | `22-ollama-unpulled-model.txt` |
| 40 | SearXNG / Docker status | `/search/status` t1_keyless, 3 engines listed; `/search/searxng/status` `degraded` "SearXNG is running but its search engines are blocked" (brave/duckduckgo/startpage suspended upstream — same environment condition rc1 probed; Docker is running today, so the census "Docker absent" state is not reachable without touching the system; the PATH-strip still cannot fake it, as rc1 recorded) | ok | honest -> honest | `40-search-status-base.txt` |
| 41/43 | chat web_search, dead custom SearXNG URL + keyless tier, PATH stripped | in-process `web_search`: dead URL -> keyless fallback ok, 5 results, 0.9 s; keyless 12.0 s -> `ok:false` "keyless web search has no engine available right now — DuckDuckGo: unreachable; Brave: rate-limiting; Mojeek: rate-limiting. Wait a moment and retry, or add an Exa key / local SearXNG" — inside the 25 s tool cap, honest | ok | broken -> ok (R15-RESEARCH-008 holds) | `41-websearch-direct-nodocker.txt`, `70-pinned-tests.txt` |
| 50 | junk: 200 HTML | `empty_response` "The model returned an empty answer." | ok | silent -> ok | `50-junk-html.txt` |
| 50 | junk: SSE non-JSON | `parse_error` "OpenAI returned an unreadable response." | ok | honest -> honest | `50-junk-badsse.txt` |
| 50 | junk: clean EOF mid-answer | `truncated` "The provider closed the stream before the answer finished."; the partial "RELIANCE closed at Rs 1,4" delta is NOT relayed | ok | silent, money-relevant -> ok | `50-junk-truncated.txt` |
| 50 | junk: choices [] | `empty_response` | ok | silent -> ok | `50-junk-emptychoices.txt` |
| 50 | junk: chunked body cut | `unknown` "Something went wrong with OpenAI. Try again or switch provider in Settings." (detail "peer closed connection ... incomplete chunked read"); partial delta not relayed | ok (generic but honest; Retry is the right step) | census refute "Could not reach OpenAI" -> generic since round 4 | `50-junk-chunkdrop.txt` |
| 50 | junk: OpenRouter-style error chunk | `provider_5xx` "OpenAI returned a server error — it may be a temporary outage." | ok | honest -> honest | `50-junk-orerror.txt` |
| 50 | 429 + Retry-After 1 | 3 attempts 1 s apart (stub log), then `rate_limit` | ok | honest -> honest | `50-junk-429.txt`, `50-junk-stub-requests-429-500.txt` |
| 50 | 500 | 3 attempts, then `provider_5xx` | ok | honest -> honest | `50-junk-500.txt` |
| 51 | Ollama: HTML / truncated NDJSON | `parse_error` "Ollama returned an unreadable response." (x2) | ok | honest -> honest | `51-ollama-junk-html.txt`, `51-ollama-junk-ndjson.txt` |
| 52 | provider accepts, never streams (live, 180 s) | 17 heartbeats, then at 180.1 s error `network` "Could not reach OpenAI — check your network." / "Check your internet connection and try again.", detail "" | partial | silent spinner -> not silent, but wrong next step (new_defect low FI-FINAL-HANG-NETWORK-COPY) | `52-junk-hang.txt` |
| 10 | malformed symbols x 9 routes (81 GETs) | 57x 200 / 24x 404, zero 5xx, zero leaked library text in any body; `/history` says `reason:"unknown_symbol"` (census: "India is EOD only"); `/indicators` 200 empty (census 502); slash-bearing symbols on `/fundamentals` + `/earnings/.../history` -> bare `{"detail":"Not Found"}` (path routing; same as census, crypto pairs routed by query per R15-DATA-081); SQL/HTML/unicode inert | ok | partial -> ok | `10-malformed-symbols.jsonl` |
| 60 | R15-AGENT-027 residual (humanize) | 12 of its 13 repro shapes now get a workable step; round-5 residual `groq 413` with an empty body still -> `unknown` "Try again" | partial | open entry, attached | `60-agent027-humanize-probe.txt` |
| 80 | corrupt `data_cache.db` (own copy) | **sidecar startup fails** (`sqlite3.DatabaseError: file is not a database` from `data_cache._connect` in the lifespan) -> the app only says "The data engine stopped (exit code N)", every launch | broken | not driven by the census -> new_defect high FI-FINAL-CORRUPT-CACHE-BRICKS-BOOT | `81-corrupt-cache-boot-fails.txt`, `83-corrupt-each-db-boot.txt` |
| 81 | corrupt workspace file | quarantined `__autosave__.vysted-workspace.corrupt-<ts>`, GET answers 404 | ok | R15-DATA-090 holds (its known 404-wording residual unchanged) | `82-corrupt-portfolio-workspace.txt` |
| 82 | corrupt legacy `portfolio.db` | `GET /portfolio/positions` bare 500; its one consumer (`fetchLegacyPositions`, `src/modules/portfolio/api.ts:68-74`, one-time import) maps `!ok` to `[]`, file untouched | ok (no user-visible harm) | new state, not filed | `82-corrupt-portfolio-workspace.txt` |
| 83 | other corrupt stores (fundamentals_cache, custom_agents, delegate_runs, plugins, workflows) | boot UP for each; see the matrix file | ok | new state | `83-corrupt-each-db-boot.txt` |
| 90 | kill MY sidecar (its sleep pid) mid-stream | the SSE body ends after 2 heartbeats with no `done`/`error` frame (client sees EOF); the chat maps exactly that to `STREAM_ENDED_EARLY` "The stream ended before the answer finished." (`streaming.ts:370`, pinned `streaming.test.ts:375,384`) and the core's `vysted://sidecar-terminated` sets "The data engine stopped (exit code N)." (`src/store/app.ts:93`, `src-tauri/src/lib.rs:85-90`) | ok | not driven by the census | `90-kill-sidecar-midstream.txt`, `90-kill-run.log` |
| 70 | pinned tests (test_errors, test_b5_runtime_liveness, test_keyless_backend) | 86 passed | ok | — | `70-pinned-tests.txt` |

Frontend mapping re-cited at d38b5d1a: `src/modules/chat/streaming.ts:172-186` (`STREAM_ENDED_EARLY`,
`STREAM_STALLED`, `AGENT_STREAM_IDLE_MS=45_000` against the 10 s runtime heartbeat), `ChatSidebar.tsx:991-997`
(provider failure held / settled), `:1380-1392` + `:1640-1680` `ErrorRow` (message, action, Details, Retry or
Open Settings). Rendering of each frame in a window is NEEDS-GUI; the text above is what the frame carries.

## Census -> final deltas

- Fixed and holding: R15-AGENT-026 (truncated/empty/HTML now explicit), R15-AGENT-025 core (no silent
  spinner; heartbeats + an error at 180 s, live), R15-RESEARCH-008 (keyless web_search inside the cap),
  R15-AGENT-028 (Ollama pull hint), no-key wording, malformed-symbol classification, R15-DATA-090.
- Still open, attached (not new): R15-AGENT-027 (groq 413 empty body -> "Try again"); R15-LEAD-071
  (earnings history empty on a provider failure, cached 24 h — now shown for a network outage too).
  R15-DATA-061 stays blocked_tier4; its data-route legs probed here hold.
- New: FI-FINAL-CORRUPT-CACHE-BRICKS-BOOT (high), FI-FINAL-HANG-NETWORK-COPY (low).
- Wording drift, not filed: chunked mid-stream drop went from "Could not reach <provider>" (census
  refute) to a generic "Something went wrong ... Try again" (since round 4); still honest.

## Not driven

- 402 with a real DeepSeek key and a live retired-slug 404 from OpenRouter: both need a real key; this
  role never reads a keystore. Covered by unit tests and the `humanize` probe.
- Docker-absent: Docker is running on this machine and the PATH strip no longer fakes its absence.
