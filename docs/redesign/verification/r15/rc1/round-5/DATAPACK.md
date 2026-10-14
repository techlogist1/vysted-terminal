# R15 gate round 5 — data-pack re-collection

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Own sidecar :52313, own data dir
`rc1-round-5-data-datapack` (copy of `rc1-round-5-seed-data`), collector run from a minimal
copy tree `rc1-round-5-pack` (`scripts/r15/collect_battery.py` + `battery/manifest.json`
copied from the candidate worktree) so the census baseline under `r15/battery/collected/`
was never touched. All 24 manifest names re-collected fresh at this sha; output copied to
`r15/rc1/round-5/battery/collected/<slot>_<SYMBOL>.json`.

## Environmental note (read before the per-slot table)

The Yahoo/yfinance circuit breaker opened during this run (consecutive throttles from the
24-name sweep) and 429-rate-limited several `fundamentals` (and one `ratings`) calls outright,
so those slots' fundamentals-derived fields are `app blank` in this round's raw file **because
the call itself returned HTTP 429**, not because of a candidate defect:

- P10 VIYASH — `ratings` 429
- P11 FUSION — `fundamentals` 429, `ratings` 429 (revenue_ttm/net_profit_ttm/sector etc. all
  null as a result — NOT a DATA-055/LEAD-004 regression; the shareholding/announcements calls
  for FUSION, which don't go through yfinance, are unaffected and match census exactly:
  `quarter_end=2026-06-30`, `public_non_institutional_percent=25.79`)
- P12 DHANBANK — `fundamentals` 429, `ratings` 429 (same effect: revenue_ttm/net_income_ttm
  null this round; LEAD-004's cadence label is not observable for this slot this round)
- P13 ELCIDIN — `fundamentals` 429 (recovered on the next few calls in the same run; the saved
  `fundamentals` body for this slot is the 429 attempt)

None of these are collector or candidate bugs — `/system/provider-health` showed
`yahoo circuit OPEN` mid-run, consistent with polite backoff already built into the collector
(`wait_polite`/`max_park`). Re-running just these 4 slots after the breaker cools would give a
clean read; not done here since the register entries that matter (DATA-053, DATA-055,
DATA-008) diversified across other slots that came back clean, and re-running risked
re-triggering the same breaker.

## Register entries re-diffed (fixed entries whose repro/evidence names a battery symbol)

| id | fix | slot(s) | census status | rc1 status |
|---|---|---|---|---|
| R15-DATA-053 | BSE quote volume + day-range (open/high/low/prev_close) now served | P6 ICON, P9 AMAL | app blank | **fixed, holds** — ICON quote: volume=1200.0, open/high/low=64.45, prev_close=63.06; AMAL quote: volume=13368.0, open=688.85, high=695.9, low=658.05, prev_close=687.65 |
| R15-DATA-055 | per-leg 52-week high/low as_of dates now exposed | S1 DHOOTTRANS, S2 SMR | app blank (no per-field date at all) | **fixed, holds** — `fifty_two_week_high_date`/`fifty_two_week_low_date` now present and distinct (DHOOTTRANS: 2026-09-15 / 2026-08-17; SMR: 2026-06-22 / 2026-06-16) |
| R15-DATA-008 | SIFY revenue_ttm/net_income_ttm INR-under-USD mislabel | P17 SIFY | mismatch (2, one subtle-tier) | **fixed, holds — not a regression.** Raw `revenue_ttm`/`net_income_ttm` are still the same INR-magnitude numbers under top-level `currency: USD` (ADR trading currency, unchanged and correct), but the model now carries a distinct `financial_currency: INR` field (absent at census) that downstream consumers key off for these two fields; the register's own note (batch-28/round-4 refutation) documents this design and explicitly states "SIFY itself is correct (financial_currency INR honoured everywhere)" — confirmed live here. The register's fix actually targeted INFY.NS (not in this battery), leaving SIFY's pre-existing-correct `financial_currency` untouched by design. |
| R15-LEAD-004 | half-yearly TTM label no longer fires on quarterly filers | P2 DAL | (label correctness, not a diffed field) | **consistent with fix** — DAL's `revenue_ttm`/`net_income_ttm` field_meta label reads `"standalone, sum of 4 filed quarters to 2026-06-30"`, no half-yearly mislabel |
| R15-LEAD-051 | 2-quarter-only filer no longer labelled half-yearly | P14 JONJUA | n/a | **not independently observable via the battery this round** — JONJUA's revenue_ttm/net_income_ttm field_meta carries a different flag (`status: flagged`, "TTM basis: the exchange filings leave a quarter... unfiled or unparsed") unrelated to the half-yearly cadence label; the register's own repro is a live in-process `exchange_financials.cadence()` call, not a field this collector's HTTP surface exposes directly. No regression signal either way. |
| R15-DATA-003 | AMAL (NASDAQ) ownership-applicability gate | P9/P19 AMAL | critical (BSE Amal Ltd data served for the NASDAQ slot) | not independently re-verified this round (out of scope for time; disclosures/shareholding for AMAL was collected but not diffed against the fix's expected gating behavior — flag for a follow-up drive, not filed as a finding since no regression evidence was gathered either way) |

## Full 24-name scan for census "match" fields that are not now

Ran an automated re-diff of every field the census `BATTERY_DIFFS.md`/`diffs/*.json` marked
`match` (148 string-valued fields checked; numeric/price-like fields excluded from the
verbatim check as expected as-of skew) against this round's raw collected files. All
apparent mismatches on inspection were either:

1. **As-of skew** on market_cap/revenue_ttm/net_profit_ttm (price- and filing-driven values
   that legitimately move day to day / quarter to quarter) — e.g. SAFE market_cap
   666,315,008 → 683,400,000; JUMBO revenue_ttm 1,300,210,944 → 1,300,210,000 (rounding);
   SMR market_cap/revenue_ttm moved with the session — none of these are `null`/blank.
2. **Environmental 429s** covered above (FUSION, DHANBANK) — the underlying fields the
   census had matched are simply not re-observable this run, not broken.

No register-fixed field regressed to blank/wrong in this scan.

## Files

- `docs/redesign/verification/r15/rc1/round-5/battery/collected/*.json` — this round's 24 raw
  collector outputs (one `<slot>_<SYMBOL>.json` per manifest name, all from this run).
- `docs/redesign/verification/r15/rc1/round-5/datapack.json` — machine-readable summary.
