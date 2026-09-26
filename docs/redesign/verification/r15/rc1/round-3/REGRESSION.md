# RC1 Gate Round 3 — Heavy Lane (ci-local + smoke)

Candidate sha: `01d6920a300b016ab1ad8aa436ee4e4586f8e336`
Worktree: `<scratch>/rc1-round-3-cand`
Command: `pnpm ci-local` (exact `package.json` script, no flags), run once via
`sh -c 'PATH="$PWD/sidecar/.venv/bin:$PATH" pnpm ci-local; echo EXIT=$?'`, detached, polled.
Log: `logs/ci-local.log` (1040 lines). Neither stage failed, so no rerun was needed.

## Per-stage results (exit codes / counts copied from the log)

| Stage | Result | Evidence |
|---|---|---|
| `pnpm install --frozen-lockfile` | PASS | lockfile up to date, `Done in 497ms` (line 15) |
| `ensure-all-sidecars.mjs` | PASS | all 3 binaries present and fresh, skipped rebuild (lines 16-22) |
| `pnpm lint` (eslint + design-token audit) | PASS | `design-token audit clean (373 files)` (line 27), no eslint errors printed |
| `pnpm format:check` (prettier) | PASS | `All matched files use Prettier code style!` (line 33) |
| `pnpm typecheck` (`tsc --noEmit`) | PASS | no diagnostics emitted (silent success) |
| `cargo fmt --check` | PASS | no diff emitted (silent success) |
| `cargo clippy --all-targets -- -D warnings` | PASS | `Finished dev profile ... in 41.29s` (line 339), zero `warning:`/`error:` lines |
| `ruff check sidecar` | PASS | `All checks passed!` (line 341) |
| `ruff format --check sidecar` | PASS | `444 files already formatted` (line 342) |
| `pnpm test` (vitest) | PASS | `Test Files 153 passed (153)`, `Tests 1849 passed (1849)` (lines 364-365) |
| `cargo test` | PASS | `test result: ok. 19 passed; 0 failed; 0 ignored` (lib), 2 further empty (0/0) test binaries, all `ok` (lines 633/639/645) |
| `pytest` (sidecar) | PASS | `3645 passed, 1 skipped, 4 warnings in 202.75s` (final line before `EXIT=0`) |

`EXIT=0` for the whole chained `ci-local` script (final log line).

Only pre-existing benign notices, none gating: pnpm's `Ignored build scripts: core-js@3.49.0`
warning, a `StarletteDeprecationWarning` (httpx/testclient) and a `DeprecationWarning`
(`streamable_http_client`) in 3 pytest tests (all counted in the "4 warnings", none a failure),
and jsdom's routine `Not implemented: Window's scrollTo()` / `navigation to another Document`
console noise during vitest (expected jsdom limitation, not a test failure).

## Smoke test

`node scripts/smoke-test-sidecars.mjs`, run once (no flags), log: `logs/smoke.log`.

| Sidecar | Result | Evidence |
|---|---|---|
| `vysted-sidecar` (main, :52986) | PASS | `/health` OK, screener universe OK, ICONIKSPEV resolution OK (deterministic BSE identity), `/agents` roster OK (13 agents), `/mcp/status` OK (ready=true, toolCount=40), `/history/ICONIKSPEV` OK (27 EOD bars, provider=bse), version OK (0.8.0) |
| `vysted-openbb-mcp-sidecar` (:53478) | PASS | bound, survived settle window |
| `vysted-sec-edgar-mcp-sidecar` (:53633) | PASS | bound, survived settle window |

Live-network no-SLA probes both passed: BSE bhavcopy endpoint reachable, NSE direct probe
HTTP 200 (8 EOD rows via curl_cffi).

Final line: `[smoke] all sidecars booted cleanly.` All 3 spawned children were fully torn down
via the run's own PID ledger (ATTENDED-SAFE mode) — no interaction with any pre-existing
`vysted-*` process, including the operator's own app.

## Summary

Both EXIT codes: `ci-local` = 0, `smoke-test-sidecars.mjs` completed clean (process exited,
final log line confirms all 3 sidecars booted and tore down cleanly). No regression, no chain
failure. `findings/rc1-heavy.json` is an empty array.
