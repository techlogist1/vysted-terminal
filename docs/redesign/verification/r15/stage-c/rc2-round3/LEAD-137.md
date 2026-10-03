# R15-LEAD-137, round 3, attempt 1: SME market cap and P/E on the current share count

Writer: claude-opus-5-5 (judgement tier, effort medium). Base `ae6ffff0`, branch `r15-r3-lead137`.
Own sidecar from source on :52940 (MCP ports 0), keyless data copy `r3-137-data` seeded from
`final-seed-data`, dev-keystore `{"secrets": {}, "migrated": true}`. No advisor consulted.

## Root cause

Round 2 (FINAL-005) added `correctness_gate._fill_market_cap_from_filed`. It set market cap to
price x (TTM net income / TTM EPS). That ratio is the weighted-average share count, and it lags
a fresh issue. The P/E was price / summed filed EPS, which uses the same weighted count. CURIS
listed on 14 Nov 2025. Its H1 FY26 filing carries paid-up capital 59,344,000 (5.93 M shares) and
its H2 filing 80,844,000 (8.08 M). The summed EPS is 7.10 + 4.01 = 11.11, which implies 6.23 M
shares. So the served market cap was 128.6 Cr and the P/E 18.59, against 167 Cr / 24.1.
The fill also ran on a provider-sized (main-board) payload that had no market cap.

## Fix (DECISIONS 5.14 fail-safe)

- `nse_provider.get_issued_size` is new and read-only. It does not change the throttle, lane or
  breaker. `api/quote-equity` still 403s from this vantage (re-probed today). The quote page's
  own API serves: `api/NextApi/apiClient/GetQuoteApi?functionName=getMetaData` returns
  `activeSeries` (CURIS trades `ST`, not `SM`), and `functionName=getSymbolData&series=<it>`
  returns `equityResponse[0].tradeInfo.issuedSize`. Live values: CURIS 8,084,434, VOLERCAR
  11,143,527, YASHOPTICS 24,765,600, GANESHIN 43,770,997.
- `exchange_financials`:
  - `parse_nse_xbrl` now reads `PaidUpValueOfEquityShareCapital` and
    `FaceValueOfEquityShareCapital` into `FiledPeriod.paid_up` / `face_value`.
  - The NSE lane reads the issued size for a `-SM.NS` listing only. It is cached with the walk.
    A failed read is logged and leaves the filed periods intact.
  - New `FiledPeriods.current_shares()`: the issued size first. Otherwise the newest filed
    paid-up / face value, used only when face value > 0 (VOLERCAR files 0). It returns the
    provenance string with the count.
- `correctness_gate`:
  - `_fill_market_cap_from_filed` (the weighted fill) is removed.
  - When the filings alone size the listing (no provider revenue, net income or EPS: the SME
    path), new `_size_on_current_count` sets market cap = ratio price x current count. It never
    replaces a provider or master figure.
  - P/E = that market cap / exchange-filed TTM net income. Both are `derived`, and the
    basis_note names the count and its source.
  - With no current count, both are null with an `unavailable` reason that contains "current
    share count unavailable". Net income not positive, or not reported: P/E null with the reason
    stated. With no TTM chain, market cap is still served from the current count, and P/E keeps
    the "no trailing EPS" reason.
  - Revenue, net income and EPS are unchanged from round 2. The main-board P/E path is
    unchanged: `_rebase_pe_on_filed_eps` (R15-FINAL-003) still runs for a provider-sized
    payload. The only main-board change is that the weighted market cap fill is gone, so
    such a payload states "current share count unavailable" instead.

## Tests (`sidecar/tests/test_final_data_fundamentals.py`)

New tests:
- `test_curis_market_cap_and_pe_use_the_current_issued_count_not_ni_over_eps`: the live CURIS
  periods. Market cap is 166.9 Cr and P/E 24.1. The result is more than 20% away from the
  weighted figure.
- `test_curis_without_the_quote_count_falls_back_to_the_newest_filed_paid_up`
- `test_no_current_share_count_leaves_market_cap_and_pe_null_with_a_typed_reason` (face value 0,
  no quote count)
- `test_a_provider_sized_listing_keeps_its_pe_on_the_filed_eps`
- `test_the_emerge_lane_reads_the_issued_size_and_survives_its_failure`
- `test_get_issued_size_reads_the_active_series_trade_info`
- `test_parse_nse_xbrl_reads_paid_up_capital_and_face_value`

Round-2 tests (Tier-3 decision, recorded here): three assertions pinned the defect itself.
They checked P/E = price / summed EPS and market cap = price x NI/EPS (`"imply"` in the
basis_note). Those assertions now check the corrected figures, priced on the live-recorded
current count. `_VOLERCAR_FILED` gets `issued_shares=11_143_527`, and `_YASH_FILED` gets its
filed paid-up 247,656,000 at face value 10, which exercises the paid-up path. Every revenue,
net income, EPS, label and as_of assertion is unchanged, and no test was deleted or skipped.
GANESHIN's test is unchanged.

