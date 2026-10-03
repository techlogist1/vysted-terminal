# R15 final pass — chain regression (ci-local + sidecar smoke)

- **SHA under test:** d38b5d1a2487bd52fe8a7e741a3a5266e3206611 (scratch worktree `final-cand`, `git rev-parse HEAD` verified before the run)
- **Lane:** final-chain (Opus 5.5, effort high), run 2026-10-03 ~15:32–15:42 IST
- **Command:** `PATH="$PWD/sidecar/.venv/bin:$PATH" pnpm ci-local` (the package.json script, no flags), then `node scripts/smoke-test-sidecars.mjs`
- **Logs:** `logs/ci-local.log`, `logs/smoke.log`
- **Both green on the first run, so no re-run was needed** (the flake re-run rule applies only to a failing command).

## ci-local — EXIT=0

| Stage | Exit | Counts from the log |
|---|---|---|
| install (`pnpm install --frozen-lockfile`) | 0 | "Lockfile is up to date"; "Already up to date"; "Done in 556ms using pnpm v10.32.1" (warning: ignored build script core-js@3.49.0) |
| ensure-all-sidecars | 0 | all 3 (vysted-sidecar, openbb-mcp, sec-edgar-mcp) "present and fresh — skipping build"; nothing rebuilt, so the shared :52800-2 stack's binaries were not touched |
| lint (eslint + design-token audit) | 0 | eslint printed nothing; "design-token audit clean (392 files)" |
| format:check (prettier) | 0 | "All matched files use Prettier code style!" |
| typecheck (`tsc --noEmit`) | 0 | no output (clean) |
| cargo fmt --check | 0 | no output (clean) |
| clippy `--all-targets -D warnings` | 0 | "Finished `dev` profile ... in 40.61s", zero warnings |
| ruff check sidecar | 0 | "All checks passed!" (ruff 0.15.12) |
| ruff format --check sidecar | 0 | "453 files already formatted" |
| vitest run --coverage | 0 | "Test Files 169 passed (169)", "Tests 2032 passed (2032)"; coverage All files 81.27% stmts / 71.98% branch / 83.25% funcs / 81.4% lines |
| cargo test | 0 | lib unittests "32 passed; 0 failed; 0 ignored"; main unittests 0 tests; doc-tests 0 tests |
| pytest (sidecar) | 0 | "collected 3922 items"; "3921 passed, 1 skipped, 4 warnings in 231.47s" |

Notes on the run (not findings):
- pytest's 4 warnings are deprecation notices only (starlette testclient httpx; `streamable_http_client` in test_mcp_client / test_openbb_mcp_provider).
- The 1 skipped pytest test is not named in the log (ci-local runs pytest without `-rs`); recorded as is, not investigated further.
- `pip install -r requirements-dev.txt` installed pytest/pytest-asyncio/pluggy/iniconfig into the candidate venv during the run (part of the script itself).

## smoke-test-sidecars — EXIT=0

| Sidecar | Result |
|---|---|
| vysted-sidecar | /health OK; version OK (0.9.0 = package.json); screener universe OK; ICONIKSPEV resolution OK; **/agents roster OK (13 agents)**; **/mcp/status OK (ready=true, toolCount=39)**; /history/ICONIKSPEV OK (26 EOD bars, provider=bse) |
| vysted-openbb-mcp-sidecar | OK (bound ephemeral port, survived settle window) |
| vysted-sec-edgar-mcp-sidecar | OK (bound ephemeral port, survived settle window) |

Freshness gate: "all bundled sidecar binaries are newer than their source." Live-exchange probes skipped (no `--require-network`, the default). The run spawned and tore down only its own 3 children on ephemeral ports. The shared stack still answered /health on :52800 afterward.

## EXIT codes

- ci-local: **EXIT=0** (one run)
- smoke: **EXIT=0** (one run)

## Findings

None. `findings/chain.json` = `[]`.
