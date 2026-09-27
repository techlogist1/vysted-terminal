# batch-9/W2-research-search-news (set-36) — rc1-battery-5, gate round 4

Own sidecar :52345 (candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad, seed-data copy `rc1-round-4-data-battery-5`).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LIFECYCLE-018 | Live: code confirms `searxng_manager.manager.warm_detect()` called from `app.py:144`'s lifespan at boot (fire-and-forget, comment cites R15-LIFECYCLE-018); post-boot `GET /search/searxng/status` answered in 1.556s, not a fresh docker-derivation stall (the ~15s budget only applies to the FIRST ever call per process, already absorbed at boot) | fast post-boot status read, matches the certified "hot-path flag flips after refresh() completes at boot" fix | holds |
| R15-DATA-094 | Live: `GET /news/sources/status` with `X-Vysted-Newsapi-Key: R15CANARY-newsapi-fake-b5` -> `{"newsapi":"unauthorized"}`; keyless -> `{"newsapi":"absent"}`; the fake key string appears 0 times in the sidecar log | fake key detected as unauthorized synchronously, never leaks to logs | holds |
| R15-UI-033 | Code: `src/modules/marketplace/MarketplacePanel.tsx` `CredentialForm` submit handler still has `configure(...).then(onDone).catch(setValidationError)` (comment cites R15-UI-033); no permanent vitest test covers this exact scratch-rendered scenario, so verified by code + the live backend rejection above (same 401->unauthorized path the catch depends on) | error path present and unchanged | holds |
| R15-CROSS-PLATFORM-002 | ci_pinned: `sidecar/tests/test_tests_encoding.py` (permanent pytest audit, not run — heavy lane's). Static check: `test_search_extract.py:467` now reads the Saksoft fixture with `encoding="utf-8"`; the other 12 named call sites (`test_nse_provider.py`, `test_corporate_disclosures.py`, `test_bse_provider.py`, `test_no_tradesa.py`) all pass `encoding=` too (0 bare `read_text()` calls remain) | — | ci_pinned |

COVERAGE: 4/4 ids raw; no raw: (none).
