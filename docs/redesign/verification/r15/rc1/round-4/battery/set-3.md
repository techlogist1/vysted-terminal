# batch-2/W4-workspace-persistence (rc1-battery-19, set-3)

Candidate: `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Sidecar: own instance on `:52359`, data dir
`rc1-round-4-data-battery-19` (copy of the keyless ISO seed).

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-CODE-FRONTEND-004 | Live POST/GET/DELETE `/workspace` on `:52359` with `Research: NVDA`, `Research: RELIANCE.NS`, `Research: M&M`, `My Layout (2)`, `../escape`, `a/b\c` | All 6 saved 200, listed correctly, files on disk percent-encoded inside `workspaces/` (`%2E%2E%2Fescape.vysted-workspace`, `a%2Fb%5Cc.vysted-workspace`, etc.) — no directory escape. All 6 deleted 204 after. | holds |
| R15-CODE-FRONTEND-001 | frontend-only (`applyLayoutSlice` scoping); source read + pinned test named | `PERSISTED_SLICES`/`applyLayoutSlice` (workspace.ts:300,672) restrict a named-workspace load to the layout slice only, matching the fix_shape; pinned `workspace.test.ts:603` encodes the exact original repro | ci_pinned (workspace.test.ts:603) |
| R15-LIFECYCLE-002 | frontend-only (restore-order / unregistered-panel handling); source read + pinned tests named | `loadWorkspace` (workspace.ts:798) no longer abandons the whole blob on an unregistered panel; pinned tests cover both the positive restore and the strip-and-restore-rest path | ci_pinned (workspace.test.ts:1001, :1084) |
| R15-LIFECYCLE-003 | frontend-only (autosave/restore race); source read + pinned test named | `restoreSettled` flag (workspace.ts:1030,1047,958) gates `autosaveLayout` until restore finishes; single `PERSISTED_SLICES` subscription loop (line 1103) replaces PanelHost's private timer | ci_pinned (workspace.test.ts:1317 describe block) |
| R15-CODE-FRONTEND-005 | frontend-only (persisted-slice trigger wiring); source read + pinned test named | `PERSISTED_SLICES` table (workspace.ts:300) is the single source for payload build, restore and trigger wiring — drawings/keybindings/research-spaces all covered generically | ci_pinned (workspace.test.ts:1317, :1457) |
| R15-CODE-FRONTEND-018 | frontend-only (savedScreens slice); source read + pinned test named | `savedScreens` now present as a `PERSISTED_SLICES` entry (previously absent per the original repro grep) | ci_pinned (workspace.test.ts:1584) |
| R15-LIFECYCLE-009 | frontend-only (one-time ledger import); source read + pinned tests named | Legacy positions-import logic present in workspace.ts, matching fix_shape; pinned tests cover both the import-once case and the idempotent/negative case | ci_pinned (workspace.test.ts:1602 describe block, :1681, :1719) |

Notes: the six frontend-logic entries need a TS/jsdom runtime (Zustand stores + `deserializeWorkspace`)
to exercise directly. The candidate worktree is read-only for this role (no test file may be added
to it), and standing up a separate writable frontend checkout + `node_modules` within the stall
budget was not attempted for a single shard; each is instead confirmed by (a) reading the exact
source lines implementing the fix_shape at the candidate sha and (b) naming the pinned, already-
committed vitest test that encodes the register entry's original repro as its assertion — per the
task's own carve-out ("an entry certified only through a pinned test → verdict ci_pinned naming
the test"). R15-CODE-FRONTEND-004 is a pure sidecar (Python) behavior and was re-run live end to
end with real HTTP against the candidate's own workspace router.

COVERAGE: 7/7 ids raw; no raw: none (the 6 ci_pinned ids still got a raw file with source-line
citations + the pinned test name, not a live run).
