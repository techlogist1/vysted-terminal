# RC1 gate round 5 — ci-local + smoke (rc1-heavy)

Candidate sha: `9bc600ece2ce6343a6aa48f130d7620b1466bb98`
Worktree: `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-5-cand`
Ran once each (no flake re-run needed — both green first pass).

## `pnpm ci-local` — EXIT=0

Log: `logs/ci-local.log` (1042 lines).

| Stage | Result |
|---|---|
| install (`pnpm install --frozen-lockfile`) | ok |
| ensure-all-sidecars | ok — "freshness gate: all bundled sidecar binaries are newer than their source" seen later in smoke, sidecars built clean here too |
| lint (`eslint . && audit-design-tokens.mjs`) | ok, 0 problems |
| format:check (`prettier --check .`) | ok |
| typecheck (`tsc --noEmit`) | ok |
| cargo fmt --check | ok (no diff output) |
| cargo clippy --all-targets -- -D warnings | ok, 0 warnings |
| ruff check sidecar | ok |
| ruff format --check sidecar | ok |
| vitest (`pnpm test`) | **Test Files 153 passed (153)**, **Tests 1879 passed (1879)** |
| cargo test | **19 passed; 0 failed** (plus two empty 0/0/0 suites) |
| pytest (sidecar) | **3780 passed, 1 skipped**, 4 warnings, 229.70s |

No failing test IDs, no clippy/eslint/tsc diagnostics anywhere in the log.

## `node scripts/smoke-test-sidecars.mjs` — EXIT=0

Log: `logs/smoke.log`.

- ATTENDED-SAFE mode, ephemeral ports, no pre-existing `vysted-*` process touched.
- vysted-sidecar (:57019): `/health` OK, screener universe OK, ICONIKSPEV resolution OK (BSE identity), `/agents` roster OK (13 agents), `/mcp/status` OK (ready=true, toolCount=40), `/history/ICONIKSPEV` OK (26 EOD bars, provider=bse).
- vysted-openbb-mcp-sidecar (:57572): bound, survived settle window.
- vysted-sec-edgar-mcp-sidecar (:57717): bound, survived settle window.
- BSE bhavcopy probe: non-200 (declared no-SLA/benign — weekend/holiday/geo-fence, URL shape unchanged).
- NSE direct probe: HTTP 200, 7 EOD rows, OK.
- All 3 spawned children fully torn down (pids 21757 / 22130 / 22386).

Both EXIT codes: ci-local=0, smoke=0.

## Findings

None. No chain (ci-local/smoke) failures on this candidate.
