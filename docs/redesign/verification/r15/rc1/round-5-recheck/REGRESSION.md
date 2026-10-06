# RC1 gate round 5-recheck — heavy lane (ci-local + smoke)

candidate sha: `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`
worktree: `rc1-round-5-recheck-cand`
logs: `logs/ci-local.log`, `logs/smoke.log`

## pnpm ci-local — EXIT=0

Exact script (unmodified, no flags): install → ensure-all-sidecars → lint → format:check →
typecheck → cargo fmt --check → cargo clippy -D warnings → ruff check → ruff format --check →
pnpm test (vitest) → cargo test → pytest.

| stage | exit | notes |
|---|---|---|
| install (`--frozen-lockfile`) | ok | `Already up to date`, `Done in 627ms` |
| ensure-all-sidecars | ok | all 3 binaries present+fresh, skipped rebuild |
| lint (eslint + design-token audit) | ok | `design-token audit clean (373 files)` |
| format:check (prettier) | ok | `Checking formatting...` → no diffs reported |
| typecheck (tsc --noEmit) | ok | no errors emitted |
| cargo fmt --check | ok | no diffs reported |
| cargo clippy -D warnings | ok | `Finished \`dev\` profile ... in 41.35s`, no warnings/errors |
| ruff check sidecar | ok | `All checks passed!` |
| ruff format --check sidecar | ok | `444 files already formatted` |
| pnpm test (vitest) | ok | `Test Files 153 passed (153)` / `Tests 1881 passed (1881)` |
| cargo test | ok | `test result: ok. 19 passed; 0 failed` (lib) + 0/0 doc-tests x2 |
| pytest (sidecar) | ok | `3784 passed, 1 skipped, 4 warnings in 226.75s (0:03:46)` — 3785 collected, 0 failed |

Overall chain: `EXIT=0`. Zero FAILED/ERROR lines anywhere in the full log. Not re-run (no
failure to disambiguate from a flake).

Disclosures-area tests relevant to the R15-LEAD-059 fix (`test_b7_exchange_disclosures.py`,
`test_disclosures_router.py`, `test_research_disclosures.py`, `test_corporate_disclosures.py`)
all passed with no failures — consistent with the fix holding under the full suite, not just
its own stated repro (checked separately by the battery lane).

## node scripts/smoke-test-sidecars.mjs — EXIT=0

ATTENDED-SAFE mode: fresh ephemeral ports, own PID ledger only, zero interaction with the
operator's running app.

| sidecar | port | result |
|---|---|---|
| vysted-sidecar (main) | 58367 | `/health` OK; screener universe OK; ICONIKSPEV resolution OK (deterministic BSE identity); `/agents` roster OK (13 agents); `/mcp/status` OK (ready=true, toolCount=40); `/history/ICONIKSPEV` OK (26 EOD bars, provider=bse); version OK (0.8.0) |
| vysted-openbb-mcp-sidecar | 58681 | OK (bound, survived settle window) |
| vysted-sec-edgar-mcp-sidecar | 58754 | OK (bound, survived settle window) |

No-SLA probes: BSE bhavcopy returned non-200 (explicitly flagged no-SLA/benign — weekend/geo-fence/publish-timing, not investigated per the script's own guidance since the URL shape is unchanged); NSE direct probe OK (HTTP 200, 7 EOD rows).

`[smoke] all sidecars booted cleanly.` All 3 spawned children torn down cleanly by the run's
own PID ledger. Not re-run (no failure).

## Findings

None. Both stages exit 0 with zero FAILED/ERROR signatures. No chain-kind findings filed.
