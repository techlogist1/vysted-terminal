"""Tradesa V2 wrapper router — v0.6.5 read-only Supabase passthrough.

Mounts at ``/tradesa-v2/*``. Every endpoint is a GET — the wrapper plugin
is READ-ONLY in v0.6.5 by operator decision (the bot itself is in an
unstable state right now; Vysted observes without adding bypass surfaces).
Adding any POST/PUT/PATCH/DELETE here is a Tier-4 contract change that
requires operator sign-off (BLUEPRINT §6.5 precedent).

Defense-in-depth layer 2 of 3 (BLUEPRINT §6.5 #2 precedent):

- layer 1 — :mod:`services.tradesa_v2_provider` has no write methods on
  its public surface (grep-time audit in ``test_tradesa_v2_provider``)
- layer 2 — this router exposes only GETs
  (grep-time audit in ``test_tradesa_v2_router``)
- layer 3 — the frontend plugin in ``plugins/tradesa-v2/`` never builds
  a fetch with ``method !== "GET"`` toward ``/tradesa-v2/*``
  (grep-time audit during integration)

The provider instance is per (URL, service-role-key) pair. The router
caches it in-process so the supabase-py httpx pool is reused. Credentials
arrive on every request via ``X-Tradesa-Supabase-Url`` /
``X-Tradesa-Supabase-Service-Key`` headers — the renderer reads them
from the OS keychain via the Tauri ``keychain_get`` command at plugin
init and forwards them on each fetch. They never persist in the sidecar
beyond process memory and never appear in any response body.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Header, HTTPException, Query

from models.tradesa_v2 import (
    TradesaBotSetting,
    TradesaConnectionState,
    TradesaCostRollup,
    TradesaDecision,
    TradesaKillSwitchEvent,
    TradesaMetaAgentRun,
    TradesaSentinelBlock,
    TradesaSettingsDrift,
    TradesaTrade,
)
from services import data_cache
from services.tradesa_v2_provider import TradesaProviderError, TradesaV2Provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tradesa-v2", tags=["tradesa-v2"])


# ---------------------------------------------------------------------------
# Credential flow + provider cache
# ---------------------------------------------------------------------------
#
# The sidecar CANNOT read the OS keychain directly — only the Tauri Rust core
# can (via keychain_set / keychain_get). Established Vysted BYOK pattern
# (Phase 3 LLM /llm/chat, Phase 5 broker connect flows) is: the renderer
# reads the keychain via Tauri invoke at plugin init, then passes the secret
# in the request to the sidecar. For Tradesa V2 we pass it in request
# headers (not body) so the read-only GET model stays clean.
#
# Headers:
#   X-Tradesa-Supabase-Url           — full URL of Tradesa V2's Supabase project
#   X-Tradesa-Supabase-Service-Key   — service-role key (until RLS lands; anon key
#                                       once Tradesa V2 ships v0.1.7.0)
#
# These headers travel over loopback only (127.0.0.1 sidecar bind, never
# network) but we still treat them as sensitive — no logging, no echo back,
# never persisted to disk. The supabase-py Client built from them lives in
# process memory only.

# Cached by a hash of (url, key) so repeated requests with the same creds
# reuse the same supabase-py httpx pool. Dict is process-local; no
# persistence layer.
_PROVIDER_CACHE: dict[tuple[str, str], TradesaV2Provider] = {}

# Stash for the previous bot_settings snapshot. Used by the settings-drift
# endpoint to compute deltas across calls.
_SETTINGS_BASELINE_CACHE_KEY = "tradesa-v2:settings:baseline"


def _resolve_provider(
    supabase_url: str | None,
    service_key: str | None,
) -> TradesaV2Provider:
    """Build or fetch the cached provider for these credentials.

    Raises ``HTTPException(401)`` with a typed body when either header is
    missing — that's the "unauthenticated" path the plugin handles via the
    first-launch settings dialog.
    """
    if not supabase_url or not service_key:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "unauthenticated",
                "message": (
                    "Tradesa V2 credentials missing. Open Plugin Manager → "
                    "Tradesa V2 → Settings to configure your Supabase URL "
                    "and service-role key."
                ),
            },
        )
    key = (supabase_url, service_key)
    cached = _PROVIDER_CACHE.get(key)
    if cached is not None:
        return cached
    provider = TradesaV2Provider(supabase_url, service_key)
    _PROVIDER_CACHE[key] = provider
    return provider


# Typed header dependencies. FastAPI converts ``-`` to ``_`` and downcases
# the header name automatically; the alias keeps the canonical Vysted form
# in the OpenAPI schema.
SupabaseUrlHeader = Annotated[
    str | None,
    Header(alias="X-Tradesa-Supabase-Url", description="Tradesa V2 Supabase project URL."),
]
SupabaseKeyHeader = Annotated[
    str | None,
    Header(
        alias="X-Tradesa-Supabase-Service-Key",
        description="Tradesa V2 Supabase service-role key.",
    ),
]


def _reset_for_tests() -> None:
    """Clear the per-provider cache. Test-only helper."""
    _PROVIDER_CACHE.clear()


# ---------------------------------------------------------------------------
# Status / probe
# ---------------------------------------------------------------------------


@router.get("/status", response_model=TradesaConnectionState)
async def get_status(
    supabase_url: SupabaseUrlHeader = None,
    service_key: SupabaseKeyHeader = None,
) -> TradesaConnectionState:
    """Probe Tradesa V2's Supabase reachability + heartbeat freshness.

    Returns a 200 ``TradesaConnectionState`` regardless of bot health —
    the plugin uses this endpoint to render its graceful-degradation UX
    states (healthy / connecting / unauthenticated / bot-offline /
    supabase-error / partial). Missing credentials map to the
    "unauthenticated" status with 200 (so the plugin doesn't surface a
    401 to the user — it renders the settings dialog instead).
    """
    if not supabase_url or not service_key:
        return TradesaConnectionState(
            status="unauthenticated",
            message=(
                "No Tradesa V2 credentials configured. Open Plugin Manager → Tradesa V2 → Settings."
            ),
            checked_at=int(datetime.now(UTC).timestamp() * 1000),
        )
    provider = _resolve_provider(supabase_url, service_key)
    return await provider.probe_connection()


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------


@router.get("/positions", response_model=list[TradesaTrade])
async def get_positions(
    supabase_url: SupabaseUrlHeader = None,
    service_key: SupabaseKeyHeader = None,
    limit: int = Query(50, ge=1, le=200),
) -> list[TradesaTrade]:
    """Return Tradesa V2's open positions (``trades.status='open'``)."""
    provider = _resolve_provider(supabase_url, service_key)
    try:
        return await provider.list_open_trades(limit=limit)
    except TradesaProviderError as exc:
        raise _http_from_provider_error(exc) from exc


