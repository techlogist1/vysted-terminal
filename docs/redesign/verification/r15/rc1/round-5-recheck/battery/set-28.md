# batch-7/W4-research-funnel (set-28) — rc1-battery-2, gate round 5-recheck

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. 9 sidecar/python entries re-run via
in-process calls (real code, candidate's own `sidecar/.venv`); 3 frontend-only entries are
`ci_pinned` (vitest is the heavy lane's job, never run here). No sidecar boot was strictly
needed for this set (all in-process), but the shard's shared sidecar on `:52342` was booted
per the role instructions and reused for set-45/set-64. Raw output: `raw/set-28/<id>.txt`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-RESEARCH-019 | `visit_for_research()` with `fetch_page` stubbed to return `HTTP 403` | `VisitResult(text=None, reason='HTTP 403')` — the error survives as a reason, no silent `None` | holds |
| R15-DATA-075 | `_fetch_bse_pdf()` with AttachLive→404, AttachHis→200 stub | AttachHis retried automatically, `final_status=200` | holds |
| R15-RESEARCH-033 | Code read (no live LLM/tool infra in this shard): `iter.py:1067-1077` — `asyncio.gather(return_exceptions=True)` + explicit crash-step recording + `good` filter | crashed explorer angle excluded from `good`, a `ResearchStep(status="error")` naming the failure is appended/emitted, synthesis proceeds on survivors | holds |
| R15-RESEARCH-023 | `_filter_results()` on the Route Mobile "All rights reserved" snippet row | kept=1 blocked=0 — the row survives (LOW_QUALITY_MARKERS is per-paragraph on extracted pages only, not applied to SERP-row snippets) | holds |
| R15-RESEARCH-038 | `CircuitBreaker()` + 2× `record_failure()`; `ATTEMPTS_PER_ENGINE`/`DEFAULT_FAIL_THRESHOLD` constants | both constants still `2`; breaker closed→open after exactly 2 failures (one fully-failed search) | holds |
| R15-RESEARCH-024 | `normalize_results_to_citations()` on a Reuters row with `published_at` set | `domain='reuters.com' published_at='2026-07-17T10:05:00'` (backend half; frontend Sources-rail render needs GUI, out of battery scope) | holds |
| R15-UI-038 | no live/in-process path (TS logic, vitest is the heavy lane's) | certified only via `src/lib/brief-ingest.test.ts:161` "prefers the URL host over a provenance-labelled domain (R15-UI-038)" — test present | ci_pinned |
| R15-RESEARCH-020 | `SearxngBackend(stub 40-row client).search(q, options={numResults:3})` | `results=3 citations=3` (was 40/8 pre-fix) | holds |
| R15-RESEARCH-021 | `entity_match()` on "BAJFINANCE 200 DMA breakout…", "BAJFINANCE 52-week high", fresh "KPITTECH 200 DMA test" | all score `1.0` (was `0.0` pre-fix) | holds |
| R15-UI-092 | same constraint (TS, vitest not run) | certified only via `src/lib/brief-ingest.test.ts` "flags markers exceeding the source count instead of deleting them (R15-UI-092)" — test present | ci_pinned |
| R15-RESEARCH-026 | same constraint (TS, vitest not run) | certified only via `src/modules/research/brief-blocks.test.ts` "an unknown currency is stated, never defaulted (R15-RESEARCH-026)" — test present | ci_pinned |

## Notes

- All 9 sidecar/python entries re-run clean against the fixed code paths present in the
  candidate at `949c3c9f` (`services/search/extract.py::visit_for_research`/`_fetch_bse_pdf`,
  `services/search/base.py::result_limit`/`normalize_results_to_citations`,
  `services/search/keyless.py::_filter_results`, `services/search/breaker.py::CircuitBreaker`,
  `services/research/relevance.py::entity_match`, `services/research/iter.py::run_heavy_research`)
  — no regression found; behaviour matches round-4's own re-run of this same set at a prior
  candidate (`1006c6da`), read as precedent, never as this round's evidence.
- RESEARCH-033 is a code read, not a live `run_heavy_research()` execution — a full live call
  needs LLM/tool/budget infra this shard does not stand up; the exact code slice the register's
  own repro names was read and confirms the mechanism unchanged.
- The 3 frontend-only entries (UI-038, UI-092, RESEARCH-026) have no live/curl-able repro and
  vitest is the heavy lane's job per the battery rules — `ci_pinned` naming their exact tests
  (all present, greped directly from source, not copied from a prior round).

COVERAGE: 11/11 ids raw; no raw: none.
