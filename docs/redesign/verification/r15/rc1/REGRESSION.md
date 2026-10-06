# RC1 Regression — ci-local + smoke (rc1-heavy)

Candidate sha: 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2
Worktree: rc1-cand (scratchpad), sidecar/.venv present, sidecars pre-built and fresh.

Note: on entry, logs from a prior attempt of this role were already on disk
(logs/ci-local.log, logs/smoke.log, both EXIT=0). Verified both ran the exact
unmodified `pnpm ci-local` script (no flags/force) to completion and the exact
smoke-test script, and both are complete and consistent — no re-run needed.

## `pnpm ci-local` — logs/ci-local.log — EXIT=0

Ran verbatim: `pnpm install --frozen-lockfile && node scripts/ensure-all-sidecars.mjs
&& pnpm lint && pnpm format:check && pnpm typecheck && cargo fmt --check &&
cargo clippy --all-targets -- -D warnings && ruff check sidecar && ruff format --check
sidecar && pnpm test && cargo test && cd sidecar && pytest`

| Stage | Result |
|---|---|
| install (--frozen-lockfile) | OK, lockfile up to date |
| ensure-all-sidecars | all 3 sidecars present and fresh — skipped rebuild |
| lint (eslint .) | clean, no output = 0 problems |
| format:check (prettier --check .) | "All matched files use Prettier code style!" |
| typecheck (tsc --noEmit) | clean, no errors |
| cargo fmt --check | clean (no diff printed) |
| cargo clippy --all-targets -D warnings | `Finished dev profile ... in 43.62s`, 0 warnings emitted |
| ruff check sidecar | "All checks passed!" |
| ruff format --check sidecar | "438 files already formatted" |
| vitest (pnpm test) | Test Files 152 passed (152), Tests 1824 passed (1824) |
| cargo test | lib.rs: 19 passed; 0 failed. main.rs: 0/0 (no tests) |
| pytest (sidecar) | 3129 passed, 1 skipped, 4 warnings, 205.61s |

Overall: `EXIT=0`

## `node scripts/smoke-test-sidecars.mjs` — logs/smoke.log — EXIT=0

- vysted-sidecar: spawned :63977, `/health` OK, version 0.8.0
- screener universe OK; ICONIKSPEV resolution OK (deterministic BSE identity)
- `/agents` roster OK (13 agents); `/mcp/status` OK (ready=true, toolCount=40)
- `/history/ICONIKSPEV` OK (27 EOD bars, provider=bse)
- vysted-openbb-mcp-sidecar: bound :64568, survived settle window — OK
- vysted-sec-edgar-mcp-sidecar: bound :64737, survived settle window — OK
- BSE bhavcopy probe OK (endpoint reachable); NSE direct probe OK (HTTP 200, 8 EOD rows)
- ATTENDED-SAFE teardown: all 3 spawned children reaped by this run's own PID ledger,
  zero interaction with any pre-existing vysted-* process.

Overall: `EXIT=0`

## Findings

None. No re-run needed (both logs already complete, no ambiguity/flake to disambiguate).
