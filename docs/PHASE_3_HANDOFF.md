# Phase 3 Handoff (v0.4.0 → Phase 4)

**Read this first** if you are the Phase 4 lead. Everything you need to
know about what Phase 3 shipped, decided, and left pending — captured
from warm context immediately after the v0.4.0 tag.

This document follows the shape of `PHASE_2_HANDOFF.md` so the Phase-N
handoff convention (one document per phase, named `PHASE_N_HANDOFF.md`,
present in `docs/`) stays predictable across the build.

---

## What v0.4.0 shipped

### Foundation (lead, pre-teammate dispatch)

- `ad1d576` — `feat(tauri): OS keychain commands via keyring crate`. The
  `keyring` 3.x crate with explicit cross-platform features
  (`apple-native`, `windows-native`, `sync-secret-service`, `crypto-rust`
  — v3 has no default features, so the explicit list is load-bearing).
  Three Tauri commands: `keychain_set` / `keychain_get` /
  `keychain_delete`. Round-trip test against the real OS store.
- `f2a88c5` — `feat(keychain): frontend wrapper + namespace conventions`.
  `src/lib/keychain.ts` exposes typed `invoke` bindings + the canonical
  `KEYCHAIN_NAMESPACES.{llmProvider,mcpServer,pluginSecret}` builders
  every teammate consumes.
- `2053150` — `feat(types): AI provider/agent, MCP, panel-context
contracts`. Three new type files (`types/ai.ts`, `types/mcp.ts`,
  `types/panel-context.ts`) — foundation contracts the three teammates
  consume.
- `06f6163` — `feat(store): panel-context bus mirroring chart-sync
pattern`. `usePanelContextBus` + `selectSnapshot` with the same
  frozen-empty-ref discipline the Phase-2 chart-sync gotcha required.
- `7a55ec9` — `feat(agents): JSON schema + discovery contract for
first-party agents`. `sidecar/agents/_schema.json` mirrors `AgentSpec`
  field-for-field; the runtime validates each `<id>.json` at startup.

### Teammate A — AI Core (`4bc9ea7` merge)

11 commits + the post-merge `chore: ruff format` consolidation.

- 5 native LLM provider adapters (`anthropic`, `openai`, `gemini`,
  `groq`, `ollama`) + 2 OpenAI-compatible dispatchers (DeepSeek, xAI
  via `base_url` override). Shared `LLMProvider` ABC in
  `sidecar/services/llm/base.py`.
- 12 first-party agent JSON configs in `sidecar/agents/` with
  substantive 200-500-word system prompts: `buffett`, `graham`,
  `lynch`, `munger`, `marks`, `klarman`, `dalio`, `druckenmiller`,
  `soros`, `researcher`, `portfolio_advisor`, `strategy_critic`.
  The 12th — AI Strategy Critic — is the §3.4-vs-§4 Tier-3 roster
  resolution (named in §4 module 38 + Use Cases 2/3; forward-compatible
  with the Phase-4 backtest engine).
- Agent runtime (`sidecar/services/agent_runtime.py`) discovers,
  JSON-Schema-validates, and streams via the resolved provider adapter.
- Sidecar routers: `POST /llm/chat` (SSE), `POST /llm/keys/validate`,
  `GET /llm/providers`, `GET /agents`, `POST /agents/{id}/invoke` (SSE).
  Agent `systemPrompt` is deliberately omitted from the `/agents` wire
  shape (configs live server-side, no need to ship 200-500 words per
  agent to the client on every render).
- Chat sidebar (`src/modules/chat/ChatSidebar.tsx` + supporting module
  files) with streaming text composer, agent picker dropdown,
  panel-context badge, BYOK key entry dialog (writes through
  `keychain_set`, never persists in JS).
- Slash commands: `/ask`, `/agent`, `/provider`, `/key set`, `/clear`,
  `/help` — registered through `src/lib/commands.ts`.
- Streaming client: custom SSE parser over `fetch` (native `EventSource`
  is GET-only; chat is POST because the body carries the BYOK key).
- 6 populated-state screenshots in `docs/screenshots/v0.4.0/teammate-a/`
  at both 1920×1080 and 2560×1440 (chat streaming, agent picker, context
  badge).

### Teammate B — MCP Layer (`9521db9` merge)

8 commits + the integration-time `list_agents` wrap fix + the orphaned
`.venv` cleanup.

