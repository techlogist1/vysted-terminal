# R15-DATA-068 refutation audit (group data) at HEAD 6741387b

Sidecar on 127.0.0.1:52360 (scratch data dir).

## Entry's own repro
Frontend (Load/Retry short-circuit on the cache, no TTL, no refresh, no as-of chip): at HEAD src/store/analyst-ratings.ts:28 has ANALYST_RATINGS_CACHE_TTL_MS = 15 min, isFresh(fetchedAt) at :42, and refresh() at :173. src/store/earnings.ts:33 has the TTL and refresh() at :211. AnalystRatingsPanel.tsx:120-211 renders an "As of" chip and a Refresh button. `pnpm exec vitest run src/store/analyst-ratings.test.ts src/modules/analyst-ratings/AnalystRatingsPanel.test.tsx src/store/earnings.test.ts ...` -> 5 files, 69 tests passed.
Sidecar envelopes:
```
GET /fundamentals/AAPL/ratings                    200 keys [buy, consensus, hold, provider, sell, strong_buy, strong_sell, symbol, target_high, target_low, target_mean] as_of= None
GET /fundamentals/MSFT/ratings                    200 same keys, as_of= None
GET /fundamentals/AAPL/ratings/individual         200 as_of= 2026-09-25T04:30:22.865298Z
GET /fundamentals/AAPL/ratings/history            200 as_of= 2026-09-25T04:30:23.727975Z
GET /fundamentals/AAPL/ratings/price-target-history 200 as_of= 2026-09-25T04:30:24.145841Z
GET /earnings/AAPL/history                        200 as_of= 2026-09-25T04:30:27.277508Z
GET /earnings/AAPL/surprises                      200 as_of= 2026-09-25T04:30:27.985298Z
GET /earnings/AAPL/estimates                      200 as_of= 2026-09-25T04:30:28.875478Z
GET /earnings/upcoming                            keys [as_of, end_date, events, start_date]
```

## Verifier's refutation (rc1-verifier:9)
Reproduced exactly: the base consensus envelope GET /fundamentals/{symbol}/ratings has no as_of.
Code: sidecar/routers/fundamentals.py:248-256. `rating, _ = await _cached(...)` at :251 computes the cache-row write time and discards it. The route is served from the data cache for _TTL_RATINGS = 6 h (:58). The AnalystRating model (sidecar/models/fundamentals.py:231-244) and its TS mirror (types/data.ts:356-368) have no as_of field. Consumer: the Equity Overview consensus/target block (src/modules/equity-overview/api.ts:115 -> sidecar-client.ts:393 analystRating), which renders a 6 h-old cached consensus with no timestamp.

## Classification: partial
Everything else in the entry holds: the frontend TTL/refresh/chip, the earnings history/surprises/estimates/upcoming envelopes, and the three extended analyst routes. The base analyst consensus envelope is in the entry's stated class ("analyst data ... served from a 6-24h cache without a timestamp") and was never fixed. Batch-10's own VERDICTS line (r15/stage-c/batch-10/VERDICTS.md:29) and the register note record this exact residual ("the base GET /fundamentals/{symbol}/ratings consensus envelope still has none"). The entry was nevertheless closed at f407107. The verifier is correct, but this is an unfixed residual, not a regression.
