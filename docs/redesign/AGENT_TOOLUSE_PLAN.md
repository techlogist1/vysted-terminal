# Agent Tool-Use + Brief/Search (Jarvis) Layer — Audit & Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan workstream-by-workstream. Steps use checkbox (`- [ ]`) syntax for tracking. **Do not begin until the operator says "execute".**

**Goal:** Make the existing agent behave like a grounded terminal copilot (not a chatbot) and make the brief/search layer tell the truth — without touching the locked UI (`ui-locked-opencode-black`), without weakening §6.5, on version 0.8.0.

**Architecture:** This is **audit-and-extend**, not a rebuild. The agent surface, ASK/AUTO, the proposal bar, the brief (typed-block markdown + research depth tiers), and the 4-rung web-search ladder all exist and mostly work. The work is: (a) give the agent temporal grounding + a market path + truthful AUTO narration; (b) reuse the brief's renderer in chat; (c) make the brief's "web unavailable" banner reflect real evidence; (d) fix depth/export/chart-tab glitches; (e) close the OpenRouter-default search gap and the Indian micro-cap data gap; (f) make the DeepSeek-default tool loop resilient. Every fix reuses an existing seam. New OSS is adopted as **copied patterns, not dependencies**, except two flagged libs and one flagged data-source decision.

**Tech stack:** Next.js 16 static-export + React 19 + TS + Tailwind 4 + Zustand (frontend); Python 3.13 FastAPI sidecar; Tauri 2 (Rust). Provider loop is native function-calling end-to-end (OpenAI-shaped adapter serves DeepSeek/xAI/OpenRouter via `base_url`).

**Provenance of this plan:** Produced by a 65-agent read-only workflow (8 grounded audit readers + adversarial verifiers + 6 OSS researchers that cloned and read source + verifiers + synthesis/critic). Every root cause below was re-checked against the code; the adversarial pass **refuted one diagnosis and corrected four** — those corrections are baked in. Load-bearing claims were additionally hand-verified by the lead (file:line confirmed). Verdict tally: 28 confirmed / 8 partial / 1 refuted.

---

## Part 0 — Audit: what exists, what's broken, what was refuted

### 0.1 What genuinely works (do not rebuild)
- **Native function-calling loop** (`sidecar/services/agent_runtime.py` `invoke_agent`, round loop ~744–855; `_MAX_TOOL_ROUNDS=6`). Every adapter (`services/llm/{openai,anthropic,gemini,groq,ollama}.py`) builds a provider-native tool schema from the single-source catalog (`agent_tools/schemas.py`) and parses native tool-call deltas back to `LLMToolUseEvent`. **No text-parsing.** DeepSeek routes through `OpenAIProvider(base_url=https://api.deepseek.com)` and **does** send tool schemas.
- **ASK/AUTO is real and safe.** Autonomy (`src/store/agent-autonomy.ts`, `ask|auto`) auto-applies safe/reversible host-actions client-side (`src/store/proposed-changes.ts:79–81`); **orders are hard-excluded and always routed through the §6.5 confirm dialog**. The §6.5 line is intact in two layers.
- **Brief renders markdown correctly** as typed blocks (`src/modules/research/brief-blocks.tsx` `BriefBody` → `parseBodyBlocks`/`renderInline`), with live ticker chips and `[n]` citations, never fabricating a metric card (`deriveMetrics` returns null when no real leg).
- **4-rung search ladder** exists (`sidecar/services/search/{registry,exa,searxng,ddg}.py` + `llm/native_search.py`): provider-native → BYOK Exa → local SearXNG → keyless DDG floor.
- **No-data is honest at the chart** (`/history` downgrades empty to a 200 empty series; `ChartPanel` clears prior candles and shows a "No price data" + Retry overlay — not silent, not stale, not a 502).
- **NSE micro-caps work keyless** via `jugaad-data` (`services/india_provider.py`, 2675 NSE symbols), ranked above yfinance.
- **Per-model tool-capability metadata** already flows for OpenRouter (`openrouter_catalog.py` reads `supported_parameters=tools`) and surfaces in the picker.

### 0.2 Root causes (grounded, verified)

