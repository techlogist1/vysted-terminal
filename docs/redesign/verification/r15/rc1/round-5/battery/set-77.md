# batch-28/W4-sonnet

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`, own sidecar `127.0.0.1:52351`,
data dir `rc1-round-5-data-rc1-battery-11` (seed copy). Live GETs, re-running each
entry's batch-28 certification repro (per batch-28 VERDICTS.md "Per-entry evidence" /
"Certified" table), not the original pre-batch-28 register repro.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-008 | `GET /fundamentals/INFY.NS`, `GET /fundamentals/HCLTECH.NS`, `GET /fundamentals/SIFY`. | INFY.NS: `currency: "INR"`, `financial_currency: null`, `revenue_ttm: 1.84582e12` with `field_meta.revenue_ttm.reason` "exchange-filed (INR, NSE) figure served; the provider's ... was served on a USD basis ... not compared", `free_cash_flow` withheld with a same-shape reason. HCLTECH.NS shows the identical pattern (`revenue_ttm: 1.34374e12`). SIFY unchanged: `currency: "USD"`, `financial_currency: "INR"`. | holds |
| R15-DATA-055 | `GET /fundamentals/NAVN`, `MDLN`, `SAIL`, each with header `X-Vysted-Region: US` (the region the resolver needs to pick the US SailPoint listing for the bare ticker `SAIL` — confirmed via `GET /resolve?q=SAIL`, which lists a Steel-Authority-of-India candidate under IN and a SailPoint, Inc. candidate under US). | NAVN `first_trade_date: 2025-10-30`, MDLN `first_trade_date: 2025-12-17`, SAIL(US) `first_trade_date: 2025-02-13` — all three with `listing_date: null`, matching batch-28's certification verbatim. (A first probe without the region header defaulted SAIL to the IN Steel Authority listing, `first_trade_date: 1996-01-01`/`listing_date: 1995-07-06` — a resolver ambiguity in this probe's own header choice, not a product regression; corrected and re-run.) | holds |
| R15-LEAD-022 | `GET /quotes/{sym}?asset_class=equity` for BMW.DE, 005930.KS, NESN.SW, BHP.AX, BRK.B, BF.B. | BMW.DE `currency: "EUR"`, 005930.KS `"KRW"`, NESN.SW `"CHF"`, BHP.AX `"AUD"` — all `200`, dashless suffixes intact in the returned `symbol`. BRK.B resolves to `symbol: "BRK-B"`, BF.B to `"BF-B"` (the US share-class dash exception). | holds |

**Set result: 3/3 holds. No regressions.**

COVERAGE: 16/16 ids raw; no raw: none.
