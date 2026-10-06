# lows-P1/agent-tools-catalog-ledger (set-58), shard rc1-battery-9, candidate ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-070 | in-process: replace(research, timeout_seconds=60); _tool_timeout_seconds | ValueError 'timeout_from_args derives the budget...'; research guard 390 s from args; a non-research cap flagged timeout_from_args gets the guard (210 s), so selection is by flag not name | holds |
| R15-AGENT-066 | in-process + LIVE MCP list_tools on :52349/mcp/ | run_custom_backtest not listed (39 tools live); every projected tool read_only; pinned test exists | holds |
| R15-AGENT-067 | in-process projection rule + live list_tools | exclusion set explicit in catalog.py comment; backtest_summary, run_custom_backtest, broker_portfolio absent; pinned test_mcp_projection_is_explicit_per_entry exists | holds |
| R15-CODE-AGENT-026 | in-process ToolKind members; grep mcp_endpoint | ToolKind = (read_handler, per_invocation, host_action), no mcp_endpoint anywhere in sidecar code; pinned test exists | holds |
| R15-DOCS-019 | grep CURRENT_STATE.md stale claims + code facts | stale 'unfixed inconsistency/Likely broken' phrases gone from body; TOOL_SCHEMAS 56, read_handlers minus schemas = empty, KNOWN_TOOL_IDS == agent_selectable_tool_ids | holds |

COVERAGE: 5/5 ids raw; no raw: none
