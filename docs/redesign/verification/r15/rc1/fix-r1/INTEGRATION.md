# RC1 fix round 1 (gate round 2): integration

Integrator: rc1-fix-r1-int (Opus). Branch `worktree-agent-rc1-4c6dfe8-fix-int`, base
`4c6dfe8c`, head `ca6ec990d226bb8a3ba2eb2cc89b5af056a6e19c` (pushed to origin). Worktree
`scratchpad/rc1-4c6dfe8-fix-int`, left in place. This file replaces the 25 Sep integration
record for base `4097dac4`.

## Merges (PLAN.md order, `--no-ff`, no conflicts)

| Commit | What | Item |
|---|---|---|
| `357bd64f` | merge W1-citation-marker-grammar `a30f693c` | rc1-drive-research-briefs:2 |
| `ca6ec990` | integrator fix on W1 (below) | rc1-drive-research-briefs:2 |

Nothing was reverted or dropped.

## Integrator fix (`ca6ec990`)

The W1 diff was read before the merge. Its pseudo-citation regex (`_PSEUDO_CITE_RE` in
`citecheck.py`, `PSEUDO_CITE_RE` in `brief-ingest.ts`) stripped the `[ref]` half of a
reference link: `See [the filing][sec] here.` became `See [the filing] here.` PLAN.md requires
that reference links survive, and the writer's own docstring claims they do. The probe was run
against the writer's regex before the fix.

- Both regexes gain a `(?<!\D\])` lookbehind. A `[label]` preceded by a non-numeric `]` is the
  second half of a reference link and is spared. `[6][New findings]` is still caught.
- Both functions now run the pseudo pass before the numeric pass. The reason is the TS path:
  once `[9]` had become `[?]`, a following `[Web evidence]` was hidden from the new lookbehind.
- Pinned on a case the writer did not write against. In pytest,
  `test_reference_link_survives_while_label_after_bad_marker_is_stripped` checks that
  `[the filing][sec]` survives while `[9][Web evidence]` is stripped. In vitest,
  `keeps a reference link and flags a label riding an out-of-range marker` checks for
  `[?][?]`. Both fail without the fix.

## Verification (all at `ca6ec990`)

| Gate | Result |
|---|---|
| `pnpm ci-local` run 1 (clean worktree: fresh venvs, all 3 sidecars rebuilt) | **CI_EXIT=0** (2026-09-26T02:51:38Z) |
| `node scripts/smoke-test-sidecars.mjs` | **SMOKE_EXIT=0** (02:54:04Z). 3 sidecars booted and were torn down, version 0.8.0, 13 agents, MCP ready with toolCount=40, openbb and sec-edgar bound, BSE/NSE probes OK |
| `pnpm ci-local` run 2 (final; the sidecars were fresh, so the build was skipped) | **CI_EXIT=0** (02:58:25Z) |

Counts from the final run: vitest has 152 files and 1834 tests passed. cargo test has 19 passed
(plus 2 empty suites). pytest has 3600 passed and 1 skipped (a pre-existing skip). lint,
prettier, tsc, cargo fmt, clippy `-D warnings` and ruff check/format all passed.

Logs: `ci-local.log` (both runs, appended) and `smoke.log`.
