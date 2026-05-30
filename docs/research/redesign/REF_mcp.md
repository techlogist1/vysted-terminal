# REF_mcp — Exposing Vysted as an MCP framework external agents build on

Research reference for the redesign. Goal: turn the Vysted sidecar into an
**MCP server** that external agents (Claude Code, Claude Desktop, Cursor, any
MCP client) can drive — same capability layer the built-in Copilot uses. This
is the "app as a framework" move: one tool catalog, two consumers.

**Bottom line up front:** Vysted *already* ships a FastMCP server
(`sidecar/services/mcp_server.py`) mounted at `/mcp` over Streamable-HTTP, and
*already* has a built-in agent runtime that consumes a tool catalog
(`sidecar/services/agent_tools/`). The redesign work is not "build an MCP
server from scratch" — it is **unifying the two tool surfaces into one catalog,
broadening coverage to all eight domains, formalising the read-only/mutation
gate with MCP annotations, and deciding the dual-transport story** (HTTP for
the running app + stdio for headless/CI use). The rest of this doc is the
evidence + the recommended architecture.

---

## 1. MCP primitives: tools vs resources vs prompts

The protocol exposes three server-side primitives, distinguished by **who
controls invocation** ([modelcontextprotocol.io spec][spec-prompts],
[WorkOS features guide][workos]):

| Primitive | Controlled by | Purpose | Side effects | Vysted fit |
|---|---|---|---|---|
| **Tools** | **Model** | Actions the LLM decides to call (query API, run computation, mutate state). The client may surface name/args and ask the user to confirm before invoking. | Allowed | quotes, history, fundamentals, screener, quant, news, portfolio reads; chart/watchlist drives; `propose_order` |
| **Resources** | **Application** | Read-only contextual data the host injects into the model's context — "knowledge, not doing." Addressed by URI, no side effects. | None | the current workspace blob, the watchlist, a system/onboarding prompt, a portfolio snapshot, a saved-strategy doc |
| **Prompts** | **User** | Pre-defined instruction templates / multi-step workflows the user explicitly selects (slash-command style). Can reference resources + tools. | None directly | "equity workup", "macro regime read", "portfolio risk review" — canned analyst playbooks |

Key design rule from the spec: **tools are model-controlled, resources are
app-controlled, prompts are user-controlled** ([WorkOS][workos],
[Anthropic course][anthropic-course]). Don't model read-only context as a tool
when a resource is the honest primitive — but note the practical reality below.

**Practical caveat (important for Vysted):** most clients today (including
Claude Code as an MCP *client*) consume **tools** far more reliably than
resources or prompts — resource/prompt support is uneven across clients. OpenBB
made the same call: it exposes everything as **tools** and uses a single
`resource://system_prompt` resource for onboarding only ([OpenBB MCP
docs][openbb-mcp]). **Recommendation: lead with tools for every capability,
add a *small* set of resources (workspace, system prompt) and prompts (canned
workflows) as progressive enhancement — never make a capability *only*
reachable via resource/prompt.**

---

## 2. Transport: stdio vs HTTP/SSE/Streamable-HTTP

FastMCP supports stdio, HTTP, SSE, and Streamable-HTTP ([FastMCP /
KDnuggets][kdnuggets], [DeepWiki][deepwiki]):

- **stdio** — subprocess over stdin/stdout, no network. Ideal for local
  editor integrations (Claude Desktop, Cursor) that *spawn* the server. Auth is
  inherited from the local process environment — no token layer
  ([FastMCP auth docs][fastmcp-auth]).
- **SSE** — legacy server-initiated streaming over HTTP. Being superseded.
- **Streamable-HTTP** — *the current standard for remote MCP and FastMCP's
  recommended production transport* ([FastMCP][kdnuggets]). Single endpoint,
  supports stateful sessions (`mcp-session-id` header) **or** stateless mode.

