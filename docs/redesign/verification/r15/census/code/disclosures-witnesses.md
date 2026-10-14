# APOSD critique — `disclosures-witnesses`

**Subsystem:** Disclosures & Witnesses (BSE XBRL, ownership) · 2,144 LOC / 9 files
**Model:** `claude-opus-5[1m]`
**Skill:** `aposd-critique` loaded and followed. **Assessment independence: degraded (sequential)** — no
sub-agent tool in this worker's toolset, so Strategic Thinker was completed and recorded before the
Tactical Tornado scan; synthesis below. **Snapshot persistence skipped** — this worker is read-only on
the repo except its two output files, so nothing was written to `.aposd/critique/`.

Files read in full: `sidecar/routers/disclosures.py`, `sidecar/services/agent_tools/disclosure_tools.py`,
`sidecar/services/corporate_disclosures.py`, `sidecar/services/earnings_quality.py`,
`sidecar/services/market_cap_witness.py`, `sidecar/services/ownership_check.py`,
`sidecar/services/research/disclosures.py`, `sidecar/services/research/range_check.py`,
`sidecar/models/announcements.py`. Consumers read for boundary claims: `services/research/semantics.py`,
`services/research/fast.py`, `services/research/relevance.py`, `services/nse_provider.py`,
`tests/test_corporate_disclosures.py`.

---

## Tactical Tornado verdict

**Risk: medium-low overall, with two tornado-shaped holes in an otherwise strategic subsystem.**

This is not tornado code. It is unusually disciplined: every module carries a wiring contract, every
`None` is justified in prose, the circularity traps (yfinance witnessing yfinance) are named and
gated. 9 red flags found, and the damning ones are not sloppiness — they are **a correct idea applied
to one path and not its sibling**:

1. **The cross-feed dedup does not work on real data** and the only test that asserts it works
   manufactures the collision (`tests/test_corporate_disclosures.py:141`). Proven below.
2. **The one honest provenance stamp the merge produces (`split_as_of`) has no production reader** —
   the downstream witness re-labels a BSE-sourced figure with the NSE quarter.
3. Five copies of `is_applicable`, two of `is_india_target`, two of `_row_value`, three of
   `_is_blocked`/`_is_rate_limited` inside the witness family — the family was written five times, never
   once.

---

## Design principles score

**11 pass · 5 at risk · 2 violate (11/18 pass)**

