# Set: lows-P2/mcp-servers (set-86) — candidate ace7dd76, sidecar :52344

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-AGENT-022 | GET /mcp/status; POST /mcp/ initialize 2025-11-25; mcp.types.LATEST_PROTOCOL_VERSION | status protocolVersion 2025-11-25 = handshake 2025-11-25 = LATEST (was 2025-06-18) | holds |
| R15-CODE-AGENT-023 | live MCP tools/call on a raising handler (price_data ZZZNOTASYMBOL999) and unknown tool | isError:true with 'tool price_data raised: correctness gate...' (was a successful {ok:false} body). Adjacent: a handler that RETURNS its own {ok:false} envelope (resolve_symbol with no query) is still isError:false; that is not the raising path the entry described | holds |
| R15-CODE-AGENT-025 | in-process: stub session whose call_tool returns isError False, content [], structuredContent {x:1} through McpClient.call_tool; then sec decode | result keeps structuredContent {x:1}; sec_filings_provider._decode_tool_result returns {'x': 1} (was 'returned no content') | holds |
| R15-CODE-AGENT-024 | design: the seven duplicated members across openbb_mcp_provider / sec_filings_provider | _resolve_endpoint/_get_client/_last_* gone from both; both build mcp_client.LocalMcpSubprocess (same class); pinned test test_local_mcp_subprocess_resolves_and_decodes_once exists in tests/test_mcp_client.py (not executed here, heavy lane) | holds |

COVERAGE: 4/4 ids raw; no raw: none
