# set-42 — batch-10/W4-screener-routes-statedocs (rc1-battery-16)

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-CROSS-PLATFORM-003 | in-process, faked `platform.system()='Windows'` on this Mac: `h.detect_device(force=True).to_dict()`; live GET /system/hardware on the M1 Pro host | faked-Windows falls back to `{ramGib:8.0, gpuBudgetGib:4.4, estimated:true}`; source has a real `_detect_windows` ctypes `GlobalMemoryStatusEx` path (hardware_fit.py:223); live host reports 16 GiB, `estimated:false` | holds |
| R15-DATA-087 | live GET /macro/CPIAUCSL (no provider) and `?provider=fred` on :52356 | no-provider → 422 "provider is required for a series id"; `provider=fred` dispatches to FRED (502 only for a missing key in this keyless profile) | holds |
| R15-DATA-095 | in-process probe4: table missing the last 3 `_ALL_COLUMNS` entries, then `fs._connect()` | `missing after migrate: []` — all 3 columns backfilled via the single `_ALL_COLUMNS` vocabulary | holds |
| R15-DOCS-016 | in-process `CAPABILITY_CATALOG` count of `kind=='host_action'`; read docs/CURRENT_STATE.md:75-82 | 19 host_action capabilities incl. `add_chart_drawing`; doc text matches ("the catalog's 19 host actions ... no order action exists, D81") | holds |
| R15-RESEARCH-025 | live POST /screener/formula/validate for 8 formulas (register's own repro + batch-10's fresh cases) | every boolean-into-arithmetic formula rejected with a positioned error; `pe > 10 and pb < 3` still validates ok | holds |

COVERAGE: 5/5 ids raw; no raw: none.
