# Phase 10 — AI / Chat Copilot Architecture Map (current state)

> Scope: full end-to-end map of the AI/chat surface as it ships today, the
> headline Phase-10 rebuild target. Every claim cites `file:line` against the
> actual source. Adversarial: where the docstrings/CLAUDE.md claim a capability,
> I verified whether the code actually delivers it.

---

## 0. TL;DR — the operator's complaint is correct, and worse than it looks

The chat surface is a **raw LLM passthrough** dressed up with an agent-persona
picker and a panel-context "badge". The two headline arcane commands (`/ask`,
`/agent`) are real and are the only two ways to send a message. The deeper
problem the operator may not realize:

1. **There is a tool-use loop in `agent_runtime.py` (lines 262–312) — but it is
   functionally dead in production.** No provider adapter ever sends a `tools`
   schema to the LLM API, so no real model ever emits a `tool_use` block, so the
   loop never iterates beyond the first stream. The loop is only ever exercised
   by tests that _mock_ the provider to fake a `tool_use` event
   (`tests/test_strategy_critic_e2e.py`). Today the system has the _plumbing_
   for agentic tool use but **zero real tool use**.
2. **Panel context is shipped as a raw JSON blob in a system message, and the
   personas are not told to act on it.** Buffett's prompt says "quote the
   company's reported figures _when the panel context supplies them_" — purely
   passive. Asking "what do you see" hits a model that received a JSON dump of
   panel state it was never instructed to interpret.
3. **`/ask` (raw chat) sends NO context and NO system prompt at all** — just
   `[{role: "user", content: prompt}]`. That is the literal definition of a
   passthrough chatbot.

So "is AAPL good" returns a generic non-answer because: (a) raw chat sends zero
context; (b) agent chat sends a context blob but the persona has no tools to
fetch fundamentals/price and is only weakly told to use the blob; (c) the model
_cannot_ call `price_data`/`fundamentals` even though those tools exist and are
registered, because no `tools` schema reaches the API.

---

## 1. Surface inventory (the files involved)

### Frontend (`src/`)

| File                                 | Role                                                                                     |
| ------------------------------------ | ---------------------------------------------------------------------------------------- |
| `src/modules/chat/ChatSidebar.tsx`   | The chat panel component (composer, transcript, agent picker, context badge, send logic) |
| `src/modules/chat/slash-commands.ts` | Pure parser for `/ask /agent /provider /key /clear /help`                                |
| `src/modules/chat/streaming.ts`      | SSE client — `fetch`-based stream parser for `/llm/chat` + `/agents/{id}/invoke`         |
| `src/modules/chat/index.ts`          | Module registration (`VystedModule`), command trigger `ask`                              |
| `src/store/chat-history.ts`          | In-memory conversation state + streaming reducer (no persistence)                        |
| `src/store/agents.ts`                | First-party + custom agent picker store                                                  |
| `src/store/llm-providers.ts`         | The seven BYOK providers + default-provider selection                                    |
| `src/store/panel-context.ts`         | The panel-context bus (publish/subscribe per panel)                                      |
| `src/lib/keychain.ts`                | Tauri keychain bindings (the only credential path)                                       |
| `types/ai.ts`                        | Wire contract: providers, streaming events, agent invocation envelope                    |

### Sidecar (`sidecar/`)

| File                                                            | Role                                                                    |
| --------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `sidecar/routers/llm.py`                                        | `GET /llm/providers`, `POST /llm/keys/validate`, `POST /llm/chat` (SSE) |
| `sidecar/routers/agents.py`                                     | `GET /agents`, `POST /agents/{id}/invoke` (SSE)                         |
| `sidecar/routers/custom_agents.py`                              | CRUD for Custom Agent Builder agents                                    |
| `sidecar/services/agent_runtime.py`                             | Discovers agent JSON, composes messages, runs the (dead) tool loop      |
| `sidecar/services/agents_store.py`                              | SQLite store for custom agents                                          |
| `sidecar/services/llm/base.py`                                  | `LLMProvider` ABC — `stream_chat` + `validate_key`                      |
| `sidecar/services/llm/{anthropic,openai,gemini,groq,ollama}.py` | Five adapter files, seven providers                                     |
| `sidecar/services/agent_tools/*`                                | Tool registry + 9 tool handlers                                         |
| `sidecar/models/{agent,llm,custom_agent}.py`                    | Pydantic wire models                                                    |
| `sidecar/agents/*.json`                                         | 12 first-party persona configs + `_schema.json`                         |

