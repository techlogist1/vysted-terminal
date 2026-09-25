# rc1-battery-0 working log

Role: REGRESSION BATTERY shard 0 (Sonnet), stage-c batch-2, sets W1-W5.

## Setup
- Own sidecar booted from `rc1-cand` (sha 4097dac4) source, data dir = copy of
  `rc1-seed-data` at `rc1-data-rc1-battery-0`, port **52340**, sleep pid **73481**
  (`nohup bash -c "sleep 86400 | .venv/bin/python3 main.py --host 127.0.0.1 --port 52340
  --data-dir <data> > <log> 2>&1"`), against shared `openbb-mcp :52153` / `sec-edgar-mcp
  :52154`, read-only.
- Health confirmed ok immediately; Yahoo circuit flapped OPEN/CLOSED for the first ~5 min
  (the sidecar's own boot-time bulk NSE fundamentals warm job hammering yfinance —
  429s), cleared on its own; retried affected entries (SIFY, DHANBANK) after ~90s wait,
  both resolved cleanly on retry.

## Sets completed
- `battery/set-0.md` — W1 fundamentals-seam: 6/6 holds.
- `battery/set-1.md` — W2 instrument-identity: 7/7 holds.
- `battery/set-3.md` — W4 workspace-persistence: 1 holds (R15-CODE-FRONTEND-004, live
  curl), 6 ci_pinned (entries whose original certification drove `src/lib/workspace.ts`
  in-process against a live sidecar / a scratch vitest — not curl-able; named against the
  committed pinning test per the "never run vitest suites" rule).
- `battery/set-4.md` — W5 surfaces-and-math: 5/9 holds (backtest `_compute_metrics`
  Sharpe/Sortino R15-DATA-009/010 reimplemented from `test_backtest_engine.py`'s own
  helpers in-process; options Greeks parity R15-DATA-011; SEC filings 404-not-fabricate
  R15-DATA-007; screener cross-currency ranking R15-DATA-043 live via `/screener/run`),
  4/9 ci_pinned (earnings/analyst currency labeling, portfolio CSV export currency column,
  `buildPortfolioSummary` concentration/weight contract nulling, bond pricer currency
  prefix — all frontend-rendering entries with a named committed vitest pin, no HTTP repro).
  Notable near-miss during R15-DATA-010: my first `_curve_from_returns` reimplementation
  omitted the test helper's leading baseline equity-curve point, producing a self-consistent
  but wrong Sortino (5.294 vs the certified 6.3521) — re-read the full helper (not a
  truncated slice) and corrected before concluding anything; recorded as a self-check
  lesson, not a finding (bug was in my repro script, not the candidate).
- `battery/set-2.md` — W3 research-integrity: COMPLETE, 8/8 holds (RESEARCH-002/034/015
  code-check, RESEARCH-037, RESEARCH-029, RESEARCH-001b live BDL deep-research on
  gpt-4o-mini, RESEARCH-003 live Blue Star deep-research on gpt-4o-mini, RESEARCH-004 live
  Kaynes ULTRA on local llama3.1:8b — 626.9s, the original repro's exact lane per
  VERDICTS.md; cross-check reads "14.5%" intact, "checked 2 numeric claim(s): 0 verified,
  2 unverified, 0 disagreement(s)" matches the 2 UNVERIFIED rows actually rendered, no
  mangled figure, no false-agree/false-disagreement-count).

## Sets complete: all 5/5 (set-0, set-1, set-2, set-3, set-4).
37/37 register entries covered: 27 holds, 10 ci_pinned, 0 regressed, 0 needs_gui,
0 blocked_env (the SIFY/DHANBANK Yahoo-429 flapping at boot was transient
self-inflicted load, resolved on retry within ~90s, not counted blocked_env).

## Method notes
- Repro method per entry followed the register's own `repro` field: curl for HTTP-shaped
  repros, in-process python (candidate `.venv`, imported modules directly, no pytest
  runner) for code-level repros (correctness_gate, news_provider parsing, symbol_resolver,
  ownership/market-cap/range witness `is_applicable`), grep for design-level entries.
- Never ran `pytest`/`vitest` suites; entries whose ONLY original certification method was
  driving frontend TS modules (which would require a jsdom/vitest harness to replicate)
  are `ci_pinned`, naming the specific committed test/describe block that now asserts the
  behavior (all confirmed present in the diff at `806a90c`).
