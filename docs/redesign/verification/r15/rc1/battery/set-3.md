# batch-2/W4-workspace-persistence

Sidecar under test: candidate `4c6dfe8c` (rc1-cand worktree), own sidecar `127.0.0.1:52340`,
data dir `rc1-data-rc1-battery-0` (seed copy). Entries whose original certification drove real
`src/lib/workspace.ts` in-process against a live sidecar (not a curl-able endpoint) are
verdict `ci_pinned` against the committed vitest test that names the entry, per the role's
"never run vitest suites" rule — grepped for presence at the candidate sha, not executed.
`R15-CODE-FRONTEND-004` is a pure HTTP repro and was re-run live.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-FRONTEND-001 | grep `src/lib/workspace.test.ts` for the committed pin. | `it("loading a named workspace never rolls back portfolios or notes (R15-CODE-FRONTEND-001)", ...)` present at line 574. | ci_pinned (src/lib/workspace.test.ts:574) |
| R15-LIFECYCLE-002 | grep `src/lib/workspace.test.ts`. | `describe("restoreLastSessionOrDefault — boot-crash guards", ...)` present at line 917. | ci_pinned (src/lib/workspace.test.ts:917) |
| R15-LIFECYCLE-003 | grep `src/lib/workspace.test.ts`. | `describe("persisted-slice registry + gated autosave (R15-LIFECYCLE-003, CODE-FRONTEND-005/018)", ...)` present at line 1288, naming the entry directly. | ci_pinned (src/lib/workspace.test.ts:1288) |
| R15-CODE-FRONTEND-005 | grep `src/lib/workspace.test.ts`. | Same describe block at line 1288 covers drawings/keybindings in the persisted-slice registry. | ci_pinned (src/lib/workspace.test.ts:1288) |
| R15-CODE-FRONTEND-018 | grep `src/lib/workspace.test.ts`. | Same describe block asserts `savedScreens` round-trips through the workspace blob. | ci_pinned (src/lib/workspace.test.ts:1288) |
| R15-CODE-FRONTEND-004 | Live re-run: `POST /workspace` with `name` = `"Research: NVDA"`, `"Research: RELIANCE.NS"`, `"Research: M&M"`, `"My Layout (2)"`, a Hindi name, `"../escape"`, `"a/b\c"`; then `GET`/`DELETE` on the NVDA name; listed the on-disk `workspaces/` dir. | All POSTs return `{"status":"saved","name":"<name>"}` (no 400). Every name is percent-encoded on disk and stays inside `workspaces/`: `%2E%2E%2Fescape.vysted-workspace`, `a%2Fb%5Cc.vysted-workspace`, the Hindi UTF-8-percent-encoded file, `Research%3A RELIANCE%2ENS.vysted-workspace`, etc. — no path traversal, no file outside the directory. `GET /workspace/Research%3A%20NVDA` returns `{}`, `DELETE` succeeds. | holds |
| R15-LIFECYCLE-009 | grep `src/lib/workspace.test.ts`. | `describe("legacy positions import (R15-LIFECYCLE-009)", ...)` present at line 1573, naming the entry directly. | ci_pinned (src/lib/workspace.test.ts:1573) |

**Set result: 1/7 holds (live), 6/7 ci_pinned.**
