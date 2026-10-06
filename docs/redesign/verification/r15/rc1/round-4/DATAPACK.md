# R15 RC1 gate round 4 — DATA-PACK re-collection (rc1-datapack)

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Own sidecar :52313, own data dir
`rc1-round-4-data-rc1-datapack` (copy of the keyless seed). Collector run from a minimal
copy tree (`rc1-round-4-pack`, never the candidate worktree, never the census
`docs/redesign/verification/r15/battery/collected/`). All 24 manifest names re-collected
this run with `--force`; every slot wrote `<slot>_<SYMBOL>.json` with `"complete": true` —
zero `.error.txt`. Raw files copied to `battery/collected/` beside this doc.

## Method

The 42 `fixed` register entries whose `raw_ids` name a battery slot (list below) were
spot-checked directly against the re-collected raw JSON. Separately, a structural diff
(`old` census `battery/collected/*.json` vs this run's re-collected files, same 24
filenames) was run over the `fundamentals`/`quote`/`shareholding` call bodies, scalar
keys only, excluding `field_meta`/`*_meta` and the known price-like keys (market_cap,
week52 fields, revenue_ttm, net_income_ttm, eps, pe/pb/ps ratios, dividend fields,
shares_outstanding, beta — price/valuation drift over the intervening week is as-of
skew per `BATTERY_DIFFS.md`, not a regression). 170 both-sides-present value changes
came back; all but the ones below are quote price/timestamp/volume drift (as-of skew)
or `revenue_growth`/`earnings_growth`/`growth_basis` quarter-rollover (also as-of skew).

## Non-price identity/classification changes reviewed

| slot | field | census | rc1 | verdict |
|---|---|---|---|---|
| P15 SUMAX | name/symbol/sector | `"SEI Short Duration Municipal F (STET)"` / `SUMAX` | `null`/`null` | fix confirmed — DATA-001 (raw_id DAT-P15-2): wrong-entity name replaced by an honest blank, not new garbage |
| P13 ELCIDIN | sector/industry/symbol | all `null` | `Elcid Investments Limited` / `ELCIDIN.NS` / Financial Services / Investment Company | fix confirmed — DATA-052/DATA-017 class (previously empty, now resolved and populated) |
| P8 NAPEROL | sector/industry | Basic Materials/Chemicals | Financial Services/Investment Company | not a regression — same correct entity name throughout (`Naperol Investments Limited`); reclassification matches the entity's own name (an investment company), consistent with upstream Yahoo classification drift, not a code defect |
| P9, P19 AMAL | symbol suffix | `AMAL.BO` | `AMAL.NS` | fix confirmed — matches DATA-115's fix shape (dual-listed exchange-suffix routing), same entity/name unchanged |
| S3 VERTEX | book_value/price_to_book field_meta | `status: ok` (silent) | `status: flagged`, reason names the 50% share-basis gap | fix confirmed — DATA-005 |
| P12 DHANBANK | held_percent_insiders field_meta | `status: ok` (silent) | `status: flagged`, reason names the promoter-vs-insiders gap | fix confirmed — DATA-004 |
| P2 DAL | quote timestamp/freshness | today's session, no flag | `2025-03-12`, `freshness: stale` | fix confirmed — DATA-006 |
| P2 DAL | income/balance/cashflow | US Delta Air Lines financials, bare `DAL` | `DAL.BO`, INR-scale Indian NBFC financials | fix confirmed — DATA-001 |

## Regression found

**R15-DATA-008 (critical, SIFY currency mislabel)** — the register's own batch-23 note
already flagged this as "may have resurfaced or is incompletely fixed." Live re-check on
the candidate reproduces the exact original symptom: `GET /fundamentals/SIFY` still
serves top-level `"currency": "USD"` next to `revenue_ttm=46506049536.0` /
`net_income_ttm=-912369984.0` — the identical INR-scale numbers the original repro cited
(46.5B vs SIFY's real ~$492M USD revenue) — both with `field_meta.status: "ok"` and no
reason. The candidate does now carry a `financial_currency: "INR"` field and correctly
withholds `price_to_sales`/`price_to_book` for the same currency-mismatch reason (the
DATA-117-class fix), but the two base scalars the entry was filed against
(`revenue_ttm`, `net_income_ttm`) are neither FX-converted nor withheld nor labelled —
only the derived ratios got the treatment. See `findings/rc1-datapack.json`.

## Slots re-diffed (all 24)

P1 JNPR, P2 DAL, P3 CHTR, P4 SAFE, P5 CSL, P6 ICON, P7 JUMBO, P8 NAPEROL, P9 AMAL,
P10 VIYASH, P11 FUSION, P12 DHANBANK, P13 ELCIDIN, P14 JONJUA, P15 SUMAX, P16 CREST,
P17 SIFY, P18 ONC, P19 AMAL, P20 SMR, S1 DHOOTTRANS, S2 SMR, S3 VERTEX, S4 TTC.

## Fixed register entries touching a battery slot (42, spot-checked subset noted above)

R15-DATA-001, 003, 004, 005, 006, 008, R15-AGENT-022, 090, R15-DATA-013, 014, 015, 016,
017, 018, 019, 022, 023, 025, 026, 027, R15-LEAD-011, R15-DATA-048, 049, 050, 051, 052,
053, 054, 055, 056, 057, 058, 060, 076, 115, R15-LEAD-004, 013, 015, 026, 028, 034,
R15-DATA-116 — found by scanning the 395 `fixed` register entries for a `\b<battery
symbol>\b` match anywhere in the entry (`vysted-r15-register.json`) against the 24 names
in `battery/manifest.json`. Slot mapping for each id is in `datapack.json`.

Sidecar :52313 stopped at end of run.
