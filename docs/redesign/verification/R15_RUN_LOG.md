# R15 LAUNCH — run log (telemetry)

Owned by the telemetry worker; appended at every wave boundary. Times are IST, from the real clock.

## Waves

| # | Started | Workflow / task | Agents | Routed → actual model | Purpose | Result |
|---|---|---|---|---|---|---|
| W0 | 06:11 | lead own-hands Stage 0 | 0 | lead = claude-fable-5-1 | brief saved, tree adjudicated, 4 commits (043850c, 7a1cd8f, 0112a0c, 96511d6) | done |
| W1 | 06:20 | wf_6871fdb3-621 r15-stage0-truth | 11 | sonnet×5, opus×5 (2 worktree writers), haiku×1 | Stage 0 scouts + pushguard + rig | in flight |
| W2 | 06:23 | wf_734dffa1-5d4 r15-census-intent-world | up to 20 | sonnet×4, opus×14 | Intent + World sweeps, ledgers | in flight |
| bg | 06:20 | `pnpm ci-local` baseline (detached) | — | — | full chain baseline numbers | in flight |

## Strategy changes

(none yet)

## Limit walls

(none yet)

## API spend

(budget pending `r15/stage0/BUDGET.md`)
