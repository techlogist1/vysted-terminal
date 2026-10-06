# newhigh / rc1-verifier:2 — MCP list_workspaces / get_workspace call /workspaces, the router is /workspace

Auditor: refutation audit round 2, group newhigh. Written 18:20 IST. Candidate code tree 4c6dfe8c (confirmed at a3275f64). Own sidecar on :52365, scratch data dir.

**Verdict: new_defect_confirmed (high). The fix is wider than the verifier's framing: a prefix-only fix still leaves list_workspaces broken.**

## 1. Verifier's claim (read)
r15/rc1/verifier/g2/adj-mcp-workspaces.txt: `mcp_server.py:252-265` GETs `/workspaces` and `/workspaces/{id}`; `routers/workspace.py:21` is `APIRouter(prefix="/workspace")`; live GET /workspaces → 404 and /workspace → 200.

## 2. Code at the candidate
- `sidecar/services/mcp_server.py:255` `client.get("/workspaces")`; `:263` `client.get(f"/workspaces/{workspace_id}")`. Both are followed by a bare `raise_for_status()`.
- `sidecar/routers/workspace.py:21` `router = APIRouter(prefix="/workspace", ...)`. `GET ""` is typed `-> list[str]` (a bare list); `GET "/{name:path}"` returns a dict.
- The module already has the right helper, `_get_list(path, key)` at mcp_server.py:113. It wraps a bare list as `{key: [...]}` and turns an HTTP failure into `{"ok": False, "error": ...}`. `list_agents`, `list_runs` and `list_workflows` use it; the two workspace tools do not.

## 3. Live route probe (own :52365, a scratch workspace saved first)
```
POST /workspace {"name":"refaudit2-ws","workspace":{"version":1}} -> {"status":"saved","name":"refaudit2-ws"} HTTP 200
GET /workspaces -> 404
GET /workspaces/refaudit2-ws -> 404
GET /workspace -> 200
GET /workspace/refaudit2-ws -> 200
```

## 4. The real MCP tools, through a FastMCP in-memory Client (VYSTED_SIDECAR_INTERNAL_BASE_URL=http://127.0.0.1:52365)
```
list_workspaces is_error= True [TextContent(type='text', text="Error calling tool 'list_workspaces': Client error '404 Not Found' for url 'http://127.0.0.1:52365/workspaces'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/404", annotations=None, meta=None)]
get_workspace is_error= True [TextContent(type='text', text="Error calling tool 'get_workspace': Client error '404 Not Found' for url 'http://127.0.0.1:52365/workspaces/refaudit2-ws'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/404", annotations=None, meta=None)]
```

## 5. Prefix-only fix simulated (a transport rewrites /workspaces → /workspace; nothing else changed)
```
list_workspaces is_error= True [TextContent(type='text', text="Error calling tool 'list_workspaces': structured_content must be a dict or None. Got list: ['refaudit2-ws']. Tools should wrap non-dict values based on their output_schema.", annotations=None, meta=None)]
get_workspace is_error= False [TextContent(type='text', text='{"version":1}', annotations=None, meta=None)]
```
So correcting the path alone fixes get_workspace but not list_workspaces. GET /workspace returns a bare list, and FastMCP rejects that for a dict-annotated tool. This is the CLAUDE.md "FastMCP tools must return a dict … wrap any bare-list REST response at the MCP boundary" gotcha.

## 6. Why tests are green
`test_mcp_server.py` and `test_mcp_catalog_parity.py` only assert that the tool NAMES are registered (lines 59-60 and 29-30). Neither tool is ever called in a test.

## 7. Root cause
`sidecar/services/mcp_server.py:252-265`. Both tools use a route spelling (`/workspaces`) that has never matched `routers/workspace.py:21` (`/workspace`), and list_workspaces skips the module's bare-list wrap.

## 8. Fix shape
In `mcp_server.py`, `list_workspaces` becomes `return await _get_list("/workspace", "workspaces")`. `get_workspace` GETs `f"/workspace/{quote(workspace_id, safe='')}"` (the route is `{name:path}`) and maps an HTTP error to `{"ok": False, "error": ...}` the same way `_get_list` does, instead of a bare `raise_for_status`. Fix both docstrings ("Maps to GET /workspace"). No REST contract change.

## 9. Acceptance test
- `sidecar/tests/test_mcp_server.py`: new `test_workspace_tools_reach_the_workspace_router`. With the `client` fixture (app bound) and a scratch VYSTED_DATA_DIR, POST /workspace {"name":"t-ws","workspace":{"version":1}}, then `asyncio.run(mcp_server.get_mcp_server().call_tool("list_workspaces", {}))`. Assert structured_content is a dict and `"t-ws" in structured["workspaces"]`. Then `call_tool("get_workspace", {"workspace_id": "t-ws"})` → structured == {"version": 1}. Also `get_workspace("missing")` → `ok is False` and "404" in error. Extend the existing `test_list_tool_reports_a_failing_route_as_not_ok` parametrize with `("list_workspaces", "/workspace")`.
- Live re-proof: own sidecar, save a workspace via POST /workspace, then run the FastMCP in-memory Client script from §4 (VYSTED_SIDECAR_INTERNAL_BASE_URL=http://127.0.0.1:<port>). Both tools must return is_error=False, with list_workspaces → {"workspaces":[...]} containing the saved name.

## 10. Severity note
Kept high, as the verifier rated it. Two advertised tools on the v1.0 external MCP surface (a Locked BLUEPRINT §2 decision) fail on every call for every client. The failure is loud (a tool error, not wrong data) and no other surface is affected. If the collator grades loud, narrow MCP failures as medium, this is the one to downgrade.

## 11. Certification-failure count
id null (new) → 0, 'new'.
