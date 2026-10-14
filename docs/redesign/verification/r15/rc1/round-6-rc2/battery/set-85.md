# Set lows-P2/market-data-providers-2 (set-85)

Candidate ace7dd768c3b809b0e72b20b20cfc94eea2368bd, sidecar :52348 (own data dir, no VYSTED_RIG_HOOKS). Raw: battery/raw/set-85/<id>.txt

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-069 | latent-design repro executed: provider_registry.get_quote patched so one symbol's Quote raises AttributeError on `change_percent` (a renamed field), then real `_compare_symbols` and `_market_overview` | compare_symbols returns rows [GOODCO ok, BADCO error] with a clean "fewer than two resolved" message instead of raising out of gather; market_overview returns all 3 index rows, BADCO as an error row; pinned tests test_one_raising_symbol_yields_one_error_row / test_one_raising_quote_yields_one_error_row exist (not run) | holds |
| R15-LIFECYCLE-033 | POST /system/provider-health/trip {"weight":3.0} and /reset on a sidecar booted without VYSTED_RIG_HOOKS | both HTTP 404 {"detail":"Not Found"}; GET /system/provider-health still shows yahoo open:false; the with-flag path is pinned by test_provider_health_mutations_work_with_rig_hooks_flag (not run) | holds |

COVERAGE: 2/2 ids raw; no raw: none
