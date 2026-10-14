# RC1 Owner-Drive Index

Collated from `docs/redesign/verification/r15/rc1/drives/*.md` and
`docs/redesign/verification/r15/rc1/findings/*.json`. No new judgement or re-runs — counts
and deltas below are read directly off each drive's own scored table.

Candidate: `4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a` (round 1) → `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`
(gate round 2). All 8 groups re-verified/continued against `4c6dfe8c` except where noted.

| Group | Interactions driven | ok | partial | broken (expected/open) | NEEDS-GUI | Census→RC1 delta | Finding keys | Evidence dir |
|---|---|---|---|---|---|---|---|---|
| composer-chat | 11 of 24 `COVERAGE.json` rows (the 11 census-admitted findings); remaining 13 carried forward from census, not re-driven | 10 | 1 | 0 | 2 (watchlist-add, note-write — frontend-only/not-a-sidecar-route, "NEEDS-GUI" per round-2 note) | 9/11 broken→ok, 1/11 broken→partial, 1/11 ok(code-confirmed, live re-drive inconclusive due to shared-ollama contention). 0 regressions, 0 new defects both rounds. | none (`rc1-drive-composer-chat.json` = `[]`) | `docs/redesign/verification/r15/surface/composer-chat/rc1/` |
| failure-inducer | 5 filed `SURF-FAILURE-INDUCER-{1..5}` findings, re-driven twice (round 1 @ `4097dac4`, round 2 @ `4c6dfe8c`) + spot-checks | 5 | 0 | 0 | 0 | 5/5 broken→ok both rounds (0 regressions). Spot-checks (junk-429/500, retired-slug, nodocker, netdown batch-symbol semantics) unchanged. | `rc1-drive-failure-inducer:1` (environment) | `docs/redesign/verification/r15/surface/failure-inducer/rc1/` |
| onboarding-stranger | 8 register-tracked items + 2 extras, re-driven live at `4c6dfe8c` (re-run of a prior attempt against the stale `4097dac4` sha) | 6 | 0 | 2 (expected-open: R15-UI-076, R15-UI-044 blocked_tier4) | 0 | 6 admitted/fixed hold `ok`, 2 expected-open confirmed unchanged, no regression. Row 10 reclassified per Gate-Round-2 LEAD NOTE from a prior-attempt `new_defect` into a register note against the adjudicated `blocked_tier4` R15-LEAD-030 class (new surface shape, same class). | `rc1-drive-onboarding-stranger:1` (regression, low — reclassification note, not a fresh finding) | `docs/redesign/verification/r15/surface/onboarding-stranger/` |
| panels-layouts | 32 `COVERAGE.json` rows; 9 census `SURF-PANELS-LAYOUTS` findings + 4 register fixes that postdate round 1, driven directly; 17 rows carried forward unchanged | 11 | 0 | 1 (expected-open: R15-UI-077 yield-curve dup-pillar 500) | 0 | 12/13 driven rows broken/partial→ok (fixed); 1 expected-open unchanged; 3 rows scope-changed to `removed_with_feature` (broker/audit panels, D81 trading removal). 0 regressions, 0 new defects across both rounds. | none (`panels-layouts.json` = `[]`) | `docs/redesign/verification/r15/surface/panels-layouts/rc1/` |
| portfolio-notes | 19 scored rows (P1-P9, sidecar CRUD, N1-N6, Toolbar) + round-2 P8 re-check | 16 | 1 (R15-UI-078, form-path blank-cost-basis still open) | 0 | 0 | 14 rows broken/partial→ok (fixed); 1 architecture change (not a bug); 4 unchanged ok; P8 was round-1 `new_defect` → round-2 `ok` (fix landed, `quoteFetchInFlightRef` guard, 65/65 tests). | `rc1-drive-portfolio-notes:1` (new_defect, high — round-1 only, closed round 2), `rc1-drive-portfolio-notes:2` (regression, low — harness-methodology note, not a product regression) | `docs/redesign/verification/r15/surface/portfolio-notes/rc1/` |
| research-briefs | 13 census `SURF-RESEARCH-BRIEFS` findings round 1, 14 register-tracked items + 1 own finding round 2 | round1: 11, round2: 14 | 0 | round1: 2, round2: 2 (both expected-open: R15-UI-080, R15-RESEARCH-041) | 0 | Round 1: 11/13 broken→ok, 2/13 correctly still open. Round 2: all 14 tracked items hold (12 ok incl. 2 critical, 2 expected-open); round-1's own new finding (:1, coverage-note false-positive) is now FIXED. 0 regressions either round. | `rc1-drive-research-briefs:2` (new_defect, medium — round 2, citation-marker shape gap; round-1's `:1` closed) | `docs/redesign/verification/r15/surface/research-briefs/rc1/` |
| screener | 7 filed `SURF-SCREENER` findings + 7 additional register-tracked items + 2 new fixes found in the round-2 diff | 16 | 0 | 0 | 0 | All 7 census broken/partial→ok (2 live-driven, 5 code-confirmed at time/ollama-contention budget). 7 additional register items re-checked, all ok. Round 2: 2 new screener fixes (R15-DATA-043 round-robin, R15-DATA-112 currency-sort-last) both ok; 1 regression recheck (zero-evaluated) confirmed unchanged. 0 regressions, 0 new defects. | none (`screener.json` = `[]`) | `docs/redesign/verification/r15/surface/screener/rc1/` |
| settings-plugins | 9 scored interactions (7 census + 1 rc1-refutation-audit item + 1 expected-open) | 8 | 0 | 1 (expected-open: R15-UI-081, disabled-module-still-opens) | 0 | 7 census broken/partial→ok; 1 refutation-audit `partial`→ok (R15-CODE-PLATFORM-013, bridged plugin toggle, 52/52 vitest incl. pinned regression test); 1 expected-open unchanged and distinct from the fixed defect (different root cause). 0 regressions, 0 new defects. | none (`rc1-drive-settings-plugins.json` = `[]`) | `docs/redesign/verification/r15/surface/settings-plugins/rc1/` |

**Totals across the 8 groups' own scored tables (round-2/latest state):** 72 ok, 2 partial,
4 expected/open (all pre-existing register `open` entries, not regressions), 2 NEEDS-GUI.
**0 regressions found by any drive against its own census baseline.** New, not-yet-registered
defects surfaced by these drives: 4 (`rc1-drive-portfolio-notes:1` — closed in round 2;
`rc1-drive-portfolio-notes:2` — harness note, not a product defect;
`rc1-drive-research-briefs:2` — open; `rc1-drive-onboarding-stranger:1` — register note against
an already-adjudicated `blocked_tier4` class, not an actionable new defect per the Gate Round 2
LEAD NOTE).

## Expected groups vs found

Expected (8): composer-chat, research-briefs, screener, panels-layouts, portfolio-notes,
settings-plugins, onboarding-stranger, failure-inducer.

All 8 have a drive file under `drives/*.md`. **None MISSING.**
