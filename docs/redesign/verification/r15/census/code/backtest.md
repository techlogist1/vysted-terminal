# R15 census — CRITIQUE: `backtest`

**Subsystem:** Backtest (bar-replay engine, signal DSL, canned strategies, run store, panel).
**Files graded:** all 15 in `CODE_PARTITION.json#backtest` (4 219 LOC), read in full for the
seven sidecar core files and `src/store/backtest.ts` + the three panel files.
**Method:** `aposd-critique` skill invoked and followed. Sub-agents unavailable to this worker,
so **assessment independence: degraded (sequential)** — Strategic Thinker pass completed and
recorded before the Tactical Tornado scan, then synthesised. Snapshot persistence to
`.aposd/critique/` deliberately skipped (R15 evidence lives under this tree).
**Proofs:** two throwaway probes driving the real engine in-process with fixture loaders
(`/tmp/.../scratchpad/probe_backtest.py`, `probe_metrics.py`); no network, no live app touched.

---

## Tactical Tornado verdict

**High risk, concentrated in the money path.** The DSL is the strategic part of this subsystem
(bounded grammar, positioned errors, `None`-propagating warm-up, hostility caps) — it reads like
someone designed it twice. The **engine's fill accounting and metric maths** read like someone
got the happy path working against four in-house strategies and stopped. The single most damning
pattern: `portfolio.positions[intent.symbol] = _OpenPosition(...)`
(`sidecar/services/backtest_engine.py:343`) sits directly under the comment
`# New long position OR add to existing` (`:324`) — the comment asserts pyramiding, the line
overwrites. Proven: four 10-share buys at a flat price of 100 report **total return −3.0 %**
because 30 shares of capital vanish from the book.

Flags found: information leakage (metrics ↔ curve sampling), shallow module (`backtest_store`),
pass-through variable (`options.signal`), conjoined units (strategy convention holds the engine's
invariants), special-general mixture (`_default_bar_loader`), repetition (rule parsed twice),
dead declared protocol (`progress`/`trade` events), comment-as-invariant (three sites), stale
process narrative in production docstrings ("Teammate K", 5 files).

---

## Design principles score

| # | Principle | Verdict | Evidence (`file:line`) | Consequence |
|---|---|---|---|---|
| 1 | Strategic over tactical | **at-risk** | `backtest_dsl.py:100-104` caps + `:440-443` RecursionError belt — strategic; vs `backtest_engine.py:360-385` sell path with no quantity reconciliation | Two different engineering standards inside one subsystem; the weaker one owns the P&L |
| 2 | Deep modules | **at-risk** | `backtest_store.py:57-70` — four module functions each one line over `_BacktestCache`, which is itself an `OrderedDict` with `move_to_end` | Interface ≈ implementation; the wrapper's only real decision (capacity 32) is the one thing callers can't see or set |
| 3 | Information hiding | **violate** | `backtest_engine.py:343` mutates `portfolio.positions` directly; `backtest_strategies.py:272,356,427` read `portfolio.positions[sym].quantity` to size their exits | Position bookkeeping is shared mutable state between engine and every strategy, so the engine cannot enforce a single fill rule |
| 4 | Information leakage | **violate** | equity sampled per bar `backtest_engine.py:391`; annualisation assumes per-day `:265-267` | The curve's sampling rate is knowledge the metric function needs and doesn't have → √N Sharpe error (F1) |
| 5 | General-purpose deeper | **at-risk** | `_default_bar_loader` `backtest_engine.py:169-182` raises unconditionally; `:417 loader = bar_loader or _default_bar_loader` | A general seam that only ever has one value, plus a fallback that exists to fail |
| 6 | Different layer, different abstraction | **pass** | `BacktestOrderIntent` (`:77-88`) vs `_OpenPosition` (`:90-99`) vs `BacktestTrade` (`models/backtest.py:59`) are genuinely different shapes | Intent/position/record separation is right and is why the engine could hold the invariants it currently doesn't |
| 7 | Pull complexity downward | **violate** | every bundled strategy must self-gate with `portfolio.has_position(...)` (`backtest_strategies.py:262,341,414`, `backtest_dsl.py:703`) and self-size the exit at `-held` | Four call sites carry an invariant the engine could hold once; the first strategy that forgets (plugin, agent, user) mints or destroys cash (F3, F4) |
| 8 | Better together / apart | **at-risk** | `backtest_summary.py:40-65` and `run_custom_backtest.py:35-58` are the same digest written twice ("mirrors backtest_summary" — `:36`) | Duplicated truth; a field added to one digest silently diverges the agent's two views of the same run |
| 9 | Define errors out of existence | **violate** | `bar_loader.py` swallows `ProviderError → []`; `backtest_engine.py:424` errors only when **all** symbols are empty | A partial data failure becomes a silent, smaller backtest reported as a clean success (F5) |
| 10 | Design it twice | **pass** (DSL) / **at-risk** (metrics) | `backtest_dsl.py:13-57` grammar + warm-up semantics are clearly a second draft; `_compute_metrics` `:226-288` is a first draft (Sortino = stdev of the loss subset, `:260`) | The metric block has never been checked against a reference implementation (F2) |
| 11 | Comments describe non-obvious | **violate** | `backtest_engine.py:324` "New long position OR add to existing" over a line that replaces; `routers/backtest.py:11-14` "no longer reachable" beside the handler at `:62-72` that catches it | Comments state the intended contract; the structure states the opposite, and the comment is what a reader trusts |
| 12 | Comments first | **pass** | `backtest_dsl.py:1-58`, `models/backtest.py:36-39,52-54` — the bounds carry their own rationale | Reading the model tells you why `gt=0` and `le=1000` exist |
| 13 | Choosing names | **pass** | `SimPortfolio`, `BacktestOrderIntent`, `_run_single_slice`, `required_bars` | Names carry their role; no rename would earn its diff |
| 14 | Modifying existing code | **at-risk** | `_encode_event_dict` "kept for parity" `routers/backtest.py:198`; `_default_bar_loader` `:169`; `NotImplementedError` arm `:62` | Three dead constructs preserved around one seam; each new reader re-derives that they're dead |
| 15 | Consistency | **violate** | DSL folds case for fields/functions (`backtest_dsl.py:346`) but not keywords (`:237`); `list_runs` documented "newest first" (`routers/backtest.py:176`) returns insertion order (`backtest_store.py:48`) | `SMA(20) > 50 AND close > 1` parses `SMA`, then dies on `AND` (F13); the runs list order is a documented lie (F10) |
| 16 | Code should be obvious | **violate** | `BacktestResultView.tsx:501` "Trades: {metrics.tradeCount}" (closed only) next to `:552` "Trades ({run.trades.length})" (closed + open) | Two different numbers labelled "Trades" three lines apart in one header (F16) |
| 17 | Design for the future | **at-risk** | `register_strategy` (`backtest_engine.py:144`) is public extension surface; the fill engine assumes the four in-house strategies' conventions | The extension point is advertised and unsafe for the first third-party strategy |
| 18 | Performance as design | **pass** | `bar_loader._LOAD_CONCURRENCY = 8`; `SymbolState` incremental EMA/RSI (`backtest_dsl.py:458-511`) | Single-pass indicators, bounded fan-out — no hot-spot to fix |