| # | Principle | Grade | Evidence (file:line) | Consequence |
|---|---|---|---|---|
| 1 | Strategic over tactical | pass | `market_cap_witness.py:1-37` — the module exists solely to break a circular check nobody was forced to notice; `range_check.py:58-70` `_EXCHANGE_DIRECT_PROVIDERS` declines rather than compute from yfinance | Investment in the non-obvious case; no change amplification found in the witness contracts |
| 2 | Deep modules | pass | `corporate_disclosures.get_shareholding` (`:366-416`) — 50 lines of interface hiding two exchange lanes, an XBRL merge, quarter alignment and lane-failure policy behind `(symbol) -> ShareholdingResponse` | Callers (`ownership_check.py:122`, `disclosure_tools.py:74`, `routers/disclosures.py:109`) know nothing of NSE vs BSE |
| 3 | Information hiding | pass | `disclosure_tools.py:33-65` and `routers/disclosures.py:44-71` both consume the service without touching `curl_cffi`, scrip codes or XBRL | Exchange mechanics stay in one file |
| 4 | Information leakage | **violate** | `is_applicable` byte-identical in `market_cap_witness.py:98-107`, `ownership_check.py:94-104`, `research/range_check.py:121-131` (+ `dividend_actions.py:63`, `earnings_quality.py:123`); `is_india_target` duplicated `research/disclosures.py:101-107` vs `research/relevance.py:374-378`; `_is_blocked` `ownership_check.py:107-115` == `range_check.py:179-182`; `_row_value` `earnings_quality.py:134-155` == `growth_check.py:85` | "What counts as an Indian listing" and "what counts as a block" are each design decisions held in 3-5 files. Add MCX, or add HTTP 503 to the block set, and the witnesses silently disagree with each other |
| 5 | General-purpose deeper | at risk | `research/disclosures.py:50-74` `_results_band` is a general ranker, but `gather_floor:169` calls `announcement_rows` without `sub_question`, so the general mechanism is bypassed on the path that most needs it | The floor's 5 citable rows are the 5 newest attachments — procedural intimations, the exact R8 failure the bands exist to fix |
| 6 | Different layer, different abstraction | at risk | Caching lives only in the router (`routers/disclosures.py:39-41, 58, 70`); the agent-tool path (`disclosure_tools.py:50`) and the research floor (`research/iter.py:351,924`) hit the NSE cookie dance uncached | The router docstring (`:9-11`) justifies the 15-min TTL as NSE-throttle protection; the throttle-heaviest caller has none |
| 7 | Pull complexity downward | at risk | `ownership_check._fetch_latest:126-132` flattens `ShareholdingPattern` by hand and drops `split_source`/`split_as_of`; `semantics.py:555-559` then rebuilds a basis string | The provenance the service worked to compute is re-derived (wrongly) one layer up |
| 8 | Better together / apart | pass | `earnings_quality.compute_earnings_quality:158-207` is split from the fetch (`:233-254`) purely so the arithmetic is unit-testable on fixture frames; same shape in `range_check.compute_range:142-176` | Pure/impure seam is deliberate and consistent |
| 9 | Define errors out of existence | pass | `market_cap_witness.get_market_cap_witness:140-153`, `range_check.get_52w_range:195-230`, `ownership_check.get_exchange_ownership:135-156` all return `None` instead of raising into research; `corporate_disclosures.get_announcements:303-307` refuses to return a silently-empty feed | A witness can never break a brief; an empty feed can never masquerade as "no news" |
| 10 | Design it twice | pass | `corporate_disclosures.py:74-80` + `models/announcements.py:104-119` — the "public includes institutions" trap was clearly considered twice and answered with a `public_basis` label plus a separate non-institutional field rather than a silent redefinition | Second-order correctness that a first draft does not produce |
| 11 | Comments describe non-obvious | pass | `range_check.py:58-70` explains *why* a yfinance-served series is disqualified (self-witnessing + adjusted-vs-unadjusted false positives) — unrecoverable from the code | Highest-value comments in the subsystem |
| 12 | Comments first | at risk | `disclosure_tools.py:85-88` ships a stale doctrine **in the payload**: "the FII/DII split lives in each quarter's linked xbrl_url filing" — false since the BSE merge (`corporate_disclosures.py:499-543`) populates `fii_percent`/`dii_percent` in that same payload | The agent reads the note as ground truth and can tell a user the split is unavailable while the numbers sit beside it |
| 13 | Choosing names | pass | `split_source` / `split_as_of` / `public_non_institutional_percent` / `public_basis` (`models/announcements.py:114-138`) each name the exact distinction they carry | Names do the work a comment would otherwise have to |
| 14 | Modifying existing code | **violate** | `corporate_disclosures.py:514-519` catches broad `Exception` around `_bse_shareholding` with a comment naming the exact hazard ("an unexpected KeyError from bse_provider"), while the lane loop 115 lines earlier (`:399`) calls the same function catching only `ProviderError`; same asymmetry in `get_announcements:300` | The hazard the author diagnosed is guarded on the enrichment path and unguarded on the primary path — a `bse_provider` `KeyError` 500s `/disclosures/shareholding` and kills a feed the other lane could have served |
| 15 | Consistency | at risk | Error posture differs per consumer of the same service: router catches `ProviderError` only (`routers/disclosures.py:68,89,110`), agent tool catches `ProviderError` + `Exception` (`disclosure_tools.py:53-56`), witnesses catch everything (`ownership_check.py:149`) | A reader cannot predict what a `corporate_disclosures` failure does without knowing the caller |
| 16 | Code should be obvious | pass | `corporate_disclosures.py:295` `# NSE first — it wins a cross-feed dedup collision`; `range_check.py:219-229` names the guard inline | Intent is legible at the point of decision (though see F-1: the dedup comment states a property the code does not have) |
| 17 | Design for the future | pass | `MCAP_WITNESS_KEY` / `OWNERSHIP_KEY` / `RANGE_KEY` / `EARNINGS_KEY` constants (`market_cap_witness.py:52`, `ownership_check.py:56`, `range_check.py:56`, `earnings_quality.py:57`) make the snapshot wiring renameable in one place | Cheap, correct future-proofing |
| 18 | Performance as design | pass | `should_cross_check` gates on payload presence before spending a network call (`ownership_check.py:80-91`, `range_check.py:108-118`, `earnings_quality.py:108-120`); blocking parses ride `asyncio.to_thread` | Budget discipline is designed in, not bolted on |

