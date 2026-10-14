# BI — Bilcare Ltd (NSE BI / BSE 526853; 2-char ticker, distressed history) — diff vs reference pack

Collected 2026-07-10T12:14Z (ref pack 2026-07-10T10:07:46Z).

## Resolve

| Probe                                    | Result                                                                                                    | Verdict                                                                                                                                                                   |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bare "BI" (multi-entity collision probe) | Binds Bilcare Limited NSE conf 1.0; candidate #2 Bilcare Ltd BSE — the dual listing, no foreign noise     | MATCH                                                                                                                                                                     |
| Full name "Bilcare Ltd"                  | **Does NOT bind** — needs_disambiguation true; top candidate IS Bilcare Limited at 0.846 but below accept | **APP-GAP** — the company's own legal name (pack spelling, "Ltd") fails to resolve; the NSE master's "Limited" long-form loses enough score to fall under the accept band |
| Enriched fields                          | isin INE986A01012 = pack; bse_code 526853 = pack                                                          | MATCH                                                                                                                                                                     |

## Field table

| Field            | Reference (as-of)                               | Collected (as-of)                             | Verdict                                                                                                                                                            |
| ---------------- | ----------------------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Price            | 62.6 (2026-07-10, screener/BSE basis)           | 63.06 (nse_direct eod 2026-07-10, vol 13,704) | MATCH (~0.7%, NSE-vs-BSE print)                                                                                                                                    |
| Mcap             | ₹147 Cr                                         | **null**                                      | **APP-GAP** — yfinance carries no mcap for BI.NS; world has it                                                                                                     |
| PE               | 26.7                                            | null (eps null too)                           | APP-GAP (same provider hole)                                                                                                                                       |
| PB               | 0.76                                            | 0.755                                         | MATCH                                                                                                                                                              |
| ROE              | **+1.66%**                                      | **-5.21%**                                    | **MISMATCH (sign flip)** — app states negative ROE where the world's consolidated view is positive; basis conflict, unflagged                                      |
| Div yield        | 0.0% (affirmed, post-NCLT)                      | null                                          | APP-GAP (null vs affirmed zero)                                                                                                                                    |
| Declared-vs-paid | trailing 0.00%                                  | dividend_declared null                        | MATCH                                                                                                                                                              |
| 52w high/low     | **116 / 50.0**                                  | **75.0 / 51.62**                              | **MISMATCH** — the app's 52w high is 35% below the world's (provider series vs exchange series); a user reading "75 high" against a 116 world is materially misled |
| Promoter %       | 30.01 (Mar 2026)                                | 30.01 (BSE 2026-03-31, subm. 2026-04-21)      | MATCH (exact)                                                                                                                                                      |
| FII %            | 0.04                                            | 0.04 (institutions 0.04)                      | MATCH (exact)                                                                                                                                                      |
| DII %            | 0.0 (ref: inferred from identity, not explicit) | null                                          | WORLD-GAP (consistent — both sides honest about the missing line)                                                                                                  |
| Public %         | 69.95                                           | 69.99                                         | MATCH                                                                                                                                                              |
| Latest quarter   | 187.66 / 7.85 Cr Q4 FY26                        | not in collected payloads                     | APP-GAP                                                                                                                                                            |

## Research bundle (gather_fast, 18.9s)

- Emitted web query: `"Bilcare Limited" BI BI stock analysis news outlook`
- Web: available, backend **keyless-fallback**, 6 citations. First 3: stockanalysis.com NSE:BI (Bilcare), economictimes (Bilcare), finance.yahoo BI.BO (Bilcare) — the multi-entity collision (Bank Indonesia / Power BI / Biogen) never surfaces; quoted-name query holds.
- Legs: price ok (nse_direct), fundamentals ok (yfinance — but with the null holes above), news ok (rss, generic), filings FAILED (sec-edgar-mcp no port).
- Derived: ownership_exchange attached (30.01/0.04/69.99 BSE 2026-03-31); dividend_declared null; 1 conflict — held_percent_insiders (67.10 vs 30.01 — a 2.2x divergence; the card is essential here), data_conflict.
- Null-field reasons: **13 null fields (market_cap, pe_ratio, eps, shares_outstanding, dividend_yield…) carry NO field_meta entry and no reason** — field_meta (26 entries) covers only populated fields. The brief's per-field provenance exists only for values that came back.

## Verdict

Worst fundamentals surface in the battery: mcap/PE/EPS null where the world has them, ROE sign-flipped, and the 52-week range materially wrong (75 vs 116 high) — all unflagged. Shareholding and identity are clean; full-legal-name resolution fails on the Ltd/Limited seam.
