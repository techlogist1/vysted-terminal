# R9 Track B — Loop integrity: report

Branch: `worktree-agent-r9-loop` (from 004 HEAD). Partition held: only
`sidecar/services/research/`, `sidecar/services/search/extract.py`, their tests,
one cached fixture, and this report. Version untouched at 0.8.0.

## What shipped (per workstream)

### B1 — Filing extraction robustness (V10)

Root cause verified live before coding: the SAKSOFT Q4 FY26 board-outcome PDF
(2.49 MB, 27pp) carries its results tables as raster scans — re-probed the real
filing from this worktree and confirmed the diagnosis page-by-page (15 zero-text
pages incl. p10 consolidated P&L and p11 standalone key info; the same-evening
earnings presentation is fully digital, 18pp, every figure verbatim). The real
per-page text is cached as `sidecar/tests/fixtures/saksoft_outcome_pages.json`
(29 KB; tests rebuild a structurally equivalent PDF offline — no binary in the
repo, no network in tests).

`services/search/extract.py`:

- **Per-page honesty signal** — `pages_empty` (pages under a 16-char floor; the
  10-char "ANNEXURE-A" separator counts, honestly) on every PDF extraction
  result, ok and miss paths. `visit_for_research` APPENDS the one-line
  `scanned_pages_note(empty, total)` to a partial-text excerpt and RETURNS it
  as the visit text for a fully image-only filing — the researcher prompt now
  reads "16 of 27 pages have no extractable text — financial tables are likely
  scanned images … prefer a digital companion filing" instead of asserting
  "not parsed".
- **Indian results caption grammar** in the page-selection keywords:
  `standalone`, `consolidated`, `quarter ended`, `year ended`, `net sales`
  (whitespace-normalized phrase matching, so pypdf's line breaks in table
  captions don't defeat the phrases).
- **pypdf layout-mode retry** on selected pages, kept only when layout yields
  strictly more WELL-FORMED financial numbers than plain extraction (the
  fused-cell shape `Revenue24,884.5023,998.71`); capped at 8 pages, failures
  keep plain.
- **Score-order page assembly when truncation is inevitable** — letterhead can
  no longer starve the results table out of the excerpt; document order is
  kept when everything fits (diagnosis item 5).
- `is_digit_sparse()` calibrated on the real filing (cover letters/notes run
  3–7% digits; genuine results-table text 25–45%; threshold 10%, 200-char
  minimum).

`services/research/deep.py` + `disclosures.py`:

- **Digital-twin fallback visit** — `_run_researcher` makes ONE bounded extra
  visit of `disclosure_rows[1]` when the primary disclosure visit missed,
  carries the scanned note, or is digit-sparse.
- **Band-0.5 row mix** — `announcement_rows` ranks the results filing first
  (band 0), its digital twin (`investor presentation|earnings presentation|
press release|analyst/results presentation`) at band 0.5, the rest at band 1
  (feed order within bands) — so `rows[1]` is the digital twin, not a fourth
  scanned outcome. Simplification noted: banding is headline-shape only (the
  feed gives no reliable same-window date pairing); newest-first within band
  approximates "same results window".
- **NO OCR** (diagnosis item 4 — binary budget + cross-platform).

### B2 — Last-mile relevance (V11)

`relevance.py`: entity matching now requires a STRONG signal in the title,
host, or URL — the symbol (word-bounded / host substring / bounded path-query
hit), a brand name token (a new sector-descriptor vocabulary excludes "mobile",
"industries", "india" …), or ALL distinctive name tokens together in the title.
A snippet-only passing mention (market roundups, peer lists, another company's
DRHP — exactly the Coromandel/Tea Post→SAKSOFT and Nestle/Zomato→ROUTE shapes)
scores at most `WEAK_MATCH_CEILING = 0.25`, strictly below `MATCH_FLOOR = 0.34`
— an off-entity source can never become a source or coverage. Tiered floors
kept: `verified_symbol` disclosure rows still pass at 1.0, the relaxed
no-target query-token path is unchanged, and micro-caps with own-host/titled
rows keep their evidence (pinned by test). All R8 relevance fixtures replayed
green; new fixtures added from the operator's failing runs (Coromandel
roundup, Tea Post DRHP, Nestle/Zomato generic-token cluster).

### B3 — Assembly completeness (V12)

- **CK-Pro structured progress state** — the iter distill step demands four
  fixed sections (`Facts established` with per-fact `[n]` markers, `Open
questions`, `Dead ends` with do-not-retry detail, `Planned next`); the
  planner is instructed never to re-plan a dead end. Render/synthesis never
  parse the sections structurally, so a weak model that ignores the contract
  still ships (the R8 guarantees hold).
- **Raw-evidence store** — researchers return their visited pages
  (`(url, full_text)`); `_Findings.evidence` holds them per run, ONE shared
  store across the heavy panel; `citecheck.ensure_citation_integrity` audits
  claims against the cited source's FULL extracted text (capped 1200 chars,
  shown once per source) instead of title+excerpt. The unsupported-claim-rate
  measure is a live metric for the lead's post-merge runs.