---

## What's working

- **The circularity guards are the best code here.** `range_check.py:219-229` declines to compute a
  52-week witness from a yfinance-served series, and `market_cap_witness._lookup:124-127` refuses any
  master row without a BSE `scrip_code`. Both are cases where computing *something* would have looked
  fine in a test and been worthless in production. Someone thought about false negatives.
- **"Absence is honest" is enforced structurally, not by convention.** Every witness entry point returns
  `None` on every failure path (`market_cap_witness.py:149-153`, `range_check.py:208-215`,
  `ownership_check.py:147-155`), and the coverage floors in `compute_range:164-165` refuse a 52-week
  claim from a 3-week series. Research cannot be broken by a witness, and a witness cannot fabricate.
- **The `public_basis` decision** (`corporate_disclosures.py:74-80`, `models/announcements.py:104-119`)
  — labelling the exchange "Public" bucket rather than silently redefining it — is a genuine
  design-it-twice outcome and is applied identically on both lanes (`:441`, `:476`).

---

## Priority findings

### [P0] F-1 — Cross-exchange dedup never fires on real feed data; the test fabricates the collision

**Principle:** 16 Obviousness / 14 Modifying existing code · **Symptom:** unknown unknowns

The NSE headline is `attchmntText` — the full disclosure body (`corporate_disclosures.py:215`). The BSE
headline is `NEWSSUB` — the short subject line (`:163`). `_dedup_key` (`:251-262`) SHA-1s the whole
normalized headline, so the same filing from both feeds hashes differently. Proven on the repo's own
fixtures (both rows are the same 2026-06-09 RELIANCE ICICI-Securities investor-meeting update):

```
NSE key: ('RELIANCE', '0136c360465b6a07', '2026-06-09')
BSE key: ('RELIANCE', '7513e4250c78084a', '2026-06-09')   COLLAPSES: False
```

The module docstring claims the feed is "deduplicated by `(symbol, headline-hash, date)`" (`:7-8`) and
`:295` comments "NSE first — it wins a cross-feed dedup collision". Only re-disseminations *within* one
feed collapse. The one test asserting otherwise builds a BSE row whose `NEWSSUB` is literally the NSE
row's `attchmntText` (`tests/test_corporate_disclosures.py:141-147`) — a shape the real API does not
produce.

**Consequence:** for every dual-listed name (i.e. most large Indian names) the merged feed is ~2x
duplicated. `limit` buys half the history it claims; `_MAX_SOURCE_ROWS = 5`
(`research/disclosures.py:43`) becomes ~2-3 distinct filings; the prompt's 12-line context
(`_CONTEXT_LIMIT`) shows ~6 distinct events.

**Smallest fix:** the BSE row *does* carry the NSE text — in `HEADLINE`, truncated to 190 chars vs NSE's
326 (verified on the fixtures; normalized 120-char prefixes match exactly). Prefer `HEADLINE` over
`NEWSSUB` in `_bse_row_to_announcement:163` and hash `normalized[:120]` in `_dedup_key:259-260`. Then
re-write the test against the two unmodified fixtures.