---

## 2. The two commands and how a message is routed

`parseSlashCommand` (`src/modules/chat/slash-commands.ts:39`) recognizes exactly:
`/ask`, `/agent`, `/provider`, `/key set`, `/clear`, `/help`, and bare text
(`raw`). Help text lives at `slash-commands.ts:92-99`.

`ChatSidebar.handleSend` (`ChatSidebar.tsx:99-222`) is the dispatcher:

- `/ask <prompt>` and bare text → **raw chat** path → `streamChat(...)`
  (`ChatSidebar.tsx:197-207`). If an agent is selected in the header dropdown,
  bare text routes to that agent instead (`ChatSidebar.tsx:138-143`).
- `/agent <id> <prompt>` → **agent** path → `streamAgentInvocation(...)`
  (`ChatSidebar.tsx:177-196`).
- `/provider`, `/key set`, `/clear`, `/help` → local store/UI side effects only,
  no network call (`ChatSidebar.tsx:106-134`).

There is no autocomplete, no command palette integration beyond opening the
panel (`src/modules/chat/index.ts:26-35` registers a single `chat.open` command
with trigger `ask`), and no natural-language routing — the user must type the
arcane commands or pre-select an agent in a `<select>` dropdown
(`ChatSidebar.tsx:313-342`).

---

## 3. What context actually reaches the model

### 3a. Raw chat (`/ask`) — ZERO context, ZERO system prompt

`ChatSidebar.tsx:198-206` calls `streamChat` with
`messages: [{ role: "user", content: prompt }]`. No system prompt, no panel
context, no history beyond the single turn. `streaming.ts:35-47` posts this
verbatim to `/llm/chat`, which forwards straight into `adapter.stream_chat`
(`routers/llm.py:72-77`). **This is a pure single-shot passthrough.** Note also
the raw-chat path does **not** send prior conversation turns — only the current
prompt — so `/ask` has no memory either.

### 3b. Agent chat (`/agent`) — a JSON context blob in a system message

`ChatSidebar.tsx:178-187` builds an `AgentContextSnapshot` from the panel-context
bus: `focusedSource`, `bySource` (per-panel `event.payload`), `capturedAt`.
`streaming.ts:50-72` posts it to `/agents/{id}/invoke`.

Server-side, `agent_runtime._compose_messages` (`agent_runtime.py:155-166`)
builds: `[system=persona prompt, system=context preamble (if any), user=prompt]`.
The context preamble (`agent_runtime.py:133-152`) renders:

```
## Terminal context (read-only — describe accurately, do not invent fields)
Focused panel: `<source>`
Per-panel state:
- `<source>`: <json.dumps(payload)>
```

So the model receives a **raw JSON dump of whatever each panel last published**,
keyed by source. There is no summarization, no schema explanation, no per-field
glossary. The model has to infer meaning from arbitrary panel payloads.

### 3c. Who publishes panel context (verified)

The bus (`src/store/panel-context.ts`) has real publishers (confirmed via grep):

- `src/modules/chart/ChartPanel.tsx:684`
- `src/modules/news/NewsFeedPanel.tsx:142`
- `src/modules/portfolio/PortfolioPanel.tsx:75`
- `src/modules/equity-overview/EquityOverviewPanel.tsx:130`
- `src/modules/watchlist/WatchlistPanel.tsx:54`

