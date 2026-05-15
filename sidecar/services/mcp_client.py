"""MCP client wrapper — connects to external MCP servers.

Vysted-as-client. Wraps the official ``mcp`` Python SDK's session
+ transport primitives behind a small, stable surface the sidecar's
services use:

- :class:`McpClient` opens and supervises one connection to one external
  MCP server. Supports the two transports the Phase-3 brief calls out:
  Streamable-HTTP (the first real consumer is openbb-mcp-server) and
  stdio (kept compatible for future filesystem-installed plugins).
- :func:`get_client` lazily caches one :class:`McpClient` per server id
  so a per-call connect/handshake/teardown does not dominate latency.
- :func:`reset_clients` is the test-friendly cache-purge.

Reconnect-on-error: any transport-level failure (the underlying anyio
streams close, the JSON-RPC request times out, the server returns an
:class:`mcp.McpError`) drops the cached session so the next call rebuilds
it. That keeps the call sites idiom-free — they call ``list_tools()`` or
``call_tool(...)`` and the wrapper handles the connection-state machine.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import AsyncExitStack
from datetime import timedelta
from typing import Any

import mcp
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamablehttp_client

_log = logging.getLogger(__name__)

# Reasonable defaults for a localhost transport. The Tauri-spawned
# openbb-mcp-server replies in tens of milliseconds for cache hits and
# up to a few seconds for fresh upstream calls; 60 s leaves headroom.
_REQUEST_TIMEOUT = timedelta(seconds=60.0)
_INIT_TIMEOUT_S = 30.0


# ---------------------------------------------------------------------------
# Config types — mirror ``types/mcp.ts``'s McpServerConfig.
# ---------------------------------------------------------------------------


class McpClient:
    """One connection to one external MCP server.

    Built by :func:`get_client` (cached by server id) so callers never need
    to manage transport lifecycles. Calls are async and re-entrant; the
    underlying session is created on first call and recreated on transport
    error.
    """

    def __init__(
        self,
        server_id: str,
        *,
        transport: str,
        endpoint: str | None = None,
        command: str | None = None,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.server_id = server_id
        self.transport = transport
        self.endpoint = endpoint
        self.command = command
        self.args = args or []
        self.env = env or {}
        self._session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None
        self._lock = asyncio.Lock()

    async def _open(self) -> ClientSession:
        """Open the transport and return an initialised :class:`ClientSession`."""
        exit_stack = AsyncExitStack()
        try:
            if self.transport == "http":
                if not self.endpoint:
                    raise ValueError(
                        f"MCP server {self.server_id!r} is configured for http transport "
                        "but no endpoint was provided."
                    )
                read_stream, write_stream, _get_session_id = await exit_stack.enter_async_context(
                    streamablehttp_client(self.endpoint)
                )
            elif self.transport == "stdio":
                if not self.command:
                    raise ValueError(
                        f"MCP server {self.server_id!r} is configured for stdio transport "
                        "but no command was provided."
                    )
                params = StdioServerParameters(
                    command=self.command, args=list(self.args), env=dict(self.env) or None
                )
                read_stream, write_stream = await exit_stack.enter_async_context(
                    stdio_client(params)
                )
            else:
                raise ValueError(
                    f"Unknown MCP transport {self.transport!r} for server {self.server_id!r}."
                )

            session = await exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream, read_timeout_seconds=_REQUEST_TIMEOUT)
            )
            await asyncio.wait_for(session.initialize(), timeout=_INIT_TIMEOUT_S)
        except Exception:
            await exit_stack.aclose()
            raise

        self._exit_stack = exit_stack
        self._session = session
        return session

    async def _ensure_session(self) -> ClientSession:
        if self._session is None:
            async with self._lock:
                if self._session is None:
                    await self._open()
        assert self._session is not None
        return self._session

    async def close(self) -> None:
        """Tear down the transport. Safe to call multiple times."""
        async with self._lock:
            if self._exit_stack is not None:
                try:
                    await self._exit_stack.aclose()
                except Exception as exc:  # noqa: BLE001
                    _log.debug("MCP client %r close raised: %s", self.server_id, exc)
            self._exit_stack = None
            self._session = None

    async def list_tools(self) -> list[dict[str, Any]]:
        """Return the external server's tool definitions as plain dicts."""
        session = await self._ensure_session()
        try:
            result = await session.list_tools()
        except (mcp.McpError, OSError, asyncio.TimeoutError) as exc:
            _log.debug("MCP %r list_tools failed, dropping session: %s", self.server_id, exc)
            await self.close()
            raise
        return [
            {
                "name": tool.name,
                "description": tool.description or "",
                "inputSchema": tool.inputSchema or {},
            }
            for tool in result.tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Invoke a tool on the external server and return a dict result.

        Returns ``{"isError", "content"}`` where ``content`` is a list of
        text/image/resource blocks shaped to match ``McpContentBlock`` in
        ``types/mcp.ts``. Transport-level failures drop the cached session
        so the next call reconnects.
        """
        session = await self._ensure_session()
        try:
            result = await session.call_tool(name, arguments or {})
        except (mcp.McpError, OSError, asyncio.TimeoutError) as exc:
            _log.debug("MCP %r call_tool(%s) failed, dropping session: %s", self.server_id, name, exc)
            await self.close()
            raise

        content: list[dict[str, Any]] = []
        for block in result.content:
            kind = getattr(block, "type", None)
            if kind == "text":
                content.append({"type": "text", "text": getattr(block, "text", "")})
            elif kind == "image":
                content.append(
                    {
                        "type": "image",
                        "data": getattr(block, "data", ""),
                        "mimeType": getattr(block, "mimeType", "application/octet-stream"),
                    }
                )
            else:
                # Future-proof: stringify any unknown block so callers always
                # have something to log even if the spec adds new block kinds.
                content.append({"type": "text", "text": str(block)})
        return {"isError": bool(result.isError), "content": content}


# ---------------------------------------------------------------------------
# Module-level registry — one cached client per server id.
# ---------------------------------------------------------------------------


_clients: dict[str, McpClient] = {}
_clients_lock = asyncio.Lock()


async def get_client(
    server_id: str,
    *,
    transport: str,
    endpoint: str | None = None,
    command: str | None = None,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> McpClient:
    """Return a cached :class:`McpClient` for ``server_id``, building on first call."""
    async with _clients_lock:
        existing = _clients.get(server_id)
        if existing is not None:
            return existing
        client = McpClient(
            server_id,
            transport=transport,
            endpoint=endpoint,
            command=command,
            args=args,
            env=env,
        )
        _clients[server_id] = client
        return client


async def reset_clients() -> None:
    """Close and forget every cached client. Used by tests + at sidecar shutdown."""
    async with _clients_lock:
        clients = list(_clients.values())
        _clients.clear()
    for client in clients:
        await client.close()
