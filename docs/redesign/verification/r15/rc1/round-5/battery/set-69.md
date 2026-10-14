# set-69 — batch-25/W4-sonnet (rc1-battery-16)

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-CODE-AGENT-034 | live GET /workspace vs /workspaces (route path); real FastMCP in-memory Client over `_build_server()` pointed at own :52356 calling `list_workspaces`/`get_workspace` | `/workspace` → 200; `/workspaces` → 404 (old path stays dead by design); real tool `list_workspaces` returns `{'workspaces': ['__autosave__']}`; `get_workspace('__autosave__')` returns the saved layout; `get_workspace(<missing>)` returns a typed `{ok:False, error:...}`, no crash | holds |
| R15-DATA-116 | live GET /disclosures/shareholding?symbol=<SYM> for AMAL, DAL, NAPEROL, JUMBO, ELCIDIN, TCS; grep own sidecar log for `index HTTP 403` | AMAL 104, NAPEROL 104, ELCIDIN 118 (exact match), DAL 43, JUMBO 110, all `source:BSE`; TCS (NSE) 20; 0 `index HTTP 403` lines | holds |

COVERAGE: 2/2 ids raw; no raw: none.
