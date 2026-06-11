"""FastAPI application factory for the Vysted Terminal sidecar.

``create_app`` wires every router, registers the provider-error handler, and
mounts the FastMCP Streamable-HTTP transport at ``/mcp`` so external MCP
clients (Claude Desktop via ``mcp-remote``, Claude Code natively) can consume
Vysted's data + agent surface. The module-level ``app`` is what ``main.py``
runs under uvicorn and what tests build a ``TestClient`` against.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import config
from routers import (
    agents,
    backtest,
    brokers,
    crypto,
    custom_agents,
    disclosures,
    earnings,
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
    quant,
    quotes,
    resolve,
    runs,
    safety,
    screener,
    search_status,
    search_tiers,
    sec_filings,
    system,
    tradesa_v2,
    workflow,
    workspace,
)
from services import (
    agent_tools,
    backtest_strategies,
    mcp_client,
    mcp_server,
    run_manager,
    searxng_manager,
)
from services import screener as screener_service
from services.errors import ProviderError

_ROUTERS = (
    health,
    quotes,
    history,
    crypto,
    disclosures,
    fundamentals,
    macro,
    indicators,
    portfolio,
    news,
    resolve,
    workspace,
    plugins,
    llm,
    agents,
    custom_agents,
    runs,
    mcp,
    safety,
    sec_filings,
    workflow,
    backtest,
    brokers,
    quant,
    earnings,
    screener,
    search_status,
    search_tiers,
    system,
    tradesa_v2,
)

_log = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan — runs the FastMCP transport lifespan + cleanup.

    FastMCP's Starlette app has its own ``lifespan`` context that wires the
    Streamable-HTTP transport's session manager; we run that as part of the
    sidecar's lifespan so the mount is fully active by the time the first
    request lands. On shutdown the MCP-client cache is closed too, so any
    transport to an external server (the openbb-mcp subprocess) is torn down
    cleanly.

    A single shared ``httpx.AsyncClient`` lives on ``app.state.httpx_client``.
    It is created in :func:`create_app` (so ``TestClient`` builds that never run
    the lifespan still have a usable client) and closed here on shutdown. The
    news provider (and any future outbound-HTTP route) reuses it so connection
    pooling eliminates the cold-first-fetch 502 cascade documented in #38;
    per-request clients re-paid the TLS handshake on every fetch.
    """
    mcp_app = mcp_server.get_streamable_http_app()
    async with mcp_app.lifespan(mcp_app):
        # Kick off the screener's warm-universe precompute (R4 / FR-126). It spawns
        # a DETACHED background task and returns immediately, so it never blocks the
        # sidecar boot the Tauri core waits on; the loop pre-warms the S&P 500 batch
        # so warm screens are sub-second. Cancelled + awaited in the finally below.
        screener_service.start_warm_precompute()
        try:
            yield
        finally:
            # Cancel + await the warm-precompute task and close the batch provider's
            # shared httpx client FIRST so neither a detached task nor an open socket
            # outlives the event loop.
            try:
                await screener_service.stop_warm_precompute()
            except Exception as exc:  # noqa: BLE001 — shutdown best-effort
                _log.debug("screener.stop_warm_precompute raised on shutdown: %s", exc)
            # Cancel any in-flight Delegate runs FIRST so their detached tasks
            # do not outlive the event loop (FR-027 durability is process-bound;
            # a clean shutdown tears the tasks down rather than orphaning them).
            try:
                await run_manager.shutdown()
            except Exception as exc:  # noqa: BLE001 — shutdown best-effort
                _log.debug("run_manager.shutdown raised on shutdown: %s", exc)
            # Cancel an in-flight managed-SearXNG setup task (docker pull can
            # run for minutes; it must not outlive the event loop).
            try:
                await searxng_manager.shutdown()
            except Exception as exc:  # noqa: BLE001 — shutdown best-effort
                _log.debug("searxng_manager.shutdown raised on shutdown: %s", exc)
            # Guard the client close so an aclose() error (timeout / SSL /
            # cleanup failure on shutdown) cannot prevent the MCP-client cache
            # reset that follows — otherwise external MCP transports leak open
            # on shutdown (Phase 9.5). Both steps run unconditionally.
            client: httpx.AsyncClient | None = getattr(app.state, "httpx_client", None)
            if client is not None:
                try:
                    await client.aclose()
                except Exception as exc:  # noqa: BLE001 — shutdown best-effort
                    _log.debug("httpx_client.aclose raised on shutdown: %s", exc)
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


def _register_v0_6_5_runtime_extensions() -> None:
    """Wire v0.6.5 (Tradesa V2 wrapper) extensions.

    v0.6.5 ships READ-ONLY by operator decision — no agent tools are
    registered for the wrapper. The aggregator helper is invoked anyway
    to maintain per-release-stamp parity with v0.5.0 / v0.6.0; when
    write capability lands in v0.6.6+ the registration list inside
    ``services/agent_tools/registry_v0_6_5.py`` becomes non-empty.
    """
    from services.agent_tools import registry_v0_6_5 as _at_v0_6_5

    _at_v0_6_5.register_v0_6_5_tools()


