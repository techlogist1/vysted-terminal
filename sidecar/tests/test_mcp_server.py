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
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
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
    # catalog-projected data/analysis tools + 6 runtime (agents/workspaces/workflows)
    assert body["toolCount"] >= 8
    assert body["protocolVersion"]


def test_mcp_server_registers_catalog_and_runtime_tools() -> None:
    """The MCP surface = the catalog's projected capabilities + the runtime tools."""
    from services.agent_tools.catalog import mcp_tool_ids

    server = mcp_server.get_mcp_server()
    tools = asyncio.run(server.list_tools())
    names = {tool.name for tool in tools}
    # Every catalog-projected capability appears by its canonical (internal) name.
    assert set(mcp_tool_ids()).issubset(names)
    # The runtime tools (agents/workspaces/workflows/runs) are MCP-only and stay.
    assert {
        "list_agents",
        "invoke_agent",
        "list_workspaces",
        "get_workspace",
        "run_workflow",
        "list_workflows",
        "list_runs",
    }.issubset(names)
    # Representative catalog names the internal copilot also uses (same names).
    assert {"price_data", "fundamentals", "macro_series", "news"}.issubset(names)


def test_projected_tool_dispatches_to_the_registered_handler() -> None:
    """A projected data tool runs the SAME registered handler the copilot calls.

    Register a stub handler and verify the MCP tool dispatches through
    ``agent_tools.invoke_tool`` to it (no logic duplication; the external surface
    is the internal handler). Restores the real registry afterwards.
    """
    from services import agent_tools

    async def _fake(args: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "echo": args}

    agent_tools.register_tool("price_data", _fake)
    try:
        server = mcp_server.get_mcp_server()
        result = asyncio.run(server.call_tool("price_data", {"symbol": "AAPL"}))
        payload = result.structured_content or {}
        assert payload.get("ok") is True
        assert payload.get("echo") == {"symbol": "AAPL"}
    finally:
        agent_tools.reset_for_tests()


def test_failing_catalog_tool_returns_is_error() -> None:
    """R15-CODE-AGENT-023: a catalog-tool handler that raises comes back over MCP
    as ``isError: true`` (a :class:`fastmcp.exceptions.ToolError`), the same
    signal Vysted's own MCP-client code (openbb_mcp_provider, sec_filings_provider)
    keys failure off of — never a successful result whose body says ``ok: false``."""
    import json as _json

    from services import agent_tools

    async def _boom(_args: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("kaboom")

    agent_tools.register_tool("price_data", _boom)
    try:
        call = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "price_data", "arguments": {}},
        }
        with TestClient(mcp_server.get_streamable_http_app()) as mcp_client:
            response = mcp_client.post(
                "/",
                headers={"Accept": "application/json, text/event-stream"},
                json=call,
            )
        assert response.status_code == 200
        data_line = next(line for line in response.text.splitlines() if line.startswith("data:"))
        body = _json.loads(data_line.removeprefix("data:").strip())
        assert body["result"]["isError"] is True
        assert "kaboom" in body["result"]["content"][0]["text"]
    finally:
        agent_tools.reset_for_tests()


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


def test_list_agents_tool_wraps_router_response(client: TestClient) -> None:
    """``list_agents`` wraps the agents-router response under an ``agents`` key.

    A's ``GET /agents`` returns a bare JSON list (REST convention). FastMCP
    rejects bare-list tool outputs (``structured_content must be a dict or
    None``), so the MCP boundary wraps the list as ``{"agents": [...]}``.
    With A's first-party agents merged, the wrapped list contains the
    Phase-3 roster.
    """
    server = mcp_server.get_mcp_server()
    result = asyncio.run(server.call_tool("list_agents", {}))
    structured = result.structured_content or {}
    if "result" in structured:
        structured = structured["result"]
    assert isinstance(structured, dict)
    agents = structured.get("agents")
    assert isinstance(agents, list)
    # 13 first-party agents (12 personas + the Phase-10 copilot router).
    assert len(agents) == 13
    assert {agent["id"] for agent in agents} >= {"buffett", "strategy_critic"}


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


def test_status_protocol_version_matches_initialize_handshake(client: TestClient) -> None:
    """R15-CODE-AGENT-022: ``/mcp/status`` reports the SDK's
    ``LATEST_PROTOCOL_VERSION`` — the same revision a live ``initialize``
    handshake negotiates — not a hardcoded constant that drifts behind it."""
    import json as _json

    from mcp.types import LATEST_PROTOCOL_VERSION

    status = client.get("/mcp/status").json()
    assert status["protocolVersion"] == LATEST_PROTOCOL_VERSION

    call = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": LATEST_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        },
    }
    with TestClient(mcp_server.get_streamable_http_app()) as mcp_client:
        response = mcp_client.post(
            "/",
            headers={"Accept": "application/json, text/event-stream"},
            json=call,
        )
    assert response.status_code == 200
    # Streamable-HTTP framing: one ``data: <json>`` SSE line per message.
    data_line = next(line for line in response.text.splitlines() if line.startswith("data:"))
    handshake = _json.loads(data_line.removeprefix("data:").strip())
    assert handshake["result"]["protocolVersion"] == status["protocolVersion"]


