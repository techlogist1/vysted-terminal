# CRITIQUE — `market-data-providers-3` (data-surface panels + stores, 3/3)

Subsystem entry: `docs/redesign/verification/r15/census/CODE_PARTITION.json` → `market-data-providers-3`.
24 files, ~5.9k LOC. Slice read in full (production files; tests read only where they
settled a claim).

**Skill status.** `aposd-critique` invoked and followed. **Assessment independence:
degraded (sequential, single worker)** — COMMON.md forbids me spawning sub-workers, so
Assessment A (Strategic Thinker) and Assessment B (Tactical Tornado) were run one after
the other in the same head rather than in isolation. Vocabulary and the file:line evidence
gate were applied unchanged. Snapshot persistence skipped (census run writes here, not to
`.aposd/`).

---

## Tactical Tornado verdict

**Risk: medium-high.** This is not slop — the panels are unusually well-commented, every
one has designed empty/loading/error states, and the error-degradation shapes
(`Promise.allSettled` fan-out, `SidecarError` detail preservation, sequence-guarded
narrative) are the work of someone who had been burned. The tornado damage is narrower and
more specific: **the module's own contracts are half-consumed.** `currency` rides
`EarningsEvent`, `PriceTargetEntry`, `IndividualAnalystForecast` and is read by *zero*
production lines in those two modules; `searchCompanies` is a fully-built store action with
no UI; `SortKey."analysts"` is a branch nothing can reach; an error banner in
`AnalystRatingsPanel` guards a state the store cannot produce. Alongside that: the
`void x; // subscribe` statements in the SEC panels are a hand-maintained invariant where
the structure could hold it, and three copies of `fmtDate` plus two of
`RATING_LABEL`/`RATING_COLOR` are duplicated truth already waiting to drift.

Most damning single pattern: `src/store/sec.ts:274-297` — three functions named `select*`
that are not selectors. They call `useSecStore.getState()` at render time, so every caller
must separately subscribe with a no-op statement (`SecFilingsPanel.tsx:75`,
`InsiderTradingTable.tsx:107`). The line that holds the panel's reactivity reads like dead
code.

---

## Design principles score