**What Vysted does today:** Streamable-HTTP, `stateless_http=True`, mounted at
`/mcp` in the main FastAPI app (`mcp_server.py:351` `get_streamable_http_app`,
`app.py:213` `app.mount("/mcp", ...)`). Protocol revision `2025-06-18`. This is
the right call for an app that is *already running* — the agent connects to the
live terminal's port (`http://127.0.0.1:<port>/mcp/`).

**The gap for "framework others build on":** the HTTP server only exists while
the Tauri app is running, and its port is assigned at launch
(`CLAUDE.md` stack note). An external agent in Claude Code needs either (a) a
discoverable port, or (b) a **stdio entrypoint** it can spawn headless without
the GUI. OpenBB ships exactly this dual story — the same `openbb-mcp` binary
runs `--transport stdio` for Claude Desktop *or* `--transport streamable-http`
(default) for a long-lived server ([OpenBB MCP docs][openbb-mcp]).

**Recommendation:**

1. **Keep Streamable-HTTP stateless at `/mcp`** for the in-app path (Copilot
   path is in-process; external clients attach to the live terminal).
2. **Add a stdio entrypoint** — a thin `python -m vysted.mcp` / PyInstaller
   binary that boots the FastAPI app headless (or just the tool layer) and
   serves the *same* FastMCP instance over stdio. This is what makes Vysted a
   framework Claude Code can spawn without the desktop app open.
3. **Publish the live port** to a well-known location (lockfile in app data dir,
   or a `.mcp.json` Vysted writes on launch) so an attached client can find it.
   Claude Code reads project `.mcp.json` for HTTP server URLs.

---

## 3. FastMCP idioms (Python) — the server you write

FastMCP turns typed Python functions into tools with zero schema boilerplate
([FastMCP tools docs][fastmcp-tools], [gofastmcp][kdnuggets]):

```python
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

mcp = FastMCP("vysted")

@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def get_quote(symbol: str) -> dict:
    """Latest quote for an equity/crypto symbol. e.g. AAPL, BTC/USDT."""
    ...  # returns a dict
```

Load-bearing idioms:

- **Schema is auto-generated** from type hints + docstring. Param descriptions
  via `Annotated[str, "..."]` or `Annotated[int, Field(description=..., ge=1, le=1000)]`.
- **Async tools** run on the loop; sync tools auto-offload to a thread pool.
- **Return a dict (or a Pydantic model / dataclass)** for structured content.
  *Vysted gotcha already in CLAUDE.md: FastMCP rejects a bare list/scalar —
  `structured_content must be a dict`. Wrap lists as `{"agents": [...]}`.*
- **`ToolAnnotations`** carry safety *hints* without spending context tokens:
  `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`
  ([FastMCP tools][fastmcp-tools]). These are **advisory** — a client *may*
  use them to skip confirmation on read-only tools — not an enforcement
  boundary. Enforce separately (§5).
- **Tags + enable/disable** for visibility: `@mcp.tool(tags={"broker"})` then
  `mcp.enable(tags={"public"}, only=True)` for an allowlist; disabled tools
  don't list and can't be called ([FastMCP tools][fastmcp-tools]).
- **Errors:** raise `fastmcp.exceptions.ToolError` for client-safe messages;
  with `mask_error_details=True` only `ToolError` text reaches the client.

**Vysted's current shim pattern is good and should be kept:** each MCP tool is a
thin adapter that calls the host FastAPI endpoint via an in-process
`httpx.ASGITransport` client (`mcp_server.py:71` `_internal_client`). No logic
duplication — a router fix propagates to the MCP surface for free. This is the
same "REST-endpoint → MCP tool" idea OpenBB automates via OpenAPI introspection
([OpenBB MCP docs][openbb-mcp]); Vysted does it by hand, which is fine at this
tool count and gives per-tool description control.

---

## 4. The dual role — one catalog, two consumers

This is the core of the redesign and the most important section.

**The reality today is two parallel tool surfaces that overlap but aren't
unified:**