# ---------------------------------------------------------------------------
# v0.5.0 workflow tools
# ---------------------------------------------------------------------------


def test_run_workflow_tool_runs_a_simple_spec(client: TestClient) -> None:
    """``run_workflow`` calls the engine directly and returns ``{ok, result}``."""
    import json as _json

    from services import workflow_engine

    async def _h(_inputs: dict, _config: dict) -> dict:
        return {"out": "value"}

    workflow_engine.register_node_type("test.passthrough", _h)
    try:
        spec = {
            "id": "wf-test-mcp",
            "name": "MCP test",
            "version": 1,
            "nodes": [
                {
                    "id": "a",
                    "type": "test.passthrough",
                    "position": {"x": 0, "y": 0},
                    "config": {},
                }
            ],
            "edges": [],
            "updatedAt": 0,
        }
        server = mcp_server.get_mcp_server()
        result = asyncio.run(server.call_tool("run_workflow", {"spec_json": _json.dumps(spec)}))
        # The tool returns ``{ok, result}``; FastMCP delivers it as the
        # ``structured_content`` dict verbatim.
        payload = result.structured_content or {}
        assert isinstance(payload, dict)
        assert payload.get("ok") is True
        run_result = payload.get("result")
        assert isinstance(run_result, dict)
        assert run_result["status"] == "ok"
    finally:
        workflow_engine.unregister_node_type("test.passthrough")


def test_run_workflow_tool_reports_invalid_spec_cleanly() -> None:
    """An unparseable spec returns ``{ok: False, error: ...}`` rather than raising."""
    server = mcp_server.get_mcp_server()
    result = asyncio.run(server.call_tool("run_workflow", {"spec_json": "{not json"}))
    payload = result.structured_content or {}
    assert payload.get("ok") is False
    assert "invalid workflow spec" in (payload.get("error") or "")


def test_list_workflows_tool_returns_dict_wrap(client: TestClient) -> None:
    """``list_workflows`` wraps the saved-workflows list per the FastMCP rule.

    The wrap-at-boundary Gotcha (v0.4.0) — bare lists are rejected by FastMCP;
    the tool ensures the response is ``{"workflows": [...]}`` even if the
    upstream router changes shape.
    """
    server = mcp_server.get_mcp_server()
    result = asyncio.run(server.call_tool("list_workflows", {}))
    payload = result.structured_content or {}
    assert isinstance(payload, dict)
    workflows = payload.get("workflows")
    assert isinstance(workflows, list)


def test_invoke_agent_takes_its_key_from_the_request_header_not_an_argument() -> None:
    """The key is never in the tool schema (the calling model's context); an
    ``X-Vysted-Api-Key`` header on the /mcp request reaches the invoke body."""
    tools = {t.name: t for t in asyncio.run(mcp_server.get_mcp_server().list_tools())}
    assert "api_key" not in tools["invoke_agent"].parameters["properties"]

    seen: dict[str, Any] = {}
    stub = FastAPI()

    @stub.post("/agents/{agent_id}/invoke")
    async def _invoke(agent_id: str, request: Request) -> StreamingResponse:
        seen["body"] = await request.json()
        frame = b'data: {"kind":"done","usage":{}}\n\n'
        return StreamingResponse(iter([frame]), media_type="text/event-stream")

    mcp_server.bind_app(stub)
    call = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "invoke_agent", "arguments": {"agent_id": "buffett", "prompt": "hi"}},
    }
    with TestClient(mcp_server.get_streamable_http_app()) as mcp_client:
        response = mcp_client.post(
            "/",
            headers={
                "Accept": "application/json, text/event-stream",
                "X-Vysted-Api-Key": "canary-key",
            },
            json=call,
        )
    assert response.status_code == 200
    assert seen["body"] == {"prompt": "hi", "api_key": "canary-key"}


@pytest.mark.parametrize(("tool", "path"), [("list_agents", "/agents"), ("list_runs", "/runs")])
def test_list_tool_reports_a_failing_route_as_not_ok(tool: str, path: str) -> None:
    """A 5xx from the in-process route is ``ok: false``, never an empty list."""
    broken = FastAPI()

    @broken.get(path)
    def _fail() -> None:
        raise HTTPException(status_code=500, detail="store unreadable")

    mcp_server.bind_app(broken)
    result = asyncio.run(mcp_server.get_mcp_server().call_tool(tool, {}))
    payload = result.structured_content or {}
    assert payload.get("ok") is False
    assert "500" in payload["error"]
