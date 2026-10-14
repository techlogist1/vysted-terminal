# R15-DATA-002 / rc1-verifier:6: partial

Refutation audit round 2, group data. Own sidecar :52360 (pid 4861, pgid 4857) booted from source at HEAD a3275f64. The code tree equals candidate 4c6dfe8c: `git diff --name-only 4c6dfe8c HEAD | grep -v '^docs/'` printed nothing. Scratch data dir: scratchpad/refaudit2-data/data. Written 18:22 IST.

## Entry
The picked cross-region listing must reach every data leg. The fix_shape carries {symbol, region, yahoo_symbol} through the pick paths and sends a per-call X-Vysted-Region. Round 1 found this partial: the chart path dropped the region. Batch 12 fixed the chart and the palette candidate pick (CommandPalette.tsx:394).

## Verifier's claim (code-level)
The watchlist path still drops the region. pickCandidate(symbol) stores a bare symbol, and SymbolEntry has no region field.

## Code at the candidate (src identical to 4c6dfe8c: `git diff --quiet 4c6dfe8c HEAD -- src` returned 0)
- src/store/symbols.ts:15-18: `interface SymbolEntry { symbol: string; assetClass: "equity" | "crypto"; }`. There is no region field.
- src/modules/watchlist/WatchlistPanel.tsx:286-287: `const pickCandidate = (symbol: string) => { addSymbol(symbol, "equity"); ...`. Line :434 calls `pickCandidate(c.symbol)` and :298 does the same on Enter. c.region and c.yahoo_symbol are discarded.
- src/modules/watchlist/api.ts `fetchWatchlistQuotes`: `sidecarApi.quotes(equitySymbols)`. It sends no per-call region, so the session X-Vysted-Region applies.
- WatchlistPanel.tsx:560 and :562: a row click calls `loadSymbolIntoChart(row.entry.symbol)` and `openCompanyOverview(row.entry.symbol)` with no region.
- CommandPalette.tsx:207: the palette's watchlist items call `loadSymbolIntoChart(item.symbolEntry.symbol)` with no region. Only the candidate pick at :394 carries `c.region`.

## Live replay of the watchlist add path (session region IN, own sidecar)
The GUI rig is not connected in this session (tauri-mcp ENOENT), so the component's exact HTTP calls were replayed:
```
18:21 IST
== step1 autocomplete (what the watchlist input calls): GET /resolve/autocomplete?q=AMAL&region=IN&limit=8
  AMAL NSE IN AMAL.NS Amal Limited 1.0
  AMAL US US AMAL Amalgamated Financial Corp. 1.0
  PIRAMALFIN NSE IN PIRAMALFIN.NS Piramal Finance Limited 0.8
  PPLPHARMA NSE IN PPLPHARMA.NS Piramal Pharma Limited 0.8
  NILKAMAL NSE IN NILKAMAL.NS Nilkamal Limited 0.8
  NEAGI NSE IN NEAGI.NS Neelamalai Agro Industries Limited 0.8
  PKTEA NSE IN PKTEA.NS The Peria Karamalai Tea & Produce Company Limited 0.8
  SHYMINV BSE IN SHYMINV.BO Shyamkamal Investments Ltd 0.8
== step2 pickCandidate(c.symbol) stores the bare symbol 'AMAL' (WatchlistPanel.tsx:286-291,434); fetchWatchlistQuotes polls GET /quotes?symbols=AMAL&asset_class=equity with the session header X-Vysted-Region: IN (no per-row region)
[{"symbol":"AMAL","price":674.4,"change":-13.25,"change_percent":-1.926852323129499,"volume":13368.0,"open":null,"high":null,"low":null,"prev_close":null,"currency":"INR","market_state":"CLOSED","timestamp":"2026-09-25T00:00:00Z","provider":"nse_direct","freshness":"eod"}]
== control: the same bare symbol with the picked listing's region (what a region-carrying entry would send)
[{"symbol":"AMAL","price":47.58000183105469,"change":0.37000183105468665,"change_percent":0.7837361386458094,"volume":170300.0,"open":null,"high":null,"low":null,"prev_close":null,"currency":"USD","market_state":null,"timestamp":"2026-09-25T20:00:01Z","provider":"yfinance","freshness":"eod"}]
== step3 row click -> openCompanyOverview('AMAL') (no region) -> /fundamentals/AMAL under IN
{'symbol': 'AMAL.NS', 'name': 'Amal Ltd', 'currency': 'INR', 'sector': 'Basic Materials'}
== SMR pair
  SMR BSE IN SMR.BO SMR Jewels Ltd
  SMR US US SMR NUSCALE POWER Corp
  SMRUTHIORG BSE IN SMRUTHIORG.BO Smruthi Organics Ltd
  SMRT US US SMRT SmartRent, Inc.
[{"symbol":"SMR","price":94.0,"change":-2.0,"change_percent":-2.083333333333333,"volume":9000.0,"open":94.0,"high":94.0,"low":92.0,"prev_close":96.0,"currency":"INR","market_state":"CLOSED","timestamp":"2026-09-25T00:00:00Z","provider":"bse","freshness":"eod"}]
```

The watchlist autocomplete offers `AMAL US Amalgamated Financial Corp.` and `SMR US NUSCALE POWER Corp`. Picking either one stores the bare symbol. The poll under the session header then returns Amal Ltd at 674.4 INR (nse_direct) and SMR Jewels at 94.0 INR (bse). With the picked listing's region (US), the same symbol returns Amalgamated at 47.58 USD. The user who picked NASDAQ:AMAL in the watchlist gets Amal Ltd's quote, chart and overview. That is the entry's exact wrong-entity defect, on a sibling pick path.

## Verdict: partial
The entry's own path (palette pick into the overview and chart) holds, per batch 12. The same defect class (a picked listing's region dropped before the data legs) is still open on the watchlist: pick, poll, row click, and the palette items built from watchlist entries. The live path confirms the code-level claim, so this is not a verifier error.

Failure count: 2 (rc1 refutation audit round 1 = partial; this gate refutation = partial). No batch not_certified listing.
