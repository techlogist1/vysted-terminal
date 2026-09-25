"""Shared cached-fetch-store helper for GET routers.

Serves a Pydantic model from :mod:`services.data_cache` within a TTL; on a
miss or a corrupt cache entry (deserialisation failure) calls ``fetch()`` and
stores the result. Returns ``(response, as_of)`` so a caller that stamps an
``as_of`` field on its response can use the cache row's own write time — a
cache hit then reports the ORIGINAL fetch time, not the read time (R15-DATA-068).

Was three near-identical copies in ``routers/fundamentals.py`` and four in
``routers/earnings.py`` (R15-CODE-DATA-011, R15-CODE-DATA-012); a provider
failure is mapped by the app's one ``ProviderError`` handler, so ``fetch()``
is never wrapped here.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from pydantic import BaseModel

from services import data_cache

logger = logging.getLogger(__name__)


async def cached[M: BaseModel](
    key: str, ttl_seconds: float, model: type[M], fetch: Callable[[], Awaitable[M]]
) -> tuple[M, datetime]:
    """Serve ``key`` from the data cache within ``ttl_seconds``, else fetch and store it."""
    hit = await data_cache.get_with_meta(key, ttl_seconds)
    if hit is not None and isinstance(hit[0], dict):
        try:
            return model.model_validate(hit[0]), datetime.fromtimestamp(hit[1], UTC)
        except Exception:  # noqa: BLE001
            logger.warning("%s: cache deserialise failed for %s; refetching", model.__name__, key)
    response = await fetch()
    fetched_at = await data_cache.set(key, response.model_dump(mode="json"))
    return response, datetime.fromtimestamp(fetched_at, UTC)
