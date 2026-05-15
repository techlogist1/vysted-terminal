# MCP Integration

Vysted Terminal speaks the Model Context Protocol on both sides:

- **Vysted-as-server** — the sidecar mounts a FastMCP application at
  `/mcp` over the Streamable-HTTP transport. External MCP clients (Claude
  Desktop, Claude Code) consume Vysted's data + agent surface as MCP tools.
- **Vysted-as-client** — the sidecar's `mcp_client.py` connects to
  external MCP servers. The first real consumer is `openbb-mcp-server`
  (the `plugins/openbb-mcp/` plugin).

This document covers the **server** side — how an external MCP client
talks to Vysted.

## Endpoint discovery

Vysted's sidecar binds to a Tauri-picked free port at app launch. The
port is printed to the dev console:

```
[vysted] Python sidecar healthy on 127.0.0.1:54321
```

From inside the running app the frontend resolves the port via the
`get_sidecar_port` Tauri command. For an external MCP client, read the
port from that dev-console line or run:

```powershell
# Windows — find the sidecar port the running app picked
Get-Process vysted-sidecar* | Select-Object Id
netstat -ano | Select-String "LISTENING.*<pid>"
```

```bash
# macOS / Linux
lsof -nP -p $(pgrep vysted-sidecar) -iTCP -sTCP:LISTEN
```

Once you have the port, the MCP endpoint is:

```
http://127.0.0.1:<sidecar-port>/mcp/
```

Vysted's MCP server is **localhost-only** — it binds to 127.0.0.1 and
inherits the rest of the sidecar's "no remote surface" posture.

## Tools exposed

Phase 3 exposes the following tools (see `sidecar/services/mcp_server.py`
for the source of truth):

| Tool               | Args                         | Returns                                                  |
| ------------------ | ---------------------------- | -------------------------------------------------------- |
| `get_quote`        | `symbol`                     | latest quote (price, change, %change, volume, timestamp) |
| `get_history`      | `symbol, timeframe, range_?` | OHLCV bars                                               |
| `get_fundamentals` | `symbol`                     | valuation ratios + company profile                       |
| `get_news`         | `symbols?, limit?`           | recent headlines                                         |
| `get_macro_series` | `series_id, provider?`       | FRED-style observations                                  |
| `list_agents`      | —                            | available first-party + custom agents                    |
| `invoke_agent`     | `agent_id, prompt, api_key?` | aggregated agent reply (SSE stream collapsed into one)   |
| `list_workspaces`  | —                            | saved workspaces                                         |
| `get_workspace`    | `workspace_id`               | one saved workspace                                      |

## Claude Desktop

Claude Desktop's `claude_desktop_config.json` does **not** accept HTTP
servers directly. Use the `mcp-remote` bridge (npm package) to translate
between Claude Desktop's stdio expectation and Vysted's HTTP transport.

Locate the config file:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Add the Vysted server:

```json
{
  "mcpServers": {
    "vysted": {
      "command": "npx",
      "args": ["mcp-remote", "http://127.0.0.1:<sidecar-port>/mcp/"]
    }
  }
}
```

Restart Claude Desktop. The Vysted tools appear in the slash-command
picker (`/vysted__get_quote`, etc.).

## Claude Code

Claude Code supports HTTP MCP servers natively. From your shell:

```bash
claude mcp add vysted http://127.0.0.1:<sidecar-port>/mcp/ --transport http
```

Verify the connection:

```bash
claude mcp list
```

Inside a Claude Code session, the tools are addressable as
`mcp__vysted__get_quote` and friends.

## Testing the connection

The simplest end-to-end probe (no MCP client needed):

```bash
curl -X POST http://127.0.0.1:<sidecar-port>/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl","version":"0.0.0"}}}'
```

A `200 OK` JSON-RPC response confirms the FastMCP transport is live.

For a richer readiness check (no JSON-RPC), GET `/mcp/status`:

```bash
curl http://127.0.0.1:<sidecar-port>/mcp/status
# {"ready":true,"toolCount":9,"endpoint":"/mcp","protocolVersion":"2025-06-18"}
```

## Authentication

There is no authentication today — Vysted's sidecar binds to 127.0.0.1
only, so any process on the same host can reach it. The "BYOK" model
applies to **outbound** calls Vysted makes (LLM provider keys live in
the OS keychain via `src/lib/keychain.ts`); the MCP server's inbound
surface is open within localhost by design.

If you want to expose Vysted's MCP server beyond localhost, terminate a
reverse proxy in front and add auth there — the sidecar itself stays
localhost-only.

## See also

- `sidecar/services/mcp_server.py` — tool registrations.
- `sidecar/services/mcp_client.py` — the Vysted-as-client wrapper.
- `plugins/openbb-mcp/` — the reference MCP-client plugin.
- `types/mcp.ts` — TypeScript types for MCP server config + status.
