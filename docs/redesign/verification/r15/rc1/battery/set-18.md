# batch-6/W1-india-exchange-data

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DATA-017 | `GET /disclosures/announcements?symbol=QUALIANCE&limit=25`, `/disclosures/shareholding?symbol=QUALIANCE`, `/disclosures/results?symbol=QUALIANCE` against candidate `:52344` | announcements 200/4 rows (headline "...Resignation of Mrs KRUPA RAJESH BADANI..." matches batch-6 evidence exactly); shareholding 200, promoter_percent=63.66 (matches); results 200/0 events | holds |
| R15-DATA-027 (+014 DAL leg, +076: one class) | `GET /fundamentals/DAL`, `/fundamentals/FUSION` | DAL revenue_ttm=99,700,000 (≈9.97cr, matches PLAN's screener.in figure), provider=bse, field_meta.reason states Yahoo's 27,600,000 disagrees and is not served; FUSION revenue_ttm=17,144,200,000 (≈1,714cr, matches PLAN's ≈1,699cr ballpark), provider=nse, Yahoo's 8,582,000,128 disclosed-not-served. DAL revenue_growth=45.2% (provider bse); FUSION revenue_growth=5.46% (provider nse) vs Yahoo's disclosed 128.1% divergence noted in field_meta.reason (DATA-076 growth-witness class) | holds |
| R15-LEAD-004 | `GET /fundamentals/JONJUA`, `/fundamentals/DHANBANK` | JONJUA field_meta.revenue_ttm.reason = "TTM basis: ... a half-yearly filer ... annual, not trailing-4Q; kept, flagged" (keeps its half-yearly label); DHANBANK field_meta.revenue_ttm.status=ok, provider=nse, sum-of-4-filed-quarters label — NOT labelled half-yearly | holds |
| R15-LEAD-015 | `GET /fundamentals/DHANBANK/income?period=quarterly` | response has explicit `gaps: ["2025-09-30"]` field; `periods` are ISO period-end dates (2026-06-30, 2026-03-31, ... 2025-03-31) | holds |
| R15-DATA-050 (+060: one class) | `GET /disclosures/results?symbol=JONJUA`, `?symbol=DAL`, `?symbol=ELCIDIN`, `/disclosures/shareholding?symbol=AAPL`, `/disclosures/shareholding?symbol=SIFY` | JONJUA/DAL/ELCIDIN (all BSE-only) results all 200 with events (10 each); AAPL shareholding 200 `coverage:"not_applicable"`, note "AAPL is not an NSE/BSE instrument..."; SIFY shareholding 200 `coverage:"covered"`, `provider:"sec-20f"`, major_shareholders populated from its 20-F (Infinity Capital Ventures 7.56%, Raju Vegesna Infotech 7.9%, etc.) | holds |

All 8 register entries in this writer set (DATA-017, DATA-027, DATA-014, DATA-076, LEAD-004, LEAD-015, DATA-050, DATA-060) re-verified live against the candidate sidecar (`:52344`, port-52344 booted from the rc1 candidate worktree source, seed data copy `rc1-data-rc1-battery-4`). No regressions found in this set.

Raw output: `docs/redesign/verification/r15/rc1/battery/raw/set-18/*.txt`.