**Summary: 5 pass, 7 at risk, 6 violate (5/18 pass).**

---

## What's working

- **The DSL is the strategic half of this subsystem.** `MAX_TOKENS`/`MAX_NESTING_DEPTH`
  (`backtest_dsl.py:102-103`), the pre-`int()` digit-length guard (`:368-378`), the
  `RecursionError → DslError` belt (`:440-443`) and `None`-propagating warm-up (`:576,591,609`)
  mean an agent- or user-authored string can at worst fail to parse with a caret position.
  `validate_definition` is documented "never raises" and actually is.
- **The honest-degradation instinct exists.** The insufficient-cash skip counts and reports
  itself (`backtest_engine.py:326-340,452-457`), `warnings` rides the contract on both sides
  (`models/backtest.py:134`, `types/backtest.ts:155`) and the panel renders it
  (`BacktestResultView.tsx:506-510`). The mechanism is right — F5 is a hole in its coverage,
  not its absence.
- **Contract mirroring is disciplined.** `types/backtest.ts` matches `models/backtest.py`
  field-for-field, aliases included, per the CLAUDE.md hand-mirror rule.

---

## Priority issues

### [P0] Multi-symbol Sharpe, Sortino, Calmar and annualised return are wrong by a factor of √N / N

- **Principle:** 4 (information leakage), 10 (design it twice)
- **Symptom:** unknown unknowns — the number looks plausible, nothing warns.
- **Evidence:** the equity curve appends one point **per bar**, not per date
  (`backtest_engine.py:391`, inside `for bar in bars` `:313`); `_compute_metrics` then treats
  consecutive points as daily and annualises with `math.sqrt(252)` / `** 252`
  (`:251-267`). Measured on a random-walk fixture, 200 dates, buy-and-hold:

  | symbols | curve points | reported Sharpe | Sharpe on date-sampled curve | ratio | √N |
  |---|---|---|---|---|---|
  | 1 | 200 | 0.647 | 0.647 | 1.00 | 1.00 |
  | 2 | 400 | 0.674 | 0.938 | 1.39 | 1.41 |
  | 4 | 800 | 1.087 | 2.215 | 2.04 | 2.00 |

  Annualised return for the 4-symbol run: reported **+0.23 %**, honest
  `(1+total)^(252/dates)-1` = **+0.90 %**. Calmar derives from it, so it inherits the error.
