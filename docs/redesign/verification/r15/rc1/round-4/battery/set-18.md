# set-18 — batch-5/W4-platform-workflow-boundary (rc1-battery-18, round 4)

Candidate: `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Own sidecar on :52358 (own data dir
`rc1-round-4-data-battery-18`, copied from `rc1-round-4-seed-data`). Raw probe output under
`battery/raw/set-18/`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-PLATFORM-004 | in-process `logic_branch()` over all 8 truthy/falsy strings + engine run with `notify` wired to the un-taken port | `_FALSY_STRINGS` honored (false/no/0/off→false_path, SKIP on true_path); engine marks the un-taken-port node `status=skipped`, not `ok` | holds |
| R15-CODE-PLATFORM-019 | in-process A(2s sleep)/B(fast)/C←B workflow run | C completes before slow A finishes; each node wrapped in `asyncio.wait_for`; `asyncio.wait(FIRST_COMPLETED)` scheduler at workflow_engine.py:320 | holds |
| R15-CODE-PLATFORM-005 | in-process `run_quant` × 60 concurrent option pricings, two interleaved valuation dates | 0/30 zero-NPV corruptions in either date group (was 1413/3000 pre-fix); routes now `async def`; pricing runs in a `ProcessPoolExecutor` with a per-worker `RLock` guarding the QuantLib global | holds |
| R15-CODE-AGENT-012 | FastMCP `get_tool("invoke_agent")` schema introspection | input schema properties = `['agent_id','prompt']`, no `api_key`; key now read server-side from `get_http_headers()` | holds |
| R15-AGENT-059 | `_get_list()` called against a forced-unreachable backend (`VYSTED_SIDECAR_INTERNAL_BASE_URL=http://127.0.0.1:1`) for list_agents/list_workflows/list_runs | all three return `{"ok": false, "error": ...}`, never an empty list | holds |
| R15-CODE-PLATFORM-020 | `workflow_store.list_workflows()` with one good + one schema-invalid (extra field) row inserted directly into sqlite | good row still lists; bad row reported under `unreadable` with a logged reason; no 500 | holds |
| R15-LEAD-001 | read `openbb_mcp_subprocess/requirements.txt` + `sec_edgar_mcp_subprocess/requirements.txt` | `fastmcp==3.3.1`/`fastmcp-slim==3.3.1`/`mcp==1.27.1`/`httpx==0.28.1` pinned in both; matches known-good freeze | holds (pins only; full clean-venv PyInstaller build out of scope for this shard) |
| R15-LEAD-003 | in-process `data_cache.ensure_build()` across a simulated version bump with a pre-fix cache row present | pre-upgrade row readable; `ensure_build` on the new version clears the whole cache table (returns True); post-upgrade read of the same key is `None` | holds |

COVERAGE: 8/8 ids raw; no raw: none.