So context _is_ populated in a real workspace. The chat sidebar
(`ChatSidebar.tsx:58-64`) subscribes to three primitive slices and reassembles
the snapshot. **The context pipe works; the consumption is the weak link** —
it's dumped, not interpreted, and only on the `/agent` path, never on `/ask`.

The header badge (`ChatSidebar.tsx:344-353`, `describeContext` at
`ChatSidebar.tsx:466-493`) shows e.g. `Context: chart (AAPL, 1d)` — proof the
context exists, but it's cosmetic.

---

## 4. The agent persona system

### 4a. Definition + discovery

12 first-party personas ship as JSON under `sidecar/agents/`:
`buffett, dalio, druckenmiller, graham, klarman, lynch, marks, munger,
portfolio_advisor, researcher, soros, strategy_critic` (`ls sidecar/agents/`).
Each validates against `agents/_schema.json` (draft-07) at module import time
(`agent_runtime.py:62-109`). A malformed file is skipped with a log warning,
not fatal (`agent_runtime.py:83-104`). The registry is cached at import
(`agent_runtime.py:109`) and refreshable via `reload()` (tests only).

Schema fields: `id, name, philosophy, systemPrompt, tools[], defaultProvider,
defaultModel?, icon?` (`agents/_schema.json`). The Pydantic mirror is
`models/agent.py:21-38` (`AgentSpec`, `extra="forbid"`). This mirrors the locked
`types/plugin.ts → AgentSpec`.

> Gotcha already documented in CLAUDE.md: the `agents/` dir was NOT bundled into
> the PyInstaller binary for 3 releases (`L3-agents-dir-not-bundled`), so
> `/agents` returned `[]` and every persona was unavailable at runtime until
> v0.8.0 fixed the `--add-data` flag. Phase 10 inherits this fragility.

### 4b. How personas surface to the UI

`GET /agents` (`routers/agents.py:37-51`) returns `AgentSummary` — note the
**system prompt is deliberately withheld** from the wire (`models/agent.py:41-56`,
comment lines 43-48; store comment `src/store/agents.ts:8-10`). The UI only sees
`{id, name, philosophy, tools, default_provider, default_model, icon}`.

`useAgentsStore` (`src/store/agents.ts:174-252`) fetches both `GET /agents`
(first-party) and `GET /custom-agents` (custom, from `routers/custom_agents.py`).
The picker (`ChatSidebar.tsx:313-342`) renders them in two `<optgroup>`s. Custom
agents are SQLite-backed (`services/agents_store.py`) and authored via the
Agent Builder (`src/modules/agent-builder/`). Custom-agent ids are forced to a
`custom:` prefix (`src/store/agents.ts:44-49`).

**UX gap:** personas are a flat `<select>` dropdown plus a one-line
`philosophy` subtitle. There is no persona avatar/voice/persistent identity in
the transcript beyond a tiny uppercase label (`ChatSidebar.tsx:261`,
`message.agentId ?? "Assistant"`). No persona-specific empty states, no
suggested prompts, no "what can this agent do" affordance.

### 4c. The personas are passive by design

Reading the actual prompts:

- **Buffett** (`agents/buffett.json`): rich 400-word framework, but the only
  context instruction is _"You quote the company's reported figures when the
  panel context supplies them"_ — passive. No instruction to _call tools_ to
  fetch figures it doesn't have. No tool-use protocol described.
- **Strategy Critic** (`agents/strategy_critic.json`): declares
  `tools: [backtest_summary, price_data, fundamentals]` and a 9-section
  framework, but the prompt references "the backtest" as if it's already
  present; it doesn't instruct the model on _when/how_ to call a tool.

