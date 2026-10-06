# lows-fix-A (cluster A) — 04:12 IST, Opus 5.5, base 2dbcde70 (lows-int candidate)

One file changed: `sidecar/services/symbol_resolver.py` (+8/-1). No test edited, skipped or weakened.

## Disclosure ids (7): test_explicit_bo_pin_on_a_different_company_takes_the_bse_company_in_every_lane x5, test_bo_pin_keeps_same_company_and_bare_behaviour, test_disclosure_tools::test_class_case_deals_and_actions_gate_the_same_way_amal_bo_still_served

- Verdict: merge_defect.
- Origin: `3acd24dc fix(disclosures): R15-LEAD-116 honour an explicit .BO pin for a same-ticker different-company listing` (built on 9368c626; not in 4c6dfe8c..9368c626). Code: P3 `ff638c45 fix(resolver): autocomplete rows state their match band, no BAND_FUZZY default (R15-CODE-DATA-017)` made `band` a required arg of `_instrument_nse`.
- Cause: LEAD-116's new `pinned_other_company_bse_code` calls `_instrument_nse(bare, 1.0)` (two args); after the P3 merge every disclosure lane routed through it raised `TypeError: _instrument_nse() missing 1 required positional argument: 'band'`. Semantic conflict, textually clean.
- Action: pass `BAND_EXACT_TICKER`, the same band its sibling `dual_listed_bse_code` uses for the exact-ticker master row. Both changes kept.

## Resolver ids (2): test_current_name_beats_an_identical_former_name_kpit, test_former_name_coincidence_binds_the_current_name_holder

- Verdict: merge_defect.
- Origin: `ea2ebd50 fix(rc1): discount former-name matches so a current name wins a tie (rc1-battery-14:1)` — added on 004 inside 4c6dfe8c..9368c626, so the tests are immovable. Code: P3 `7f98480b refactor(resolver): delete the dead Resolution.needs_disambiguation surface (R15-CODE-DATA-018)`.
- Cause: P3 deleted `Resolution.needs_disambiguation` (and migrated the call sites it could see); the rc1 tests landed on 004 after P3 branched and assert `not r.needs_disambiguation`.
- Action: restored the property verbatim (delegates to `resolution_policy.decide`, the one policy, so no second decision surface) plus the `decide` import. Keeps P3's call-site migrations; reverses only the deletion half of R15-CODE-DATA-018 because a certified rc1 test pins the attribute.

## Verification

Focused ids: 9 passed in 1.06s.
Whole files + every test file importing symbol_resolver / corporate_disclosures / disclosures (42 files): 913 passed, 3 failed — the 3 are test_research_deep `test_run_researcher_drops_*` (`deep._run_researcher` gone, P1 research refactor), owned by another cluster, untouched by this change.
ruff format --check sidecar (453 files) and ruff check sidecar clean.

## Live (own sidecar, port 52391, X-Vysted-Region: IN, scratch data dir, real bundled masters)

`python main.py --port 52391 --data-dir <scratch> --cache-dir <scratch>/cache`, then `fix-A-live/run.py` (curl GET /disclosures/<lane>?symbol=<s>). Raw JSON + summary in `fix-A-live/`.

| lane | FOCUS.BO | 543312 | equal | FOCUS (NSE only, note) | AMAL.BO (NSE+BSE) | INFY.NS | HDFCBANK |
|---|---|---|---|---|---|---|---|
| announcements | 23 | 23 | True | 44 | 21 | 50 | 50 |
| results | 10 | 10 | True | 35 | 10 | 70 | 75 |
| shareholding | 12 | 12 | True | 21 | 104 | 21 | 22 |
| corporate-actions | 5 | 5 | True | 4 | 5 | 20 | 20 |
| deals | 39 | 39 | True | 11 | 18 | 219 | 120 |

AMAL.BO still merges both exchanges with the same counts as the LEAD-116 writer record; bare FOCUS NSE-only with "BSE FOCUS is a different company; only the NSE feed is served"; INFY.NS/HDFCBANK merge. (FOCUS shareholding 12 vs the writer's 13: live feed, FOCUS.BO == 543312 either way.) Sidecar stopped (pid 18866).
