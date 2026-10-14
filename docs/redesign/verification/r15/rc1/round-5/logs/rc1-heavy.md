# rc1-heavy working log — gate round 5

- Confirmed candidate worktree HEAD == 9bc600ece2ce6343a6aa48f130d7620b1466bb98.
- Checked round-5 dir for a prior rc1-heavy attempt: none found (only gate8-role files existed: PREFLIGHT.md, gate8.json, GATE8.md, gate8/, findings/rc1-gate8.json, logs/preflight-*.log). Started this role fresh.
- Launched `pnpm ci-local` detached (PATH prefixed with sidecar/.venv/bin) -> logs/ci-local.log. Polled via short background waits + one Monitor watch. Completed EXIT=0 in ~4 min wall (cargo deps were largely pre-warmed from earlier preflight sidecar build).
  - vitest: 153 files / 1879 tests passed.
  - cargo test: 19 passed, 0 failed.
  - pytest: 3780 passed, 1 skipped, 229.70s.
  - No clippy/eslint/tsc/prettier/ruff diagnostics.
- Launched `node scripts/smoke-test-sidecars.mjs` detached -> logs/smoke.log. EXIT=0.
  - All 3 sidecars (main, openbb-mcp, sec-edgar-mcp) bound and tore down cleanly on ephemeral ports.
  - BSE bhavcopy probe non-200 (declared no-SLA/benign in the script's own log line).
  - NSE direct probe OK.
- Both commands green on first run — no flake re-run needed.
- Wrote REGRESSION.md, findings/rc1-heavy.json (empty — no chain failures).