@router.get("/trade-history", response_model=list[TradesaTrade])
async def get_trade_history(
    supabase_url: SupabaseUrlHeader = None,
    service_key: SupabaseKeyHeader = None,
    limit: int = Query(100, ge=1, le=500),
) -> list[TradesaTrade]:
    """Return Tradesa V2's closed trades, newest first."""
    provider = _resolve_provider(supabase_url, service_key)
    try:
        return await provider.list_closed_trades(limit=limit)
    except TradesaProviderError as exc:
        raise _http_from_provider_error(exc) from exc


# ---------------------------------------------------------------------------
# Decisions + LLM cost ledger
# ---------------------------------------------------------------------------


@router.get("/decisions", response_model=list[TradesaDecision])
async def get_decisions(
    supabase_url: SupabaseUrlHeader = None,
    service_key: SupabaseKeyHeader = None,
    limit: int = Query(100, ge=1, le=500),
) -> list[TradesaDecision]:
    """Return Tradesa V2's brain decisions (DirectorDecision rows)."""
    provider = _resolve_provider(supabase_url, service_key)
    try:
        return await provider.list_decisions(limit=limit)
    except TradesaProviderError as exc:
        raise _http_from_provider_error(exc) from exc


@router.get("/meta-agent-runs", response_model=list[TradesaMetaAgentRun])
async def get_meta_agent_runs(
    supabase_url: SupabaseUrlHeader = None,
    service_key: SupabaseKeyHeader = None,
    limit: int = Query(100, ge=1, le=500),
    kind: str | None = Query(None, description="Optional MetaAgentKind filter."),
) -> list[TradesaMetaAgentRun]:
    """Return Tradesa V2's meta-agent run ledger (LLM call audit + cost)."""
    provider = _resolve_provider(supabase_url, service_key)
    try:
        return await provider.list_meta_agent_runs(limit=limit, kind=kind)
    except TradesaProviderError as exc:
        raise _http_from_provider_error(exc) from exc


