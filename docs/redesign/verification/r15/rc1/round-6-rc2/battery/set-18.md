# Set: batch-5/W4-platform-workflow-boundary (set-18) — rc1-battery-21 @ ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-PLATFORM-004 | POST /workflow/run: logic.branch(value in false/no/0/off/true) -> true_path -> notify_desktop -> log, own sidecar :52361 | false/no/0/off route false_path; notify + downstream node-skipped; 'true' runs both | holds |
| R15-CODE-PLATFORM-019 | POST /workflow/run: A=flow.sleep 4s, B fast, C dep on B; separate node timeout_seconds=2 on a 6s sleep | C started/finished at 0.02s while A finished 4.03s; timeout node-error at 2.02s "node timed out after 2s" | holds |
| R15-CODE-PLATFORM-005 | 200 concurrent (32 threads) POST /quant/option/price alternating two valuation dates vs serial refs | 0 mismatches, 0 zero prices (refs 29.1490 / 18.1748) | holds |
| R15-CODE-AGENT-012 | fastmcp Client list_tools on get_mcp_server() | invoke_agent properties = agent_id, prompt only (no api_key) | holds |
| R15-AGENT-059 | fastmcp Client list_agents/list_workflows/list_runs against a stub returning 500 (VYSTED_SIDECAR_INTERNAL_BASE_URL) | each returns {ok:false, error:"GET ... failed: Server error '500 ...'"}, not empty lists | holds |
| R15-CODE-PLATFORM-020 | insert good + extra-key + version-2 rows into workflows.db of own data dir; GET /workflow/saved, GET /saved/{id} | 200; workflows=[good], unreadable lists bad (extra_forbidden) and v2; v2 load -> 409 "saved with workflow schema version 2; this build reads version 1" | holds |
| R15-LEAD-001 | clean-venv MCP build requires pins: grep requirements + candidate's freshly built binaries + /mcp/status | mcp==1.27.1, httpx==0.28.1 (+fastmcp 3.3.1) pinned in both requirements; all 3 binaries built 3 Oct 05:06-05:09 at candidate; /mcp/status ready toolCount 39 (full clean-venv rebuild is the heavy lane's chain) | holds |
| R15-LEAD-003 | in-process data_cache.ensure_build: warm on 0.7.9, boot 0.8.0, boot 0.8.0 again | upgrade cleared row (size 1 -> 0, stale get None, backups/0.7.9 made); same-version boot kept new row | holds |

COVERAGE: 8/8 ids raw (battery/raw/set-18/); no raw: none