| #   | Principle                             | Verdict     | Evidence (file:line)                                                                                                                                                       |
| --- | ------------------------------------- | ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Strategic over tactical               | at-risk     | `equity-overview/api.ts:101-125` fan-out + per-leg degrade is strategic; `EarningsCalendarPanel.tsx:216-447` hand-rolls a table the slice already has (`DataTable`) — tactical |
| 2   | Deep modules                          | at-risk     | `store/earnings.ts:100-182` — three near-identical 25-line accessors whose whole interface is "GET this URL, cache by symbol"; interface ≈ implementation                     |
| 3   | Information hiding                    | **violate** | `store/sec.ts:274-297` `select*` read `getState()`; callers must hand-subscribe (`SecFilingsPanel.tsx:75`, `InsiderTradingTable.tsx:107`) — the store's reactivity leaks out   |
| 4   | General- over special-purpose         | pass        | `components/DataTable` consumed by 6 of 7 tables in the slice; `EpsEstimateGrid.tsx:58` and `FilingsListTable.tsx:123` both fit it without special cases                       |
| 5   | Different layer → different abstraction | at-risk   | `EquityOverviewPanel.tsx` (1119 ln) holds formatters, field catalogue, 6 sub-components, autocomplete, panel-context and the command channel at one layer                      |
| 6   | Pull complexity downward              | **violate** | `store/sec.ts` keeps status/error GLOBAL while data is keyed (`:77-91`); each panel re-derives which error belongs to which key                                                |
| 7   | Better together / apart               | pass        | `store/analyst-ratings.ts` + `AnalystRatingsPanel` split is right; `EarningsSurpriseChart`/`EpsEstimateGrid` are correctly separate leaf components                            |
| 8   | Define errors out of existence        | at-risk     | `store/sec.ts:241-243` `catch { }` throws away the reason (every sibling action keeps `err.message`) — a failure becomes an indistinguishable empty                            |
| 9   | Design it twice                       | at-risk     | `PriceTargetTimeline.tsx:93-111` picks "unweighted daily mean of whoever re-rated" with no alternative considered and no honest label                                          |
| 10  | Comments say what code cannot         | pass        | `EquityOverviewPanel.tsx:599-603`, `:663-666`, `store/sec.ts:17-21` explain *why*, not *what* — genuinely above average                                                        |
| 11  | Comments written first / kept true    | at-risk     | `EarningsSurpriseChart.tsx:102` "Sort newest-first → reverse for chart" sits over a plain ascending sort with no reverse                                                        |
| 12  | Naming                                | at-risk     | `select*` (`store/sec.ts:274`) are not selectors; `const AMBER = ACCENT_CORAL` (`PriceTargetTimeline.tsx:41`) names a colour it is not                                          |
| 13  | Consistency                           | **violate** | Freshness: `EquityOverviewPanel.tsx:286-314` badges provider+as-of; earnings/analyst/SEC show none. Table: 6 use `DataTable`, `EarningsCalendarPanel` hand-rolls one            |
| 14  | Obviousness                           | **violate** | `void filingsByIdentifier; // subscribe` (`SecFilingsPanel.tsx:75`) — deleting an apparently-dead statement silently freezes the panel                                          |
| 15  | Avoid temporal decomposition          | pass        | Stores are keyed by identity, not by load order; `loadFilings`/`loadInsider`/`loadFilingDetail` are independent entry points                                                    |
| 16  | No pass-through methods/variables     | at-risk     | `store/sec.ts:320` `_internal_getSidecarBaseUrl` is a re-export for tests only; `InsiderTradingTable.tsx:107` `void byIdentifier` is a pass-through subscription                |
| 17  | Exception / failure handling          | at-risk     | `NewsFeedPanel.tsx:230-239` retries 12× without inspecting `SidecarError.status`; `equity-overview/api.ts:101` has no abort or timeout                                          |
| 18  | Clean modification (no special-casing)| at-risk     | `InsiderTradingTable.tsx:110-113` special-cases a shape "a mocked `sidecarGet`" could return — production code bent to satisfy a test                                           |

**Summary: 4 pass, 10 at risk, 4 violate — 4/18 pass.**

---

## What's working

1. **Per-leg failure degradation is real, not decorative.** `equity-overview/api.ts:101-125`
   fans out six calls with `Promise.allSettled`, returns `null` per failed section, and
   only reports `allFailed` when every leg rejects — and `rejectionReason` (`:89-98`)
   preserves the sidecar's own detail so `EquityOverviewPanel.tsx:1048` can explain *why*
   fundamentals are missing rather than showing a bare blank. Cuts change amplification:
   adding a seventh section needs no new error plumbing.
2. **The R13 honest-absence cell.** `EquityOverviewPanel.tsx:190-240` renders a null field
   as an em-dash **plus its recorded reason** (`withheld — implausible` / `not published`)
   with the provider + as-of in the title. This is the single best thing in the slice: it
   removes an unknown-unknown (was the value missing, withheld, or zero?) at the structural
   level instead of by convention.
3. **Loading states are table-shaped, not prose.** `AnalystRatingsPanel.tsx:34-47`,
   `SecFilingsPanel.tsx:193-205`, `FilingViewer.tsx:128-152`, `EarningsCalendarPanel.tsx:216-256`
   all pulse the real row geometry, so the fetch window never gets mistaken for an empty
   result — and `AnalystRatingsPanel.tsx:94` gates the child empty-states behind an explicit
   `tabLoading` so "loading" is never rendered as "no data".

---

## Priority issues

### [P0] The earnings + analyst surfaces discard `currency`, and the calendar sorts mixed-currency EPS as one column

