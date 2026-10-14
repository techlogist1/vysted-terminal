# rc2 gate round 6-rc2 - heavy lane (ci-smoke)

Candidate sha: ace7dd768c3b809b0e72b20b20cfc94eea2368bd (HEAD verified).

## pnpm ci-local (exact script, venv PATH): EXIT=1 (run 1 logs/ci-local.log, re-run logs/ci-local-run2.log, identical, deterministic)
The chain is && chained and stopped at format:check; later stages did not run inside it.

| stage | in chain | result |
|---|---|---|
| install --frozen-lockfile | ran | exit 0 ("Already up to date") |
| ensure-all-sidecars | ran | exit 0 (3 sidecars present and fresh) |
| lint (eslint + design-token audit) | ran | exit 0 (design-token audit clean, 392 files) |
| format:check | ran | EXIT 1: `[warn] docs/redesign/BACKLOG_0.9.1.md` (only file flagged) |
| typecheck, cargo fmt, clippy, ruff check, ruff format, vitest, cargo test, pytest | not reached | see individual run below |

## Individual stages run afterwards (adjacent info, logs/ci-stages-individual.log, logs/vitest.log, logs/pytest.log; no fixes, no installs in the candidate)
- typecheck exit 0; cargo fmt exit 0; clippy -D warnings exit 0
- ruff check sidecar exit 0 (All checks passed); ruff format --check sidecar exit 0
- vitest: exit 0, 169 files, 2031/2031 tests passed
- cargo test: exit 0, 31 passed, 0 failed
- pytest: exit 0, 3921 passed, 1 skipped, 4 warnings (229.8 s). The candidate venv has no pytest/ruff (the chain's pip install steps were never reached), so pytest ran from a separate venv (scratchpad rc2-pytest-venv, requirements-dev.txt) with cwd candidate/sidecar and -p no:cacheprovider.

## smoke (node scripts/smoke-test-sidecars.mjs): EXIT=0 (logs/smoke.log)
    [smoke] vysted-sidecar: spawning on :57688 ...
    [smoke] vysted-sidecar /health OK (port=57688).
    [smoke] vysted-sidecar: probing screener universe endpoint ...
    [smoke] vysted-sidecar: probing ICONIKSPEV resolution (masters-only) ...
    [smoke] vysted-sidecar: probing /agents roster ...
    [smoke] vysted-sidecar: probing /mcp/status (own MCP integration) ...
    [smoke] vysted-sidecar: probing /history/ICONIKSPEV (no-SLA, live BSE) ...
    [smoke] vysted-sidecar version OK (0.9.0).
    [smoke] vysted-sidecar screener universe OK.
    [smoke] vysted-sidecar ICONIKSPEV resolution OK (deterministic BSE identity).
    [smoke] vysted-sidecar /agents roster OK (13 agents).
    [smoke] vysted-sidecar /mcp/status OK (ready=true, toolCount=39).
    [smoke] vysted-openbb-mcp-sidecar: spawning on :57960 (no-watchdog), probing port bind ...
    [smoke] vysted-openbb-mcp-sidecar OK (bound :57960, survived settle window).
    [smoke] vysted-sec-edgar-mcp-sidecar: spawning on :58012 (no-watchdog), probing port bind ...
    [smoke] vysted-sec-edgar-mcp-sidecar OK (bound :58012, survived settle window).
