# BABA — Baba Arts Ltd (BSE 532380, group X, mid-open-offer) — diff vs reference pack

Collected 2026-07-10T12:10Z (ref pack 2026-07-10T10:07:46Z).

## Resolve

| Probe                                   | Result                                                                                                                                                              | Verdict                                                            |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Bare "BABA" (collision probe)           | Binds Baba Arts Ltd BSE conf 1.0; candidate #2 is **Alibaba Group Holding Ltd (US, conf 1.0)** — listed but not chosen (IN region wins), needs_disambiguation false | MATCH — collision candidate surfaced, Indian name bound            |
| Full name "Baba Arts Ltd"               | Binds at 1.0                                                                                                                                                        | MATCH                                                              |
| Former name "Galaxy Multimedia Limited" | Does NOT resolve — disambiguation with unrelated names (Max India 0.714, GAIL 0.711…)                                                                               | APP-GAP (former-name lineage absent from masters; pack carries it) |
| Enriched fields                         | isin INE893A01036 = pack; bse_code 532380 = pack; former_name null vs pack "Galaxy Multimedia Limited"                                                              | APP-GAP (former_name not populated)                                |

## Field table

| Field            | Reference (as-of)     | Collected (as-of)                        | Verdict                                                                                               |
| ---------------- | --------------------- | ---------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Price            | 16.7 (2026-07-10)     | 16.54 (bse eod 2026-07-10)               | MATCH (~1%; T2T group X — both same-day but different prints; flagging as source variance, not error) |
| Mcap             | ₹87.8 Cr              | ₹86.8 Cr                                 | MATCH (~1%, tracks the price gap exactly)                                                             |
| PE               | 135                   | 137.8                                    | MATCH (~2%)                                                                                           |
| PB               | 3.1                   | 3.15                                     | MATCH                                                                                                 |
| ROE              | 2.4%                  | 2.41%                                    | MATCH                                                                                                 |
| Div yield        | 0.0%                  | null (dps null, ttm null)                | APP-GAP (world affirms a true zero; app emits null — "no dividend" vs "unknown" indistinguishable)    |
| Declared-vs-paid | no note in pack       | dividend_declared null                   | MATCH (consistent)                                                                                    |
| 52w high/low     | 17.2 / 6.01           | 17.24 / 6.01                             | MATCH                                                                                                 |
| Promoter %       | 74.68 (Mar 2026)      | 74.68 (BSE 2026-03-31, subm. 2026-04-10) | MATCH (exact — pre-open-offer figure on both sides; pack itself warns figures are mid-offer)          |
| FII %            | 0.0                   | null (institutions_percent 0.0)          | MATCH (via institutions bucket; FII line not carried this quarter)                                    |
| DII %            | null (world_gap)      | null                                     | WORLD-GAP (consistent)                                                                                |
| Public %         | 25.31                 | 25.32                                    | MATCH                                                                                                 |
| Latest quarter   | 5.16 / 0.1 Cr Q4 FY26 | not in collected payloads                | APP-GAP                                                                                               |

## Research bundle (gather_fast, 16.8s)

- Emitted web query: `"Baba Arts Ltd" BABA BABA stock analysis news outlook`
- Web: available, backend **keyless-fallback**, 6 citations. First 3: walletinvestor (Baba Arts BSE), moneycontrol (Baba Arts), aajtak.in (Baba Arts) — zero Alibaba leakage. The quoted-name query holds under the heaviest collision in the battery.
- **Open-offer blind spot**: none of the surfaced citations mention the live Skybridge Interactive open offer (pack's headline event, LoO filed 2026-06-01). Structured legs have no vehicle for it either (filings leg down, news leg generic). APP-GAP on the moving event.
- Legs: price ok (bse), fundamentals ok (yfinance), news ok (rss, generic mint headlines — irrelevant), filings FAILED (sec-edgar-mcp no port).
- Derived: ownership_exchange attached (74.68/0.0/25.32 BSE 2026-03-31); conflicts: 1 — held_percent_insiders (81.59 vs 74.68), data_conflict.
- Null-field reasons: none carried (field_meta covers populated fields only; 30 entries).

## Verdict

Numbers all match; the misses are structural — former-name lineage unresolvable, live open offer invisible to every collected lane, dividend null-vs-affirmed-zero.