This matters: even if tool-calling were wired (it isn't — §5), the prompts
aren't written to drive an agentic loop.

---

## 5. Tools: registered, callable in isolation, but UNREACHABLE by the model

### 5a. The registry is real and populated

`services/agent_tools/__init__.py` is a clean registry: `register_tool`,
`is_registered`, `invoke_tool`, `registered_tools` (lines 46-67). Tools register
at startup in both entrypoints (`main.py:83-101`, `app.py:128-156`):

- import-time: `backtest_summary`
- `register_v0_5_0_tools()`: `price_data`, `fundamentals`
- `register_v0_6_0_tools()` (`registry_v0_6_0.py`): macro, sec, quant, earnings,
  analyst, screener tool families
- `register_v0_6_5_tools()`: **intentionally empty** — read-only Tradesa wrapper
  (`registry_v0_6_5.py`), guarded by the §6.5 audit grep.

The handlers are genuinely functional — e.g. `price_data._price_data`
(`agent_tools/price_data.py:17-79`) calls `provider_registry.get_history/get_quote`
and returns real OHLCV + quote dicts.

### 5b. The tool loop exists in the runtime

`agent_runtime.invoke_agent` (`agent_runtime.py:228-312`) has a full
agentic loop: on each `LLMToolUseEvent` it appends to `pending_tools`, yields it
to the UI, and when the stream's per-round `done` arrives it dispatches every
pending tool (`_dispatch_tool`, `agent_runtime.py:198-225`), appends a
`role="tool"` message keyed on `tool_call_id`, and re-calls the provider. Capped
at `_MAX_TOOL_ROUNDS = 6` (`agent_runtime.py:195`). `_dispatch_tool` even handles
unregistered tools gracefully (lines 213-217).

### 5c. THE FATAL GAP — no `tools` schema is ever sent to any provider

This is the headline finding. **No provider adapter passes a `tools` parameter
to the LLM API**, and **nothing builds a tool schema from `AgentSpec.tools`.**

Verified:

- `anthropic.py:92-99` — `stream_kwargs` is only `{model, max_tokens, messages,
[system]}` + raw `kwargs`. No `tools=`. So the Anthropic API returns no
  `tool_use` blocks, making `_translate_event`'s tool_use branch
  (`anthropic.py:162-170`) **dead code in production**.
- `openai.py:65-71` — `request_kwargs` is `{model, messages, stream,
stream_options}` + raw `kwargs`. No `tools=`. The `tool_calls` parsing
  (`openai.py:88-101`) never fires because no functions are declared.
- `gemini.py:65-77`, `groq.py:47-54`, `ollama.py:56-65` — same; no tool config.
- Grep for any `tools=` / `tool_schema` / `tool_choice` / `"tools"` build across
  `sidecar/services/` returns **only** `agents_store.py:94` (the `tools` column
  passthrough) — i.e. **zero** tool-schema construction anywhere.

The `AgentSpec.tools` allow-list (e.g. Buffett's
`["price_data","fundamentals","news"]`) is therefore **pure metadata** that
never leaves the persona config. The runtime never reads `spec.tools` to build a
provider tool definition — `invoke_agent` doesn't reference `spec.tools` at all
(it composes messages and streams; lines 252-312).

### 5d. The loop is only "proven" by mocked tests

`tests/test_strategy_critic_e2e.py:105-141` defines `_MockCriticProvider` that
_manually yields_ `LLMToolUseEvent(name="backtest_summary", ...)`. The e2e test
(lines 150-255) monkeypatches `get_provider` to return this mock. It proves the
_runtime plumbing_ works — not that a real LLM will ever trigger it. No test
sends a real `tools` schema to a real adapter. `test_agent_runtime.py` only uses
`tools` as config metadata (lines 33, 139), never the loop.

### 5e. Second-order bug if tools WERE wired: OpenAI tool-arg reassembly is broken

Even if a `tools` schema were sent, the OpenAI adapter forwards _each streaming
argument delta_ as a separate `LLMToolUseEvent` with
`input={"arguments_delta": <partial json str>}` (`openai.py:88-101`). The runtime
passes `event.input` straight to `invoke_tool` (`agent_runtime.py:219`), so the
tool would receive `{"arguments_delta": "{\"sym"}` fragments, never a
reassembled args object. The OpenAI streaming function-call protocol requires
accumulating `arguments` deltas by `tool_call.index` and parsing once at the end.
This is a latent bug Phase 10 must fix when it actually wires tools.

---

## 6. Provider abstraction + BYOK key flow

### 6a. The abstraction

`LLMProvider` ABC (`services/llm/base.py:33-74`): `stream_chat(messages, model,
api_key, **kwargs)` yielding the discriminated `LLMStreamEvent` union
(`base.py:30`), plus `validate_key`. Five adapter files cover seven providers —
`services/llm/__init__` dispatches OpenAI/DeepSeek/xAI through the one
OpenAI-shaped adapter via `base_url` override (`openai.py:35-47`, `provider_id`
informational). Catalog in `DEFAULT_PROVIDERS` (`src/store/llm-providers.ts:31-54`)
matches the sidecar's `PROVIDER_INFO`.

Each adapter translates the provider's native stream into neutral events:
text → `delta`, thinking → `thinking` (Anthropic only, `anthropic.py:157-160`),
final → `done` with usage. Errors are caught and emitted as `error` events so the
SSE always terminates.

### 6b. BYOK key flow (renderer → keychain → request body)

The flow is structurally clean and matches CLAUDE.md's documented pattern:

1. Key stored via `KeyEntryDialog` → `setSecret` → Tauri `keychain_set`
   (`src/lib/keychain.ts:50-52`). **Only Tauri Rust touches the OS keychain.**
2. On send, the frontend reads the key on demand:
   `getSecret(KEYCHAIN_NAMESPACES.llmProvider(provider))`
   (`ChatSidebar.tsx:155-164`). Namespace `llm-provider:<id>`
   (`keychain.ts:28`). If missing, it errors with `run /key set <provider>`.
3. The key rides in the request **body** as `api_key`
   (`streaming.ts:42` raw chat; `streaming.ts:64` agent) and is forwarded into
   `stream_chat` (`routers/llm.py:74`, `routers/agents.py:67`). The sidecar
   **never persists** it (`base.py:7-11`, `agent_runtime.py:18-19`).
4. The key is **never cached on the frontend** after the request
   (`ChatSidebar.tsx:30-32` comment; read on demand each send).

Validation: `POST /llm/keys/validate` (`routers/llm.py:47-59`) does a cheap
models-list probe before the key is saved.

> Note: for the **agent** path the frontend resolves the key using
> `defaultProviderId` even though the agent may declare a _different_
> `defaultProvider` (`ChatSidebar.tsx:147-159` sets `providerId = undefined` for
> agents, then `provider = providerId ?? defaultProviderId`). The runtime then
> resolves the agent's real provider server-side
> (`agent_runtime._resolve_provider_id`, `agent_runtime.py:169-170`). **Mismatch
> risk:** if the agent's default provider ≠ the UI default provider, the key
> read from the keychain is for the _wrong_ provider. This is a real BYOK bug on
> the agent path.

### 6c. Model defaults are hardcoded and stale-prone

Default model resolution is duplicated in **two** places:

- frontend `defaultModelFor` (`ChatSidebar.tsx:418-435`)
- sidecar `_resolve_model` (`agent_runtime.py:173-188`)
  Both hardcode e.g. `claude-opus-4-7`, `gpt-4.1-mini`. Drift between them (and
  against real model releases) is a maintenance trap. `types/ai.ts:38-45` notes
  models are meant to be free-form strings discovered via `POST /llm/models` — but
  that endpoint isn't wired into the chat send path.

---

## 7. Streaming / SSE

Wire protocol: `text/event-stream`, `data: <json>\n\n` frames, each frame one
`LLMStreamEvent` (`types/ai.ts:88-93`). Encoded server-side identically for both
endpoints (`routers/llm.py:92-99`, `routers/agents.py:85-91`).

Frontend can't use `EventSource` (POST + body), so `streaming.ts:74-125` uses
`fetch` with a manual reader/decoder and a `\n\n`-split frame parser. Events are
snake_case→camelCase normalized in `normalizeEvent` (`streaming.ts:150-187`),
which handles `delta`, `thinking`, `tool_use`, `done`, `error`. The
`ChatSidebar` `makeHandlers` (`ChatSidebar.tsx:443-463`) only acts on `delta`,
`error`, `done` — **`thinking` and `tool_use` events are silently dropped by the
UI** (no rendering of tool calls or reasoning). So even if the loop fired, the
user would see no "using tool X…" affordance despite the runtime yielding the
event (`agent_runtime.py:274`).

Chat history (`src/store/chat-history.ts`) is **in-memory only**, session-scoped
(comment lines 1-13). No persistence, no multi-thread, no resume. `clear`
(`/clear`) wipes it.

---

## 8. Every gap between today and a real terminal-aware agentic copilot

**A. No real tool use (highest priority).** The loop is dead because no `tools`
schema is sent (§5c). Fix requires: (1) per-adapter tool-schema serialization
from `AgentSpec.tools` → provider-native tool defs; (2) fix OpenAI streaming
arg-reassembly (§5e); (3) write personas/system prompts that drive tool use.

**B. `/ask` raw chat sends no context and no system prompt** (§3a). A
terminal-aware copilot should inject panel context (and a base system prompt) on
_every_ path, not only `/agent`.

**C. No conversation memory.** Raw chat sends only the current turn
(`ChatSidebar.tsx:202`); agent invocation sends only system+context+prompt
(`agent_runtime.py:155-166`). No prior turns are replayed to the model. History
is UI-only (`chat-history.ts`), never fed back. The copilot can't hold a thread.

**D. Context is dumped, not interpreted.** Panel state is `json.dumps`'d into a
system message (`agent_runtime.py:151`) with no summarization, no tool to _query_
live terminal state, no schema. "What do you see" forces the model to parse raw
payloads it was never taught to read.

**E. Personas are passive + thinly surfaced** (§4b, §4c). Flat dropdown, no
persona identity in transcript, prompts not written for agentic behavior,
system prompt withheld from UI (no transparency).

**F. UI drops `tool_use` and `thinking` events** (§7) — no tool-call timeline, no
reasoning display, no streaming "agent is doing X" UX.

**G. Arcane command UX** (§2) — `/ask` / `/agent <id>` with no autocomplete,
no NL routing, no slash-command palette.

**H. BYOK provider-mismatch bug on the agent path** (§6b) — key resolved for the
UI default provider, not the agent's declared provider.

**I. Duplicated/stale hardcoded model defaults** in FE + sidecar (§6c); the
`/llm/models` discovery endpoint exists in contract but isn't used by chat.

**J. No streaming of intermediate state / no cancel.** `streaming.ts` accepts an
`AbortSignal` (`streaming.ts:31`) but `ChatSidebar` never wires a stop button —
only a `disabled` composer while `streaming` (`ChatSidebar.tsx:42, 291`).

**K. No grounding tools for "what's on my screen."** There's no tool that lets
the model _pull_ current chart symbol / watchlist / positions on demand — it
only gets a one-shot snapshot blob. A real copilot needs read tools over live
terminal state, not a frozen dump.

**L. Distribution fragility.** The `agents/` dir bundling bug history
(CLAUDE.md `L3-agents-dir-not-bundled`) means the persona roster is only as
reliable as the PyInstaller `--add-data` flag. Any Phase-10 additions to
`agents/` or new data dirs inherit this.

---

## 9. Confidence

- §5 (dead tool loop, no `tools` sent): **9/10** — verified by reading all five
  adapters and grepping the entire `services/` tree for tool-schema construction;
  the only mock-driven proof is `test_strategy_critic_e2e.py`.
- §3 (context dumped, `/ask` contextless): **9/10** — read both code paths
  end-to-end.
- §6b (BYOK provider-mismatch on agent path): **7/10** — the code reads that
  way; worth a runtime check with an agent whose `defaultProvider` differs from
  the UI default before treating as a confirmed shipping bug.
- Everything else: **8/10**.
