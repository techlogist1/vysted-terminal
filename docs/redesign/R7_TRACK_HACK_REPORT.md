# R7 Track N — Hackability Report (worktree `r7-hack`, branch `worktree-agent-r7-hack`)

All three pillars shipped and EXECUTE end-to-end in tests. Gates green from this
worktree: `pnpm typecheck` / `pnpm lint` / `pnpm test` (133 files, 1204 tests, 0 fail)
and `ruff format --check sidecar` / `ruff check sidecar` / `pytest` (1557 passed,
2 skipped — both accounted for below). Branch head `4beed66`, pushed.

---

## Real execution paths found (study notes)

- **Node editor run path:** `NodeEditorPanel.tsx:346 handleRun` builds the serializable
  `WorkflowSpec` from graph state, opens a `fetch` stream against `POST /workflow/run`
  (`NodeEditorPanel.tsx:386`) and consumes SSE `node-output` / terminal frames from
  `sidecar/services/workflow_engine.py`. There is NO frontend evaluator for unregistered
  node types — `_validate_spec` server-side rejects unknown types, which is why the code
  node ships with a client-side execution seam (below) plus a paste-ready Python parity
  handler in INTEGRATION_NOTES.
- **Backtest strategy contract:** `GET /backtest/strategies` (`routers/backtest.py:104`)
  lists the registry built by `backtest_strategies.register_all()`
  (`backtest_strategies.py:443`); a run is `POST /backtest/run` SSE
  (`routers/backtest.py:42`) → `backtest_engine` → `strategy.evaluate(bar_window)` per
  bar. Strategy params ride `BacktestRequest.params` untyped — the custom lane needed
  ZERO model changes.
- **Screener run path:** `POST /screener/run` (`routers/screener.py:47`) →
  `services/screener.py` batch evaluation with the honest skip ledger
  (`skipped_count == len(skip_details)`, screener.py:33–35). The formula AND-combines
  with criteria inside the same evaluation pass.

## Pillar 1 — code node (`transform.code`)

| What                                                                                                                                   | Where                                                                                                                                            |
| -------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Node spec, sandboxed mathjs compile/eval                                                                                               | `src/modules/node-editor/code-node.ts` (id :28, `compileCodeExpression` :145, `evaluateCodeExpression` :166)                                     |
| Hybrid run seam: partition + topological client eval                                                                                   | `src/modules/node-editor/code-node-run.ts` (`partitionWorkflow` :60, `evaluateCodeNodes` :157)                                                   |
| Inspector: monospaced editor, binding management, live error surface                                                                   | `src/modules/node-editor/code-node-inspector.tsx`                                                                                                |
| Run wiring (partition at :365, engine-parity `upstream node failed` propagation, no false run-complete on terminal-frame-less streams) | `src/modules/node-editor/NodeEditorPanel.tsx:342–420`                                                                                            |
| Palette opened up: ALL 23 first-party kinds, grouped by the five `NodeSpec.category` sections, search at >12 kinds                     | `src/modules/node-editor/node-palette.tsx` (search :86, sections :112), `node-registry.ts` (`FIRST_PARTY_NODE_SPECS` :404, `buildRegistry` :563) |

Sandbox: an isolated mathjs instance with `import`/`createUnit`/`evaluate`/`parse`
removed and a scope whitelist — expressions only, no JS execution. Spec is fully
serializable: `config = {"expression": str, "inputs": [str, ...]}`; each `inputs[i]`
is both an input port id and an expression variable; one output port `value`.
Code→server edges are rejected pre-run with an honest message (server engine cannot
see client-computed values tonight; parity handler retires the seam in one place —
see INTEGRATION_NOTES).

## Pillar 2 — custom backtest strategies that EXECUTE

| What                                                                                                                      | Where                                                                                                                         |
| ------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Restricted recursive-descent DSL (NO eval/exec)                                                                           | `sidecar/services/backtest_dsl.py` (`DslError` :81 with caret position, `validate_definition` :625, `CustomDslStrategy` :673) |
| Registered as strategy id `custom`                                                                                        | `sidecar/services/backtest_strategies.py:452` (listed :167)                                                                   |
| Validate route                                                                                                            | `POST /backtest/strategies/custom/validate` (`routers/backtest.py:159`)                                                       |
| Frontend lane: picker is server-driven; `custom` swaps in the definition editor with inline validation + run gating       | `src/modules/backtest/BacktestPanel.tsx:105,115,176`, `custom-strategy-editor.tsx`                                            |
| Agent tool handler (catalog-gated, see wiring)                                                                            | `sidecar/services/agent_tools/run_custom_backtest.py` (handler :60, `register()` :125)                                        |
| Trade-table fix: real column widths, right-aligned `tabular-nums`, no `max-w-0 overflow-hidden`; composed `EmptyState` ×2 | `src/modules/backtest/BacktestResultView.tsx:225,279–335,439`                                                                 |

**Grammar (brief):** fields `open high low close volume`; functions
`sma(n) ema(n) rsi(n) highest(n) lowest(n) stdev(n) change(n)` with integer periods
1..500; `+ - * /`, comparisons, `and/or/not`, parens, unary minus. Definition =
`{"entry": str, "exit": str, "position_size": number}` riding `BacktestRequest.params`.
Hostile-input caps: MAX_TOKENS 256, MAX_NESTING_DEPTH 32, period length-guard (digit
floods and recursion bombs are clean `DslError`s, commits `46136c4` + `4492866`).
Warm-up and div-by-zero yield no-signal, never a crash. §6.5: simulation only — no
order path is reachable from this lane.

## Pillar 3 — screener formula expression layer

