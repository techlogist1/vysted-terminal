# Code census — subsystem `screener` (APOSD critique)

**Partition entry:** `docs/redesign/verification/r15/census/CODE_PARTITION.json` → id `screener`
(16 owning files, 6,566 LOC, 12 test files).
**Responsibility (verbatim):** "Full-stack cold/warm stock screener: the India universe + formula
DSL/parser on the backend, the criteria-builder + pasted-formula UI on the frontend, and the agent
tool that lets a chat turn author a screen."

**Skill:** `aposd-critique` loaded and followed (18 principles, two personas, file:line evidence).
**Assessment independence:** degraded (sequential) — this run is itself a subagent, so Assessment A
(Strategic Thinker) and Assessment B (Tactical Tornado) were run in sequence in one head rather than
in isolated sub-agents. Noted per the skill's Hard Invariants.
**Snapshot persistence:** skipped — this run is READ-ONLY on the repo except its two output files,
so nothing was written to `.aposd/critique/`.
**Files read in full:** `sidecar/services/screener.py`, `screener_formula.py`,
`screener_universe_india.py`, `routers/screener.py`, `models/screener.py`,
`agent_tools/screener_tools.py`, `src/lib/screener-expr.ts`, `src/store/screener.ts`,
`src/modules/screener/{ScreenerPanel,ScreenerResultsTable,ScreenerCriteriaBuilder}.tsx`.
Cross-checked: `src/lib/host-actions.ts` (the `write_screener_filters` host action),
`sidecar/services/market_cap_witness.py` (the India master's other consumer),
`sidecar/services/agent_tools/catalog.py` (the tool projection).

---

## Tactical Tornado verdict

**Risk: medium-low, with two sharp exceptions.** This is not tornado code. The engine's phased
design (`screener.py:8-47`) is genuinely thought through, the wall-budget discipline is real, the
skip ledger is a deliberate honesty mechanism, and the formula parser is careful about hostile input.
A tornado does not write `_and_leaves` with a correctness argument for why OR subtrees must never
prune (`screener.py:468-484`).

What the tornado scan *did* find is a specific, repeating shape: **the module knows the right
invariant, states it in a comment, and then does not build the structure that holds it.**

| Red flag | Where | Damning detail |
|---|---|---|
| Invariant held by prose | `screener.py:41-43` ↔ `screener.py:397`, `ScreenerResultsTable.tsx:296` | "market_cap is in the LISTING currency" — then sorted with `av - bv` one screen after D57 fixed the *display* of the same field |
| Doc asserts behaviour the code omits | `screener.py:683-685` ↔ `screener.py:718` | `_finalize` promises NULL-field itemization for "a field the screen references"; checks only the enrichment subset |
| Doc asserts a feature that has no caller | `routers/screener.py:74-77` ↔ `screener.py:114` | FR-060 region default: prose describes it as shipped; zero call sites exist |
| Repetition of a *protocol* | `store/screener.ts:403`, `:425`, `:562` | The run-completion sequence written out three times, invariant documented in a 7-line comment at `:30` |
| Swallowed exception | `screener.py:985` | `except (TimeoutError, Exception)` — a tautology; an adapter `AttributeError` is indistinguishable from a network timeout, at DEBUG |
| Dead general mechanism | `screener.py:363-374`, `types/screener.ts:176` | `matched_criteria` computed in the hot loop, shipped on the wire, read by no file, always `[]` under `group` |
| Duplicated truth, already drifted | `screener_formula.py:476-490` vs `screener.py:268-278` | Two `_field_value` implementations of the same mapping; the formula one coerces to `float` and returns `None` for non-numerics, the criteria one does not |
| Inconsistent caching in one module | `screener_universe_india.py:106` vs `:130`, `:147` | Three readers of the same 1 MB file, one `@lru_cache`d, two not, no comment |
| Double-invoked render helpers | `ScreenerPanel.tsx:433/435`, `439/441`, `444/445` | `{fn() && <div>{fn()}</div>}` × 3, one of them an O(skips) Map build |

Patterns the Strategic pass initially missed and the tornado scan caught: the double-invoke idiom in
`ScreenerPanel`, the operator-change value reset (`ScreenerCriteriaBuilder.tsx:163-170`), and the
positional-tuple indexing in `screener_universe_india.py:217-220`.

---

## Design principles score

| # | Principle | Verdict | Evidence |
|---|---|---|---|
| 1 | Strategic over tactical | **pass** | `screener.py:8-47` phased U→P→B→E→F engine with a stated budget model; `_and_leaves` (`:468-484`) carries a soundness argument for why OR subtrees never prune — investment, not a patch |
| 2 | Deep modules | **pass** | `run_screener(req, wall_budget_s, on_progress) -> ScreenerResult` (`:1008`) hides five phases, a SQLite prefilter, batch chunking, a circuit breaker and partial finalization behind one call |
| 3 | Information hiding | **at-risk** | `screener.py:602` `_V7_FIELD_SET = frozenset(fundamentals_store._V7_NUMERIC_FIELDS)` and `:731` `fundamentals_store._field_column(field_name)` — the engine reaches through two underscore-private names to reconstruct the store's column vocabulary |
| 4 | Information leakage | **violate** | Listing-currency knowledge is in a comment (`screener.py:41`) and in `row.currency` (`:779`) but not in the comparator (`:397`) or the client's (`ScreenerResultsTable.tsx:296`); India master tuple layout is duplicated across `:103`, `:176`, `:217-220` and load-bearing at `market_cap_witness.py:123` |
| 5 | General-purpose is deeper | **at-risk** | `default_universe_for_region` (`screener.py:114`) is a general mechanism with zero clients; `matched_criteria` (`:394`) is a general field with zero readers |
| 6 | Different layer, different abstraction | **violate** | Sort is split across layers with neither owning it: server ranks by market_cap then truncates (`:397`, `:770`), client re-ranks the truncated page (`ScreenerResultsTable.tsx:326-330`). Also `screener_tools.py:67` re-exports the HTTP payload wholesale into an LLM context |
| 7 | Pull complexity downward | **at-risk** | `deserializeSavedScreens` (`store/screener.ts:83-142`) pushes 60 lines of hand shape-walking up to the caller while leaving `universe` and `operator` unvalidated (`:94`, `:100`) |
| 8 | Better together or apart | **pass** | Criteria evaluation, group evaluation and the formula evaluator are separately testable and separately reachable; the formula grammar's split into `screener_formula.py` earns its file |
| 9 | Define errors out of existence | **violate** | `_evaluate_criterion` returns `False` for both "value absent" and "value fails" (`:296-297`) while the formula path distinguishes them (`screener_formula.py:47-51`) — the same request answers the same question two ways. `_enrich_survivors`'s `except (TimeoutError, Exception)` (`:985`) aggregates programming errors into "field missing" |
| 10 | Design it twice | **pass** | The serve-with-label ladder (`_field_serving`, `:605-652`) is visibly a second design over "drop stale rows", with the per-tier reasoning recorded; the phased engine replaced an unbounded batch call (`:12-13`) |
| 11 | Comments describe non-obvious | **at-risk** | Excellent where present (`:468-484`, `:808-811`, `screener_formula.py:36-39` on why `pct_change` is deliberately absent) — but three load-bearing comments are false: `:683-685`, `routers/screener.py:86-88`, `market_cap_witness.py:109-111` |
| 12 | Comments first | **pass** | Every module opens with a design-level docstring stating the model before the code (`screener.py:1-56`, `screener_formula.py:1-58`, `screener_universe_india.py:1-18`) |
| 13 | Choosing names | **pass** | `_cheap_prune_criteria`, `_and_leaves`, `pruned_failed` vs `skip_reasons`, `budget_exhausted` — the vocabulary is precise and consistent with the ledger it describes |
| 14 | Modifying existing code | **at-risk** | Phase markers (R4/R7/R10/R11/D40/D52/D53/D57) are threaded through every file as running commentary; useful as provenance, but `screener.py` now carries four generations of rationale inline and `_finalize` has accreted six jobs (`:671-829`) |
| 15 | Consistency | **violate** | Null-handling differs between the criteria and formula paths for the same field; cache discipline differs between three readers of one file (`screener_universe_india.py:106` vs `:130`/`:147`); NSE master rows are unfiltered while BSE rows filter on `STATUS == "Active"` (`:59-67` vs `:77-88`) |
| 16 | Code should be obvious | **at-risk** | `partial = state.partial and bool(skip_details)` (`:812`) needs its own four-line comment to be readable; `_field_serving` returns an unnamed 3-tuple (`:605`); the boolean-coerces-to-1.0 path in the formula evaluator (`screener_formula.py:513`) is invisible at the call site |
| 17 | Design for the future | **at-risk** | Two futures were built and never arrived (`default_universe_for_region`, `matched_criteria`); the `sort_by` that the results table actually needs was not |
| 18 | Performance as design | **pass** | Chunked sweep with per-chunk upsert (`:877-879`, with the measured 1.4 ms/symbol justification), `_nse_lookup` hoisted after an O(n²) 4 s boot stall (`screener_universe_india.py:93-96`), `upsert_v7_batch` one transaction per chunk. The two regressions found (`ScreenerPanel.tsx:433-445`, `screener_universe_india.py:130`) are local |

**Summary: 8 pass, 6 at risk, 4 violate (8/18 pass).**

---

## Overall impression

This subsystem was built by someone who understood the problem. The engine's honesty machinery — the
itemized skip ledger, the serve-with-label basis ladder, the partial-finalization path, the "pruning
may only widen, never narrow" argument — is the kind of thing most screeners never build, and it is
the right investment for a product whose stated moat is data trust.

The failure mode is narrower and more interesting than sloppiness: **the module repeatedly identifies
an invariant, writes it down, and stops.** Currency is the clearest case. The team already fought this
battle once at the display layer (D57, `ScreenerResultsTable.tsx:49-54`: "₹1,293 must never render as
$1,293") and won. The comparator forty lines below still subtracts rupees from dollars, and the
criterion input still takes a bare number with no unit. The knowledge exists in the file; the
structure does not carry it.

Single biggest opportunity: **make currency and null-ness structural rather than documentary.** One
normalized comparison value on `ScreenerResultRow` and one tri-state criterion result would close the
two highest-severity findings and would delete three of the false comments at the same time.

---

## What's working

1. **The wall-budget + partial-finalization design** (`screener.py:1022-1074`, `:671-829`). Every
   phase is budgeted from one deadline closure, cancellation is caught and `uncancel()`ed so a
   disconnected client still gets an honest partial, and `_finalize` works at *any* phase. This kills
   the whole class of "the UI spun for five minutes" bug rather than one instance of it — change
   amplification avoided, because adding a phase does not require touching the timeout story.

2. **The prune-soundness argument** (`screener.py:468-497`). `_and_leaves` returns nothing for an OR
   subtree, with a three-line proof of why: a row failing one OR branch may pass another on a
   not-yet-fetched tier. `_cheap_prune_criteria` extends it — when a `group` is present the inactive
   flat list must not prune. This is the reasoning a reader cannot reconstruct alone, written exactly
   where it is needed. Unknown-unknowns reduced.

3. **The formula grammar's refusal to fabricate** (`screener_formula.py:36-39`). `pct_change` is
   deliberately not a function, with the reason stated: screener rows are point-in-time snapshots
   with no per-row history to difference. A tactical implementation adds the function and computes
   something. This one names the honest alternatives (`change_percent_1d`, `fifty_two_week_change`)
   instead.

---

## Priority issues

### [P0] Currency-denominated fields are ranked and thresholded as bare numbers

- **Principle:** 4 (Information leakage), 16 (Obviousness)
- **Complexity symptom:** Unknown unknowns — a caller cannot tell from the interface that the number
  it sorts on has a per-row unit.
- **Evidence:** `sidecar/services/screener.py:397`
  (`key=lambda row: (row.market_cap is None, -(row.market_cap or 0.0))`),
  `sidecar/services/screener.py:299` (`return value > threshold`),
  `src/modules/screener/ScreenerResultsTable.tsx:296-312` (`av - bv`, with `r.currency` in scope and
  unused), against `sidecar/services/screener.py:41-43` and
  `src/modules/screener/ScreenerResultsTable.tsx:152` (which *does* format per row currency).
- **Why it matters:** The ranking IS the output of a screener. A `custom` universe of
  `AAPL, RELIANCE.NS` — a first-class, documented flow (`store/screener.ts:374`,
  `screener_tools.py:37`) — puts Reliance above Apple under a header that reads "Market cap ▼". And
  because a `SavedScreen` carries `universe` and `criteria` together (`store/screener.ts:69-76`), the
  same saved `market_cap > 1e10` silently means $10 B on `sp500` and ₹1,000 crore on `india-all`,
  with no unit shown at either the input (`ScreenerCriteriaBuilder.tsx:31`, label "Market cap", bare
  `type="number"`) or the output.
- **Fix:** Add `market_cap_base` (one reference currency) to `ScreenerResultRow`, populate it in
  `_finalize` where `currency` is already being stamped (`screener.py:779`), and sort/threshold on it
  in `apply_criteria` and `compareValue`. Until the conversion exists, suffix the criterion input and
  the column header with the resolved universe's currency — the unit must be visible, not implied.

### [P0] A NULL on a non-enrichment field silently fails the criterion instead of being itemized

- **Principle:** 15 (Consistency), 9 (Define errors out of existence)
- **Complexity symptom:** Cognitive load — a reader must know which fields `field_needs_enrichment`
  returns true for to predict whether a NULL is reported or hidden.
- **Evidence:** `sidecar/services/screener.py:718-723` (`absent` iterates `needed_fields`),
  `sidecar/services/screener.py:433-443` (`_enrichment_fields_needed` filters to
  `yahoo_batch_provider.field_needs_enrichment(f)`), `sidecar/services/screener.py:296-297`
  (`if value is None: return False`), against the promise at `sidecar/services/screener.py:683-685`
  and the formula path's opposite semantics at `sidecar/services/screener_formula.py:47-51`.
- **Why it matters:** `pe_ratio < 20` as a *criterion* drops NULL-P/E rows silently and reports
  "screened 2,675 of 2,675 — 0 unavailable"; `pe < 20` as a *formula*, in the same request, itemizes
  them `missing_field:pe_ratio`. SC-034's "zero silent drops" holds for the fields least likely to be
  NULL and fails for the ones most likely (P/E on loss-making names, dividend_yield on non-payers).
  The result is that "no rows matched" is indistinguishable from "we had no data" — the exact
  confusion the ledger was built to prevent.
- **Fix:** In `_finalize`, compute `absent` over `_criteria_fields(list(req.criteria), req.group) |
  set(formula_fields)` rather than over `needed_fields`. `_criteria_fields` already exists two
  functions above (`:421`) and is already called at `:699` for `basis_fields`.

### [P1] Column sort reorders only the truncated page

- **Principle:** 6 (Different layer, different abstraction)
- **Complexity symptom:** Change amplification — neither layer can fix this alone; the request
  contract has to change.
- **Evidence:** `sidecar/services/screener.py:397-399` (server ranks by market_cap),
  `sidecar/services/screener.py:770-771` (`rows = matched[:limit]`),
  `src/modules/screener/ScreenerResultsTable.tsx:326-330` (client re-sorts `result.rows`).
- **Why it matters:** "Cheapest stock on the NSE" is a query the UI visibly offers (a sortable P/E
  header) and silently cannot answer — it returns the cheapest of the 200 largest. For a screener
  benchmarked against screener.in this is a core-flow break, not a polish item, and there is no
  affordance anywhere that discloses it.
- **Fix:** Add `sort_by: ScreenerNumericField | None` + `sort_dir` to `ScreenerRequest`, apply in
  `apply_criteria` before the limit cut (the comparator at `:397` is already the single sort site),
  and make the header click re-run rather than re-sort.

### [P1] `default_universe_for_region` is dead — the India-first default was never wired

- **Principle:** 17 (Design for the future), 11 (Comments describe non-obvious)
- **Complexity symptom:** Unknown unknowns — the router docstring teaches a reader that FR-060 ships.
- **Evidence:** `sidecar/services/screener.py:114-117` (defined), `:1323` (exported), zero call sites
  across `*.py`/`*.ts`/`*.tsx` including `sidecar/tests/`; `src/store/screener.ts:267` and `:654`
  hardcode `universe: "sp500"`; `sidecar/routers/screener.py:74-77` describes the mechanism as the
  home of region-aware defaults "for the callers that must *choose* a default" — there are none.
- **Why it matters:** An Indian user opens the flagship India-market terminal's screener on the S&P
  500, with a default `market_cap > 100_000_000_000` criterion (`store/screener.ts:233`) that is
  incoherent the moment they switch universe (see P0 #1). The product's positioning is contradicted
  by the panel's first frame, and the capability to fix it already exists and is merely unconnected.
- **Fix:** Initialise the store's `universe` from the region surface on first mount via
  `default_universe_for_region`, or delete the function and the router docstring's claim. Do not
  leave it in the third state.

### [P1] The `screener_run` agent tool ships an unbounded skip ledger into model context

- **Principle:** 6 (Different layer, different abstraction), 7 (Pull complexity downward)
- **Complexity symptom:** Change amplification — every field added to `ScreenerResult` silently
  enters every agent turn.
- **Evidence:** `sidecar/services/agent_tools/screener_tools.py:67-70`
  (`result.model_dump(mode="json")`), `sidecar/models/screener.py:347` (`skip_details` is one entry
  per dropped symbol), against the tool's own stated concern at `screener_tools.py:39-42` (it caps
  `limit` to 50 because 200 "produces a chunky context blob for agents").
- **Why it matters:** One partial `india-all` screen emits up to ~5,000 `{symbol, reason}` objects.
  The tool caps the useful payload at 50 rows and then ships two orders of magnitude more bookkeeping,
  consuming the context the agent was supposed to reason in.
- **Fix:** In `_screener_run`, replace `skip_details` with the reason-count aggregate the UI already
  computes (`ScreenerPanel.tsx:161-175`) before returning — same honesty, two lines of payload.

---

## Persona walkthrough

**Tactical Tornado walkthrough.** If the Tornado owned this code, the growth would not be in the
engine — it would be in `_finalize` and in `runScreener`. `_finalize` (`screener.py:671-829`) is
already six jobs in one function: store fetch, missing-field itemization, per-field basis
classification, formula evaluation, criteria application, and human-string composition. Each new
honesty requirement (D52 added the basis ladder, D57 added currency stamping) has been appended
in place, and line `:812` — `partial = state.partial and bool(skip_details)` — now needs a
four-line comment to explain what `partial` means this quarter. The Tornado adds D58 the same way.
Symmetrically, `store/screener.ts:315-565` has already accreted three copies of the run-completion
protocol (`:403`, `:425`, `:562`) each with its own `isCurrent()`/`aborted` ordering, governed by a
seven-line comment at `:30-36`; the Tornado adds a fourth transport fallback and a fourth copy, and
one of the four eventually drops the guard.

**Strategic Thinker walkthrough.** The Strategic redesign is small and specific, not a rewrite. (1)
Make the two invariants structural: one `market_cap_base` field populated where `currency` is already
stamped (`screener.py:779`) so `apply_criteria`'s comparator (`:397`) and `compareValue`
(`ScreenerResultsTable.tsx:296`) have a single unit-safe number to use; and one tri-state from
`_evaluate_criterion` (`matched | failed | absent`) so the criteria path can itemize absence exactly
as the formula path does, deleting the `needed_fields` special case at `:718` entirely. (2) Extract
from `_finalize` the one cohesive piece that keeps growing — the per-row basis classification
(`:725-747`) — into `_classify_row_basis(row, basis_fields, now, quote_ttl) -> (basis, as_of)`,
leaving `_finalize` as fetch → classify → evaluate → compose. (3) On the client, one
`finish(patch)` helper closing over `controller` so the superseded-run invariant lives in code rather
than in the comment at `:30`. Three changes, four of the five priority issues closed, and three
currently-false comments become deletable because the structure says what they were claiming.

**Where the two assessments agreed:** the currency leak and the enrichment-only NULL check were the
top two in both passes. **Where Strategic saw strength the Tornado scan would have flagged:** the
per-field `_field_serving` tuple and the density of phase markers look like accretion to a red-flag
scan, but they are a deliberate, documented honesty model (principle 10, Design It Twice) and should
not be simplified away.

---

## Minor observations

- `screener_formula.py:476-490` `_field_value` duplicates `screener.py:268-278`
  `_numeric_field_value` — the stated reason ("to avoid a service-module import cycle") is real but
  the function depends only on `models`, so it could live there. The two copies have already drifted:
  the formula one coerces via `float()` and returns `None` for non-numerics, the criteria one does not.
- `src/lib/screener-expr.ts:40-70` hand-lists all 29 numeric fields while the Python side derives them
  from `get_args(ScreenerNumericField)` (`screener_formula.py:92`). Adding a field is auto-picked-up
  server-side and silently missed client-side; the only accidental guard is the exhaustive
  `FIELD_HINTS: Record<ScreenerNumericField, string>` at `:445`.
- `ScreenerPanel.tsx:15-23` `UNIVERSE_LABELS` is a third hand-maintained copy of labels the sidecar
  already returns (`screener.py:223`/`:232`/`:244`, `screener_universe_india.py:168`/`:175`/`:185`);
  the panel fetches `universeInfo` (`:113`) and reads only `.symbols.length`/`.asset_class`, never
  `.label`.
- `screener_universe_india.py:59-67` takes every NSE master row regardless of instrument type — 326
  of the 2,675 rows are `ETF` (verified against the bundled master) — while the BSE path filters on
  `STATUS == "Active"` (`:84`). `nse-all`/`india-all` therefore mix funds into an
  `asset_class="equity"` universe, and no criterion field exists to exclude them.
- `ScreenerCriteriaBuilder.tsx:170` and `:216` use `Number(e.target.value)`, so clearing a numeric
  input yields `0` rather than empty — `market_cap > 0` matches everything.
- `routers/screener.py:91` `_sse_frame(payload: dict)` and `:172`
  `FormulaValidation(**screener_formula.validate_formula(...))` both cross the model boundary as bare
  dicts; `screener_formula` already imports from `models.screener` (`:67`), so `validate_formula`
  could return the model.
- During a run the panel keeps the *previous* result's coverage / PARTIAL badge / basis lines mounted
  (`ScreenerPanel.tsx:402`) while the table below shows a skeleton — stale coverage numbers presented
  without qualification for the duration of the new run.

---

## Questions to consider

1. If `ScreenerResultRow` carried one unit-normalized comparison value, how many of this subsystem's
   currency comments could simply be deleted?
2. `_evaluate_criterion` returns `bool`. The formula evaluator returns `(matched, missing_field)`.
   Both answer the same question about the same row in the same run — what is the argument for two
   answers, and does it survive being written down?
3. The engine already owns the only sort (`apply_criteria:397`) and the only truncation (`:770`).
   What is the client's sort doing that the server could not do better, given it sees all matches and
   the client sees `limit`?
4. `matched_criteria` has no reader and `default_universe_for_region` has no caller. Is there a cheap
   check — a dead-export lint over `__all__` and `types/`— that would have surfaced both before they
   shipped twice?

---

## Run notes

- Target slug: `screener` (partition id). Ignore list: none (`.aposd/critique/ignore.md` absent).
- Assessment independence: **degraded (sequential)** — sub-agents unavailable from inside a subagent.
- Snapshot persistence: **skipped** — read-only run; no write to `.aposd/critique/`.
- One targeted proof executed (`sidecar/.venv/bin/python`, direct `services.screener_formula` call,
  no test file modified, no process started or stopped) to confirm COD-screener-6's boolean coercion.
  No requests were issued to the operator's live app or to the isolated sidecar; this was a pure code
  sweep. No GUI interaction.
- Raw findings: `docs/redesign/verification/r15/census/raw/code-screener.json` (15 findings:
  1 critical, 4 high, 9 medium, 1 low).
