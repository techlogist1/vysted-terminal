# batch-12/W8-design-token-gate — rc1-battery-11 (shard 11)

Candidate sha `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. Method: direct repo
reads + a standalone `node scripts/audit-design-tokens.mjs` run (not via
`pnpm ci-local`, which the heavy lane owns), plus live GETs against
rc1-battery-11's own sidecar (`:52351`, reaching the shared read-only
sec-edgar-mcp on `:52154` for real SEC EDGAR data). Raw output:
`battery/raw/set-61/<id>.txt`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-RELEASE-007 | `grep audit-design package.json`; `node scripts/audit-design-tokens.mjs` | `package.json` `lint` now chains the audit (`eslint . && node scripts/audit-design-tokens.mjs`), which `ci-local`'s `pnpm lint` step and the lint workflow both inherit; standalone run exits 0, "design-token audit clean (373 files)" | holds |
| R15-LEAD-010 | `GET /sec/filings?symbol=AAPL&form_type=10-K`, then `GET /sec/filings/{accession}?identifier=AAPL&form_type=10-K` for both a recent (2025) and an old (2021, outside the unfiltered 40-window) AAPL 10-K | both accessions resolve HTTP 200 with real filing sections, no 404; router (`sec_filings.py`) now accepts and forwards `form_type` as a lookup hint on both `/filings/{accession}` and `/filings/{accession}/sections` | holds |

COVERAGE: 2/2 ids raw; no raw: none.
