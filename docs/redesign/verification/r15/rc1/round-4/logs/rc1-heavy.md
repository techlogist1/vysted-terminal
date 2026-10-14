# rc1-heavy — gate round 4 log

- Confirmed candidate worktree HEAD = `1006c6da694ede5776c3dabbd27b305aeb56b5ad` (matches gate facts).
- No prior round-4 rc1-heavy artifacts found; started fresh.
- Ran `pnpm ci-local` (with sidecar venv on PATH) detached in the candidate worktree, polled via Monitor/background sleeps. Total wall time ~13 min (install/ensure-sidecars fast since binaries fresh; cargo fmt/clippy build ~1m40s; vitest 27s; cargo test build + run; pytest 3658 items, ~3m30s, includes some live-network tests e.g. test_keyless_backend which ran slower than others).
- ci-local: EXIT=0. All 12 stages passed on first attempt — no flake re-run needed. See REGRESSION.md for the per-stage breakdown copied from the log.
- Ran `node scripts/smoke-test-sidecars.mjs` detached, polled via Monitor. All 3 sidecars (main, openbb-mcp, sec-edgar-mcp) bound and passed their probes; BSE bhavcopy probe returned a documented benign WARN (no-SLA); NSE direct probe OK. EXIT=0, clean teardown of all 3 spawned children (ATTENDED-SAFE, ephemeral ports, own PID ledger — no interaction with operator's live app).
- No regressions, no chain failures. findings/rc1-heavy.json is an empty array.