- **Why it matters:** multi-symbol is a first-class input (`BacktestPanel.tsx:196` "Symbols
  (comma-sep)", `bar_loader` fans out 8-wide) and these six numbers are what the header shows
  (`BacktestResultView.tsx:477-502`) and what the Strategy Critic reasons over
  (`backtest_summary.py:55`). A wrong Sharpe presented as true is exactly the data-trust moat.
- **Fix:** collapse the curve to one point per `timestamp` (last bar of each date) before
  `_compute_metrics`, or make the periods-per-year explicit: pass
  `periods_per_year = len(returns) / trading_days_spanned` instead of the literal `252`.

### [P0] `sortino` is not the Sortino ratio — measured 41× overstatement

- **Principle:** 10 (design it twice), 16 (obviousness)
- **Symptom:** unknown unknowns.
- **Evidence:** `backtest_engine.py:260` `downside_stdev = statistics.pstdev(downside)` where
  `downside = [r for r in returns if r < 0]` (`:259`) — the **dispersion of the losses**, where
  Sortino's denominator is the downside deviation `sqrt(mean(min(r,0)²))` over **all** periods.
  Run through the real `_compute_metrics`: returns `[+2 %]×10, −5 %, −5.1 %` → reported
  **261.93**, textbook **6.35**. Two similar losses drive the denominator to ~0 and the ratio to
  the moon; identical losses give `pstdev == 0` → the code reports **Sortino 0.00**, visually
  identical to "no downside at all".
- **Why it matters:** rendered to two decimals next to a correct-looking Sharpe
  (`BacktestResultView.tsx:487`) and fed to the Critic agent as fact.
- **Fix:** one line —
  `downside_dev = math.sqrt(sum(min(r,0.0)**2 for r in returns)/len(returns))`, keep the
  `> 0` guard.

### [P1] The engine's cash/position invariants are held by strategy convention, not by the engine

- **Principle:** 7 (pull complexity downward), 3 (information hiding), 11 (comments)
- **Symptom:** change amplification + unknown unknowns.
- **Evidence:** two proven money defects, both from the same root — `_run_single_slice` applies
  an intent without reconciling it against the book:
  - **Repeat buy destroys the earlier position.** `backtest_engine.py:343`
    `portfolio.positions[intent.symbol] = _OpenPosition(...)` under the comment
    `# New long position OR add to existing` (`:324`). Four 10-share buys at a flat 100:
    cash correctly debited 4×1 001, book keeps **10 shares, not 40** → final equity
    **96 996** and **totalReturn −3.00 %** on a flat market. The orphaned entry rows keep
    `pnl = None` forever, so `tradeCount`/`winRate` never see them.
  - **Overselling mints cash.** `:365` credits `abs(intent.quantity) * fill_price` and `:385`
    pops the whole position regardless of held size. Buy 10 @ 100 then sell 100 @ 100 →
    final equity **108 989** from a flat market, trade P&L reported as `−20` (fees).
  Nothing guards either path; the only reason production is clean is that all four bundled
  strategies gate on `has_position` and size exits as `-held`
  (`backtest_strategies.py:262-279,341-363,414-434`, `backtest_dsl.py:703-712`) — a convention
  repeated four times, in code a plugin (`register_strategy` is public, `:144`) or an
  agent-authored strategy can join without knowing.
- **Fix:** put both rules inside the fill, ~8 lines in `_run_single_slice`: on buy, add to the
  existing `_OpenPosition` (weighted-average entry) instead of replacing it; on sell,
  `qty = min(abs(intent.quantity), position.quantity)`, credit and P&L on `qty`, pop only when
  it reaches 0. Then delete the `has_position` gate from the strategies that only exist to
  protect the engine.

### [P1] A partial data failure is reported as a clean, smaller backtest

- **Principle:** 9 (define errors out of existence)
- **Symptom:** unknown unknowns.
- **Evidence:** `services/bar_loader.py` catches `ProviderError` per symbol and
  `return []` (logging a warning nobody sees); `backtest_engine.py:424` raises **only** when
  `request.symbols and not bars` — i.e. all symbols empty. Ask for `AAPL, MSFT, RELIANCE.NS`,
  have one fail, and the result reports three symbols in `result.request.symbols`
  (`models/backtest.py:123`), metrics computed on two, `warnings = None`, and the panel header
  prints all three (`BacktestResultView.tsx:462`).
- **Fix:** the engine already has the channel. Compute
  `missing = set(request.symbols) - {b.symbol for b in bars}` after the load and append
  `f"no historical data for {missing} — metrics cover N of M symbols"` to `warnings`.

### [P2] Declared streaming protocol that nothing emits — the progress readout is frozen at 0 %

- **Principle:** 15 (consistency), 16 (obviousness)
- **Symptom:** cognitive load, and a UI that reads as hung.
- **Evidence:** `BacktestRunEvent.kind` declares five kinds (`models/backtest.py:142`,
  `types/backtest.ts:163-168`); the engine only ever emits two — `_emit` is called at
  `backtest_engine.py:435` (`run-start`) and `:499` (`run-complete`), confirmed by instrumenting
  a 10-bar run: `['run-start', 'run-complete']`. So `src/store/backtest.ts:183-220` (the
  `progress` and `trade` handlers, ~38 lines) is unreachable, and
  `BacktestResultView.tsx:464-468` renders `running… 0/{totalBars} (0%)` for the entire run,
  above a pane that says `computing equity curve…` (`:541-543`).
- **Fix:** either emit `progress` every K bars from the `for bar in bars` loop (the `_emit`
  helper and the queue plumbing already exist) — or delete the two kinds from the model, the
  contract, and the store, and show an indeterminate spinner. Do not leave the protocol
  half-declared.

---

## Persona walkthrough

**Tactical Tornado.** They wrote `_run_single_slice` against `BuyAndHoldDay2`
(`tests/test_backtest_engine.py:36`), which buys once and never re-buys — so `positions[sym] = …`
was never wrong in front of them, and the comment at `:324` records the intent they *meant* to
implement. They'd keep going the same way: the next special case (short entries, pyramiding,
partial exits) becomes another `if` inside the same `for intent in intents` block, and the
`# (Full close is the engine's assumed case … partial-close size reduction remains a separate,
documented limitation)` note at `:368-370` is the tell — a known-wrong case parked in prose
instead of in the structure. They'd also leave `_default_bar_loader`, the `NotImplementedError`
arm and `_encode_event_dict` exactly where they are, because deleting them is work that doesn't
close a ticket.

