# rc1-battery-22 — regression battery shard 22, gate round 5

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98` (verified via `git rev-parse HEAD` in the shared candidate
worktree). Booted own sidecar on `:52362` from `<cand>/sidecar` against a fresh copy of `rc1-round-5-seed-data`
(`rc1-round-5-data-rc1-battery-22`), sleep-launcher pid 68950 / worker pid 68953, both killed at end.

Sets covered (15 entries total, 15/15 with raw evidence):

- **batch-5/W2-resolver-market-data (set-16)**: R15-DATA-015, R15-DATA-037, R15-DATA-057, R15-DATA-072,
  R15-DATA-097, R15-LEAD-009, R15-LEAD-011 — all **holds**.
- **batch-8/W3-data-error-honesty (set-31)**: R15-AGENT-030, R15-AGENT-061, R15-DATA-081, R15-LEAD-005 — **holds**;
  R15-UI-029, R15-UI-030 — **ci_pinned** (React-component-level repros pinned by named vitest tests; this role does
  not run vitest suites and no non-vitest render harness was available).
- **batch-27/W1-sonnet (set-73)**: R15-DATA-117, R15-LEAD-040 — both **holds**.

Notable re-probes beyond a plain curl:

- R15-DATA-015: the candidate now serves ELCIDIN's 52-week high/low as `status:"ok"` with the exact screener.in
  values (144500.0 / 87003.0), unflagged — an improvement on batch-5's certified "flagged, honest outcome" state,
  not a regression.
- R15-DATA-072: drove `provider_health` into an open breaker state in-process (3x `record_rate_limited`), then
  called the real `yfinance_provider.get_history` — confirmed one successful call closes it.
- R15-DATA-097: mocked `time.monotonic` in-process to fast-forward 301s past the empty-result TTL and confirmed a
  fresh live-lookup call is issued (not served from the stale empty cache entry).
- R15-LEAD-009 / R15-LEAD-011: region and index-symbol probes required the `X-Vysted-Region` HEADER (the router has
  no `region` query param) — an initial query-param attempt silently no-op'd and would have misread as a
  regression; corrected before judging.
- R15-LEAD-040: re-ran the concurrency storm live (16 concurrent cold `/resolve` + `/resolve/autocomplete`) against
  the own sidecar; the unrelated `/quotes/AAPL` call took 1.80s (pre-fix register baseline ~9.4s) — no starvation.

No regressions found in this shard. No new defects found outside the register.

COVERAGE: 15/15 ids raw; no raw: none.