@router.get("/cost-today", response_model=TradesaCostRollup)
async def get_cost_today(
    supabase_url: SupabaseUrlHeader = None,
    service_key: SupabaseKeyHeader = None,
) -> TradesaCostRollup:
    """Return today's LLM cost rollup (UTC day)."""
    provider = _resolve_provider(supabase_url, service_key)
    try:
        return await provider.get_cost_today()
    except TradesaProviderError as exc:
        raise _http_from_provider_error(exc) from exc


# ---------------------------------------------------------------------------
# Health + kill-switch (display-only)
# ---------------------------------------------------------------------------


@router.get("/health")
async def get_bot_health(
    supabase_url: SupabaseUrlHeader = None,
    service_key: SupabaseKeyHeader = None,
) -> dict[str, object]:
    """Return the latest ``bot_health`` heartbeat row + recent kill events.

    Combined into one payload so the Health panel renders without a second
    round-trip. The heartbeat row may be null if the bot has never reported
    (panel renders "bot never started" placeholder in that case).
    """
    provider = _resolve_provider(supabase_url, service_key)
    try:
        latest = await provider.get_bot_health_latest()
        events = await provider.list_kill_switch_events(limit=10)
    except TradesaProviderError as exc:
        raise _http_from_provider_error(exc) from exc
    return {
        "latest": latest.model_dump(mode="json") if latest else None,
        "recent_kill_switch_events": [e.model_dump(mode="json") for e in events],
    }


@router.get("/kill-switch-events", response_model=list[TradesaKillSwitchEvent])
async def get_kill_switch_events(
    supabase_url: SupabaseUrlHeader = None,
    service_key: SupabaseKeyHeader = None,
    limit: int = Query(50, ge=1, le=500),
) -> list[TradesaKillSwitchEvent]:
    """Return Tradesa V2's kill-switch event history (display-only).

    Vysted v0.6.5 never fires the bot's kill switch — control lives on
    the bot side (Telegram / VPS CLI). This endpoint is for display.
    """
    provider = _resolve_provider(supabase_url, service_key)
    try:
        return await provider.list_kill_switch_events(limit=limit)
    except TradesaProviderError as exc:
        raise _http_from_provider_error(exc) from exc


# ---------------------------------------------------------------------------
# Sentinel + settings + drift
# ---------------------------------------------------------------------------


@router.get("/sentinel", response_model=list[TradesaSentinelBlock])
async def get_sentinel_blocks(
    supabase_url: SupabaseUrlHeader = None,
    service_key: SupabaseKeyHeader = None,
) -> list[TradesaSentinelBlock]:
    """Return sentinel-gate decline tallies (today + total)."""
    provider = _resolve_provider(supabase_url, service_key)
    try:
        return await provider.list_sentinel_blocks()
    except TradesaProviderError as exc:
        raise _http_from_provider_error(exc) from exc


