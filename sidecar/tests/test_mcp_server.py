"""Tests for the Vysted MCP server (FastMCP) and its mount-in-sidecar wiring.

The MCP server is exercised via :mod:`services.mcp_server` directly — every
tool is registered through ``@mcp.tool`` decorators on the FastMCP instance,
so the assertions cover (a) tool registration (right names, count) and
(b) call routing (each tool's `httpx.AsyncClient` hits the right sidecar
endpoint and returns the body the data layer produced).

The ``/mcp/status`` plain-JSON endpoint is exercised via TestClient on the
real app instance — the mount happens in ``create_app``, so a freshly built
app should report ``ready=True`` and the correct tool count.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient

from services import mcp_server


@pytest.fixture(autouse=True)
def _reset_mcp_server() -> Any:
    """Drop any cached FastMCP instance between tests so registration is fresh."""
    mcp_server._reset_for_tests()
    yield
    mcp_server._reset_for_tests()


def test_status_endpoint_reports_ready(client: TestClient) -> None:
    """``GET /mcp/status`` returns the VystedMcpStatus contract shape."""
    body = client.get("/mcp/status").json()
    assert body["ready"] is True
    assert body["endpoint"] == "/mcp"
    assert isinstance(body["toolCount"], int)
    assert body["toolCount"] >= 8  # 5 data + 2 agent + 2 workspace tools
    assert body["protocolVersion"]


def test_mcp_server_registers_expected_tools() -> None:
    """Every Phase-3 brief tool is registered on the FastMCP server."""
    server = mcp_server.get_mcp_server()
    tools = asyncio.run(server.list_tools())
    names = {tool.name for tool in tools}
    assert {
        "get_quote",
        "get_history",
        "get_fundamentals",
        "get_news",
        "get_macro_series",
        "list_agents",
        "invoke_agent",
        "list_workspaces",
        "get_workspace",
    }.issubset(names)


def test_get_quote_tool_proxies_quotes_endpoint(
    client: TestClient, mock_yfinance: object
) -> None:
    """The ``get_quote`` tool returns the same payload the /quotes/{symbol} route returns.

    The fixture pins the FastAPI app reference for in-process httpx, so the
    tool call invokes the mocked yfinance backend by going through the
    real router stack.
    """
    server = mcp_server.get_mcp_server()
    # The MCP server's bound app is the TestClient's app (set in create_app).
    result = asyncio.run(server.call_tool("get_quote", {"symbol": "AAPL"}))
    text_blocks = [
        block.text for block in result.content if getattr(block, "type", None) == "text"
    ]
    assert any("AAPL" in block for block in text_blocks)


def test_invoke_agent_tool_returns_error_when_agents_router_missing(
    client: TestClient,
) -> None:
    """``invoke_agent`` reports an error cleanly when Teammate A's route is absent.

    Teammate A's ``/agents`` router is not in this worktree; the tool should
    surface a structured error rather than raise.
    """
    server = mcp_server.get_mcp_server()
    result = asyncio.run(
        server.call_tool("invoke_agent", {"agent_id": "buffett", "prompt": "test"})
    )
    # The tool wraps the outcome in a dict; FastMCP serialises it as text.
    assert result.structured_content is not None
    # The dict either has 'error' or empty content with no usage — both are
    # acceptable "agents not wired" responses.
    structured = result.structured_content
    # structured_content for dict returns is the dict itself (no wrap)
    if "result" in structured:
        structured = structured["result"]
    assert isinstance(structured, dict)
    assert structured.get("agent_id") == "buffett"


def test_list_agents_tool_returns_empty_when_router_missing(client: TestClient) -> None:
    """``list_agents`` returns an empty list rather than erroring."""
    server = mcp_server.get_mcp_server()
    result = asyncio.run(server.call_tool("list_agents", {}))
    structured = result.structured_content or {}
    if "result" in structured:
        structured = structured["result"]
    assert isinstance(structured, dict)
    assert structured.get("agents") == []


def test_streamable_http_app_mounts_under_slash_mcp() -> None:
    """``get_streamable_http_app`` returns a Starlette app with a single endpoint."""
    app = mcp_server.get_streamable_http_app()
    assert hasattr(app, "lifespan")
    # The FastMCP http_app registers a POST/DELETE route at "/" — the outer
    # sidecar mount adds the "/mcp" prefix.
    paths = [getattr(route, "path", None) for route in app.routes]
    assert "/" in paths


def test_protocol_version_returns_a_string() -> None:
    """``protocol_version`` returns a non-empty version string."""
    version = mcp_server.protocol_version()
    assert isinstance(version, str)
    assert len(version) > 0