1. **Built-in agent surface** — `sidecar/services/agent_tools/` with
   `schemas.py::TOOL_SCHEMAS` (provider-neutral JSON Schema) + per-provider
   serialisers (`anthropic_tools` / `openai_tools` / `gemini_tools`). The
   `agent_runtime.invoke_agent` loop threads `tool_ids=list(spec.tools)` into
   the LLM call; each agent JSON (e.g. `agents/copilot.json`) carries a `tools`
   allow-list. Tools: `price_data`, `fundamentals`, `screener_run`,
   `macro_series`, `earnings_history`, `analyst_history`, `sec_filings_list`,
   plus per-invocation (`get_terminal_state`, `get_portfolio`,
   `broker_portfolio`) and host-action tools (`open_panel`, `set_chart_symbol`,
   `add_to_watchlist`, `propose_order`).
2. **External MCP surface** — `sidecar/services/mcp_server.py` FastMCP tools:
   `get_quote`, `get_history`, `get_fundamentals`, `get_news`,
   `get_macro_series`, `list_agents`, `invoke_agent`, `list_workspaces`,
   `get_workspace`, `run_workflow`, `list_workflows`.

These were built in different phases and **do not share a catalog.** Note the
asymmetry: the internal Copilot can drive the chart and propose orders; the
external MCP surface can read quotes and *invoke a whole agent* but can't, say,
run the screener or read fundamentals through the same names. That divergence is
the thing to fix.

**Target architecture: a single capability catalog, two adapters.**

```
                ┌───────────────────────────────────────────┐
                │   Capability layer (one source of truth)   │
                │   sidecar/services/agent_tools/*           │
                │   handler fn + JSON-Schema + annotations   │
                │   (read-only flag, mutation gate, domain)  │
                └───────────────┬───────────────────────────┘
                                │  catalog: {id -> {handler, schema, annotations}}
          ┌─────────────────────┴─────────────────────┐
          ▼                                             ▼
 ┌──────────────────────┐                  ┌──────────────────────────┐
 │ Internal adapter      │                  │ External adapter (FastMCP) │
 │ agent_runtime         │                  │ mcp_server.FastMCP         │
 │ → anthropic/openai/   │                  │ → @mcp.tool per catalog id │
 │   gemini tool shapes  │                  │   over stdio + HTTP        │
 │ Consumer: Copilot +   │                  │ Consumer: Claude Code,     │
 │ 11 persona agents     │                  │ Desktop, Cursor, any MCP   │
 └──────────────────────┘                  └──────────────────────────┘
```

The catalog already half-exists: `TOOL_SCHEMAS` is provider-neutral and keyed by
the *same id* used in the registry and in `AgentSpec.tools` — exactly the right
seam. The redesign generates the FastMCP tool set **from that same catalog**
instead of hand-writing a second list. Then:

- Adding `price_data` once makes it visible to Copilot *and* to Claude Code.
- The `read-only` flag drives **both** the internal mutation gate **and** the
  MCP `readOnlyHint` annotation from one declaration.
- Domain tags (`market-data`, `fundamentals`, `quant`, `broker`) let you do
  OpenBB-style category scoping (§6) for both consumers.

**Precedent in OpenBB:** the OpenBB MCP server and OpenBB Workspace's built-in
agents both consume the *same* Platform REST endpoints surfaced as tools — the
MCP layer is "the interface that makes MCP work for financial workflows" rather
than a separate integration ([OpenBB blog][openbb-iface]). Same idea: the app's
own AI and external AIs eat from one bowl.

**One wrinkle to design around — host-action tools.** `open_panel`,
`set_chart_symbol`, `propose_order` are resolved *inside* `invoke_agent` because
they need request scope / must drive the frontend (`schemas.py` header comment;
`agent_runtime._build_local_tools`). For an external MCP client there is **no
frontend to drive** (it may be running headless). Two options:

