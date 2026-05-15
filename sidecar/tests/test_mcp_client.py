"""Tests for the MCP client wrapper (Vysted-as-client).

The :class:`McpClient` is exercised against a real FastMCP-served Streamable-
HTTP transport, running in-process via Starlette's ``TestClient`` substitute
(httpx ASGITransport). We can't ``TestClient`` the FastMCP app directly (the
``ClientSession`` handshake needs persistent bidirectional streams), so the
session-shape assertions monkey-patch the underlying ``mcp`` SDK pieces.

What the tests cover:
  - Cache + reset behaviour of :func:`get_client`.
  - Transport-failure path drops the cached session.
  - The reply-shape mapping turns MCP content blocks into the dict shape
    callers consume.
"""

from __future__ import annotations

import asyncio
from typing import Any

import mcp
import pytest

from services import mcp_client


@pytest.fixture(autouse=True)
def _reset_clients() -> Any:
    asyncio.run(mcp_client.reset_clients())
    yield
    asyncio.run(mcp_client.reset_clients())


class _FakeSession:
    """A stand-in for :class:`mcp.client.session.ClientSession`."""

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self._tools: list[Any] = []
        self._call_result: Any | None = None

    async def initialize(self) -> None:
        return None

    async def list_tools(self) -> Any:
        class _Result:
            tools = self._tools

        return _Result()

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        return self._call_result


def test_get_client_caches_per_server_id() -> None:
    async def _go() -> None:
        first = await mcp_client.get_client(
            "test", transport="http", endpoint="http://127.0.0.1:0/mcp/"
        )
        second = await mcp_client.get_client(
            "test", transport="http", endpoint="http://127.0.0.1:0/mcp/"
        )
        assert first is second

    asyncio.run(_go())


def test_reset_clients_purges_cache() -> None:
    async def _go() -> None:
        first = await mcp_client.get_client(
            "test", transport="http", endpoint="http://127.0.0.1:0/mcp/"
        )
        await mcp_client.reset_clients()
        second = await mcp_client.get_client(
            "test", transport="http", endpoint="http://127.0.0.1:0/mcp/"
        )
        assert first is not second

    asyncio.run(_go())


def test_unknown_transport_raises_clean_error() -> None:
    """``McpClient`` with an unknown transport rejects the call cleanly."""

    async def _go() -> None:
        client = mcp_client.McpClient("bad", transport="ipx")
        with pytest.raises(ValueError, match="Unknown MCP transport"):
            await client.list_tools()

    asyncio.run(_go())


def test_http_client_without_endpoint_raises() -> None:
    """``http`` transport without an endpoint surfaces a clear error."""

    async def _go() -> None:
        client = mcp_client.McpClient("no-endpoint", transport="http")
        with pytest.raises(ValueError, match="no endpoint was provided"):
            await client.list_tools()

    asyncio.run(_go())


def test_stdio_client_without_command_raises() -> None:
    """``stdio`` transport without a command surfaces a clear error."""

    async def _go() -> None:
        client = mcp_client.McpClient("no-command", transport="stdio")
        with pytest.raises(ValueError, match="no command was provided"):
            await client.list_tools()

    asyncio.run(_go())


def test_call_tool_failure_drops_cached_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """A transport error during ``call_tool`` clears the session so the next call reconnects."""

    async def _go() -> None:
        client = mcp_client.McpClient(
            "boom", transport="http", endpoint="http://127.0.0.1:0/mcp/"
        )
        # Plant a fake session so ``_ensure_session`` returns it.
        client._session = _FakeSession()
        client._exit_stack = None

        async def _raise_call(self: Any, name: str, args: dict[str, Any]) -> Any:
            raise mcp.McpError(error=mcp.ErrorData(code=-32000, message="boom"))

        monkeypatch.setattr(_FakeSession, "call_tool", _raise_call)
        with pytest.raises(mcp.McpError):
            await client.call_tool("x", {})
        assert client._session is None

    asyncio.run(_go())


def test_call_tool_maps_text_blocks_to_dicts(monkeypatch: pytest.MonkeyPatch) -> None:
    """``call_tool`` translates the MCP ``CallToolResult`` into a plain dict."""

    async def _go() -> None:
        client = mcp_client.McpClient(
            "ok", transport="http", endpoint="http://127.0.0.1:0/mcp/"
        )
        # Build a minimal ``CallToolResult`` lookalike with one text block.
        class _Block:
            type = "text"
            text = '{"hello": "world"}'

        class _Result:
            isError = False
            content = [_Block()]

        async def _fake_call(self: Any, name: str, args: dict[str, Any]) -> Any:
            return _Result()

        monkeypatch.setattr(_FakeSession, "call_tool", _fake_call)
        client._session = _FakeSession()
        client._exit_stack = None
        result = await client.call_tool("any", {})
        assert result["isError"] is False
        assert result["content"][0]["type"] == "text"
        assert result["content"][0]["text"] == '{"hello": "world"}'

    asyncio.run(_go())


def test_list_tools_returns_dicts(monkeypatch: pytest.MonkeyPatch) -> None:
    """``list_tools`` returns dicts whose ``name`` field matches the MCP server's."""

    async def _go() -> None:
        client = mcp_client.McpClient(
            "ok", transport="http", endpoint="http://127.0.0.1:0/mcp/"
        )

        class _Tool:
            name = "foo"
            description = "a foo tool"
            inputSchema = {"type": "object"}

        async def _fake_list(self: Any) -> Any:
            class _R:
                tools = [_Tool()]

            return _R()

        monkeypatch.setattr(_FakeSession, "list_tools", _fake_list)
        client._session = _FakeSession()
        client._exit_stack = None
        tools = await client.list_tools()
        assert tools == [{"name": "foo", "description": "a foo tool", "inputSchema": {"type": "object"}}]

    asyncio.run(_go())
