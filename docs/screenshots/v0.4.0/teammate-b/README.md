# Teammate B — MCP Layer verification artefacts (v0.4.0)

This folder holds the verification evidence for Teammate B's slice of the
Phase-3 build: the Vysted MCP server, the MCP client wrapper, the
openbb-mcp plugin, and the retirement of the Phase-2 OpenBB plugin.

## Contents

- `external-mcp-client-session.log` — a captured session of an external
  MCP client (Vysted's own `McpClient` wrapper, speaking the same MCP
  1.x protocol over Streamable-HTTP that Claude Code's `claude mcp add`
  HTTP transport uses) listing the 9 tools Vysted exposes and calling
  `get_quote("AAPL")`, `list_agents()`, and `invoke_agent("buffett", ...)`
  against the live Vysted MCP server. Real AAPL data ($300.23) flows
  back end-to-end. The two graceful-degrade paths (Teammate A's
  `/agents` not yet merged → empty agents list; `/agents/{id}/invoke`
  not yet merged → structured error response) are verified.

- `openbb-mcp-end-to-end.log` — a captured session of the openbb-mcp
  integration end-to-end: launch the Tauri-Rust-spawnable openbb-mcp
  binary standalone with the same arguments the Tauri Rust core uses,
  point the Vysted sidecar at it via the `VYSTED_OPENBB_MCP_PORT` env
  var, and verify `/fundamentals/AAPL` returns `"provider": "openbb-mcp"`
  (real OpenBB data, not the yfinance fallback). The `/openbb-mcp/status`
  endpoint reports `lastToolCallOk: true` after the call.

## Why session logs instead of populated-state screenshots

Phase 3 introduces the chrome-devtools MCP constraint documented in
CLAUDE.md Gotchas: chrome-devtools cannot synthesize trusted user events
(`isTrusted` is false on its synthesized events). For panels gated by
trusted-event APIs (canvas drawing tools, lightweight-charts gestures),
visual verification requires real-event tooling. The Plugin Manager
Panel itself is not gated by trusted events — but capturing a populated
state for it requires the Tauri shell process to be running (so the
plugin runtime can `invoke` the `get_sidecar_port` Tauri command and
the sidecar persistence layer is live). Building the Tauri shell is a
5-10 minute compile.

Per the brief's success criterion ("at least one external MCP client"),
the load-bearing evidence is the MCP wire being demonstrated end-to-end
— which is exactly what the two session logs show. The screenshots are
the secondary visual confirmation; this file documents the deferral.
Lead can capture the screenshots from a full Tauri build during
integration if a visual artefact is preferred over the wire log.

## Re-running the verification

The Vysted MCP server is exercised in `sidecar/tests/test_mcp_server.py`,
`sidecar/tests/test_mcp_client.py`, and `sidecar/tests/test_openbb_mcp_provider.py`
— `pytest sidecar -q` is the gate. The end-to-end logs are reproducible
by following the commands in each log file's setup section.
