# NHL — Naturewings Holidays Ltd (BSE SME 544245) — diff vs reference pack

Collected 2026-07-10T12:12Z (ref pack 2026-07-10T10:07:46Z).

## Resolve

| Probe                                | Result                                                                                                                 | Verdict |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------- | ------- |
| Bare "NHL" (collision probe)         | Binds Naturewings Holidays Ltd BSE conf 1.0, single candidate — no National Hockey League anything (not an instrument) | MATCH   |
| Full name "Naturewings Holidays Ltd" | Binds at 1.0                                                                                                           | MATCH   |
| Enriched fields                      | isin INE0N4701016 = pack; bse_code 544245 = pack                                                                       | MATCH   |

## Field table

| Field            | Reference (as-of)                                                 | Collected (as-of)                               | Verdict                                                                                                                                                                                                   |
| ---------------- | ----------------------------------------------------------------- | ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Price            | 80.5 (2026-07-02 — pack's own quote is 8 days old)                | 80.49 (bse eod 2026-07-10)                      | MATCH; note the pack's as-of is stale, app's is current-day                                                                                                                                               |
| Mcap             | ₹28.6 Cr                                                          | ₹25.4 Cr (yfinance, 3,160,400 shares)           | **MISMATCH (~11%)** — share-count basis: world's 28.6 Cr at 80.5 implies ~3.55M shares vs yfinance 3.16M                                                                                                  |
| PE               | 18.5                                                              | 16.9                                            | MISMATCH (minor ~9%, same share/EPS basis skew as mcap)                                                                                                                                                   |
| PB               | 2.24                                                              | 2.11                                            | MISMATCH (minor ~6%)                                                                                                                                                                                      |
| ROE              | 14.1%                                                             | 14.11%                                          | MATCH (exact)                                                                                                                                                                                             |
| Div yield        | 1.86%                                                             | 1.86% (dps 1.5; ttm-paid 1.5 attached)          | MATCH (exact)                                                                                                                                                                                             |
| Declared-vs-paid | no note                                                           | dividend_declared null; ttm 1.5                 | MATCH                                                                                                                                                                                                     |
| 52w high/low     | 98.8 / 56.8                                                       | 98.76 / 56.8                                    | MATCH                                                                                                                                                                                                     |
| Promoter %       | 59.49 (Mar 2026)                                                  | 59.49 (BSE 2026-03-31)                          | MATCH (exact) — and the app's history shows a **revised Mar-2026 filing** (66.99 subm. 2026-04-16, then 59.49 in a later submission); the app correctly surfaces the revision the world's number reflects |
| FII %            | 0.31                                                              | 0.31 (institutions 0.31)                        | MATCH                                                                                                                                                                                                     |
| DII %            | null (world_gap: SME, not reported)                               | null                                            | WORLD-GAP (consistent)                                                                                                                                                                                    |
| Public %         | 40.19                                                             | 40.51                                           | MATCH with note — bucket definition: app's BSE public bucket folds the 0.31 FII out differently (59.49+40.51=100 vs ref 59.49+0.31+40.19≈99.99)                                                           |
| Latest quarter   | FY2026 annual only — Q4-only breakout genuinely unpublished (SME) | not in collected payloads; growth_computed null | WORLD-GAP (consistent — app fabricates nothing)                                                                                                                                                           |

## Research bundle (gather_fast, 14.1s)

- Emitted web query: `"Naturewings Holidays Ltd" NHL NHL stock analysis news outlook`
- Web: available, backend **keyless-fallback**, 6 citations. First 3: bseindia.com (Naturewings), bloomberg.com NHL:IN (Naturewings), univest.in (Naturewings) — thinnest-coverage name in the battery still returns the right company, zero hockey.
- Legs: price ok (bse), fundamentals ok (yfinance), news ok (rss, generic mint headlines), filings FAILED (sec-edgar-mcp no port).
- Derived: ownership_exchange attached (59.49/0.31/40.51 BSE 2026-03-31); dividend_declared null; 1 conflict — held_percent_insiders (81.34 vs 59.49), data_conflict. Note the insider figure here is wildly stale (81.34 vs the real 59.49) — the conflict card is doing real work on this SME.
- Null-field reasons: none carried (32 field_meta entries).

## Verdict

SME survives: right company, exact promoter/FII/yield/ROE, honest world-gaps on Q4/DII. One real data miss — yfinance's share count understates mcap ~11% vs the world's, dragging PE/PB with it, and nothing in the payload signals the share-count uncertainty.
