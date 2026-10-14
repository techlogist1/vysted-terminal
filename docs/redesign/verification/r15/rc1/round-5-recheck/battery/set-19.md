# batch-5/W4-platform-workflow-boundary (set-19)

Candidate 949c3c9fd49d61ecadc9813a8321bcdfd81178bd, own sidecar :52355 (shard-15). In-process
probes against the candidate's sidecar venv unless noted (curl against the live route for
PLATFORM-020).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-PLATFORM-004 | in-process: `builtin.logic_branch` on "false"/"no"/"0"/"off"; engine run with notify_desktop wired to the false port, "yes" input | all four falsy strings route to `false_path` (`true_path: SKIP`); notify + its downstream log both `status: skipped`, node-skipped events emitted for both, taken branch `ok` | holds |
| R15-CODE-PLATFORM-019 | in-process: A(4s sleep)/B(fast)/C<-B via `run_workflow`; separately a `timeout_seconds:2` hung node | C started at t=0.00s while A still running (`run.done()=False`); hung node ends `status=error`, `error='node timed out after 2s'` at t=2.00s | holds |
| R15-CODE-PLATFORM-005 | in-process: 1500x concurrent `options.price(reqA)`/`options.price(reqB)` (different valuation dates) + 1500x `bonds.price_bond` vs `options.price` race | 0/1500 and 0/1500 mismatches vs single-threaded reference price (all engines/routes go through `@holds_ql_lock`) | holds |
| R15-CODE-AGENT-012 | in-process: inspect `invoke_agent` MCP tool's published JSON-schema via `FastMCP.list_tools()` | schema properties = `{agent_id, prompt}` only, no `api_key`; key is read from `x-vysted-api-key` header (`API_KEY_HEADER`) in `mcp_server.py:206` | holds |
| R15-AGENT-059 | in-process: `mcp_server._get_list()` against a stub HTTP 500 server (`VYSTED_SIDECAR_INTERNAL_BASE_URL` override) for `/agents`, `/workflow/saved`, `/runs` | all three return `{"ok": False, "error": "GET ... failed: Server error '500...'"}`, none degrades to an empty list | holds |
| R15-CODE-PLATFORM-020 | live HTTP on :52355: inserted a corrupt-JSON row + a `version:2` row directly into `workflows.db`, then `GET /workflow/saved` and `GET /workflow/saved/{v2-id}` | list route: both rows appear under `unreadable` with named reasons, `workflows: []` for those; individual GET on the v2 row returns `409` with `"saved with workflow schema version 2; this build reads version 1"` | holds |
| R15-LEAD-001 | pins check (`sidecar/openbb_mcp_subprocess/requirements.txt`, `sidecar/sec_edgar_mcp_subprocess/requirements.txt`) + standalone launch of the freshly-built `vysted-openbb-mcp-sidecar-aarch64-apple-darwin` binary on :52397 | `fastmcp==3.3.1`, `fastmcp-slim==3.3.1`, `mcp==1.27.1`, `httpx==0.28.1` pinned in both files; binary boots clean (FastMCP 3.3.1 banner, Uvicorn up), no `PackageNotFoundError` | holds (see raw file note: lighter check than a full clean-venv `ensure-all-sidecars.mjs --force` rebuild, which belongs to the chain/build lane) |
| R15-LEAD-003 | in-process: `data_cache.ensure_build()` across a simulated pre-fix(`0.7.9`)→post-fix(`0.8.0`) upgrade, plus a same-version reboot | pre-fix row present (size=1) before upgrade; `ensure_build('0.8.0')` clears the cache (size=0, meta.build restamped 0.8.0); a same-version reboot does NOT clear a freshly-written row (size stays 1) | holds |

COVERAGE: 8/8 ids raw; no raw: none.
