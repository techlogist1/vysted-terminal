# set-28 — batch-7/W4-research-funnel (rc1-battery-2, gate round 4)

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Every id re-run via an in-process
python call against the candidate's sidecar venv (cwd `sidecar/`), mirroring each
entry's own repro/certification shape. Raw output: `battery/raw/set-28/<id>.txt`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-RESEARCH-019 | `visit_for_research()` with `fetch_page` stubbed to return `HTTP 403` | `VisitResult(text=None, reason='HTTP 403')` — the error survives as a reason, no silent `None` | holds |
| R15-DATA-075 | `_fetch_bse_pdf()` with AttachLive→404, AttachHis→200 stub | retried AttachHis automatically, `final_status=200` | holds |
| R15-RESEARCH-033 | `run_heavy_research(angles=3, ...)` with explorer 2 raising `RuntimeError("explorer boom")` | brief still synthesizes (`brief_has_markdown=True`) and an error step is emitted: `"explorer angle 2 (Angle Beta) failed: RuntimeError: explorer boom"` | holds |
| R15-RESEARCH-020 | `SearxngBackend(stub 40-row client).search(q, options={numResults:3})` | `results=3 citations=3` (was 40/8 pre-fix) | holds |
| R15-RESEARCH-021 | `entity_match()` on "BAJFINANCE 200 DMA breakout…", "BAJFINANCE 52-week high", fresh "KPITTECH 200 DMA test" | all score `1.0` (was `0.0` pre-fix) | holds |
| R15-RESEARCH-022 | `KeylessSearchBackend(engines={'ddg': block-page-stub}).search('q')` | raises typed `SearchError(reason='rate_limited')` naming "DuckDuckGo: blocked (challenge page)"; breaker counts 1 failure (not silently reset) | holds |
| R15-RESEARCH-023 | `_filter_results()` on the Route Mobile "All rights reserved" row + a challenge row | Route Mobile row kept (1), challenge row still blocked (1) | holds |
| R15-RESEARCH-038 | one search failing both `ATTEMPTS_PER_ENGINE` attempts, then a second failed search | after search 1: breaker `closed`, `failures=1`; after search 2: breaker `open` | holds |
| R15-RESEARCH-024 | `SearxngBackend` row with `publishedDate` → `Citation` | `domain='reuters.com' published_at='2026-07-17T10:05:00'` (backend half; frontend Sources-rail render needs GUI, out of battery scope) | holds |
| R15-UI-038 | no live/in-process path available (TS logic, no tsx/ts-node in candidate; vitest suites are the heavy lane's) | certified only via `src/lib/brief-ingest.test.ts:161` | ci_pinned |
| R15-UI-092 | same constraint | certified only via `src/lib/brief-ingest.test.ts` `sanitizeCitationMarkers` → "flags markers exceeding the source count instead of deleting them (R15-UI-092)" | ci_pinned |
| R15-RESEARCH-026 | same constraint | certified only via `src/modules/research/brief-blocks.test.ts:344`/`:359` | ci_pinned |

## Notes

- All 9 sidecar/python entries re-run clean against the fixed code paths present in the
  candidate (`services/search/extract.py::_fetch_bse_pdf`, `services/search/base.py::result_limit`,
  `services/search/keyless.py::_filter_results`/`KeylessSearchBackend`, `services/research/relevance.py::entity_match`,
  `services/research/iter.py::run_heavy_research`) — no regression found.
- The 3 frontend-only entries (UI-038, UI-092, RESEARCH-026) have no live/curl-able repro and
  no in-process JS/TS execution path in this shard (candidate `node_modules/.bin` carries
  `vitest` only, no `tsx`/`ts-node`); per the battery rules, running vitest itself is the
  heavy lane's job, so these are `ci_pinned` naming their exact tests rather than judged from
  the diff.

COVERAGE: 12/12 ids raw; no raw: none.
