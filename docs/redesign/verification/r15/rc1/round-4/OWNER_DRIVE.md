# Owner Drive — RC1 Gate Round 4

One row per group, mechanically collated from `drives/<group>.md`'s own scored-table verdict cell (the bolded cell in each row). No new judgement, no re-runs.

| group | ok | partial | broken/new_defect | needs_gui | not_tested | unscored* | finding keys | evidence dir |
|---|---|---|---|---|---|---|---|---|
| composer-chat | 8 | 0 | 0 | 0 | 0 | 0 | none | `docs/redesign/verification/r15/surface/composer-chat/rc1/round-4/` |
| research-briefs | 11 | 0 | 0 | 0 | 0 | 3 | none | `docs/redesign/verification/r15/surface/research-briefs/rc1/round-4/` |
| screener | 10 | 1 | 1 | 0 | 1 | 0 | rc1-drive-screener:1 | `docs/redesign/verification/r15/surface/screener/rc1/round-4/` |
| panels-layouts | 14 | 0 | 2 | 0 | 4 | 0 | rc1-drive-panels-layouts:1 | `docs/redesign/verification/r15/surface/panels-layouts/rc1/round-4/` |
| portfolio-notes | 15 | 0 | 0 | 1 | 2 | 0 | none | `docs/redesign/verification/r15/surface/portfolio-notes/rc1/round-4/` |
| settings-plugins | 12 | 2 | 2 | 0 | 0 | 0 | none | `docs/redesign/verification/r15/surface/settings-plugins/rc1/round-4/` |
| onboarding-stranger | 15 | 1 | 0 | 0 | 0 | 2 | none | `docs/redesign/verification/r15/surface/onboarding-stranger/rc1/round-4/` |
| failure-inducer | 6 | 0 | 2 | 0 | 1 | 2 | rc1-drive-failure-inducer:1, rc1-drive-failure-inducer:2 | `docs/redesign/verification/r15/surface/failure-inducer/rc1/round-4/` |

*unscored: rows whose bolded verdict text didn't literally contain ok/holds/fixed/partial/broken/needs-gui/not-tested (e.g. "blocked_tier4, no fix round", "NOT re-run this round — cite census") — read the drive file directly for these rows' actual disposition.

## Census → rc1 deltas (per group)

- **composer-chat**: 6 census/round-3 regression-risk items confirmed cleared (stop-cancel, divergence notice x2, intent-gate, schema coercion, tool-call-id uniqueness); 1 new probe (R15-LEAD-043) ok. No new defects.
- **research-briefs**: 14/14 register-tracked items held (12 ok, 2 open-as-expected low, 1 blocked_tier4 no-regression). Zero regressions, zero new defects.
- **screener**: Census findings 1,2,3,4,5/6,7 and COD-workspace-layout-6 all FIXED and confirmed. New: AUTO-autonomy narration/mode mismatch (rc1-drive-screener:1).
- **panels-layouts**: 14 round-3-held rows re-verified, all hold; 2 new fixes since round 3 (DATA-117, LEAD-040) both hold. New: INFY.NS news off-topic articles (rc1-drive-panels-layouts:1).
- **portfolio-notes**: 197 real-component vitest assertions (91+106) all pass; 10 sidecar/live-quote/intent-gate checks all ok. No regressions, no new defects.
- **settings-plugins**: 8 census-broken rows now fixed and confirmed (fake-key validate, untrimmed key, region copy, keybinding conflict, plugin disable, NewsAPI probe, export/import, dual-store drift); 2 open-lows unchanged (no regression). No new defects.
- **onboarding-stranger**: All previously-certified fixes reconfirmed live; 2 open-lows unchanged at adjudicated status. No new defects.
- **failure-inducer**: 5 census/round-3 fixes (AGENT-026/025/027, RESEARCH-008, DATA-061) hold, no regression. New: 2 fresh live instances of the DATA-061 misclassification class the round-3 verifier already flagged (rc1-drive-failure-inducer:1, :2).

## Drive raw output

Checked on disk against `docs/redesign/verification/r15/surface/<group>/rc1/round-4/` (a group whose dir is missing or holds no file other than `.md` is a named lane failure):

- **composer-chat**: 20 raw files present — has raw output.
- **research-briefs**: 4 raw files present — has raw output.
- **screener**: 22 raw files present — has raw output.
- **panels-layouts**: 21 raw files present — has raw output.
- **portfolio-notes**: 15 raw files present — has raw output.
- **settings-plugins**: 18 raw files present — has raw output.
- **onboarding-stranger**: 20 raw files present — has raw output.
- **failure-inducer**: 8 raw files present — has raw output.

Per-row cited-raw-file check (each drive's own citations against its surface dir): every backtick-quoted filename in each `drives/<group>.md` resolves to a real file in that group's `rc1/round-4/` surface dir, **except** a handful of non-raw references that are not row citations to this round's evidence — a config filename (`copilot.json` in screener row 12's prose), prose mentions of `COVERAGE.json`, and explicit census-evidence citations on rows the drive itself marks `NOT TESTED this round` (failure-inducer row 11 cites the top-level census dir's `20-*.jsonl`/`52-junk-hang.txt` by design, not `rc1/round-4/` raw). No scored row's raw-file citation was found dangling.

**none missing.**

