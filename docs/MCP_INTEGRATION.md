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

## Connecting an external MCP client

There are two ways to reach Vysted's MCP surface: the **loopback HTTP
endpoint** (the running app's mounted transport) and a **stdio
entrypoint** (spawn the sidecar binary directly). Both expose the same
tool set.

### 1. Loopback HTTP endpoint + the discovery file

Vysted's sidecar binds to a Tauri-picked free port at app launch. Once
the sidecar is confirmed healthy, the Tauri core writes a small
discovery file so an external MCP client does not have to scrape the
dev-console line:

```
[vysted] Python sidecar healthy on 127.0.0.1:54321
[vysted] wrote MCP endpoint discovery file ".../mcp-endpoint.json"
```

The discovery file is `mcp-endpoint.json` under Vysted's per-OS app data
directory:

- macOS: `~/Library/Application Support/com.vysted.terminal/mcp-endpoint.json`
- Windows: `%APPDATA%\com.vysted.terminal\mcp-endpoint.json`
- Linux: `~/.local/share/com.vysted.terminal/mcp-endpoint.json`

(The exact directory is whatever Tauri's `app_data_dir()` resolves for
the bundle identifier; the three paths above are the platform defaults.)
Its contents:

```json
{
  "sidecarPort": 54321,
  "mcpEndpoint": "http://127.0.0.1:54321/mcp",
  "protocolVersion": "2025-06-18"
}
```

A failed/disconnected boot (no free port) writes **no** file, so a stale
file never points at a dead port. From inside the running app the
frontend instead resolves the port via the `get_sidecar_port` Tauri
command. Falling back to OS tooling if needed:

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

### 2. stdio entrypoint (`--mcp-stdio`)

The same sidecar binary doubles as a stdio MCP server (no second
`externalBin`). An MCP client that prefers stdio spawns the binary with
`--mcp-stdio`; the FastMCP server then speaks JSON-RPC over stdin/stdout
instead of binding a port. `--port` is ignored in this mode.

```jsonc
{
  "mcpServers": {
    "vysted": {
      "command": "/path/to/vysted-sidecar",
      "args": ["--mcp-stdio", "--data-dir", "<vysted-app-data-dir>"],
    },
  },
}
```

Pass `--data-dir` so the stdio process resolves the same SQLite stores
and saved workspaces the running app uses. The stdio transport owns
stdin, so the sidecar's stdin-EOF shutdown watchdog is disabled in this
mode and the FastMCP startup banner is suppressed (stdout is the
JSON-RPC channel).

## Tools exposed

The data + analysis tools are **projected from the single capability
catalog** (`sidecar/services/agent_tools/catalog.py`) — the external MCP
surface is not a hand-maintained duplicate. The agent / workspace /
workflow tools below are hand-written and MCP-only. The source of truth
is `sidecar/services/mcp_server.py` plus the catalog; the exact count
grows as catalog capabilities land, so probe `/mcp/status` (below) for
the live `toolCount` rather than relying on a number here.

Catalog-projected data + analysis tools (each under its catalog id):
`price_data`, `fundamentals`, `news`, `screener_run`, `macro_series`,
`macro_search`, `earnings_upcoming`, `earnings_history`,
`earnings_estimates`, `analyst_history`, `analyst_individual`,
`price_target_history`, `sec_filings_list`, `sec_filing_content`,
`sec_insider_transactions`, `price_option`, `compute_greeks`,
`price_bond`, `yield_curve_value`, `broker_portfolio`.

Hand-written agent / workspace / workflow tools:

| Tool              | Args                         | Returns                                                |
| ----------------- | ---------------------------- | ------------------------------------------------------ |
| `list_agents`     | —                            | available first-party + custom agents                  |
| `invoke_agent`    | `agent_id, prompt, api_key?` | aggregated agent reply (SSE stream collapsed into one) |
| `list_workspaces` | —                            | saved workspaces                                       |
| `get_workspace`   | `workspace_id`               | one saved workspace                                    |
| `run_workflow`    | `spec_json`                  | unary workflow run result                              |
| `list_workflows`  | —                            | saved workflows                                        |

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
picker (`/vysted__price_data`, etc.).

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
`mcp__vysted__price_data` and friends.

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
# {"ready":true,"toolCount":26,"endpoint":"/mcp","protocolVersion":"2025-06-18"}
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
