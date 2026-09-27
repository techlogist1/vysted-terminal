# rc1-battery-24 log

Candidate: `949c3c9fd49d61ecadc9813a8321bcdfd81178bd` (verified via `git rev-parse HEAD` on the candidate scratch worktree before starting).

Own sidecar booted from candidate source on `127.0.0.1:52364`, data dir `rc1-round-5-recheck-data-rc1-battery-24` (cp -R from the seed). `/health` confirmed ok before probing; sidecar/sh-wrapper PID 3646 (python PID 3649) killed at end of shard.

## Sets worked (in order)

1. **batch-9/W5-frontend-shell (set-39)** — UI-016, CODE-FRONTEND-016, UI-086, CROSS-PLATFORM-004, UI-058, DATA-092, UI-052. All 7 are pure frontend keybinding/palette/settings/onboarding-copy behaviors originally certified via scratch (uncommitted) vitest in batch-9's fresh verifier. This role has no GUI and is barred from running vitest suites; located a committed, named pinned test for each id in the candidate tree (`keybindings.test.ts`, `CommandPalette.test.tsx`, `command-palette.test.ts`, `settings.test.ts`, `search-settings.test.ts`, `SettingsPanel.test.tsx`, `region.test.ts`, `OnboardingFlow.test.tsx`, `OnboardingBanner.test.tsx`) plus a static source spot-check that the fixed code paths still exist. Verdict `ci_pinned` for all 7.

2. **batch-2/W1-fundamentals-seam (set-0)** — DATA-004, DATA-013, DATA-006, DATA-070, DATA-033. All live-probed: DATA-004/013/006 via curl against the sidecar (DHANBANK ownership flag, DAL eps/pe flag, DAL stale-quote label); DATA-070/033 via in-process python calling the real `news_provider.py` / `correctness_gate.py` functions from the candidate's own `sidecar/.venv`. All 5 hold, matching or exceeding the batch-2 certified evidence.

3. **batch-28/W5-opus (set-79)** — LEAD-045, LEAD-044, DATA-114, DATA-053. LEAD-045 and LEAD-044 via in-process python (`yahoo_batch_provider.fetch_quotes_batch`, `screener._fetch_pair`) — LEAD-045 reproduced the exact certified fresh-case numbers (16 rows, 0 failures); LEAD-044 reproduced the bug/fix contrast live (HAL resolves to Hindustan Aeronautics under a bare IN-session lookup, Halliburton once the sp500 universe's intrinsic-region override is applied). DATA-114 and DATA-053 via curl against the sidecar. All 4 hold.

## Notes

- No vitest or pytest suite was run by this role (barred; heavy lane owns them).
- `sleep`-based waits for detached probes used `run_in_background` + a poll loop per the harness rule, not inline `sleep N; cmd` chains.
- No entry in these 3 sets showed any deviation from its certified behaviour; no findings.

COVERAGE: 16/16 ids raw across all 3 sets; no raw: none.
