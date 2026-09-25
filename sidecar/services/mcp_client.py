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

Reconnect-on-error: any failure of a call (the underlying anyio streams
close, the JSON-RPC request times out, the server returns an
:class:`mcp.McpError`, the transport's task group cancels) drops the cached
session so the next call rebuilds it, and surfaces as a
:class:`~services.errors.ProviderError` so the provider registry falls
through; only a genuine cancellation of the calling task propagates. That
keeps the call sites idiom-free — they call ``list_tools()`` or
``call_tool(...)`` and the wrapper handles the connection-state machine.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamablehttp_client

from services.errors import ProviderError

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
        self._owner: asyncio.Task[None] | None = None
        self._stop: asyncio.Event | None = None
        self._lock = asyncio.Lock()
        # Bumped every time a new session is opened. A failing call captures the
        # generation it ran against and passes it to ``close()`` so a stale
        # error handler can't tear down a session a SIBLING request already
        # reopened (the concurrent-cold-call poisoning race).
        self._generation = 0

    async def _open(self) -> ClientSession:
        """Open the transport and return an initialised :class:`ClientSession`.

        The transport and session contexts are entered and exited in a dedicated
        owner task. Their anyio task groups cancel the task that hosts them when
        the child dies; hosting them in the request task let a dead child cancel
        whichever request happened to open the session (R15-LIFECYCLE-005).
        """
        if self.transport == "http":
            if not self.endpoint:
                raise ValueError(
                    f"MCP server {self.server_id!r} is configured for http transport "
                    "but no endpoint was provided."
                )
            transport_cm: Any = streamablehttp_client(self.endpoint)
        elif self.transport == "stdio":
            if not self.command:
                raise ValueError(
                    f"MCP server {self.server_id!r} is configured for stdio transport "
                    "but no command was provided."
                )
            params = StdioServerParameters(
                command=self.command, args=list(self.args), env=dict(self.env) or None
            )
            transport_cm = stdio_client(params)
        else:
            raise ValueError(
                f"Unknown MCP transport {self.transport!r} for server {self.server_id!r}."
            )

        ready: asyncio.Future[ClientSession] = asyncio.get_running_loop().create_future()
        stop = asyncio.Event()

        async def _own() -> None:
            session: ClientSession | None = None
            try:
                async with transport_cm as streams:
                    async with ClientSession(
                        streams[0], streams[1], read_timeout_seconds=_REQUEST_TIMEOUT
                    ) as session:
                        await asyncio.wait_for(session.initialize(), timeout=_INIT_TIMEOUT_S)
                        if not ready.done():
                            ready.set_result(session)
                        await stop.wait()
            except BaseException as exc:  # noqa: BLE001 - the transport's failure lands here
                while isinstance(exc, BaseExceptionGroup):
                    exc = exc.exceptions[0]  # the task group wraps the real cause
                if not ready.done():
                    ready.set_exception(
                        ProviderError(f"MCP server {self.server_id!r} failed to open: {exc!r}")
                    )
                _log.debug("MCP %r transport ended: %r", self.server_id, exc)
            finally:
                if session is not None and self._session is session:
                    self._session = None

        owner = asyncio.create_task(_own(), name=f"mcp-{self.server_id}")
        try:
            session = await ready
        except asyncio.CancelledError:
            owner.cancel()
            raise
        self._owner = owner
        self._stop = stop
        self._session = session
        self._generation += 1
        return session

    async def _ensure_session(self) -> tuple[ClientSession, int]:
        if self._session is None:
            async with self._lock:
                if self._session is None:
                    await self._open()
        assert self._session is not None
        return self._session, self._generation

    async def close(self, expected_generation: int | None = None) -> None:
        """Tear down the transport. Safe to call multiple times.

        ``expected_generation`` lets a failing call request teardown of only the
        session it actually ran against — if a sibling request already reopened
        a newer session (generation advanced), this no-ops instead of killing
        the fresh session out from under that sibling.
        """
        async with self._lock:
            if expected_generation is not None and expected_generation != self._generation:
                return  # a newer session was already opened; don't tear it down
            owner, self._owner = self._owner, None
            if self._stop is not None:
                self._stop.set()
            self._stop = None
            self._session = None
            if owner is not None:
                await owner

    async def _failed(self, exc: BaseException, what: str, generation: int) -> ProviderError:
        """Drop the session a call failed on and return the ProviderError to raise.

        A ``CancelledError`` while this task is not itself being cancelled came
        from the transport, not from the caller, so it is a failure like any
        other; a genuine outer cancellation is re-raised untouched.
        """
        task = asyncio.current_task()
        if isinstance(exc, asyncio.CancelledError) and task is not None and task.cancelling():
            raise exc
        _log.debug("MCP %r %s failed, dropping session: %r", self.server_id, what, exc)
        await self.close(expected_generation=generation)
        return ProviderError(f"MCP server {self.server_id!r} {what} failed: {exc!r}")

    async def list_tools(self) -> list[dict[str, Any]]:
        """Return the external server's tool definitions as plain dicts."""
        session, generation = await self._ensure_session()
        try:
            result = await session.list_tools()
        except (Exception, asyncio.CancelledError) as exc:
            raise await self._failed(exc, "list_tools", generation) from exc
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
        ``types/mcp.ts``. Any failure drops the cached session so the next
        call reconnects, and raises :class:`ProviderError`.
        """
        session, generation = await self._ensure_session()
        try:
            result = await session.call_tool(name, arguments or {})
        except (Exception, asyncio.CancelledError) as exc:
            raise await self._failed(exc, f"call_tool({name})", generation) from exc

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
        return {
            "isError": bool(result.isError),
            "content": content,
            # FastMCP 3.x tools with an ``output_schema`` reply with structured
            # content alongside (or instead of) a text block; pass it through so
            # a caller whose decode falls back to it (e.g. sec_filings_provider)
            # sees real data instead of "no content" (R15-CODE-AGENT-025).
            "structuredContent": getattr(result, "structuredContent", None),
        }


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
