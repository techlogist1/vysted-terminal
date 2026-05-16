# Phase 4 Handoff (v0.5.0 → Phase 5)

**Read this first** if you are looking at Phase 4's work. Phase 4 (Node
Editor + Workflow Engine + Backtest Engine + Strategy Critic e2e) shipped
together with Phase 5 under one v0.5.0 tag — the mega-sprint compression
explained in `CHANGELOG.md` v0.5.0. This handoff covers Phase 4's slice
specifically; Phase 5's is in `docs/PHASE_5_HANDOFF.md`.

The handoff follows the `PHASE_2_HANDOFF.md` / `PHASE_3_HANDOFF.md` shape
that has been the standing convention since v0.4.0.

---

## What Phase 4 shipped (inside v0.5.0)

### Foundation (lead, pre-teammate dispatch)

- **`@xyflow/react@12.10.2`** pinned in `package.json` — Phase 0 stack
  documentation referred to `reactflow`; v0.5.0 captures the npm rebrand
  in the Tier-3 decisions log.
- **`types/workflow.ts`** — `WorkflowSpec` (DAG of `WorkflowNode` +
  `WorkflowEdge`), `WorkflowRunRequest`, discriminated-union
  `WorkflowRunEvent` (run-start / node-start / node-output / node-error /
  run-complete / run-error), `NodeRunResult`, `WorkflowRunResult`.
- **`types/backtest.ts`** — `BacktestStrategySpec` (paramsSchema-driven
  picker form), `BacktestRequest`, full `BacktestResult` with metrics
  (totalReturn / annualizedReturn / Sharpe / Sortino / Calmar /
  maxDrawdownPct / winRate / tradeCount / bestTradePnl / worstTradePnl),
  trade log, equity curve, walk-forward slices. Plus the compact
  `BacktestSummary` digest the Strategy Critic agent's `backtest_summary`
  tool returns.
- **`sidecar/models/{workflow,backtest}.py`** — Pydantic mirrors of the
  TS contracts; CLAUDE.md "types/data.ts mirrors sidecar/models/ by hand"
  convention applied.
- **`sidecar/services/workflow_engine.py`** — custom asyncio engine with
  registry, Kahn's-algorithm cycle detection, parallel-wave execution
  via `asyncio.gather`, per-node observability via `on_event` callback,
  error propagation (one node failing marks its downstream as
  "upstream node failed" without cancelling siblings).
- **`sidecar/services/backtest_engine.py`** — custom event-driven engine
  (`BacktestStrategy` ABC with single `on_bar(bar, portfolio)` hook;
  walk-forward; fee/slippage BPS; Sharpe/Sortino/Calmar/win-rate metrics).
- **`sidecar/services/backtest_store.py`** — bounded LRU cache (capacity 32) for `BacktestResult` lookups by run_id, used by the Strategy Critic
  `backtest_summary` tool.
- **`sidecar/services/agent_tools.py`** — `register_tool(tool_id, handler)`
  registry + `invoke_tool` dispatcher. Foundation registers
  `backtest_summary` at import time; Teammate K added `price_data` +
  `fundamentals` via `register_v0_5_0_tools()`.
- **`sidecar/routers/{workflow,backtest}.py`** — `/workflow/run` SSE +
  `/workflow/save` + `/workflow/saved` (+ id GET/DELETE);
  `/backtest/run` SSE + `/backtest/strategies` + `/backtest/runs` (+ id GET).

### Teammate W — Workflow engine concrete + 10 built-in nodes (5 commits)

Plug-in nodes register via `workflow_engine.register_node_type(type_id,
handler)`. Built-in types: `data.fetch_quote`, `data.fetch_history`,
`compute.indicator`, `ai.agent_invoke`, `logic.branch`, `logic.compare`,
`action.log`, `action.notify_desktop`, `transform.json_path`, `flow.sleep`.

- `sidecar/services/workflow_nodes/{__init__.py, builtin.py}` — handlers +
  `register_all()` (called from `main.py`).
- `sidecar/services/mcp_server.py` — `run_workflow` + `list_workflows`
  MCP tools registered with wrap-list-at-boundary per v0.4.0 Gotcha.
- `src/store/workflow.ts` — Zustand store with module-level frozen
  empty-ref selectors (defeats `useSyncExternalStore` infinite-loop
  precedent from Phase 2 chart-sync gotcha).

### Teammate K — Backtest strategies + Strategy Critic Use Case 2 e2e (8 commits)

3 strategy archetypes: `mean_reversion` (z-score), `trend_following`
(golden cross with 200-day MA filter), `regime_aware` (vol-conditioned
position sizing). Each is a `BacktestStrategy` subclass registered via
`register_strategy(id, cls)` in `register_all()`.

- `sidecar/services/backtest_strategies.py` — 3 strategies + registry.
- `sidecar/services/bar_loader.py` — production OHLCV via Phase 1's
  `provider_registry` (yfinance / ccxt / openbb-mcp).
- `sidecar/services/agent_tools.py` extension — `price_data` (most
  recent 90 bars + latest quote) and `fundamentals` (yfinance fundamentals
  proxy), called by Strategy Critic to corroborate strategy claims.
