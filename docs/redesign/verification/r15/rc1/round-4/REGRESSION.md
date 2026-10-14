# RC1 Gate Round 4 — CI/Smoke Regression (rc1-heavy)

Candidate sha: `1006c6da694ede5776c3dabbd27b305aeb56b5ad`
Worktree: `rc1-round-4-cand` (scratchpad)
Run 1 of each command (no flake re-run needed — both passed clean on the first attempt).

## `pnpm ci-local` — logs/ci-local.log — EXIT=0

| Stage | Result | Notes |
|---|---|---|
| install (`--frozen-lockfile`) | PASS | |
| ensure-all-sidecars | PASS | all 3 sidecar binaries present and fresh, no rebuild needed |
| lint (eslint + design-token audit) | PASS | design-token audit clean (373 files) |
| format:check (prettier) | PASS | all matched files use Prettier style |
| typecheck (tsc --noEmit) | PASS | no errors |
| cargo fmt --check | PASS | no diff |
| cargo clippy -D warnings | PASS | `Finished dev profile ... in 38.64s`, zero warnings |
| ruff check sidecar | PASS | "All checks passed!" |
| ruff format --check sidecar | PASS | "444 files already formatted" |
| vitest (pnpm test) | PASS | Test Files 153 passed (153); Tests 1849 passed (1849); Duration 26.77s |
| cargo test (src-tauri) | PASS | 19 passed; 0 failed (plus two empty doctest/unit suites, 0/0) |
| pytest (sidecar) | PASS | 3657 passed, 1 skipped, 4 warnings in 201.69s |

Overall: `EXIT=0`. Zero failures across all 12 stages. No flake re-run was needed.

## `node scripts/smoke-test-sidecars.mjs` — logs/smoke.log — EXIT=0

ATTENDED-SAFE mode: ephemeral ports, own PID ledger, zero interaction with the operator's live app.

| Sidecar | Result |
|---|---|
| vysted-sidecar (main) | OK — `/health`, screener universe, ICONIKSPEV resolution, `/agents` roster (13 agents), `/mcp/status` (ready=true, toolCount=40), `/history/ICONIKSPEV` (26 EOD bars, live BSE), version 0.8.0 |
| vysted-openbb-mcp-sidecar | OK — bound :51725, survived settle window |
| vysted-sec-edgar-mcp-sidecar | OK — bound :51824, survived settle window |
| BSE bhavcopy probe | WARN (no-SLA, not a failure) — did not return 200; documented benign (weekend/holiday/geo-fence/no outbound network) |
| NSE direct probe | OK — HTTP 200, 7 EOD rows |

`all sidecars booted cleanly.` All 3 spawned children torn down cleanly. `EXIT=0`.

## Verdict

No regressions found. Both stages green on the candidate sha on the first run.
