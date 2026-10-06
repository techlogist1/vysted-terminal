# rc1-battery-2 — regression battery shard 2, stage-c batch-4

Candidate sha `4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a`, scratch worktree `rc1-cand`
(read-only, sidecars pre-built). Own sidecar booted from `rc1-cand/sidecar` on
`127.0.0.1:52342`, data dir `rc1-data-rc1-battery-2` (copy of `rc1-seed-data`),
env `VYSTED_OPENBB_MCP_PORT=52153` / `VYSTED_SEC_EDGAR_MCP_PORT=52154`. Sleep
pid 98570 (wrapper bash 98568). `/health` returned `ok` in ~8s. Stopped by
killing pid 98570 at the end of the shard; confirmed no orphan and `/health`
unreachable after.

No prior-attempt work found for this shard (checked `battery/set-10..14.md`,
`battery/raw/set-10..14/`, `logs/rc1-battery-2.md`, `findings/rc1-battery-2.json`
— all absent at start). Fresh run, single pass, no restart needed.

## Dispatch

- set-10 (batch-4/W1-agent-runtime): R15-AGENT-011
- set-11 (batch-4/W2-workflow-backtest-feeds): R15-AGENT-011
- set-12 (batch-4/W3-chat-runs-mcp): (none)
- set-13 (batch-4/W4-market-data-gate): R15-UI-090
- set-14 (batch-4/W5-panels-screener): R15-UI-090

Both entries are two-part (sidecar half + frontend/portfolio half), per
`stage-c/batch-4/PLAN.md` and `VERDICTS.md`'s "Per-entry evidence" section
(read before each repro, not judged from the diff).

## R15-AGENT-011

- **Sidecar half (set-10): holds.** In-process unit call of
  `agent_runtime._auto_open_backtest_event` (candidate's own `.venv`):
  success payload `{"ok":true,"runId":"bt-check-1"}` emits the synthetic
  `open_panel {panel:"backtest", run_id:"bt-check-1"}` tool_use event with id
  `auto-backtest-call-1`; a failed-run payload emits `None`. Confirmed the
  call site is wired at `agent_runtime.py:2254-2255`. Live end-to-end check
  of the storage/retrieval half: `POST /backtest/run` (trend_following,
  AAPL) on the candidate sidecar completed a real run and
  `GET /backtest/runs/{id}` returned the full stored result — the same
  endpoint the frontend `loadRun` fetches.
  - Note: a 2024-dated backtest failed with "no data" from every provider —
    the seeded data only goes back to roughly Sep 2025 against the env's
    2026-09-25 clock. Not a regression (env/seed-data limitation); a
    2026-dated range succeeded immediately. Logged as an environment note,
    not a finding.
- **Frontend half (set-11): ci_pinned.** The original certification's live
  scratch-vitest evidence no longer exists (uncommitted, removed with its
  worktree). The only remaining coverage in the candidate is the committed,
  register-id-named test `src/lib/host-actions.test.ts` `describe("open_panel
  backtest run_id (R15-AGENT-011)")` — read in full, unweakened, asserting
  the same success/failure shapes VERDICTS.md describes. Did not execute it
  (vitest suites excluded per role instructions); confirmed by reading the
  test and the two code paths it exercises (`host-actions.ts:2007-2016`,
  `store/backtest.ts:331-347`), both intact.

## R15-UI-090

- **Sidecar half (set-13): holds.** Could not reproduce the exact live
  market-hours split from the original repro (13:32 EDT, US open/NSE
  closed) — re-run at 20:22 EDT / 05:52 IST finds both home markets closed.
  Instead verified the actual fix directly and more strongly: `GET
  /quotes/AAPL` and `GET /quotes/RELIANCE.NS` against the candidate,
  each under both `X-Vysted-Region: IN` and `X-Vysted-Region: US` — freshness
  is byte-identical regardless of session region (session region has zero
  effect). Code read confirms `routers/quotes.py:44` and
  `routers/history.py:117-119` both call `instrument_region(...)`, not
  `config.get_region()`, matching the certified fix.
- **Portfolio half (set-14): ci_pinned.** Same situation as AGENT-011's
  frontend half: the original jsdom scratch-render evidence is gone. Only
  remaining coverage is the committed, register-id-named test
  `src/modules/portfolio/PortfolioPanel.test.tsx:240` (`it("R15-UI-090: an
  eod quote renders a staleness cue on its holding row")`), read in full,
  unweakened. Render path (`PortfolioPanel.tsx:91-102`, `StalenessBadge` from
  `quote.freshness`) confirmed intact and fed by the sidecar-half fix
  verified live in set-13.

## Findings

None. All four half-entries hold in the candidate (two by direct live repro,
two by an intact, unweakened, register-id-named pinned test after the
original scratch evidence was legitimately removed with its worktree). No
regression, no chain failure, no gate-8 concern.

## 2026-09-26 07:07 IST — shard complete

All 13 assigned sets (set-10..14, set-56..63) written, covering all 62 unique
register ids across batch-4 (W1-W5) and batch-12 (W1-W8). Own sidecar :52342 on
data dir rc1-data-battery-2 used throughout. No regressions found: 55 holds,
5 ci_pinned (CODE-PLATFORM-012/014, UI-018/020, CODE-PLATFORM-013 — vitest-only
certs, pinned tests confirmed present+unweakened by code read), 1 needs_gui
(LIFECYCLE-008), 1 blocked_env-adjacent-but-not (DATA-022 hit a live BSE 403 on
this IP but the certified honest-502 mechanism itself was directly observed,
so verdict holds not blocked_env). findings/rc1-battery-2.json is [] (no
regressions). Stopping own sidecar (sleep pid 63022) now.