1. **Expose them anyway, with a "queued directive" semantics** — the MCP tool
   returns a directive the *attached live app* picks up over a websocket/event
   bus (only meaningful when the GUI is attached; returns "no host attached"
   otherwise). This is the honest dual-mode behaviour.
2. **Tag them `host-only` and exclude from the external surface by default** —
   the external catalog is data + analysis + `propose_order`; UI-driving stays
   internal. Simpler, and arguably correct for v1 of the framework story.

Recommend **option 2 for v1** (clean read/analysis framework), with option 1 as
the documented path when a live GUI session is attached.

---

## 5. Safe / read-only by default, gate the mutations

This is the highest-risk surface and Vysted already has strong precedent
(§6.5 safety architecture). Layer the defenses — annotations are *advisory*,
real enforcement is structural.

**Layer 1 — read-only by default, declared in the catalog.** Every tool carries
a `read_only: bool` (or a `mutates` flag). Default `read_only=True`. The FastMCP
adapter sets `ToolAnnotations(readOnlyHint=True)` from it. Clients *may* skip
the confirmation prompt for read-only tools, so getting this right matters for
UX, not just safety ([FastMCP tools][fastmcp-tools], [WorkOS][workos]).

**Layer 2 — no mutating tools on the external surface, structurally.** Vysted's
existing trading-wrapper pattern is the template (CLAUDE.md "three
defense-in-depth read-only enforcement layers"): the provider class exposes no
`insert_/update_/delete_/place_/submit_/execute_/create_` methods; the router
has no non-GET routes; `capabilities.supportsControlPlane = false`. **Carry the
same audit-test discipline to the MCP surface:** a `test_mcp_server.py` that
walks the registered tool set and asserts no tool's id matches the
mutation-verb deny-list, and that no exposed tool is annotated as
non-`readOnlyHint` unless it is on an explicit allowlist.

**Layer 3 — the one sanctioned write path is propose-not-place.** Vysted's
§6.5 invariant: the AI tool is `propose_order`, never `place_order` /
`submit_order` / `execute_order` (the names `test_safety_end_to_end.py` greps
the registry for). `propose_order` only *returns a directive that opens a
confirmation dialog* the user must approve; the AI has no path to
`confirm_and_place`. **For the MCP framework story, this is the model for ALL
mutations:** an external agent can *propose*, a human *confirms*. The append-only
audit log (SQLite triggers, `RAISE(ABORT)` on UPDATE/DELETE) records every
proposal/placement regardless of which consumer originated it.

**Layer 4 — credential isolation.** Never put secrets in MCP tool args. Vysted's
established pattern: the sidecar cannot read the OS keychain (only Tauri Rust
can); secrets ride in **request headers**, never tool/body params, never logged
or echoed (`X-Tradesa-*` precedent; `test_response_never_echoes_credentials`).
OpenBB independently arrived at the same rule: "API keys and credentials are
managed centrally. An agent can use a data connection without the key ever being
exposed" ([OpenBB Workspace MCP][openbb-workspace]). For BYOK LLM keys on the
external surface, the key rides the request, not the tool schema.

**Layer 5 — auth on the HTTP transport when it leaves loopback.** Today the
sidecar binds `127.0.0.1` only, so the MCP HTTP endpoint is unauthenticated by
the same logic as the rest of the API (`routers/mcp.py` comment). That is
**correct for loopback**. The moment the redesign exposes MCP off-box (team
server, remote agent), add FastMCP auth: `JWTVerifier` (JWKS/issuer/audience),
`OAuthProxy` for GitHub/Google, or a static-token bearer provider ([FastMCP
auth][fastmcp-auth]). stdio transport inherits security from the spawning
process — no token layer needed there. **Rule: loopback HTTP = no auth; any
non-loopback bind = auth required, block-and-ask (Tier-4) before shipping it.**

**Layer 6 — permission parity (forward-looking).** OpenBB's governance model:
"entitlements apply to the agent exactly as they apply to the user behind it,"
and agent-created artifacts inherit the user's access controls with full data
lineage ([OpenBB Workspace MCP][openbb-workspace]). Vysted is single-user
local-first today so this is latent, but the principle to bake in now: an
external agent operates with *the user's* entitlements, never a superset — the
broker connection it can read is the one the user connected, gated by the same
§6.5 safety layer.

---

## 6. Tool scoping & discovery at scale (the OpenBB lesson)

A finance terminal has *dozens* of endpoints across eight domains. Dumping 60+
tools into one client's context is a token + accuracy problem. OpenBB's answer is
**dynamic tool discovery** — worth adopting as Vysted's coverage grows
([OpenBB MCP docs][openbb-mcp]):

- Root "admin" tools the agent calls first: `available_categories`,
  `available_tools` (by category), `activate_tools` / `deactivate_tools`. The
  agent explores categories and *activates only the toolset it needs this
  session*, instead of the host paying for all schemas every turn.
- Disable via `--no-tool-discovery` for fixed/multi-client deployments.
- Category scoping flags: `--allowed-categories` (what exists server-wide),
  `--default-categories` (what's on at startup, default `all`). Categories derive
  from router paths (`equity`, `crypto`, `economy`, `news`, with subcategories
  like `equity_price`, `equity_fundamental`).

**For Vysted:** at the current ~12 tools, ship the **flat catalog** (no
discovery overhead). **Design the catalog with domain tags from day one**
(`market-data`, `fundamentals`, `screener`, `quant`, `portfolio`, `news`,
`macro`, `broker`) so that *when* coverage crosses ~25–30 tools you can add the
OpenBB-style `available_tools`/`activate_tools` discovery layer over the same
tags with no catalog rewrite. This is a Tier-2/3 decision (spec-derivable) — the
tags are cheap insurance.

---

## 7. Concrete recommended architecture for Vysted

**The eight-domain tool catalog** (map each to its existing router; reuse the
in-process ASGI shim pattern):

| Domain | MCP tools (read-only unless noted) | Router source |
|---|---|---|
| **Quotes** | `get_quote`, `get_history` (`price_data`) | `routers/quotes.py` |
| **Charts** | `set_chart_symbol`*, `add_indicator`* (host-only, §4) | frontend drive |
| **Screener** | `run_screener` (`screener_run`) | `routers/screener.py` |
| **Fundamentals** | `get_fundamentals`, `earnings_history`, `analyst_history`, `sec_filings_list` | `routers/*` |
| **Portfolio** | `get_portfolio`, `broker_portfolio` (read-only) | `routers/portfolio.py`, `routers/brokers.py` |
| **News** | `get_news` (with sentiment) | `routers/news.py` |
| **Quant** | `quant_stats`, `run_backtest` (read-only compute) | `routers/quant.py` |
| **Brokers** | `broker_portfolio` (read); `propose_order` (**only** gated mutation) | `routers/brokers.py` |

\* host-only tools: excluded from external surface by default (§4 option 2);
returned as queued directives only when a live GUI session is attached.

**Server shape:**

1. **Single FastMCP instance** generated from the unified catalog
   (`agent_tools` registry + `TOOL_SCHEMAS`), not a hand-written second list.
   Each catalog entry → `@mcp.tool` with `ToolAnnotations(readOnlyHint=...)`
   derived from the entry's `read_only` flag and a domain tag.
2. **Streamable-HTTP at `/mcp`, stateless** — the in-app path (already built).
3. **New stdio entrypoint** — headless spawnable binary for Claude Code /
   Desktop, serving the *same* FastMCP instance.
4. **Port discovery file** — Vysted writes `<appdata>/vysted/mcp.json`
   (`{url, port, protocolVersion}`) on launch; document it so a project
   `.mcp.json` can point Claude Code at the live terminal.
5. **A small resource set:** `resource://system_prompt` (onboarding for external
   agents — what Vysted is, the propose-not-place rule, available domains),
   `resource://workspace/current`, `resource://watchlist`.
6. **A small prompt set:** `equity_workup`, `macro_regime`, `portfolio_review`
   — canned analyst playbooks the user picks (OpenBB "server prompts" pattern).
7. **Built-in Copilot + external agents both consume the same catalog** — the
   internal adapter (`agent_runtime`) and the external adapter (FastMCP) are two
   renderers of one source of truth.

**Safety posture (non-negotiable, §5):** read-only by default; no
mutation-verb tools on the external surface (audit-tested); `propose_order` the
sole write path, propose-not-place into the append-only audit log; credentials
in headers never args; loopback = no auth, non-loopback = auth + Tier-4 review;
external agents inherit the user's entitlements, never a superset.

**What changes vs. today (the redesign delta):**

- Unify the two divergent tool lists into one catalog (the big one).
- Broaden external coverage from 5 data tools to all eight domains.
- Drive `readOnlyHint` + domain tags from the catalog declaration.
- Add the stdio entrypoint + port-discovery file (the "framework" enabler).
- Add the safety audit test to the MCP surface (mirror the §6.5 grep-check).
- Add a thin resource + prompt layer (progressive enhancement).

**Blast-radius note:** none of this touches `types/plugin.ts` (Tier-1) — the MCP
surface is a *consumer* of capabilities, orthogonal to the plugin contract.
Tool-catalog unification and stdio entrypoint are Tier-2 (spec-derivable);
domain-tagging and the discovery-layer-when-it-grows decision are Tier-3
(DNA-derived: max extensibility / "app as framework" positioning). **Any
non-loopback bind or any new mutating MCP tool is Tier-4 — block and ask.**

---

## Sources

- [Prompts — Model Context Protocol spec (2025-06-18)][spec-prompts]
- [Understanding MCP features: Tools, Resources, Prompts… — WorkOS][workos]
- [Introduction to Model Context Protocol — Anthropic course][anthropic-course]
- [FastMCP — The Pythonic Way to Build MCP Servers (KDnuggets)][kdnuggets]
- [FastMCP / jlowin — DeepWiki][deepwiki]
- [FastMCP Tools docs (gofastmcp.com)][fastmcp-tools]
- [FastMCP Authentication docs (gofastmcp.com)][fastmcp-auth]
- [openbb-mcp — OpenBB Docs][openbb-mcp]
- [Introducing Workspace MCP: agentic financial workflows, governed by design — OpenBB][openbb-workspace]
- [OpenBB: the interface that makes MCP work for financial workflows — OpenBB][openbb-iface]
- In-repo: `sidecar/services/mcp_server.py`, `sidecar/services/mcp_client.py`,
  `sidecar/services/agent_tools/{schemas.py,__init__.py}`,
  `sidecar/services/agent_runtime.py`, `sidecar/routers/mcp.py`,
  `sidecar/agents/copilot.json`, `sidecar/app.py`, project `CLAUDE.md`
  (§6.5 safety + MCP/agent-loop gotchas), `docs/SAFETY_ARCHITECTURE.md`.

[spec-prompts]: https://modelcontextprotocol.io/specification/2025-06-18/server/prompts
[workos]: https://workos.com/blog/mcp-features-guide
[anthropic-course]: https://anthropic.skilljar.com/introduction-to-model-context-protocol
[kdnuggets]: https://www.kdnuggets.com/fastmcp-the-pythonic-way-to-build-mcp-servers-and-clients
[deepwiki]: https://deepwiki.com/jlowin/fastmcp
[fastmcp-tools]: https://gofastmcp.com/servers/tools
[fastmcp-auth]: https://gofastmcp.com/servers/auth/authentication
[openbb-mcp]: https://docs.openbb.co/odp/python/extensions/interface/openbb-mcp
[openbb-workspace]: https://openbb.co/blog/introducing-workspace-mcp/
[openbb-iface]: https://openbb.co/blog/openbb-the-interface-that-makes-mcp-work-for-financial-workflows/
