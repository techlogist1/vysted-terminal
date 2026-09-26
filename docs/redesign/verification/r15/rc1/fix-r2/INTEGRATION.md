# RC1 fix round 2 (gate round 2): integration

Integrator: rc1-fix-r2-int (Opus). Branch `worktree-agent-rc1-4c6dfe8-fix-int`, base `ca6ec990`
(the round-1 head), head `81fbfe910d472ecd154fa62e42d86bce213a697e`, pushed to origin. The worktree
`scratchpad/rc1-4c6dfe8-fix-int` is left in place. This file replaces the 25 Sep round-2 integration
note for `1d6511c8`, which is in git at `b2cfbb68`.

## Merge (PLAN.md order, `--no-ff`, no conflicts)

| Merge | Writer branch head | Items |
|---|---|---|
| `81fbfe91` | W1-citation-grammar-r2 `39585dc3` | rc1-drive-research-briefs:2 (`39585dc3`) |

The writer branch was based on `ca6ec990` and touched exactly the five files PLAN.md names. I read
the diff before merging it. The two regexes are byte-identical to PLAN.md in both `citecheck.py` and
`brief-ingest.ts`, and range expansion is inclusive from the lower endpoint to the higher one. The
round-1 tests are unchanged. The new pins are 2 pytest cases in `test_research_citecheck.py`, 1 in
`test_research_iter.py` and 2 vitest cases in `brief-ingest.test.ts`. They include `[3—5]` with 4
sources, which is the case the fix was not written against. Nothing was reverted or dropped, and
there were no integration fixes. Before the full run, the targeted suites
(`test_research_citecheck`, `test_research_iter`, `brief-ingest.test.ts`) passed: 46 pytest and 53
vitest tests (`targeted.log`).

## Verification (all at `81fbfe91`)

| Gate | Result |
|---|---|
| `pnpm install --frozen-lockfile` | EXIT=0 (`install.log`) |
| `pnpm ci-local` run 1 (the main sidecar was rebuilt as STALE; both MCP sidecars were fresh) | **EXIT=0** (03:35:42Z) |
| `node scripts/smoke-test-sidecars.mjs` | **SMOKE_EXIT=0** (03:38:16Z). 3 sidecars booted, the `/agents` roster had 13 agents, MCP was ready with 40 tools, openbb and sec-edgar bound, and all children were torn down |
| `pnpm ci-local` run 2 (final; all three sidecars fresh) | **EXIT=0** (03:42:36Z) |

Counts from the final run:

- vitest: 152 files, 1836 tests passed. Round 1 had 1834; the 2 new tests are W1's.
- cargo test: 19 passed, plus 2 empty suites.
- pytest: 3603 passed and 1 skipped (the pre-existing skip). Round 1 had 3600; the 3 new tests are
  W1's.
- lint, prettier (444 files), tsc, cargo fmt, clippy `-D warnings` and ruff check/format all passed.

Logs: `ci-local.log` has both runs appended, and each ends in an `EXIT=` line. Also `smoke.log`,
`install.log` and `targeted.log`.

## Carried issues (not in the diff)

- The integrator did not re-run PLAN.md's scratch acceptance check, the BDL brief through
  `../fix-r1/recheck/gr2-original-bdl-brief-through-candidate`. That belongs to the recheck. The
  committed pins already cover `[basis: trailing 52 weeks]` byte-identical with 0 counted broken, in
  both nets.
- `expand_marker_groups`/`expandMarkerGroups` has no upper bound on range width. A model-written
  `[1-999]` expands to 999 markers before the range check strips all but the valid ones. The output
  is correct but wasteful. This is outside the entry's scope and not observed in any run.
