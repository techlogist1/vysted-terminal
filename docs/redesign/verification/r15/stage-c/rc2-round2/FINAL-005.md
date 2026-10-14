# R15-FINAL-005, round 2: NSE Emerge (SME) fundamentals

Writer: claude-opus-5-5 (judgement tier, effort high), base `d0744711`, branch `r15-r2-final005`.
Own sidecar from source on :52940, keyless data copy `r2-005-data` (seeded from `final-seed-data`,
dev-keystore `{"secrets": {}, "migrated": true}`). No advisor consulted.

## Root cause (live, own sidecar + direct NSE probes)

VOLERCAR (`VOLERCAR-SM.NS`) files quarterly results in Jun and Dec, but its Sep and Mar
Integrated Filings carry only the 6-month context. The Sep-25 XBRL
(`INTEGRATED_FILING_NONINDAS_1568410_07112025065049_WEB.xml`) has one duration context, `OneD`
2025-04-01..2025-09-30. There is no Jul-Sep quarter. The lane's filed periods, newest first:

| period | months | revenue (INR) | net profit | EPS |
|---|---|---|---|---|
| 2026-04-01..2026-06-30 | 3 | 142,105,000 | 10,954,000 | 0.98 |
| 2025-10-01..2026-03-31 | 6 | 266,055,000 | 13,384,000 | 1.20 |
| 2025-10-01..2025-12-31 | 3 | 126,540,000 | 6,417,000 | 0.58 |
| 2025-04-01..2025-09-30 | 6 | 262,386,000 | 21,322,000 | 1.91 |
| 2025-04-01..2025-06-30 | 3 | 123,519,000 | 12,704,000 | 1.14 |

`FiledPeriods.trailing()` walks Q1 FY27 (3) + H2 FY26 (6) = 9 months, then takes H1 FY26 (6)
and reaches 15 months, so it returns `None`. The cadence is `quarterly-gap`. In
`overlay_filed_periods` the sizes block is skipped silently. Growth still serves, because Q1 FY27
has a filed year-ago quarter. That is why revenue_growth and earnings_growth were computed while
revenue_ttm, net_income_ttm, eps, pe_ratio and market_cap stayed null. The cause is not the
`-SM` mapping (the index and the XBRL are reached), not a currency gate, and not the correctness
gate nulling a value. The overlay wrote no field_meta for what it could not size. On the
round-1 fallback path (every provider not_found) the shell starts with an empty meta, so those
nulls had no reason at all. YASHOPTICS works because it files only half-years: two filed halves
form a clean 12-month chain.

There is a second finding. Today Yahoo answers `-SM.NS` names with a name and price shell
instead of not_found. So `/fundamentals` no longer reaches round 1's
`get_fundamentals_from_filings` (it runs only on a ProviderError). With round 1's code, YASHOPTICS
on this sidecar also served revenue/eps/pe/market cap null, stamped only with Yahoo's generic
"provider did not publish this field" (`r2-005-live/before/fund2-*.json`). The fix therefore sits
in the overlay that both paths run (`apply_witnesses` → `overlay_filed_periods`), not in the
fallback.

GANESHIN has the same shape, plus one more gap: its consolidated filings start at Sep-25, so
Apr-Jun 2025 has no consolidated quarter and no chain reaches 2026-06-30.
SUMAX and QUALIANCE have zero rows in the NSE Integrated Filing index.

## Fix (fill only, never replace a provider figure)

- `exchange_financials.FiledPeriods.trailing(best_effort=True)`: an unfiled quarter of a filed
  half-year whose other quarter is filed is derived. Revenue and profit come by subtraction. EPS
  uses the half's implied share count, so a bonus issue between the filings cannot skew it. Each
  derived period records how it was derived. The chain walk skips a period that would overshoot
  12 months. If there is still no chain to the newest end, the newest complete earlier chain is
  returned, and its first period names the end. Plain `trailing()` and `cadence()` are unchanged
  (the R15-LEAD-004 tests pin `quarterly-gap` on this exact shape).
- `correctness_gate.overlay_filed_periods`: it uses best effort only when the provider serves none
  of revenue_ttm, net_income_ttm or eps, so a main-board listing keeps its provider figure and its
  cadence label. Sizes carry `as_of` = the chain end. The label names any derivation, e.g.
  `standalone, sum of 3 periods to 2026-06-30; 2025-07-01..2025-09-30 derived as the filed
  half-year 2025-04-01..2025-09-30 less its filed quarter 2025-04-01..2025-06-30`.
  P/E is re-derived on that EPS, as before.
  - New `_fill_market_cap_from_filed`: when no provider or master market cap exists, market cap
    = ratio price x the share count implied by filed TTM net income / TTM EPS
    (`provider="derived"`, with a basis_note).
  - New `_state_headline_gaps`: any of revenue_ttm, net_income_ttm, eps, pe_ratio or market_cap
    left null, with no meta or only an `unavailable` stamp, gets a typed reason:
    "insufficient filed periods" (with the newest end), "not reported for every period",
    "no trailing EPS", "EPS not positive", "no price", or "no exchange-filed results could be
    read". Withheld and flagged fields keep their own reason.
- `apply_witnesses`: an `-SM.NS` listing whose filings could not be read gets the same floor.
  It is limited to SME because `test_a_served_market_cap_is_never_overridden` pins a meta-less
  main-board payload.
