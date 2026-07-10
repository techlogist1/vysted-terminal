# GEE — GEE Ltd (BSE 504028, group X illiquid, numeric-scrip-identified) — diff vs reference pack

Collected 2026-07-10T12:13Z (ref pack 2026-07-10T10:07:46Z).

## Resolve

| Probe                                                   | Result                                                                                                                                  | Verdict                              |
| ------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| Bare "GEE"                                              | Binds GEE Ltd BSE conf 1.0, single candidate                                                                                            | MATCH                                |
| Full name "GEE Ltd"                                     | Binds at 1.0                                                                                                                            | MATCH                                |
| **Numeric scrip "504028"**                              | **Binds GEE Ltd at conf 1.0** — the numeric-scrip identity class resolves                                                               | MATCH (designed probe passed)        |
| Former name "General Electrodes and Equipments Limited" | resolved null, needs_disambiguation **false**, candidates **empty** — an honest total no-match (distinct from the disambiguation shape) | APP-GAP (former-name lineage absent) |
| Enriched fields                                         | isin INE064H01021 = pack; bse_code 504028 = pack; former_name null vs pack                                                              | APP-GAP (former_name)                |

## Field table

| Field            | Reference (as-of)                                                                 | Collected (as-of)                           | Verdict                                                                                                                                    |
| ---------------- | --------------------------------------------------------------------------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Price            | 105 (2026-07-10)                                                                  | 105.0 (bse eod 2026-07-10, +5.0 on the day) | MATCH (exact)                                                                                                                              |
| Mcap             | ₹546 Cr                                                                           | ₹545.8 Cr                                   | MATCH                                                                                                                                      |
| PE               | 35.7 (screener consolidated)                                                      | 42.7 (yfinance, eps 2.46)                   | **MISMATCH (~20%)** — EPS basis (consolidated vs provider TTM); unflagged                                                                  |
| PB               | 2.54                                                                              | 1.31                                        | **MISMATCH (~2x)** — book-value basis conflict between world and provider; the largest ratio divergence in the battery after TI; unflagged |
| ROE              | 7.48%                                                                             | 6.36%                                       | MISMATCH (minor ~15%)                                                                                                                      |
| Div yield        | 0.0% (pack note: trailing zero, none declared/paid)                               | null                                        | APP-GAP (null vs affirmed zero)                                                                                                            |
| Declared-vs-paid | trailing 0.00%, nothing declared                                                  | dividend_declared null, ttm null            | MATCH (consistent)                                                                                                                         |
| 52w high/low     | 127 / 53.6                                                                        | 127.0 / 53.61                               | MATCH                                                                                                                                      |
| Promoter %       | 63.97 (Mar 2026)                                                                  | 63.97 (BSE 2026-03-31)                      | MATCH (exact)                                                                                                                              |
| FII %            | 1.37                                                                              | 1.37                                        | MATCH (exact)                                                                                                                              |
| DII %            | 0.0                                                                               | 0.0                                         | MATCH                                                                                                                                      |
| Public %         | 34.68                                                                             | 36.03                                       | MATCH with note — bucket definition (34.68 + 1.37 FII ≈ 36.05; app's public bucket includes non-institutional non-promoter)                |
| Latest quarter   | 112.16 / 3.54 Cr Q4 FY26                                                          | not in collected payloads                   | APP-GAP                                                                                                                                    |
| Promoter pledge  | world: 43.4% of promoter stake pledged (screener key concern, in pack world_gaps) | nothing in any collected surface            | APP-GAP (pledge data absent)                                                                                                               |

## Research bundle (gather_fast, 16.5s)

- Emitted web query: `"GEE Ltd" GEE GEE stock analysis news outlook`
- Web: available, backend **keyless-fallback**, 6 citations. First 3: economictimes (GEE Ltd), beta.bseindia.com (Gee Ltd 504028), walletinvestor (GEE Ltd BSE) — right company on a generic 3-letter string.
- Legs: price ok (bse), fundamentals ok (yfinance), news ok (rss, generic), filings FAILED (sec-edgar-mcp no port).
- Derived: ownership_exchange attached (63.97/1.37/36.03 BSE 2026-03-31); dividend_declared null; **2 conflicts**, both data_conflict: held_percent_insiders (71.33 vs 63.97) and **held_percent_institutions (yfinance 0.00 vs BSE 1.37)** — the second card correctly catches the provider's institutional zero being false.
- Null-field reasons: none carried (30 field_meta entries).

## Verdict

Identity and shareholding perfect (incl. the numeric-scrip probe and the institutions conflict card). Valuation ratios are the weak flank: PB 1.31 vs the world's 2.54 and PE 42.7 vs 35.7 ride provider book/EPS bases with no conflict flag, and the 43.4% promoter pledge is invisible to the app.
