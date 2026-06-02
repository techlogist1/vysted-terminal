"""Search-backend registry — selects the active BYOK/local backend at call time.

The agent runtime asks the registry for "the backend the user has configured"
(``active_id``) and the registry hands back a ready :class:`SearchBackend` —
or ``None`` when the requested backend is missing its credential/URL. ``None``
is the **honest fallback signal**: the caller then prompts the user to add a
key or switch routes (C.1 "never surprise routing/cost"), rather than silently
degrading.

Backend ids:

  * ``"exa"`` — Tier-2 BYOK REST search; needs ``EXA_API_KEY`` (``exa_key``).
  * ``"searxng"`` — Tier-3 local/private metasearch; needs a base ``searxng_url``.
  * ``"ddg"`` — the keyless FLOOR (DuckDuckGo); needs nothing, so it always
    resolves. Not a user-selectable tier — the ``web_search`` handler falls back
    to it last so search is never dark on a fresh, key-less install.

The concrete backends live in :mod:`services.search.exa` /
:mod:`services.search.searxng` and are **lazy-imported** here (guarded) so the
two backends can be built in parallel — a missing or half-built module yields
``None`` instead of an import error at resolve time.
"""

from __future__ import annotations

from collections.abc import Callable

from .base import SearchBackend

#: Known backend ids, in preference order (BYOK first, then local, then the
#: keyless DuckDuckGo floor that always resolves).
KNOWN_BACKENDS: tuple[str, ...] = ("exa", "searxng", "ddg")


def _build_exa(
    *, exa_key: str | None, searxng_url: str | None, region: str | None
) -> SearchBackend | None:
    """Construct the Exa backend if a key is present, else ``None``."""
    if not exa_key:
        return None
    try:
        from .exa import ExaSearchBackend
    except ImportError:
        return None
    return ExaSearchBackend(api_key=exa_key, region=region)


def _build_searxng(
    *, exa_key: str | None, searxng_url: str | None, region: str | None
) -> SearchBackend | None:
    """Construct the SearXNG backend if a base URL is present, else ``None``."""
    if not searxng_url:
        return None
    try:
        from .searxng import SearxngSearchBackend
    except ImportError:
        return None
    return SearxngSearchBackend(base_url=searxng_url, region=region)


def _build_ddg(
    *, exa_key: str | None, searxng_url: str | None, region: str | None
) -> SearchBackend | None:
    """Construct the keyless DuckDuckGo floor — UNCONDITIONAL (needs no credential)."""
    try:
        from .ddg import DdgSearchBackend
    except ImportError:
        return None
    return DdgSearchBackend(region=region)


# Each builder takes the full credential bundle by keyword and returns a backend
# or ``None``; keeping a uniform signature lets resolve() dispatch generically.
_BUILDERS: dict[str, Callable[..., SearchBackend | None]] = {
    "exa": _build_exa,
    "searxng": _build_searxng,
    "ddg": _build_ddg,
}


def resolve(
    active_id: str | None,
    *,
    exa_key: str | None = None,
    searxng_url: str | None = None,
    region: str | None = None,
) -> SearchBackend | None:
    """Return the configured :class:`SearchBackend`, or ``None`` (honest fallback).

    ``None`` is returned when ``active_id`` is unknown/empty, or when the
    requested backend lacks its credential/URL — the caller treats ``None`` as
    "no usable search backend; prompt the user", never as a hard error.
    """
    if not active_id:
        return None
    builder = _BUILDERS.get(active_id.strip().lower())
    if builder is None:
        return None
    return builder(exa_key=exa_key, searxng_url=searxng_url, region=region)


__all__ = ["KNOWN_BACKENDS", "resolve"]