### [P0] F-2 — A BSE-sourced institutional holding is rendered under the NSE lane's quarter

**Principle:** 7 Pull complexity downward · **Symptom:** change amplification / wrong provenance

`_merge_bse_split` (`corporate_disclosures.py:499-543`) does the honest thing: it stamps
`split_source="BSE"` and `split_as_of=<the BSE quarter the split came from>` precisely because the
quarter may differ (`:507-509`). **No production code reads either field** — `grep` finds them only in
`models/announcements.py:133,138` and `types/data.ts:376,381`. The single downstream consumer,
`ownership_check._fetch_latest:126-132`, copies `institutions_percent` and then stamps
`as_of_quarter=latest.quarter_end` and `source=latest.source` — the **NSE** quarter and the **NSE**
lane. `semantics.py:555-559` renders that as `basis = f"{source} shareholding filing, {as_of}"` on the
fact `institutions_percent_exchange` (`:578-583`) and into the conflict payload (`:590-594`).

**Consequence:** a brief states "Institutional holding (exchange filing) — NSE shareholding filing,
2026-06-30" for a figure that is BSE's 2026-03-31 XBRL. The subsystem's stated invariant is "an honest
as-of, never silently aligned" (`:507-509`); the last hop silently aligns it. This is the one finding
where the money-relevant label shown to the user is false.

**Smallest fix:** carry the two fields through `ExchangeOwnership` (`ownership_check.py:59-77`) —
`as_of_quarter = (latest.split_as_of or latest.quarter_end).isoformat()` for the institutions figure and
`split_source` into `source` — and have `semantics._ownership_*` use them for the institutions basis.

### [P1] F-3 — The nearest-quarter split merge has no staleness ceiling

**Principle:** 9 Define errors out of existence · **Symptom:** unknown unknowns

`corporate_disclosures.py:530`: `match = min(with_split, key=lambda p: abs((p.quarter_end -
pattern.quarter_end).days))`. Unbounded. If a company stopped filing its SEBI XBRL on BSE three years
ago, every current NSE quarter is enriched with a three-year-old FII/DII split. Nothing in the function
or its callers bounds the distance. With F-2 in place, that three-year-old split is also labelled with
the current quarter.

**Smallest fix:** one guard — skip the merge when `abs(days) > ~200` (two quarters), leaving the split
`None`. Absence is already the module's honest default (`:509-510`).

### [P1] F-4 — The lane loops guard only `ProviderError`; the author already documented why that is wrong

**Principle:** 14 Modifying existing code / 15 Consistency · **Symptom:** change amplification

`corporate_disclosures.py:512-519` wraps `_bse_shareholding` in `except Exception` with the comment "a
bug/timeout deep in the BSE lane (e.g. an unexpected KeyError from bse_provider) must degrade to 'no
split enrichment', never surface as a 500". The lane loop at `:396-402` calls **the same function**
catching `ProviderError` only; `get_announcements:297-302` is identical for the NSE/BSE fetchers. The
router then converts only `ProviderError` to 502 (`routers/disclosures.py:68-69, 89-90, 110-111`), so
anything else is a 500 — which, per CLAUDE.md, surfaces in the webview as a bogus CORS error.

**Consequence:** the "one lane failing degrades honestly to a partial merge" guarantee (`:25-27`) holds
for exactly one exception type. A `TypeError`/`KeyError` in the BSE parser takes down a feed the NSE
lane could have served.

**Smallest fix:** widen both loops to `except Exception` (they already record the reason into `errors`,
so the degradation stays honest and visible).

### [P1] F-5 — The research floor bypasses the results-ranking the floor exists to provide

**Principle:** 5 General-purpose modules / 15 Consistency · **Symptom:** cognitive load

