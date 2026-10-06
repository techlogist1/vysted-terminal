# batch-9/W2-research-search-news

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Sidecar: rc1-battery-8 shard, source, port 52348 (same as set-27/set-78).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LIFECYCLE-018 | Source read (original batch-9 cert was itself a source read, not a live timed race) of sidecar/app.py:144 + sidecar/services/searxng_manager.py:533-558 | warm_detect() confirmed called from the FastAPI lifespan startup; ready_base_url_detected() confirmed as correct double-checked locking (_hot_path_detected set in `finally` AFTER refresh(), both guarded by the same asyncio.Lock) -- opposite of the pre-fix bug (flag set before the await). | holds |
| R15-DATA-094 | GET /news/sources/status and GET /news?limit=5 with X-Vysted-Newsapi-Key: R15CANARY-B8-fake | {"newsapi":"unauthorized"}; /news carries x-news-sources: rss=ok;newsapi=unauthorized and 5 RSS-only items; fake key 0 occurrences in the sidecar log. | holds |
| R15-UI-033 | No permanent pinned test exists (checked MarketplacePanel.test.tsx, only 3 its, none about credential rejection). Reused the live DATA-094 network leg (identical unauthorized response) + source read of the call chain: marketplace.ts:33-53 probeNewsApiKeyOrThrow -> throws before setSecret is reached; marketplace.ts:192-220 configure() calls the probe before setSecret for vysted-news/newsapi_key and re-throws (finally does not swallow); MarketplacePanel.tsx:349-357 onSubmit .catch(setValidationError). | The live leg the fix depends on (unauthorized status for the fake key) reproduces; the source chain from that response to the form staying open with a message and no keychain write is unbroken. | holds |
| R15-CROSS-PLATFORM-002 | Ran the ONE permanent class-pin test file directly (not the full suite): candidate's .venv `python3 -m pytest sidecar/tests/test_tests_encoding.py -v` | 3 passed: test_every_test_file_names_its_text_encoding, test_scanner_itself_catches_a_missing_encoding (fresh tmp_path case), test_scanner_ignores_a_binary_open_and_an_encoded_call. Original Saksoft fixture read confirmed fixed at test_search_extract.py:464 (encoding="utf-8"). | holds |

COVERAGE: 4/4 ids raw; no raw: none.
