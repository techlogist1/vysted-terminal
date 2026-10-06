# R15-DATA-002 refutation audit (group data) at HEAD 6741387b

Sidecar: scratch boot `sleep 86400 | VYSTED_DATA_DIR=<scratch>/data sidecar/.venv/bin/python3 main.py --host 127.0.0.1 --port 52360 --data-dir <scratch>/data`, /health ok 2026-09-25 ~09:59 IST.

## Entry's own repro (EO fan-out, sidecar + frontend)
Sidecar per-call region header (X-Vysted-Region) at HEAD:
```
## region IN
resolve AMAL Amal Limited NSE needs_dis False [('AMAL','NSE'),('AMAL','BSE'),('AMAL','US')]
quote {'symbol':'AMAL','price':687.65,'currency':'INR','provider':'nse_direct'}
fund Amal Ltd INR None
history AMAL nse_direct ... close 687.65
## region US
resolve AMAL Amalgamated Financial Corp. US ...
quote {'symbol':'AMAL','price':47.2099,'currency':'USD','provider':'yfinance'}
fund Amalgamated Financial Corp. USD None
history AMAL yfinance ... close 47.21
```
SMR under IN: /resolve lists [('SMR','BSE',1.0,'SMR Jewels Ltd'), ('SMR','US',1.0,'NUSCALE POWER Corp')]; /quotes/SMR -> INR 96.0 bse; /fundamentals/SMR -> SMR.BO 'SMR Jewels Limited'; /fundamentals/SMR/income -> symbol SMR.BO, periods ['2025-03-31','2024-03-31'] (no NuScale statements mixed in); /fundamentals/SMR/ratings -> SMR.BO. The EO is one company per panel.

Frontend: `pnpm exec vitest run src/modules/equity-overview/EquityOverviewPanel.test.tsx ...` -> `Test Files 5 passed (5) Tests 69 passed (69)`. This includes the describe block "EquityOverviewPanel — cross-region tickers (R15-DATA-002)" (EquityOverviewPanel.test.tsx:506-562): the picked NASDAQ:AMAL candidate loads with its own region, a typed two-region ticker shows a chooser and fans out nothing, and a host command carrying a region loads that listing. The EO half of the entry holds.

## Verifier's refutation (rc1-verifier:2 / rc1-vshard-0:2)
Code at HEAD:
- src/components/CommandPalette.tsx:390-392 — the live "Tickers" row (which shows `c.exchange`, e.g. `AMAL US` and `AMAL NSE`) calls `loadSymbolIntoChart(c.symbol)` and drops the exchange/region.
- src/components/CommandPalette.tsx:207 — the corpus symbol row does the same.
- src/lib/host-actions.ts:318 `loadSymbolIntoChart(symbol, timeframe?)`: no region param (compare openCompanyOverview(symbol, highlight, region) just below it, which the fix added).
- src/store/chart-command.ts:39 `loadSymbol(symbol, timeframe?)`: no region.
- src/lib/sidecar-client.ts:341 `history(symbol, timeframe, range, assetClass)`: no regionHeader(), unlike the EO accessors (sidecar-client.ts:322-335, 393-398).
Live: bare /history/AMAL under IN is nse_direct close 687.65 INR; under US it is yfinance close 47.21 USD (output above). So picking the `AMAL US` row in an IN session charts Amal Ltd.

## Classification: partial
The title says "every data panel re-queries the bare symbol, so the user who picked NASDAQ:AMAL ... gets Amal Ltd". The fix (806a90c / 8f8f5f34) carried the picked region through openCompanyOverview/loadEquityOverview only. The chart, the other price surface a user reaches from the same per-listing Cmd-K pick, still re-queries the bare symbol under the session region. The verifier is right that the pick is lost. It is wrong only to call it a regression: this path was never in the fix, and the entry's EO repro holds.
