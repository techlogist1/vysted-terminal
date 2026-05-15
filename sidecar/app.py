"""FastAPI application factory for the Vysted Terminal sidecar.

``create_app`` wires every router and registers the provider-error handler. The
module-level ``app`` is what ``main.py`` runs under uvicorn and what tests build
a ``TestClient`` against.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers import (
    crypto,
    fundamentals,
    health,
    history,
    indicators,
    macro,
    news,
    portfolio,
    quotes,
    workspace,
)
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
)


def create_app() -> FastAPI:
    """Build and return a fully wired sidecar FastAPI application."""
    app = FastAPI(title="Vysted Terminal Sidecar", version="0.2.1")

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
    return app


app = create_app()
