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

from .base import SearchBackend

#: Known backend ids, in preference order (the local instance first, then the
#: keyless multi-engine rotation, then the bare DuckDuckGo floor it grew out of).
KNOWN_BACKENDS: tuple[str, ...] = ("searxng", "keyless", "ddg")


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
    """Construct the keyless DuckDuckGo floor — UNCONDITIONAL (needs no credential)."""
    try:
        from .ddg import DdgSearchBackend
    except ImportError:
        return None
    return DdgSearchBackend(region=region)


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


__all__ = ["KNOWN_BACKENDS", "resolve"]
