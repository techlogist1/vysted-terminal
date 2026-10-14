# batch-9/W2-research-search-news (rc1-battery-7)

Candidate `4c6dfe8c`. Own sidecar on `:52347`. 4 certified entries re-run (authoritative
entry list per `battery/INDEX.json` / batch-9 `PLAN.md` — the task's copied entry list for
this set (`RESEARCH-074, RESEARCH-076, RESEARCH-078, DATA-070`) does not match any real
batch-9 entry (none of those ids belong to batch-9's W2 set); treated as a harness
transcription error, logged in notes, worked from the authoritative batch-9 W2 roster
instead).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CROSS-PLATFORM-002 | `pytest tests/test_tests_encoding.py -v` (single committed guard file, not the full suite) + `grep read_text` on the fixed call site | 3 passed (`test_every_test_file_names_its_text_encoding`, `test_scanner_itself_catches_a_missing_encoding`, `test_scanner_ignores_a_binary_open_and_an_encoded_call`); `test_search_extract.py:467` reads `fixture.read_text(encoding="utf-8")` — the fix and its AST-scan guard both intact | holds |
| R15-DATA-094 | `GET /news/sources/status` + `GET /news?limit=5` with `X-Vysted-Newsapi-Key: R15CANARY-newsapi-fake` | `{"newsapi":"unauthorized"}`; response header `x-news-sources: rss=ok;newsapi=unauthorized`; fake key appears 0 times in the response body — matches cert | holds |
| R15-LIFECYCLE-018 | `grep sidecar/services/searxng_manager.py` `ready_base_url_detected`/`warm_detect` | `_hot_path_detected = True` sits in the `finally` block AFTER `await self.refresh()`, under `self._detect_lock`; `app.py:144` calls `warm_detect()` at lifespan boot — fix mechanism unchanged | holds |
| R15-UI-033 | `grep src/modules/marketplace/MarketplacePanel.tsx` around the `configure()` call | `configure(...).then(onDone).catch((err) => ...)` — the `.catch` (missing pre-fix) is present, comment cites R15-UI-033 by id | holds |

Raw output: `battery/raw/set-36/*`.