class _RegionMiddleware:
    """Pure-ASGI middleware threading per-request locale + search config into ContextVars.

    The frontend sends the active region as ``X-Vysted-Region`` and the web-search
    preference as ``X-Vysted-Research-Tier`` / ``X-Vysted-Searxng-Url`` on every
    sidecar request (the same per-request transport BYOK secrets use). This
    middleware reads them into per-request ContextVars (:func:`config.get_region`,
    :func:`config.get_effective_research_tier`, …) so the provider registry,
    news/screener/macro, and the agent search tools shape data + ground web
    context for the user's locale + chosen tier (FR-060/080). Pure ASGI (not
    ``BaseHTTPMiddleware``) so the ContextVar set runs in the same task as the
    endpoint and is reliably visible to it. Absent the headers, region defaults
    to ``US`` and the tier to ``tier_a`` — never a surprise paid route.

    R9 (Track A) two-tier contract on this transport:

    - ``X-Vysted-Research-Tier`` — ``tier_a`` (Unlimited Local, the default) or
      ``tier_b`` (hosted research model); legacy R7/R8 spellings normalize in
      :func:`config.normalize_research_search_tier`.
    - ``X-Vysted-Openrouter-Key`` — the tier_b BYOK secret: process-memory for
      the request only, reset on exit, never logged or persisted.
    - ``X-Vysted-Research-Models`` — the tier_b per-stop model map
      (``normal=…,deep=…,ultra=…``), parsed defensively in
      :func:`config.parse_research_models`.
    - ``X-Vysted-Search-Tier`` — the LEGACY pre-R8 header, still parsed as
      MIGRATION INPUT only (``byok-exa`` → tier_b-with-key else tier_a; the Exa
      key header is dead and no longer read).
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        region: str | None = None
        tier: str | None = None
        searxng_url: str | None = None
        research_tier: str | None = None
        openrouter_key: str | None = None
        research_models: str | None = None
        for key, value in scope.get("headers", []):
            if key == b"x-vysted-region":
                region = value.decode("latin-1")
            elif key == b"x-vysted-search-tier":
                tier = value.decode("latin-1")
            elif key == b"x-vysted-searxng-url":
                searxng_url = value.decode("latin-1")
            elif key == b"x-vysted-research-tier":
                research_tier = value.decode("latin-1")
            elif key == b"x-vysted-openrouter-key":
                openrouter_key = value.decode("latin-1")
            elif key == b"x-vysted-research-models":
                research_models = value.decode("latin-1")
        region_token = config.set_request_region(region)
        search_tokens = config.set_request_search(tier=tier, searxng_url=searxng_url)
        research_tier_token = config.set_request_research_search_tier(research_tier)
        openrouter_token = config.set_request_openrouter_search_key(openrouter_key)
        models_token = config.set_request_research_models(research_models)
        try:
            await self.app(scope, receive, send)
        finally:
            config.reset_request_research_models(models_token)
            config.reset_request_openrouter_search_key(openrouter_token)
            config.reset_request_research_search_tier(research_tier_token)
            config.reset_request_search(search_tokens)
            config.reset_request_region(region_token)


def create_app() -> FastAPI:
    """Build and return a fully wired sidecar FastAPI application."""
    app = FastAPI(title="Vysted Terminal Sidecar", version="0.8.0", lifespan=_lifespan)

    # Shared pooled outbound-HTTP client for routes that fetch external sources
    # (currently the news provider). Created at build time so TestClient builds
    # that skip the lifespan still resolve ``request.app.state.httpx_client``;
    # the lifespan closes it on shutdown. Connection reuse eliminates the
    # cold-first-fetch 502 cascade (#38).
    app.state.httpx_client = httpx.AsyncClient(follow_redirects=True)

    # The frontend WebView fetches the sidecar cross-origin (dev: localhost:3000,
    # prod: tauri://localhost). The sidecar binds to 127.0.0.1 only, so a
    # permissive CORS policy is safe and avoids a tauri-plugin-http dependency.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Region threading (FR-060): read the ``X-Vysted-Region`` header into the
    # per-request ContextVar so every handler shapes data for the user's locale.
    app.add_middleware(_RegionMiddleware)

    @app.exception_handler(ProviderError)
    async def _provider_error_handler(_request: Request, exc: ProviderError) -> JSONResponse:
        """Translate any upstream provider failure into a clean 502 response."""
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    for module in _ROUTERS:
        app.include_router(module.router)

    # FR-051: no broker is registered at app-build / boot time. Adapters
    # register lazily via ``brokers_registry.ensure_registered(...)`` when a
    # marketplace plugin connects (``POST /brokers/{id}/connect``), so a fresh
    # boot has an empty broker registry.

    # v0.5.0 runtime extensions — backtest strategies + agent tools.
    # Registered at app-build time so TestClient + uvicorn paths converge.
    _register_v0_5_0_runtime_extensions()

    # v0.6.0 (Phase 6) runtime extensions — macro + SEC + earnings +
    # analyst + quant + screener agent tools and workflow nodes. The
    # aggregators currently no-op until each Phase 6 teammate's
    # submodule uncomments its registration entry.
    _register_v0_6_0_runtime_extensions()

    # v0.6.5 (Tradesa V2 wrapper) runtime extensions — read-only release,
    # no agent tools registered. Aggregator slot reserved for v0.6.6+
    # when write capability is added per the operator-brief progression.
    _register_v0_6_5_runtime_extensions()

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