| # | Symptom | Root cause (verified) | Fix WS |
|---|---------|----------------------|--------|
| 1 | "how is the market today?" → generic chatbot answer, no tool action | **No date/time anywhere in the prompt path** (`_compose_messages` 306–320, `_render_terminal_preamble` 205–262, `copilot.json:5` — zero date) + **no forced/encouraged tool call** (no `tool_choice`) + **no market-overview path** (prompt is all per-symbol; no `market`/`movers` tool) + on the keyless default (**`ollama` qwen2.5:7b**, documented unreliable at tool-use; adapter silently retries without tools on failure) the model emits no tool call at all. | WS1 |
| 3 | AUTO says "added to the proposal bar" instead of executing | **Behavior is correct; the words are wrong.** AUTO genuinely auto-applies. But **autonomy is never sent to the sidecar** (`streaming.ts` body has `mode`, no `autonomy`), and `_make_host_action` (agent_runtime.py ~600–607) **hardcodes** `status="awaiting_user_review"` + a note: *"Tell the user you proposed this change for review; do not claim it is done."* So the model narrates "proposed for review" even when the frontend already applied it. | WS1 |
| 4 | Agent chat renders raw markdown; brief renders it | Chat `MessageBody` dumps `message.content` into `<div className="whitespace-pre-wrap">` (`ChatSidebar.tsx:169`). The brief's `parseBodyBlocks`/`BriefBody` is **not** reused. (`parseBodyBlocks`/`deriveMetrics`/`BriefBody` are exported; the block components + `renderInline` are module-private — extraction must happen **inside** `brief-blocks.tsx`.) | WS2 |
| 2 | Accurate macro section ("2 SOURCES") **and** a "web unavailable / structured-data-only" banner at the same time | **REFUTED that symbol vs macro search are different code paths.** Real cause: the banner is **brief-local** and `web_available` counts **web citations only** — `deep.py:352 web_available=bool(findings.web_sources)` (and `iter.py:594`, FAST `fast.py` web round). A run that gathered structured sources (or whose native/model search produced citations the brief never folded in) shows "N sources" **and** fires the banner. Plus the FAST `_NO_WEB_NOTE` says "no backend configured" even for a transient DDG rate-limit (DDG zero-hit returns `ok:True`; only a `SearchError`/202/429 returns `ok:False`), and `web.note`/`web.detail` are stranded (never read by `_auto_publish_event`). | WS3 |
| 5 | After a deep report, "GO ALL OUT" still shows | The hide logic is correct (hidden only when `depth==='heavy'`). But a **model-issued `publish_brief` clobbers `depth`**: `briefFromInput` (`host-actions.ts:91`) carries `structured` forward across a re-publish but **not `depth`**, and the `publish_brief` schema has no `depth` param (only `mode` FAST/DEEP) — so a re-publish collapses `heavy→deep` ("Go all out" reappears) or `→quick` ("Go deeper" reappears). | WS4 |
| 6 | Export MD/PDF unreliable, unclear content, truncated path | MD compose is pure and reliable. PDF/PNG rasterize **mid framer-motion entrance** (faded/partial), the raster ref **excludes the Sources tray** (PDF ≠ MD content), the PNG bg is a **stale `#1a1814`** (panel is `#161616`), and the saved-path status uses `truncate` (full path only on hover). | WS4 |
| 7 | Duplicate "Chart"/"chart" tabs | **Not** a casing-differing registration (one module registration). Two creation paths coexist: literal id `chart` from `default-layout.ts:33` + `layout-templates.ts:28,114`, vs a freshly-minted `chart-<ts>-<rand>` from `openPanel('chart')` because the chart is **`singleton: false`** (an abandoned Phase-2 multi-chart flag). Command-palette "Open Chart" mints a duplicate every click. | WS4 |
| — | OpenRouter/DeepSeek default route has **no native search** | `native_search.py:49 SUPPORTS_NATIVE_SEARCH = {anthropic, openai, gemini, groq, xai}` — the two **defaults** (OpenRouter, DeepSeek) are absent, so the keyless default falls all the way to the fragile DDG scraper. Native-search is gated per-**provider**, which is wrong for OpenRouter (capability is per-**model**). | WS5 |
| — | yfinance returns empty for `.NS`/`.BO` | `get_quote`/`get_history` use `_normalize_symbol` (dot→dash) instead of the region-aware `_yahoo_symbol`, so `RELIANCE.NS`→`RELIANCE-NS` (the all-dashes form Yahoo 502s on). The mapper was retrofitted onto fundamentals/statements but **not** quote/history. | WS6 |
| — | BSE-only micro-caps have **no** keyless source | `jugaad-data` is NSE-only; `.BO` falls through to the (mangled) yfinance path. | WS6 |
| — | DeepSeek-default tool loop has reliability gaps | Malformed tool-args silently coerced to `{}` (no validation/repair), no rescue when a model leaks a tool call as text (a documented DeepSeek bug), no transport retry (one 429 kills the stream), and `deepseek-reasoner` needs `reasoning_content` echoed on multi-round turns. | WS8 |

### 0.3 Refuted / corrected during adversarial verification (do not act on the original wrong theory)
- **REFUTED:** "symbol search and macro search are disjoint paths." Both FAST (`research.py`) and DEEP (`deep_research.py`) dispatch `web_search` through `agent_tools.invoke_tool` regardless of tier; the native-tier bypass only withholds `web_search` from the **model's chat-loop allow-list**, never from the research tool. The banner is brief-local, not a path-disjointness artifact. → WS3 is built on the corrected cause.
- **CORRECTED (partial):** "the read-only gate causes the no-tool-action symptom." The gate (`agent_runtime.py:667–678`) **does** strip panel-driving host-actions on a read intent (a real bug: a read-*safe* action like opening the index chart is forbidden) — but it does **not** strip data/search tools, so it is **not** why zero tools fired. The no-tool-action symptom is the date/forcing gap + the weak local model. → WS1 loosens the read gate for read-safe panel actions **and** adds date/market grounding; it does not pretend the gate was the whole story.
- **CORRECTED:** the banner's transient-vs-no-backend conflation (DDG zero-hit is `ok:True`, not `ok:False`) and the web-citations-only flag at `deep.py:352` are the actionable defects — not a generic "empty" conflation.
- **CORRECTED:** `renderInline` and the block components are **not** exported (only `parseBodyBlocks`/`deriveMetrics`/`BriefBody`). The shared `MarkdownBody` must be extracted and exported from **inside** `brief-blocks.tsx`.
- **CORRECTED:** `BseIndiaApi` is **keyless** (not key/self-host); the only blocker is GPL-3.0 vs AGPL-3.0 + commercial (a linking/relicense question), which is why WS6 reimplements the trivial bhavcopy logic under AGPL.

---

## Part 1 — OSS prior-art recommendations + every flagged dependency/decision

All candidate repos were cloned into a scratch dir and read at the source level (not READMEs). License compatibility was independently verified against AGPL-3.0 **+ the commercial dual license**.

### 1.1 Recommendation table

| Need | Recommendation | License | New runtime dep? | Keyless-first? |
|------|---------------|---------|------------------|----------------|
| Reliable DeepSeek/OpenRouter tool loop | **Copy** `vercel/ai` `parse-tool-call.ts` validate-and-repair pattern + header-aware backoff | Apache-2.0 | **No** (reuse `jsonschema` + `oneshot.complete`, both present) | Yes |
| Weak/local (qwen) tool fallback | **Copy** `litellm` `function_call_prompt()` text-mode pattern (~15 lines) | MIT | **No** (do **not** import litellm) | Yes |
| Always-on search for the **default** route | Add **`openrouter:web_search`** server tool rung | hosted (no code) | No (request-shaping) | Yes — rides the key the user already has |
| Harden the keyless floor | **Copy** `nickclyde/duckduckgo-mcp-server` token-bucket rate-limiter; optional `curl_cffi` TLS-impersonation | MIT | rate-limiter **No**; `curl_cffi` **flagged** | Yes |
| Chat markdown | **Reuse** in-repo `brief-blocks` + **port** `vercel/streamdown` `remend` incomplete-token logic (~60–80 lines) | AGPL (own) + Apache-2.0 | **No** (do **not** adopt streamdown/assistant-ui) | Yes |
| Keyless BSE micro-cap data | **Reimplement** the BSE bhavcopy + StockReachGraph fetch under AGPL (idea-level, ~25 lines), modeled on `BennyThadikaran/BseIndiaApi` | (reimpl AGPL) | **flagged** | Yes |
| Per-model capability metadata | **Extend** existing `openrouter_catalog.py` to parse `supported_parameters`/`pricing` from OpenRouter `/api/v1/models` | hosted (no code) | **No** | Yes (public `/models` needs no key) |
| BSE intraday/realtime upgrade | **Kite/Upstox** historical via the existing read-only broker seam (`*_info` duck-type) | MIT client / proprietary API | opt-in only | No (BYOK upgrade) |
| External MCP "control plane" (exposing panels as agent tools) | **Defer** — Tier-4; if ever built, use bundled FastMCP `ctx.elicit()` + propose-not-apply, study OpenBB's AGPL discovery layer | Apache-2.0 / AGPL-3.0 | No | Yes |

