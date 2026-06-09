# R7 Track N — Hackability Brief (worktree: worktree-agent-r7-hack)

Build the hackability pillar (code escape hatches everywhere, agent-drivable), inside THIS
worktree only: `~/Documents/dev/vysted-terminal/.claude/worktrees/r7-hack`. Branch
`worktree-agent-r7-hack`. NEVER write to the main repo path.

## Ground rules
- You OWN: `src/modules/node-editor/**`, `src/modules/screener/**`, `src/modules/backtest/**`,
  `sidecar/services/backtest*` + `sidecar/services/screener*` (engine-side execution),
  `sidecar/routers/{backtest,screener}.py`, and their tests. NOTHING else. New agent tools
  need `sidecar/services/agent_tools/catalog.py` — you may NOT edit it (another track owns
  it); register handlers in `agent_tools/` and append the exact Capability entries to
  `docs/redesign/INTEGRATION_NOTES_R7_HACK.md` for the lead, and write your tests so they
  pass once wired (mark those `@pytest.mark.skip(reason="lead wires catalog entry")` — the
  ONE permitted skip class).
- Frontend gates: `pnpm typecheck && pnpm lint && pnpm vitest run <your suites>` per commit.
  Python gates: main venv binaries `~/Documents/dev/vysted-terminal/sidecar/.venv/bin/{python,ruff,pytest}`
  with cwd in THIS worktree; ruff format/check + targeted pytest per commit.
- Conventional commits per deliverable; push to `origin worktree-agent-r7-hack`.
- Design law: docs/redesign/VYSTED_DESIGN.md. §6.5 safety untouched (backtests/screeners
  never touch order paths).
- No stubs/TODOs. Everything you ship EXECUTES.

## Pillar 1 — Custom code nodes in the node editor
A first-class `code` node: user/agent-authored expression/script that transforms inputs to
outputs inside a workflow run. Study how the node editor executes workflows today
(workflow-run-overlay, the sidecar workflow execution if any — find the real execution
path first and document it in your report). Implement the safest expressive option that
ships TONIGHT: a sandboxed expression evaluator on data inputs — the repo already ships
`mathjs` (frontend) — a mathjs-evaluated node with multi-input bindings, error surface,
and a monospaced editor textarea in the node inspector. The agent must be able to author
one (the node spec is serializable; note the agent-tool entry for creating/updating
workflow nodes in INTEGRATION_NOTES if one doesn't exist).
The palette: study `node-palette` — open it up so ALL registered node kinds incl. the new
code node are composable, with grouped sections and search if >12 kinds.

## Pillar 2 — Agent-written backtest strategies that EXECUTE
Find the backtest engine's strategy contract (strategy-picker + sidecar backtest service).
Today it runs built-in strategies. Add a `custom` strategy lane: a user/agent-supplied
strategy definition that the SIDECAR executes safely — implement a declarative signal DSL
(JSON: entry/exit rules over indicator comparisons, e.g. {entry: "sma(20) > sma(50)",
exit: "rsi(14) > 70"}, parsed and evaluated server-side over the price series with a
restricted expression grammar — NO eval/exec of arbitrary Python). Wire it through the
backtest router + frontend strategy picker ("Custom strategy" with a definition editor +
validation errors inline). Register an agent_tools handler `run_custom_backtest` (catalog
entry via INTEGRATION_NOTES) so the agent can author + run one and the results render in
the existing BacktestResultView.
Also fix (it's your file): the trade table's mid-number truncation (`max-w-0
overflow-hidden` on numeric cells → real column widths, right-aligned tabular)
and the bare empty state (composed EmptyState).

## Pillar 3 — Screener formulas as a real expression layer
The screener has a custom-formula leaf (`ScreenerFormulaLeaf`, `CUSTOM FORMULA` chip seen
live). Grow it into a documented expression layer: field references (pe, market_cap, roe,
…the existing screener fields), arithmetic, comparisons, boolean ops, and a few functions
(abs/min/max/pct_change if the data supports it) — one grammar shared by the screener
service evaluation; clear inline validation (error with caret position), autocompletion of
field names in the editor (simple prefix dropdown), and 3 example formulas as one-click
chips. Server-side evaluation must be safe (no eval; use/extend the existing parser or
write a small recursive-descent one) and tested against edge cases (div-by-zero, missing
fields → row skipped with skip-count surfaced honestly — the "X eval, Z skip" summary
exists; keep it).
Presentation: bring the screener panel to the design law while you're in there (criteria
rows, preset chips, results table on DataTable rhythm, composed empty state).

## Done =
Everything executes end-to-end in tests (frontend + sidecar). Gates green. Committed +
pushed. Final report `docs/redesign/R7_TRACK_HACK_REPORT.md`: shipped file:line, the real
execution paths you found, grammar docs (brief), INTEGRATION_NOTES entries, what the lead
should eyeball live, NEEDS-MANUAL-CHECK list.
