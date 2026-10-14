# R15-LEAD-137, attempt 2: DECISIONS 5.14 fail-safe (SME P/E)

Base `b7d37fd9`, branch `r15-fs-lead137`. Writer: Opus 5.5 (`claude-opus-5-5`), medium.

## Root cause

The overlay runs twice on the SME path.

1. `provider_registry._fundamentals_from_filings` serves the filings-only shell via
   `overlay_filed_periods`. That pass is filings-only, so `_size_on_current_count` sets
   P/E = market cap (current share count) / TTM NI. CURIS: 24.14.
2. The route then calls `correctness_gate.apply_witnesses`, which re-runs
   `overlay_filed_periods` on the filled shell. Revenue/NI/EPS are now non-null, so
   `filings_only` was False. Strict `trailing()` succeeds on names with a strict trailing year,
   so `_rebase_pe_on_filed_eps` overwrote P/E with price / summed filed EPS (weighted count).
   CURIS: 18.59. The same pass also filled a typed-null P/E (no current count) with price / EPS.

Attempt 1's tests called the overlay once, so they never saw pass 2.

## Fix (`sidecar/services/correctness_gate.py`, +7 / -1)

`filings_only = f.provider == filed.venue or <no provider size>`. The filings stand-in's shell
is the only Fundamentals built with `provider = filed.venue` (no provider constructs one with
`nse`/`bse`). It stays filings-only on every later pass. So pass 2 skips the EPS rebase and
re-runs `_size_on_current_count`, which is idempotent: the market cap is kept, P/E = cap / TTM
NI, or a typed null ("current share count unavailable", "no trailing net income"). Provider-sized
main-board names (`provider = yfinance` etc.) keep the R15-FINAL-003 rebase unchanged.

## Tests (`sidecar/tests/test_final_data_fundamentals.py`, +82)

- `test_curis_route_pe_survives_the_gates_second_overlay_pass`: `GET /fundamentals/CURIS`
  in-process via TestClient, real `apply_witnesses` (second pass), stubbed providers and filings.
- `test_no_current_count_route_pe_stays_a_typed_null_through_the_gate`: same route, no current
  count. P/E must stay a typed null.
- `test_a_provider_sized_listing_keeps_its_filed_eps_pe_on_a_second_pass`: main-board guard
  (overlay twice still gives price / filed EPS). It passes at base by design.

Fail before (fix stashed, base code):

```
E       assert 12.151215121512152 == 15.780093257955844 ± 1.6e-05     (price 135 / EPS 11.11)
E       assert 12.151215121512152 is None
2 failed, 1 passed, 25 deselected, 1 warning in 0.29s
```

Pass after: `3 passed, 25 deselected, 1 warning in 0.12s`.

## Live (own source sidecar :52940, keyless seed copy, region IN, `GET /fundamentals/<SYM>`)

Raw JSON and screener HTML were saved under the writer's scratch `fs137-live/`. screener.in was
fetched on 3 Oct 2026.

| name | ours mcap | ours P/E (basis) | screener.in | gap |
|---|---|---|---|---|
| CURIS | 166.9 Cr | 24.14 (cap on current count / TTM NI) | 167 Cr / 24.1, https://www.screener.in/company/CURIS/ | 0.1% / 0.2% |
| SHETHJI | 416.5 Cr | 20.91 (same) | 419 Cr / 21.0, https://www.screener.in/company/SHETHJI/ | 0.6% / 0.4% |
| FINBUD | 234.3 Cr | 20.43 (same) | 241 Cr / 20.7, https://www.screener.in/company/FINBUD/ | 2.8% / 1.3% (quote 123 vs 126) |
| VOLERCAR | 241.0 Cr | 73.14 (same) | 241 Cr / 73.0, https://www.screener.in/company/VOLERCAR/ | 0% / 0.2% |
| GANESHIN | 388.7 Cr | 5.10 (same) | 379 Cr / 5.15, https://www.screener.in/company/GANESHIN/ | 2.6% / 1.0% (quote 88.8 vs 86.6) |

Every name now serves the basis "market cap on the current share count / exchange-filed TTM net
income ... shares from the NSE quote issued size". No name serves price / EPS.

## Checks

- Touched area (final_data_fundamentals, correctness_gate, b7_exchange_financials,
  exchange_financials_negcache, fundamentals, fundamentals_tool, fundamentals_basis,
  provider_registry, provider_registry_region): `189 passed, 1 warning in 15.80s`, EXIT=0.
  This includes the R15-FINAL-003 tests (SUNRAJDI rebase, higher filed EPS, non-positive EPS) and
  `test_a_provider_sized_listing_keeps_its_pe_on_the_filed_eps`.
- Full suite: `4006 passed, 1 skipped, 4 warnings in 220.15s (0:03:40)`, EXIT=0.
- `ruff format <changed>`: "2 files left unchanged". `ruff format --check .`: "455 files already
  formatted". `ruff check .`: "All checks passed!".
- No TS change.
