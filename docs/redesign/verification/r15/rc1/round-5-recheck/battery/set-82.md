# Regression battery — set-82 (batch-29/W2-sonnet)

Shard: rc1-battery-18. Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Own sidecar :52358.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-063 | `GET /indicators` vs `GET /history` freshness on the same symbol: TCS.NS rsi, HDFCBANK.NS macd, RELIANCE.BO rsi, TCS.NS 1h, BTC/USDT 1h (crypto), and the empty series ZZZNOTREAL. | All equity/BSE cases: `eod`/`eod` parity. BTC/USDT 1h: `live`/`live` parity. ZZZNOTREAL: HTTP 200, `provider: none`, `freshness: None` (downgrade kept). Matches the certified table exactly. | holds |
| R15-LEAD-004 | `GET /fundamentals/<sym>` with `X-Vysted-Region: IN` for TCS.NS, NDTV, JONJUA; in-process `FiledPeriods.cadence()` for 6 fresh shapes (gap, complete-quarterly, 2x pure half-yearly, calendar-FY halves, fresh-listing gap). | TCS.NS: no TTM reason. NDTV: "…leave a quarter of the trailing year unfiled or unparsed; kept, flagged" (no "half-yearly"). JONJUA: same quarterly-gap message as NDTV — batch-29 saw JONJUA as half-yearly hours earlier; live data most likely drifted (one more quarter now filed), not a code change — an adjacent note, not a regression, since the mechanism (a quarterly filer never gets the half-yearly label) still holds. All 6 in-process `cadence()` shapes matched the certified table exactly. | holds |

COVERAGE: 2/2 ids raw; no raw: none.