### 1.2 FLAGGED DECISIONS — operator must choose (defaults in **bold**)

> These are surfaced, not baked in. The build will use the **bold** default unless you say otherwise.
>
> **Operator decisions locked (2026-06-09):** #3 BSE → **reimplement under AGPL**; #4 read-gate → **allow read-safe panel actions**; #5 → **add `market_overview` read_handler tool**; #7 export → **replace with Copy-markdown**. Decisions #1, #2, #6, #8, #9, #10 stand at their bold defaults unless changed.

1. **OpenRouter `web_search` cost.** Enabling the default-route search rung bills the user's **existing** OpenRouter key ($0.005/≤10 results + $0.001/extra). No new credential, but it is per-search spend. **Default: enable it and surface the per-search cost in the existing cost-preview UI before a search fires.** (Pricing/`:online`-deprecated taken from OpenRouter docs, not source — could drift; the build will re-confirm at implementation.)
2. **`curl_cffi` (TLS-impersonation) for the DDG floor.** Beats the one DDG failure mode `httpx` can't (403/Cloudflare TLS fingerprint), but is a new sidecar binary dep that ships a bundled libcurl → must pass the PyInstaller `--onefile` ≤120 MB audit + smoke-test. **Default: ship the proactive token-bucket rate-limiter only (no new lib); defer `curl_cffi`.**
3. **Keyless BSE source.** `BseIndiaApi` is GPL-3.0; merging GPL into the AGPL + **commercial** dual-licensed codebase is a licensing conflict (Tier-4). **Default: reimplement the ~25-line bhavcopy download + parse under our own AGPL** (the URL/CSV shape is idea-level, mirrors how public-domain jugaad is vendored). Alternative: carry `BseIndiaApi` as a separate isolated process. **Block on operator sign-off either way (Tier-4 licensing).**
4. **Read-gate loosening (safety-adjacent).** Today a read-intent turn strips **all** mutating host-actions, so the agent can't open the index chart to ground a market answer. **Default: allow a small allow-list of read-**safe** panel actions (`open_panel`, `set_chart_symbol`, `set_chart_indicators`, `arrange_layout`, `add_to_watchlist`) on read intents; `propose_order` stays excluded.** This touches the §6.5-adjacent gating logic — **operator sign-off required.**
5. **New `market_overview` agent tool.** Fixes "how's the market today" with a first-class path (resolve indices → quotes → market news → synthesize). Adds a catalog `Capability` → bumps the roster count asserted by `test_capability_catalog`/`test_mcp_catalog_parity` and projects to the MCP surface. **Default: add it as a `read_handler` (SAFE-auto), with parity tests updated.** Alternative: prompt-only branch using existing `price_data`/`news` (less reliable). 
6. **Thread `autonomy` to the sidecar.** Additive field on `AgentInvocationRequest`; lets `_make_host_action` narrate truthfully. **Default: thread it.** Not the plugin contract; low blast radius. (Safety check baked into WS1: the `applied` narration branch is for **non-order** host-actions only; `propose_order` keeps `awaiting_user_review` in every mode.)
7. **Export vs Copy-markdown.** Operator's stated preference: replace MD+PDF with a single **"Copy markdown to clipboard"** unless export is genuinely needed. **Default: replace both buttons with Copy-markdown** (reuses the already-reliable `composeBriefMarkdown`, kills the PDF mid-animation/Sources/bg/path bugs at the root). Alternative: keep + fix export (await settle, include Sources, fix bg, show full path). 
8. **Pending-proposal persistence.** A half-reviewed batch is lost on reload (in-memory store). **Default: leave ephemeral for v0.8.0** (a reload-loss glitch, not a correctness bug), note in `CHANGELOG.md`. Alternative: persist to the workspace blob.
9. **Optional BYOK search rung (Tavily).** Finance-friendly recency filters, free 1k/mo. **Default: defer; Exa stays the BYOK default.** Brave killed its free tier (Feb 2026) — not a floor.
10. **External MCP control-plane.** Researched (operator asked to evaluate MCP for exposing panels/data/actions). **Default: defer (Tier-4).** Orthogonal to the 7 symptoms; would widen the §6.5 boundary. Safe design documented in Part 4 if you want it later.

### 1.3 New dependencies summary (explicit)
- **No new runtime dependency is required** for WS1–WS5, WS8, or the search/capability work — all are copied patterns or reuse of `jsonschema`, `oneshot.complete`, the existing `SearchBackend` seam, and the OpenRouter catalog fetch already in place.
- **`curl_cffi`** — flagged, **default deferred** (Decision 2).
- **BSE provider** — **reimplemented under AGPL, zero new lib** is the default (Decision 3); a 5-line token-bucket replaces `mthrottle`.
- **Optional/deferred:** `streamdown`, `assistant-ui`, `react-markdown`, `litellm`, `Tavily`, `BseIndiaApi`, broker historical libs — none adopted by default.

---

## Part 2 — Safety boundary (must hold in every workstream)

