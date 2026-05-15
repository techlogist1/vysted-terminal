"""Vysted MCP server — exposes the sidecar's data + agent surface as MCP tools.

The Phase-3 brief calls for Vysted to participate in the Model Context Protocol
on BOTH sides. This module is the SERVER side: a FastMCP 3.x application
mounted into the main sidecar's FastAPI app at ``/mcp`` over the Streamable-HTTP
transport. External MCP clients — Claude Desktop via the ``mcp-remote``
bridge, Claude Code natively over HTTP — connect to this endpoint and see
Vysted's data layer (quotes, history, fundamentals, news, macro,
workspaces) and agent invocation as standard MCP tools.

Architecture notes
------------------

Each tool implementation is a thin shim that calls the corresponding sidecar
HTTP endpoint via an in-process :class:`httpx.AsyncClient` bound to the
already-running FastAPI app. There is no logic duplication — the MCP layer is
purely a protocol adapter. This keeps the data layer single-source: a router
fix lands in one place and the MCP tool surface picks it up.

``invoke_agent`` is the one tool that consumes an SSE stream and aggregates
it into a unary string, because MCP tool replies are unary by spec. The
aggregated content is what an external MCP client (the LLM) sees as the
tool's output.

The FastMCP app is created with ``stateless_http=True`` so each request
carries no server-side session state — the simplest mount shape and
the right call for a localhost-only sidecar where state can live with
the data layer (workspaces, plugin store, etc.) rather than the MCP
transport.

Tool registration is lazy: :func:`get_mcp_server` builds the FastMCP
instance on first call and caches it. Tests can reset the cache via the
``_reset_for_tests`` helper.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx
from fastapi import FastAPI
from fastmcp import FastMCP

_log = logging.getLogger(__name__)

# Streamable-HTTP transport, per the Phase-3 brief. ``/mcp`` is the mount
# point in the main sidecar; ``http_app(path="/")`` registers a single POST/
# DELETE endpoint and the outer ``app.mount("/mcp", ...)`` adds the prefix.
_TRANSPORT = "http"
_PROTOCOL_VERSION = "2025-06-18"  # MCP revision FastMCP 3.x speaks.

# Env var for an override base URL. In production the MCP server is mounted
# into the same app whose endpoints it calls, so the natural choice is an
# in-process AsyncClient bound to the ASGI app. Tests can set this to swap.
_SIDECAR_BASE_URL_ENV = "VYSTED_SIDECAR_INTERNAL_BASE_URL"

# Cached singletons.
_mcp_server: FastMCP | None = None
_streamable_http_app: Any = None
_app_reference: FastAPI | None = None


# ---------------------------------------------------------------------------
# Internal client — calls the host FastAPI app in-process where possible.
# ---------------------------------------------------------------------------


def _internal_client() -> httpx.AsyncClient:
    """Build an httpx AsyncClient that calls the host FastAPI app.

    When the FastAPI ``app`` reference has been registered via
    :func:`bind_app`, the client uses :class:`httpx.ASGITransport` so calls
    skip the network entirely — the MCP tool runs inside the same process
    as the data router. When unbound (tests, etc.), the env-var override
    is honoured.
    """
    override = os.environ.get(_SIDECAR_BASE_URL_ENV)
    if override:
        return httpx.AsyncClient(base_url=override, timeout=30.0)
    if _app_reference is not None:
        transport = httpx.ASGITransport(app=_app_reference)
        return httpx.AsyncClient(transport=transport, base_url="http://sidecar", timeout=30.0)
    # Fallback: assume localhost on the sidecar's default port. The MCP
    # server should normally be reached through the in-process transport;
    # this branch exists so an early failure produces a useful error.
    return httpx.AsyncClient(base_url="http://127.0.0.1:0", timeout=30.0)


def bind_app(app: FastAPI) -> None:
    """Register the host FastAPI app so MCP tools can call it in-process.

    Called once from :func:`app.create_app` after the routers are mounted.
    """
    global _app_reference
    _app_reference = app


# ---------------------------------------------------------------------------
# FastMCP setup — tool registration.
# ---------------------------------------------------------------------------


def _build_server() -> FastMCP:
    """Construct the FastMCP server and register every tool."""
    mcp = FastMCP("vysted")

    # ---------- Market data tools ----------

    @mcp.tool
    async def get_quote(symbol: str) -> dict[str, Any]:
        """Return the latest quote for the given equity symbol.

        Maps to GET /quotes/{symbol} on the Vysted sidecar.
        """
        async with _internal_client() as client:
            response = await client.get(f"/quotes/{symbol}")
            response.raise_for_status()
            return response.json()

    @mcp.tool
    async def get_history(symbol: str, timeframe: str = "1d", range_: str | None = None) -> dict[str, Any]:
        """Return OHLCV history bars for the given symbol and timeframe.

        Timeframe is one of: 1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo.
        Range is an optional ISO date (YYYY-MM-DD) that scopes the start.
        Maps to GET /history/{symbol}.
        """
        params: dict[str, str] = {"timeframe": timeframe}
        if range_:
            params["range"] = range_
        async with _internal_client() as client:
            response = await client.get(f"/history/{symbol}", params=params)
            response.raise_for_status()
            return response.json()

    @mcp.tool
    async def get_fundamentals(symbol: str) -> dict[str, Any]:
        """Return valuation ratios and company profile for the given symbol.

        Maps to GET /fundamentals/{symbol}.
        """
        async with _internal_client() as client:
            response = await client.get(f"/fundamentals/{symbol}")
            response.raise_for_status()
            return response.json()

    @mcp.tool
    async def get_news(symbols: list[str] | None = None, limit: int = 20) -> dict[str, Any]:
        """Return recent news headlines, optionally filtered by symbol list.

        Maps to GET /news. Symbols are joined into the ``symbols`` query
        parameter the sidecar expects.
        """
        params: dict[str, Any] = {"limit": limit}
        if symbols:
            params["symbols"] = ",".join(symbols)
        async with _internal_client() as client:
            response = await client.get("/news", params=params)
            response.raise_for_status()
            return response.json()

    @mcp.tool
    async def get_macro_series(series_id: str, provider: str | None = None) -> dict[str, Any]:
        """Return a macro time-series by id (FRED-style).

        Maps to GET /macro/{series_id}. Provider is an optional override
        for the upstream macro source (defaults to FRED).
        """
        params: dict[str, str] = {}
        if provider:
            params["provider"] = provider
        async with _internal_client() as client:
            response = await client.get(f"/macro/{series_id}", params=params)
            response.raise_for_status()
            return response.json()

    # ---------- Agent tools (Teammate A's surface) ----------

    @mcp.tool
    async def list_agents() -> dict[str, Any]:
        """List the agents available in this Vysted sidecar.

        Maps to GET /agents (Teammate A). When the agents router is not
        mounted (Teammate A pre-merge) this tool returns an empty list
        rather than erroring — keeps the MCP surface stable across
        teammate merges.
        """
        async with _internal_client() as client:
            try:
                response = await client.get("/agents")
                if response.status_code == 404:
                    return {"agents": []}
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as exc:
                _log.debug("list_agents: agents router not reachable: %s", exc)
                return {"agents": []}

    @mcp.tool
    async def invoke_agent(agent_id: str, prompt: str, api_key: str | None = None) -> dict[str, Any]:
        """Invoke an agent and aggregate its streaming reply into a single string.

        Maps to POST /agents/{agent_id}/invoke. The sidecar's agent runtime
        streams via Server-Sent Events; this tool consumes the stream and
        concatenates ``delta`` text events into one unary reply, which is
        what the MCP tool-call boundary requires. Returns
        ``{"agent_id", "content", "usage"}``.
        """
        body: dict[str, Any] = {"prompt": prompt}
        if api_key:
            body["api_key"] = api_key
        text_buffer: list[str] = []
        usage: dict[str, Any] = {}
        async with _internal_client() as client:
            try:
                async with client.stream(
                    "POST",
                    f"/agents/{agent_id}/invoke",
                    json=body,
                    headers={"Accept": "text/event-stream"},
                ) as response:
                    response.raise_for_status()
                    async for raw_line in response.aiter_lines():
                        if not raw_line or not raw_line.startswith("data:"):
                            continue
                        payload = raw_line[len("data:") :].strip()
                        if not payload or payload == "[DONE]":
                            continue
                        try:
                            event = json.loads(payload)
                        except json.JSONDecodeError:
                            text_buffer.append(payload)
                            continue
                        kind = event.get("kind") or event.get("type")
                        if kind == "delta":
                            text_buffer.append(str(event.get("text") or ""))
                        elif kind == "done":
                            usage = event.get("usage") or {}
                        elif kind == "error":
                            return {
                                "agent_id": agent_id,
                                "content": "".join(text_buffer),
                                "error": event.get("message") or "agent error",
                            }
            except httpx.HTTPError as exc:
                return {
                    "agent_id": agent_id,
                    "content": "".join(text_buffer),
                    "error": f"agent invocation failed: {exc}",
                }
        return {"agent_id": agent_id, "content": "".join(text_buffer), "usage": usage}

    # ---------- Workspace tools (existing workspace_store surface) ----------

    @mcp.tool
    async def list_workspaces() -> dict[str, Any]:
        """List saved workspaces. Maps to GET /workspaces."""
        async with _internal_client() as client:
            response = await client.get("/workspaces")
            response.raise_for_status()
            return response.json()

    @mcp.tool
    async def get_workspace(workspace_id: str) -> dict[str, Any]:
        """Return a saved workspace by id. Maps to GET /workspaces/{id}."""
        async with _internal_client() as client:
            response = await client.get(f"/workspaces/{workspace_id}")
            response.raise_for_status()
            return response.json()

    return mcp


def get_mcp_server() -> FastMCP:
    """Return the singleton FastMCP server, building it on first call."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = _build_server()
    return _mcp_server


