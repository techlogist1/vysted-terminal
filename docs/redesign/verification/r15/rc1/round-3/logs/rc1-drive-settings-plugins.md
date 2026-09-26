# rc1-drive-settings-plugins — working log (round 3)

Candidate `01d6920a300b016ab1ad8aa436ee4e4586f8e336`, worktree
`rc1-round-3-cand`, verified `git rev-parse HEAD` matches.

1. Read `PROMPT_surface_s2.md` (OWNER-DRIVE, settings-plugins scope), `COMMON.md`,
   `ISO_STACK.md`.
2. Read census evidence: `surface/settings-plugins/EVIDENCE.md`, `COVERAGE.json`,
   `census/raw/surf-settings-plugins.json`, `census/refute/surf-settings-plugins.json`
   (7 raw findings, all admitted: 1 high, 3 medium, 3 low → register ids R15-RESEARCH-010,
   R15-UI-057, R15-UI-058, R15-DATA-094, R15-UI-033 (merged from COD-plugins-8),
   R15-CODE-PLATFORM-012, R15-UI-082, R15-UI-081(merged -5/-7)).
3. Read round-2 redrive: `surface/settings-plugins/rc1/rc1-redrive.md` — 6 rows fixed and
   live-confirmed at candidate `4097dac4` and re-confirmed at gate-round-2 candidate
   `4c6dfe8c`; R15-UI-081 confirmed still open both times.
4. Register check (`vysted-r15-register.json`): R15-UI-081 open/low, R15-UI-082 open/low
   (with a triage note describing the exact residual — Devanagari names rejected by the
   percent-encoded byte-length cap), everything else in this group `fixed`. Neither open row
   is critical/high/medium, so this group carries no gate blocker either way.
5. `git diff --stat 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2..HEAD` scoped to this group's
   files → only `src/store/modules.ts` in-scope (`setEnabledMap` plugin:* preservation,
   `ef102fa5`, R15-CODE-PLATFORM-013 follow-up); `src/lib/host-actions.ts` changed too but is
   the R15-DATA-002 watchlist-region fix, portfolio-notes/composer-chat scope not mine.
6. Copied `rc1-round-3-seed-data` → `rc1-round-3-data-settings-plugins`. Booted own sidecar
   `cd rc1-round-3-cand/sidecar && sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1
   --port 52325 --data-dir <data>` (env `VYSTED_OPENBB_MCP_PORT=52153`,
   `VYSTED_SEC_EDGAR_MCP_PORT=52154`), sleep-wrapper pid 87059, worker pid 87062. `/health`
   200 version 0.8.0, openbb-mcp available.
7. Live-recheck of the 4 previously-fixed sidecar-side rows via curl against `:52325`:
   fake OpenRouter key validate, whitespace OpenAI key validate, NewsAPI status probe (key +
   keyless), plugin toggle persist round-trip — all match round-2's finding (still fixed).
   Output: `surface/settings-plugins/rc1/round-3/01-fixed-rows-recheck.txt`,
   `02-workspace-and-plugin-recheck.txt`.
8. Workspace-name edge cases re-run live: 234-char ASCII (400, reason present), 33-char/36-
   encoded-byte-per-glyph Devanagari name (400 "too long" — the register's documented residual,
   not a new finding), short 10-char Devanagari name (200 saved, cleaned up with DELETE).
9. Code-read confirmed `src/store/workspace.ts` `openPanel` is byte-identical to round 2 in
   this range (not in the diff) — R15-UI-081 genuinely unchanged, not a stale re-assertion.
10. Ran the 5 test files this group's changed row maps to
    (`pnpm exec vitest run src/store/modules.test.ts src/components/SettingsPanel.test.tsx
    src/lib/plugin-runtime.test.ts src/lib/workspace.test.ts src/store/workspace.test.ts`)
    against the candidate worktree (read-only — ran, did not edit or install): 5 files / 157
    tests pass, including the 3 tests pinned to R15-CODE-PLATFORM-013's `setEnabledMap`
    behaviour. Log: `rc1-round-3-vitest-settings-plugins.log` (scratch).
11. Wrote `surface/settings-plugins/rc1/round-3/COVERAGE.json` (14 rows, all in one of
    ok/partial/broken with round-3 evidence), `rc1/round-3/drives/settings-plugins.md`
    (scored table + deltas), `rc1/round-3/findings/rc1-drive-settings-plugins.json` (`[]` —
    no regression, no new defect).
12. Stopped own sidecar: `kill 87059`.

## Result

No regressions. No new defects. 6 previously-fixed rows hold live; 1 new in-scope fix
(R15-CODE-PLATFORM-013 follow-up) confirmed via committed regression tests; 2 previously-open
low-severity rows (R15-UI-081, R15-UI-082-residual) confirmed genuinely unchanged, matching
the register exactly — neither is a gate blocker (both low severity, both already carry a
register note).
