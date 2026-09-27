# batch-10/W4-screener-routes-statedocs (set-43)

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Own sidecar `127.0.0.1:52347`, data dir
`rc1-round-4-data-battery-7`. Raw output: `raw/set-43/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DATA-061 | Live: `GET /macro/NOT.A.REAL.WB.ID?provider=world-bank`, `GET /macro/NOT.A.REAL?provider=ecb`, `GET /quotes/ZZQXNOTASYM`, `GET /macro/CPIAUCSL?provider=fred` (keyless) | World Bank/ECB both `502 provider_error` ("The data provider returned an unexpected response."); quotes `404 not_found` ("check the symbol"); keyless FRED `502` with the authored copy naming fred.stlouisfed.org and the no-key-needed alternatives (ECB/IMF/World Bank). All four match the certified shape. | holds |
| R15-DATA-087 | Live: `GET /macro/CPIAUCSL` (no `provider` param) | `422 {"detail":"provider is required for a series id"}` | holds |
| R15-RESEARCH-025 | Live: `POST /screener/formula/validate` for `'(pe > 10) + 1'`, `'abs(pe > 10)'`, `'max(pe > 10, 1)'`, `'(pe > 10) * 2 + 1'`, `'pe > 10 and pb < 3'`, `'min(pe < 5, roe) > 0.5'` | All four boolean-in-arithmetic forms rejected with the "wrap the comparison on its own, or combine with 'and'/'or'" copy (abs/max/min all reject uniformly, the same class-fix as `+`/`*`); `'pe > 10 and pb < 3'` -> `ok:true` with `fields:["pe_ratio","price_to_book"]`. | holds |
| R15-CROSS-PLATFORM-003 | In-process (candidate venv): `platform.system=lambda:'Windows'` then `hardware_fit.detect_device(force=True)`; live `GET /system/hardware` on this M1 Pro | Faked Windows -> `ramGib:8.0, gpuBudgetGib:4.4, estimated:true` (constant fallback, not a real read); live real M1 -> `ramGib:16.0, estimated:false` (real `GlobalMemoryStatusEx`-style path not taken on macOS, real sysctl read instead) — matches the certified "ctypes on Windows, honest fallback on the fake, honest real read on the real machine" shape. | holds |
| R15-DATA-095 | In-process: built a `fundamentals` table via `fundamentals_store._ALL_COLUMNS` minus `seed_updated_at`/`eod_updated_at`/`provider` (confirmed absent via `PRAGMA table_info`), pointed the store at it with `reset_for_tests(path)`, called real `_connect()` | All 3 columns present after `_connect()` — the general `_migrate` ALTERs every column in `_ALL_COLUMNS`, not a hand-picked subset. | holds |
| R15-DOCS-016 | grep `docs/CURRENT_STATE.md:78-80`; in-process `catalog.CAPABILITY_CATALOG` filtered to `kind=="host_action"` | Doc: "the catalog's 19 host actions ... no order action exists, D81 — none auto-apply". Live catalog: exactly 19 host_action ids, none order-shaped (`add_chart_drawing`...`write_screener_filters` listed, no `place_order`/`submit_order`/etc). | holds |

**Set result: 6/6 holds.**
