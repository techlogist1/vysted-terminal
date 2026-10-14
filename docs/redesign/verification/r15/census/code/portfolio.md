# CODE CRITIQUE — `portfolio`

**Subsystem** (CODE_PARTITION.json): paper-portfolio persistence and P&L — SQLite positions,
the metrics module, the panel, and the agent-facing `broker_portfolio` read tool. 1639 LOC.

**Method**: `aposd-critique` skill loaded and followed (18 principles, pass / at-risk / violate,
mandatory `file:line` evidence, two personas). **Assessment independence: degraded (sequential)**
— no sub-agent tool is available to a worker in this run, so Strategic Thinker and Tactical
Tornado passes were run back-to-back in one head. Snapshot persistence to `.aposd/critique/`
deliberately skipped (this run's output files are the deliverable; no repo pollution).

Every file in the partition was read in full, plus the consumers the partition does not own but
that define its real contract: `src/lib/host-actions.ts` (the only writer of the sidecar ledger),
`sidecar/services/agent_tools/catalog.py`, `sidecar/services/broker_base.py`,
`sidecar/services/brokers/{kite,dhan,angelone}.py`, `sidecar/models/broker{,_reads}.py`,
`sidecar/services/brokers/registry.py`, `sidecar/services/agent_runtime.py`.

---

## Tactical Tornado verdict

**Risk: HIGH.** Not because the code is sloppy — it is unusually well-commented and several
hard-won money-honesty laws (D57 mixed currency, denominator-matched P&L%, null-not-zero P&L
percent) are implemented carefully. The tornado damage is structural: **the subsystem was built
twice and neither copy was deleted.** A sidecar SQLite CRUD (`models/portfolio.py`,
`routers/portfolio.py`, `services/portfolio_db.py`, 331 LOC of tests) and a frontend Zustand
store (`src/store/portfolios.ts`) both claim to be the portfolio. Four docstrings make three
incompatible claims about which one is true. The write path that connects them is dead by
construction (COD-portfolio-2), nothing reads the SQLite side, and the seam accumulated a dead
68-line typed client (COD-portfolio-7), an unreachable error banner (COD-portfolio-4), and a
CSV exporter that violates the exact currency law the table beside it enforces
(COD-portfolio-5).

The most damning single pattern is not in the partition's own files but in what it hands the
model: `broker_portfolio.py:36` serialises an `AccountSummary` that carries **no provenance
label**, and three adapters return hardcoded ₹10,00,000 equity / ₹5,00,000 cash in paper mode.
The sibling granular read path computes `synthetic` correctly one file over
(`brokers/kite.py:231`). That is fabricated money reaching the LLM described as "REAL".

---

## Design principles score

| # | Principle | Verdict | Evidence (`file:line`) | Consequence |
|---|---|---|---|---|
| 1 | Strategic over tactical | **violate** | `PortfolioPanel.tsx:121-123` adapts `Holding`→`Position` with the stated reason "keeps metrics.ts + its tests untouched"; `portfolio_db.py:1-12` and `modules/portfolio/api.ts:4-7` each assert a different owner of truth | Two persistence designs shipped instead of one chosen; tests now shape production shape |
| 2 | Deep modules | **at-risk** | `portfolio_db.py:81-149` — five functions, each one SQL statement; `routers/portfolio.py:21-47` wraps them 1:1 | Interface as wide as implementation; no behaviour hidden that a caller could not write |
| 3 | Information hiding | **at-risk** | `PortfolioPanel.tsx:124-136` builds the sidecar wire shape (`cost_basis`, `asset_class`, `opened_at`) for a computation that never crosses the wire | The sidecar's serialization format leaks into a pure client-side calculation; renaming a wire field edits the panel |
| 5 | General-purpose is deeper | **pass** | `metrics.ts:88` `buildPortfolioSummary(positions, quotes)` — pure over two collections, consumed by the table (`PortfolioPanel.tsx:314`), CSV export (`486`) and the context publisher (`212`) | One function serves three callers with no interface change |
| 6 | Different layer, different abstraction | **violate** | `routers/portfolio.py:21-24` and `27-30` mirror `portfolio_db.list_positions` / `create_position` exactly — textbook pass-through methods | A layer that adds nothing but a URL; every schema change is edited twice |
| 7 | Pull complexity downward | **violate** | `portfolios.ts:151-162` `addHolding` returns `void`, so `addPosition:226-236` must snapshot the count, re-read, and assume append-at-end to learn the id it just created | Caller-side reconstruction of information the store already had |
| 8 | Better together / apart | **violate** | `portfolio_db.py:1-12` vs `modules/portfolio/api.ts:4-7` ("there is NO sidecar positions CRUD") vs `portfolios.ts:212-213` ("no sidecar CRUD") vs `host-actions.ts:1254,1321` ("the paper-portfolio positions endpoint (sidecar SQLite ledger)") | One concept, two stores, four docs, three contradictory claims |
| 9 | Define errors out of existence | **violate** | `api.ts:27-32` catches every quote error to `null`, so `fetchPositionQuotes` can never reject, so `PortfolioPanel.tsx:153-159` `.catch` and the banner at `794-808` are unreachable | The error was masked at the wrong level: the panel's honest-failure path is dead code |
| 10 | Design it twice | **at-risk** | Both designs exist in the tree: sidecar CRUD (`routers/portfolio.py`) and store (`portfolios.ts`) | The second design was written; the first was never deleted |
| 11 | Comments describe non-obvious | **at-risk** | Excellent: `metrics.ts:26-32,63-69` explain D57 and the denominator fix. Actively false: `portfolios.ts:210-212` names importers that do not exist (`host-actions.ts:43` imports only the hook); `portfolios.ts:105` says "Patch" for a full replace | Comments are the only statement of several invariants, and some of them are wrong |
| 12 | Comments first | **pass** | `metrics.ts:11-80` — every exported field documents its contract *including* its null semantics before the body | A reader learns `marketValue: null` means "quote did not resolve", not "zero" |
| 13 | Choosing names | **at-risk** | `Position` (wire) / `Holding` (store) / `PositionRow` (metrics) / `PortfolioTableRow` (`PortfolioPanel.tsx:31`) — four names for one concept in one module; `refresh()` (`portfolios.ts:273-276`) names an action it does not perform | Every reader must re-derive which of the four they are holding |
| 14 | Modifying existing code | **at-risk** | `portfolios.ts:255-260` fixes the fabricated-success re-read in `updatePosition` and explains why; the identical pattern survives in `addPosition:226-236` | The lesson was written down and applied to one of two siblings |
| 15 | Consistency | **violate** | Quote polling: `WatchlistPanel.tsx:219-224` polls, `PortfolioPanel.tsx:142-164` never refetches. D57: enforced at `PortfolioPanel.tsx:402`, ignored at `486-497`. Validation: `PortfolioPanel.tsx:266-277` guards, `portfolios.ts:69-89` does not | Three separate "the sibling does it, this one doesn't" defects |
| 16 | Code should be obvious | **at-risk** | `PortfolioPanel.tsx:314-317` joins metrics rows to holdings **by array index**; the invariant lives only in the comment at `312-313` and the `id: i` at `127` | A future reorder or filter in `buildPortfolioSummary` silently mislabels every edit/delete button |
| 17 | Design for the future | **violate** | 190 LOC of sidecar CRUD + 331 LOC of tests for a table with no production reader (`GET /portfolio/positions` appears only in `sidecar/tests/` and `host-actions.test.ts`) | Deletion was the available move; extension was taken |
| 18 | Performance as design | **pass** | `api.ts:35-45` fans quotes out with `Promise.all`; `PortfolioPanel.tsx:166` memoises the summary on `[positions, quotes]`; `224` keys the publish effect on a serialized holdings string | No N+1 waterfall, no publish churn |
| 19 | Increments are abstractions | **at-risk** | `PortfolioPanel.tsx` is 838 LOC carrying form state, portfolio-name edit state, quote fetching, the drop ladder, the context publish and CSV export; `metrics.ts` is the module's only extracted abstraction | Decomposed by UI surface, not by abstraction boundary |

**Summary: 3 pass, 8 at risk, 7 violate (3/18 pass).**

---

## What's working

- **`metrics.ts` is the strongest file in the partition.** Pure, fully documented, and it refuses
  to fabricate: `metrics.ts:100` returns `null` P&L% on a zero cost basis rather than a
  misleading `+0.00%`; `metrics.ts:107-110` matches the P&L denominator to the *resolved*
  positions only; `metrics.ts:118-140` buckets by quote currency because "₹64,650 + $1,200 is not
  65,850 of anything" (`metrics.ts:26-32`). Each of these is a money-honesty law held by
  structure, not by convention.
- **`broker_portfolio.py` is correctly thin on the safety axis.** 41 lines, read-only, no order
  path, typed recoverable errors (`broker_portfolio.py:31,35`), a catalog-declared 20 s timeout
  (`catalog.py:929`) enforced by `agent_runtime.py:655-666`, and a blanket
  `except Exception` upstream at `agent_runtime.py:671` that turns any raw adapter failure into a
  model-readable result. Its §6.5 posture is sound — the defect below is a provenance defect, not
  a safety-boundary one.
- **The D57 mixed-currency law is implemented end-to-end in the UI** — totals per currency
  (`PortfolioPanel.tsx:726-752`), concentration withheld with a stated reason (`756-767`), the
  weight column dropped (`402`). It is exactly the "never publish a fabricated aggregate"
  discipline the product needs. Which is what makes the CSV hole (COD-portfolio-5) a regression
  against the project's own standard rather than an oversight.

---

## Priority findings

### [P0] COD-portfolio-1 — the agent is handed fabricated broker money labelled "REAL"

**Principle**: Define errors out of existence / Consistency · **Symptom**: unknown unknowns,
money-relevant.

`broker_portfolio.py:36` returns `summary.model_dump(by_alias=True)`. `AccountSummary`
(`models/broker.py:109-121`) has **no** `synthetic` / `mode` / `provider` field — `extra="forbid"`,
so nothing can add one at the boundary either. The three brokers in the tool's enum
(`catalog.py:921`) all return hardcoded figures whenever `self._mode == "paper" or self._client
is None` — the ABC's default mode is `"paper"` (`broker_base.py:94`):

- `brokers/kite.py:179-189` → equity `1_000_000.0`, cash `500_000.0`, buyingPower `1_000_000.0`,
  `positions=[]`
- `brokers/dhan.py:112-122` → identical
- `brokers/angelone.py:89-99` → identical

The tool's own docstring (`broker_portfolio.py:3-5`) and its catalog description
(`catalog.py:913-915`) both say **"the user's REAL connected-broker account"**. So "what is my
Zerodha buying power?" returns ₹10,00,000 of nothing, stated as fact, with no way for the model
to know. The `or self._client is None` disjunct means a **live**-mode adapter whose client failed
to build fabricates too, rather than raising `BrokerError`.

The correct pattern already exists one file over: `brokers/kite.py:231-234` computes
`synthetic = self._mode == "paper" or self._client is None` for the granular read, and
`models/broker_reads.py:13-14,42-44` documents the FR-041 label as mandatory *"so a paper /
disconnected read is never mistaken for a live one"*.

**Fix (smallest)**: in `_broker_portfolio`, add the label at the tool boundary from state the
adapter already exposes — `{"synthetic": adapter.mode == "paper", "mode": adapter.mode,
"provider": broker}` alongside `"account"` (`broker_base.py:110` exposes `mode`). No ABC change,
no §6.5 change, no `AccountSummary` change. Second choice: route the tool through the
`positions_info` seam, which already carries the label.

### [P1] COD-portfolio-2 — the sidecar ledger can never see an update or a delete

**Principle**: Define errors out of existence · **Symptom**: change amplification, silent
divergence.

The catalog types `position_id` as `{"type": "string"}` (`catalog.py:1345`) — it is the frontend
holding id (`h-<uuid>`), which is what `resolveHolding:550` matches on.
`sidecarPositionId` (`host-actions.ts:1313-1317`) does `Number("h-3f2a…")` → `NaN` →
`Number.isInteger(NaN)` is false → `undefined`. So `portfolioUrl(undefined)` (`1255-1259`) yields
`/portfolio/positions`, and the router declares PUT/DELETE **only** at
`/positions/{position_id}` (`routers/portfolio.py:33,42`) → FastAPI answers **405**.
`syncPositionToSidecar` returns `response.ok || response.status === 404` → `false`
(`host-actions.ts:1306`) — and both call sites discard the boolean (`1361`, `1381`).

Consequence: the SQLite table is append-only by accident. An agent-added, then agent-deleted
position stays there forever; an agent-updated position keeps its original quantity. Since
nothing reads the table today the damage is latent, which is exactly what makes it dangerous —
the first feature that reads it (restore, reconciliation, a `get_portfolio` backed by the
ledger) inherits silently wrong money.

**Fix**: delete the sync (see COD-portfolio-3) — or, if the ledger is to stay, return the
sidecar's assigned integer id from the POST (`host-actions.ts:1337` currently discards the
response) and store it on the `Holding` so PUT/DELETE can address a real row.