- `sidecar/services/agent_runtime.py` extension — multi-round `tool_use`
  dispatch loop (`_MAX_TOOL_ROUNDS=6`); when a provider emits a tool_use
  block, the runtime calls `agent_tools.invoke_tool` and feeds the result
  back, looping up to 6 rounds.
- `src/store/backtest.ts` — strategy catalogue + SSE-consuming run store.
- `src/modules/backtest/{BacktestPanel,BacktestResultView,strategy-picker}.tsx`
  — `lightweight-charts` equity + drawdown shaded area + sortable trade
  log + walk-forward strip.
- `sidecar/tests/test_strategy_critic_e2e.py` — Use Case 2 round-trip in
  3 cases: backtest run → `backtest_summary` tool → Strategy Critic
  invocation with critique text generated end-to-end.

### Teammate N — Node editor frontend (9 commits)

`src/modules/node-editor/` — react-flow canvas + drag-drop palette +
edge connect + properties panel + save/load + run overlay.

- `NodeEditorPanel.tsx` — main canvas + toolbar.
- `node-palette.tsx` — drag-source palette grouped by category.
- `node-registry.ts` — combines 10 built-in nodes (foundation) with
  plugin-contributed nodes from `usePluginsStore.nodes` (Phase 2 wiring).
- `graph-state.ts` — pure-state graph manipulation, separately testable.
- `VystedNode.tsx` — react-flow custom node renderer.
- `workflow-save-dialog.tsx` — POST /workflow/save.
- `workflow-run-overlay.tsx` — per-node observability overlay consuming
  WorkflowRunEvent SSE.
- 8 populated screenshots at 1920×1080 + 2560×1440 in
  `docs/screenshots/v0.5.0/teammate-n/`. Canvas drag-drop interaction
  shots deferred (chrome-devtools MCP `isTrusted` gap from v0.3.0); Load
  path mocked-fetch shots cover the equivalent visual surface.
- Tier-3 design call: `BUILT_IN_NODE_CONFIG_FIELDS` (host-side typed
  config schema) lives in `node-registry.ts` instead of growing
  `NodeSpec` in the locked plugin contract — preserves Tier-1 lock while
  delivering typed inputs for built-ins; plugin nodes fall back to JSON
  editor.

---

## Architectural decisions made autonomously (Tier-2/3)

1. **Custom asyncio workflow engine, NOT Prefect / Dagster** (Tier-3).
   Those are server orchestrators; the desktop sidecar needs zero-config
   local execution. `<300 LoC` keeps the bundle lean (v0.4.0 main was
   67 MB; v0.5.0 main is 67.4 MB — workflow engine added effectively zero).

2. **Custom event-driven backtest engine, NOT vectorbt / backtrader at
   runtime** (Tier-3). backtrader stopped active dev ~2018; vectorbt's
   numba dep risks the 120 MB main-sidecar threshold. BLUEPRINT §7
   "vectorbt+backtrader patterns" wording supports drawing on their
   design ideas without runtime dependency.

3. **`@xyflow/react@12.10.2` (rebrand)** (Tier-3). The library formerly
   known as `reactflow` republished under `@xyflow/react` with the 12.x
   release; pinning the rebrand at foundation time avoids future
   downstream confusion.

4. **`backtest_summary` tool digest** (Tier-3). The Strategy Critic
   agent does NOT receive the raw equity curve (thousands of points) —
   only metrics + 20 most-recent trades + best-3 + worst-3 + walk-forward
   slices. Compact enough that the agent prompt does not drift across
   model releases.

5. **`agent_runtime` multi-round tool_use loop** (Tier-3, Teammate K).
   Phase 3 streamed text only; v0.5.0 dispatches up to 6 rounds of tool
   calls + tool results before returning the final agent message.
   Strategy Critic typically needs 1–3 rounds (backtest_summary +
   optional price_data + optional fundamentals).

6. **Node-config-fields host-side, NOT in NodeSpec** (Tier-3, Teammate N).
   Forms for the 10 built-in nodes use `BUILT_IN_NODE_CONFIG_FIELDS` in
   `src/modules/node-editor/node-registry.ts`. Plugin-contributed nodes
   without a host-side spec fall back to a JSON editor. Preserves
   `types/plugin.ts` Tier-1 lock.

---

## Known issues carried forward to v0.5.1 (none blocks v0.5.0)

1. **Canvas drag-drop / edge-connect interaction screenshots require
   Playwright** (chrome-devtools MCP can't synthesize `isTrusted`
   events). Teammate N's mocked-fetch Load-path screenshots cover the
   equivalent visual surface; a Playwright real-event suite would close
   the regression-test gap.

2. **Walk-forward slice configuration is binary (slices > 1 enables)** —
   future iterations might expose per-slice train/test window controls
   in the BacktestPanel UI.

3. **Workflow `resume-from` mode in `WorkflowRunRequest`** — the schema
   field exists; the engine ships full-run only in v0.5.0. Partial replay
   from a failed-node id is a v0.5.1 enhancement; the run cache + node
   outputs are already captured per-bar, so adding the resume path is
   small.