- **Principle:** Information hiding / consistency (the contract carries the unit; the view drops it)
- **Complexity symptom:** unknown unknowns — the reader cannot tell what unit a number is in
- **Evidence:** `EarningsCalendarPanel.tsx:34-37` (`fmt` → `formatPrice`, no currency), `:51-66`
  (`sortValue` returns the raw float for `consensus`/`dispersion`), `:360-365` (rendered);
  `EpsEstimateGrid.tsx:25-31`; `EarningsSurpriseChart.tsx:83` (`title: "Surprise (EPS $)"` —
  a hardcoded `$`); `IndividualAnalystTable.tsx:69`; `PriceTargetTimeline.tsx:96-108`
  (`bucket.sum += entry.target_to`, currency ignored). Contracts carry it:
  `types/earnings.ts` `EarningsEvent.currency`, `types/analyst.ts` `PriceTargetEntry.currency`,
  `IndividualAnalystForecast.currency`. Provider sets it honestly:
  `sidecar/services/earnings_provider.py:270` `currency=str(payload.get("currency") or "USD")`.
  `grep -rn currency src/modules/earnings src/modules/analyst-ratings` → **production hits: zero**
  (test fixtures only).
- **Why it matters:** the Earnings Calendar is watchlist-filtered, and the product target is
  India **and** global. A ₹-denominated NSE consensus EPS renders as a bare `42.10` in the same
  column as a `$2.35`, and clicking "Consensus EPS" sorts them against each other by raw
  magnitude — a false ranking of money. The one place in the slice that got this right
  (`EquityOverviewPanel.tsx:54-59`, "the live D10 defect put ₹ on AAPL's market cap") proves the
  team knows the rule; three modules over it was never applied.
- **Fix:** thread the row's `currency` into `fmt` / `eps` / `revenue` / the target column
  (`formatMoney(value, currency)` already exists in `@/lib/format`); take the currency for the
  chart series title from the data instead of the literal `$`; disable (or group) the
  consensus/dispersion sort when the visible rows span more than one currency.

### [P1] Analyst + earnings caches are permanent for the session — no TTL, no invalidation, no refresh control, no as-of

- **Principle:** define errors out of existence (staleness is silently indistinguishable from freshness); consistency
- **Complexity symptom:** unknown unknowns
- **Evidence:** `store/analyst-ratings.ts:51-54`, `:79-82`, `:107-110` — `const cached = get().histories[normalized]; if (cached) return cached;` with no timestamp;
  identically `store/earnings.ts:105-108`, `:133-136`, `:161-164`.
  `AnalystRatingsPanel.tsx:96-102` — `retryTab()` calls the same cached accessor, so it cannot
  re-fetch; `:71-77` — `handleSubmit` sets the *same* string, React bails out of the update and
  the effect at `:64-69` never re-runs. There is therefore **no path at all** to refresh analyst
  data once loaded. No `as_of` is rendered anywhere in either module.
- **Why it matters:** open AAPL ratings at 09:00; a firm downgrades at 11:00; the panel shows the
  09:00 call until the app restarts, with nothing on screen saying when it was fetched. The
  sibling `EquityOverviewPanel.tsx:286-314` badges provider **and** freshness/as-of — so this
  is inconsistent inside one subsystem, on the axis the product calls its moat. Secondary:
  every cache is an unbounded `Record` — `store/sec.ts:82` `filingDetailByAccession` holds whole
  parsed filings and is never evicted.
- **Fix:** store `{ payload, fetchedAt }`, treat older-than-N-minutes as a miss, and give each
  panel an explicit Refresh that bypasses the cache. The in-repo precedent is one hook:
  `NewsFeedPanel.tsx:209-257` (`refreshNonce`).

### [P1] `EquityOverviewPanel.doLoad` has no sequence guard, while its own sibling `fetchNarrative` does

