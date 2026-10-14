# Set: batch-2/W4-workspace-persistence (set-3.md) - rc1-battery-15 at ace7dd76

Raw: battery/raw/set-3/<id>.txt. Frontend-store repros are vitest-only (battery never runs suites): ci_pinned, test existence confirmed at the candidate.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-FRONTEND-004 | live POST/GET/list/DELETE /workspace for 'Research: NVDA', 'Research: RELIANCE.NS', 'Research: M&M', 'My Layout (2)', Hindi name | all POST 200, GET 200, listed, DELETE 204 (orig: 400) | holds |
| R15-CODE-FRONTEND-001 | frontend loadWorkspace rollback | test present: src/lib/workspace.test.ts:664 | ci_pinned |
| R15-LIFECYCLE-002 | restore with unregistered panel | tests present: workspace.test.ts:1063, :1146 | ci_pinned |
| R15-LIFECYCLE-003 | autosave burst during restore | test present: workspace.test.ts:1489 | ci_pinned |
| R15-CODE-FRONTEND-005 | drawings/keybindings not autosaving | test present: workspace.test.ts:1540 | ci_pinned |
| R15-CODE-FRONTEND-018 | screener saved screens not in blob | test present: workspace.test.ts:1671 | ci_pinned |
| R15-LIFECYCLE-009 | v0.8.0 ledger import | sidecar GET /portfolio/positions 200; tests present: workspace.test.ts:1689, :1768 | ci_pinned |

COVERAGE: 7/7 ids raw; no raw: none
