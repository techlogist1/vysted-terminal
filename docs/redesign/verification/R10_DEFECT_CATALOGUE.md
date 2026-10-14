# R10 Defect Catalogue — the engine layer

Every operator-reported failure, root-caused with file:line evidence. Phase-0 live/static
repro stamps are inline. Fix ownership maps to the five R10 teams.

## E1 — Wrong-entity resolution (Reliance→RECX, RELIANCE.NS→RPOWER)

**Root cause (REPRODUCED STATICALLY, 2026-06-11):** whole-query fuzzy matching. The
resolver (`sidecar/services/symbol_resolver.py`) fuzzy-scores the ENTIRE query string
against company names with a `SequenceMatcher` floor of 0.6 (`_MIN_NAME_SCORE`), and the
research target binding (`services/research/target.py`) accepts anything ≥ 0.5
(`CONFIDENCE_FLOOR`) — while the agent-facing path disambiguates at 0.72
(`DISAMBIGUATION_THRESHOLD`). Three gates, one resolver, two truths. Live probes on the
shipped masters:

| Query | Bound | Score |
| --- | --- | --- |
| `Reliance Q4 results` | FRLCY · Freelancer Ltd (US) | 0.686 |
| `Reliance Industries Q4 FY26 results` | LNKS · Linkers Industries Ltd (US) | 0.712 |
| `research Reliance` | REFR · Research Frontiers Inc (US) | 0.798 |
| `reliance industries quarterly results` | LNKS (US) 0.690 — beats RELIANCE NSE 0.688 | 0.690 |

RECX = "Recreatives **Industries**, Inc." in `us_instruments.json` — the same class
(SM("reliance industries", "recreatives industries, inc.") = 0.638 ≥ 0.6). RPOWER =
"Reliance Power Limited" (NSE) — a legitimate fuzzy match for Reliance-led salads. The
model authors keyword-salad research queries; the tool binds the salad; the model's own
narration uses its world knowledge — that is the "two organs disagree" symptom.

**LIVE on the running sidecar (Phase 0):** `GET /resolve?q=research%20Reliance` →
`resolved: REFR "RESEARCH FRONTIERS INC", confidence 0.7979, needs_disambiguation:
false, region: "US"` — the endpoint BINDS a US ETF-adjacent micro-cap for a phrase any
user would type, with the region defaulted to US on this install. Candidate 2 was RACC
"Research Alliance Corp III". The Q4-salad query ranked LNKS above RELIANCE live.

Aggravators: `resolve()` defaults `region` to US (symbol_resolver.py:336) with a +0.08
ADDITIVE locale bonus, so a US prefix-band match (0.92+0.08=1.00) can outrank an NSE
first-word match (0.97); `_live_lookup` (yfinance) ignores region and returns the first
hit at 0.6 ≥ the research floor; the prefix fallback tries 4→3→2 words, never 1, so
`RELIANCE.NS <anything>` queries resolve NONE on the full string and never try the bare
ticker; Tier B research (`deep_research.run_research_model_brief`) does ZERO resolution —
`ResearchBrief(symbol="")`, entity identity is the hosted model's prose.

Also confirmed: "Tata" → TCS and "Bajaj" → BAJFINANCE bind silently at a CLAMPED 1.0
(0.97 first-word + 0.08 bonus, clamp hides the uncertainty) — marquee families never
disambiguate.

**Fix:** Team RESOLVE — one acceptance policy (≥0.72 bind / 0.5–0.72 disambiguate /
<0.5 unresolved), band-then-locale tie-break (never additive), IN-first region default,
marquee alias/disambiguation table, region-aware live lookup capped at disambiguate,
1-word prefix fallback at first-word band, Tier B binds the same target pre-dispatch.

## E2 — DEEP run stamped "Mode: FAST"

**Root cause:** the stamp derives from the result PAYLOAD, not the execution.
`agent_runtime._auto_publish_event` (≈:704): `raw_mode = str(payload.get("mode") or
"fast")` — any payload without `mode` stamps FAST. `fast.gather_fast` returns no mode
field. Tier B stamps `"fast" if stop == "normal" else "deep"` from the REQUESTED stop,
not what ran. Durable-run resume (`run_manager.resume_run`) rebuilds options without
`research_depth` — the ContextVar floor silently resets to NORMAL mid-conversation.

**Fix:** Team RUNTIME — `ResearchExecution` record minted at the tool boundary stamped
from the loop that RAN; auto-publish derives mode/depth ONLY from it; payload without an
execution record never auto-publishes; options persisted and re-threaded on resume.

## E3 — Stale/hallucinated brief served as current; publish claims never read back

**Root cause (three interlocking mechanisms):**
1. Briefs persist in the workspace autosave blob and restore as-if-current. Phase-0
   evidence: the LIVE blob (`__autosave__.vysted-workspace`) carries a brief with
   `query=''`, `symbol=None`, mode FAST, 5 sources — an identity-less artifact that
   re-renders on every boot. (The specific ₹2,088 Cr brief was already overwritten by a
   later publish — exactly the no-provenance problem: failed/stale artifacts leave no
   trail.)