**Strategic Thinker.** They'd make `SimPortfolio` own the fill — `apply(intent, price) ->
Fill | None` — so "add to a position", "sell no more than held", "skip when cash is short" are
one decision in one place, and `_run_single_slice` becomes a loop over intents plus the equity
sample. That single move retires three of the six `violate` rows (3, 7, 11), deletes the
`has_position` gate from four strategies, and makes the plugin extension point at `:144` safe by
construction rather than by convention. Second, they'd give `_compute_metrics` an explicit
`periods_per_year` and a date-collapsed curve, because a metric function that silently depends on
its caller's sampling rate is a leak that no test of the current four strategies can catch.

---

## Minor observations

- `CustomDslStrategy.__init__` parses each rule twice — `validate_definition` (`backtest_dsl.py:685`)
  then `compile_rule` again (`:693-694`). Harmless today; duplicated truth if validation ever
  normalises the source.
- `paramsSchema` advertises `minimum`/`maximum` (`backtest_strategies.py:69-92`) that nothing
  enforces: `ParamsForm` drops them (`strategy-picker.tsx:110-119`), `BacktestRequest.params` is
  a free dict (`models/backtest.py:48`), and the strategies coerce with a bare `int()`
  (`:235`). `window = 0 / -5 / ""` surface as
  `fmean requires at least one data point` / `maxlen must be non-negative` /
  `invalid literal for int() with base 10: ''` in the SSE error frame.
- `startRun` takes `options.signal` (`src/store/backtest.ts:86,269`) and no caller ever supplies
  one (`BacktestPanel.tsx:133`); there is no Stop control, so a mis-typed 5-year, 8-symbol run
  must be waited out.
- Walk-forward slices share their boundary date: `_slice_dates` returns
  `[('2024-01-01','2024-01-06'), ('2024-01-06','2024-01-11')]` and the filter is inclusive at
  both ends (`backtest_engine.py:466`), so the boundary bar trades in two slices.
- `backtest_store` is in-memory, capacity 32 (`backtest_store.py:23,31`) while the partition
  calls this subsystem "persisted run history"; `backtest_summary` 404s after a sidecar restart.
  Nothing in `src/` ever calls `GET /backtest/runs` or `/runs/{id}` (grep), yet
  `catalog.py:869` tells the model "the full result renders in the backtest panel".
- Five production docstrings still narrate the build ("Teammate K's deliverable",
  `backtest_engine.py:10,176-181`; `backtest_strategies.py:1`; `routers/backtest.py:11-14`) —
  two of them now false.
- `DEFAULT_END = "2025-12-31"` (`BacktestPanel.tsx:18`) was the future when written; today the
  default range ends nine months in the past.

---

## Questions to consider

- If `SimPortfolio` owned the fill, would any strategy still need to read
  `portfolio.positions[sym].quantity`?
- What would `_compute_metrics` have to be handed for a multi-symbol run to be arithmetically
  indistinguishable from a single-symbol one?
- Is `progress` worth emitting at all, or is the honest UI a spinner plus the bar count the
  `run-start` event already carries?
