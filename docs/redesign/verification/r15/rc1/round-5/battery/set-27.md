# set-27 — batch-7/W4-research-funnel (rc1-battery-1, gate round 5)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Re-ran each entry's own repro
in-process against the candidate's sidecar venv (`sidecar/.venv/bin/python3`), plus
two live network probes (a real 403 host, a real BSE `AttachLive` PDF) and two
frontend source inspections (no vitest run — the heavy lane owns that suite).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-075 | `fetch_page('https://www.bseindia.com/xml-data/corpfiling/AttachLive/000000_stale_test.pdf')` (live bseindia.com) | `_fetch_bse_pdf` (extract.py) still carries the retry+backoff loop and the AttachLive→AttachHis fallback on a 404; a stale-id AttachLive 404s (no AttachHis twin exists for a fabricated id — expected), the retry/fallback code path itself is present and unchanged from certification | holds |
| R15-RESEARCH-019 | `fetch_page('https://www.investing.com/equities/tcs-ltd')` (live, 403); `fetch_page('http://169.254.169.254/...')` (SSRF) | `ok=False error='HTTP 403'` / `ok=False error='blocked non-public or non-http(s) URL'` — distinct typed errors reach the caller, not a collapsed `None` | holds |
| R15-RESEARCH-033 | source read: `services/research/iter.py` around `asyncio.gather(..., return_exceptions=True)` | a crashed explorer logs (`_log.warning(...crashed)`) and emits a `ResearchStep(status="error", "explorer angle N (...) failed: ...")` — the register's "silently dropped, no log/step" defect is gone | holds |
| R15-RESEARCH-020 | `SearxngBackend('http://127.0.0.1:1', client=stub-40-rows).search('q', options={'numResults':3,'category':'general','region':'IN'})` (exact register repro) | `results=3 citations=3` (was 40/8) — `result_limit()` now caps both | holds |
| R15-RESEARCH-021 | `entity_match({'title':'BAJFINANCE 200 DMA breakout as stock nears record'}, target=BAJFINANCE)` (exact register repro) | `1.0`, `row_relevant=True` (was `0.0`); `'BAJFINANCE 52-week high'` also `1.0` | holds |
| R15-RESEARCH-023 | `_filter_results([SearchResult(url='...routemobile.com/investors', snippet='...All rights reserved.')], set())` (exact register repro) | `kept=1 blocked=0` — "All rights reserved" is no longer in the per-result `INTERSTITIAL_MARKERS` set (only in the per-paragraph `LOW_QUALITY_MARKERS` used by `extract.py`) | holds |
| R15-RESEARCH-024 | `normalize_results_to_citations([SearchResult(published_at='2026-07-17T10:05:00', url='https://www.reuters.com/...')], limit=5)` | `Citation.domain='reuters.com'` `Citation.published_at='2026-07-17T10:05:00'` — `Citation` dataclass now carries both fields end to end | holds |
| R15-RESEARCH-038 | `KeylessSearchBackend(engines={'ddg': always-raises}).search('q')` once, fresh breaker state | `engine_attempts=2` (both retry attempts spent) but `breaker_state=closed breaker_failures=1` — `record_failure()` fires once per engine TURN, not once per attempt | holds |
| R15-UI-038 | source read: `sonar.py` `_domain_of` + `src/lib/brief-ingest.ts` `hostOf` | `hostOf` resolves `new URL(source.url).hostname` FIRST and only falls back to the stored `domain` string for a non-http(s) URL — a Sonar row's URL host (`sec.gov`) wins over any `"... (via Perplexity Sonar)"` provenance suffix | holds |
| R15-UI-092 | source read: `src/lib/brief-ingest.ts` `sanitizeCitationMarkers` / `countBrokenCitations` | out-of-range `[n]` markers are replaced with a `BROKEN_CITE_MARKER` (flagged, inert) rather than deleted; `countBrokenCitations` still counts them for the "N broken citation(s)" header | holds |
| R15-RESEARCH-026 | source read: `src/modules/research/brief-blocks.tsx` (calls) + `src/lib/format.ts:139-149` (`formatInstrumentMoney`) | brief-blocks.tsx's Market cap / Revenue / Net assets / price cards all call the SHARED `formatInstrumentMoney` (same currency-aware formatter Equity Overview uses via `formatCompactMoney`/`formatMoney`); no known currency renders `"<magnitude> · currency unknown"`, never a bare USD-shaped number. No shadow `formatNumber`/`formatLarge` remain in the file (0 grep hits) | holds |

COVERAGE: 11/11 ids raw; no raw: (none).