---

## Plugin contract status

- **`types/plugin.ts` is unchanged in v0.5.0.** Verified
  `git diff v0.4.0..v0.5.0 -- types/plugin.ts` empty across every
  teammate branch and the release commit. Tier-1 lock held.
- **`capabilities.contributesNodes` + `getNodes()`** — used end-to-end by
  Teammate N's node-registry. Plugin-contributed nodes flow through this
  surface unchanged.
- **Node-editor canvas operates on host-side `BUILT_IN_NODE_CONFIG_FIELDS`
  rather than extending NodeSpec** — preserves Tier-1 lock.

---

## Phase 5 entry context — where Phase 5 plugs into Phase 4

Phase 5 (broker integration + §6.5 safety) shipped under the same v0.5.0
tag. The relevant Phase 4 surfaces Phase 5 consumes:

1. **`agent_tools` registry** — the v0.5.0 plan reserved space for
   `place_order`-style tools but explicitly forbade them (operator-brief
   tightening of BLUEPRINT §6.5 #6). Phase 5's order flow goes through
   the broker adapter directly, not through the agent_tools registry.

2. **Workflow `ai.agent_invoke` node** — workflows can invoke a Strategy
   Critic agent that calls `backtest_summary`. The critique output flows
   downstream as the node's `content` output. Future workflows can add
   broker proposal steps that route to the safety-gated propose →
   confirm flow.

3. **`backtest_summary` digest** — the Strategy Critic agent's compact
   view of a backtest result. Phase 5's broker plugins can be added to
   workflow chains where the Strategy Critic approves a strategy and the
   workflow proposes orders (still going through the human-confirm gate
   per §6.5 #6).

---

## File / commit pointers for deeper context

- `CHANGELOG.md` v0.5.0 entry — full ship log + decisions log
- `docs/PHASE_5_HANDOFF.md` — companion handoff (Phase 5 slice)
- `docs/SAFETY_ARCHITECTURE.md` — §6.5 enforcement reference (cross-
  cutting; relevant to Phase 4's `agent_tools` decisions)
- `docs/superpowers/plans/2026-05-16-phase-4-5-mega-sprint.md` — the
  v0.5.0 plan
- `BLOCKERS.md` — current open items (kept slim post-release)
- `CLAUDE.md` — Phase 4 gotchas appended (worktree contamination
  lesson; chrome-devtools MCP isTrusted gap; `@xyflow/react` rebrand)
- **Foundation commits** (lead): 444dd5e, 0c70167, 846885a, 5da3b72,
  b0dc93a, b0b50ac, d837975, 0ee1663
- **Teammate W merge**: `6157e47` (df9cfbc)
- **Teammate K merge**: `d2fc0b0`
- **Teammate N merge**: `6157e47`
- **Teammate I/G/X merges**: `197fc60` (I), `6dc286f` (G + accidental
  early-S stores), `109e160` (X)
- **Safety audit + SAFETY_ARCHITECTURE.md**: `e4de55c`

---

## Verification snapshot at handoff

- `pnpm typecheck` / `pnpm lint` / `pnpm format:check` clean.
- `pnpm test` — **406 tests pass** (+194 over v0.4.0's 212).
- `pytest sidecar` — **579 tests pass** (+306 over v0.4.0's 273),
  including the 9-test `test_safety_end_to_end.py` audit suite.
- `ruff check sidecar` + `ruff format --check sidecar` clean.
- `cargo fmt --check` + `cargo clippy -- -D warnings` + `cargo test` clean.
- `pnpm sidecar:build` — main sidecar `--onefile` **67.4 MB**
  (+0.4 MB over v0.4.0's 67 MB).
- `git diff v0.4.0..v0.5.0 -- types/plugin.ts` empty.
- CI green on Win / macOS / Linux (Windows verified locally; matrix on CI).

---

## Coordination lesson for Phase 5+ (Phase 4 slice)

The Agent-tool `isolation: "worktree"` parameter does NOT fully isolate
writes for every agent — some agents wrote tracked files in the lead's
main worktree during execution. The going-forward rule: **lead audits
via `origin/<branch>` only; main-worktree contamination is always
discarded (`git restore HEAD -- <file>`) and re-merged from origin.**

Concrete v0.5.0 incidents: K modified `routers/backtest.py` +
`services/agent_runtime.py` + `services/agent_tools.py` in the main
worktree before pushing its branch; S modified `src/modules/index.ts` +
`src/lib/module-registry.test.ts`. The contamination surfaced at first
merge attempt (test failures on imports for modules that hadn't merged
yet). Resolution: restore HEAD, proceed with proper fetch + merge from
origin/<branch>. This precedent is captured in CLAUDE.md for the next
mega-sprint.

The two file-conflict resolutions during Phase 5 broker merges
(`sidecar/services/brokers/__init__.py`, `docs/BROKER_INTEGRATIONS.md`)
are documented in PHASE_5_HANDOFF.md.