- **WebWeaver-lite (heavy/ultra only)** — heavy synthesis emits an outline
  first (`<title> :: [n] [m]` lines, ≤5 sections, ≤8 sources each), then
  writes sections IN PARALLEL against only their bound sources + raw evidence
  excerpts; skipped under a thin wall (<25s) or breached budget; a garbled
  outline falls back to the proven single-call synthesist. The dev step names
  the mode (`webweaver outline` / `single-call`).
- **Cross-source numeric assembly** — distill keeps metric COMPONENTS as
  separate facts plus an assembled-total fact citing all components; the iter,
  deep, heavy-synthesist, and section-writer prompts all carry the "ASSEMBLE
  ACROSS SOURCES … interim dividends plus a final dividend" directive (the
  ₹11/share ROUTE gate shape, pinned at the prompt-contract level in tests;
  the live gate is the lead's post-merge ROUTE run).

### B4 — Cross-verification rule (gate 5)

Team A's interface landed on `origin/worktree-agent-r9-tiers` mid-track and B4
is built against it EXACTLY: `verify.cross_check(..., native_search=...)`
consumes a channel callable `await native_search(prompt) -> {"ok", "text",
"citations"}` — A's `native_search_oneshot` with provider/model/key closed
over; A's `native_search_available(...)` is the detection gate and A's wiring
decides when to pass the callable (tier_b never does). Behavior:

- both channels carry evidence + AGREE → "AGREE (corroborated across
  channels)" in the section, `corroborated: true` on the check row;
- one channel only → still cross-checked, flagged
  `single-channel (searxng|native) — not corroborated by the other channel`;
- channels stating different figures → DISAGREE, surfaced in section + note
  (the verdict prompt carries an explicit channel-conflict rule);
- independence floor: distinct domains + the native grounded completion as ONE
  extra independent retrieval path (one-domain SearXNG + native clears
  `min_domains=2` honestly; both dark → UNVERIFIED, no LLM call);
- `native_search=None` keeps the single-lane wire shape byte-compatible (no
  `channels`/`corroborated` keys — pinned), channel crash degrades to single
  lane, cost bounded to one pass, one native call per claim (≤5).

**Integration note for the lead:** the only wiring left is Team A's
`deep_research._run_loop` passing
`native_search=partial(native_search_oneshot, provider, model, key,
model_web_search=...)` into `cross_check` when `native_search_available(...)`
— signature-compatible today; nothing on my side blocks the merge order.

### B5 — Depth honesty + V14 (ULTRA wall)

`depth.py` untouched — profiles deterministic, the composer slider stays the
floor (`test_composer_slider_is_the_floor_model_may_escalate` green). V14
decision: the ULTRA wall stays 240s with the honest skip. Rationale: no live
runs are possible in this worktree, so there is no timing evidence to justify
a rebalance; the R9 changes CUT ultra's synthesis wall pressure in the common
case (WebWeaver sections write in parallel; the weave is skipped under a thin
wall) and the cross-verify adds at most one bounded native call window. If the
lead's live gates still show honest skips on slow chat models, the one-knob
change is `PROFILES[ultra].wall_seconds` — deliberately left to live evidence.

## Verification

- Full pytest in-worktree: **2024 passed, 1 skipped** (baseline at branch:
  1982 passed, 1 skipped — **+42 new pinned tests**, zero regressions). One
  pre-existing perf test (`test_autocomplete_stays_keystroke_fast_over_full_
masters`, outside this partition) flaked once under concurrent shell load
  and passes in isolation and on the clean rerun.
- `ruff check .` and `ruff format --check .` clean over the sidecar (365 files).
- The track's test files (`test_search_extract`, `test_research_r9_regressions`
  [16 new tests], `test_research_relevance`, `test_research_citecheck`,
  `test_research_verify`, `test_research_disclosures`,
  `test_research_r8_regressions`, `test_research_iter`, `test_research_deep`,
  `test_research_depth`): **164 passed** — all offline, R8 regression payloads
  replayed green.
- Live SAKSOFT/ROUTE deep-run gates: cannot run in the worktree (no network
  research stack) — the lead drives them post-merge; every mechanical
  precondition is pinned by fixture here.

## Files touched

- `sidecar/services/search/extract.py`
- `sidecar/services/research/{deep,iter,relevance,citecheck,verify,disclosures}.py`
- `sidecar/tests/{test_search_extract,test_research_r8_regressions,
test_research_r9_regressions,test_research_relevance,test_research_citecheck,
test_research_verify,test_research_disclosures}.py`
  (r8 file untouched except none; r9 file is new)
- `sidecar/tests/fixtures/saksoft_outcome_pages.json` (new, real-filing text)
- `docs/redesign/R9_TRACK_LOOP_REPORT.md` (this file)
