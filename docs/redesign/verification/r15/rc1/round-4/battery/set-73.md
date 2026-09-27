# set-73 — batch-25/W4-data-116-code-agent-034-data-113

Candidate: 1006c6da694ede5776c3dabbd27b305aeb56b5ad. Sidecar :52341, own data dir
`rc1-round-4-data-rc1-battery-1` (copy of the keyless ISO seed).

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DATA-113 | `GET /earnings/WIT/estimates` | `eps_estimate_mean:0.035, currency:"USD", revenue_estimate_mean:244747656810.0, revenue_currency:"INR"` — EPS and revenue now carry independently-labelled currencies; `EpsEstimateGrid.tsx:71` formats revenue with `revenue_currency` (falls back to `currency` only when undefined). | holds |
| R15-DATA-116 | `GET /disclosures/shareholding?symbol=<SYM>` for AMAL, DAL, NAPEROL, JUMBO, ELCIDIN (register repro set) + TCS | all 6 return HTTP 200 with populated `patterns` (AMAL: 104 quarters, source `BSE`, `xbrl_url` present) | holds |
| R15-CODE-AGENT-034 | In-process FastMCP `Client(mcp_server.get_mcp_server())` (candidate's own `sidecar/.venv`), `list_workspaces` and `get_workspace("__autosave__")`; also plain REST `GET /workspace` (200) vs `GET /workspaces` (404, confirms old-path 404 still correctly 404 — router prefix stayed `/workspace`) | `list_workspaces` → `{'workspaces': ['__autosave__']}` (no error, bare-list wrap present); `get_workspace` → full workspace dict, no `is_error` | holds |

COVERAGE: 3/3 ids raw; no raw: none.
