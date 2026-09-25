# batch-10/W3-fundamentals-bse-cache (rc1-battery-7)

Candidate `4097dac4`. Own sidecar on `:52347`, data copy of the iso-seed profile. All 7
certified entries re-run live against the candidate's own routes (no full test suite run).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-048 | `GET /fundamentals/RELIANCE.NS`, `/CREST.NS`, `/AMAL.NS` | roce RELIANCE 0.08994, CREST 0.03686, AMAL 0.22332 — matches cert (0.0899/0.0369/0.2233); `field_meta.roce.provider=derived`, basis_note "annual EBIT / (total assets - current liabilities)" | holds |
| R15-DATA-054 | same fetches, `basis` field | RELIANCE `consolidated`, CREST `consolidated`, AMAL/ELCIDIN `null`; `field_meta.basis.provider=exchange-filings` (the f4ef5673 fix is present) | holds |
| R15-DATA-055 | listing_date on AMAL, DHOOTTRANS, RELIANCE, TCS | AMAL 2026-08-17, DHOOTTRANS 2026-08-17, RELIANCE 1995-11-29, TCS 2004-08-25 — exact match to cert | holds |
| R15-DATA-053 | `GET /quotes/ICON.BO`, `/quotes/ICONIKSPEV.BO` | ICON.BO: provider=bse, price 64.45, volume 1200, open/high/low 64.45, prev_close 63.06 (exact match); ICONIKSPEV.BO: volume 5967, open 33.95, high 33.95, low 32.57 (exact match) | holds |
| R15-DATA-096 | `GET /fundamentals/AAPL/income` twice, timed | cold 0.36s, warm (repeat) 0.00s, identical payload — cache hit confirmed | holds |
| R15-DATA-068 | `GET /earnings/AAPL/history`, `/fundamentals/AAPL/ratings/{history,individual,price-target-history}` | all 4 routes carry a populated `as_of` timestamp | holds |
| R15-LEAD-024 | `GET /macro/WEO%2FUSA.NGDP_RPCH.A?provider=imf` | 2023 2.93/false, 2024 2.79/false, 2025 2.12/true, 2026 2.32/true, 2031 1.76/true — exact match to cert's is_projection pattern | holds |

Excluded (not certified in batch-10): R15-DATA-071 (fall-through leg left open by writers).

Raw output: `battery/raw/set-40/*.json`.
