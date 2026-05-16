"""FastAPI application factory for the Vysted Terminal sidecar.

``create_app`` wires every router, registers the provider-error handler, and
mounts the FastMCP Streamable-HTTP transport at ``/mcp`` so external MCP
clients (Claude Desktop via ``mcp-remote``, Claude Code natively) can consume
Vysted's data + agent surface. The module-level ``app`` is what ``main.py``
runs under uvicorn and what tests build a ``TestClient`` against.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers import (
    agents,
    backtest,
    brokers,
    crypto,
    custom_agents,
    fundamentals,
    health,
    history,
    indicators,
    llm,
    macro,
    mcp,
    news,
    plugins,
    portfolio,
    quotes,
    safety,
    screener,
    workflow,
    workspace,
)
from services import agent_tools, backtest_strategies, mcp_client, mcp_server
from services.brokers import registry as brokers_registry
from services.errors import ProviderError

_ROUTERS = (
    health,
    quotes,
    history,
    crypto,
    fundamentals,
    macro,
    indicators,
    portfolio,
    news,
    workspace,
    plugins,
    llm,
    agents,
    custom_agents,
    mcp,
    safety,
    workflow,
    backtest,
    brokers,
    screener,
)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan — runs the FastMCP transport lifespan + cleanup.

    FastMCP's Starlette app has its own ``lifespan`` context that wires the
    Streamable-HTTP transport's session manager; we run that as part of the
    sidecar's lifespan so the mount is fully active by the time the first
    request lands. On shutdown the MCP-client cache is closed too, so any
    transport to an external server (the openbb-mcp subprocess) is torn down
    cleanly.
    """
    mcp_app = mcp_server.get_streamable_http_app()
    async with mcp_app.lifespan(mcp_app):
        try:
            yield
        finally:
            await mcp_client.reset_clients()


def _register_v0_5_0_runtime_extensions() -> None:
    """Wire backtest strategies + v0.5.0 agent tools into their registries.

    Idempotent — both ``backtest_strategies.register_all`` and
    ``agent_tools.register_v0_5_0_tools`` overwrite by stable id, so a
    second call from ``main.py`` after the lifespan kicks in is a
    no-op. Called from :func:`create_app` so TestClient builds pick the
    registrations up without a separate fixture, and re-called from
    ``main.py`` for parity with the documented v0.5.0 boot path.
    """
    backtest_strategies.register_all()
    agent_tools.register_v0_5_0_tools()


def _register_v0_6_0_runtime_extensions() -> None:
    """Wire Phase 6 agent tools + workflow nodes into their registries.

    Aggregator stubs that no-op until a Phase 6 teammate's submodule
    uncomments its registration line. Lives next to the v0.5.0 helper
    above and is called from :func:`create_app` so TestClient builds
    pick the registrations up.
    """
    from services.workflow_nodes import registry_v0_6_0 as _wf_v0_6_0

    agent_tools.register_v0_6_0_tools()
    _wf_v0_6_0.register_v0_6_0_nodes()


def create_app() -> FastAPI:
    """Build and return a fully wired sidecar FastAPI application."""
    app = FastAPI(title="Vysted Terminal Sidecar", version="0.5.0", lifespan=_lifespan)

    # The frontend WebView fetches the sidecar cross-origin (dev: localhost:3000,
    # prod: tauri://localhost). The sidecar binds to 127.0.0.1 only, so a
    # permissive CORS policy is safe and avoids a tauri-plugin-http dependency.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ProviderError)
    async def _provider_error_handler(_request: Request, exc: ProviderError) -> JSONResponse:
        """Translate any upstream provider failure into a clean 502 response."""
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    for module in _ROUTERS:
        app.include_router(module.router)

    # India broker adapters (Teammate I — Dhan + Angel One + Kite).
    # Bootstrapping at app-build time ensures the TestClient + uvicorn
    # paths converge on the same registry state.
    brokers_registry.bootstrap_default_adapters()

    # v0.5.0 runtime extensions — backtest strategies + agent tools.
    # Registered at app-build time so TestClient + uvicorn paths converge.
    _register_v0_5_0_runtime_extensions()

    # v0.6.0 (Phase 6) runtime extensions — macro + SEC + earnings +
    # analyst + quant + screener agent tools and workflow nodes. The
    # aggregators currently no-op until each Phase 6 teammate's
    # submodule uncomments its registration entry.
    _register_v0_6_0_runtime_extensions()

    # Mount the FastMCP Streamable-HTTP transport at /mcp. External MCP
    # clients reach it via http://127.0.0.1:<port>/mcp/. The plain-JSON
    # ``/mcp/status`` endpoint defined in :mod:`routers.mcp` sits next to
    # it so the plugin-manager UI can probe readiness without speaking
    # JSON-RPC.
    app.mount("/mcp", mcp_server.get_streamable_http_app())
    # Wire the in-process httpx ASGI transport the MCP tools use so they
    # call the data router directly rather than through a TCP loopback.
    mcp_server.bind_app(app)

    return app


app = create_app()
