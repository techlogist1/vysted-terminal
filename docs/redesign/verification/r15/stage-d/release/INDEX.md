# Release docs draft set - index

Drafted from `d38b5d1a2487bd52fe8a7e741a3a5266e3206611` (code) and `4da7fc91` (docs and register). Promote at the launch tag by filling markers.

| File | What it is | Promote to |
| --- | --- | --- |
| RELEASE_NOTES.md | User-facing v0.9.0 notes, known-limitation block verbatim, LEAD-116 status, open items | repo root or `CHANGELOG`-adjacent release notes <<CHECK: target path>> |
| CURRENT_STATE.md | Replacement draft of `docs/CURRENT_STATE.md`, current-state only | `docs/CURRENT_STATE.md` |
| GITHUB_RELEASE_v0.9.0.md | Body for the DRAFT GitHub release plus the exact `gh release create` command | `--notes-file` of the release |
| OPERATOR_BRIEFING.md | Replacement draft of `docs/redesign/OPERATOR_BRIEFING.md`: outcome, public-button sequence, signing paragraph | `docs/redesign/OPERATOR_BRIEFING.md` |
| HAND_TESTING_GUIDE.md | Cold-return 30-45 minute tour of the installed app | `docs/` |
| BACKLOG_0.9.1.md | Replacement draft of `docs/redesign/BACKLOG_0.9.1.md` | `docs/redesign/BACKLOG_0.9.1.md` |
| WINDOWS_MANUAL_CHECK.md | NEEDS-MANUAL-CHECK list for the Windows (ROG) test, CODE-AGENT-001 first | `docs/` |
| PMSET_REVERT.md | Power and system settings this run changed (none recorded for pmset) and how to revert | operator only |
| INDEX.md | This file | - |

## Markers

| Marker | Meaning | Used in |
| --- | --- | --- |
| `<<RC2_SHA>>` | the rc2 tag sha | RELEASE_NOTES, OPERATOR_BRIEFING, CURRENT_STATE |
| `<<LAUNCH_SHA>>` | the r15-launch tag sha the bundle is built from | RELEASE_NOTES, GITHUB_RELEASE, OPERATOR_BRIEFING, HAND_TESTING_GUIDE, CURRENT_STATE |
| `<<BUNDLE_SHA256>>` | sha256 of the final dmg | RELEASE_NOTES, GITHUB_RELEASE, OPERATOR_BRIEFING, HAND_TESTING_GUIDE, CURRENT_STATE |
| `<<BUNDLE_BYTES>>` | byte size of the final dmg | RELEASE_NOTES, GITHUB_RELEASE, OPERATOR_BRIEFING, HAND_TESTING_GUIDE, CURRENT_STATE |
| `<<FINAL_PASS_SUMMARY>>` | the final adversarial pass summary | RELEASE_NOTES, OPERATOR_BRIEFING, BACKLOG_0.9.1, CURRENT_STATE |
| `<<OPEN_COUNTS>>` | open medium and low totals after the final pass | RELEASE_NOTES, GITHUB_RELEASE, OPERATOR_BRIEFING, BACKLOG_0.9.1, CURRENT_STATE |
| `<<CHECK: ...>>` | a fact that was not on disk; resolve or delete at promotion | see the list below |

`<<CHECK: ...>>` occurrences are listed by `grep -n "<<CHECK" *.md` in this folder; the checks cover: whether the dmg is signed (RELEASE_NOTES, GITHUB_RELEASE), the real commercial contact (GITHUB_RELEASE), the sidecar dev-sign step for a Developer ID build (OPERATOR_BRIEFING), the app data directory name and issue tracker (HAND_TESTING_GUIDE), Windows prerequisites and uninstall behaviour (WINDOWS_MANUAL_CHECK), generic macOS pmset defaults and whether the final-pass caffeinate stage ran (PMSET_REVERT), and version-file confirmation and the panel inventory (CURRENT_STATE).
