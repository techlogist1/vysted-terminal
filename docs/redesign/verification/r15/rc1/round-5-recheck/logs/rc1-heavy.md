# rc1-heavy — working log

Candidate sha verified: `949c3c9fd49d61ecadc9813a8321bcdfd81178bd` (matches
`git -C <worktree> rev-parse HEAD`).

1. `pnpm ci-local` started detached (`sh -c 'PATH="$PWD/sidecar/.venv/bin:$PATH" pnpm ci-local; echo EXIT=$?'`)
   in the candidate worktree, exactly as the package.json script (no flags, no --force).
   Polled `logs/ci-local.log` in short calls until `EXIT=`.
   Result: `EXIT=0`. Full stage breakdown in `REGRESSION.md`.
2. `node scripts/smoke-test-sidecars.mjs` started detached the same way into
   `logs/smoke.log`, polled to `EXIT=`.
   Result: `EXIT=0`. All 3 sidecars booted, health-checked, torn down cleanly (own PID
   ledger only, never touched the operator's running app or any pre-existing vysted-*
   process).

Neither command failed, so neither was re-run (spec only calls for a re-run to
disambiguate flake vs failure).

No fixes attempted (role is verification-only). See `REGRESSION.md` for the full report.
