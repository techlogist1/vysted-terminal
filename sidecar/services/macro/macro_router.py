"""Macro provider dispatcher — provider-aware routing + ``data_cache`` seam.

The four macro providers in this package each ship the same three-call
public surface; this module is the single dispatch point the FastAPI
router (and the agent-tool wrapper and the workflow-node wrapper) call
into. Every read funnels through :mod:`services.data_cache` with a
6-hour TTL (per the v0.6.0 plan) so the hot path on repeated reads is
microseconds, not an upstream round-trip.

All upstream SDKs are synchronous; the dispatcher runs each provider
call inside :func:`asyncio.to_thread` so the FastAPI event loop is never
blocked by upstream HTTP I/O.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from models.macro_extended import (
    MacroCatalog,
    MacroProvider,
    MacroSearchResult,
    MacroSeriesExtended,
)
from services import data_cache
from services.errors import ProviderError
from services.macro import (
    ecb_provider,
    fred_provider,
    imf_provider,
    world_bank_provider,
)

_log = logging.getLogger(__name__)

#: Cache TTL for macro reads. 6 hours, per the v0.6.0 plan — World Bank
#: updates annually, ECB MRO weekly, IMF GDP quarterly, FRED varies but
#: most series are daily-or-slower. 6h satisfies all four.
DEFAULT_CACHE_TTL_SECONDS = 6 * 60 * 60

# Per-provider dispatch table. Each entry is a (get_series, search, catalog)
# triple of synchronous callables — the dispatcher wraps each in
# ``asyncio.to_thread`` at the call site.
_PROVIDERS: dict[str, Any] = {
    "fred": fred_provider,
    "ecb": ecb_provider,
    "imf": imf_provider,
    "world-bank": world_bank_provider,
}


def _provider(provider: str | MacroProvider) -> Any:
    """Return the module for a provider id, or raise :class:`ProviderError`."""
    key = str(provider).lower()
    mod = _PROVIDERS.get(key)
    if mod is None:
        raise ProviderError(f"Unknown macro provider {provider!r}; supported: {sorted(_PROVIDERS)}")
    return mod


async def get_series(
    series_id: str,
    provider: str | MacroProvider,
    *,
    ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS,
) -> MacroSeriesExtended:
    """Fetch a macro time series via the dispatched provider, cache-aware.

    Cache key: ``macro:<provider>:<series_id>``. Cache value is the
    JSON-serialised :class:`MacroSeriesExtended` payload; on hit we
    re-construct the model so callers always see the strict-typed contract.
    """
    if not series_id:
        raise ProviderError("series_id is required")
    mod = _provider(provider)
    key = f"macro:{mod.PROVIDER}:{series_id}"

    cached = await data_cache.get(key, ttl_seconds)
    if cached is not None:
        try:
            return MacroSeriesExtended.model_validate(cached)
        except Exception as exc:  # noqa: BLE001 — discard a corrupt cached row
            _log.warning("macro: discarding malformed cached row for %s: %s", key, exc)

    result: MacroSeriesExtended = await asyncio.to_thread(mod.get_series, series_id)
    await data_cache.set(key, result.model_dump(mode="json"))
    return result


async def search(
    query: str,
    provider: str | MacroProvider,
    *,
    limit: int = 25,
    ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS,
) -> list[MacroSearchResult]:
    """Search the dispatched provider's catalog, cache-aware."""
    if not query:
        return []
    mod = _provider(provider)
    key = f"macro:{mod.PROVIDER}:search:{query.lower()}:{limit}"

    cached = await data_cache.get(key, ttl_seconds)
    if isinstance(cached, list):
        try:
            return [MacroSearchResult.model_validate(row) for row in cached]
        except Exception as exc:  # noqa: BLE001
            _log.warning("macro: discarding malformed cached search rows for %s: %s", key, exc)

    rows: list[MacroSearchResult] = await asyncio.to_thread(mod.search, query, limit)
    await data_cache.set(key, [r.model_dump(mode="json") for r in rows])
    return rows


async def get_catalog(
    provider: str | MacroProvider,
    *,
    limit: int = 25,
    ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS,
) -> MacroCatalog:
    """Return the dispatched provider's curated catalog, cache-aware."""
    mod = _provider(provider)
    key = f"macro:{mod.PROVIDER}:catalog:{limit}"

    cached = await data_cache.get(key, ttl_seconds)
    if cached is not None:
        try:
            return MacroCatalog.model_validate(cached)
        except Exception as exc:  # noqa: BLE001
            _log.warning("macro: discarding malformed cached catalog for %s: %s", key, exc)

    result: MacroCatalog = await asyncio.to_thread(mod.catalog, limit)
    await data_cache.set(key, result.model_dump(mode="json"))
    return result


__all__ = [
    "DEFAULT_CACHE_TTL_SECONDS",
    "get_catalog",
    "get_series",
    "search",
]
