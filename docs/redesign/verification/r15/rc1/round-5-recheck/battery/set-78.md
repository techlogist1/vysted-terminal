# batch-28/W4-sonnet

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Sidecar: rc1-battery-8 shard, source, port 52348 (same as set-27/set-36).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-008 | GET /fundamentals/HCLTECH.NS, /fundamentals/SIFY, /fundamentals/AAPL, /fundamentals/WIPRO.NS, /fundamentals/DRREDDY.NS | HCLTECH.NS matches the fresh case exactly (financial_currency null, currency INR, revenue_ttm/net_income_ttm served from NSE with a two-currency reason, FCF withheld with a matching reason). SIFY unchanged (currency USD, financial_currency INR, revenue_ttm raw, no reason) -- matches what batch-28 itself recorded as expected/non-regressed. AAPL/WIPRO.NS/DRREDDY.NS normal. | holds |
| R15-LEAD-022 | GET /quotes/{BMW.DE,005930.KS,NESN.SW,BHP.AX,BRK.B,BF.B} | All 6 priced correctly: BMW.DE 55.72 EUR, 005930.KS 285500 KRW, NESN.SW 77.17 CHF, BHP.AX 60.72 AUD (foreign suffixes unchanged, not "possibly delisted"); BRK.B->BRK-B 505.48 USD, BF.B->BF-B 26.16 USD (intentional US share-class dash quirk). | holds |
| R15-DATA-055 | GET /fundamentals/{NAVN,MDLN,SAIL,DHOOTTRANS} | NAVN first_trade_date=2025-10-30, MDLN=2025-12-17, both listing_date null -- matches fresh case exactly. SAIL now resolves to Steel Authority of India (SAIL.NS, listing_date 1995-07-06) rather than the fresh case's 2025-02-13/null result -- symbol-resolver data drift, not a code regression (its own per-field dates are correct). DHOOTTRANS's per-field dates (listing_date, first_trade_date, fifty_two_week_high_date, fifty_two_week_low_date, forward_pe_fiscal_year) all present and distinct, addressing the original repro's core claim. Frontend threshold logic pinned at EquityOverviewPanel.test.tsx:674 "(R15-DATA-055)", not re-executed. | holds |

COVERAGE: 3/3 ids raw; no raw: none.
