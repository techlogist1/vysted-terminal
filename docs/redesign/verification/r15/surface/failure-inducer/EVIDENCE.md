# surf-S2D failure-inducer — induced failures at the app's edge (session 2)

Agent: claude-opus-5-5[1m]. Continues `surface/inducer/` (01 401, 02 no-key, 03 402, 05 network
.txt from 19 Sep). All induction was done on MY sidecar only: `:52224` booted from source per
`ISO_STACK.md`, data dir = `sqlite3 .backup` copy of `$ISO/data` at
`$ISO/seat-failure-inducer/data`, own MCP pair `:53224` (openbb) / `:53234` (sec-edgar). Each
induced state is an env profile of that one process (`harness/boot.sh <profile>`):

| profile | how induced (my process only) |
|---|---|
| base | normal env |
| netdown | `HTTP(S)_PROXY/ALL_PROXY=http://127.0.0.1:9` (closed port), `NO_PROXY=127.0.0.1,localhost` so loopback MCP/SearXNG still resolve |
| nodocker | `PATH=/usr/bin:/bin:/usr/sbin:/sbin` (no `docker`, no OrbStack bin) |
| junk | `OPENAI_BASE_URL=http://127.0.0.1:52294/v1`, `OLLAMA_HOST=http://127.0.0.1:52294` -> `harness/junk_provider.py` (loopback stub, mode chosen by model id) |

