# batch-9/W2-research-search-news (rc1-battery-7)

Candidate `4097dac4`. Own sidecar on `:52347`. 6 certified entries re-run.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LIFECYCLE-018 | `grep` `sidecar/app.py` lifespan | `# R15-LIFECYCLE-018: derive the managed SearXNG's world state at boot instead of lazily on the first research request` — `searxng_manager.manager.warm_detect()` called directly in the lifespan, before `yield` | holds |
| R15-DATA-094 | `GET /news/sources/status`, `GET /news` with `X-Vysted-Newsapi-Key: <fake>` | `{"newsapi":"unauthorized"}`; response header `x-news-sources: rss=ok;newsapi=unauthorized`; no key echoed in body | holds |
| R15-UI-033 | `grep` `src/store/marketplace.ts` (cert evidence was a scratch, never-committed render of `MarketplacePanel`) | `throw new Error("NewsAPI rejected this key")` at :45, caught and surfaced verbatim at :48 — the exact string the sidecar's 401 maps to, keychain write gated on success | holds |
| R15-CROSS-PLATFORM-002 | test file presence: `sidecar/tests/test_tests_encoding.py` (cert evidence was a fresh scratch test file with unencoded `open()`/`read_text()` calls, deleted after) | file present (the checker itself); no permanent fixture to re-run (the offending scratch file was cert-local and removed) | ci_pinned |
| R15-UI-083 | GUI check (Save .md/PDF/PNG raster of a settled brief) | no GUI available to this headless shard | needs_gui |
| R15-UI-050 | GUI check (whether a two-line Notes slash row still clips) | no GUI available to this headless shard | needs_gui |

Excluded (not certified in batch-9): R15-RESEARCH-028 (still not certified — searxng quality
gate order, see set-42 for the batch-10 fix that supersedes it), R15-AGENT-063, R15-UI-032.

Raw output: `battery/raw/set-34/*`.
