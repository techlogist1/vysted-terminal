"""Tests for the MCP client wrapper (Vysted-as-client).

The :class:`McpClient` is exercised against a real FastMCP-served Streamable-
HTTP transport, running in-process via Starlette's ``TestClient`` substitute
(httpx ASGITransport). We can't ``TestClient`` the FastMCP app directly (the
``ClientSession`` handshake needs persistent bidirectional streams), so the
session-shape assertions monkey-patch the underlying ``mcp`` SDK pieces.

What the tests cover:
  - Cache + reset behaviour of :func:`get_client`.
  - Any call failure drops the cached session and raises ProviderError.
  - The reply-shape mapping turns MCP content blocks into the dict shape
    callers consume.
"""

from __future__ import annotations

import asyncio
import contextlib
import socket
from typing import Any

import anyio
import httpx
import mcp
import pytest

from services import mcp_client
from services.errors import ProviderError


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


@pytest.mark.parametrize(
    "exc",
    [
        mcp.McpError(error=mcp.ErrorData(code=-32000, message="boom")),
        anyio.ClosedResourceError(),
        httpx.ReadError("peer closed"),
        asyncio.CancelledError("Cancelled via cancel scope"),
    ],
    ids=["McpError", "ClosedResourceError", "ReadError", "transport-CancelledError"],
)
def test_call_tool_failure_drops_session_and_raises_provider_error(
    monkeypatch: pytest.MonkeyPatch, exc: BaseException
) -> None:
    """Any failure of a call (including a CancelledError the transport raised while
    the caller is not being cancelled) drops the session and becomes a ProviderError,
    the only error the provider registry falls through on (R15-CODE-AGENT-002)."""

    async def _go() -> None:
        client = mcp_client.McpClient("boom", transport="http", endpoint="http://127.0.0.1:0/mcp/")
        client._session = _FakeSession()

        async def _raise_call(self: Any, name: str, args: dict[str, Any]) -> Any:
            raise exc

        monkeypatch.setattr(_FakeSession, "call_tool", _raise_call)
        with pytest.raises(ProviderError):
            await client.call_tool("x", {})
        assert client._session is None
        await asyncio.sleep(0)  # the calling task was not left cancelled

    asyncio.run(_go())


def test_outer_cancellation_still_cancels_the_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """A genuine cancellation of the calling task propagates and keeps the session."""

    async def _go() -> None:
        client = mcp_client.McpClient("slow", transport="http", endpoint="http://127.0.0.1:0/mcp/")
        session = _FakeSession()
        client._session = session

        async def _hang(self: Any, name: str, args: dict[str, Any]) -> Any:
            await asyncio.Event().wait()

        monkeypatch.setattr(_FakeSession, "call_tool", _hang)
        task = asyncio.create_task(client.call_tool("x", {}))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert client._session is session

    asyncio.run(_go())


def test_open_against_a_closed_port_raises_provider_error() -> None:
    """A dead child (nothing listening) fails the open as a ProviderError and leaves
    the calling task usable; it used to escape as the transport's CancelledError and
    tear down the request (R15-LIFECYCLE-005)."""

    async def _go() -> None:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        client = mcp_client.McpClient(
            "dead", transport="http", endpoint=f"http://127.0.0.1:{port}/mcp"
        )
        with pytest.raises(ProviderError, match="ConnectError"):
            await client.call_tool("x", {})
        assert client._session is None
        await asyncio.sleep(0.01)  # would raise CancelledError if the request were poisoned

    asyncio.run(_go())


def test_transport_death_does_not_cancel_the_task_that_opened_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The transport's task group lives in the client's owner task, so when the child
    dies later it cancels that task only, never the request that opened the session."""

    died = asyncio.Event()

    @contextlib.asynccontextmanager
    async def _dying_transport(_url: str) -> Any:
        async with anyio.create_task_group() as tg:

            async def _die() -> None:
                await died.wait()
                raise httpx.ConnectError("child died")

            tg.start_soon(_die)
            yield (None, None, None)

    class _Session(_FakeSession):
        async def __aenter__(self) -> _Session:
            return self

        async def __aexit__(self, *_exc: Any) -> None:
            return None

    monkeypatch.setattr(mcp_client, "streamablehttp_client", _dying_transport)
    monkeypatch.setattr(mcp_client, "ClientSession", _Session)

    async def _go() -> None:
        client = mcp_client.McpClient("t", transport="http", endpoint="http://127.0.0.1:0/mcp")
        await client.list_tools()
        assert client._session is not None
        died.set()
        await asyncio.sleep(0.05)  # the opener survives the transport's cancellation
        assert client._session is None
        await client.close()

    asyncio.run(_go())


def test_call_tool_maps_text_blocks_to_dicts(monkeypatch: pytest.MonkeyPatch) -> None:
    """``call_tool`` translates the MCP ``CallToolResult`` into a plain dict."""

    async def _go() -> None:
        client = mcp_client.McpClient("ok", transport="http", endpoint="http://127.0.0.1:0/mcp/")

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
        result = await client.call_tool("any", {})
        assert result["isError"] is False
        assert result["content"][0]["type"] == "text"
        assert result["content"][0]["text"] == '{"hello": "world"}'

    asyncio.run(_go())


def test_call_tool_passes_structured_content_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """``call_tool`` no longer drops ``structuredContent`` (R15-CODE-AGENT-025):
    a result with no text block but a structured body decodes through a
    provider's structured-content fallback instead of "no content"."""

    async def _go() -> None:
        client = mcp_client.McpClient("ok", transport="http", endpoint="http://127.0.0.1:0/mcp/")

        class _Result:
            isError = False
            content: list[Any] = []
            structuredContent = {"x": 1}

        async def _fake_call(self: Any, name: str, args: dict[str, Any]) -> Any:
            return _Result()

        monkeypatch.setattr(_FakeSession, "call_tool", _fake_call)
        client._session = _FakeSession()
        result = await client.call_tool("any", {})
        assert result["structuredContent"] == {"x": 1}

        from services import sec_filings_provider

        decoded = sec_filings_provider._decode_tool_result(result, "any")
        assert decoded == {"x": 1}

    asyncio.run(_go())