- **Principle:** consistency; pull complexity downward
- **Complexity symptom:** unknown unknowns (a late response silently wins)
- **Evidence:** `EquityOverviewPanel.tsx:740-769` — `doLoad` awaits `loadEquityOverview` and
  calls `setData(overview)` unconditionally, no seq ref. Three functions above,
  `:707-734` `fetchNarrative` implements exactly the guard (`narrativeSeqRef`), and `:600-603`
  comments the hazard. `:821-831` — the external equity-command effect is **not** gated on
  `loading`, so a screener row / brief `$CASHTAG` chip / ⌘K result fired mid-load starts a
  second `doLoad`; whichever `loadEquityOverview` settles LAST wins `setData`, and whichever
  settles FIRST runs `finally { setLoading(false) }` and kills the spinner. `api.ts:101` has no
  `AbortController` and no timeout, so a hung leg is unbounded.
- **Why it matters:** the panel can end up showing company A's fundamentals after the user
  asked for B. The manual path is guarded (`disabled={loading}` at `:922` blocks the button and
  implicit Enter-submit); the command-bus path is not, and that is the path CLAUDE.md documents
  as always-consumed.
- **Fix:** copy the `seqRef` pattern already in the file into `doLoad` (≈4 lines), and gate the
  command effect on `!loading` or let the seq guard handle it.

### [P1] `select*` in the SEC store are not selectors — reactivity is held by a `void x;` statement

- **Principle:** information hiding; obviousness
- **Complexity symptom:** unknown unknowns / change amplification
- **Evidence:** `store/sec.ts:274-297` — `selectFilings`, `selectFilingDetail`, `selectInsider`
  each call `useSecStore.getState()` rather than taking state. Callers compensate:
  `SecFilingsPanel.tsx:74-77` `void filingsByIdentifier; // subscribe` and
  `InsiderTradingTable.tsx:106-115` `void byIdentifier; // hooked above for subscription`.
  The file's own header (`:17-21`) documents the frozen-empty stable-identity pattern that a
  real selector would need — then the functions sidestep being selectors.
- **Why it matters:** the panel's entire reactivity rests on a statement that looks like dead
  code. A `no-unused-expressions` lint pass, a tidy-up commit, or the next reader deleting the
  "pointless" line freezes the table at its first render — silently, with no error, no failing
  type-check, and a test suite that mounts fresh components each time and so would not catch it.
- **Fix:** delete the three module-level functions and subscribe directly, one line per call
  site: `useSecStore((s) => s.insiderByIdentifier[insiderKey(id, form)] ?? EMPTY_INSIDER)`.
  The frozen empties at `:52-65` already give the stable identity this needs.

### [P2] Failure handling is unconditional where the error object already says it is hopeless

- **Principle:** exception handling; pull complexity downward
- **Complexity symptom:** cognitive load (a 50-second wait that explains nothing)
- **Evidence:** `NewsFeedPanel.tsx:230-239` — `.catch((error: unknown) => { ... if (n < 12) { timer = setTimeout(() => attempt(n + 1), Math.min(1000 * 2 ** n, 5000)); return; } ... })`.
  The `error` is never inspected, though `SidecarError.status` is available and is used 80 lines
  up in `errorMessage` (`:152-156`). The shared hook the Earnings and SEC panels use has the same
  unconditional shape (`lib/use-sidecar-retry.ts`, MAX_ATTEMPTS 12). Separately,
  `store/sec.ts:241-243` `catch { set({ searchResults: EMPTY_SEARCH, searchStatus: "error" }); }`
  discards the reason entirely — every other action in that file keeps `err.message`.
- **Why it matters:** a bad BYOK NewsAPI key (401) or a malformed symbol (400) will never
  succeed; the user watches a skeleton for ~50 s before the honest message appears, and the
  sidecar takes 12 pointless requests. The cold-boot case the backoff exists for is a *connection*
  failure, which is exactly the case a status check leaves untouched.
