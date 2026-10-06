# rc1-battery-21 — shard 21 log

Candidate sha 1006c6da694ede5776c3dabbd27b305aeb56b5ad (verified via
`git rev-parse HEAD` at start). Own sidecar booted on :52361 (cwd
`<cand>/sidecar`, data dir `rc1-round-4-data-rc1-battery-21` copied from the
seed snapshot), sleep pid 8747; shared main sidecar :52152 confirmed healthy
before starting; openbb-mcp :52153 / sec-edgar-mcp :52154 confirmed reachable.

Sets covered: batch-3/W5-india-data-witnesses (set-9, 7 ids), batch-10/W6-chart-notes-blueprint
(set-45, 7 ids), batch-12/W5-agent-runtime (set-60, 1 id). No prior round-4 work
existed for this label at start (checked battery/set-9.md, set-45.md, set-60.md,
findings/rc1-battery-21.json — none present).

Environment note: the shared candidate worktree's `docs/` tree (5148 files)
shows as deleted on disk (`git status --short`) though `git show HEAD:<path>`
returns full content for every one of them — `sidecar/`, `src/`, `src-tauri/`
are untouched. Read doc-check entries (DOCS-004, DOCS-005, DATA-078,
CODE-PLATFORM-024) via `git show HEAD:<path>` instead of the working tree.
Filed as `rc1-battery-21:1` (kind environment, since this is not a product
defect but affects any role reading candidate docs/ from disk).

Verdicts: 13 holds, 2 ci_pinned (R15-UI-048, R15-UI-024 — vitest-pinned, not
re-run per instructions; structurally verified via source + test-name grep
instead). 0 regressed, 0 needs_gui, 0 blocked_env.

R15-AGENT-092 required a live delegate run through `POST /agents/copilot/runs`
on llama3.1:8b (local-model lock held around each `vy.py post` launch call;
released on return since the run itself executes detached server-side after
launch returns — the lock cannot cover the detached inference window, only the
launch call). Halted run (maxTokens=1000): status error, "token ceiling 1000
reached (7611 used)", host_actions []. Control run (default budget): status
done, host_actions carries the dispatched write_note. Matches batch-12 cert.

Stopped own sidecar (killed sleep pid 8747) at end. Ollama lock dir confirmed
absent (not held) after each launch call returned.

COVERAGE: 15/15 ids raw across all three sets; no raw missing.
