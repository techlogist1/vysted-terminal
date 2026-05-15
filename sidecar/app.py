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
    workspace,
)
from services import mcp_client, mcp_server
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


def create_app() -> FastAPI:
    """Build and return a fully wired sidecar FastAPI application."""
    app = FastAPI(title="Vysted Terminal Sidecar", version="0.4.0", lifespan=_lifespan)

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
