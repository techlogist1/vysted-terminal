"""Search-backend registry — selects the active local backend at call time.

The agent runtime asks the registry for "the backend this request resolves to"
(``active_id``) and the registry hands back a ready :class:`SearchBackend` —
or ``None`` when the requested backend is missing its URL. ``None`` is the
**honest fallback signal**: the caller then floors to the keyless rotation
(stamped with the honest ``keyless-fallback`` id by the ``web_search``
handler) rather than fabricating or erring.

Backend ids (R9 two-tier — retrieval is ONE local lane):

  * ``"searxng"`` — the local/private metasearch instance (the managed
    one-click container or a custom URL); needs a base ``searxng_url``.
  * ``"keyless"`` — the keyless tier: DuckDuckGo → Brave → Mojeek rotation
    with per-engine circuit breakers, pacing, and a quality filter
    (:mod:`services.search.keyless`). Needs nothing, always resolves — the
    ``web_search`` handler's invisible fallback (NOT a user-facing tier).
  * ``"ddg"`` — the single-engine DuckDuckGo floor the keyless tier grew out
    of. Kept resolvable as the defensive fallback should the keyless module
    ever fail to import.

The R7/R8 BYOK scraper backends (``exa``, ``hosted``) are DEAD — deleted in R9
(Track A): hosted research now routes to a research MODEL via OpenRouter (see
:mod:`services.agent_tools.deep_research`), not to a paid search scraper.

The concrete backends are **lazy-imported** here (guarded) so a missing or
half-built module yields ``None`` instead of an import error at resolve time.
"""

from __future__ import annotations

from collections.abc import Callable

from .base import SearchBackend, SearchResponse


class _PacedBackend:
    """Paces a bare (non-rotation) backend via the shared per-engine queue.

    The keyless rotation tier already paces each engine turn itself
    (:meth:`services.search.keyless.KeylessSearchBackend._try_engine` acquires
    :func:`~services.search.pacing.get_queue` once per attempt before calling
    the engine). A backend resolved directly by id (e.g. the bare ``"ddg"``
    floor, not routed through keyless) has nothing pacing its outbound hits —
    this wraps exactly ONE ``pacing.get_queue().acquire(engine_id)`` around the
    whole ``search()`` call (never per internal retry/fallback the backend
    makes on its own) so the two lanes share one rate policy
    (R15-CODE-RESEARCH-009).
    """

    def __init__(self, backend: SearchBackend, *, engine_id: str) -> None:
        self._backend = backend
        self._engine_id = engine_id

    async def search(self, query: str, *, options: dict | None = None) -> SearchResponse:
        from .pacing import get_queue

        await get_queue().acquire(self._engine_id)
        return await self._backend.search(query, options=options)


def _build_searxng(
    *, searxng_url: str | None, region: str | None, **_: object
) -> SearchBackend | None:
    """Construct the SearXNG backend if a base URL is present, else ``None``."""
    if not searxng_url:
        return None
    try:
        from .searxng import SearxngSearchBackend
    except ImportError:
        return None
    return SearxngSearchBackend(base_url=searxng_url, region=region)


def _build_ddg(*, searxng_url: str | None, region: str | None, **_: object) -> SearchBackend | None:
    """Construct the keyless DuckDuckGo floor — UNCONDITIONAL (needs no credential).

    Wrapped in :class:`_PacedBackend`: this bare-id lane runs OUTSIDE the
    keyless rotation, so unlike ``DdgSearchBackend`` used via
    :mod:`services.search.keyless` (which the rotation already paces), nothing
    else paces it (R15-CODE-RESEARCH-009).
    """
    try:
        from .ddg import DdgSearchBackend
    except ImportError:
        return None
    return _PacedBackend(DdgSearchBackend(region=region), engine_id="ddg")


def _build_keyless(
    *, searxng_url: str | None, region: str | None, **_: object
) -> SearchBackend | None:
    """Construct the keyless rotation tier — UNCONDITIONAL (needs no credential)."""
    try:
        from .keyless import KeylessSearchBackend
    except ImportError:
        return None
    return KeylessSearchBackend(region=region)


# Each builder takes the credential bundle by keyword and returns a backend or
# ``None``; keeping a uniform signature (extras swallowed via ``**_``) lets
# resolve() dispatch generically as new credential kinds are added.
_BUILDERS: dict[str, Callable[..., SearchBackend | None]] = {
    "searxng": _build_searxng,
    "keyless": _build_keyless,
    "ddg": _build_ddg,
}


def resolve(
    active_id: str | None,
    *,
    searxng_url: str | None = None,
    region: str | None = None,
) -> SearchBackend | None:
    """Return the configured :class:`SearchBackend`, or ``None`` (honest fallback).

    ``None`` is returned when ``active_id`` is unknown/empty, or when the
    requested backend lacks its URL — the caller treats ``None`` as "floor to
    keyless", never as a hard error.
    """
    if not active_id:
        return None
    builder = _BUILDERS.get(active_id.strip().lower())
    if builder is None:
        return None
    return builder(searxng_url=searxng_url, region=region)


__all__ = ["resolve"]
