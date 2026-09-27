# rc1-battery-16 — regression battery shard 16 (gate round 4)

Candidate: 1006c6da694ede5776c3dabbd27b305aeb56b5ad (verified via `git rev-parse HEAD` on the
scratch worktree before starting).

Own sidecar booted at :52356, cwd `<cand>/sidecar`, data dir a fresh copy of
`rc1-round-4-seed-data` at `rc1-round-4-data-battery-16`, sleep-wrapper pid 94042 (killed at end
of shard). `/health` clean, `openbb-mcp: available`.

## Sets covered

- batch-5/W2-resolver-market-data (set-16.md): DATA-057, DATA-097, LEAD-011, DATA-063, DATA-015,
  DATA-037, LEAD-009, DATA-072 — all **holds**.
- batch-8/W5-agent-runtime-research (set-34.md): CODE-AGENT-004, LEAD-019, CODE-AGENT-007,
  CODE-AGENT-016, LIFECYCLE-014, CODE-RESEARCH-003 — all **holds**.
- batch-11/W6-options-chain (set-53.md): DATA-079 — **holds**.
- unplanned-1 (set-79.md): CODE-DATA-023 — **holds**.

## Method notes

- Live HTTP probes against my own sidecar for anything reachable that way (resolver, history,
  indicators, fundamentals, earnings, ratings, options chain, /health).
- In-process python calls against the candidate's `sidecar/.venv` for behaviour that needs
  time-travel, forced provider failures, or editing registry rows in memory — mirroring how the
  batch-5/8 verifiers themselves certified these entries (monkeypatched `time.monotonic`,
  monkeypatched `yfinance.Search`, forced `run_iter_research`/`run_heavy_research` to raise,
  edited `model_registry.default_base_url_for`, `_discover_specs` on a scratch agents dir).
- DATA-037: my first probe omitted `asset_class=crypto` (route defaults to `equity`) and got 502s
  from the equity fallback chain — a probe error, not a regression; corrected probe reproduced
  the exact cert numbers (30/365/1826 bars, ETH 720).
- LEAD-009: first probe hit a nonexistent `/fundamentals/{symbol}/rating` path (404); corrected
  to `/ratings` (the real route) and reproduced the cert's IN buy / US hold split exactly.
- DATA-079: NIFTY OI count (244 vs cert's 238) differs because this run's `as_of` is one trading
  day later (2026-09-25 vs 2026-09-24) — expected day-to-day drift, not a regression; contract
  count (276), RELIANCE (90), AAPL yfinance-with-IV, and the not-listed 404 shape all matched
  exactly.
- No vitest/pytest suites run (out of this role's scope; heavy lane owns them). No entry in this
  shard was certified only via a pinned test, so no `ci_pinned` verdicts.

## Result

0 regressions, 0 new defects, 16/16 entries hold. Stopped sidecar (killed sleep pid 94042) at end
of shard.

COVERAGE: 16/16 ids raw; no raw: none.