- **Fix:** `if (error instanceof SidecarError && error.status >= 400 && error.status < 500) { setState(error); return; }` before the backoff, in both the panel and the shared hook.

---

## Persona walkthrough

**Tactical Tornado.** The Tornado wrote `EarningsCalendarPanel.tsx:216-447`: needed a table,
had one (`DataTable`, used by six siblings including two files in this same module), wrote a
new one anyway — then needed a skeleton, copied the seven `<col>` widths from `:279-287` to
`:217-225` rather than hoisting them, and re-implemented the sortable header at `:453-480` and
the null glyph at `:34-37`. That is three copies of truth in one file. The Tornado also left
`SortKey."analysts"` (`:23`, `:63-64`) wired to nothing, shipped `searchCompanies` +
`searchResults` + `clearSearch` (`store/sec.ts:228-248`) against a real `/sec/filings/search`
route with no component consuming any of it, and guarded a state the store cannot produce at
`AnalystRatingsPanel.tsx:155-164`. Next iteration, the Tornado grows a fourth `fmtDate` and a
third `RATING_LABEL` and the "Rating" colour scale quietly differs between the two analyst
tables.

**Strategic Thinker.** The Strategic Thinker would not start with the components. They would
notice that the three stores in this slice (`earnings.ts`, `analyst-ratings.ts`, `sec.ts`) are
the same module written three times — per-key cache, per-key error string, a `*Errors` map
holding `""` as "no error", an accessor that returns the cache without asking how old it is —
and that all three panels then re-derive freshness, retry and emptiness from that shape, each
slightly differently. Their redesign is one keyed-resource helper holding
`{ payload, fetchedAt, error }` per key, returning a discriminated
`loading | ready(payload, fetchedAt) | error(reason)`; panels render `fetchedAt` as the as-of
badge (deleting P1-freshness and P1-retry as *classes*, not as five patches), and an explicit
`refresh(key)` that bypasses the cache (deleting the dead retry). They would delete the three
`select*` functions in favour of direct subscriptions (P1-selectors), and — the one-line change
with the largest blast radius — make the row's `currency` a required argument of the money
formatters those panels call, so P0 becomes a type error rather than an omission.

---

## Minor observations

- `EarningsSurpriseChart.tsx:102` — comment says "Sort newest-first → reverse for chart"; the
  code sorts ascending with no reverse. The result is right, the comment is not.
- `PriceTargetTimeline.tsx:41` — `const AMBER = ACCENT_CORAL;` renames a token to a colour it
  isn't. `store/sec.ts:320` `_internal_getSidecarBaseUrl` is a test-only re-export in production code.
- `IndividualAnalystTable.tsx:87` — `formatPercent(x * 100).replace("+", "")` does string surgery
  on a formatter's output to strip a sign the formatter deliberately added.
- `InsiderTradingTable.tsx:110-113` defends against "a mocked `sidecarGet` that returned a generic
  `FilingsListResponse`" — production code shaped by a test's mock.
- `NewsFeedPanel.tsx:24-43` `relativeTime` returns `""` on an unparsable date, leaving a dangling
  `Reuters ·` separator at `:127-131`; ages are computed at render and never tick.
- `FilingViewer.tsx:52-58` returns a bare centred sentence for the no-accession case while every
  other empty state in the slice composes `EmptyState`.

---

## Questions to consider

1. If `currency` were a **required** parameter of the money formatters these panels call, how
   many of the P0 sites would have failed to compile instead of shipping?
2. The three stores are the same store three times. What would the panels stop needing to know
   if a keyed resource returned `{ payload, fetchedAt }` and a `refresh(key)` instead of a bare
   cached payload?
3. `searchCompanies` exists in the store and on the sidecar, but the SEC panel only accepts a
   Symbol/CIK you already know (`SecFilingsPanel.tsx:126-133`). Against the screener.in benchmark
   ("any listed company, however obscure"), is that panel's entry point the real product, or the
   half that got wired?
