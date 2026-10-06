# batch-25/W4-sonnet (rc1-battery-13, shard 13)

Candidate 949c3c9fd49d61ecadc9813a8321bcdfd81178bd, own sidecar :52353.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-116 | GET /disclosures/shareholding?symbol=AMAL, NAPEROL, ELCIDIN; grep sidecar log for "index HTTP 403" | AMAL: 200, count=104; NAPEROL: 200, count=104; ELCIDIN: 200, count=118 — all match cert's exact figures. 0 "index HTTP 403" lines in the sidecar log | holds |
| R15-CODE-AGENT-034 | live FastMCP `Client("http://127.0.0.1:52353/mcp")`, real `list_workspaces`/`get_workspace` calls (HTTP MCP transport, not just the in-process pinned test) | `list_workspaces` → `{'workspaces': ['__autosave__']}` (is_error False, real saved workspace, not a 404); `get_workspace('__autosave__')` → the full real workspace dict (layout/panels/watchlist/etc, not an error); `get_workspace('definitely-not-a-real-workspace-xyz')` → `{'ok': False, 'error': "...404 Not Found for url '.../workspace/definitely-not-a-real-workspace-xyz'..."}` — both tools reach the real `/workspace` router (not `/workspaces`), and the bare-list-to-dict wrap works | holds |

COVERAGE: 2/2 ids raw; no raw: none.
