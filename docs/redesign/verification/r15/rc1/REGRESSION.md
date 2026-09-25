# RC1 CI-Smoke Regression Report (rc1-heavy)

- **Candidate sha:** 4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a
- **Branch:** 004-r4-experience-rebuild
- **Worktree:** rc1-cand scratch worktree
- **Lane:** ci-smoke (rc1-heavy, heavy-lane owner)
- **Overall result: PASS (no re-runs required — zero failures on first pass)**

## `pnpm ci-local` — EXIT=0

Log: `docs/redesign/verification/r15/rc1/logs/ci-local.log`

| Stage | Result | Detail |
|---|---|---|
| install | OK | `Lockfile is up to date, resolution step is skipped`; `Done in 538ms using pnpm v10.32.1` |
| ensure-all-sidecars | OK | all 3 bundled sidecar binaries present and fresh — skipped rebuild |
| lint (`eslint .`) | OK | no errors reported |
| format:check | OK | `All matched files use Prettier code style!` |
| typecheck (`tsc --noEmit`) | OK | no errors reported |
| cargo fmt --check | OK | no diff reported |
| clippy (`-D warnings`, all-targets) | OK | `Finished \`dev\` profile [unoptimized + debuginfo] target(s) in 43.62s`, zero warnings |
| ruff check sidecar | OK | `All checks passed!` |
| ruff format --check sidecar | OK | `438 files already formatted` |
| vitest (`pnpm test`) | OK | `Test Files 152 passed (152)`, `Tests 1824 passed (1824)`, duration 28.07s |
| cargo test (src-tauri) | OK | lib: `19 passed; 0 failed; 0 ignored`; main.rs unittests: `0 passed; 0 failed` (no `#[test]` fns in main.rs, expected — binary crate delegates tests to lib); doctests: `0 passed; 0 failed` |
| pytest (sidecar) | OK | `3129 passed, 1 skipped, 4 warnings in 205.61s (0:03:25)` |

Final log line: `EXIT=0`

## `node scripts/smoke-test-sidecars.mjs` — EXIT=0

Log: `docs/redesign/verification/r15/rc1/logs/smoke.log`

Mode: ATTENDED-SAFE (ephemeral ports only, own PID ledger, zero interaction with any pre-existing vysted-* process).

| Sidecar | Result |
|---|---|
| vysted-sidecar (main, :63977) | `/health` OK; version OK (0.8.0); screener universe OK; ICONIKSPEV resolution OK (deterministic BSE identity); `/agents` roster OK (13 agents); `/mcp/status` OK (ready=true, toolCount=40); `/history/ICONIKSPEV` OK (27 EOD bars, provider=bse) |
| vysted-openbb-mcp-sidecar (:64568) | OK (bound, survived settle window) |
| vysted-sec-edgar-mcp-sidecar (:64737) | OK (bound, survived settle window) |
| BSE bhavcopy probe (no-SLA) | OK (endpoint reachable) |
| NSE direct probe (no-SLA) | OK (HTTP 200, 8 EOD rows) |

Teardown: all 3 spawned children (pid=76559, 77552, 77882) tree-killed cleanly via the run's own PID ledger. `[smoke] all sidecars booted cleanly.`

Final log line: `EXIT=0`

## Re-runs

None required — no stage failed on the first pass, so the "re-run once to distinguish flake from failure" rule was never triggered.

## Findings

None. See `findings/rc1-heavy.json` (empty array).
