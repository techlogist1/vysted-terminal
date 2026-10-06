# rc1-battery-19 — REGRESSION BATTERY shard 19 (Sonnet)

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd (verified via `git rev-parse HEAD` in the
scratch worktree before starting).

Sets: batch-3/W2-agent-frontend-gate (set-6, 7 ids), batch-7/W1-india-exchange-data (set-25, 6
ids), batch-29/W3-sonnet (set-83, 2 ids). 15 ids total.

## Setup

- Data dir: `cp -R rc1-round-5-recheck-seed-data -> rc1-round-5-recheck-data-battery-19`
  (own copy, keyless IN-profile snapshot).
- Own sidecar booted from the candidate's `sidecar/` source on :52359
  (`VYSTED_OPENBB_MCP_PORT=52153`, `VYSTED_SEC_EDGAR_MCP_PORT=52154` pointing at the shared
  read-only MCP subprocesses), `sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1
  --port 52359 --data-dir <own data dir>`, detached, sleep pid recorded and polled to `/health`
  ok in ~15s.
- Reused for all three sets; stopped at the end (sleep-wrapper pid killed, then the orphaned
  uvicorn worker pid killed directly — the sh|python pipe left the worker alive after the
  wrapper died, confirmed by a follow-up `/health` timeout and `ps` showing nothing on :52359).

## Method per set

- **set-6** (frontend/agent-gate defects): re-ran the pinned vitest files that cover each id
  (`pnpm exec vitest run <9 files>` — 173/173 passed) and, for the two R15-UI-001 sub-repros
  with no dedicated committed test (select-all+delete persistence, unmount-flush), read
  `NotesPanel.tsx`'s `flush()`/cleanup logic directly to confirm the fix (matches how batch-3's
  own certification treated those two as scratch checks, not committed tests).
- **set-25** (India exchange data): every id has a pure HTTP repro in the register — re-ran each
  one verbatim against the own sidecar (`curl` DAL/FUSION/JONJUA/TCS/AAPL fundamentals,
  DHANBANK income gaps, disclosures results/shareholding/announcements for
  JONJUA/DAL/CHTR/ELCIDIN/SIFY/AAPL) and diffed the live numbers against the register's/cert's
  stated figures (9.97 Cr, 1,714.42 Cr, 0.452 growth, 83.78% SIFY family control, etc.) —
  all matched exactly, in one case (SIFY 20-F) the live SEC fetch succeeded outright where
  batch-7's own certification had needed a workaround for a sec-edgar-mcp timeout.
- **set-83** (lifecycle/resolver): R15-LIFECYCLE-020's own live repro (`/system/provider-health`
  after boot) reproduced batch-29's cert exactly (circuit closed, opens_total=0); the two
  underlying source-level defects (boot-time region-blind sp500 warm loop, and the round-4
  refutation's shared-circuit-weight follow-up) were confirmed fixed by reading
  `screener.py`/`fundamentals_warm.py` (`_warm_follow_region`, `_WARM_THROTTLE_WEIGHT=0.0`).
  R15-LEAD-049 was re-run live (`/screener/run` nifty50 sweep, `/resolve?q=TATAMOTORS`,
  `/quotes/TMPV.NS`) and matched the cert's numbers (290.45, candidate order
  [TMPV,TMCV,TSLA]) exactly.

## Result

All 15/15 ids: **holds**. No regressions, no chain failures, nothing needed vitest/pytest as
the primary evidence (only the already-committed, already-passing pinned tests were re-run —
no full suite was executed by this shard, per the role's scope). No `ci_pinned`/`needs_gui`/
`blocked_env` verdicts.

COVERAGE: 15/15 ids raw; no raw missing.