`announcement_rows(result, *, symbol, sub_question="")` ranks the actual results filing first, its
investor-presentation twin second (`research/disclosures.py:252-259`). `gather` passes `sub_question`
(`:324`). `gather_floor` does not (`:169`) — and `gather_floor` is the R13 path that exists *because*
web coverage is starving (`:127-141`), i.e. precisely when the 5 citable rows are all the user gets.

**Consequence:** the floor cites the 5 newest attachments. For an Indian listing in results season those
are procedural intimations — the exact R8 gate-1 failure documented at `:222-225`.

**Smallest fix:** `gather_floor` has no sub-question, so pass a constant: `sub_question="results"` at
`:169` (or hoist the banding to always apply when no sub-question is given).

### [P2] F-6 — The `shareholding_pattern` tool ships a stale doctrine note that contradicts its own payload

**Principle:** 12 Comments first / 4 Information leakage · **Symptom:** cognitive load

`disclosure_tools.py:85-88` returns, to the LLM, `"promoter/public/employee-trust percentages come from
the NSE master; the FII/DII split lives in each quarter's linked xbrl_url filing."` Both clauses are
false when the BSE lane served (`corporate_disclosures.py:452-486`, `source="BSE"`) or when the dual-
listed merge fired (`:499-543`, `fii_percent`/`dii_percent` populated). The truth is already in the
payload — `source`, `split_source`, `public_basis` — duplicated into English that has since drifted.

**Smallest fix:** delete the static note; the per-pattern `source`/`split_source`/`public_basis` fields
already say it, per row, correctly.

### [P2] F-7 — The witness family is five copies of one module that was never written

**Principle:** 4 Information leakage / 5 General-purpose · **Symptom:** change amplification

`is_applicable` is byte-identical in `market_cap_witness.py:98-107`, `ownership_check.py:94-104`,
`research/range_check.py:121-131` (and again in `dividend_actions.py:63`); `_is_blocked` is identical in
`ownership_check.py:107-115` and `range_check.py:179-182` (and `dividend_actions.py:75`); `_row_value`
is a self-declared copy of `growth_check._row_value` (`earnings_quality.py:134-140` says so in its
docstring); `is_india_target` exists twice (`research/disclosures.py:101-107` vs
`research/relevance.py:374-378`) and `research/fast.py:426` imports the *other* copy than
`research/disclosures.py` uses.

**Consequence:** two design decisions — "which listings are Indian" and "which errors are blocks" — are
each held in 3-5 places. The next change (a third exchange, HTTP 503, a suffix form) lands in some and
not others, and the witnesses disagree silently.

**Smallest fix:** one `services/witness.py` with `is_india_listing(symbol)` and `is_block_error(exc)`;
the five modules import it. ~20 lines deleted, no abstraction invented.

### [P2] F-8 — `provider: "nse+bse"` is stamped unconditionally on a possibly single-lane response

