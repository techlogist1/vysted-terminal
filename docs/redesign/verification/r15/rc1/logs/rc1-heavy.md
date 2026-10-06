# rc1-heavy working log

- Role: HEAVY-LANE OWNER, lane ci-smoke, sha 4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a, branch 004-r4-experience-rebuild.
- Verified candidate worktree (rc1-cand) HEAD matched expected sha, tree clean, before starting.
- Checked for a prior rc1-heavy attempt (logs/findings dirs) — none found; started fresh.
- Ran `pnpm ci-local` (unmodified package.json script, no flags/--force) detached via
  `nohup sh -c 'PATH="$PWD/sidecar/.venv/bin:$PATH" pnpm ci-local; echo EXIT=$?' > logs/ci-local.log 2>&1 &`,
  polled with separate short sleep+tail/ps calls per the harness stall rule (no combined sleep+check calls).
  Completed EXIT=0, all 12 stages passed on first attempt — no re-run needed.
- Ran `node scripts/smoke-test-sidecars.mjs` the same detached-and-poll way into logs/smoke.log.
  Completed EXIT=0 — all 3 bundled sidecars booted, probed, and tore down cleanly in ATTENDED-SAFE mode.
- During polling, briefly misjudged elapsed wall-clock time on the smoke test's sec-edgar-mcp
  probe (thought it might be stalling); cross-checked with `date` + `ps -o pid,lstart,etime`
  which showed normal elapsed time — no actual issue, process was healthy and completed shortly after.
- Extracted exact stage counts/exit lines directly from ci-local.log via targeted grep
  (install, lint, typecheck, cargo fmt, clippy, ruff check/format, vitest, cargo test
  lib+main.rs+doctests, pytest) — see REGRESSION.md for the full table.
- Zero failures observed anywhere in either log. No `chain`-kind findings to report;
  findings/rc1-heavy.json is an empty array.
- No fixes attempted (out of scope for this lane — observer/reporter only).
- Wrote REGRESSION.md, findings/rc1-heavy.json (empty), and this log; proceeding to
  StructuredOutput.
