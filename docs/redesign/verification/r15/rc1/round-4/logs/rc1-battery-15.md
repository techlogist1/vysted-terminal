# rc1-battery-15 — regression battery shard 15

Candidate: 1006c6da694ede5776c3dabbd27b305aeb56b5ad
Sidecar: :52355, cwd <cand>/sidecar, data dir rc1-round-4-data-rc1-battery-15
Sets: batch-4/set-13, batch-8/set-32, batch-11/set-52, batch-25/set-76

## Result

All 16 assigned entries re-checked against candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad:
- 12 holds (live curl / in-process python repros matching the certification's cited evidence exactly)
- 4 ci_pinned (jsdom/vitest component tests: R15-UI-030, R15-UI-029, R15-AGENT-053 — pinned test file/case located and read, not executed per the battery role's no-vitest rule)
- 0 regressed, 0 needs_gui, 0 blocked_env

One self-correction during the run: R15-AGENT-030's first attempt called `services.errors.humanize()` directly and got `code:"unknown"` (not a regression — wrong function). Re-read the register's own wording ("the exact guard `error_frame`") and re-ran against `error_frame()`, which matched the certification exactly (`code:"internal"`). Logged here per the harness's no-speculation rule.

One notable resolution issue during set-13: bare symbol `KSE` (no suffix) autocompletes to a coincidental NSE-listed `KSE.NS`, not the intended BSE-only scrip 519421 the R15-DATA-036 entry is about; re-ran against `KSE.BO` (confirmed via `/resolve?q=519421`).

One notable resolution issue during set-32: `/quotes/{symbol}` takes no `region` query param; region rides the `X-Vysted-Region` request header (a per-request ContextVar). R15-LEAD-005's ADR probes needed that header set to `US` to reach the yfinance-US lane at all.

Sidecar :52355 started and stopped cleanly (sleep-wrapper pid 94323/94325, python pid 94326).

Sets, findings, and raw probe outputs are under docs/redesign/verification/r15/rc1/round-4/battery/{set-13,set-32,set-52,set-76}.md and battery/raw/set-{13,32,52,76}/.

COVERAGE: 16/16 ids raw; no raw: none.
