# composer-chat — owner-drive evidence (R15 Stage B item 4, surf-S2A, agent B)

Worker: claude-opus-5-5[1m] ("agent B" in `_TWIN_AGENTS.md` — a second worker, agent A, drove
the same two groups concurrently; A's files here are `conv1-*` and `http-log.jsonl`). Date
2026-09-23 IST. Headless only. A and B agreed (see `_TWIN_AGENTS.md`) that B finalises this
group's `COVERAGE.json` and `census/raw/surf-composer-chat.json`, merging A's rows/findings.

## Rig

- Sidecar `127.0.0.1:52217`, source run, data dir `$SCRATCH/vysted-iso/seat-composer-chat/data`
  (cp -R of `$SCRATCH/vysted-iso/data`, keyless `dev-keystore.json` seed). 07:15-07:54 on A's
  process (sleep 95299 / worker 95300, MCP env `:52153/:52154`); A's processes stopped ~07:54, so
  B booted its own (07:57, MCP pair `:53217/:53218`); that set died ~08:04 (not by B — cause
  unknown), B re-booted at 08:05:41. Current pids: `$SCRATCH/vysted-iso/pids-surf-S2A-B.json`.
- Client `$SCRATCH/s2a/drive.py`: posts `/agents/{id}/invoke` with EXACTLY the body
  `src/modules/chat/streaming.ts:155-178` builds (prompt, `context_snapshot{focused_source,
  by_source.__terminal__, captured_at}`, provider, model, mode, autonomy, `options{history,
  deepResearchBackend, research_depth}`) plus the `X-Vysted-Region`/`X-Vysted-Research-Tier`
  headers (`streaming.ts:191-203`). History = last 10 prior user/assistant turns
  (`ChatSidebar.tsx:749-753`). `--ack` mirrors `ackHostAction` (`src/lib/host-actions.ts:1452-1470`)
  including its early return on an empty `toolCallId` (`:1457`). Ledger rows via `vy.py`'s own
  `_budget_check`/row format (tags `s2a-cc-*`); paid calls went through `vy.py` itself.
- Frontend replay `$SCRATCH/s2a/vt/replay.s2a.test.ts` (scratch vitest config, nothing under
  `src/`): each captured SSE transcript -> real `streamAgentInvocation` (fetch mocked with the
  captured bytes) -> `applyHostAction` -> `useBriefStore` -> `deriveMetrics` / `isDivergenceNotice`.
  Pure-logic drive `$SCRATCH/s2a/vt/pure.s2a.test.ts` feeds real catalog/SSE inputs to the
  composer's pure functions (`51-pure-logic-on-real-inputs.json`).
- Local lane: ollama `llama3.1:8b`. Contended (B's parallel research/delegate runs + agent A on
  the same Ollama), so latencies are upper bounds.

Seeded evidence: `seat-retail/`, `seat-microcap/`, `agent-behaviour/`, `funnel-largecap/` are
empty; `seat-us/` never touched the composer; `seat-stranger/transcript.md` is keyless GET
probes only. Nothing to continue from — every drive below is new.

## 1. Catalog reads the composer makes on mount

| Surface | Call (as the store makes it) | Result |
|---|---|---|
| persona picker | `GET /agents` (`src/store/agents.ts:204`), `GET /custom-agents` (`:220`) | 200, 13 agents (copilot `ollama/qwen2.5:7b`, 11 personas `anthropic`, researcher `openai`), every one with the SAME 50-tool list; custom `[]` |
| model picker | `GET /llm/providers`, `GET /llm/models?provider=ollama` | 200; live ollama catalog 3 models, all capability fields `null` -> `buildModelGroups` = one flat group, `selectedIsNoTools:false` (`51-…json` `modelPicker`) |
| agents rail | `GET /runs` | 200 dual-case rows |

## 2. Multi-turn conversation (llama3.1:8b, history threaded, context snapshot attached)

| Turn | Prompt | What the model did (SSE) | Score | Evidence |
|---|---|---|---|---|
| 1 | "What does Cochin Shipyard do, and what's its current share price, P/E and market cap?" (ask) | `research{depth:quick}` -> auto `publish_brief` (`__autobrief`) | **partial** — price ₹1388.9 / P/E 53.6 / mcap ₹36,539 cr match the bundle and `GET /quotes/COCHINSHIP`; "revenue growth of **0.024%**, earnings growth **-0.193%**" = fractions 0.024/-0.193 read as percent (true 2.4% / -19.3%) | `10-multiturn-t1.*` |
| 2 | "How does it compare with Mazagon Dock on valuation — which one is cheaper?" | `compare_symbols{[COCHINSHIP, MAZAGONDOCK]}` | **partial** — "it" resolved from history; invented ticker (real `MAZDOCK`), tool does not resolve names, answer blames "no current quote" | `11-multiturn-t2.*` |
| 3 | "Add both of them — Cochin Shipyard and Mazagon Dock — to my watchlist." (auto) | 2x `add_to_watchlist`, `tool_call_id: ""` | **broken (half)** — replay: "Added MAZAGONDOCK to your watchlist" (dead ticker applied); both acks impossible (empty id) -> narration "pending confirmation" for an auto-applied change; `GET /quotes/MAZAGONDOCK` -> 502 raw yfinance AttributeError, batch silently drops it | `12-multiturn-t3-watchlist.*`, `replay-turns-1-4.json` |
| 4 | "Write a note on Cochin Shipyard: valuation looks stretched at ~54x trailing P/E; revisit after Q2 results." (auto) | NO tool call: `{"name": "write_note", "parameters": {...}}` emitted as one `delta` (2/2) | **broken** — root cause: `classify_intent` = `read` (no cue) so the runtime stripped `write_note` from the 50 tools before the call (`52-intent-gate-probe.txt`: 37 tools sent, `write_note=False`); the model, offered no such tool, typed it as JSON; no leak rescue on Ollama either | `13-*`, `13b-*`, `52-intent-gate-probe.txt` |
| 5 | "screen for Indian defence and shipbuilding stocks with P/E below 60 and market cap above 10000 crore" (= the composer's `/screener` expansion, `slash-commands.ts:188`) | `screener_run` with `criteria`/`group` JSON-STRINGS -> validation error (`mcp_call` replay: "Input should be a valid list"), then a second `screener_run` leaked as text | **broken** — read intent again: `write_screener_filters` (the tool the copilot prompt names for "Screen for …") was stripped; no screen authored | `14-multiturn-t5-screen.*` |
| 6 | "Arrange my workspace to compare Cochin Shipyard and Bharat Dynamics side by side" (auto) | `arrange_layout{pattern:compare, symbols:[COCHINSHIP,BDL]}` | **partial** — correct call (build intent); ack skipped (empty id) so model said "pending confirmation"; the apply itself needs a mounted dockview (`host-actions.ts` arrange branch returns null with no `dockviewApi`) — not headlessly provable | `16-multiturn-t6-arrange.*`, `replay-turns-5-6-ask-stop.json` |

Extra single turns:

| Drive | Result | Score | Evidence |
|---|---|---|---|
| ASK autonomy: "Pull up Bharat Dynamics on the chart and add the RSI indicator" | `set_chart_symbol{BDL}` (runtime result = `awaiting_user_review`, "do not claim it is done") — model: "**I've set** Bharat Dynamics (BDL) as the new symbol on your chart", then leaked `set_chart_indicators` as text | **broken** (claims a staged change done; second action lost) | `15-ask-autonomy-chart.*` |
| Persona `munger` via provider override (the persona's own default is anthropic — no key) | 0 tool calls, 700 tokens of in-role prose, ungrounded claims ("large order book", "moderate revenue growth"), ends by LISTING tools it "will dispatch" — none dispatched | **partial** | `17-persona-munger.*` |
| Compound plan (gpt-4o-mini, $0.0014): "Open the chart and the watchlist, then pull up Bharat Electronics and add it to my watchlist" | `agent_plan` 4 steps (args `{}` on every step), then `set_chart_symbol{BEL.NS}` + `add_to_watchlist{BEL.NS}`; replay applies both ("Loaded BEL.NS into the chart", "Added BEL.NS to your watchlist"); narration "I've proposed…" (honest for ASK) | **ok** (plan args empty — cosmetic) | `18-plan-compound-4omini.*`, `replay-plan-and-error.json` |
| Raw chat path `/llm/chat` (no agent — `streamChat`, `ChatSidebar.tsx:1028`) with 2 prior turns | "Cochin Shipyard, your favorite." — history honoured | **ok** | `19-raw-chat-history.sse` |
| Agent A `conv1-t1` | `get_terminal_state` read back the snapshot correctly ("focused on the chart for KEI (1d, sma20)… watchlist KEI, DIXON, TRENT") | ok (context badge / snapshot path) | `conv1-t1.stdout.txt` |

## 3. Error frames (chat error row)

`20-err-nokey-openai.*`, `21-err-edges.txt`, `replay-plan-and-error.json`:
- no key on a key provider -> frame `{message: "Something went wrong with the AI provider.", action:
  "Try again or switch provider in Settings.", detail: "Missing credentials…", code: "unknown"}`;
  `errorFrameOf` carries action/detail/code to the Details disclosure. (The composer blocks this
  case before sending — `ChatSidebar.tsx:786-792` — so the frame is only reachable on a resumed
  delegate run.) Unknown agent -> 404; bad provider/mode or camelCase `apiKey` -> 422 with
  pydantic detail (`streaming.ts:216-219` shows that raw text — COD-error-layer-2 already).

## 4. Delegate runs (agents rail / budget config / run store)

`30-delegate-launch.txt`, `31-delegate-lifecycle.txt`:
- A (`max_tokens 2000`) -> `error` "token ceiling 2000 reached (10126 used)" (honest, 5x overshoot
  — COD-runs-durable-delegate-3); transcript ends at the partial "It".
- B cancelled at t+8 s -> `cancelled`; `POST /runs/{B}/answer` -> 409 "not awaiting an answer";
  nothing in the product can put a run in `paused` (`run_manager.pause_run` has no caller —
  COD-runs-durable-delegate-10), so the rail's answer box is unreachable.
- C (all-null budget, what a cleared budget field sends) -> accepted 201, ran unbounded, `done`
  (COD-runs-durable-delegate-12 / COD-frontend-panels-agent-shell-7).
- `POST /runs/{A}/resume` on the llama run -> the resumed run loaded **Qwen2.5 7B** (ollama log
  07:46:58 "starting runner … general.name = Qwen2.5 7B Instruct … evicting a model") — resume
  drops the user's model (COD-runs-durable-delegate-2, now live). Cancelled at 07:47:57.

## 5. Stop mid-stream (the composer's stop square)

`40-stop-midstream.*` + `40-stop-midstream-watch.txt`: deep research prompt, client closed the
HTTP connection at 170.0 s (07:51:00, during research round 1). Sidecar pid 95300 afterwards:
3 ESTABLISHED connections to Ollama until 07:51:35 and 1 until 07:54:06; HTTPS connections rose to
11 at 07:51:05 and again to 9 at 07:53:07 (web research); Ollama GIN log shows `/api/chat`
calls finishing at 07:51:33, :35, :53, 07:52:00, 07:53:00, 07:54:06 — the research tool kept
running ~3 min with no client. Mechanism: `_dispatch_tool_with_progress` runs the tool as
`asyncio.create_task(_run())` and its `finally` never cancels it
(`sidecar/services/agent_runtime.py` `_dispatch_tool_with_progress`), matching
COD-agent-runtime-4 (code-read) — now proven live.

## 6. Pure composer logic on real inputs (`51-pure-logic-on-real-inputs.json`) + unit tests

- collapse ladder: 220/300 -> icons, 360 -> compact, >=420 -> full. Depth cycle normal->deep->ultra->normal.
- plus-menu: Context(@chart,@news,@filings,@terminal) / Scope(@watchlist,@portfolio) / Route to(@analyst,@quant).
- mentions: `@analyst is BDL cheap vs peers?` -> "[Act as a fundamental analyst] is BDL cheap vs peers?"
  (and that prompt still classifies `read`).
- slash: `/` lists 10; `/screener defence stocks P/E < 40` -> "screen for defence stocks P/E < 40"
  (classified `read` -> `write_screener_filters` stripped, `52-intent-gate-probe.txt`); `/BDL` -> null.
- queue: queue 3, remove index 1, consume -> head "first", rest ["third"] (FIFO correct).
- divergence chips: `isDivergenceNotice` on the runtime's three copies (`agent_runtime.py`
  `_publish_divergence_notices`): no-ack **true**, kept_previous **false**, failed **false**.
- markdown: 232 real t1 frames, no open-fence state; the leaked tool call renders verbatim as
  prose `{"name": "write_note", "parameters": {...}}`.
- `formatElapsed(3_725_000)` -> "3725s".
- Existing unit tests for these surfaces, one vitest run, 22 files / 269 tests pass
  (`50-existing-unit-tests.log`; files listed in `$SCRATCH/s2a/vt/existing-tests.txt`).

## 7. Data spot-check (screener.in, `curl` 2026-09-23)

KPITTECH: price 529, mcap ₹14,504 cr, div yield 1.42% — the brief panel (replay) renders
"INR 144.02B", "Dividend yield 1.42%"; the chat said "₹1.44 **lakh crores**" and "**0.0142%**"
(`../research-briefs/10-normal-kpit.stdout.txt`). The derived bundle ships
`dividend_yield: {value: 0.01417…, unit: "percent", basis: "fraction of price"}`.

## Spend

Local/keyless except two gpt-4o-mini calls on this group (`18-plan…` $0.0014) — ledger tags
`s2a-cc-*`.
