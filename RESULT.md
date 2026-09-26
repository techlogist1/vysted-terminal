# R15-CODE-AGENT-031 second attempt (CN, base 4c6dfe8c)

- Stamped: 06:54 IST
- Outcome: fixed_untested
- Branch: worktree-agent-lows-CN-r15-code-agent-031-4c6dfe8
- Fix commit: 65859b92
- Cherry-picked: none (the W6 branch carries no commit for this entry; its 3 commits are 017/029/032)
- Merge check: git merge-tree of origin/worktree-agent-lows-P1-W6-runs-stores and this branch is clean

## Fix
The runs wire is snake_case only, both directions. models/run.py loses every alias and
populate_by_name (the docstring now names the real TS reader, src/lib/delegate-runs.ts, not a
non-existent types/data.ts mirror). routers/runs.py loses _dual_case; GET /runs and
GET /runs/{id} dump the models as-is; launch returns {run_id} only. delegate-runs.ts reads
run_id and host_actions only. docs/SIDECAR_API.md gains a Delegate runs section.

## Files
docs/SIDECAR_API.md, sidecar/models/run.py, sidecar/routers/runs.py,
sidecar/tests/test_runs_router.py, sidecar/tests/test_run_manager.py,
src/lib/delegate-runs.ts, src/lib/delegate-runs.test.ts

## Tests (written as source, NOT run: off-lane rule)
- New acceptance: sidecar/tests/test_runs_router.py::test_runs_rows_carry_only_snake_case_keys
  (exact key sets for the list row, the detail, cost and budget)
- Rewritten (pinned the old wire): test_launch_returns_201_with_run_id (snake body, {run_id}
  exactly), test_launch_response_never_echoes_api_key (snake api_key),
  test_launch_accepts_snake_case_run_budget -> test_launch_rejects_a_camel_case_budget (422),
  test_list_runs_dual_case_shape -> test_list_runs_shape, test_get_run_returns_transcript
  (checkpoint_messages), test_run_manager::test_run_output_is_returned_untruncated_by_get_run
  (host_actions), delegate-runs.test.ts (run_id / host_actions mocks)
- Ran only: py_compile, ruff format/check (touched .py), prettier --write (touched .ts/.md)

## Untested pending integration
All of it: pytest test_runs_router/test_run_manager/test_runs_store, vitest delegate-runs and
AgentsRail, typecheck.

## Risks
- A launch body with the old camelCase apiKey is now a 422, and FastAPI's default 422 body
  echoes the offending input value. The only caller (delegate-runs.ts) sends api_key, so no
  live path hits it; a caller that sends camelCase would get its own key back on loopback.
- CLAUDE.md (Tier-1, not touched by this branch) still says "GET /runs emits BOTH camelCase +
  snake_case"; the lead should change that line to "GET /runs is snake_case only".
- Any unmerged branch that adds a camelCase reader of the runs wire (or a new field on the run
  models) would break or trip the exact key-set test; the test failing is the intended signal.