- Vysted MCP server: FastMCP 3.2.4 mounted in-sidecar at `/mcp` over
  Streamable-HTTP transport. 9 tools — 5 data (`get_quote`,
  `get_history`, `get_fundamentals`, `get_news`, `get_macro_series`),
  2 agent (`list_agents`, `invoke_agent`), 2 workspace (`list_workspaces`,
  `get_workspace`). Each tool is a thin shim that calls the
  corresponding sidecar HTTP endpoint via an in-process
  `httpx.AsyncClient` bound through `httpx.ASGITransport` — no logic
  duplication, the MCP layer is purely a protocol adapter.
- MCP client wrapper (`sidecar/services/mcp_client.py`) — wraps the
  official `mcp` SDK; supports stdio + Streamable-HTTP transports;
  caches per server id; reconnects on transport error.
- openbb-mcp-server integration: `plugins/openbb-mcp/` replaces the
  Phase-2 `plugins/openbb/`. The PyPI package is built into a separate
  PyInstaller `--onefile` binary at `sidecar/openbb_mcp_subprocess/`
  (55 MB on Windows), spawned by Tauri Rust `Command::new` from
  `src-tauri/src/openbb_mcp.rs` — the architectural fix the v0.3.0
  handoff identified for the Phase-2 Windows deadlock.
- Phase-2 OpenBB Tier-2 plugin **retired** (delete, not deprecate):
  `plugins/openbb/`, `sidecar/openbb_subprocess/`,
  `scripts/ensure-openbb-sidecar.mjs`, `sidecar/services/openbb_provider.py`,
  `sidecar/routers/openbb.py`, and their tests are all gone. The data
  surface is preserved end-to-end through `openbb_mcp_provider` so
  existing data callers see no functional regression.
