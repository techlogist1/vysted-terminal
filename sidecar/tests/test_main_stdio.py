"""Tests for the sidecar entrypoint — the ``--mcp-stdio`` MCP transport (FR-025).

The stdio entrypoint reuses the one sidecar binary: instead of binding a port
under uvicorn it runs the FastMCP server over stdin/stdout so an external MCP
client can spawn the binary directly. These tests assert the arg parsing makes
``--port`` optional in stdio mode and that the stdio branch builds the server
with the full catalog tool set — WITHOUT entering the real (blocking) stdio
loop or binding a port.
"""

from __future__ import annotations

import asyncio

import pytest

import main
from services import mcp_server
from services.agent_tools.catalog import mcp_capabilities


def test_port_optional_when_mcp_stdio() -> None:
    """``--mcp-stdio`` does not require ``--port``; the default HTTP path does."""
    parser = main._build_parser()

    stdio_args = parser.parse_args(["--mcp-stdio"])
    assert stdio_args.mcp_stdio is True
    assert stdio_args.port is None

    http_args = parser.parse_args(["--port", "54321"])
    assert http_args.mcp_stdio is False
    assert http_args.port == 54321


def test_http_mode_without_port_errors() -> None:
    """HTTP mode (no ``--mcp-stdio``) still requires ``--port``."""
    with pytest.raises(SystemExit):
        main.main([])


def test_mcp_stdio_branch_builds_full_catalog_tool_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The stdio entrypoint registers runtime tools, binds the app, and builds the
    FastMCP server with every catalog-projected tool — without blocking on the
    real stdio loop or binding a port."""
    mcp_server._reset_for_tests()

    ran: dict[str, object] = {}

    def _fake_run(self: object, transport: str | None = None, **kwargs: object) -> None:
        # Capture the call instead of entering the blocking anyio stdio loop.
        ran["transport"] = transport
        ran["kwargs"] = kwargs

    monkeypatch.setattr(mcp_server.FastMCP, "run", _fake_run, raising=True)

    main.main(["--mcp-stdio"])

    assert ran["transport"] == "stdio"
    # Banner suppressed so the JSON-RPC stdout channel stays clean.
    assert ran["kwargs"] == {"show_banner": False}

    # The server the stdio path built carries the full catalog tool surface.
    server = mcp_server.get_mcp_server()
    tools = asyncio.run(server.list_tools())
    tool_names = {tool.name for tool in tools}
    catalog_names = {cap.id for cap in mcp_capabilities()}
    assert catalog_names, "catalog projection must be non-empty"
    assert catalog_names <= tool_names, (
        f"stdio MCP server missing catalog tools: {catalog_names - tool_names}"
    )

    mcp_server._reset_for_tests()
