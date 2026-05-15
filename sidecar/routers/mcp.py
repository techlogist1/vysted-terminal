"""MCP layer router — status endpoints for the Vysted MCP server + openbb-mcp.

The FastMCP-managed Streamable-HTTP transport lives at ``/mcp`` (mounted
directly in :mod:`app`). This router exposes plain-JSON convenience
endpoints next to it:

- ``GET /mcp/status`` — Vysted MCP server readiness (plugin manager polls
  this to surface "MCP server: ready" without speaking JSON-RPC).
- ``GET /openbb-mcp/status`` — health of the Tauri-Rust-spawned
  openbb-mcp-server subprocess. Read by ``plugins/openbb-mcp``'s
  ``healthCheck()``.

Both endpoints are unauthenticated, mirroring the rest of the sidecar API
(the process binds to 127.0.0.1 only — no remote surface).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from services import mcp_server, openbb_mcp_provider

router = APIRouter(tags=["mcp"])


@router.get("/mcp/status")
async def get_mcp_status() -> dict[str, Any]:
    """Report readiness of the Vysted MCP server.

    Returns the same shape as ``types/mcp.ts:VystedMcpStatus`` so the
    frontend plugin-manager UI can typecheck against the response.
    """
    count = await mcp_server.tool_count()
    return {
        "ready": True,
        "toolCount": count,
        "endpoint": "/mcp",
        "protocolVersion": mcp_server.protocol_version(),
    }


@router.get("/openbb-mcp/status")
async def get_openbb_mcp_status() -> dict[str, Any]:
    """Report readiness of the Tauri-Rust-spawned openbb-mcp-server child.

    Surfaced by ``plugins/openbb-mcp``'s ``healthCheck()`` so the plugin
    manager UI can show whether OpenBB data is live (the child is healthy
    and the MCP handshake succeeded) or falling back to yfinance (the
    child failed to come up).
    """
    return await openbb_mcp_provider.status()
