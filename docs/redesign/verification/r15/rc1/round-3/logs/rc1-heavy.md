# rc1-heavy working log — RC1 gate round 3

Candidate sha confirmed: `01d6920a300b016ab1ad8aa436ee4e4586f8e336` (matches
`git -C <scratch>/rc1-round-3-cand rev-parse HEAD`).

Found COMMON `PREFLIGHT.md` already complete for this round (pnpm install, sidecar builds,
seed data, shared stack boot, register counts) — not redone.

1. `pnpm ci-local` — exact package.json script, no flags — started detached via
   `sh -c 'PATH="$PWD/sidecar/.venv/bin:$PATH" pnpm ci-local; echo EXIT=$?' > logs/ci-local.log 2>&1 &`,
   polled with a Monitor + short spaced Bash calls (no single call over ~20s). Ran ~4.5 min
   total (install skip-fresh, eslint, prettier, tsc, cargo fmt, cargo clippy `-D warnings`,
   ruff check + format, vitest, cargo test, pytest). `EXIT=0`. Every stage passed — see
   `REGRESSION.md` for the per-stage table with line-number evidence.
2. `node scripts/smoke-test-sidecars.mjs` — started detached, no flags, polled the same way.
   All 3 sidecars (main :52986, openbb-mcp :53478, sec-edgar-mcp :53633) booted, passed their
   probes (health, screener universe, ICONIKSPEV resolution, /agents roster, /mcp/status,
   /history live BSE, BSE bhavcopy reachability, NSE direct probe), and were torn down cleanly
   by the run's own PID ledger. Final log line: `[smoke] all sidecars booted cleanly.`

Neither command failed, so the "rerun once on failure" rule did not apply — each ran exactly
once. No fix attempted (role is read-only/never-fix). No findings — `findings/rc1-heavy.json`
is `[]`.
