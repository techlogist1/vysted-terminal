# Phase 10 Study — Kite Connect Auth + Agentic Terminal Copilot

Research date: 2026-05-29. Author: research subagent.
Sources: official Kite Connect v3 docs (kite.trade), Zerodha support/forum, RFC 8252, Tauri 2 plugin docs, Anthropic/OpenAI tool-use docs. Grounded against the actual Vysted Terminal codebase (cited `file:line`).

This is an adversarial study — every external claim is from official docs and every "we already have X" claim is cited to source in this repo. Where the existing `kite.py` adapter is wrong or incomplete, it is called out explicitly.

---

# PART A — Real Kite Connect (Zerodha) auth + read-only data flow

## A.0 What Kite Connect actually is

Kite Connect is a set of REST-like HTTP APIs. Requests are **form-encoded**; responses are **JSON**. The API endpoints are **not CORS-enabled** — they cannot be called directly from a browser (Source: https://kite.trade/docs/connect/v3/). This matters for Vysted: the Next.js frontend (static export running in a Tauri webview) must NOT call `api.kite.trade` directly. All Kite calls go through the Python sidecar (which is exactly what `sidecar/services/brokers/kite.py` does via the `kiteconnect` SDK). The webview-origin CORS problem alone forces the sidecar-proxy design.

## A.1 The app credential model: `api_key` + `api_secret`

- Developers register an app in the Kite developer console and get an `api_key` (public) and `api_secret` (private).
- Each app registers a **redirect URL** where users land after login.
- Official guidance (verbatim from docs): for **mobile and desktop applications, a backend service must handle the authentication handshake, as the `api_secret` should never be embedded in client applications** (Source: https://kite.trade/docs/connect/v3/).

Implication for Vysted: the `api_secret` must never reach the Next.js bundle. It belongs in the OS keychain (Tauri Rust-only access per the stack rules) and the SHA-256 checksum step must execute in Rust or the Python sidecar — never in the webview JS. See A.6 for the recommended split.

## A.2 The login redirect flow (exact)

1. App sends the user to:
   ```
   https://kite.zerodha.com/connect/login?v=3&api_key=xxx
   ```
2. User logs in to Zerodha (credentials + 2FA TOTP) entirely on Zerodha's domain.
3. On success Zerodha redirects to the app's **registered redirect URL** with a `request_token` query parameter appended (and a `status=success`). Example: `https://your-redirect/?request_token=<token>&action=login&status=success`.
4. The `request_token` is **single-use and short-lived** — it must be exchanged for an access token immediately.

(Source: https://kite.trade/docs/connect/v3/user/)

## A.3 Session exchange (exact)

POST (form-encoded) to:

```
POST https://api.kite.trade/session/token
```

Body parameters:

- `api_key` — the public API key
- `request_token` — from the login redirect
- `checksum` — `SHA-256(api_key + request_token + api_secret)` (string concatenation, then SHA-256 hex digest)

(Source: https://kite.trade/docs/connect/v3/user/)

### A.3.1 Response body fields (verified field list)

The `data` object returned contains:
`user_type`, `email`, `user_name`, `user_shortname`, `broker`, `exchanges` (array), `products` (array), `order_types` (array), `avatar_url`, `user_id`, `api_key`, `access_token`, `public_token`, `enctoken`, `refresh_token`, `silo`, `login_time`, `meta` (object with `demat_consent`).

(Source: https://kite.trade/docs/connect/v3/user/)

Key fields for Vysted:

- `access_token` — the bearer for all subsequent calls.
- `user_id` — Zerodha client id; `kite.py:_connect` already stores this as `_account_id` (sidecar/services/brokers/kite.py, `_connect`).
- `refresh_token` — **caveat below (A.4).**

## A.4 Token lifetime + the daily-expiry reality

- `access_token` **expires at 6:00 AM the next day** — this is a **regulatory requirement**, not a tunable (Source: https://kite.trade/docs/connect/v3/user/). It is reset daily regardless of activity.
- There is **no usable silent-refresh for the retail Connect plan.** The docs list a `refresh_token` field, but the docs **do not document a `/session/refresh_token` endpoint** (verified — the user page describes no refresh endpoint; refresh-token grant is a Kite-platform/partner-tier concept, not standard retail Connect). **Do not build the UX assuming you can silently refresh.** The honest model is: **the user must complete the interactive login once per trading day.**
- Logout: `DELETE https://api.kite.trade/session/token` with `api_key` + `access_token` as query params invalidates the access token and destroys the API session (but does NOT log the user out of the official Kite web/mobile apps) (Source: https://kite.trade/docs/connect/v3/user/).

### Daily-token UX implication (this is the single most important product decision in Part A)

Because every Kite-connected user re-authenticates **every morning**, the terminal must treat "Kite session expired" as an _expected daily event_, not an error:

1. Detect expiry proactively: any data call returning **HTTP 403 / `TokenException`** means the session is dead (Source: https://kite.trade/docs/connect/v3/exceptions/). On 403 from any Kite endpoint, surface a non-blocking "Reconnect Kite" affordance, do not crash the panel.
2. On app launch, if a Kite access token exists in keychain but was minted before the most recent 6 AM IST boundary, mark it stale **before** making a call — saves a round-trip and gives an instant "tap to reconnect" prompt.
3. Persist `api_key` + `api_secret` in keychain so the only daily friction is the interactive login + checksum exchange, not re-entering credentials.
4. Cache the `user_id`, `exchanges`, `products` so the connected-broker UI can render the account identity even when the token is stale (greyed "session expired" badge).

**Gap in current code:** `kite.py` has no token-staleness awareness and no 403→reconnect path. `_account_info` and `_place_confirmed` let raw SDK exceptions propagate as `BrokerError` (sidecar/services/brokers/kite.py, `_account_info`, `_place_confirmed`). They should specifically catch `kiteconnect.exceptions.TokenException` and translate it to a typed "session expired, reconnect" outcome so the frontend can show the daily reconnect prompt instead of a generic broker error.

## A.5 Authenticating subsequent requests + the read-only endpoints

Every authenticated request carries two headers:

```
Authorization: token api_key:access_token
X-Kite-Version: 3
```

(Source: https://kite.trade/docs/connect/v3/portfolio/, /user/)

### Read-only endpoints needed for positions / holdings / P&L / funds

**GET `/portfolio/holdings`** — long-term equity holdings (delivered/T1).
Per-holding fields (verified): `tradingsymbol`, `exchange`, `instrument_token`, `isin`, `quantity`, `used_quantity`, `t1_quantity`, `realised_quantity`, `average_price`, `last_price`, `close_price`, `pnl`, `day_change`, `day_change_percentage`, `product`, `collateral_quantity`, `collateral_type`, `opening_quantity`, `authorised_quantity`, `authorised_date`.
(Source: https://kite.trade/docs/connect/v3/portfolio/)

**GET `/portfolio/positions`** — intraday + F&O positions. Returns **two arrays**: `net` (carry-forward portfolio) and `day` (today's snapshot).
Per-position fields (verified): `tradingsymbol`, `exchange`, `instrument_token`, `product`, `multiplier`, `quantity`, `overnight_quantity`, `average_price`, `close_price`, `last_price`, `pnl`, `m2m`, `unrealised`, `realised`, `value`, `buy_quantity`, `buy_price`, `buy_value`, `buy_m2m`, `day_buy_quantity`, `day_buy_price`, `day_sell_quantity`, `day_sell_price` (and sell counterparts).
(Source: https://kite.trade/docs/connect/v3/portfolio/)

**GET `/user/margins`** (and `/user/margins/:segment` where segment ∈ `equity`,`commodity`) — funds/margin. Response has `net` (available balance), `available` (with `cash`, `collateral`, …) and `utilised` (margin blocked: exposure, SPAN, etc.).
(Source: https://kite.trade/docs/connect/v3/user/)

**GET `/portfolio/holdings/auctions`** — holdings under auction, adds `auction_number`. (Source: https://kite.trade/docs/connect/v3/portfolio/) Niche; not needed for the P&L panel.

**Bug in current code (high-confidence):** `kite.py:_account_info` computes equity as `available.cash` only:

```
equity = float(available.get("cash") or 0.0)
```

and then sets `equity = cash = buyingPower` all to that one number (sidecar/services/brokers/kite.py, `_account_info`). That ignores `net` (the true available balance), `collateral`, and `utilised`. The Kite margins object's authoritative "what can I deploy" number is `equity.net`, not `equity.available.cash`. For accurate buying-power display this should read `equity_block.get("net")` for `buyingPower`/equity and keep `available.cash` only for the cash line. Confidence 8/10 (exact field semantics depend on Kite's current margins payload, but `net` vs `available.cash` divergence is real and documented).

**Second issue:** `_account_info` only translates **holdings** into positions; it never calls `positions()`. Intraday and F&O positions (the `net`/`day` arrays) are invisible to the account summary. For an F&O-capable broker (which Kite is — `supportsFutures=True`, `supportsOptions=True` in `CAPABILITIES`) this is a material omission. The P&L panel will under-report. Confidence 7/10.

## A.6 Desktop redirect handling — the core Tauri problem and the recommendation

Kite assumes a **web app with a public registered redirect URL**. A Tauri desktop app has no public web server. There are three viable patterns (RFC 8252, "OAuth 2.0 for Native Apps", is the governing reference — Source: https://www.rfc-editor.org/rfc/rfc8252):

### Option 1 — Loopback localhost redirect (RFC 8252 §7.3, recommended for desktop)

Register `http://127.0.0.1:<port>/kite/callback` (or `http://localhost`) as the Kite redirect URL. At login time, Tauri Rust spins up a one-shot loopback HTTP listener, opens the system browser to the Kite login URL, and captures `request_token` from the redirect. RFC 8252 explicitly blesses loopback `http` redirects ("the redirect never leaves the device") and requires servers to treat the **port as variable** for loopback hosts (Source: https://www.rfc-editor.org/rfc/rfc8252, §7.3/§8.3). In Tauri this is exactly what **`tauri-plugin-oauth`** does — it "spawns a temporary localhost server to capture OAuth redirects" (Source: https://github.com/FabianLars/tauri-plugin-oauth, https://lib.rs/crates/tauri-plugin-oauth).

- Pro: zero copy-paste, system browser (real 2FA, password managers work), best UX.
- Con: Kite's console may require a fixed redirect URL; if it won't accept a variable port you must pin one port (pick a high, unlikely-to-collide port and fall back gracefully). Kite historically requires the redirect to match exactly, so pin one port.

### Option 2 — Custom URL scheme / deep link (`vysted://kite/callback`)

Register a custom scheme via **`tauri-plugin-deep-link`** (Source: https://v2.tauri.app/plugin/deep-linking/, https://github.com/FabianLars/tauri-plugin-deep-link). Kite redirects to `vysted://…?request_token=…`, the OS hands the URL to the running app.

- Pro: no local server, can cold-start the app.
- Con: RFC 8252 warns custom schemes are weaker — **multiple apps can claim the same scheme**, enabling code interception; mitigated by PKCE, but **Kite does not implement PKCE** (it's a checksum/secret model, not standard OAuth2 PKCE). Also, many providers reject custom schemes as redirect URLs. Riskier and Kite-console support is uncertain.

### Option 3 — Manual `request_token` paste

Open the login URL in the system browser; the user copies the `request_token` from the redirected URL bar and pastes it into the plugin.

- Pro: works with literally any redirect URL config; zero platform plumbing.
- Con: ugly, error-prone, defeats "natural language drives the app."
- **Note:** the existing `kite.py` docstring assumes exactly this ("the user logs in at kite.zerodha.com and pastes the URL back into the plugin"). That is the current implicit design and it is the weakest of the three.

### Recommendation for Vysted (Tauri desktop)

**Use Option 1 (loopback localhost) via `tauri-plugin-oauth`, with Option 3 as an explicit fallback.** Concrete flow:

1. Frontend "Connect Kite" → Tauri command `kite_begin_login`.
2. Rust reads `api_key` from keychain, starts a one-shot loopback listener on a pinned port (e.g. `http://127.0.0.1:43117/kite/callback`, registered in the Kite console), opens the system browser to `https://kite.zerodha.com/connect/login?v=3&api_key=<key>`.
3. Browser redirects to the loopback; Rust captures `request_token`, shows a "you can close this tab" page, shuts the listener.
4. Rust reads `api_secret` from keychain, computes `checksum = SHA-256(api_key + request_token + api_secret)` **in Rust** (secret never leaves Rust), then either (a) POSTs `/session/token` itself, or (b) hands `{api_key, request_token, checksum}` to the sidecar which POSTs. Prefer (b) only if you pass the already-computed checksum so the secret stays in Rust; do NOT ship `api_secret` to the sidecar process if avoidable. (Pragmatic alternative: keep the secret in keychain, let Rust hand `api_key`+`access_token` to the sidecar after exchange — which matches what `kite.py:_connect` already expects: it takes a resolved `api_key`+`access_token`.)
5. Store `access_token` (+ `login_time`) in keychain, hand `api_key`+`access_token` to the sidecar `kite` adapter's `_connect`.
6. Fallback: if the loopback can't bind / corporate firewall blocks it, fall back to manual paste (Option 3) behind a "trouble connecting?" link.

This keeps the **`api_secret` Rust-only** (matches the stack's keychain rule), uses the **system browser** (real 2FA), and gives a one-tap daily reconnect.

## A.7 The SEBI static-IP rule — scope clarification

- SEBI circular SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/0000013 (Feb 2025), deadline extended to **2026-04-01** via .../2025/132, requires brokers to "allow access only through a unique vendor client specific API key and static IP whitelisted by the broker." (Source: https://kite.trade/forum/discussion/15912/, https://inthemoneybyzerodha.substack.com/p/sebi-algo-trading-changes-april-2026)
- **The static-IP requirement applies to ORDER PLACEMENT only.** All other endpoints — **WebSocket data, order book, positions, holdings, margins** — remain accessible **from any IP** (Source: Zerodha support — https://support.zerodha.com/category/trading-and-markets/general-kite/kite-api/articles/static-ip; forum confirmation https://kite.trade/forum/discussion/15359/). Orders from unregistered IPs are rejected; data is unaffected.
- Up to two static IPs (one primary mandatory, one secondary optional), registered in the Developer Console Profile; shareable only with immediate family. (Source: https://support.zerodha.com/.../static-ip)
- **Note the data-vendor caveat:** Zerodha staff (forum) state "Kite Connect is purely an execution platform. For your data requirements, you will need to contact an exchange-authorised data vendor" (Source: https://kite.trade/forum/discussion/15359/). Practically, holdings/positions/margins still work, but Zerodha discourages using Connect as a _market-data_ feed — Vysted should source live quotes/candles from its own data layer (yfinance/OpenBB/etc., already present in `sidecar/services/`) and use Kite only for **the user's own account state + execution**.

**Codebase alignment (good):** This rule is already modeled correctly. `BrokerCapabilities.requiresStaticIp` is documented as "order placement only" and set true for `kite` (types/broker.ts, `BrokerCapabilities.requiresStaticIp`; sidecar/services/brokers/kite.py, `CAPABILITIES`). `static_ip_detector.py` correctly states "Kite rejects orders from unregistered IPs while leaving data/holdings/positions endpoints unaffected" and the detector never pre-blocks placement (sidecar/services/static_ip_detector.py, module docstring). `kite.py:set_mode` audit-logs the detected-vs-configured IP comparison on the live toggle. This is the right design: don't pre-block (user may be on VPN/VPS with the right IP), surface a banner, let Kite's order-time 403 be the source of truth.

**One refinement:** the static-IP banner should make explicit that **read-only panels keep working even on a mismatched IP** — only order placement is at risk. Otherwise users will think their whole Kite connection is broken when only execution is.

## A.8 Rate limits + error handling (for the data-poll loop)

Per-endpoint rate limits (verified — Source: https://kite.trade/docs/connect/v3/exceptions/):

- Quote: **1 req/s**
- Historical candle: **3 req/s**
- Order placement: **10 req/s** (also: ≤400 orders/min, ≤10/s, ≤5000/day per user/api_key)
- All other (positions, holdings, margins, profile): **10 req/s**

So the portfolio/P&L poll loop (positions + holdings + margins) is comfortably within 10 req/s — but **do not poll faster than once every few seconds**; there's no value in hammering, and Kite data is not tick-by-tick on REST. For live ticks use the Kite WebSocket (separate from REST), but per A.7 prefer Vysted's own data layer for quotes.

`TokenException` → **HTTP 403** → clear session + re-login (Source: https://kite.trade/docs/connect/v3/exceptions/). This is the daily-expiry signal from A.4.

---

# PART B — Agentic, terminal-aware AI copilot (tool-using LLM loop)

Goal: "natural language drives the app." The user types/speaks a request; an LLM with tools reads live terminal state and either answers or _acts_ (opens a panel, sets a chart symbol, proposes an order through the safety gate). This must be **BYOK multi-provider** (the seven providers in `types/ai.ts`).

**Reality check first:** Vysted already has most of this built. This section documents the canonical patterns AND maps them to the existing implementation so Phase 10 extends rather than reinvents.

## B.1 The tool/function-calling loop — canonical shape

Both Anthropic and OpenAI use the same fundamental loop; only the wire shape differs. The model can't run your code, so **every tool call is a round-trip**: model asks → host executes → host reports back → model continues (Source: https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works).

### Anthropic (Messages API)

- Send `messages` + a `tools` array (each tool: `name`, `description`, `input_schema` JSON Schema).
- Loop keyed on `stop_reason`:
  - `stop_reason == "tool_use"` → response has one or more `tool_use` content blocks, each with an `id`. Execute each, append a `user` message containing `tool_result` blocks keyed by `tool_use_id`, re-call.
  - `stop_reason == "end_turn"` → done.
  - `stop_reason == "pause_turn"` (server tools) → re-send to continue.
    (Source: https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use, https://docs.anthropic.com/en/api/handling-stop-reasons)

### OpenAI (Chat Completions)

- Send `messages` + `tools` (each: `type:"function"`, `function:{name,description,parameters}`), optional `tool_choice`.
- Response: `choices[0].message.tool_calls[]` (each has `id`, `function.name`, `function.arguments` as a JSON **string**). Execute, append one `role:"tool"` message per call with `tool_call_id` + stringified result, re-call. Loop until no `tool_calls`.
- Streaming: `tool_calls` arrive as **incremental argument deltas** in `choices[0].delta.tool_calls` — you must accumulate `function.arguments` fragments per `index` before parsing.

### Codebase: this loop already exists and is correct

`sidecar/services/agent_runtime.py:invoke_agent` implements exactly this loop:

- `while True:` collecting `pending_tools: list[LLMToolUseEvent]` from `adapter.stream_chat(...)` (agent_runtime.py ~263).
- Capped at `_MAX_TOOL_ROUNDS` to bound runaway tool-spam (agent_runtime.py ~191, ~282) — this is the right guardrail.
- On each round it dispatches every pending tool via `_dispatch_tool` and appends `role="tool"` messages keyed on `tool_call_id`, then re-enters (agent_runtime.py ~297-303).
- `_dispatch_tool` swallows unregistered-tool and handler exceptions into a JSON error payload fed back to the model rather than crashing the stream (agent_runtime.py ~198-221) — correct: let the model recover.

Provider translation is already abstracted:

- Anthropic adapter maps `role="tool"` messages into `tool_result` content blocks keyed on `tool_use_id` and emits `tool_use` blocks as `LLMToolUseEvent` (sidecar/services/llm/anthropic.py ~53-66, ~164-166).
- OpenAI adapter forwards `delta.tool_calls` function deltas as `LLMToolUseEvent(input={"arguments_delta": ...})` (sidecar/services/llm/openai.py ~88-100).

**Gap (medium, B-critical for Phase 10):** the OpenAI adapter forwards **`arguments_delta` fragments** but I see no accumulator that reassembles the streamed JSON-string fragments into a complete `input` dict before `_dispatch_tool` parses it. Anthropic's SDK gives whole blocks; OpenAI gives fragments. If `_dispatch_tool`/the runtime feeds a partial `arguments_delta` to a handler, OpenAI-provider agents will mis-parse multi-token tool arguments. **Verify there is a per-`tool_call_id` argument-buffer that concatenates `arguments_delta` until the tool-call is complete, then parses once.** If absent, OpenAI/DeepSeek/xai/groq (all OpenAI-compatible) tool calls with non-trivial args are broken. Confidence 6/10 (couldn't see the full reassembly path in the grep; needs a direct read of the runtime's tool-arg handling).

## B.2 Injecting app/terminal state as context

Two complementary mechanisms — Vysted already uses both:

### (a) Context snapshot in the prompt preamble (cheap, always-on)

Attach a structured snapshot of _what the user is looking at_ to every invocation. Vysted's `PanelContextEvent`/`AgentContextSnapshot` does this: a Zustand bus (`src/store/panel-context.ts`) aggregates per-panel state (focused chart symbol, active indicators, focused news article, portfolio positions) and the chat sidebar attaches the aggregated snapshot to the agent request (types/panel-context.ts, module docstring; types/ai.ts `AgentContextSnapshot`; sidecar/models/agent.py `AgentContextSnapshot` with `focused_source`, `by_source`, `captured_at`).

Design notes that are already right:

- `by_source` is intentionally loose (`dict[str, Any]`) — each panel publishes its own shape (sidecar/models/agent.py). Good: don't over-type panel payloads.
- Snapshot is rendered into the system-prompt preamble via `JSON.stringify` (types/panel-context.ts comment). Good for cheap context; keep it **small** — only the focused panel + a compact summary of others, not full tables.
- Subscribers skip self-`source` echoes to avoid render loops (types/panel-context.ts). This is a frontend correctness detail, not an AI one, but it's load-bearing.

**Recommendation:** keep the _preamble_ snapshot as a terse "current view" summary (focused symbol, timeframe, open panels, top-N positions). Push _detailed_ state retrieval into **tools** (B.1) — e.g. a `get_portfolio()` tool the model calls only when it needs full position rows. This keeps token cost down and lets the model pull detail on demand rather than always paying for it.

### (b) Tools that read live state on demand (precise, pull-based)

The `agent_tools` registry (sidecar/services/agent_tools/) already exposes `price_data`, `fundamentals`, `news`, `backtest_summary`, plus per-domain tools (analyst, earnings, macro, quant, screener, sec). Each agent's `tools` field is an **allow-list** (types/plugin.ts `AgentSpec.tools`; e.g. buffett.json lists `["price_data","fundamentals","news"]`). The runtime only exposes allow-listed tools to that agent (`agent_tools.is_registered` check in `_dispatch_tool`).

For "natural language drives the app," Phase 10 needs to add **action tools** (not just read tools), and they must route through the safety layer:

- `set_chart_symbol`, `open_panel`, `add_to_watchlist` — pure UI actions, safe to execute directly (still echo a confirmation in the response).
- `propose_order` — must NOT place; it must create a `BrokerOrderProposal` with `source="ai-agent"`, which per the LOCKED contract opens the confirmation dialog **defaulted to declined** with the originating agent named (types/broker.ts `BrokerOrderSource`, `BrokerOrderProposal`; the §6.5 safety files are LOCKED). The AI layer has **no path** to `place_order`. Any Phase-10 action tool that touches a broker must emit a proposal, never a placement.

## B.3 The persona roster (discoverable agent design)

Vysted already ships a 12-agent roster (sidecar/agents/README.md): 9 investor personas (buffett, graham, lynch, munger, marks, klarman, dalio, druckenmiller, soros) + 3 functional agents (researcher, portfolio_advisor, strategy_critic). The config contract is the LOCKED `AgentSpec` (types/plugin.ts) discovered from JSON files validated against `_schema.json` at startup.

What makes this roster _discoverable_ and worth keeping:

- Each agent has a one-line `philosophy` shown as a subtitle in the picker (sidecar/agents/\_schema.json `philosophy`; README "shown as a subtitle"). This is the discoverability surface — users browse by lens, not by model.
- `icon` (Lucide name) gives visual identity (buffett.json `"icon":"landmark"`).
- `systemPrompt` is substantive (200-500 words) and encodes a _real framework_, with explicit anti-roleplay guardrails ("You are not Warren Buffett; you do not roleplay as him, and you do not invent quotes" — buffett.json). This is the right call: a persona that _applies a framework_ is useful; one that _performs a celebrity_ is a liability (fabricated quotes, false authority).
- `tools` allow-list per agent scopes capability to role (buffett gets fundamentals/news, strategy_critic gets backtest_summary).
- `systemPrompt` is NOT echoed to the frontend (`AgentSummary` omits it — sidecar/models/agent.py `AgentSummary` docstring). Good: keeps prompts server-side.
- User-defined agents use a `custom:` id prefix in a separate SQLite store (README; routers/custom_agents.py). Good separation of first-party vs user.

### Patterns to add in Phase 10 (BYOK multi-provider discoverability)

1. **A "concierge"/router persona** that the user talks to by default and which can _hand off_ to a specialist (or fan out to several and synthesize). This is the natural "natural-language drives the app" entry point — the user shouldn't have to pick "Buffett" to ask "is my portfolio overexposed to tech?"; a default copilot routes it.
2. **Provider transparency in the picker:** each agent has `defaultProvider`/`defaultModel`, user-overridable at invocation (types/ai.ts; \_schema.json). Surface "running on <provider>/<model>" in the chat so BYOK users know which key is being billed. Grey out agents whose `defaultProvider` has no key configured (except `ollama`, `requiresKey:false`).
3. **Capability badges** on each agent card derived from its `tools` allow-list ("reads fundamentals", "can backtest") so users discover what an agent can _do_, not just its vibe.

## B.4 UX for "natural language drives the app"

Concrete, implementation-ready patterns layered on the existing SSE streaming protocol (sidecar emits `data: <json>` SSE frames; frontend `EventSource` reassembles — sidecar/models/llm.py module docstring):

1. **Stream everything, narrate tool use.** The runtime already yields `LLMToolUseEvent` to the caller "so the UI can show 'using tool X…'" (agent_runtime.py ~240-241). Render these as inline status chips ("Reading your positions…", "Pulling AAPL fundamentals…"). This is the difference between "feels alive" and "spinner of death."
2. **Show, then act.** For UI actions (set symbol, open panel) the model executes the tool AND the response narrates it; the panel visibly changes. Tie the action tool's effect to the same panel-context bus so the chart actually moves.
3. **Confirm, never auto-execute, for money.** Any `propose_order` tool result renders the confirmation dialog (declined-by-default, agent named) per the LOCKED §6.5 contract. The chat shows "I've prepared this order — review and confirm" with the dialog, never "I placed it." (types/broker.ts `BrokerOrderSource` comment explicitly notes the auto-approve mode was _removed_ in v0.5.0.)
4. **Context preamble = "what you're looking at."** Because the panel snapshot is attached (B.2a), the user can say "what do you think of this?" and the agent knows "this" = the focused chart symbol. Make that resolution visible ("Looking at AAPL on the daily…") so the user trusts the agent saw the right thing.
5. **Tool-round cap is a feature, surface it.** `_MAX_TOOL_ROUNDS` (agent_runtime.py ~191) bounds runaway loops; if hit, tell the user "I gathered what I could in N steps" rather than silently truncating.
6. **BYOK error UX.** A 401 from a provider = "your <provider> key is invalid/expired," not a generic failure. The `LLMErrorEvent` path (anthropic.py ~114, openai.py ~113) should carry enough to render per-provider remediation.
7. **Persona-appropriate refusals.** buffett.json already declines market-timing questions ("that is not the framework"). Lean into this — an agent that knows its limits is more trustworthy than one that answers everything.

## B.5 Multi-provider abstraction (what to keep)

The existing design is the right one and should be the Phase-10 baseline:

- One internal message shape (`LLMMessage` with `role ∈ system|user|assistant|tool`, `tool_call_id`) that mirrors both APIs (types/ai.ts `LLMRole`, `LLMMessage`; sidecar/models/llm.py).
- One internal stream-event union (`LLMDeltaEvent`, `LLMToolUseEvent`, error, done) (sidecar/models/llm.py).
- Per-provider adapters translate to/from that shape (`anthropic.py`, `openai.py`; the OpenAI adapter is reused for OpenAI-compatible providers — deepseek/xai/groq — via `_provider_id`).
- Tools defined once (the `agent_tools` registry) and translated per provider (Anthropic `input_schema` vs OpenAI `function.parameters`).

**The only structural risk** is the OpenAI streaming-arg reassembly gap flagged in B.1 — fix/verify that before relying on OpenAI-family tool calls.

---

# Appendix — Concrete checklist for Phase 10

**Kite auth:**

- [ ] Loopback redirect via `tauri-plugin-oauth` (pinned port registered in Kite console); manual-paste fallback.
- [ ] `api_secret` Rust/keychain-only; checksum computed in Rust; never in webview JS or shipped to sidecar.
- [ ] Daily-token UX: launch-time staleness check (vs last 6 AM IST), 403/`TokenException` → one-tap reconnect, don't crash panels.
- [ ] `kite.py:_account_info`: use `equity.net` for buying power (not `available.cash`); also fetch `positions()` (`net`+`day`) not just holdings.
- [ ] `kite.py`: catch `TokenException` specifically → typed "session expired" outcome.
- [ ] Static-IP banner: clarify read-only panels keep working; only order placement is IP-gated.
- [ ] Source live quotes/candles from Vysted's own data layer, not Kite (per Zerodha's "execution platform only" stance).

**Agentic copilot:**

- [ ] Verify/fix OpenAI streaming tool-argument reassembly (per-`tool_call_id` buffer).
- [ ] Add UI-action tools (`set_chart_symbol`, `open_panel`, `add_to_watchlist`) wired to the panel-context bus.
- [ ] Add `propose_order` action tool routing through the LOCKED safety gate (proposal, declined-by-default, agent named) — never `place_order`.
- [ ] Add a default "concierge"/router persona with handoff to specialists.
- [ ] Surface provider/model + capability badges in the picker; grey out agents whose provider key is missing.
- [ ] Render tool-use events as inline status chips; narrate "what you're looking at" context resolution.
