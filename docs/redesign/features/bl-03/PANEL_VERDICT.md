# BL-03 panel verdict — extracted passages

Verbatim quotes pulled from the r15 invent-phase panel and backlog documents. Each
section names its source file and the line range it was copied from, as read at
worktree HEAD `0af5afc1` on `004-r4-experience-rebuild`.

## `docs/redesign/verification/r15/invent/PANEL.md`, verdict table row (line 29)

```
| 1 | BL-03 | Reasons about you: your position and your notes in every answer | 4/5/4.5 | 4/5/4.5 | 5/5/5.0 | 4/4/4.0 | 5/4/4.5 | 1.5 | N | The position line and a renderer-side brief card from the holdings the snapshot already carries; zero tokens, keyless, closes WLD-agent-native-ux-1. Top survivor. |
```

## `docs/redesign/verification/r15/invent/PANEL.md`, top-3 order paragraph (line 98)

```
**Top-3 order.** Judge A's top three were BL-15, BL-03, BL-18; Judge B's BL-03, BL-11, BL-18. Both judges mark BL-03, BL-11 and BL-18 as small-build candidates; the ranking rule puts them at 1, 3, 2. BL-15 is a candidate for Judge A only and its reframe drops to rank 9 on the averaged scores, so the runners-up are BL-18 and BL-11.
```

## `docs/redesign/verification/r15/invent/PANEL.md`, ranked survivors item 1 (line 104)

```
1. **BL-03** Reasons about you: your position and your notes in every answer (1.5/day, life 4.5): The position line and a renderer-side brief card from the holdings the snapshot already carries; zero tokens, keyless, closes WLD-agent-native-ux-1. Top survivor.
```

## `docs/redesign/verification/r15/invent/PANEL.md`, section "5. The one small build: BL-03 Reasons about you (the position half)" (lines 152–175)

