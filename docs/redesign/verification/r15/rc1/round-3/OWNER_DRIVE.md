# RC1 Gate Round 3 — Owner Drive Index

Candidate sha `01d6920a300b016ab1ad8aa436ee4e4586f8e336`. Collated mechanically from
`drives/*.md` and `findings/rc1-drive-*.json` already on disk — no re-runs, no new judgement.

Expected groups (8): composer-chat, research-briefs, screener, panels-layouts,
portfolio-notes, settings-plugins, onboarding-stranger, failure-inducer. All 8 present.
MISSING: none.

| Group | Interactions driven | ok | partial | broken/regression | NEEDS-GUI | NOT TESTED | Census → rc1 deltas | Finding keys | Evidence dir |
|---|---|---|---|---|---|---|---|---|---|
| composer-chat | 7 (6 conversation turns + no-key probe) | 2 | 1 (turn 2, invented ticker — known llama3.1:8b resolver limitation, out of fix-class) | 4 (3 turns fixed from broken: t3/t4/t5; **1 new REGRESSION**: no-key OpenAI/Groq error frame now generic "internal" instead of humanized) | 0 | 0 | 3 previously-broken turns now fixed (tool-call-id identity, write_note intent gate, screener write+run); 1 new regression filed | `rc1-drive-composer-chat:1` (new_defect, medium) | `docs/redesign/verification/r15/surface/composer-chat/rc1/round-3/` |
| research-briefs | 13 items | 11 | 0 | 2 (open/expected, not regressions: vysted:// favicon links R15-UI-080; no-web-honest-banner R15-RESEARCH-041) | 0 | 0 | All 11 previously-fixed/critical citation-integrity findings hold live; 2 already-open low items confirmed unchanged | `rc1-drive-research-briefs:1` (new_defect, medium — non-numeric `[vysted://...]` bracket token bypasses citation-marker regex) | `docs/redesign/verification/r15/surface/research-briefs/rc1/round-3/` |
| screener | 10 scored rows + universe/limit/formula spot-checks | 10 | 0 | 0 | 1 (row-click drill/CSV download/column-resize, per Stage B GUI skip) | 0 (mid-run cancel not re-timed, unchanged) | All census broken/partial rows now fixed and hold; bonus: boolean-coercion in min/max now rejected at validate time (strict improvement) | none | `docs/redesign/verification/r15/surface/screener/rc1/round-3/` |
| panels-layouts | 14 scored rows | 12 (holds) | 1 (Agent Builder tool vocab — backend half holds, frontend not re-checked) | 0 (1 already-open/low unchanged: R15-UI-077 yield-curve duplicate-pillar 500, not a regression) | 0 | 6 named panels/layouts carried forward at census score (budget) | All 8 census-fixed rows hold; 1 known-open row confirmed still open by design; no regressions, no new defects | none | `docs/redesign/verification/r15/surface/panels-layouts/rc1/round-3/` |
| portfolio-notes | 27 scored rows | 23 (incl. 1 ok/NEEDS-GUI hybrid: Link-button popover render) | 0 | 0 | 1 dedicated (drag reorder / WKWebView save dialogs / Tauri note-mirror / slash-nav in a real webview) | 3 (injection-shaped content, 100-position render, huge-note perf — all unchanged since census) | All 8 census raw findings (SURF-PORTFOLIO-NOTES-1..8) reproduce as fixed; no regression, no new defect | none | `docs/redesign/verification/r15/surface/portfolio-notes/rc1/round-3/` |
| settings-plugins | 8 scored rows | 7 | 0 | 0 | 0 | 5 items not re-driven live (unchanged code, cited instead) | 6 previously-fixed rows re-confirmed live; 1 new in-scope fix (`setEnabledMap` plugin:* flag preservation) confirmed; 1 already-open row (disabled-module-panel-still-opens) proven unchanged via diff; no regressions | none | `docs/redesign/verification/r15/surface/settings-plugins/rc1/round-3/` |
| onboarding-stranger | 14 scored rows | 11 | 0 | 0 (1 already-open/low-by-design unchanged: default watchlist/chart vs IN region, R15-UI-076) | 0 | 2 (keychain-denied dead end — blocked_tier4 adjudicated; Ollama daemon-down states — shared daemon, unchanged) | 6 fixing register ids confirmed live/code-verified with no regression; 1 not_a_defect confirmed current; no new defects | none | `docs/redesign/verification/r15/surface/onboarding-stranger/rc1/round-3/` |
| failure-inducer | 5 inducer classes | 5 | 0 | 0 | 0 | 2 (Docker/SearXNG-down honesty path, and malformed-symbol sweep beyond the one repro — both unchanged code paths, not re-probed) | All 5 census broken/silent/misleading inducer classes now score ok, confirmed live or by direct code read; zero regressions | none | `docs/redesign/verification/r15/surface/failure-inducer/rc1/round-3/` |

## Notes

- "ok" folds in rows the source drive marked `holds`, `fixed`, or `ok (code)` — i.e. previously
  broken/partial and now verified working, or previously-ok and still ok.
- Rows the source drive itself scored as an already-known `open`/low-severity/by-design item
  (not touched by this gate's fix scope, and not a regression) are counted separately in the
  broken/regression column with an explicit "(open/expected, not a regression)" note and are
  **not** treated as new failures.
- Two new_defect findings this round (composer-chat, research-briefs) are carried into
  `FINDINGS.json`/`FINDINGS.md` below with full repro/evidence.
