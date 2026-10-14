# RC1 gate round 5 — fix round 1 integration (rc1-fix-r1-int)

Written 2026-09-27 16:30 IST. Base 9bc600ece2ce6343a6aa48f130d7620b1466bb98.
Branch `worktree-agent-rc1-round-5-9bc600e-fix-int` (pushed), worktree
`scratchpad/rc1-round-5-9bc600e-fix-int` (left in place).

## Merged (PLAN.md order)

| Writer branch | Commit | Finding | Outcome |
|---|---|---|---|
| origin/worktree-agent-rc1-round-5-9bc600e-fix-r1-insider-table | 38a64fda | rc1-drive-panels-layouts:1 | merged clean (merge 633f8440) |

The diff touches only `src/modules/sec/InsiderTradingTable.tsx` and its test, as PLAN.md scoped it.
The null Direction cell and the `|| null` Reporter both route to DataTable's `NULL_GLYPH`, because
`BodyCell` treats `custom === null` / `text === null` as null (src/components/DataTable.tsx:153-155).
No conflicts, no integration fixes, and no dropped commits.

## Gates at head 633f844071d972b337f4c3526d86555c80df0568

| Gate | Result |
|---|---|
| ci-local run 1 (`ci-local.log`, first section) | EXIT=0 |
| ci-local run 2, final (`ci-local.log`, appended) | EXIT=0 |
| smoke-test-sidecars (`smoke.log`) | EXIT=0 |

Counts from the final run: vitest 153 files / 1881 tests passed; cargo test 19 passed (0 failed);
pytest 3780 passed, 1 skipped; lint, format:check, typecheck, cargo fmt, clippy -D warnings, ruff
check and ruff format --check all passed (the command is &&-chained). Run 1 rebuilt all 3 sidecars
from clean in this worktree (main 87 MB, openbb-mcp 55 MB, sec-edgar-mcp 83 MB).
Smoke: version 0.8.0, 13 agents, /mcp/status ready with toolCount=40, the openbb-mcp and
sec-edgar-mcp subprocesses bound and survived the settle window, and all children were torn down.

## Issues (outside the entry, not in the diff)

These are carried from PLAN.md: sec-edgar-mcp 1.0.8 insider tools read attributes that
edgartools 5.59.1 does not expose, so there are no per-trade insider rows; and
`_direction_from_code` maps code X to disposed and has an unreachable empty branch.
