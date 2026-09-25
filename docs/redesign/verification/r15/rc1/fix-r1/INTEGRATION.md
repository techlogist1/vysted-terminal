# RC1 fix round 1 — integration

Integrator: rc1-fix-r1-int (Opus). Branch `worktree-agent-rc1-4097dac-fix-int`, base
`4097dac4`, head `b0f2b256f2fc2379f742bf9e0687eb54db44d290` (pushed to origin). Worktree
`scratchpad/rc1-4097dac-fix-int` (left in place).

## Merges (PLAN.md order, `--no-ff`, no conflicts)

| Merge | Writer branch head | Items |
|---|---|---|
| `27e490e1` | W1-research-coverage `0f1a4a71` | rc1-drive-research-briefs:1 (`83ec78e8`), rc1-battery-4:1 (`0f1a4a71`) |
| `73036305` | W2-agent-model-boundary `1379f26a` | rc1-scenarios:5 (`23f2ab34`), rc1-drive-onboarding-stranger:1 (`1379f26a`) |
| `e81c2b3d` | W3-fundamentals-derived `7e1f3627` | rc1-datapack:1 (`7e1f3627`) |
| `b0f2b256` | W4-portfolio-and-docs `ed1ed202` | rc1-drive-portfolio-notes:1 (`dcb09674`), rc1-gate8:1 (`ed1ed202`) |

Each writer diff was read before merge and matches its PLAN.md writer set. Nothing was
reverted, dropped or changed by the integrator. There were no integration fixes, because
the first ci-local run was green.

## Verification (all at `b0f2b256`)

| Gate | Result |
|---|---|
| `pnpm ci-local` run 1 (clean worktree: fresh venv, all 3 sidecars rebuilt) | **CI_EXIT=0** (01:58:51Z) |
| `node scripts/smoke-test-sidecars.mjs` | **SMOKE_EXIT=0** (02:01:23Z). 3 sidecars booted, 13 agents, MCP ready with 40 tools, openbb + sec-edgar bound |
| `pnpm ci-local` run 2 (final) | **CI_EXIT=0** (02:05:48Z) |

Counts from the final run: vitest has 152 files and 1825 tests passed. cargo test has 19 passed
across 3 suites. pytest has 3141 passed and 1 skipped (a pre-existing skip). lint, prettier,
tsc, cargo fmt, clippy `-D warnings` and ruff check/format all passed.

Logs: `ci-local.log` (both runs appended, each ending in a `CI_EXIT=` line) and `smoke.log`.

## Carried issues (from PLAN.md, not in any diff)

- The ADR-ratio half of scenarios:5 is a model-capability limit.
- A fabricated tool result that already streamed stays in the transcript after a
  call-syntax rescue.
- The `nse_provider` throttle waits while it holds the module `_lock`.
