# Set — batch-10/W3-fundamentals-bse-cache (rc1-battery-6)

Candidate: `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Own sidecar `:52346` (seed-data copy
`rc1-round-4-data-rc1-battery-6`), reused for the whole shard.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-048 | Live: `GET /fundamentals/ICON` (same symbol as register repro DAT-P6-5) with `X-Vysted-Region: IN`. | `roce: 0.1673...` present with a `field_meta.roce` entry naming its derivation ("annual EBIT / (total assets - current liabilities)"). | holds |
| R15-DATA-054 | Live: `GET /fundamentals/CREST` (same symbol as register repro). | `pe_ratio: 31.28...` (matches register's stated ~31x consolidated figure), top-level `basis: "consolidated"` field plus per-field labels ("consolidated, sum of 4 filed quarters to 2026-06-30"). | holds |
| R15-DATA-055 | Live: `GET /fundamentals/DHOOTTRANS` + `/resolve?q=DHOOTTRANS` (same symbol as register repro). | `listing_date: "2026-08-17"` now populated; `fifty_two_week_high_date`/`fifty_two_week_low_date` now carry distinct per-leg dates (was: absent entirely). | holds |
| R15-DATA-053 | Live: `GET /quotes/ICON?asset_class=equity` and `/quotes/AMAL?asset_class=equity` (same symbols as register repro), `X-Vysted-Region: IN`. | ICON: `volume: 1200.0`, `open/high/low/prev_close` all populated, provider `bse` (was: volume null, no OHLC fields at all). AMAL: volume populated (routed to `nse_direct` this run, not the BSE path the register named — a provider-selection detail outside this entry's scope). | holds |
| R15-DATA-096 | Code trace: `routers/fundamentals.py` `/income` `/balance` `/cashflow` `/ratings` now all call `_cached(...)`; `services/data_cache.py` has an LRU eviction ceiling (`ORDER BY updated_at ... LIMIT`) and confirms SQLite work runs via `asyncio.to_thread`. | Both halves of the register's complaint (uncached routes; a cache that never evicts and runs on-loop) are addressed. | holds |
| R15-LEAD-024 | Live: `GET /macro/WEO/IND.NGDP_RPCH.A?provider=imf` (same series as batch-9 verifier's live check), `X-Vysted-Region: IN`. | Every observation at/after the IMF's projection cutoff (2026–2031 in this run) carries `is_projection: true`; code trace confirms the flag threads provider → model (`models/market.py`) → chart (`MacroChart.tsx` renders it on a distinct series). | holds |

Raw files: `battery/raw/set-42/R15-*.txt` (6 files, one per id).

COVERAGE: 6/6 ids raw; no raw: none.
