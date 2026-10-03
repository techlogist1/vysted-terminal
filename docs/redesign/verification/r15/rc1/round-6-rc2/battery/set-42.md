# Set: batch-10/W3-fundamentals-bse-cache (set-42) — rc1-battery-21 @ ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-048 | GET /fundamentals/{RELIANCE,CREST,AMAL}.NS on own sidecar :52361 | roce present: 0.08994 / 0.03686 / 0.22332 (same values the batch verifier certified; screener.in divergence is the verifier's filed issue) | holds |
| R15-DATA-054 | GET /fundamentals/{RELIANCE,CREST,AMAL}.NS | basis 'consolidated' / 'consolidated' / null (no filing) | holds |
| R15-DATA-055 | GET /fundamentals/AMAL.NS, RELIANCE.NS (+ field_meta) | listing_date 2026-08-17 / 1995-11-29; fifty_two_week_high_date 2026-08-20, low_date 2026-09-28; forward_pe_fiscal_year field present (null); per-field as_of differs per leg | holds |
| R15-DATA-053 | GET /quotes/ICON.BO, /quotes/ICONIKSPEV.BO | provider bse; ICON volume 2400, open/high/low/prev_close populated; ICONIKSPEV volume 7934, o/h/l 33.66/33.66/31.98 | holds |
| R15-DATA-096 | GET /fundamentals/AAPL/{income,balance,cashflow,ratings} twice | first 0.23-0.35 s, repeat 0.001 s on all four (now cached); MAX_ROWS ceiling pinned by test_data_cache (ci) | holds |
| R15-DATA-068 | GET /earnings/AAPL/{history,surprises,estimates}, /earnings/upcoming, /fundamentals/AAPL/ratings{,/history,/individual,/price-target-history} | every envelope carries as_of (incl. base /ratings, newer than the verifier's note); panel chip pinned by vitest AnalystRatingsPanel (heavy lane) | holds |
| R15-LEAD-024 | GET /macro/WEO%2FUSA.NGDP_RPCH.A and WEO%2FIND.PCPIPCH.A provider=imf (live api.imf.org) | 2018-2024 is_projection false; 2025-2031 true on both series | holds |

COVERAGE: 7/7 ids raw (battery/raw/set-42/); no raw: none