Docker, the network, the shared SearXNG container and every other port were never touched.
LLM calls: vy.py only. Spend: $0 (OpenRouter `:free` x3, Ollama local, junk-stub calls use
vy's fake `--bad-key` so no real key or money reaches a real host).

Frontend error mapping (what a chat turn renders for an `error` frame):
`src/modules/chat/streaming.ts:344-356` parses `{message, action, detail, code}`;
`ChatSidebar.tsx:2023-2024` -> `onError` -> `ChatSidebar.tsx:900-911` stores the frame and
`fail()`s the message; `ChatSidebar.tsx:1239-1250` renders `ErrorRow` (message, action,
"Details" = detail, Retry). A `done` frame instead goes `ChatSidebar.tsx:914-919` ->
`finalizeAssistantMessage` (`src/store/chat-history.ts:213-219`), which checks neither
`finishReason` nor empty content — no error row, no Retry.

## Scorecard

| # | inducer | what the app SAID | honest? | evidence |
|---|---|---|---|---|
| 01 | 401 bad key (19 Sep) | "The OpenRouter API key was rejected — check it in Settings." code auth | honest | `../inducer/01-401-badkey.*` |
| 02 | no key (19 Sep) | "Something went wrong with the AI provider." code unknown | partial (UI blocks keyless send; path reachable via MCP/delegate — see COD-error-layer-6, COD-runs-durable-delegate-2) | `../inducer/02-nokey.*` |
| 03 | 402 DeepSeek (19 Sep) | "Your DeepSeek balance is empty — top up or switch provider in Settings." | honest | `../inducer/03-402-deepseek.*` |
| 05 | network unreachable (LLM) | "Could not reach OpenRouter — check your network." code network, 1.4 s | honest | `../inducer/05-network-unreachable.jsonl` + `.vy.txt` (finished this session; the 19 Sep `.txt` was the curl half) |
| 30 | network unreachable (data routes) | `/history/AAPL` 200 `bars:[] reason:null` in 3 ms -> chart "No price data for this symbol"; `/quotes?symbols=RELIANCE,TCS,AAPL` silently drops AAPL; `/fundamentals/TCS` 502 raw curl text; `/news` 502 "all news sources failed"; `/health`, `/search/status` stay green | **misleading** | `30-netdown-data-routes.txt`, `31-netdown-sidecar-log-excerpt.txt` -> SURF-FAILURE-INDUCER-4 |
| 20 | retired slug `z-ai/glm-4.5-air:free` | 404 -> "The requested model is not available on OpenRouter — pick another model." (detail carries OpenRouter's "use z-ai/glm-4.5-air") | honest | `20-retired-slug-glm45air.*` |
| 21 | nonsense slug | 400 -> "Something went wrong with OpenRouter. Try again or switch provider" code unknown | misleading (retry can't help) | `21-nonsense-slug.*` -> SURF-FAILURE-INDUCER-5 |
| 22 | un-pulled Ollama model | "not available on Ollama — pick another model" | partial (already COD-error-layer-2-2: should say `ollama pull`) | `22-ollama-unpulled-model.*` |
| 40 | Docker absent | `/search/searxng/status` state `not_installed_docker`, detail "docker CLI not found — install Docker Desktop or OrbStack" (Settings renders it, `SettingsPanel.tsx:710,743,874`); `/search/status` tier `t1_keyless`, all 3 engines "available" | honest (status) | `40-nodocker-status.txt` |
| 41/43 | Docker absent (+ dead custom SearXNG URL on 41) -> chat web_search | 2/2 agent runs: tool cut at the 25 s cap; model tells user "timed out ... network issues ... narrow the query or retry at a lighter depth" | **silent/misleading** | `41-*`, `43-*`, `42-websearch-direct.txt`, `44-keyless-engine-timing.txt` -> SURF-FAILURE-INDUCER-2 |
| 50 | junk: 200 HTML page | `done` only, zero text, no error | **silent** | `50-junk-html.*` -> SURF-FAILURE-INDUCER-1 |
| 50 | junk: SSE with non-JSON data | "OpenAI returned an unreadable response." code parse_error | honest | `50-junk-badsse.*` |
| 50 | junk: stream cut mid-answer | delta "RELIANCE closed at Rs 1,4" then `done` (finish_reason null), no error | **silent, money-relevant** | `50-junk-truncated.*` -> SURF-FAILURE-INDUCER-1 |
| 50 | junk: choices [] then [DONE] | `done` only, zero text | **silent** | `50-junk-emptychoices.*` -> SURF-FAILURE-INDUCER-1 |
| 50 | 429 + Retry-After 1 | 3 attempts (stub log n=1..3), then "OpenAI is rate-limiting your account — try again in a minute." | honest for a real per-account 429 (free-pool 429 wording is SURF-RESEARCH-BRIEFS-8; OpenAI insufficient_quota-as-429 is COD-error-layer-5) | `50-junk-429.*` |
| 50 | 500 | 3 attempts, "OpenAI returned a server error — it may be a temporary outage." | honest | `50-junk-500.*` |
| 51 | Ollama: HTML / truncated NDJSON | "Ollama returned an unreadable response." (partial "Partial ans" delta precedes it) | honest — the Ollama adapter gets right what the OpenAI-compatible adapter gets wrong | `51-ollama-*` |
| 52 | provider accepts, never streams | zero SSE events for 150 s (client gave up); SDK read timeout is 600 s, no stall watchdog anywhere | **silent spinner** | `52-junk-hang.txt` -> SURF-FAILURE-INDUCER-3 |
| 10 | malformed symbols x 9 routes | see below | mixed, all already registered | `10-malformed-symbols.jsonl` (81 rows), `11-typo-history.txt` |

## Malformed symbols (`harness/malformed.py`, 9 symbols x 9 routes = 81 GETs)

Every defect seen is ALREADY a registered finding — cross-referenced here, not re-filed:

- `/quotes/{bad}` -> 502 `'PriceHistory' object has no attribute '_dividends'` for `"   "`, `$$$`,
  300 chars, SQL, Hindi, emoji, `RELIANCE.NS.NS` (SURF-COMPOSER-CHAT-3, INT-spec-135-137,
  DAT-P15-1). New fact: the SAME AttributeError is what a network outage produces for a valid US
  ticker (`31-netdown-sidecar-log-excerpt.txt`), so the message cannot mean "bad symbol".
- `/history/{bad}` -> 200 `bars:[] reason:"in_eod_only"` -> chart says "BSE/NSE serve end-of-day
  only — intraday/realtime needs a BYOK broker" for typos `RELIANC`, `INFOSYS`
  (`11-typo-history.txt`; the chart calls `/history` with the raw input, no resolve —
  `ChartPanel.tsx:996-1003,372`) = INT-spec-135-137 part 2 / SURF-PANELS-LAYOUTS-3. Its broker
  pointer also dies with the trading removal.
- `/indicators/{bad}` 502 vs `/history` 200 for the same symbol = COD-market-data-providers-2-7.
- `/earnings/RELIANCE.NS/history` -> symbol rewritten `RELIANCE-NS`, empty 200 =
  COD-market-data-providers-1-3.
- Any symbol containing `/` (`<script>…</script>`, `../../etc/passwd`, and the real pair
  `BTC/USDT`) -> 404 `Not Found` on every path route (Starlette decodes `%2F`) =
  COD-frontend-panels-data-surfaces-9, SURF-PORTFOLIO-NOTES-2, SURF-PANELS-LAYOUTS-5.
- SQL/HTML/unicode are inert: echoed back as data, no 500, no execution; `/resolve` answers
  `ok:false "No instrument matched …"` (honest). `/resolve?q=RELIANCE.NS.NS` offers only
  `RS "RELIANCE, INC." (US)` at 0.64 in region IN — low, not filed (resolver territory).

## SearXNG down + Docker absent -> chat web search (SURF-FAILURE-INDUCER-2)

`44-keyless-engine-timing.txt`: one cold `web_search` on the keyless tier — DuckDuckGo fails
twice at ~20.5 s each (41 s), then Brave answers in 0.9 s; total 42.5 s. Other cold runs:
42.6 s, 45.1 s, 47.4 s (`42-websearch-direct.txt`); a warm second call in the same process 1.7-4 s.
The agent cuts `web_search` at `catalog.py:313` `timeout_seconds=25.0`
(`agent_runtime.py:652-666`), so in chat the tool times out before the rotation ever reaches
Brave. Both agent runs on `:52224` (llama3.1:8b, `41-*` with a dead custom SearXNG URL, `43-*`
without) returned the timeout; the model relayed the research-domain hint
(`catalog.py:1572` "narrow the query or retry at a lighter depth" — web_search has no depth) and
blamed "network issues". `/search/status` said all three engines "available" before the call.
The dead custom URL itself costs nothing extra (connection refused -> immediate keyless
degrade, `web_search.py:140-144`); the stall is DuckDuckGo-first ordering x 2 attempts x
~20 s with no per-engine deadline (`keyless.py:150-190,201-232`, `pacing.py:42`, `ddg.py:60,84`).

## Honest-by-construction confirmations (no finding)

- Retired free slug -> clear "model not available, pick another" (`errors.py:173-180`); the
  stale pick survives relaunch by design (`model-selection.ts:69-75` never prunes OpenRouter).
- Docker absent -> Settings' SearXNG section names the cause and the fix.
- 429/500 -> bounded retries (3 attempts, Retry-After honoured) then plain language.

## Not tested

- A real provider 429 on the paid OpenAI lane (would cost ~$0.01 of burst traffic; the stub
  reproduces the adapter path exactly, so not worth the money).
- GUI rendering of each frame: NEEDS-GUI (text above is derived from the cited components).

## Process record

Sidecar `:52224` (sleep pid in `$ISO/seat-failure-inducer/main.sleep.pid`), MCP sleeps
37057/37060 (`mcp-pids.json`), junk stub pid in `junk-stub.pid` — all stopped at the end of
this stage.

## Refute-stage addendum (53)

`53-adapter-direct-stream-ends.txt` (`harness/adapter_direct.py`, adapter driven directly against
the stub, no sidecar): a chunked-transfer cut mid-answer -> "Could not reach <provider>" and an
OpenRouter-style error chunk (`error` + `finish_reason:"error"`) -> "<provider> returned a
server error" — both HONEST. Only a clean EOF without finish_reason, a 200 non-SSE body, and a
zero-output round stay silent, so SURF-FAILURE-INDUCER-1 was corrected to medium in
`census/refute/surf-failure-inducer.json`.

## Continuation addendum (COVERAGE + "does any frontend surface say research is degraded?")

- `COVERAGE.json` written (was missing): skeleton rows `chat-error-row`, `generic-error-frame-pattern`,
  `settings-research` (SearXNG sub-surface only), `provider-health-breaker`, plus four `x-` rows for
  the inducer classes. Every state scored from the files above; no new sidecar was booted.
- Degraded-research signal, code-read: `grep -rn "search/status" src/` finds ONE consumer,
  `SettingsPanel.tsx:710` (`/search/searxng/status`). The keyless-tier engine status `/search/status`
  has no frontend consumer at all, so the only degraded-research surfaces are Settings' SearXNG
  section (Docker absent: honest) and the brief's zero-source `noWeb` banner (`BriefPanel.tsx:709+`,
  fires only when a run gathered zero sources). A chat web_search that times out is surfaced only by
  the model's own prose — part of SURF-FAILURE-INDUCER-2, not re-filed.
- Panel error text under netdown: news -> "Sidecar error 502: all news sources failed"
  (`NewsFeedPanel.tsx:151-155`); equity-overview fundamentals -> the raw curl string via
  `SidecarError.message` (`equity-overview/api.ts:86-98,166-174`), part of SURF-FAILURE-INDUCER-4.
- `/system/provider-health` stayed `open:false, opens_total 0` through the full outage: the Yahoo
  breaker counts throttles, not transport failures (by design; not filed).
