# rc1-drive-panels-layouts — gate round 3 re-drive

Candidate `01d6920a300b016ab1ad8aa436ee4e4586f8e336`. Own sidecar `127.0.0.1:52323`
(sleep pid 86782, worker pid 86785), source `<worktree>/sidecar`, data dir a fresh
`cp -R` of `rc1-round-3-seed-data`, pointed at the **shared, read-only** MCP pair on
`:52153` (openbb) / `:52154` (sec-edgar) — no separate MCP subprocesses spawned for
this role, since both are read-only fetchers and the shared pair is already up per
the gate facts; all writes (workspace saves) went through my own `:52323` sidecar/
data-dir, never through the shared stack. Method: direct `sidecar/routers/*.py` +
`sidecar/models/*.py` reads for each route/body shape, then plain `urllib` GET/POST
against `:52323` (two scripts, `rc1-drive-1.jsonl` / `rc1-drive-2.jsonl` in this
evidence dir), read back before claim.

Census baseline: `docs/redesign/verification/r15/surface/panels-layouts/EVIDENCE.md`
(2026-09-23) filed 9 new findings (SURF-PANELS-LAYOUTS-1..9); the register resolved
8 of them **fixed** (R15-DATA-011/028/029/038/064/065/066/067, R15-UI-053) and left
one **open, low** (R15-UI-077, yield-curve duplicate pillar). This drive targeted a
regression check on the 8 fixed rows plus a live confirm that UI-077 is still open,
across the panels this round's budget allowed (not the full 20-row group — see
`COVERAGE.json`'s `NOT TESTED` rows for what carried forward from census unchanged).

## Scored deltas (census -> rc1 round 3)

| Register id | Census finding | Census score | rc1 r3 re-check | Result |
|---|---|---|---|---|
| R15-DATA-064 (fixed) | Chart 30m dead every symbol | broken | `chart-30m-aapl`/`chart-30m-reliance` -> 200, real intraday bars, US+IN | **holds** |
| R15-DATA-065 (fixed) | Weekly/monthly freshness badge wrong | broken(part) | `/history/AAPL?timeframe=1wk` -> `freshness:"eod"` on a 5-day-old bar mid-period, not "stale" | **holds** |
| R15-DATA-029/062 (fixed) | `.NS` quotes never join in batch | broken | `quotes-batch-ns` -> RELIANCE.NS+TCS.NS join with real INR prices | **holds** (throttle-starves-other-routes half of DATA-066 not re-exercised under concurrency) |
| R15-DATA-029 (fixed) | News/ratings dead for IN symbols | broken | `news-symbols-infy` relevant articles rank in; `ratings-reliance` populated consensus/targets | **holds** |
| R15-DATA-038 (fixed) | SEC sections/insider always empty | broken | `sec-detail-real`/`sec-sections-real` -> real 10-K Business/Risk-Factors text; `sec-insider-aapl` -> rows now present (empty per-trade fields on these accessions are the documented filing-level fallback, `services/sec_filings_provider.py:437-438`, not a parser miss) | **holds** |
| R15-DATA-007 (fixed) | SEC detail fabricates identity for a fake accession | (confirmed live, no new id) | `sec-detail-fake-with-identifier` -> honest 404 `not_found`, no fabricated metadata | **holds** |
| R15-DATA-067 (fixed) | Earnings quarter label off-by-one | broken | Same repro (JPM 10-13, TSLA 10-22, INFY.NS 10-23) -> `fiscal_period: null` instead of a wrong label (honest-null fix shape) | **holds** |
| R15-DATA-028 (fixed) | Earnings default = 10 US mega-caps only | broken | `earnings-upcoming-60d`/`-default` include IN names (DEEPA.NS etc.), not US-only | **holds** |
| R15-UI-053 (fixed) | Macro IMF tab 100% dead, incl. only India series | broken | `macro-catalog-imf` populated; direct fetch of the US series AND the India series (`WEO/IND.NGDP_RPCH.A`) both -> 200 with real observations | **holds** |
| R15-DATA-011 (fixed, critical) | Binomial gamma 0-at-odd-steps / theta sign flip | broken | `quant-binomial-200` gamma 0.02759 vs `quant-binomial-201` gamma 0.02752 (no parity flip); theta negative for a long call (correct sign) | **holds** |
| R15-CODE-FRONTEND-004 (fixed) | `Research: X` workspace name rejected | broken | `workspace-save-colon-name` -> 200 saved | **holds** |
| (workspace-layout-7, folded into CODE-FRONTEND-019 area) (fixed) | 300-char workspace name -> 500 | broken | `workspace-save-300char` -> clean 400 `"...too long to save"` | **holds** |
| R15-UI-077 (open, low) | Duplicate yield-curve pillar crashes | broken | `yieldcurve-dup-pillar` -> still 500, no CORS header | **still broken, as documented** (no fix round warranted per the lead note) |
| R15-UI-003 (fixed) | Agent Builder hard-codes 20-of-50 tool vocab | broken(part) | `GET /custom-agents/tool-ids` -> 56 ids (full backend catalog); frontend render not re-checked (browser-only) | **backend half holds** |

## Regressions

None found. Every register-fixed row this drive could reach re-verified live on the
round-3 candidate.

## New defects

None found. The one thing that looked suspicious on first read — SEC insider rows
carrying blank `reporter_name`/`shares`/`price_per_share`/`direction` — is the
codebase's own documented fallback (`_insider_rows_from_payload`,
`sec_filings_provider.py:437-438`: "a filing-level row carries no trade to
classify... kept with its filing date and a null direction/shares") for accessions
where sec-edgar-mcp's own upstream payload is filing-level only, not a parser
regression; Apple's current Form-4 filings in this data window are exactly that
case. Two of my own probes (`sec-detail-fake-accession` in the first script,
`quant-bs-baseline`, bond-pricer, greeks-dashboard) were malformed requests
(wrong/missing required fields against the actual pydantic models) rather than
product defects — corrected where the budget allowed (`drive2.jsonl`), left
`NOT TESTED` with the reason where it did not (`COVERAGE.json`).

## Not tested this round (budget)

`panel-equity-overview`, `panel-backtest` (beyond the strategies list), `panel-
greeks-dashboard`, `panel-bond-pricer`, `panel-context-publishers`, `layouts-
arrange-templates` — carried forward at their census score; no register-fix or
regression signal pointed at these this round. `layouts-macos-menu-bridge` is
GUI-only per the skeleton. `panel-broker-connect`/`panel-broker-order-entry` are
`removed_with_feature` (trading out of product).

## Sidecar stop

Stopped by killing sleep pid `86782`; the worker pid `86785` did not exit on stdin EOF within a few seconds (unlike the shared-stack pattern), so it was killed directly too (both are this drive's own dedicated processes, not the shared `:52152-54` stack) -- port `52323` confirmed freed (`/health` unreachable).
