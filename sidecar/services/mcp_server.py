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
from fastmcp.tools import FunctionTool
from mcp.types import ToolAnnotations

from services import agent_tools
from services.agent_tools.catalog import mcp_capabilities

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


def _make_catalog_tool(tool_id: str) -> Any:
    """Build an MCP tool handler that dispatches to the registered agent_tools
    handler for ``tool_id`` — the SAME handler the internal copilot loop calls.

    No logic duplication: the external MCP surface and the internal agent loop
    run the identical handler. Errors (unregistered handler, handler raise)
    surface as a structured ``{"ok": False, "error": ...}`` dict so an MCP
    client recovers cleanly rather than seeing a transport error.
    """

    async def _handler(**kwargs: Any) -> dict[str, Any]:
        try:
            return await agent_tools.invoke_tool(tool_id, kwargs)
        except KeyError:
            return {"ok": False, "error": f"tool {tool_id!r} is not available in this build"}
        except Exception as exc:  # noqa: BLE001 — surface to the MCP client
            return {"ok": False, "error": f"tool {tool_id!r} raised: {exc}"}

    return _handler


# ---------------------------------------------------------------------------
# FastMCP setup — tool registration.
# ---------------------------------------------------------------------------


def _build_server() -> FastMCP:
    """Construct the FastMCP server and register every tool."""
    mcp = FastMCP("vysted")

    # ---------- Data + analysis tools (projected from the capability catalog) ----------
    #
    # FR-020/021/022: the external MCP surface is NOT a hand-maintained
    # duplicate. Every data/analysis capability is declared ONCE in
    # ``services.agent_tools.catalog`` and projected here under the SAME name the
    # internal copilot uses, with the SAME input schema and a ``readOnlyHint``
    # driven by the catalog's ``read_only`` flag. Each tool dispatches to the
    # SAME registered handler the internal agent loop calls (no logic
    # duplication). Adding a capability to the catalog makes it appear on both
    # surfaces; the SC-004 parity audit (``test_mcp_catalog_parity``) locks it.
    for capability in mcp_capabilities():
        mcp.add_tool(
            FunctionTool(
                name=capability.id,
                description=capability.description,
                parameters=capability.input_schema,
                fn=_make_catalog_tool(capability.id),
                annotations=ToolAnnotations(readOnlyHint=capability.read_only),
            )
        )

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
                # A's `/agents` returns a bare JSON list (REST convention);
                # FastMCP requires tool outputs to be a dict (or declare an
                # output_schema), so wrap the list at the MCP-tool boundary.
                return {"agents": response.json()}
            except httpx.HTTPError as exc:
                _log.debug("list_agents: agents router not reachable: %s", exc)
                return {"agents": []}

    @mcp.tool
    async def invoke_agent(
        agent_id: str, prompt: str, api_key: str | None = None
    ) -> dict[str, Any]:
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

    # ---------- Workflow tools (Teammate W's v0.5.0 surface) ----------

    @mcp.tool
    async def run_workflow(spec_json: str) -> dict[str, Any]:
        """Run a workflow spec to completion and return the unary result.

        ``spec_json`` is a JSON-encoded :class:`WorkflowSpec` (the same shape
        ``POST /workflow/run`` accepts inside its ``WorkflowRunRequest`` body).
        MCP tools are unary so this proxy calls :func:`workflow_engine.run_workflow`
        directly rather than consuming the SSE stream the HTTP route emits —
        the per-event observability is intentionally only on the SSE path.

        Returns ``{ok: bool, result: WorkflowRunResult-dict}`` to satisfy the
        FastMCP dict-output requirement (the v0.4.0 Gotcha — bare scalars and
        bare lists are rejected at the tool boundary).
        """
        # Local imports to avoid pulling workflow models into module-load when
        # the MCP server is built; the workflow router already loaded them.
        from models.workflow import WorkflowSpec
        from services import workflow_engine

        try:
            spec = WorkflowSpec.model_validate_json(spec_json)
        except Exception as exc:  # noqa: BLE001 — surface parse errors cleanly
            return {"ok": False, "error": f"invalid workflow spec: {exc}"}

        try:
            result = await workflow_engine.run_workflow(spec)
        except workflow_engine.WorkflowEngineError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "result": result.model_dump(mode="json", by_alias=True)}

    @mcp.tool
    async def list_workflows() -> dict[str, Any]:
        """List every saved workflow.

        Maps to ``GET /workflow/saved``. The router returns a dict
        ``{workflows: [...]}`` already, but this tool keeps that wrap rule
        explicit at the MCP boundary per the v0.4.0 Gotcha (FastMCP rejects
        bare-list outputs; always return a dict).
        """
        async with _internal_client() as client:
            try:
                response = await client.get("/workflow/saved")
                if response.status_code == 404:
                    return {"workflows": []}
                response.raise_for_status()
                body = response.json()
                # Router already returns {workflows: [...]}; normalise to that
                # shape if a future revision flattens to a bare list.
                if isinstance(body, list):
                    return {"workflows": body}
                if isinstance(body, dict) and "workflows" in body:
                    return body
                return {"workflows": []}
            except httpx.HTTPError as exc:
                _log.debug("list_workflows: workflow router not reachable: %s", exc)
                return {"workflows": []}

    # ---------- Delegate-run tools (P3 durable-runs surface) ----------

    @mcp.tool
    async def list_runs() -> dict[str, Any]:
        """List Delegate runs (status + cost-so-far). Maps to GET /runs.

        Hand-written + MCP-only (it is a runtime/framework surface, not a
        catalog data capability), mirroring ``list_workspaces``. The router
        already returns ``{runs: [...]}``; this keeps the dict-wrap rule explicit
        at the MCP boundary (FastMCP rejects bare-list outputs — the v0.4.0
        Gotcha).
        """
        async with _internal_client() as client:
            try:
                response = await client.get("/runs")
                if response.status_code == 404:
                    return {"runs": []}
                response.raise_for_status()
                body = response.json()
                if isinstance(body, list):
                    return {"runs": body}
                if isinstance(body, dict) and "runs" in body:
                    return body
                return {"runs": []}
            except httpx.HTTPError as exc:
                _log.debug("list_runs: runs router not reachable: %s", exc)
                return {"runs": []}

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