| What                                                                                                                                 | Where                                                                                                                                            |
| ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Authoritative server grammar                                                                                                         | `sidecar/services/screener_formula.py` (`FormulaError` :78 positioned, `compile_formula` :441, `validate_formula` :462, `evaluate_formula` :563) |
| Hand-mirrored TS twin (editor caret validation + autocomplete; parity vectors in both suites)                                        | `src/lib/screener-expr.ts`                                                                                                                       |
| Service integration: formula fields join enrichment; missing field → row skipped, itemized `missing_field:<f>` (SC-034 ledger holds) | `sidecar/services/screener.py:477,625–655`                                                                                                       |
| Validate route → `{ok, error, position, fields}`                                                                                     | `POST /screener/formula/validate` (`routers/screener.py:74`)                                                                                     |
| Editor: caret-position error row, prefix autocomplete dropdown, 3 one-click example chips                                            | `src/modules/screener/ScreenerFormulaLeaf.tsx` (EXAMPLES :34, chips :219)                                                                        |
| Panel to design law: criteria rows, raised segmented toggles, preset chips, DataTable rhythm, composed empty state                   | `ScreenerPanel.tsx`, `ScreenerCriteriaBuilder.tsx`, `ScreenerResultsTable.tsx`, `CriterionGroupEditor.tsx` (commits `7a3a363`, `4beed66`)        |

**Grammar (brief):** field refs = any numeric screener field incl. aliases
(`pe`→`pe_ratio`, `marketCap`, `pb`, …); `+ - * /`, comparisons, `and/or/not`;
functions `abs(x)`, `min(2..8 args)`, `max(2..8 args)` (`pct_change` deliberately
omitted — the screener rows are point-in-time snapshots, no history to diff
honestly). Same caps as the DSL (256 tokens / depth 32); zero eval anywhere;
div-by-zero is a no-match, never a crash. `ScreenerRequest.formula` AND-combines
with criteria; the "X eval, Z skip" summary is preserved and now itemizes
`missing_field:<f>`.

The `screener_run` agent tool already accepts `formula` today (handler revalidates
through `ScreenerRequest`) — only the catalog schema advertisement is pending (below).

---

## INTEGRATION_NOTES entries (lead actions — all paste-ready in `docs/redesign/INTEGRATION_NOTES_R7_HACK.md`)

1. **Server-side `transform.code` parity handler** — stdlib-`ast` whitelist evaluator
   module + one `register_node_type` line (workflow-nodes track owns the target file).
   Unblocks agent/MCP `run_workflow` specs containing code nodes; retiring the
   client seam afterwards is a one-function change in `code-node-run.ts`.
2. **`save_workflow` MCP tool** — hand-written MCP-only entry for `services/mcp_server.py`
   (workflow tools are NOT catalog read_handlers per CLAUDE.md) so the agent can
   author/update workflows, not just run them.
3. **`run_custom_backtest` catalog Capability + `register()` call** — both must land
   together (SC-006 parity gate). Then un-skip
   `test_backtest_custom.py:546 test_catalog_capability_exists` and add the tool id
   to an agent allow-list (Strategy Critic is the natural fit).
4. **`formula` property on the `screener_run` catalog schema** (~catalog.py L370) —
   the handler already works; the models just can't SEE the parameter until the
   schema advertises it.

## Verification snapshot

- Frontend (this worktree): `pnpm typecheck` ✓, `pnpm lint` ✓, `pnpm test` ✓
  (133 files / 1204 tests).
- Sidecar (main venv, cwd this worktree): `ruff format --check sidecar` ✓,
  `ruff check sidecar` ✓, `pytest` ✓ 1557 passed, 2 skipped:
  - `test_backtest_custom.py:546` — "lead wires catalog entry", the ONE permitted
    skip class (asserts the exact Capability in INTEGRATION_NOTES once wired).
  - `test_native_search_live.py:41` — pre-existing live-key gate
    (`OPENROUTER_LIVE_KEY`), R4 search track, unrelated to this track.
- No unrelated failures observed; nothing this track introduced is red.
- Test-run side effect: pytest regenerates
  `docs/screenshots/v0.5.0/safety-audit/kill-switch-benchmark.json` timings —
  reverted, not committed.

## What the lead should eyeball live

1. Node editor: drag a `Code` node from the grouped/searchable palette, bind two
   upstream nodes, type `quote.price * qty`, run — watch the overlay show the
   client-evaluated value and the honest rejection when a code node feeds a
   server node.
2. Backtest: pick "Custom Strategy (DSL)", enter `entry: sma(20) > sma(50)`,
   `exit: rsi(14) > 70`, watch inline caret-positioned validation, run, and check
   the trade table columns no longer truncate mid-number at narrow widths.
3. Screener: click an example chip, break the formula (e.g. `pe <`), confirm the
   caret error row; run a formula over a sparse field and confirm the skip summary
   counts `missing_field` rows honestly.

## NEEDS-MANUAL-CHECK

- The mathjs sandbox blocks `evaluate/parse/import/createUnit`, but mathjs has a
  large surface — a 10-minute adversarial session in the live inspector trying to
  escape the scope whitelist is cheap insurance.
- Cross-lane expression parity (mathjs frontend vs the proposed Python `ast`
  handler) holds for arithmetic/comparison/boolean/named functions only; mathjs
  sugar (`^` power, matrices, units) intentionally diverges — verify agent
  prompting steers to the shared subset once wiring request 1 lands.
- The TS/Python screener-grammar twins are hand-mirrored with parity vectors in
  both suites; any future grammar change must touch both (`screener_formula.py`
  ⇄ `src/lib/screener-expr.ts`) — flag in review if only one moves.
- Visual design-law pass on the screener panel + backtest empty states was
  test-asserted but not screenshot-verified against a live populated panel
  (no app session in this overnight window).
