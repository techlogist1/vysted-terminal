# Set: batch-9/W2-research-search-news (set-36) — rc1-battery-19 @ ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LIFECYCLE-018 | in-process SearxngManager.ready_base_url_detected, stubbed 1.5 s refresh, two concurrent first reads, then a later read | both concurrent readers got the READY url after the SAME single refresh (flag False during, set after); later read 0.0 s, no second refresh | holds |
| R15-DATA-094 | live: fake key in X-Vysted-Newsapi-Key; /news/sources/status, /news | {"newsapi":"unauthorized"}; header x-news-sources rss=ok;newsapi=unauthorized; key in body 0, in sidecar log 0 | holds |
| R15-UI-033 | frontend render of MarketplacePanel (vitest); not run here | pinned MarketplacePanel.test.tsx + src/store/marketplace.test.ts present; panel .catch at MarketplacePanel.tsx:354, store throws "NewsAPI rejected this key" | ci_pinned (MarketplacePanel.test.tsx, marketplace.test.ts) |
| R15-CROSS-PLATFORM-002 | HYG-2 decode repro + AST scan of sidecar/tests for read_text/write_text without encoding | fixture cp1252 decode still raises (so the fix is needed) but test_search_extract.py:467 reads encoding="utf-8"; 0 unencoded calls in sidecar/tests; guard test_tests_encoding.py present | holds |

COVERAGE: 4/4 ids raw (battery/raw/set-36/); no raw: none