**Principle:** 4 Information leakage · **Symptom:** wrong provenance (boundary finding — the defect is
in `research/fast.py`, the leaked field is this subsystem's)

`AnnouncementsResponse.sources` (`models/announcements.py:52-53`) records which exchanges *actually*
served, and `errors` records which failed. `research/fast.py:437-439` ignores both and sets
`value["provider"] = "nse+bse"` whenever `ok`. A response served by NSE alone (BSE down, recorded in
`errors`) is badged as both under FR-041.

**Smallest fix:** `value["provider"] = "+".join(result.get("sources") or []) or "exchange"`.

### [P3] F-9 — Two comments describe behaviour the code does not have

**Principle:** 11 Comments describe non-obvious · **Symptom:** cognitive load

`range_check.py:93` lists `yfinance` as a possible `Range52w.source` — line 219 makes that value
unreachable. `earnings_quality.py:193-198` computes `distortion` and then may discard it via the
`return None` guard two lines later (harmless, but it reads as though the guard came first).

---

## Persona walkthrough

**Tactical Tornado.** A tornado wrote `tests/test_corporate_disclosures.py:141` — needing a
cross-exchange dedup test and finding that the real fixtures don't collide, it edited the fixture
(`NEWSSUB=duplicate_headline`) until the test passed, and shipped the module docstring's dedup claim
(`corporate_disclosures.py:7-8`) as though the feature existed. The same instinct produced the
`gather_floor:169` call that dropped an argument rather than deciding what the floor's ranking should
be, and the `disclosure_tools.py:85-88` note that restates provenance in prose where the payload already
carries it in fields. Left alone, this subsystem accretes more per-witness copies of `is_applicable` and
more English restatements of structured truth — both drift, neither fails a test.

**Strategic Thinker.** A strategist would make the *structure* hold the invariants the comments
currently hold. Three moves, in order: (1) make `split_as_of` load-bearing — thread it through
`ExchangeOwnership` (`ownership_check.py:59-77`) so an as-of cannot be re-derived incorrectly one layer
up, then the honesty stamp that already exists stops being decoration; (2) key the dedup on a normalized
prefix of the *disclosure text* both feeds actually carry (`HEADLINE` on BSE, `attchmntText` on NSE) and
delete the fixture edit, so the test and production see the same shape; (3) extract one 20-line
`services/witness.py` holding `is_india_listing` + `is_block_error`, deleting five copies. No new
abstraction, no new layer — three deletions and one thread-through.

### Two redesigns considered for F-2

*Option A (rejected):* have `semantics.py` read `split_source`/`split_as_of` off the raw pattern. Rejected
— it re-opens the flattening layer to the full `ShareholdingPattern`, pushing exchange-lane knowledge up
into the semantics layer (principle 6).
*Option B (taken):* resolve the as-of inside `_fetch_latest` (`ownership_check.py:126-132`), which
already owns the flattening, and let `semantics.py` keep consuming two scalars. Complexity moves down,
the interface does not widen.

---

## Minor observations

- `range_check.compute_range:159-160` rebuilds the window twice (`windowed`, then `windowed_ts` by
  re-scanning `stamped` with the same predicate) — one desync away from a wrong `coverage_days`.
- `routers/disclosures.py:56-71 / 79-92 / 101-113` are three verbatim copies of
  cache-read → validate → to_thread → cache-set. A TTL-policy change is a three-file-region edit.
- `earnings_quality._fetch_income_stmt:230` calls `yf.Ticker(...).income_stmt` with no timeout — the
  only network call in the subsystem without one (`_bse_get_json:96` sets 20s). It is inside
  `to_thread`, so a hang leaks a thread rather than blocking the loop, but the run's wall budget pays.
- `corporate_disclosures._BSE_ANN_WINDOW_DAYS = 30` (`:88`) silently caps the BSE lane at one month
  while NSE returns full history; a `limit=200` request gets an asymmetric merge with no note in
  `sources`/`errors`.

## Questions to consider

- If `split_as_of` has no reader, is it a feature or a comment with a type? What else in the payload is
  decoration?
- Would `get_shareholding` be a deeper module if it returned the *latest reconciled* pattern (the only
  thing every caller actually takes — `ownership_check.py:125`, and `disclosure_tools.py:79` takes 12)?
- The five witnesses share an entry-point shape (`should_cross_check` → `is_applicable` → `to_thread` →
  circuit-breaker → `None`). Is that a family that wants one `Witness` protocol, or five modules that
  merely rhyme? (The duplication in F-7 is the *predicates*, not the shape — extract those only.)

## Run notes

- Target slug: n/a — persistence deliberately skipped (read-only worker).
- Ignore list: `.aposd/critique/ignore.md` not present.
- Assessment independence: **degraded (sequential)** — no sub-agent tool available.
- Verification run: one read-only `.venv/bin/python` snippet against repo fixtures to prove F-1 (no repo
  state touched). No tests executed, no processes started.
- Temp files: none created outside the two output paths.
