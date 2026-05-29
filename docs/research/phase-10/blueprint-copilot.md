# Phase 10 — Agentic Terminal-Aware Copilot: Implementation Blueprint

> Author: AI-copilot track architect (headless). Date: 2026-05-29.
> Every claim is grounded against the actual source (file:line). This is the
> build spec for turning the chat surface from a raw LLM passthrough into THE
> headline feature: a real agentic copilot that reads live terminal state and
> can _drive_ the terminal, multi-provider BYOK, with a discoverable persona
> roster and no command arcana. Built directly within the LOCKED contracts —
> `types/plugin.ts`, `types/ai.ts`, and the §6.5 safety files are untouched.

---

## 0. The four problems, the four fixes, in one paragraph each

**Tool loop is dead (the #1 fix).** The runtime loop is real and correct
(`agent_runtime.py:263-311`) but **no adapter ever sends a `tools=` schema** to
any provider, so no model ever emits a `tool_use` block, so the loop never
iterates. Verified across all five adapters: `anthropic.py:92-99`,
`openai.py:65-71`, `gemini.py:65-77`, `groq.py`, `ollama.py:56-65` — none build
a tool definition. Fix: serialize `AgentSpec.tools` → per-provider tool schemas,
thread them through `stream_chat(**kwargs)`, and fix the OpenAI streaming
arg-reassembly bug (`openai.py:96-101` emits `{"arguments_delta": <fragment>}`
with no accumulator). This is the load-bearing change; everything else composes
on top of it.

**Context is dumped, not interpreted, and only on the agent path.** Panel state
is `json.dumps`'d into a system message (`agent_runtime.py:151`) with no schema,
no summary; `/ask` sends none at all (`ChatSidebar.tsx:198-206`). Fix: a
host-side **context provider** that renders a terse, labelled "what you're
looking at" preamble injected on _every_ path, **plus** a `get_terminal_state`
read-tool so the model can pull live state on demand instead of paying for a
frozen blob every turn.

**Personas are a flat `<select>` dropdown.** 12 strong JSON personas
(`sidecar/agents/`) surfaced as `<option>`s (`ChatSidebar.tsx:313-342`), no
avatar, no capability badges, no "what can this do". Fix: a clickable 3-pane
roster UI driven by extended sidecar JSON metadata (Tier-2, NOT the locked
contract) and a host-resolved view-model.

**Command arcana.** `/ask`, `/agent <id>` with no autocomplete, no NL routing
(`slash-commands.ts:39`). Fix: kill `/ask`+`/agent` as the _primary_ path —
bare text "just works" through a **router/concierge** that decides answer vs.
specialist hand-off vs. tool-driven action. Slash commands survive only as power
-user shortcuts; the LLM passthrough survives as an explicit fallback.

---

## 1. TERMINAL CONTEXT — what to capture and how to feed it

### 1.1 The state surfaces that already exist (verified publishers)

The panel-context bus (`src/store/panel-context.ts`) is live with real
publishers. Exact payloads on the wire today:

| Source            | file:line                     | `payload` shape (verified)                                        |
| ----------------- | ----------------------------- | ----------------------------------------------------------------- |
| `chart-<panelId>` | `ChartPanel.tsx:689-699`      | `{ symbol, timeframe, activeIndicators: string[], drawingCount }` |
| `watchlist`       | `WatchlistPanel.tsx:68-77`    | `{ symbols: string[], selectedSymbol: string \| null }`           |
| `portfolio`       | `PortfolioPanel.tsx:88-96`    | `{ positionCount, totalValue }`                                   |
| `news`            | `NewsFeedPanel.tsx:142`       | focused-article snapshot                                          |
| `equity`          | `EquityOverviewPanel.tsx:130` | equity-overview snapshot                                          |

Plus **live stores** the copilot can read directly (frontend-side, no bus):

- `useSymbolsStore` (`src/store/symbols.ts:40`) — the canonical watchlist
  (`entries: {symbol, assetClass}[]`).
- `useWorkspaceStore` (`src/store/workspace.ts:41`) — `dockviewApi`; open panels
  enumerable via `dockviewApi.panels` / `getPanel(id)`.
- `useModulesStore.enabledPanels()` — which modules/panels exist.
- `usePortfolioStore` / `useOrdersStore` — local positions + pending proposals.

**The pipe works; consumption is the weak link.** The fix is two-layer:
(a) a compact always-on preamble, (b) on-demand read tools. Do not enlarge the
preamble into a full state dump — that burns tokens every turn.

### 1.2 The context provider (NEW host module)

Create **`src/modules/chat/context-provider.ts`**. Single responsibility: turn
the live bus + stores into (a) a terse markdown "current view" preamble and
(b) a structured `TerminalState` object the `get_terminal_state` tool returns.

```ts
// src/modules/chat/context-provider.ts  (NEW)
import { usePanelContextBus } from "@/store/panel-context";
import { useWorkspaceStore } from "@/store/workspace";
import { useSymbolsStore } from "@/store/symbols";

/** Structured snapshot the copilot reasons over. Serialisable, no React types. */
export interface TerminalState {
  focusedPanel: string | null;
  /** The ticker the user is "looking at" — focused chart symbol, else watchlist selection. */
  focusedSymbol: string | null;
  charts: { panelId: string; symbol: string; timeframe: string; indicators: string[] }[];
  watchlist: { symbols: string[]; selected: string | null };
  portfolio: { positionCount: number; totalValue: number } | null;
  openPanels: string[];
  capturedAt: number;
}

/** Read the live stores once and assemble a structured snapshot. */
export function captureTerminalState(): TerminalState {
  /* read bus + stores */
}

/**
 * Render a SHORT preamble (<= ~200 tokens). Names the focused symbol, lists
 * open panels, top-line portfolio. Detail comes from get_terminal_state, NOT here.
 */
export function renderContextPreamble(s: TerminalState): string {
  // "## What the user is looking at\nFocused: chart AAPL (1d, RSI+VWAP). \
  //  Open panels: chart, watchlist, portfolio. Watchlist: AAPL, MSFT, NVDA, SPY. \
  //  Portfolio: 3 positions, $42,310. \
  //  When the user says \"this\"/\"it\", they mean AAPL unless they name another symbol."
}
```

The crucial line in the preamble is the **deixis resolution sentence**: _"When
the user says 'this' or 'it', they mean `<focusedSymbol>` unless they name
another symbol."_ This is what makes "is this cheap?" resolve to the chart
ticker — the single highest-leverage prompt-craft addition (the kite study
calls this out, §B.4.4).

### 1.3 Wire mechanism — preamble + tool, both

**Preamble (cheap, always-on).** Reuse the existing
`AgentContextSnapshot`/`context_snapshot` envelope — it is already in
`types/ai.ts:114-121` and `models/agent.py:59-69` and already flows over
`POST /agents/{id}/invoke` (`streaming.ts:57-70`). No contract change. The
host computes the preamble string client-side and passes the structured
snapshot; the sidecar renders it via the existing
`_build_context_preamble` (`agent_runtime.py:133-152`) — **but rewrite that
renderer** to consume the new structured shape with field labels instead of
`json.dumps` of arbitrary payloads. The snapshot's `by_source` map stays
`dict[str, Any]` (loose by design, `models/agent.py:68`), so the richer
`TerminalState` rides inside it under a reserved key without any model change:

```ts
// In ChatSidebar send path, replace the raw bySource map with the structured snapshot:
const terminalState = captureTerminalState();
const snapshot: AgentContextSnapshot = {
  focusedSource: terminalState.focusedPanel,
  bySource: { __terminal__: terminalState }, // reserved key; renderer special-cases it
  capturedAt: terminalState.capturedAt,
};
```

`agent_runtime._build_context_preamble` learns to special-case `__terminal__`
and emit the labelled markdown instead of `json.dumps` (it falls back to the
old per-source dump for any other key, preserving backward compat).

**Tool (precise, pull-based).** Add `get_terminal_state` to the tool catalog
(§2.3). The sidecar can't read the frontend's Zustand stores, so this tool
returns the `TerminalState` that was **passed in the request** — i.e. the
runtime stashes the inbound `context_snapshot.by_source["__terminal__"]` and the
`get_terminal_state` handler returns it. This lets a persona that needs full
detail (all open charts, every watchlist symbol) pull it without bloating every
turn's preamble. Implementation note: tool handlers are module-level
`async (dict) -> dict` (`agent_tools/__init__.py:41`) with no access to request
scope — so `get_terminal_state` is registered as a **per-invocation closure**
bound to the inbound snapshot (see §2.4), not a global registration.

---

## 2. AGENTIC TOOL LOOP — make the dead loop live

### 2.1 The tool catalog (the contract the model sees)

Define every tool once, provider-neutral, in a NEW module
**`sidecar/services/agent_tools/schemas.py`**. Each entry is a JSON-Schema tool
definition keyed by the same id used in the registry (`agent_tools/__init__.py`)
and in `AgentSpec.tools`.

```python
# sidecar/services/agent_tools/schemas.py  (NEW)
from typing import Any

#: Provider-neutral tool definitions: {id: {description, input_schema}}.
#: input_schema is JSON Schema (draft-07 subset both Anthropic + OpenAI accept).
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "price_data": {
        "description": "Recent OHLCV bars + latest quote for a symbol. Use to "
                       "check price, volatility, drawdown, or recent action.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker, e.g. AAPL or BTC/USDT"},
                "timeframe": {"type": "string", "enum": ["1d","1h","1wk","1mo"], "default": "1d"},
                "range": {"type": "string", "default": "6mo"},
                "asset_class": {"type": "string", "enum": ["equity","crypto"], "default": "equity"},
            },
            "required": ["symbol"],
        },
    },
    "fundamentals": { ... },       # mirrors fundamentals.py handler args
    "news": { ... },
    "screener_run": { ... },       # mirrors screener_tools.py / ScreenerRequest
    "macro_series": { ... },
    "sec_filings": { ... },
    "earnings": { ... },
    "analyst_ratings": { ... },
    "quant": { ... },
    "backtest_summary": { ... },
    # --- read tools over live terminal state ---
    "get_terminal_state": {
        "description": "Read what the user is currently looking at: open panels, "
                       "focused chart symbol + timeframe + indicators, watchlist, "
                       "and portfolio summary. Call this when the user refers to "
                       "'this', 'my chart', 'my watchlist', or 'my portfolio'.",
        "input_schema": {"type": "object", "properties": {}},
    },
    "get_portfolio": {
        "description": "Read the user's local portfolio positions with P&L.",
        "input_schema": {"type": "object", "properties": {}},
    },
    # --- action tools that DRIVE the terminal (host-executed, see §2.6) ---
    "open_panel": {
        "description": "Open or focus a terminal panel by id "
                       "(chart, watchlist, news, portfolio, equity, screener, macro, ...).",
        "input_schema": {"type": "object",
            "properties": {"panel": {"type": "string"}}, "required": ["panel"]},
    },
    "set_chart_symbol": {
        "description": "Load a symbol (and optional timeframe) into the chart panel.",
        "input_schema": {"type": "object",
            "properties": {"symbol": {"type": "string"},
                           "timeframe": {"type": "string", "enum": ["1d","1h","1wk","1mo"]}},
            "required": ["symbol"]},
    },
    "add_to_watchlist": {
        "description": "Add a symbol to the user's watchlist.",
        "input_schema": {"type": "object",
            "properties": {"symbol": {"type": "string"},
                           "asset_class": {"type": "string", "enum": ["equity","crypto"], "default": "equity"}},
            "required": ["symbol"]},
    },
    "propose_order": {
        "description": "Prepare a broker order for the user to REVIEW. This NEVER "
                       "places an order — it opens a confirmation dialog the user "
                       "must approve. Use only when the user explicitly asks to buy/sell.",
        "input_schema": { ...side/type/quantity/limit/stop... },
    },
}

def anthropic_tools(tool_ids: list[str]) -> list[dict]:
    """[{name, description, input_schema}] for the Anthropic Messages API."""
    return [{"name": tid, "description": TOOL_SCHEMAS[tid]["description"],
             "input_schema": TOOL_SCHEMAS[tid]["input_schema"]}
            for tid in tool_ids if tid in TOOL_SCHEMAS]

def openai_tools(tool_ids: list[str]) -> list[dict]:
    """[{type:'function', function:{name, description, parameters}}] for OpenAI/DeepSeek/xai/groq."""
    return [{"type": "function", "function": {
              "name": tid, "description": TOOL_SCHEMAS[tid]["description"],
              "parameters": TOOL_SCHEMAS[tid]["input_schema"]}}
            for tid in tool_ids if tid in TOOL_SCHEMAS]

def gemini_tools(tool_ids: list[str]) -> list[dict]:
    """Gemini function-declarations shape."""
    return [{"function_declarations": [
              {"name": tid, "description": TOOL_SCHEMAS[tid]["description"],
               "parameters": TOOL_SCHEMAS[tid]["input_schema"]} for tid in tool_ids
              if tid in TOOL_SCHEMAS]}]
```

> **SAFETY (§6.5) — naming is load-bearing.** `test_safety_end_to_end.py:358-366`
> greps `agent_tools.registered_tools()` for any id containing
> `place_order | submit_order | execute_order` and asserts the list is empty.
> The action tool is therefore named **`propose_order`** and is NEVER registered
> as a placement handler — it returns a proposal object only (§2.6). This keeps
> the audit green by construction.

### 2.2 Threading the schema through the loop

`invoke_agent` (`agent_runtime.py:228`) currently ignores `spec.tools`. Change:
read the allow-list, build the neutral id list, and pass it into the adapter as
a kwarg the adapter translates to its native shape.

```python
# agent_runtime.invoke_agent — inside the while loop, before adapter.stream_chat:
tool_ids = list(spec.tools)            # the allow-list, finally used
...
async for event in adapter.stream_chat(
    messages=messages,
    model=resolved_model,
    api_key=api_key,
    tool_ids=tool_ids,                  # NEW: neutral allow-list
    **(options or {}),
):
```

The base ABC `stream_chat` already accepts `**kwargs` (`base.py:42-48`), so
adding `tool_ids` is non-breaking. Each adapter pops `tool_ids` and builds its
native tool param:

```python
# anthropic.py stream_chat — after building stream_kwargs:
tool_ids = kwargs.pop("tool_ids", None)
if tool_ids:
    from services.agent_tools.schemas import anthropic_tools
    tools = anthropic_tools(tool_ids)
    if tools:
        stream_kwargs["tools"] = tools

# openai.py stream_chat — after building request_kwargs:
tool_ids = kwargs.pop("tool_ids", None)
if tool_ids:
    from services.agent_tools.schemas import openai_tools
    tools = openai_tools(tool_ids)
    if tools:
        request_kwargs["tools"] = tools
```

Gemini: `config["tools"] = gemini_tools(tool_ids)` before `generate_content_stream`.
Groq: OpenAI-shaped, same as openai. Ollama: tool-calling supported in recent
Ollama (`tools=` on `client.chat`) but **degrade gracefully** — if the local
model doesn't support tools the chat still streams text; pass `tools` only and
let Ollama ignore unsupported. The raw `/llm/chat` path passes no `tool_ids`
(it stays the passthrough fallback, §4.4).

### 2.3 Fix the OpenAI streaming arg-reassembly bug (REQUIRED)

`openai.py:88-101` forwards each `function.arguments` _fragment_ as its own
`LLMToolUseEvent(input={"arguments_delta": <partial json>})`. If tools fire,
`_dispatch_tool` (`agent_runtime.py:219`) feeds the model a fragment, not a
parsed args object. OpenAI streams tool-call args as deltas keyed by
`tool_call.index`; you MUST accumulate per index and parse once at the end of
the stream.

```python
# openai.py stream_chat — replace the per-delta yield with an accumulator:
tool_buffers: dict[int, dict[str, str]] = {}   # index -> {id, name, args}
...
for tool_call in tool_calls:
    idx = getattr(tool_call, "index", 0) or 0
    buf = tool_buffers.setdefault(idx, {"id": "", "name": "", "args": ""})
    if getattr(tool_call, "id", None):
        buf["id"] = tool_call.id
    fn = getattr(tool_call, "function", None)
    if fn is not None:
        if getattr(fn, "name", None):
            buf["name"] = fn.name
        if getattr(fn, "arguments", None):
            buf["args"] += fn.arguments
...
# When finish_reason == "tool_calls" (or stream ends with buffers pending):
for idx in sorted(tool_buffers):
    buf = tool_buffers[idx]
    try:
        parsed = json.loads(buf["args"]) if buf["args"] else {}
    except json.JSONDecodeError:
        parsed = {}
    yield LLMToolUseEvent(tool_call_id=buf["id"], name=buf["name"], input=parsed)
# THEN yield LLMDoneEvent.
```

Critically, the `tool_use` events are emitted **before** the round's
`LLMDoneEvent`, which is exactly what the runtime loop expects
(`agent_runtime.py:272-285`: it collects `pending_tools` then breaks on `done`).
Anthropic already emits whole `input` blocks (`anthropic.py:165-169`), so it is
correct as-is once `tools=` is sent. The OpenAI assistant turn must also be
appended to `messages` with its `tool_calls` so the follow-up `role:"tool"`
messages associate correctly — extend `_dispatch_tool`'s caller to append an
assistant message carrying the tool-call ids when the provider is OpenAI-shaped.
(Anthropic handles this server-side via `tool_use_id` in the `tool_result`
block, already mapped in `anthropic.py:53-66`.)

### 2.4 Per-invocation tools (terminal-state + actions)

`get_terminal_state`, `get_portfolio`, and the three action tools cannot be
plain globals — they need the inbound request's snapshot and they need to signal
the _frontend_ to act. Register them as **per-invocation closures** inside
`invoke_agent`, layered over the global registry:

```python
# agent_runtime.invoke_agent — build a local dispatch table:
async def _dispatch_tool(event, *, local_tools):
    if event.name in local_tools:
        return await local_tools[event.name](event.input)
    # ...existing global-registry path (agent_runtime.py:213-225)...

# inside invoke_agent, before the loop:
local_tools = {}
if context_snapshot is not None:
    ts = (context_snapshot.by_source or {}).get("__terminal__")
    local_tools["get_terminal_state"] = lambda _args, ts=ts: _async_return({"ok": True, "state": ts})
    local_tools["get_portfolio"] = lambda _args, ts=ts: _async_return(
        {"ok": True, "portfolio": (ts or {}).get("portfolio")})
# action tools resolve to a "host action" marker (see §2.6).
```

Read tools (`price_data`, `fundamentals`, `screener_run`, etc.) stay global
registrations as today (`agent_tools/__init__.py`) and reuse the existing
handlers unchanged — `price_data._price_data` (`price_data.py:17`),
`screener_tools._screener_run` (`screener_tools.py:27`), etc. No new data
plumbing; the only new thing is the _schema_ (§2.1) that finally makes them
reachable.

### 2.5 How tool results stream back to the UI

The streaming contract is unchanged on the wire (`LLMStreamEvent`,
`types/ai.ts:88-93`, `models/llm.py:71-106`) — `tool_use`, `delta`, `thinking`,
`done`, `error`. The runtime already yields `LLMToolUseEvent` to the caller
_before_ dispatching (`agent_runtime.py:274`). Two UI changes make this visible:

1. **Render `tool_use` events as inline status chips.** Today `makeHandlers`
   (`ChatSidebar.tsx:443-463`) only handles `delta`/`error`/`done` — `tool_use`
   and `thinking` are silently dropped (`streaming.ts:155-165` normalizes them
   but the handler ignores them). Add handling: on `tool_use`, push a transient
   "tool step" into the in-flight assistant message ("Pulling AAPL
   fundamentals…", "Reading your portfolio…", "Opening chart…").
2. **Add a `tool_result` echo event (optional, host-only).** For richer UX,
   after `_dispatch_tool` resolves, the runtime can yield a second
   `LLMToolUseEvent`-shaped frame with a `phase: "result"` flag — but this needs
   a new event kind. **Do NOT add an event kind** (would touch `types/ai.ts`,
   Tier-foundation). Instead, encode completion as a `delta` of nothing and keep
   the chip transition client-side (chip flips from "running" → "done" when the
   next `delta`/`tool_use`/`done` arrives). Zero contract change.

`chat-history.ts` gains a `toolSteps: ToolStep[]` field on `ChatMessage` (UI-only
type, not a wire type) so the transcript can render the timeline. This is a
local-store change (`src/store/chat-history.ts:19-34`), no contract impact.

### 2.6 Action tools and the §6.5 safety gate

Three action tools **DRIVE** the terminal. The sidecar cannot touch the DOM or
Zustand, so an action tool returns a **host-action directive** that the frontend
executes, then reports the outcome back to the model as the tool result.

Mechanism: the action tool's handler returns
`{"ok": True, "host_action": {"type": "set_chart_symbol", "args": {...}}}`. The
runtime yields this as a normal `LLMToolUseEvent` (the model sees it), AND the
_frontend_ streaming handler recognises a `host_action` and executes it
client-side. But tool _results_ must feed back to the model server-side for the
loop to continue — so the cleaner design is:

- **UI-action tools (`open_panel`, `set_chart_symbol`, `add_to_watchlist`)** are
  resolved **on the frontend**, not the sidecar. When the runtime emits a
  `tool_use` for one of these, the sidecar's local dispatch returns a synthetic
  success immediately (`{"ok": true, "applied": true, "note": "executed on host"}`)
  so the loop continues, AND the frontend, on seeing that `tool_use` event,
  performs the real action against the live stores:

  ```ts
  // ChatSidebar handler, on tool_use:
  switch (event.name) {
    case "set_chart_symbol":
      useChartSyncBus.getState().setSymbol("copilot", String(event.input.symbol));
      // (chart panels subscribed to the symbol flavor pick it up; chart-sync.ts:81)
      break;
    case "open_panel":
      useWorkspaceStore.getState().openPanel(String(event.input.panel)); // workspace.ts:46
      break;
    case "add_to_watchlist":
      useSymbolsStore
        .getState()
        .addSymbol(String(event.input.symbol), event.input.asset_class ?? "equity"); // symbols.ts:42
      break;
  }
  ```

  This reuses existing drive surfaces verbatim — `openPanel`
  (`workspace.ts:46`), `setSymbol` (`chart-sync.ts:81`), `addSymbol`
  (`symbols.ts:42`). No new control-plane needed; these are pure UI actions and
  safe to auto-execute (the kite study §B.2 blesses this).

- **`propose_order` routes through the LOCKED §6.5 gate, never auto-executes.**
  Its handler does NOT place an order. It returns a directive the frontend turns
  into a `BrokerOrderProposal` with `source: "ai-agent"` and
  `sourceDetails: {agentId, agentName}` (`types/broker.ts:130-136`), pushed to
  `useOrdersStore.addProposal` (`orders.ts:60`). The
  `OrderConfirmationDialog` opens **defaulted to declined** — the user must tick
  "I reviewed this AI-proposed order" to enable Confirm (`orders.ts:11-18`
  comment; `BrokerOrderSource` comment `broker.ts:95-101`). The AI layer has
  **no path** to `confirm_and_place`. The tool result fed back to the model is
  `{"ok": true, "proposal_created": true, "status": "awaiting_user_review"}` —
  the model says "I've prepared this order for your review," never "I placed it."

> This is the one place where the action does NOT auto-apply. Encode the
> distinction in the system prompt of any tool-using persona: _"`propose_order`
> prepares an order for the user to approve. It never executes. Tell the user to
> review and confirm."_

### 2.7 Tool-round cap, error recovery (already correct)

`_MAX_TOOL_ROUNDS = 6` (`agent_runtime.py:195`) bounds runaway loops — keep it.
`_dispatch_tool` already swallows unregistered/raising tools into a JSON error
the model can recover from (`agent_runtime.py:212-225`) — keep it. When the cap
is hit, surface "I gathered what I could in N steps" rather than silent
truncation (UI string in `makeHandlers`).

---

## 3. PERSONA ROSTER — discoverable, clickable, composable

### 3.1 Extend the SIDECAR JSON (Tier-2), NOT the locked contract

`AgentSpec` (`types/plugin.ts:143-158`) is LOCKED — do not touch it. But the
`sidecar/agents/_schema.json` (`_schema.json`) is a **sidecar-internal
convention** (its own description says it "mirrors" the contract; the fincept
study §1 confirms it's Tier-2 and may evolve). Add OPTIONAL fields with
`additionalProperties:false` relaxed to allow them:

```jsonc
// _schema.json — add OPTIONAL properties (keep required[] unchanged):
"category":      { "type": "string", "enum": ["investor","macro","research","quant","execution","router"] },
"capabilities":  { "type": "array", "items": { "type": "string" } },   // searchable tags
"recommendedModel": { "type": "string" },                              // distinct from defaultModel
"sampleQuestions":  { "type": "array", "items": { "type": "string" } } // empty-state suggestions
```

These never reach `AgentSpec` (the Pydantic `AgentSpec` has
`extra="forbid"`, `models/agent.py:29`). **Two options, pick the clean one:**
relax `AgentSpec` to `extra="ignore"` (Tier-2 sidecar model change, NOT the TS
contract) so the JSON validates, OR add the new fields to a **separate**
`AgentRosterMeta` Pydantic model loaded alongside the spec. Use the second — it
keeps `AgentSpec` byte-identical to the locked TS type and isolates the new
metadata. The agent runtime loads both from the same file:

```python
# models/agent.py — NEW model, does not touch AgentSpec:
class AgentRosterMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")
    category: str = "research"
    capabilities: list[str] = Field(default_factory=list)
    recommended_model: str | None = Field(default=None, alias="recommendedModel")
    sample_questions: list[str] = Field(default_factory=list, alias="sampleQuestions")
```

### 3.2 New endpoint: `GET /agents/roster`

`GET /agents` (`agents.py:37-51`) returns `AgentSummary` (no system prompt —
correctly withheld, `models/agent.py:41-48`). Add a sibling that includes the
roster metadata + a derived capability summary from `tools`:

```python
# routers/agents.py — NEW:
@router.get("/roster")
def get_roster() -> list[AgentRosterEntry]:
    return [
        AgentRosterEntry(
            id=spec.id, name=spec.name, philosophy=spec.philosophy,
            icon=spec.icon, default_provider=spec.default_provider,
            default_model=spec.default_model,
            category=meta.category, capabilities=meta.capabilities,
            recommended_model=meta.recommended_model,
            sample_questions=meta.sample_questions,
            tool_badges=_tool_badges(spec.tools),     # ["reads fundamentals","can screen"]
        )
        for spec, meta in agent_runtime.list_roster()
    ]
```

`_tool_badges` maps tool ids → human badges ("price_data" → "reads price",
"screener_run" → "can screen", "propose_order" → "can prepare orders"). The
system prompt stays server-side; the roster never leaks it.

### 3.3 The roster UI (3-pane, clickable — replaces the `<select>`)

Replace the `<select>` AgentPicker (`ChatSidebar.tsx:313-342`) with a roster
surface. Two presentations:

- **Inline roster strip** in the chat header: clickable avatar chips (Lucide
  `icon`) for the top personas + a "Browse all" button.
- **Full roster panel** (NEW `src/modules/chat/AgentRoster.tsx`), opened by
  "Browse all" or the cmd+K command `roster.open`. 3-pane like fincept's
  `AgentsViewPanel` (study §1): left = list grouped by `category` with count
  chips + a search box filtering on `name`/`capabilities`/`philosophy`; center =
  selected persona card (icon, name, philosophy, capability badges, "running on
  `<provider>/<model>`", greyed if the provider key is missing); right = sample
  questions (clickable → fills the composer and sends).

```tsx
// AgentRoster.tsx (NEW) — driven by useAgentsStore extended with roster meta.
// Grey-out logic reuses the keychain probe:
const hasKey = useProviderKeysStore((s) => s.status[entry.defaultProvider] === "present");
const usable = entry.defaultProvider === "ollama" || hasKey; // ollama requiresKey:false
```

Store change: `useAgentsStore` (`src/store/agents.ts`) gains a
`rosterMeta: Record<string, AgentRosterEntry>` slice fetched from
`GET /agents/roster`, joined to the existing `firstPartyAgents`. Custom agents
(`GET /custom-agents`) get a synthetic `category: "custom"` + badges derived
from their `tools`. The `AgentSummary` picker selectors
(`agents.ts:262-278`) stay; the roster reads the richer slice.

### 3.4 Persona transcript identity

Today the assistant label is a tiny uppercase `message.agentId ?? "Assistant"`
(`ChatSidebar.tsx:261`). Give each persona message its **icon + name** header
(resolve from `rosterMeta[agentId]`), so a Buffett answer reads as Buffett. This
is pure rendering in the transcript `<li>` (`ChatSidebar.tsx:251-274`).

### 3.5 How a persona composes with the loop + context

A persona is just an `AgentSpec` whose `systemPrompt` encodes a framework and
whose `tools` allow-list is now _live_. Composition:

1. User picks a persona (or the router picks one, §4) → `streamAgentInvocation`.
2. `invoke_agent` composes `[system=persona prompt, system=context preamble,
user=prompt]` (`agent_runtime.py:155-166`) **and** sends the persona's
   `tools` schema (§2.2).
3. The persona reasons, calls its allow-listed tools (Buffett:
   `price_data`/`fundamentals`/`news` + `get_terminal_state`), the loop runs,
   the answer is grounded in real fetched data — not a generic non-answer.

**Rewrite the persona prompts to drive tools.** Buffett's prompt currently says
"quote reported figures _when the panel context supplies them_"
(`buffett.json:5`) — passive. Change to: _"When you need a figure you don't
have, call `fundamentals` or `price_data`. When the user says 'this', call
`get_terminal_state` to learn the focused symbol, then proceed."_ Steal the
fincept prompt skeleton (study §1.4): **BEFORE you answer / INPUTS (named tools)
/ FRAMEWORK / OUTPUT / DO NOT**. Every shipped persona's `tools` array gains
`get_terminal_state` so "what do you think of this?" always resolves.

---

## 4. NATURAL INTERACTION — kill the command arcana

### 4.1 The default: bare text "just works"

Today bare text routes to raw chat unless an agent is pre-selected
(`ChatSidebar.tsx:138-143`), and `/ask`/`/agent` are the documented entry points
(`slash-commands.ts:92-99`). Flip the model: **bare text is the only thing the
user needs.** It goes to a **router** that decides what to do. The composer
placeholder becomes "Ask anything — your portfolio, a chart, a screen…" not
"/ask a question, /agent buffett <prompt>".

### 4.2 The router (concierge persona)

Add a first-party `sidecar/agents/copilot.json` — `category: "router"`, the
**default selected agent on launch** (`activeAgentId` defaults to `"copilot"`
in `ChatSidebar.tsx:66`). Its tool allow-list is the FULL catalog (read +
action + `get_terminal_state`). Its system prompt makes it the concierge:

> _You are Vysted's terminal copilot. The user talks to you in plain language.
> You have tools to read what they're looking at and to drive the terminal.
> Decide: (a) answer directly if it's general; (b) call `get_terminal_state` +
> data tools to answer grounded questions ("is AAPL cheap", "how's my
> portfolio"); (c) take an action when asked ("pull up TSLA" → `set_chart_symbol`;
> "add NVDA to my watchlist" → `add_to_watchlist`); (d) for deep single-lens
> analysis, recommend a specialist persona by name. Never invent figures —
> fetch them._

This makes "ask about my portfolio" call `get_portfolio` and answer; "pull up
Tesla" call `set_chart_symbol`; "is this a good buy" call `get_terminal_state`
then `fundamentals`. No command, no agent id, no arcana.

### 4.3 Routing/intent — model-native, not a rules engine

**Do not build a separate intent classifier.** The router IS the intent
classifier: tool-calling over a capable model is exactly intent routing — the
model picks the tool (= the action) from the catalog. This is the whole point of
the agentic loop. For the **hand-off to a specialist**, two patterns, ship both:

1. **Soft hand-off (default):** the router answers, and if a specialist lens
   fits, it ends with "Want Buffett's value take on this?" rendered as a
   clickable chip (parse a structured suggestion the router emits, or just let
   the user click the named persona in the roster strip). Cheap, no new wire.
2. **Hard hand-off (a `delegate` tool):** add `delegate_to_persona` to the
   router's catalog: `{persona_id, question}`. Its handler invokes the target
   agent server-side via `invoke_agent` (recursive, capped at depth 1) and
   streams the specialist's answer back as the tool result. This is the
   fincept "teams" idea (study §1, deferred there) but scoped to a single
   hop — buildable now, no contract change. Mark it `depth=1` so a router can't
   chain personas infinitely.

### 4.4 Slash commands survive as power-user shortcuts + the passthrough fallback

Keep `slash-commands.ts` but demote it: `/agent <id>` still force-routes to a
named persona (power users), `/ask` still force-routes to **raw passthrough**
(`/llm/chat`, no tools, no context — the explicit "just talk to the raw model"
escape hatch the brief requires). `/provider`, `/key set`, `/clear`, `/help`
stay. The difference: they're optional accelerators, not the documented primary
path. The empty-state (`ChatSidebar.tsx:355-372`) changes from "Type /ask…" to
"Ask me anything about what you're looking at" + 3 clickable sample questions
from the router's `sampleQuestions`.

### 4.5 Conversation memory (fixes gap C)

Today no prior turns are replayed (raw chat sends only the current prompt,
`ChatSidebar.tsx:202`; agent invocation sends only system+context+prompt,
`agent_runtime.py:155-166`). A copilot must hold a thread. Pass the recent
transcript: extend `AgentInvocationRequest` consumption — the request already
carries `prompt`; add the prior turns by having `ChatSidebar` send the last N
messages as part of the composed conversation. Since `_compose_messages`
(`agent_runtime.py:155`) builds the messages list, thread an optional `history:
list[LLMMessage]` through `AgentInvocationRequest.options` (which is already a
free-form `dict[str, Any]`, `models/agent.py:83`) — **no model field change**.
`_compose_messages` inserts history between the context preamble and the new
user prompt. Cap at ~10 turns to bound tokens.

---

## 5. EXACT FILE MANIFEST

### Create

- `sidecar/services/agent_tools/schemas.py` — `TOOL_SCHEMAS` + `anthropic_tools`/`openai_tools`/`gemini_tools`. **The keystone file.**
- `sidecar/agents/copilot.json` — the default router/concierge persona (full tool allow-list, `category:"router"`).
- `src/modules/chat/context-provider.ts` — `captureTerminalState` + `renderContextPreamble`.
- `src/modules/chat/AgentRoster.tsx` — 3-pane clickable persona roster.
- `sidecar/tests/test_tool_loop_e2e.py` — real tool-schema serialization tests + OpenAI arg-reassembly test (the gap §2.3).
- `sidecar/tests/test_action_tools.py` — `propose_order` returns a proposal, never places; UI-action tools return host directives; §6.5 grep still green.

### Modify (sidecar)

- `sidecar/services/agent_runtime.py` — pass `tool_ids` to `stream_chat` (§2.2); per-invocation local tools (§2.4); special-case `__terminal__` in `_build_context_preamble` (§1.3); thread `history` (§4.5); append OpenAI assistant tool-call message before tool results (§2.3).
- `sidecar/services/llm/anthropic.py` — build + send `tools=` from `tool_ids` (§2.2).
- `sidecar/services/llm/openai.py` — build + send `tools`; **fix streaming arg reassembly** (§2.3).
- `sidecar/services/llm/gemini.py` — `config["tools"]` from `tool_ids`; emit `LLMToolUseEvent` on function-call parts.
- `sidecar/services/llm/groq.py` — same as openai (OpenAI-shaped).
- `sidecar/services/llm/ollama.py` — pass `tools=`, degrade gracefully.
- `sidecar/routers/agents.py` — `GET /agents/roster` (§3.2).
- `sidecar/models/agent.py` — `AgentRosterMeta` + `AgentRosterEntry` (NOT `AgentSpec`); `list_roster()` helper in `agent_runtime.py`.
- `sidecar/agents/_schema.json` — optional `category`/`capabilities`/`recommendedModel`/`sampleQuestions` (§3.1).
- `sidecar/agents/*.json` — rewrite persona prompts to drive tools; add `get_terminal_state` to each `tools` array; add roster meta fields.

### Modify (frontend)

- `src/modules/chat/ChatSidebar.tsx` — default to `copilot` agent; render `tool_use` chips + thinking; persona transcript identity; capture+send `TerminalState`; new empty-state; roster strip.
- `src/modules/chat/streaming.ts` — handle host-action `tool_use` events (execute against stores); pass `history`.
- `src/modules/chat/slash-commands.ts` — demote to power-user shortcuts (keep parser, change help/empty-state copy).
- `src/store/chat-history.ts` — add `toolSteps` UI field to `ChatMessage`.
- `src/store/agents.ts` — add `rosterMeta` slice from `GET /agents/roster`.
- `src/modules/chat/index.ts` — register `roster.open` command + `AgentRoster` panel component.

### LOCKED — DO NOT TOUCH

- `types/plugin.ts` (`AgentSpec`, `CommandSpec`, all capabilities). Everything above fits the existing `AgentSpec` and the existing `AgentSpec.tools` allow-list.
- `types/ai.ts` (`LLMStreamEvent`, `LLMMessage`, `AgentContextSnapshot`, `AgentInvocationRequest`). No new event kinds, no new fields — `options` carries `history`; `by_source.__terminal__` carries the structured state.
- `sidecar/models/audit_log.py`, `kill_switch.py`, `broker_base.py`, `tests/test_safety_end_to_end.py` (§6.5). `propose_order` is named to pass the `place_order|submit_order|execute_order` grep (`test_safety_end_to_end.py:358-366`); the AI never reaches `confirm_and_place`.

---

## 6. REQUEST / RESPONSE / STREAMING CONTRACT (unchanged wire, richer use)

- **Endpoint:** `POST /agents/{agent_id}/invoke` (SSE) — unchanged
  (`agents.py:54-77`). Default `agent_id = "copilot"`.
- **Request body** (`AgentInvocationRequest`, `models/agent.py:72-83`) —
  unchanged fields. `context_snapshot.by_source.__terminal__ = TerminalState`.
  `options.history = LLMMessage[]` (last ~10 turns). `options.tool_ids` is
  derived server-side from `spec.tools`, not client-sent.
- **BYOK key fix (gap H):** the agent path currently resolves the key for the UI
  `defaultProviderId`, not the agent's `defaultProvider`
  (`ChatSidebar.tsx:147-159`). Fix: read `entry.defaultProvider` (now available
  from the roster meta) to choose the keychain namespace
  (`KEYCHAIN_NAMESPACES.llmProvider(...)`, `keychain.ts:28`) before sending.
- **Stream:** `text/event-stream`, `data: <json>\n\n`, one `LLMStreamEvent` per
  frame (`llm.py:92-99`, `agents.py:85-91`). Event kinds unchanged. `tool_use`
  events now actually fire (the loop is live) and the UI renders them as chips.
- **Fallback:** `POST /llm/chat` (`llm.py:62-84`) stays the raw passthrough —
  no `tool_ids`, no context, reached via `/ask`. This is the explicit
  "talk to the bare model" escape hatch.

---

## 7. RISKS / OPEN QUESTIONS

- **OpenAI assistant-turn reconstruction (§2.3).** The OpenAI follow-up after a
  tool call requires the prior assistant message to carry the `tool_calls` array
  so `role:"tool"` messages associate by `tool_call_id`. `LLMMessage`
  (`models/llm.py:48-54`) has no `tool_calls` field. Solution without a contract
  change: the OpenAI adapter reconstructs the assistant tool-call message from
  the `role:"tool"` messages it receives (it knows the ids). Verify this round-
  trips before relying on multi-round OpenAI tool use. Confidence 7/10.
- **Ollama tool support varies by model.** `tools=` works on newer Ollama models
  (llama3.1+) but silently no-ops on others. Must degrade to text-only chat, not
  error. Confidence 7/10.
- **Gemini function-call streaming shape** (`gemini.py`) — the current adapter
  has no tool path at all; the function-call parts arrive as
  `candidate.content.parts[].function_call`. Needs a direct read of the
  google-genai streaming surface to emit `LLMToolUseEvent` correctly. Confidence
  6/10 — verify against the installed SDK.
- **`agents/` bundling fragility** (CLAUDE.md `L3-agents-dir-not-bundled`).
  Adding `copilot.json` inherits the `--add-data "agents:agents"` PyInstaller
  requirement; the new `schemas.py` is a normal Python module (auto-discovered),
  safe. Confirm the copilot persona ships in the binary via the smoke-test.
- **`extra="forbid"` on `AgentSpec`** (`models/agent.py:29`) will reject the new
  JSON fields unless the loader reads them via the separate `AgentRosterMeta`
  model (§3.1). If a teammate instead relaxes `AgentSpec` to `extra="ignore"`,
  flag it — it diverges from the locked TS `AgentSpec`. Use the separate model.
- **Token cost of always-on preamble + history.** Keep the preamble terse
  (§1.2) and cap history at ~10 turns; push detail into `get_terminal_state`.