def get_streamable_http_app() -> Any:
    """Return the Starlette ASGI app for the FastMCP Streamable-HTTP transport.

    The sidecar's ``create_app`` mounts the returned app under ``/mcp``, so
    external MCP clients reach it at ``http://127.0.0.1:<port>/mcp``.
    Stateless HTTP keeps the mount surface trivial — no per-client session
    bookkeeping in the sidecar.

    Crucially: the returned Starlette app must be the SAME instance used both
    for the parent's ``app.mount("/mcp", ...)`` and for the parent's
    ``lifespan`` driver (FastMCP's StreamableHTTPSessionManager is initialised
    in the app's lifespan; if a fresh app is constructed for the lifespan and a
    different one for the mount, every request raises "Task group is not
    initialized"). The function caches the instance for that reason.
    """
    global _streamable_http_app
    if _streamable_http_app is None:
        _streamable_http_app = get_mcp_server().http_app(
            path="/", transport=_TRANSPORT, stateless_http=True
        )
    return _streamable_http_app


def protocol_version() -> str:
    """Return the MCP protocol revision this server speaks (e.g. ``"2025-06-18"``)."""
    return _PROTOCOL_VERSION


async def tool_count() -> int:
    """Return the number of tools currently registered on the MCP server."""
    server = get_mcp_server()
    tools = await server.list_tools()
    return len(tools)


def _reset_for_tests() -> None:
    """Clear cached state — used only from the test suite."""
    global _mcp_server, _app_reference, _streamable_http_app
    _mcp_server = None
    _app_reference = None
    _streamable_http_app = None
