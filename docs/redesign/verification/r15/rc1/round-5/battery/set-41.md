# set-41 — batch-10/W3-fundamentals-bse-cache (rc1-battery-1, gate round 5)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Live GETs against my own isolated
sidecar (`127.0.0.1:52341`, isolated data copy) plus source inspection.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-048 | `GET /fundamentals/RELIANCE.NS`, `CREST.NS`, `AMAL.NS`, `ELCIDIN.NS` (register/certification symbols) | `roce` field present with `field_meta.roce`: RELIANCE 0.08994 (basis_note "annual EBIT / (total assets - current liabilities)"), CREST 0.03686, AMAL 0.22332 (all `provider: derived`) — matches batch-10 VERDICTS.md's certified values exactly; ELCIDIN `roce=None` with an honest `reason: "insufficient statement data to derive ROCE"`, never a fabricated number | holds |
| R15-DATA-054 | Same 4 GETs, `basis` + `field_meta.basis` | RELIANCE/CREST `basis="consolidated"` (`provider: exchange-filings`, `status: ok`); AMAL/ELCIDIN `basis=None` with `reason: "no NSE/BSE filing states a basis"` — the response now names its accounting basis or honestly says it doesn't know, never a silent default | holds |
| R15-DATA-096 | `GET /fundamentals/AAPL/income` then repeat; `GET /fundamentals/AAPL/ratings` then repeat | income cold `0.26s` → warm `0.001s`; ratings cold `0.41s` → warm `0.001s` — both now cache-hit on repeat. `routers/fundamentals.py` grep: income/balance/cashflow/ratings all call the shared `_cached()` helper into `data_cache` (7 call sites, was 3). `data_cache.py` `upsert()` still runs the `MAX_ROWS=20_000` DELETE-oldest eviction on every set | holds |
| R15-LEAD-024 | `GET /macro/WEO%2FUSA.NGDP_RPCH.A?provider=imf` (exact register/certification query) | 2023 `is_projection=false`, 2024 `false`, 2025..2031 `true` — byte-for-byte the same true/false split the batch-10 verifier recorded. `MacroChart.tsx` still reads `obs.is_projection`, splits points into `actual`/`projected` arrays, and renders the dashed-segment legend (`• dashed = projected (N)`) | holds |

COVERAGE: 4/4 ids raw; no raw: (none).