2. `briefFromInput` (src/lib/host-actions.ts:185–210) carries `prevBrief.structured`
   forward inside a 20-second wall-clock window keyed on symbol-or-absent — across
   reloads and across entities when symbols are empty (Tier B briefs ALWAYS have empty
   symbols).
3. The autonomy=auto path synthesizes the model's tool result as "applied … tell the
   user it is done, in past tense" BEFORE the frontend runs `applyHostAction`
   (agent_runtime.py:773–800) — whose D33 shrink guard can keep the OLD brief. The agent
   then truthfully reports a publish that never landed. No read-back exists.

**Fix:** Teams RUNTIME + FRONTEND-BRIEF — brief state machine (in_flight / published /
archived-with-reason; restored blobs ALWAYS archival), run_id-scoped carry, ack ledger
(`POST /agents/actions/ack`) + end-of-stream divergence notice, TerminalState carries
brief identity, honest auto-mode narration.

## E4 — Screener: Nifty-50 loop, 5-minute hangs, universe unwired

**Root cause:** universes are three static JSONs (`sp500`, `nifty50` = 50 symbols,
`crypto-top50`) — the full NSE master (2,675 rows) and BSE master (4,873 rows) sit
unwired beside them. The Yahoo v7 batch call (`screener.py:687`) has NO timeout; the UI
awaits `/screener/run` with no client timeout and no progress channel; the agent retries
the opaque tool (the 4× "loop"). No bulk India fundamentals layer exists (sector/ROE ride
per-symbol yfinance `.info` only).

**Fix:** Team SCREENER — india universes from the masters, SQLite fundamentals cache with
per-tier TTLs, build-time sector map from BSE ListOfScripData (INDUSTRY + Mktcap are
fetched and DISCARDED by today's regenerate script), prune-then-enrich engine under a
120s wall with SSE progress + honest partials, background warming.

## E5 — "I don't have a direct backtesting tool" (regression vs R7)

**Root cause (CONFIRMED STATICALLY):** `run_custom_backtest` is registered and catalogued
but absent from `sidecar/agents/copilot.json` (37 tools; the quant four are missing too).
The D21 loader union adds only host-actions + research. No test asserts allow-list
completeness — tools fall out of the belt silently by JSON drift.

**Fix:** Team RUNTIME — catalog-driven default grant for first-party agents +
toolbelt-integrity test + agent-vs-engine backtest parity test.

## E6 — Portfolio read-only for the agent

**Root cause:** POST/PUT/DELETE `/portfolio/positions` exist (routers/portfolio.py); no
agent capability wraps them. **Fix:** Team RUNTIME (capabilities) + FRONTEND-BRIEF
(apply cases): portfolio_add/update/delete_position as `data-write` proposed changes —
auto-applicable under AUTO, NEVER touching the §6.5 order path.

## E7 — Multi-minute silent tool hangs

**Root cause:** `agent_runtime._dispatch_tool` has no timeout wrapper; screener/web/
broker tools do unbounded network work. **Fix:** Team RUNTIME — per-tool-class
`asyncio.wait_for` budgets + honest timeout messages with a next step.

## E8 — Metric semantics conflation (drawdown vs 52w-change; dividend 55%/₹1; growth bases)

**Root cause:** `deriveMetrics` (brief-blocks.tsx) renders provider fields with no basis
labels; nothing computes drawdown-from-high; `dividend_yield` vs `dividend_per_share`
never reconciled (yfinance unit chaos absorbed by a magic <25% guard); growth basis
unlabeled; the synthesis prompt receives raw numbers with no semantic contract.
**Fix:** Team RESOLVE — `services/research/semantics.py` derived leg + conflicts[] +
prompt block; FRONTEND-BRIEF renders derived cards + conflict flags.

## E9 — Naked provider JSON in chat (402, twice)

**Root cause:** every LLM adapter yields `LLMErrorEvent(message=str(exc))`
(services/llm/openai.py:793–796 et al.); `routers/agents.py:74–77` stringifies the
last-resort guard; ChatSidebar renders `message.error` verbatim. No humanization layer
exists anywhere in the app. **Fix:** Team ERRORS — `services/errors.py` classifier
(message + action + raw detail), structured SSE error frames, frontend renders human
copy + "Show details" toggle. Note: the operator's direct DeepSeek balance is EMPTY BY
CHOICE — the 402 is an expected condition to humanize, not an outage.

## E10 — Streaming line clips the VYSTED COPILOT header

**REPRODUCED LIVE (r10/phase0/01-streaming-t2.png):** mid-stream, the streamed text /
caret renders OVER the agent message's "VYSTED COPILOT" author label (the label reads
"▌YSTED COPILOT" — first glyph overdrawn), and the "● VYSTED COPILOT AGENT" streaming
status strip overlays the "CONTEXT: PORTFOLIO" row at the panel top. Once the stream
completes (02-streaming-t5.png) the layout is clean — the defect is the in-flight
layering/reserved-height of the author label + status strip. Fix in FRONTEND-BRIEF.

## E11 — Tradesa dead weight

39 files / ~1,050 lines across plugins/tradesa-v2/, sidecar provider+router+model+tests,
types, marketplace, keychain namespace. Removal owned by Team ERRORS+TRADESA; the plugin
SYSTEM must be proven alive after the strip.