def test_call_tool_structured_content_defaults_to_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """A ``CallToolResult`` lookalike with no ``structuredContent`` attribute
    (older/minimal fakes) does not blow up the mapping."""

    async def _go() -> None:
        client = mcp_client.McpClient("ok", transport="http", endpoint="http://127.0.0.1:0/mcp/")

        class _Result:
            isError = False
            content: list[Any] = []

        async def _fake_call(self: Any, name: str, args: dict[str, Any]) -> Any:
            return _Result()

        monkeypatch.setattr(_FakeSession, "call_tool", _fake_call)
        client._session = _FakeSession()
        result = await client.call_tool("any", {})
        assert result["structuredContent"] is None

    asyncio.run(_go())


def test_local_mcp_subprocess_resolves_and_decodes_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """A :class:`LocalMcpSubprocess` resolves its endpoint from env vars,
    reports status, and ``call_tool_json`` decodes text+structuredContent
    through the caller's ``decode`` exactly once, updating health flags."""

    async def _go() -> None:
        monkeypatch.setenv("TEST_MCP_PORT", "9876")
        subprocess = mcp_client.LocalMcpSubprocess(
            "sec-edgar", port_env="TEST_MCP_PORT", host_env="TEST_MCP_HOST"
        )
        assert subprocess.resolve_endpoint() == "http://127.0.0.1:9876/mcp"
        assert subprocess.is_available() is True

        status = await subprocess.status("sec-edgar-mcp")
        assert status == {
            "available": True,
            "provider": "sec-edgar-mcp",
            "endpoint": "http://127.0.0.1:9876/mcp",
            "lastToolCallOk": None,
            "lastError": None,
        }

        calls: list[str] = []

        def _decode(result: dict[str, Any], name: str) -> Any:
            calls.append(name)
            return result.get("structuredContent") or {
                b["text"]: True for b in result["content"] if b["type"] == "text"
            }

        client = mcp_client.McpClient("sec-edgar", transport="http", endpoint="http://x/mcp")
        client._session = _FakeSession()

        class _Result:
            isError = False
            content: list[Any] = []
            structuredContent = {"decoded": "once"}

        async def _fake_call(self: Any, name: str, args: dict[str, Any]) -> Any:
            return _Result()

        monkeypatch.setattr(_FakeSession, "call_tool", _fake_call)

        async def _fake_get_client(*_a: Any, **_k: Any) -> mcp_client.McpClient:
            return client

        monkeypatch.setattr(mcp_client, "get_client", _fake_get_client)

        decoded = await subprocess.call_tool_json("t", {}, decode=_decode)
        assert decoded == {"decoded": "once"}
        assert calls == ["t"]  # decode ran exactly once
        assert subprocess.last_tool_call_ok is True
        assert subprocess.last_error is None

    asyncio.run(_go())


def test_local_mcp_subprocess_port_zero_is_not_available() -> None:
    """A port of ``"0"`` (Tauri's graceful-degrade signal) is treated the
    same as an unset env var, not as a real endpoint."""
    subprocess = mcp_client.LocalMcpSubprocess(
        "x", port_env="UNSET_TEST_PORT_ZERO", host_env="UNSET_TEST_HOST_ZERO"
    )
    assert subprocess.resolve_endpoint() is None
    assert subprocess.is_available() is False


def test_local_mcp_subprocess_call_failure_marks_unhealthy(monkeypatch: pytest.MonkeyPatch) -> None:
    """A decode failure counts as a failed call (R15-DATA-083): the health
    flags record it, wrapped as a :class:`ProviderError`."""

    async def _go() -> None:
        monkeypatch.setenv("TEST_MCP_PORT_2", "1234")
        subprocess = mcp_client.LocalMcpSubprocess(
            "openbb-mcp", port_env="TEST_MCP_PORT_2", host_env="TEST_MCP_HOST_2"
        )
        client = mcp_client.McpClient("openbb-mcp", transport="http", endpoint="http://x/mcp")
        client._session = _FakeSession()

        class _Result:
            isError = False
            content: list[Any] = []
            structuredContent = None

        async def _fake_call(self: Any, name: str, args: dict[str, Any]) -> Any:
            return _Result()

        def _decode(result: dict[str, Any], name: str) -> Any:
            raise ValueError("bad payload")

        monkeypatch.setattr(_FakeSession, "call_tool", _fake_call)

        async def _fake_get_client(*_a: Any, **_k: Any) -> mcp_client.McpClient:
            return client

        monkeypatch.setattr(mcp_client, "get_client", _fake_get_client)

        with pytest.raises(ProviderError):
            await subprocess.call_tool_json("t", {}, decode=_decode)
        assert subprocess.last_tool_call_ok is False
        assert subprocess.last_error is not None

    asyncio.run(_go())


def test_list_tools_returns_dicts(monkeypatch: pytest.MonkeyPatch) -> None:
    """``list_tools`` returns dicts whose ``name`` field matches the MCP server's."""

    async def _go() -> None:
        client = mcp_client.McpClient("ok", transport="http", endpoint="http://127.0.0.1:0/mcp/")

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
        tools = await client.list_tools()
        assert tools == [
            {"name": "foo", "description": "a foo tool", "inputSchema": {"type": "object"}}
        ]

    asyncio.run(_go())
