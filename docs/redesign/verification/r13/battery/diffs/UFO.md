# UFO — UFO Moviez India Ltd (NSE UFO / BSE 539141; common-word ticker) — diff vs reference pack

Collected 2026-07-10T12:16Z (ref pack 2026-07-10T10:07:46Z).

## Resolve

| Probe                                    | Result                                                                                                            | Verdict                        |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| Bare "UFO" (common-word collision probe) | Binds UFO Moviez India Limited NSE conf 1.0; candidate #2 the BSE dual listing; industry "Entertainment" enriched | MATCH                          |
| Full name "UFO Moviez India Ltd"         | **Does NOT bind** — needs_disambiguation; top candidate IS UFO Moviez at 0.909, below accept                      | **APP-GAP** (Ltd/Limited seam) |
| Enriched fields                          | isin INE527H01019 = pack; bse_code 539141 = pack                                                                  | MATCH                          |

## Field table

| Field            | Reference (as-of)                                                                  | Collected (as-of)                             | Verdict                                                                                  |
| ---------------- | ---------------------------------------------------------------------------------- | --------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Price            | 69.68 (2026-07-10)                                                                 | 69.68 (nse_direct eod 2026-07-10, vol 57,743) | MATCH (exact)                                                                            |
| Mcap             | ₹271.27 Cr                                                                         | ₹270.5 Cr                                     | MATCH                                                                                    |
| PE               | 10.89                                                                              | 10.85                                         | MATCH                                                                                    |
| PB               | 0.91                                                                               | 0.835                                         | MISMATCH (minor ~8%, book basis)                                                         |
| ROE              | 8.0%                                                                               | 8.0%                                          | MATCH (exact)                                                                            |
| Div yield        | 0.0% (pack: genuinely zero — nothing paid since Mar 2020, not a timing artifact)   | null                                          | APP-GAP (null vs affirmed zero — the app cannot state the pack's "correctly 0.00%" fact) |
| Declared-vs-paid | last dividend Rs 15/share paid 2020-03-11; nothing since                           | dividend_declared null, ttm null              | MATCH (consistent)                                                                       |
| 52w high/low     | 92.97 / 53.75                                                                      | 92.97 / 53.75                                 | MATCH (exact)                                                                            |
| Promoter %       | 22.33 (Mar 2026)                                                                   | 22.33 (NSE 2026-03-31, subm. 2026-04-15)      | MATCH (exact)                                                                            |
| FII %            | 0.84                                                                               | null                                          | **APP-GAP** (NSE-lane split missing)                                                     |
| DII %            | **24.22**                                                                          | null                                          | **APP-GAP** — a quarter of the register (DII 24.22%) invisible                           |
| Public %         | 52.62                                                                              | 77.67                                         | APP-GAP consequence (NSE public bucket folds institutions: 22.33 + 77.67 = 100)          |
| Latest quarter   | 136.37 / 4.48 Cr Q4 FY26 (pack notes world's own 136.37-vs-133.22 source variance) | not in collected payloads                     | APP-GAP                                                                                  |
| Promoter pledge  | world: ~26.2% of promoter stake pledged (pack world_gap)                           | nothing in collected surfaces                 | APP-GAP (pledge invisible)                                                               |

## Research bundle (gather_fast, 18.1s)

- Emitted web query: `"UFO Moviez India Limited" UFO UFO stock analysis news outlook`
- Web: available, backend **keyless-fallback**, 5 citations. First 3: stockanalysis.com NSE:UFO, google.com/finance UFO:NSE, economictimes (UFO Moviez) — zero alien-phenomena noise; quoted-name query holds on the common word.
- Legs: price ok (nse_direct), fundamentals ok (yfinance), news ok (rss, generic mint headlines), filings FAILED (sec-edgar-mcp no port).
- Derived: ownership_exchange attached, promoter-only (22.33, NSE 2026-03-31; institutions null); dividend_declared null; 1 conflict — held_percent_insiders (53.05 vs 22.33, another 2.4x catch), data_conflict.
- Null-field reasons: none carried (31 field_meta entries).

## Verdict

Price/valuation/promoter all exact. Same two structural holes as the other dual-listed names: FII/DII split lost to NSE-lane precedence (here hiding DII at 24.22%), and pledge data nonexistent.