### [P1] COD-portfolio-3 — portfolio truth is forked, and the fork is undocumented-to-wrong

**Principle**: Better together or better apart / Design for the future · **Symptom**: change
amplification.

The user path writes only the store (`PortfolioPanel.tsx:286-289`, `309`). The agent path writes
both (`host-actions.ts:1337`+`1342`, `1361`+`1366`, `1381`+`1386`). Nothing reads the sidecar
side: `GET /portfolio/positions` appears only in `sidecar/tests/test_portfolio.py` and
`host-actions.test.ts:987`. So the two stores diverge from the first hand-entered holding, and
the divergence has no detector.

Meanwhile the four docstrings disagree: `portfolio_db.py:1-12` ("SQLite-backed positions store
**for the portfolio panel**"), `modules/portfolio/api.ts:4-7` ("there is **NO** sidecar positions
CRUD"), `portfolios.ts:212-213` ("no sidecar CRUD"), `host-actions.ts:1254,1321` ("the
paper-portfolio positions endpoint (sidecar SQLite ledger)"). A maintainer cannot learn the
answer by reading.

**Fix**: pick one. The store already is the truth every surface reads (panel, workspace blob,
`get_portfolio` snapshot) — so delete `routers/portfolio.py`, `services/portfolio_db.py`,
`models/portfolio.py`, `syncPositionToSidecar`/`portfolioUrl`/`sidecarPositionId`/`positionBody`
(`host-actions.ts:1254-1317`) and `sidecar/tests/test_portfolio.py`: ~520 LOC deleted, one
truth left, three false docstrings gone with them. (`models/portfolio.Position` is re-exported
by `models/__init__.py:74` and referenced by `models/broker.py:13`'s prose — check both when
cutting.)

### [P1] COD-portfolio-4 — a sidecar outage is indistinguishable from "symbol not found"

**Principle**: Define errors out of existence · **Symptom**: cognitive load, data trust.

`fetchPositionQuote` (`api.ts:23-32`) wraps every call in `try/catch` returning `null`.
`fetchPositionQuotes` (`35-45`) is `Promise.all` over those never-rejecting promises, so it
cannot reject. Therefore `PortfolioPanel.tsx:153-159`'s `.catch(() => setQuotesError(true))`
never fires, and the entire banner + Retry control (`112-113`, `794-808`) is unreachable at
runtime. The panel tests only ever `mockResolvedValue` (`PortfolioPanel.test.tsx:62,94,113,132`),
so nothing catches it.

With the sidecar down, every Price / Mkt val / P&L cell reads `—`, the summary bar shows
`Market value: …` of the resolved subset (zero), and the footer says "N without a live quote" —
the same rendering a portfolio of genuinely unknown tickers produces. On a terminal whose moat is
data trust, "we couldn't reach the data" and "this instrument does not exist" must not look
identical.

**Fix**: make the failure legible where it is known. In `fetchPositionQuotes`, count the nulls
that came from a *thrown* error separately (or have `fetchPositionQuote` return a
`{quote} | {error}` union) and return `{quotes, failed: number}`; set `quotesError` when
`failed > 0`. The banner and Retry already exist and already work.

### [P2] COD-portfolio-5 — the CSV export fabricates cross-currency weights and drops currency

**Principle**: Consistency · **Symptom**: money-relevant wrong data, outside the app's guardrails.

`handleExport` (`PortfolioPanel.tsx:469-505`) writes `Weight %` unconditionally
(`495`), although the table drops that column precisely because the ratio is corrupt across
currencies (`402`, and the rationale at `400-401`). The header row (`474-485`) has `Price`,
`Market value`, `P&L` as bare numbers with **no currency column** — so a ₹ row and a $ row are
indistinguishable in the file. The in-app D57 law is enforced in the panel and abandoned in the
artifact the user takes to a spreadsheet, which is where they will actually do arithmetic on it.

**Fix**: add a `Currency` column sourced from `quote?.currency` and blank the `Weight %` cell
when `summary.mixedCurrencies` — two lines, and it matches what the table already decided.

---

## Secondary findings (full detail in `raw/code-portfolio.json`)

- **COD-portfolio-6** (medium) — `editingId` (`PortfolioPanel.tsx:106`) survives a portfolio
  switch (`557-569` never clears it). Edit a holding in A, switch to B, press Save →
  `updateHolding(B.id, <A's holding id>, …)` (`286`) finds no matching holding
  (`portfolios.ts:164-177`), so nothing is written — and `290-291` clears the error and resets
  the form, so the UI reads as a successful save. Silent loss of the user's edit.
- **COD-portfolio-7** (medium) — `addPosition` / `updatePosition` / `deletePosition` / `refresh`
  (`portfolios.ts:209-276`, 68 LOC) have **no production importer**; `host-actions.ts:43` imports
  only `usePortfoliosStore`, `AssetClass`, `Holding` and calls `addHolding` directly at `1342`.
  The comment at `210-212` names a consumer that does not exist, and `portfolios.test.ts` gives
  the block green coverage.
- **COD-portfolio-8** (medium) — validation lives in the form, not the store. `normalizeHolding`
  (`portfolios.ts:69-89`) accepts negative `quantity` and negative `costBasis` and coerces
  non-finite to `0` (`84-85`). `setAll` (`186-206`) is the workspace-restore path and runs the
  same normalizer, so a hand-edited or partially-written blob restores a `quantity: 0` holding
  that counts in `positionCount` and is published to the agent (`PortfolioPanel.tsx:212-223`).
  The sidecar model *does* validate (`models/portfolio.py:36-39`, `gt=0` / `ge=0`) — on the dead
  path.
- **COD-portfolio-9** (medium) — quotes are fetched once per holding-set change and never again
  (`PortfolioPanel.tsx:142-164`, deps `[quotesKey, quotesNonce]`), and no as-of timestamp is
  rendered. `WatchlistPanel.tsx:219-224` polls on an interval. A portfolio panel left open across
  a session presents a stale price as live P&L.
- **COD-portfolio-10** (medium) — `deletePortfolio` (`PortfolioPanel.tsx:607-616` →
  `portfolios.ts:136-146`) destroys every hand-entered holding on one unconfirmed click, and the
  workspace autosave persists it. No confirm, no undo. It is the only irreversible destruction of
  manually entered data in the panel; the icon sits next to Export and Rename.
- **COD-portfolio-11** (medium) — the cost-basis unit is stated only to the model.
  `metrics.ts:94` multiplies `cost_basis` by `quantity` (per-share); the catalog tells the agent
  "Per-share cost in the listing currency" (`catalog.py:1350`); the human sees a form label
  "Cost basis" with no placeholder (`PortfolioPanel.tsx:647-654`), a column header "Cost"
  (`353`), and an empty-state hint that says nothing about it (`818`). Entering total cost —
  a common reading — makes every P&L wrong by a factor of quantity.
- **COD-portfolio-12** (low) — `metrics.ts` computes on the sidecar's snake_case `Position`
  although no sidecar position ever reaches it; `PortfolioPanel.tsx:124-136` adapts with
  `id: i` and the stated reason "keeps metrics.ts + its tests untouched" (`121-123`). The
  index-order join at `314-317` is the downstream cost.
- **COD-portfolio-13** (low) — `pnlTone` (`PortfolioPanel.tsx:43-45`) is used at `742` and `748`,
  and the identical ternary is re-inlined at `391-393`.
- **COD-portfolio-14** (low) — `updateHolding`'s interface comment says "Patch an existing
  holding" (`portfolios.ts:105`) but it replaces; absent numerics become `0` (`84-85`).
  `updatePosition`'s doc (`241-248`) warns about exactly this hazard. Types prevent it today.
- **COD-portfolio-15** (low) — `concentration` (`metrics.ts:150`) is derived from cross-currency
  weights and returned on `PortfolioSummary` with no flag; only the panel knows to withhold it
  (`756`). The field's own doc (`metrics.ts:70-71`) does not carry the caveat its neighbours
  `totalMarketValue` / `totalPnl` do (`54-62`).

---

## Persona walkthrough

**Tactical Tornado.** The tornado's fingerprints are on the *seam*, not the files. Faced with
"the panel needs holdings and the agent needs to write them", it kept `portfolio_db.py` (already
written, tests green) and added `src/store/portfolios.ts` (what the panel actually needed), then
bridged them with `syncPositionToSidecar` (`host-actions.ts:1281-1310`) marked "best-effort" —
a phrase that discharges the obligation to check whether it works. It does not
(COD-portfolio-2). The same move appears at `api.ts:27-32`: catching to `null` is the fastest way
to make the panel stop throwing, and it silently killed the error surface three files away
(COD-portfolio-4). And at `PortfolioPanel.tsx:121-123`: adapting `Holding`→`Position` is faster
than updating `metrics.test.ts`, so the test suite now dictates the production data shape.
Left alone, the next increment grows the bridge — a reconciler, an id-mapping table, a
"which store wins" flag — instead of deleting one side.

**Strategic Thinker.** The redesign is a deletion, not an addition. The store is already the
truth every surface reads; make that the *only* statement in the tree. Cut
`routers/portfolio.py`, `services/portfolio_db.py`, `models/portfolio.py`,
`host-actions.ts:1254-1317` and `sidecar/tests/test_portfolio.py` (~520 LOC), which resolves
COD-portfolio-2, -3 and half of -12 at once and removes three false docstrings. Then move the two
things that belong *below* the UI down into it: teach `normalizeHolding` (`portfolios.ts:69-89`)
the validation that currently lives in the form (`PortfolioPanel.tsx:266-277`), so the
workspace-restore path and the agent path inherit it (COD-portfolio-8); and give
`fetchPositionQuotes` (`api.ts:35-45`) a `failed` count so the panel's existing banner can fire
(COD-portfolio-4). Finally, make `metrics.ts` compute on `Holding` directly and update its tests —
one edit that removes the adapter, the `id: i`, and the index-order join together. The subsystem
ends smaller than it started, with one truth, one validator, and an error path that can actually
report.

## Questions worth asking

- If nothing has ever read `GET /portfolio/positions`, what is the ledger *for*? If the answer is
  "a future reconciliation feature", note that it currently stores data that is wrong by
  construction (COD-portfolio-2) — the feature would inherit corruption, not a head start.
- `broker_portfolio` and the panel's `get_portfolio` snapshot are two different portfolios with
  one word between them. Does the agent's prompt make a model reliably distinguish "your Zerodha
  account" from "your paper portfolio"? A provenance field (COD-portfolio-1) fixes half of that;
  the naming fixes the other half.
- Should a paper-mode adapter return ₹10,00,000 at all, rather than raising "not connected"? The
  fabricated default is what turns a missing label into wrong money.