@router.get("/settings", response_model=list[TradesaBotSetting])
async def get_settings(
    supabase_url: SupabaseUrlHeader = None,
    service_key: SupabaseKeyHeader = None,
) -> list[TradesaBotSetting]:
    """Return Tradesa V2's live ``bot_settings`` snapshot.

    Side effect: stashes this snapshot under the data-cache baseline key
    so the next ``GET /settings/drift`` call can diff against it.
    """
    provider = _resolve_provider(supabase_url, service_key)
    try:
        settings = await provider.list_bot_settings()
    except TradesaProviderError as exc:
        raise _http_from_provider_error(exc) from exc
    await data_cache.set(
        _SETTINGS_BASELINE_CACHE_KEY,
        [s.model_dump(mode="json") for s in settings],
    )
    return settings


@router.get("/settings/drift", response_model=list[TradesaSettingsDrift])
async def get_settings_drift(
    supabase_url: SupabaseUrlHeader = None,
    service_key: SupabaseKeyHeader = None,
) -> list[TradesaSettingsDrift]:
    """Return drift between the previous baseline snapshot and current state.

    Empty list when no baseline is stashed yet — the first call to
    ``GET /settings`` seeds the baseline.
    """
    provider = _resolve_provider(supabase_url, service_key)
    # No TTL = always read whatever's stored. The baseline lifecycle is
    # explicit (set on /settings call, queried here), not freshness-bounded.
    raw_baseline = await data_cache.get(_SETTINGS_BASELINE_CACHE_KEY, ttl_seconds=86400 * 365)
    if raw_baseline is None:
        return []
    try:
        previous = [TradesaBotSetting.model_validate(r) for r in raw_baseline]
        current = await provider.list_bot_settings()
    except TradesaProviderError as exc:
        raise _http_from_provider_error(exc) from exc
    return provider.compute_settings_drift(previous, current)


# ---------------------------------------------------------------------------
# Meta-agents (tuning / discovery / reflection)
# ---------------------------------------------------------------------------


MetaAgentSurface = Literal["tuning", "discovery", "reflection"]


@router.get("/meta-agents/{kind}")
async def get_meta_agent_output(
    kind: MetaAgentSurface,
    supabase_url: SupabaseUrlHeader = None,
    service_key: SupabaseKeyHeader = None,
    limit: int = Query(50, ge=1, le=500),
) -> dict[str, list[object]]:
    """Return one of the three meta-agent output streams.

    Returned shape: ``{"items": [...]}`` so the frontend doesn't have to
    branch on response shape — the same panel renders all three with a
    tab switcher.
    """
    provider = _resolve_provider(supabase_url, service_key)
    try:
        if kind == "tuning":
            rows: list[object] = [
                p.model_dump(mode="json") for p in await provider.list_tuning_proposals(limit=limit)
            ]
        elif kind == "discovery":
            rows = [
                h.model_dump(mode="json")
                for h in await provider.list_discovery_hypotheses(limit=limit)
            ]
        else:  # reflection
            rows = [
                n.model_dump(mode="json") for n in await provider.list_reflection_notes(limit=limit)
            ]
    except TradesaProviderError as exc:
        raise _http_from_provider_error(exc) from exc
    return {"items": rows}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _http_from_provider_error(exc: TradesaProviderError) -> HTTPException:
    """Map ``TradesaProviderError`` to the right HTTPException + typed body.

    All Supabase upstream failures map to 502 with the ``status`` carried
    in the detail so the frontend renders the right graceful-degradation
    UX. The status field stays a stable string (matches
    TradesaConnectionStatus) so the frontend can switch on it cleanly.
    """
    return HTTPException(
        status_code=502,
        detail={
            "status": exc.status,
            "message": exc.message,
        },
    )


# ---------------------------------------------------------------------------
# Audit invariant — every route is a GET
# ---------------------------------------------------------------------------

_NON_GET_METHODS: tuple[str, ...] = ("POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")
"""HTTP methods the v0.6.5 router must NEVER expose.

The audit test in ``tests/test_tradesa_v2_router.py`` walks ``router.routes``
and fails if any route's methods include any of these. Defense-in-depth
layer 2 of 3 (provider has no write methods; router has no non-GET routes;
frontend never fetches with method !== "GET").
"""

__all__ = [
    "router",
    "_NON_GET_METHODS",
    "_reset_for_tests",
]