```
## 5. The one small build: BL-03 Reasons about you (the position half)

**Why this row.** Rank 1 on value per build-day (1.5/day) with lifecycle 4.5; the only row both judges score feasibility 5 and mark as a small-build candidate. Judge A: "the residual is a preamble position line and a brief metric". Judge B: "what is missing is the one line the real user notices in every answer about a held name: quantity, average cost, weight in the book"; his one objection (an 8b model's attention to a preamble line) is answered by placing the line immediately before the deixis sentence the model already obeys, and by the transcript demo.

**Boundary check (passed).** Reads the tracked portfolio the user keeps by hand (explicitly kept); no broker, no order, no write. No Tier-4 file. No new capability (the catalog and the roster tests stay untouched; the position never projects to MCP). Works keyless: the preamble is a string the local model reads, the card is derived on the renderer from the store it already has. No new dependency. Design system: on (one existing metric-card group, no new primitive). Two-tier research untouched. Green release line: additive code behind guards, two new tests, no wire change.

**What the user gets.** Every answer about a name they hold starts from their position: quantity, average cost, weight in the book, unrealised P&L, at zero tokens and with no tool round. The research brief for a held name shows a 'Your position' card beside the live metrics. Closes census finding WLD-agent-native-ux-1 (high).

**Size band.** S, 2-3 days for a small agent team. One sidecar function edit, one renderer helper, one store selector, two call sites, two test files.

**Files to touch (paths and lines verified at HEAD `913235f3`).**

1. `sidecar/services/agent_runtime.py`, `_render_terminal_preamble` (def at line 404; the `Portfolio:` line is line 460). Directly after line 460 and before the `openPanels` line: look up `ts['focusedSymbol']` in `pf.get('holdings') or []` (exact symbol match, case-insensitive, `TerminalHolding` shape from `context-provider.ts:38-51`: `symbol`, `quantity`, `costBasis`, optional `marketValue`, `pnl`) and append one line: `Your position in <SYM>: <quantity> units, avg cost <costBasis>, <weight>% of book, unrealised P&L <pnl>.` Weight = `marketValue / totalValue` only when both are numeric and `totalValue > 0`; when `marketValue` or `pnl` is null say `not marked-to-market (open the Portfolio panel)`, never 0 (the E3/E6 honesty rule already in the file). Then one line `Held: SYM1, SYM2, ...` capped at 12 symbols so the model knows a mentioned name is held without a `get_portfolio` round. No holdings, or no match: render nothing new. Keep the line before the `When the user says "this"` deixis sentence (line 475-478) so the 8b model reads the position next to the instruction it already follows.
2. `src/modules/research/brief-blocks.tsx`, `deriveMetrics` (line 412): add an optional second argument `position?: { quantity: number; costBasis: number; marketValue?: number | null; pnl?: number | null; weight?: number | null }` and, after the semantic items, push one 'Your position' group of `MetricItem`s (`:74`): `Your position` = `<quantity> @ <costBasis>`; `Unrealised P&L` and `Weight in book` only when non-null (the existing `makeItems` collector at `:118` already drops absent values). Absent argument: output identical to today.
3. `src/store/portfolios.ts` (`PortfoliosState` at `:99`, `usePortfoliosStore` at `:121`): one selector `holdingFor(symbol: string): Holding | null` returning the active portfolio's (`activeId`) case-insensitive match. `src/modules/research/BriefPanel.tsx:641` and `brief-blocks.tsx:1061` (`BriefBody`) pass `holdingFor(brief.symbol)` into `deriveMetrics`; `marketValue`/`pnl`/`weight` come from the same mark-to-market rows `PortfolioPanel.tsx:405-460` publishes when the panel has them, else null.
4. Tests. `sidecar/tests/test_agent_runtime.py` beside `test_terminal_preamble_renders_prior_stated_values` (line 387): (a) focused `TANLA` with a matching holding renders the `Your position in TANLA` line with weight and P&L; (b) null `marketValue` renders the not-marked-to-market wording and no percentage; (c) a focused symbol with no holding renders neither line; (d) 13 holdings render a 12-symbol `Held:` line. `src/modules/research/brief-blocks.test.ts`: `deriveMetrics(structured, position)` yields the group; `deriveMetrics(structured)` is unchanged (snapshot of today's output).
5. Gates before merge: `pnpm typecheck`, `pnpm vitest run src/modules/research`, `pytest sidecar/tests/test_agent_runtime.py sidecar/tests/test_tool_loop_e2e.py`, `ruff format --check sidecar && ruff check sidecar`, `pnpm format:check`.

**Acceptance test that pins it.** `test_terminal_preamble_renders_focused_position`: given `by_source['__terminal__'] = {focusedSymbol: 'TANLA', portfolio: {positionCount: 2, totalValue: 812000, holdings: [{symbol: 'TANLA', quantity: 500, costBasis: 812, marketValue: 405000, pnl: -17500}, {symbol: 'KAYNES', quantity: 100, costBasis: 4070, marketValue: 407000, pnl: 0}]}}`, the preamble contains `Your position in TANLA: 500 units, avg cost 812, 49.9% of book, unrealised P&L -17,500` and `Held: TANLA, KAYNES`; with `marketValue: null` it contains `not marked-to-market` and no percentage; with `focusedSymbol: 'INFY'` neither line appears but `Held:` does.

**Demo.** A chat transcript: portfolio panel open with TANLA 500 @ 812, chart focused on TANLA, keyless llama3.1:8b, user asks `should I add to TANLA?`; the reply quotes the position and weight before reasoning, with no `get_portfolio` step in the trace. Plus one populated brief screenshot (dark, 1920x1080 and 2560x1440) of TANLA showing the 'Your position' card beside the live metric cards, under `docs/screenshots/v<tag>/`.

**Explicitly out of scope.** No new agent tool or catalog entry (roster/parity counts unchanged). No change to `read_notes` or the notes line (they exist, R15-AGENT-020/021). No sidecar wire change to `gather_fast` or `BriefStructured`, no `types/data.ts` or `sidecar/models` mirror (Judge B's fast.py/types/brief.ts variant is rejected as a wire change for the same card). No portfolio write of any kind. No position for symbols only mentioned in the message (the `Held:` list covers the tool decision). No MCP projection of the position. No per-symbol note excerpt growth.
```

## `docs/redesign/verification/r15/invent/BACKLOG.md`, dependency graph line (line 37)

```
BL-03 Reasons about you ──► BL-09 · BL-27 Rulebook · BL-37
```

## `docs/redesign/verification/r15/invent/BACKLOG.md`, ranked backlog row (line 50)

```
| 3 | BL-03 Reasons about you: your position and your notes in every answer | 1 | S-M | 4 | reads | — | OPP-7 |
```
