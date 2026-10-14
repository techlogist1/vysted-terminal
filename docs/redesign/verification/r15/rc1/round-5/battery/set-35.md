# batch-9/W2-research-search-news (rc1-battery-10)

Candidate: 9bc600ece2ce6343a6aa48f130d7620b1466bb98. Sidecar :52350.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-CROSS-PLATFORM-002 | The actual defect (Windows-only cp1252 UnicodeDecodeError under a plain pytest step) cannot reproduce on macOS's UTF-8 default locale. Ran the pinned scanner `sidecar/tests/test_tests_encoding.py` in-process (3 tests, 0.45s) against the candidate: all pass, confirming every test file still names its encoding and the scanner itself still catches an unencoded `open()`/`read_text()` | scanner intact; platform-specific crash itself not reproducible off Windows | ci_pinned (sidecar/tests/test_tests_encoding.py) |
| R15-DATA-094 | Live `GET /news/sources/status` with `X-Vysted-Newsapi-Key: R15CANARY-newsapi-fake` -> `{"newsapi":"unauthorized"}`; `GET /news?limit=5` with the same fake key -> 200, header `x-news-sources: rss=ok;newsapi=unauthorized`, body has 0 occurrences of the fake key, sidecar.log has 0 occurrences of the fake key | matches batch-9 certification exactly | holds |
| R15-LIFECYCLE-018 | Source check: `sidecar/app.py:144` still calls `searxng_manager.manager.warm_detect()` from the FastAPI lifespan at boot; `searxng_manager.py:550-558` still flips `_hot_path_detected = True` only in the `finally` of `ready_base_url_detected()`, under `self._detect_lock`, after `await self.refresh()`. Live boot log of my own sidecar shows normal startup with no stall on first search | mechanism unchanged, matches certified fix | holds |
| R15-UI-033 | Frontend-only (marketplace store `configure()` catch on `setSecret` rejection); no sidecar API repro. Source still throws/catches "NewsAPI rejected this key" (marketplace.ts:45,48); pinned vitest `marketplace.test.ts` still asserts `rejects.toThrow("NewsAPI rejected this key")` at two call sites | pinned test intact | ci_pinned (src/store/marketplace.test.ts) |

COVERAGE: 4/4 ids raw; no raw: none.
