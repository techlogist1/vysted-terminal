# BMW — BMW Industries Ltd (BSE 542669) — diff vs reference pack

Collected 2026-07-10T12:09Z (ref pack collected_at 2026-07-10T10:07:46Z; ~2h skew, same trading day).

## Resolve

| Probe                          | Result                                                                                                        | Verdict                                   |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| Bare "BMW" (collision probe)   | Binds BMW Industries Ltd, BSE, conf 1.0, 1 candidate — no Bayerische Motoren Werke candidate (not in masters) | MATCH — collision handled by construction |
| Full name "BMW Industries Ltd" | Binds at 1.0 (top of 6 candidates)                                                                            | MATCH                                     |
| Enriched fields                | isin INE374E01021 = pack; bse_code 542669 = pack; industry null; former_name null (pack: none)                | MATCH                                     |

## Field table

| Field                    | Reference (as-of)                          | Collected (as-of)                                             | Verdict                                                  |
| ------------------------ | ------------------------------------------ | ------------------------------------------------------------- | -------------------------------------------------------- |
| Price                    | 54.0 (2026-07-10)                          | 54.0 /quotes, provider bse, eod 2026-07-10                    | MATCH (exact)                                            |
| Mcap                     | ₹1,216 Cr                                  | ₹1,215.5 Cr (yfinance)                                        | MATCH (<0.1%)                                            |
| PE                       | 14.9                                       | 15.04                                                         | MATCH (~1%)                                              |
| PB                       | 1.51                                       | 1.516                                                         | MATCH                                                    |
| ROE                      | 10.9%                                      | 10.51%                                                        | MATCH (~3.6%, basis skew tolerated)                      |
| Div yield                | 0.81%                                      | 0.80% (dps 0.43; ttm-paid 0.43 attached in FAST leg)          | MATCH                                                    |
| Declared-vs-paid         | pack: no distinction published (world_gap) | dividend_declared null; ttm 0.43                              | WORLD-GAP (consistent)                                   |
| 52w high/low             | 65.19 / 26.06                              | 65.19 / 26.06                                                 | MATCH (exact)                                            |
| Promoter %               | 74.36 (Mar 2026)                           | 74.36 (BSE filing 2026-03-31, subm. 2026-04-20)               | MATCH (exact, same quarter)                              |
| FII %                    | 0.0                                        | 0.0                                                           | MATCH                                                    |
| DII %                    | null (world_gap: not broken out)           | null                                                          | WORLD-GAP (consistent)                                   |
| Public %                 | 25.63                                      | 25.64                                                         | MATCH (rounding)                                         |
| Latest quarter (rev/PAT) | 209 / 33 Cr Q4 FY26                        | not in /fundamentals payload (TTM only; growth_computed null) | APP-GAP (per-quarter P&L absent from collected surfaces) |

## Research bundle (gather_fast, NO-LLM, 14.9s)

- Emitted web query (per fast.py, name≠symbol): `"BMW Industries Ltd" BMW BMW stock analysis news outlook`
- Web: available, backend **keyless-fallback**, 6 citations. First 3: in.marketscreener.com (BMW Industries BOM), marketscreener.com (same), bloomberg.com/quote/BMW:IN — all the Indian company, zero Bayerische leakage. Relevance keeps/rejects not exposed by the FAST bundle.
- Legs: price ok (bse), fundamentals ok (yfinance), news ok (rss) — **but items are generic mint headlines (PM Modi / typhoon), not BMW-specific**; filings FAILED: "sec-edgar-mcp is not available — the subprocess did not bind a port this launch".
- Derived: ownership_exchange attached (74.36 / inst 0.0 / public 25.64, BSE 2026-03-31); dividend_declared null; 1 conflict — `held_percent_insiders` (yfinance 81.68 insiders vs BSE 74.36 promoter group), conflict_kind `data_conflict`.
- Null-field reasons: field_meta (33 entries) covers only populated fields; nulls (e.g. dividend_per_share_ttm on REST lane) carry no meta entry/reason.

## Verdict

Cleanest name in the battery: every subtle-tier field matches. Residuals are the battery-wide ones: news-leg irrelevance, filings-leg down, no per-quarter P&L in the collected payloads.