- **AUTO auto-runs SAFE / REVERSIBLE tools only:** data reads, navigation/layout, chart/watchlist host-actions, date/time, briefs, screeners, `market_overview`, broker **GET** reads. These already auto-apply client-side; the only change is **truthful narration**.
- **ALWAYS require explicit human confirmation, regardless of ASK/AUTO:** orders, broker writes, fund moves, settings/key changes, destructive actions.
- `propose_order` is **excluded from the AUTO auto-apply branch** (`proposed-changes.ts:79`) **and** `accept()` routes it through the §6.5 confirm-before-place dialog. The agent never has a path to `confirm_and_place`. **This stays true after autonomy-threading** (WS1's `applied` status branch is gated to non-order host-actions; the `propose_order` branch in `_make_host_action` keeps `awaiting_user_review` in all modes).
- **§6.5 stays 9/9, untouched:** append-only audit log + triggers, kill-switch (Rust + Python), type gate + grep audit, read-only broker wrappers. `test_safety_end_to_end.py` must stay green.
- **Tier-1 / sign-off-only files are not edited by default:** `types/plugin.ts`, CI workflows, `tauri.conf.json`, licensing, `CLAUDE.md`. The only safety-adjacent change (read-gate loosening, Decision 4) is **blocked on operator sign-off**.
- **No merge to main.** Work stays on `004-r4-experience-rebuild`. UI is locked (`ui-locked-opencode-black`) — no visual redesign; reuse existing tokens/components.

---

## Part 3 — Workstreams (build order)

Each workstream is independently shippable and testable. Recommended order WS1 → WS8; WS1–WS5 are no-dep and high-value, WS6–WS8 are heavier.

### WS1 — Grounding + truthful AUTO ("copilot, not chatbot") — fixes #1, #3

**Files:**
- Modify: `sidecar/services/agent_runtime.py` (`_compose_messages` ~306–320; `_render_terminal_preamble` ~205–262; `_make_host_action` ~591–612; read-gate ~667–678)
- Modify: `sidecar/models/agent_invocation.py` (or wherever `AgentInvocationRequest` is defined — grep `class AgentInvocationRequest`)
- Modify: `src/modules/chat/streaming.ts` (~59–77 invoke body)
- Modify: `sidecar/agents/copilot.json` (`systemPrompt`)
- New tool: `sidecar/services/agent_tools/market_overview.py` + register in `agent_tools/catalog.py` (Decision 5)
- Tests: `sidecar/tests/test_agent_runtime.py`, `sidecar/tests/test_capability_catalog.py`, `sidecar/tests/test_mcp_catalog_parity.py`

- [ ] **Step 1 — Inject server date + stale directive into the context preamble.** In `_compose_messages` (or `_build_context_preamble`), prepend a system-level line built from the server clock (Python 3.13: `from datetime import datetime, timezone` → `datetime.now(timezone.utc)`). Render the user's session region/locale if available. Text:
  ```
  Current date: {YYYY-MM-DD} ({weekday}). Session locale: {region}.
  Your training data is STALE. For anything time-sensitive ("today", "now",
  "latest", "current", "this week", a price, market state, or breaking news)
  you MUST call a tool to fetch live data before answering — never answer from
  memory. If you cannot fetch it, say so plainly; do not invent specifics.
  ```
  Keep it terse; it is one preamble line group, not a rewrite.
- [ ] **Step 2 — Add a market-overview path.** Add `market_overview` as a `read_handler` Capability in `catalog.py` (Decision 5): resolves the user's locale indices (US: `^GSPC`/`^IXIC`/`^DJI` + `SPY`/`QQQ`; IN: `^NSEI`/`^BSESN`), fetches quotes via the existing `price_data` provider path, pulls symbol-less market news (`news_tool` supports an empty `symbols` list), and returns a structured `{indices:[...], movers?:[...], headlines:[...]}` dict. Register the handler in `agent_tools`, add the `Capability` (auto-projects to `TOOL_SCHEMAS` + allow-list + MCP), and add `market_overview` to `copilot.json`'s `tools`. Update the roster/parity test counts.
- [ ] **Step 3 — Copilot prompt: add a market branch + honesty rule + autonomy-aware narration.** In `copilot.json` `systemPrompt` add: (a) "For a broad market-state question ('how's the market today', 'what moved') call `market_overview` first, then synthesize — do not answer from memory."; (b) "An empty quote/result for ONE obscure instrument is a coverage gap for THAT symbol, not a feed/search outage — say 'no data for X', never 'search is down'."; (c) autonomy-aware: "If auto-apply is on, the change is ALREADY applied — say so in past tense ('Opened the SPY chart'). If review mode is on, it is staged in the proposal bar for the user's accept. ORDERS always require the user's explicit confirmation."
- [ ] **Step 4 — Thread `autonomy` to the sidecar (Decision 6).** Add an optional `autonomy: Literal["ask","auto"] | None = None` field to `AgentInvocationRequest`. In `src/modules/chat/streaming.ts` add `autonomy: payload.autonomy` to the invoke body (read from `useAgentAutonomyStore`). Pass it through to `_make_host_action`'s closure.
- [ ] **Step 5 — Truthful host-action narration (non-orders only).** In `_make_host_action`, branch on the threaded autonomy **for non-order tools only**:
  ```python
  if tool_id == "propose_order":
      # UNCHANGED — orders always staged, every mode.
      return {"ok": True, "proposal_created": True,
              "status": "awaiting_user_review",
              "host_action": {"type": tool_id, "args": args}}
  if autonomy == "auto":
      return {"ok": True, "status": "applied", "applied": True,
              "note": "Applied immediately (auto-apply is on). Tell the user it is done, in past tense.",
              "host_action": {"type": tool_id, "args": args}}
  return {  # ask / unknown → current behavior
      "ok": True, "status": "awaiting_user_review", "staged_for_review": True,
      "note": "Staged in the user's review queue — applies only after they accept it. "
              "Tell the user you proposed this change for review; do not claim it is done.",
      "host_action": {"type": tool_id, "args": args}}
  ```
- [ ] **Step 6 — Loosen the read-gate for read-safe panel actions (Decision 4, sign-off-gated).** In the read-only filter (~667–678), keep `propose_order` stripped on a read intent but **retain** a small allow-list (`open_panel`, `set_chart_symbol`, `set_chart_indicators`, `arrange_layout`, `add_to_watchlist`) so a read question can still ground the index chart. Do not land this step without operator sign-off.
- [ ] **Step 7 — Tests.** `test_agent_runtime`: the composed messages contain a "Current date:" line; an `autonomy="auto"` host-action returns `status="applied"`; `propose_order` returns `awaiting_user_review` even with `autonomy="auto"`; a read-intent turn retains the panel allow-list but not `propose_order`. Update `test_capability_catalog`/`test_mcp_catalog_parity`/`test_agents_router` for the new tool + roster count. Run: `ruff format sidecar && ruff check sidecar && pytest sidecar/tests/test_agent_runtime.py test_capability_catalog.py test_mcp_catalog_parity.py -q`.
- [ ] **Step 8 — Commit.** `feat(agent): temporal grounding, market_overview path, truthful AUTO narration`

> **Note on the keyless default (Decision 1 context):** even with WS1, the `ollama` qwen2.5:7b default under-invokes tools. WS1 makes the failure *honest* (date + market branch + "say so if you can't fetch"). The deeper fix is the tool-loop resilience in WS8 and/or steering the default to a tool-capable provider — surfaced, not silently changed.

### WS2 — Reuse the brief renderer in chat — fixes #4

**Files:**
- Modify: `src/modules/research/brief-blocks.tsx` (extract + export `MarkdownBody`; add a `code` block kind)
- New: `src/lib/markdown-stream.ts` (ported incomplete-token completer)
- Modify: `src/modules/chat/ChatSidebar.tsx` (`MessageBody` ~154–187)
- Tests: `src/modules/research/brief-blocks.test.ts`, a new `src/lib/markdown-stream.test.ts`

- [ ] **Step 1 — Extract `MarkdownBody` inside `brief-blocks.tsx`.** Pull the `blocks.map(...)` render loop (the heading/paragraph/list/table switch) into an **exported** `export function MarkdownBody({ source, known, onCite }: { source: string; known?: Set<string>; onCite?: (n: number) => void })`. It calls the existing private `parseBodyBlocks(source)` + the private block components + `renderInline` (all in scope inside this file). `BriefBody` then renders `<MetricsBlock/> + <MarkdownBody source={brief.markdown} known={knownTickersOf(...)} onCite={onCite}/>` — behavior unchanged for the brief.
- [ ] **Step 2 — Add a fenced-code block kind.** Extend `parseBodyBlocks`: a line matching `/^(```|~~~)/` opens a fenced block; buffer until the matching close; emit `{kind:'code', lang, text}`. Render in a `<pre><code>` using existing `charcoal` mono classes (no Shiki — Decision deferred). Add the type to the `BodyBlock` union.
- [ ] **Step 3 — Port the streaming incomplete-token completer.** New `src/lib/markdown-stream.ts` with pure functions ported from `vercel/streamdown`'s `remend` (~60–80 lines, Apache-2.0, attributed): `completeIncomplete(text)` closes a dangling `**`/`*`/`` ` `` at end-of-buffer and appends a synthetic closing fence when `hasIncompleteCodeFence(text)` (walk CommonMark fences). No dependency.
- [ ] **Step 4 — Swap chat `MessageBody` to render markdown.** Replace the `whitespace-pre-wrap` div with `<MarkdownBody source={completeIncomplete(shown)} known={chatKnownSet} />` where `chatKnownSet` = the watchlist symbols (`useSymbolsStore`) so ticker chips fire only on `$CASHTAG` or known symbols (empty Set is fine; never a bare uppercase word). Pass a no-op `onCite` (chat has no source rail) — verify `[n]` chips render inert, not broken. **Preserve** the existing `briefPublished` collapse-to-`firstSentences` affordance and the pulsing `▋` caret (caret on the last block only, suppressed inside an incomplete fence).
- [ ] **Step 5 — Tests.** `markdown-stream.test.ts`: unclosed `**`, half a table, and an open ``` are completed; complete input is unchanged. `brief-blocks.test.ts`: `MarkdownBody` renders headings/lists/tables/code; `deriveMetrics(undefined)===null` (chat path renders no metric grid). Run: `pnpm vitest run src/lib/markdown-stream.test.ts src/modules/research/brief-blocks.test.ts`.
- [ ] **Step 6 — Commit.** `feat(chat): render assistant markdown via shared MarkdownBody (reuse brief renderer)`

### WS3 — Honest web-search banner + per-section provenance — fixes #2

**Files:**
- Modify: `sidecar/services/research/{deep.py:352, iter.py:594, fast.py}` (`web_available` derivation + note forwarding)
- Modify: `sidecar/services/agent_runtime.py` (`_auto_publish_event` ~527–548 — forward `web.note`/`web.detail`)
- Modify: `src/lib/host-actions.ts` (~134–136 `briefFromInput` web_available default + source-count reconciliation)
- Modify: `src/modules/research/BriefPanel.tsx` (~442, 487–497 banner copy)
- Modify: `sidecar/services/search/ddg.py` (distinguish transient vs no-backend), `agent_tools/web_search.py`
- Tests: `sidecar/tests/test_research_*.py`, `src/store/brief.test.ts`

- [ ] **Step 1 — `web_available` reflects all web evidence, reconciled with source count.** In `deep.py:352` and `iter.py:594`, set `web_available = bool(findings.web_sources) or source_count > 0` — a brief that cites N sources cannot also claim "structured-data-only". In `briefFromInput` (`host-actions.ts:134–136`), tie `webAvailable` to actual source count when the model omits it (don't default-true a real outage; don't false-flag a sourced brief). Fold native-search/`publish_brief` citations into the source set the flag reads.
- [ ] **Step 2 — Distinguish transient from no-backend.** In `ddg.py`, surface a typed reason on `SearchError` (rate-limit/202/429 vs transport). Replace the canonical `_NO_WEB_NOTE` ("no backend configured") so a transient DDG throttle says "web search was rate-limited, retrying" — not a false global outage. Forward `web.note`/`web.detail` from the FAST bundle into the brief (`_auto_publish_event` currently reads only the top-level note — read the nested `web.*`).
- [ ] **Step 3 — Banner copy is per-symbol/honest.** In `BriefPanel.tsx`, the banner only shows when there is genuinely no web evidence **and** says why: "Web search was unavailable for this run ({reason})" or, when structured-only by design, "Structured data only — no web sources found for {symbol}." Never a global "no backend" claim when the run cited sources.
- [ ] **Step 4 — Provenance guarantee for live-data prose.** Tighten the DEEP/iter synthesis prompts (`deep.py`/`iter.py`) so every numeric or dated claim must carry a `[n]` citation to a real gathered source; the metric-card layer already never fabricates (`deriveMetrics` returns null). Document the guarantee: live-data sections (macro/prices/news) come from a live call or are honestly flagged as a gap — never parametric memory. (This composes with WS1's date directive that forces the live call in the first place.)
- [ ] **Step 5 — Reconcile with WS5 (native search).** If WS5 enables `openrouter:web_search`, its citations must feed `web_available`/source set so a successful native search **clears** the banner. Add this to the Step-1 fold-in.
- [ ] **Step 6 — Tests.** A DEEP run with structured sources but zero web citations does **not** fire the banner if `source_count>0`; a transient DDG error yields a "rate-limited" note, not "no backend"; `briefFromInput` never default-trues a true outage. Run: `pytest sidecar/tests/test_research_*.py -q && pnpm vitest run src/store/brief.test.ts`.
- [ ] **Step 7 — Commit.** `fix(brief): web_available reflects real evidence; honest per-symbol search messaging`

### WS4 — Brief depth state, export, chart dedup — fixes #5, #6, #7

**Files:**
- Modify: `src/lib/host-actions.ts` (~91, 115–126 — depth carry-forward), `sidecar/services/agent_tools/catalog.py` (publish_brief schema)
- Modify: `src/modules/research/BriefPanel.tsx` (export buttons), `src/lib/brief-ingest.ts` (`composeBriefMarkdown`)
- Modify: `src/modules/chat/ChatSidebar.tsx` (depth controls — research-mode consolidation)
- Modify: `src/modules/chart/index.ts` (`singleton`), `src/store/workspace.ts`, `src/components/CommandPalette.tsx`, `src/lib/host-actions.ts` (`ensureChartOpen`)
- Tests: `src/lib/host-actions.test.ts`, `src/store/brief.test.ts`

- [ ] **Step 1 — Carry `depth` forward across re-publish (fixes #5).** In `briefFromInput` (`host-actions.ts`), mirror the existing `structured` carry-over: when the model's `publish_brief` omits `depth`, keep `prev.depth`; when both present, take the **max** tier (`quick < deep < heavy`) for the same symbol. Add `depth` to the `publish_brief` schema in `catalog.py` so a model **can** set it explicitly. Now `depth==='heavy'` is no longer clobbered → "Go all out" correctly disappears.
- [ ] **Step 2 — Consolidate research-mode controls into chat with correct state (operator ask).** Move the depth/escalation affordance from the brief-only `GoDeeper` into the chat surface (a compact control near the composer/transcript, reusing locked tokens): show the current depth (FAST/DEEP/HEAVY) and a single explicit "Go deeper" / "Go all out" action that is **disabled with a 'deepest' label at `heavy`** and shows a **running** state while a deep pass streams (derive from the active run/stream state, not a guess). Make escalation **deterministic**: send a structured depth arg (`research(subject, depth=next)`) rather than relying on the model to parse "go all out" from prose. Keep the brief's inline affordance as a thin mirror or remove it (operator preference — default: keep one source of truth in chat, mirror read-only on the brief).
- [ ] **Step 3 — Export → Copy-markdown (Decision 7 default).** Replace the MD + PDF buttons in `BriefPanel.tsx` with a single "Copy markdown" button that calls `composeBriefMarkdown(brief)` (already pure + reliable, includes the `## Sources` appendix) and writes to the clipboard, flashing "Copied" (no path, no truncation, no raster). Remove the `saveTextArtifact`/`savePdfArtifact` calls and the framer-motion-raster path. *(If the operator chooses "keep export": instead await an animation settle, include the Sources tray in the raster ref, fix the bg to `#161616`, and show the full non-truncated path.)*
- [ ] **Step 4 — Chart dedup (fixes #7).** Flip `src/modules/chart/index.ts` `singleton: false` → `singleton: true` (abandon the unfinished Phase-2 multi-chart). With `singleton:true`, `openPanel('chart')` reuses the literal-id `chart` panel (`workspace.ts` singleton branch), matching `default-layout`/`layout-templates`/`ensureChartOpen`. Verify the command-palette "Open Chart" (`CommandPalette.tsx:181`) and `ensureChartOpen` (`host-actions.ts`) now reuse rather than mint. (No casing change needed — there was never a second registration.)
- [ ] **Step 5 — Tests.** `host-actions.test.ts`: a depth-less re-publish preserves `prev.depth`; `heavy` survives a `mode='DEEP'` re-publish. A second `openPanel('chart')` returns the same panel id. Copy-markdown produces `composeBriefMarkdown` output including `## Sources`. Run: `pnpm vitest run src/lib/host-actions.test.ts src/store/brief.test.ts`.
- [ ] **Step 6 — Commit.** `fix(brief): preserve depth across re-publish; copy-markdown; single Chart panel; chat-side depth controls`

### WS5 — OpenRouter default-route search + per-model capability — closes the default search gap

**Files:**
- Modify: `sidecar/services/llm/native_search.py` (add `openrouter`; new helper), the OpenRouter adapter path in `services/llm/openai.py`/`__init__.py`
- Modify: `sidecar/services/agent_runtime.py` (~687–694 — per-model gate)
- Modify: `sidecar/services/llm/openrouter_catalog.py` (parse more flags), `sidecar/models/llm.py` + `types/ai.ts` (new optional fields, same commit), `src/store/model-catalog.ts`
- Modify: `src/components/.../SettingsPanel` native-tier copy (model/provider-aware)
- Tests: `sidecar/tests/test_openrouter_catalog.py`, `test_native_search*.py`

- [ ] **Step 1 — Add the OpenRouter native-search rung.** In `native_search.py`, add `"openrouter"` to `SUPPORTS_NATIVE_SEARCH` **(gated per-model — see Step 2)** and add `openrouter_web_search_tool()` returning `{"type": "openrouter:web_search"}`. Inject it under the same `web_search` kwarg the other 5 providers use; citations come back as OpenAI-style `url_citation` annotations → reuse `normalize_openai()`.
- [ ] **Step 2 — Make the native-search gate per-model, not per-provider.** In `agent_runtime.py:687–694`, replace `provider_id in SUPPORTS_NATIVE_SEARCH` with a capability lookup of the **resolved model**: enable native search when the model's `web_search=='native'`; if `'plugin'`, optionally let OpenRouter run its plugin (else keep the local `web_search` tool); if `'none'`, keep the local tool (current FR-082 fallback, never fabricates). The loop already withholds the local `web_search` tool when native is active and re-adds it otherwise.
- [ ] **Step 3 — Parse per-model capability flags.** In `openrouter_catalog.py`'s model loop, derive from each model's `supported_parameters`/`pricing`: `supports_structured_outputs`, `supports_reasoning`, and `web_search = 'native' if 'web_search_options' in params else ('plugin' if pricing.get('web_search') else 'none')`. Add these as **optional** fields to `LLMModelOption` (`sidecar/models/llm.py`) and mirror in `types/ai.ts` **in the same commit** (mirror-by-hand rule). Non-OpenRouter providers leave them `None` (unknown) — nothing regresses. Public `/models` needs no key (keyless-first holds); a BYOK key only narrows to routable models.
- [ ] **Step 4 — Surface it subtly + honest Settings copy.** Pass the flags through `src/store/model-catalog.ts`; render subtle inline pips in the picker (search glyph: filled=native, outline=plugin-available, absent=app-fallback) reusing the existing tool-capability badge pattern (no new UI chrome — UI locked). Fix the SettingsPanel native-tier text so it's model/provider-aware (today it claims "your active model's own web search" even on OpenRouter/DeepSeek where it never fired).
- [ ] **Step 5 — Cost surface (Decision 1).** When `openrouter:web_search` will fire, show the per-search cost in the existing cost-preview UI before the call.
- [ ] **Step 6 — Tests.** Extend `test_openrouter_catalog.py` fixtures with `supported_parameters` incl. `web_search_options` + a `pricing.web_search` row; assert flag derivation. Assert the runtime enables native search for an OpenRouter model marked `web_search=='native'` and falls back to the local tool for `'none'`. Run: `pytest sidecar/tests/test_openrouter_catalog.py test_native_search*.py -q`.
- [ ] **Step 7 — Commit.** `feat(search): OpenRouter native-search rung + per-model capability gate`

### WS6 — Indian data coverage — yfinance suffix fix + keyless BSE

**Files:**
- Modify: `sidecar/services/yfinance_provider.py` (`get_quote:113`, `get_history:139`)
- New: `sidecar/services/bse_provider.py` (AGPL reimpl — Decision 3, sign-off-gated)
- Modify: `sidecar/services/provider_registry.py` (register `bse`), `symbol_resolver.py` (BSE master + `is_bse_symbol`/`region_hint`), `resolver_masters/` (BSE master)
- Modify: `src/modules/chart/ChartPanel.tsx` (region-aware "no data" message), `sidecar/routers/history.py`
- Tests: `sidecar/tests/test_yfinance_provider.py`, `test_india_provider.py`, new `test_bse_provider.py`, `test_provider_registry_region.py`

- [ ] **Step 1 — Fix the yfinance suffix mangling (independent, high value, do first).** In `yfinance_provider.get_quote` (113) and `get_history` (139), replace `_normalize_symbol(symbol)` with the region-aware `_yahoo_symbol(symbol)` already used by fundamentals/statements (passes `.NS`/`.BO` through, suffixes bare NSE tickers, only applies the dot→dash US quirk where valid). Add tests feeding `RELIANCE.NS` and `532837.BO` through quote/history (today only `BRK.B` is tested). Commit this alone: `fix(data): route yfinance quote/history through region-aware _yahoo_symbol`.
- [ ] **Step 2 — Keyless BSE provider (Decision 3, blocked on operator licensing sign-off).** New `sidecar/services/bse_provider.py` modeled on `india_provider.py`: `get_history` backed by a once-daily full-universe bhavcopy cache (download `BhavCopy_BSE_CM_0_0_0_{YYYYMMDD}_F_0000.CSV`, key by scrip code/ticker — instant full micro-cap coverage), `get_quote` via `getScripHeaderData`. Reuse india_provider's UA/header hardening, cache-dir-race retry, IST trading-date fix, EOD labelling; raise on intraday with the existing "add a BYOK broker (Kite/Upstox/Dhan)" message. A 5-line token-bucket replaces `mthrottle`. **Reimplemented under AGPL — no GPL import.**
- [ ] **Step 3 — Resolver + registry wiring.** Build a BSE resolver-master (groups B/X/XT/T/Z with ISIN + market cap) and add `is_bse_symbol()` + extend `region_hint()` so a bare BSE-only ticker resolves to IN (today only a `.BO` suffix does). Register in `provider_registry._PROVIDERS` as `id='bse'`, `rank~25` (between `nse=20` and `yfinance=50`), `region={'IN'}`, `asset_classes={'equity'}`, `serves={'quote','ohlcv'}`. `active_providers()`/`/health` derive automatically.
- [ ] **Step 4 — Region-aware "no data" UX.** When all providers are empty for an IN symbol, surface a typed honest message ("BSE/NSE EOD only; intraday/realtime needs a BYOK broker (Kite/Upstox/Dhan)") instead of the generic "No price data" — carry the reason from the provider's `ProviderError` to the chart (`history.py` → `ChartPanel`).
- [ ] **Step 5 — Tests + smoke.** `test_bse_provider.py` (bhavcopy parse, quote shape, intraday raises), a region test routing a `.BO` symbol to `bse`. Mirror `types/data.ts`. The bhavcopy URL must be probed by `scripts/smoke-test-sidecars.mjs` (live-data, no SLA). Run: `pytest sidecar/tests/test_yfinance_provider.py test_bse_provider.py test_provider_registry_region.py -q`.
- [ ] **Step 6 — Commit.** `feat(data): keyless BSE micro-cap provider + region-aware no-data state` (after the standalone Step-1 commit).

### WS7 — Harden the keyless DDG floor

**Files:** `sidecar/services/search/ddg.py`, tests `sidecar/tests/test_ddg*.py`

- [ ] **Step 1 — Proactive token-bucket rate-limiter (no dep).** Add a small async token-bucket (~20–30 req/min) before `_fetch` in `ddg.py` to dodge the 202 "anomaly" *before* it triggers, rather than only reacting with the existing 202/429 retry. Pattern ported from `nickclyde/duckduckgo-mcp-server` (MIT). ~10 lines, no new dependency.
- [ ] **Step 2 — (Deferred, Decision 2) `curl_cffi` TLS-impersonation retry.** Only if the operator approves the new lib: an optional `curl_cffi AsyncSession(impersonate="chrome131")` retry on 403/Cloudflare-challenge bodies, gated behind an optional extra, audited against the PyInstaller `--onefile` ≤120 MB target via the smoke-test (not `cargo test`). **Default: skip for v0.8.0.**
- [ ] **Step 3 — Tests + commit.** Test the limiter paces requests; existing DDG tests stay green. `perf(search): proactive rate-limiter on the keyless DDG floor`.

### WS8 — DeepSeek/OpenRouter tool-loop resilience (heaviest; last)

**Files:** `sidecar/services/llm/openai.py` (`_flush_tool_buffers` ~95–121; stream loop; client call ~207), `sidecar/services/agent_runtime.py` (~787–798 reconstructed turns), tests `sidecar/tests/test_llm_openai*.py`

- [ ] **Step 1 — Validate + repair tool-call args (port `vercel/ai` `parse-tool-call.ts`, no dep).** In `_flush_tool_buffers`, after `json.loads`, validate args with `jsonschema` (already a sidecar dep) against `TOOL_SCHEMAS[tid]['input_schema']`. On failure, run **one** repair round via the existing `oneshot.complete(provider_id, model, api_key, [...])` (already used by the planner, rides per-request BYOK creds) giving the model the schema + validation error + raw args; re-validate. If repair still fails, **do not coerce to `{}`** — append a `role='tool'` result `{"ok":False,"error":"invalid arguments for <tool>: <error>; call again with valid args"}` keyed on `tool_call_id`, so the model self-corrects next round (mirrors the existing graceful `_dispatch_tool` convention).
- [ ] **Step 2 — Content-leak rescue (port `litellm` `function_call_prompt` round-trip, no dep).** When a round finishes with `finish_reason != 'tool_calls'` and no tool buffers, but `delta.content` contains a `{"name":...,"arguments":{...}}` JSON block matching a known tool id, parse it into an `LLMToolUseEvent`. **Gate on `provider_id in {'deepseek','openrouter','ollama'}`** to avoid false positives on chatty OpenAI/Anthropic. Fixes the documented DeepSeek text-fall-through.
- [ ] **Step 3 — Header-aware transport retry.** Wrap `client.chat.completions.create` (~207) in exponential backoff (port `retry-with-exponential-backoff.ts`) that retries only `openai.RateLimitError`/5xx/connection errors, honoring `Retry-After`, `maxRetries≈2`. Today a single 429 kills the stream.
- [ ] **Step 4 — `deepseek-reasoner` guard.** If `resolved_model` contains `reasoner`, echo `reasoning_content` back on the reconstructed assistant tool-use turn (`agent_runtime.py:787–798`, currently `content=''`) or steer tool loops to non-reasoner `deepseek-chat`. (Open question flagged in Part 5.)
- [ ] **Step 5 — Keep as-is:** `_MAX_TOOL_ROUNDS=6`, graceful `_dispatch_tool` tool-not-found, `metadata['name']` for Gemini, OpenRouter `require_parameters=true`.
- [ ] **Step 6 — Tests + commit.** A malformed-args round triggers exactly one repair then recovers; a content-leaked tool call is rescued for DeepSeek but not OpenAI; a 429 retries then succeeds. `feat(llm): tool-call validate+repair, content-leak rescue, transport retry for DeepSeek/OpenRouter`.

---

## Part 4 — Deferred / Tier-4 (flagged, not built by default)

- **External MCP control-plane** (operator asked to evaluate exposing panels/data/actions as agent tools). Vysted already has a read-only MCP data surface (`mcp_server.py` projects `read_handler` capabilities; host-actions are deliberately excluded per `catalog.py:1040` + `test_mcp_catalog_parity.py:93`). A safe extension exists but is **Tier-4** (widens §6.5): an **opt-in, flag-gated** (`VYSTED_MCP_CONTROL_PLANE=1`, default off) tier that projects host-actions as **propose-not-apply** (returns the same `awaiting_user_review` payload into the existing review queue), uses FastMCP `ctx.elicit()` to confirm where the client supports it (feature-detect + degrade), studies OpenBB's AGPL discovery layer for tool-surface scaling, and **permanently excludes `propose_order`**. Do **not** promote the dev-only `tauri-plugin-mcp` rig (it writes Zustand stores directly, bypassing the gate). **Recommend defer** — orthogonal to all 7 symptoms.
- **`curl_cffi`** (Decision 2), **Tavily BYOK rung** (Decision 9), **broker historical** (Kite/Upstox intraday upgrade), **pending-proposal persistence** (Decision 8) — all deferred by default, surfaced for a later sprint.

---

## Part 5 — Verification gates, open questions, sequencing

### Gates (before any tag)
- `pnpm ci-local` green (install → ensure-all-sidecars → lint → format:check → typecheck → cargo fmt → clippy `-D warnings` → ruff → vitest → cargo test → pytest).
- `node scripts/smoke-test-sidecars.mjs` (catches the binary-runtime gap; add the BSE bhavcopy URL probe in WS6).
- `test_safety_end_to_end.py` stays **9/9**. `test_capability_catalog`/`test_mcp_catalog_parity` parity holds after the new `market_overview` tool.
- Mirror-by-hand pairs edited in the **same commit**: `sidecar/models/llm.py` ↔ `types/ai.ts` (WS5); `sidecar/models/` ↔ `types/data.ts` (WS6).
- Cheapest in-sprint guard before each push: `pnpm format:check`; before any Python commit: `ruff format <files> && ruff format --check sidecar && ruff check sidecar`.

### Open questions to resolve during the build (flagged, low-confidence in audit)
- **deepseek-reasoner multi-round** (`reasoning_content` echo) — needs a live multi-round repro before choosing echo-vs-steer (WS8 Step 4).
- **BRIEF-2 PDF-mid-animation** (confidence 0.7, not reproduced) — moot if Decision 7 = Copy-markdown (WS4 Step 3 removes the raster path entirely).
- **OpenRouter `:online` deprecation + $0.005 price** — from docs, not source; re-confirm at WS5 implementation.
- **Streaming re-parse cost** — running `parseBodyBlocks` + completer on every delta of a long message; measure in WS2; if heavy, parse on finalize + a cheap pass while streaming.
- **The actual ticker/exchange in symptom #2 was never identified** — WS6 assumes BSE-only; if the operator's ticker was NSE, WS6 Step 1 (the yfinance fix) already covers it and the BSE provider is a coverage bonus.

### Build order
WS1 (grounding + truthful AUTO) → WS2 (chat markdown) → WS3 (honest banner) → WS4 (depth/export/chart) → WS5 (search rung + capability) → WS6 (data: yfinance fix first, then BSE behind sign-off) → WS7 (DDG limiter) → WS8 (tool-loop resilience). WS1–WS5 + WS6-Step1 + WS7 are no-new-dep and unblock the bulk of the symptoms; WS6-Step2 and WS8 are the heavier, more-flagged tail.

---

**STOP — awaiting operator approval.** Nothing is built. On "Yes, execute the plan," the build runs as a second workflow following this document workstream-by-workstream, surfacing each flagged decision's default unless overridden.
