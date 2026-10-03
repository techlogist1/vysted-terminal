# set-43 — batch-10/W4-screener-routes-statedocs (battery shard 24, candidate ace7dd76)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-087 | GET /macro/DGS10 with US and IN region, no provider param; GET /macro/CPIAUCSL?provider=fred | 422 "provider is required for a series id" in both regions (no more cross-namespace 502); explicit provider=fred dispatches (502 only for missing FRED key, keyless profile) | holds |
| R15-CROSS-PLATFORM-003 | venv python: platform.system=Windows; detect_device(force=True) | _detect_windows branch exists (GlobalMemoryStatusEx via ctypes, unreachable on macOS); fallback now reports estimated: True instead of presenting 8 GiB as measured; real-RAM path pinned by test_detect_windows_uses_real_ram_via_ctypes | holds (real Windows API path not runnable on macOS; ci_pinned) |
| R15-RESEARCH-025 | POST /screener/formula/validate x3 repro formulas + '(pe > 10) + 1' + 'pe < 5 and roe > 0.1' | all boolean-in-arithmetic/min/abs rejected ok:false with explicit message; valid and/or formula ok:true | holds |
| R15-DATA-095 | existing DB + simulate next numeric field (ebitda_margin) from candidate source; _connect() | column ALTERed in on the existing DB (present after _connect, was absent in the old DB) | holds |
| R15-DOCS-016 | read docs/CURRENT_STATE.md write-surface lines vs catalog | doc states "19 host actions", catalog has exactly 19 non-read-only (all host_action); doc says none auto-apply under ASK / AUTO_APPLIED_KINDS = panel,chart,watchlist matches types/proposed-change.ts | holds |

COVERAGE: 5/5 ids raw; no raw: none