- `docs/MCP_INTEGRATION.md` documents Claude Desktop config (via
  `mcp-remote` bridge — Claude Desktop's `claude_desktop_config.json`
  doesn't accept HTTP servers directly) and Claude Code (native HTTP).
- End-to-end MCP wire verified in `docs/screenshots/v0.4.0/teammate-b/`
  session logs (Vysted's own `McpClient` over Streamable-HTTP using the
  same protocol Claude Code uses; `get_quote("AAPL")` and
  `invoke_agent("buffett", ...)` exercised end-to-end).

### Teammate C — Custom Agent Builder + per-panel context publishers (`7a98d58` merge)

10 commits.

- BLUEPRINT Module 36 (Custom Agent Builder): a form-based UI
  (`src/modules/agent-builder/`) for defining user-named agents.
  Custom-agent ids are `custom:`-prefixed at validation time so they
  cannot collide with first-party ids; the chat sidebar's picker groups
  them under a "Custom" section.
- Sidecar CRUD for custom agents: `agents_store.py` SQLite store
  mirroring `plugins_store.py`; `routers/custom_agents.py` exposes
  the full GET / GET-one / POST / PUT / DELETE surface with Pydantic
  validation.
- Per-panel context publishers wired into all five Phase-1 panels
  (chart, watchlist, news, equity, portfolio). Each panel publishes a
  payload via `usePanelContextBus.publish` on relevant state change;
  unmount cleanup calls `unregisterSource`. Render-loop discipline is
  asserted per panel (publish-spy call count bounded after mount +
  microtask flush).

### Lead release work (`a5ad96d` + this commit)

- Version bump 0.3.0 → 0.4.0 across `package.json`, `Cargo.toml`,
  `Cargo.lock`, `tauri.conf.json`, sidecar `FastAPI(version="0.4.0")`.
- `CHANGELOG.md` v0.4.0 entry — full per-teammate decomposition,
  decisions, failed approaches, known issues, verification matrix.
- `docs/BLUEPRINT.md` Phase 3 row marked shipped.
- `BLOCKERS.md` refreshed: Phase-2 OpenBB deadlock RESOLVED (retired);
  Phase-4 follow-ups documented (Claude Desktop screenshot polish,
  chart-tool `isTrusted` verification gap from v0.3.0).
- `docs/screenshots/v0.4.0/teammate-c/README.md` documents the
  Module 36 screenshot deferral (Agent Builder mid-edit shot is the
  only one not covered by A's existing shots; deferred to Phase-4
  polish, unit-integration coverage compensates).

---

## Architectural decisions made autonomously (Tier-2/3, no Tier-4)

1. **AI Strategy Critic as the 12th first-party agent** (Tier-3).
   BLUEPRINT §3.4's table has 12 rows but the 12th is the Custom Agent
   Builder UI; §4 module catalog separates them as module 35 (12
   pre-built agents) + module 36 (Custom Agent Builder UI). §4 is
   authoritative for module counting. AI Strategy Critic is the
   strongest spec-derivable 12th agent (named in §4 module 38, Use
   Cases 2/3, forward-compatible with Phase 4).
2. **OpenBB integration via MCP, not in-process** (Tier-2). The Phase-2
   `subprocess.Popen` deadlock fix the brief called for is the explicit
   trigger. Replacing `subprocess.Popen` with Tauri Rust `Command::new`
   AND retiring the bespoke REST subprocess in favour of the stock
   `openbb-mcp-server` PyPI package is the cleanest path.
3. **MCP server in-sidecar via Streamable-HTTP at `/mcp`** (Tier-3).
   Avoids a second binary, reuses the sidecar's port + lifecycle.
   Tools call the host FastAPI app in-process via
   `httpx.ASGITransport` — zero network hops for data tool calls.
4. **`list_agents` MCP tool wraps the bare-list response at the MCP-
   tool boundary** (Tier-3, integration-time). A's `GET /agents`
   returns a bare JSON list per REST convention; FastMCP rejects
   bare-list tool outputs. Wrap moved to the MCP tool, not A's REST
   contract.
5. **Unified `src/store/agents.ts` hand-merge at integration** (Tier-3,
   integration-time). Both A and C wrote a working store; the lead
   hand-merged into a single store exposing both API surfaces. See
   the v0.4.0 merge commit for the design.
6. **Custom-agent IDs `custom:`-prefixed** (Tier-3). Prevents collision
   with first-party ids and lets the chat sidebar picker group them
   without re-filtering.
7. **Streaming chat is POST + custom SSE parser, not `EventSource`**
   (Tier-3). Native `EventSource` is GET-only and the BYOK key must
   travel in the request body.
8. **Phase-2 OpenBB retired, not deprecated** (Tier-3). Same `DataSource`
   shape preserved through the new plugin so no functional regression;
   removing the bespoke subprocess + plugin pair saves ~43 MB on disk
   and removes the deadlock investigation surface from the codebase.

---

## Known issues carried forward (Phase-4 follow-ups, none blocks v0.4.0)

### 1. Claude Desktop live-screenshot for the MCP server

End-to-end MCP wire is verified via Vysted's own `McpClient` session
log (same Streamable-HTTP wire Claude Code uses). A polish-tier
deliverable: a real screenshot of Claude Desktop consuming Vysted's
MCP server through the `mcp-remote` bridge documented in
`docs/MCP_INTEGRATION.md`. Not load-bearing.

### 2. Custom Agent Builder populated-state screenshot

A's existing context-badge shots prove the per-panel publisher chain
end-to-end. The Agent Builder mid-edit screenshot pair (1920×1080 +
2560×1440) is deferred to a Phase-4 polish session running
`pnpm tauri dev` — A's shots cover the load-bearing chat sidebar +
context badge surfaces.

### 3. Drawing-tool on-canvas screenshots (carried from v0.3.0)

`lightweight-charts` `isTrusted` check — chrome-devtools MCP cannot
exercise click-to-create. Documented across CLAUDE.md + BLOCKERS.md.
A Playwright real-event suite would close the loop.

---

## Plugin contract status

- **`types/plugin.ts` is unchanged in v0.4.0.** Verified across every
  teammate branch and the release commit
  (`git diff v0.3.0..v0.4.0 -- types/plugin.ts` empty). Tier-1 lock
  held.
- **`AgentSpec` is the runtime contract for both first-party AND custom
  agents.** First-party agents come from `sidecar/agents/*.json`
  configs validated against `sidecar/agents/_schema.json`; custom
  agents come from the SQLite store. Both produce `AgentSpec`-shaped
  records the agent runtime consumes uniformly.
- **`capabilities.contributesAgents` + `getAgents()` is unused on
  first-party agents** — they are config-driven and not plugin-
  contributed. The capability stays available for third-party plugin
  authors who want to ship agents alongside their own data layer.

---

## Phase 4 entry context — where the node editor + backtest plug in

Per BLUEPRINT §7 Phase 4, the next phase adds: node editor (react-flow
based), workflow execution engine, backtest engine, AI Strategy Critic
agent integration. Mapping each to existing Phase-3 surfaces:

### Node editor

The locked plugin contract already supports node contributions via
`capabilities.contributesNodes` + `getNodes()` returning `NodeSpec[]`
(`types/plugin.ts`). `usePluginsStore.nodes` is wired from Phase 2
and populated whenever a plugin sets the capability flag. Phase 4
consumes that store; no runtime change required.

### Workflow execution engine

Will sit in the sidecar. A new router (`sidecar/routers/workflow.py`)

- service (`sidecar/services/workflow_engine.py`) following the
  established router-service-test convention. The agent runtime from
  Phase 3 (`sidecar/services/agent_runtime.py`) is the call surface
  for any agent invocation a workflow needs — workflow nodes that
  fire agents call `agent_runtime.invoke_agent(...)` directly.

### Backtest engine

Pydantic models for backtest spec + result land in `sidecar/models/`.
The AI Strategy Critic agent (already shipping in v0.4.0) has its
tool list `["backtest_summary", "price_data", "fundamentals"]`
deliberately shaped so it can consume a backtest summary from the
engine when Phase 4 wires it in.

### Per-panel context bus consumption

A backtest result panel or workflow runner panel would publish its
state through `usePanelContextBus` so the chat sidebar agents can
reason over backtest results the same way they reason over chart
state in v0.4.0.

### MCP tool surface extension

Adding workflow / backtest tools to the Vysted MCP server is a
register-an-`@mcp.tool` change in `sidecar/services/mcp_server.py`.
External MCP clients (Claude Desktop, Claude Code) pick up new
tools automatically through the standard MCP `list_tools` handshake.

---

## File / commit pointers for deeper context

- `CHANGELOG.md` v0.4.0 entry — full ship log
- `docs/BLUEPRINT.md` §7 Phase 4 row — scope you are about to execute
- `docs/MCP_INTEGRATION.md` — external MCP client config (added v0.4.0)
- `docs/PLUGIN_DEVELOPMENT.md` — plugin author guide; the MCP plugin
  pattern (Teammate B) is the latest reference plugin shape
- `BLOCKERS.md` — open Phase-4 follow-ups
- `CLAUDE.md` Gotchas — Phase-3 lessons (BYOK + keychain, MCP
  list-wrap-at-tool-boundary, ruff drift across worktrees)
- `a5ad96d` — v0.4.0 release commit precursor (version bump)
- Per-teammate merge commits: `4bc9ea7` (A), `9521db9` (B), `7a98d58` (C)
- Foundation commits: `ad1d576`, `f2a88c5`, `2053150`, `06f6163`,
  `7a55ec9`, `1dad808`

---

## Verification snapshot at handoff

Pulled from the v0.4.0 release commit on `origin/main`:

- `pnpm typecheck` / `lint` / `format:check` clean
- `pnpm test` — 24 files, **212 tests pass** (+55 over v0.3.0)
- `pytest sidecar` — **273 tests pass** (+83 over v0.3.0)
- `ruff check sidecar` / `ruff format --check sidecar` clean
- `cargo fmt --check` / `cargo clippy -- -D warnings` clean;
  `cargo test` — **2 pass** (+1 keychain round-trip over v0.3.0)
- `pnpm sidecar:build` — main sidecar `--onefile` **67 MB**
  (+10.1 MB over v0.3.0's 56.9 MB)
- `pnpm openbb-mcp-sidecar:build` — openbb-mcp subprocess `--onefile`
  **55 MB** (replaces v0.3.0's 43 MB)
- Total Phase-3 binary footprint **≈ 122 MB** on Windows
  (+22 MB over v0.3.0)
- `git diff v0.3.0..v0.4.0 -- types/plugin.ts` empty (Tier-1 lock held)
- CI green on Win / macOS / Linux (Windows verified locally; matrix on CI)

---

## Coordination lesson for Phase 4

The Phase-3 plan told both Teammate A and Teammate C to write
`src/store/agents.ts` from scratch. The plan called C's version
"authoritative"; A's brief said theirs was "bare initial". A's
ended up working (the chat sidebar needed a real store), C's ended
up working (the builder needed real CRUD). Both shipped; lead
hand-merged at integration into a unified store.

For Phase 4: if two teammates need to write the SAME file, the plan
should specify (a) which teammate owns it as primary and (b) what
API surface the secondary teammate adds without rewriting. A
forcing function: schedule the dependent teammate's worktree to
branch from the primary teammate's pushed branch, not from `main`.
Phase 3 didn't do this because A and C worked in parallel — a Phase-4
sequencing improvement.