Fail before, full base services (`ae6ffff0`) with the new tests:
```
E   TypeError: FiledPeriod.__init__() got an unexpected keyword argument 'paid_up'
ERROR tests/test_final_data_fundamentals.py - TypeError: FiledPeriod.__init__...
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
```
Fail before, with only `correctness_gate.py` reverted to `ae6ffff0` (data plumbing kept so the
module collects):
```
FAILED tests/test_final_data_fundamentals.py::test_yashoptics_fundamentals_come_from_the_nse_filings
FAILED tests/test_final_data_fundamentals.py::test_volercar_ttm_is_built_from_its_half_year_less_the_filed_quarter
FAILED tests/test_final_data_fundamentals.py::test_the_derived_fill_never_replaces_a_provider_size
FAILED tests/test_final_data_fundamentals.py::test_curis_market_cap_and_pe_use_the_current_issued_count_not_ni_over_eps
FAILED tests/test_final_data_fundamentals.py::test_curis_without_the_quote_count_falls_back_to_the_newest_filed_paid_up
FAILED tests/test_final_data_fundamentals.py::test_no_current_share_count_leaves_market_cap_and_pe_null_with_a_typed_reason
FAILED tests/test_final_data_fundamentals.py::test_a_provider_sized_listing_keeps_its_pe_on_the_filed_eps
7 failed, 18 passed, 1 warning in 0.48s
```
Pass after: `25 passed, 1 warning in 0.27s`.

## Live values (own :52940, X-Vysted-Region IN, 2026-10-03 21:57-22:03 IST)

| name | price | market cap | P/E | basis | grounding (URL, value) | off |
|---|---|---|---|---|---|---|
| CURIS | 206.5 | 166.94 Cr | 24.14 | 206.5 x 8,084,434 (NSE issued size); / NI 69,163,000 | https://www.screener.in/company/CURIS/ 167 Cr, P/E 24.1. NSE getSymbolData totalMarketCap 1,669,435,621, pdSymbolPe 24.14 | 0.0% / 0.2% |
| VOLERCAR | 216.3 | 241.03 Cr | 73.14 | 216.3 x 11,143,527; / NI 32,956,000 | https://www.screener.in/company/VOLERCAR/ 241 Cr, P/E 73.0 | 0.0% / 0.2% |
| GANESHIN | 88.8 | 388.69 Cr | 5.10 | 88.8 x 43,770,997; / NI 761,727,000 | https://www.screener.in/company/GANESHIN/ 379 Cr @ 86.6, P/E 5.15 | 2.6% (the price-lane gap 88.8 vs 86.6; the share count is identical: 379 Cr / 86.6 = 43.8 M) / 0.9% |
| AVANA (listed 20 Jan 2026) | 125.25 | 283.63 Cr | null | 125.25 x 22,645,408. P/E: "no trailing EPS to derive it from (the NSE filings (newest period to 2026-03-31) do not cover a trailing 12 months — insufficient filed periods)" | https://www.screener.in/company/AVANA/ 287 Cr @ 127 (P/E 24.5) | 1.2% (price) / typed null |
| VICTORYEV (listed 14 Jan 2026) | 13.5 | 32.52 Cr | null | 13.5 x 24,090,000. P/E typed null, as for AVANA | not grounded separately | |

Before (`ae6ffff0`, round-2 verifier): CURIS 128.6 Cr / 18.59. Revenue, net income and EPS
for CURIS (60.63 Cr / 6.92 Cr / 11.11), VOLERCAR and GANESHIN are the round-2 figures.
A first CURIS call hit a transient NSE connection reset ("no exchange-filed results could be read"
typed reason, negative-cached 5 min); the retry after expiry served the row above.

## Checks

- Full suite `.venv/bin/python -m pytest tests -q`: `3996 passed, 1 skipped, 4 warnings in 218.62s (0:03:38)`, `EXIT=0`.
- Touched area (`test_final_data_fundamentals`, `test_b7_exchange_financials`, `test_correctness_gate`, `test_nse_provider*`): `111 passed, 1 warning in 9.93s`.
- `ruff format <changed>`; `ruff format --check .`: `455 files already formatted`; `ruff check .`: `All checks passed!`.
- No TS change.

## Residuals (not in this entry)

- AVANA's P/E is null because its NSE filings do not chain a trailing year. screener shows 24.5
  from the FY26 annual figures. That is a coverage gap stated with a typed reason, not a wrong
  figure.
- The agent `fundamentals` tool (`apply_exchange_financials`) uses the same overlay and the same
  `FiledPeriods`, so it gets the current count too. The REST/agent split in VERIFY N1 is
  separate.