- `provider_registry._fundamentals_from_filings`: it returns the shell whenever a filing was read,
  so the fallback path also carries typed reasons, never a 404. The 404 "no results filing"
  remains only when nothing was read.
- Statements (income/balance) are unchanged from round 1: an empty statement still carries the
  typed SME `reason`. Statements are not built from the filings (not asked for).

## Tests (sidecar/tests/test_final_data_fundamentals.py, +5)

`test_volercar_ttm_is_built_from_its_half_year_less_the_filed_quarter`,
`test_the_derived_fill_never_replaces_a_provider_size`,
`test_ganeshin_serves_the_newest_complete_filed_year_stating_its_end`,
`test_too_few_filed_periods_state_a_typed_reason_on_every_headline_field`,
`test_an_unread_filing_states_why_each_headline_field_is_null`. The fixtures are the live-recorded
VOLERCAR and GANESHIN periods.

Fail before (service changes reverted to `d0744711`, new tests kept):

```
FAILED tests/test_final_data_fundamentals.py::test_volercar_ttm_is_built_from_its_half_year_less_the_filed_quarter
FAILED tests/test_final_data_fundamentals.py::test_the_derived_fill_never_replaces_a_provider_size
FAILED tests/test_final_data_fundamentals.py::test_ganeshin_serves_the_newest_complete_filed_year_stating_its_end
FAILED tests/test_final_data_fundamentals.py::test_too_few_filed_periods_state_a_typed_reason_on_every_headline_field
FAILED tests/test_final_data_fundamentals.py::test_an_unread_filing_states_why_each_headline_field_is_null
5 failed, 13 deselected, 1 warning in 0.35s
```

Pass after: `5 passed, 13 deselected, 1 warning in 0.15s`.

## Live values (own :52940, X-Vysted-Region IN, 2026-10-03 ~20:42 IST)

| name | revenue_ttm | net_income_ttm | eps | pe | market_cap | as_of / basis |
|---|---|---|---|---|---|---|
| VOLERCAR | 54.70 Cr (547,027,000) | 3.30 Cr | 2.952 | 73.27 @216.3 | 241.5 Cr | 2026-06-30, standalone, Jul-Sep 25 derived |
| YASHOPTICS | 53.99 Cr | 9.05 Cr | 3.65 | 37.48 @136.8 | 339.1 Cr | 2026-03-31, 2 filed halves |
| GANESHIN | 835.55 Cr | 76.17 Cr | 17.83 | 4.98 @88.8 | 379.4 Cr | 2026-03-31, consolidated, 2 filed halves |
| TEJASCARGO (fresh) | 628.72 Cr | 20.93 Cr | 8.76 | 46.12 @404 | 965.3 Cr | 2026-03-31, consolidated, 2 filed halves |
| SUMAX | null | null | null | null | null | each: "not published by the data provider; no exchange-filed results could be read for this listing" (pe/mcap name the missing EPS) |
| QUALIANCE | null | null | null | null | null | same typed reasons as SUMAX |

Growth: VOLERCAR +15.0% revenue, -13.8% earnings (Q1 FY27 vs Q1 FY26). YASHOPTICS +29.1%, +17.6%.
TEJASCARGO +31.5%, -19.9%. GANESHIN has no consolidated year-ago quarter, so it shows Yahoo's
generic stamp; growth is not a headline field. Income/balance for VOLERCAR and SUMAX: `periods []`
with the reason "No data provider covers financial statements for this NSE Emerge (SME) listing."

Grounding against the NSE filings:
- VOLERCAR Mar-26 XBRL (`..._1681085_12062026013015_WEB.xml`), `FourD` FY26: revenue
  528,441,000, profit 34,706,000, EPS 3.11. FY26 + Q1 FY27 - Q1 FY26 = 547,027,000 /
  32,956,000 / 2.95, matching the served figures. Paid-up capital 111,435,000 at face value 10
  (the filing states face value 0) gives 11.14 M shares. The implied count is 11.16 M (0.2% off).
- GANESHIN Mar-26 consolidated XBRL (`..._1681637_14062026013222_WEB.xml`), `FourD`: revenue
  8,355,456,000, profit 761,727,000, EPS 17.83, all exact. Paid-up 213,607,000 / face value 5 =
  42.72 M shares, matching the implied 42.72 M.
- TEJASCARGO halves 3,271,078,000 + 3,016,110,000. YASHOPTICS halves 306,140,000 + 233,758,000
  (screener FY26 sales 53.99 Cr).

## Checks

- Touched area (`test_final_data_fundamentals`, `test_b7_exchange_financials`,
  `test_correctness_gate`, `test_fundamentals`, `test_provider_registry`):
  `134 passed, 1 warning in 14.51s`
- Full suite: `3977 passed, 1 skipped, 4 warnings in 224.62s (0:03:44)` / `EXIT=0`
- `ruff format <changed>`: `1 file left unchanged`. `ruff format --check .`: `455 files already
  formatted`. `ruff check .`: `All checks passed!`
- No TS change (model shape unchanged), so no pnpm checks were run.

## Ceilings

- The market-cap share count is a weighted average implied by NI/EPS. It drifts after a fresh
  issue. The upgrade is filed paid-up capital / face value, but VOLERCAR files a face value of 0,
  so this fallback would be needed anyway.
- A stale chain (GANESHIN to 2026-03-31) is served with its end in `as_of` and the label. It is
  never presented as running to the newest quarter.
