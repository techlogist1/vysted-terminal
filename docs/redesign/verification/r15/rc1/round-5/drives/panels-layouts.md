# panels-layouts — owner-drive, gate round 5

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Own sidecar `127.0.0.1:52323` (source
worktree `rc1-round-5-cand`, data dir `rc1-round-5-data-panels-layouts`, seeded from the
round's shared keyless snapshot), sleep pid 35505, stopped at end of drive. Reads against the
shared `127.0.0.1:52152`; all writes (agent-builder CRUD, backtest run, workspace save/load)
against the own sidecar. No LLM lane needed — every row in this group is API/code-level.

Raw evidence: `docs/redesign/verification/r15/surface/panels-layouts/rc1/round-5/*` (files
`01`-`46`, `COVERAGE.json`). Census baseline: `docs/redesign/verification/r15/surface/
panels-layouts/{EVIDENCE.md,COVERAGE.json}` (Stage B, 2026-09-23).

## Scored table (20 rows, all panels+layouts rows in COVERAGE_SKELETON.json)

| Row | Score | Evidence | Census→rc1 delta |
|---|---|---|---|
| panel-chart | ok | 01,02,03 | broken→ok: 30m timeframe (0 bars for every symbol) now returns 286 bars for AAPL and RELIANCE.NS, indicators compute too. Fixed by **R15-DATA-064**. |
| panel-watchlist | ok | 23,24 | broken→ok: 20-name IN batch is 78s cold (one-time) but 0.013s warm (EOD cache), vs census's 23s-every-cycle starvation. Fixed by **R15-DATA-066**. |
| panel-news | partial | 19,19b | broken→partial: bare `BDL`/`BDL.NS` no longer returns Flanigan's Enterprises (US) headlines mistagged BDL — now 0 articles. Mistag gone; genuine-IN-coverage case not independently re-verified this round. |
| panel-equity-overview | ok | 18 | unchanged ok: keyless narrative honest. |
| panel-agent-builder | ok | 25-31 | partial→ok: full CRUD + 422 validation (unknown tool id) + 404-after-delete all correct; catalog now exposes ~50 tools (previous 20-of-50 drift not reproduced). |
| panel-backtest | ok | 32-35 | partial→ok: out-of-range `window=999` now a clean 422 ("must be between 5 and 200") instead of a silent 0-trade result. Fixed by **R15-UI-010**. mean_reversion produces 13 real trades; trend_following's 0 trades on SPY 2024-25 is a genuine no-signal result (default params), not a bug. |
| panel-broker-connect | NOT TESTED | — | out of scope (D81, removed_with_feature). |
| panel-broker-order-entry | NOT TESTED | — | out of scope (D81, removed_with_feature). |
| panel-macro | ok | 07,08 | broken→ok: all IMF catalog/series calls now 200 with real WEO projection data (was 404 for all 8 entries). Fixed. |
| panel-sec-filings | partial | 04,05,06 | broken→partial: sections viewer now returns real filing text (was `sections:[]`); insider list now returns 9 rows (was `[]`). Fixed by **R15-DATA-038**. But every insider row's economic fields are blank and Direction renders green for a null value — **new finding rc1-drive-panels-layouts:1**. |
| panel-earnings-calendar | ok | 09,10 | broken→ok: INFY now resolves to INFY.NS with EPS+revenue both INR (fixed, **R15-DATA-113**); reported_date≠period_end (fixed, **R15-LEAD-016**); the buggy quarter-label was removed outright rather than corrected (**R15-DATA-067**, confirmed by code read — no label left to mislabel). |
| panel-analyst-ratings | partial | 16,17,20,21,22 | broken→partial: AAPL (US) now shows real per-firm price targets and rating history (fixed, **R15-DATA-069**); RELIANCE.NS (IN) still shows only 1 Consensus point and empty trend/individual — read as a genuine yfinance IN-coverage gap (same code path, AAPL has the data and IN doesn't), not re-proven honest within budget. |
| panel-option-pricer | ok | 12,13,14 | broken→ok: binomial gamma/theta now within ~1% of Black-Scholes at 200 AND 201 steps (was 1.4-5.6x off or 0, wrong theta sign). Fixed by **R15-DATA-011**. |
| panel-greeks-dashboard | ok | 45 | unchanged ok. |
| panel-bond-pricer | ok | 46 | unchanged ok. |
| panel-yield-curve | broken | 15 | unchanged broken: duplicate-tenor pillar still 500s with no CORS header. Matches already-**open**, low-severity **R15-UI-077** (lows-triage confirmed `still_reproduces`); no fix round per this round's lead note — not re-filed. |
| layouts-arrange-templates | ok | 44 | unchanged ok: layout-templates.test.ts 100% pass. |
| layouts-macos-menu-bridge | NEEDS-GUI | — | GUI-only end-to-end (native menu + Tauri shell); handler logic already covered under layouts-arrange-templates. |
| layouts-workspace-save-load | ok | 36-43,44 | broken/partial→ok: colon name ("Research: X") now saves 200 (was 400); 300-char name now a clean 400 with a reason (was 500); a hand-corrupted file is listed then quarantined to `.corrupt-<ts>` on GET (fixed, **R15-DATA-090**) — the response is a plain 404 rather than a status naming the quarantine, an already-documented residual on that same fixed entry (its own round-3 note), not re-filed. workspace.test.ts 100% pass. |
| panel-context-publishers | ok | 44 | unchanged ok: panel-context-publishers.test.tsx 100% pass. |

## New finding this round

1. **SEC Insider tab renders filing-level rows as blank + a false-positive-green Direction**
   (medium, `rc1-drive-panels-layouts:1`). R15-DATA-038 fixed the *count* (0→9 rows for AAPL)
   but every row's reporter/shares/price/value/code field is still empty, and
   `InsiderTradingTable.tsx`'s Direction cell colours a `null` direction `text-positive`
   (green) with no visible text — a user scanning the tab sees a table of green-tinted blanks
   with no "no per-trade detail in this filing" explanation. See findings file for repro.

## Confirmed-still-open, not re-filed (already tracked, no fix round warranted this round)

- **R15-UI-077** (open, low) — yield-curve duplicate-pillar 500/no-CORS reproduces exactly as
  its own repro states. Lows-round item, per this gate round's lead note.
- **R15-DATA-090**'s own documented residual (fixed, medium) — corrupt-workspace GET answers a
  plain 404 rather than naming the quarantine; the quarantine mechanism itself (rename to
  `.corrupt-<ts>`) works correctly, confirmed live this round.

## Method notes

- Schemas for `/quant/option/price`, `/quant/option/greeks`, `/quant/bond/price`,
  `/quant/yield-curve`, `/custom-agents`, `/workspace`, `/sec/filings*` were read from
  `sidecar/models/quant.py`, `sidecar/routers/custom_agents.py` +
  `sidecar/models/custom_agent.py`, `sidecar/routers/workspace.py`,
  `sidecar/routers/sec_filings.py` before driving (several first attempts 422'd on a wrong
  guessed shape — corrected, evidence files show the corrected call only where noted).
  `/custom-agents` (not `/agents/custom`) and `/news?symbols=` (not `?symbol=`) are the actual
  routes/params, confirmed by router/api.ts source.
  `panel-watchlist`'s 78s "cold" figure is a one-time cache-miss cost by design (fix_shape),
  confirmed by the 0.013s warm re-run right after — not treated as a regression.
