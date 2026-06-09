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
  * ``"keyless"`` — the rebuilt T1 keyless tier (R7): DuckDuckGo → Brave →
    Mojeek rotation with per-engine circuit breakers, pacing, and a quality
    filter (:mod:`services.search.keyless`). Needs nothing, always resolves —
    the ``web_search`` handler's default floor.
  * ``"ddg"`` — the single-engine DuckDuckGo floor the keyless tier grew out
    of. Kept resolvable as the defensive fallback should the keyless module
    ever fail to import.
  * ``"hosted"`` — the R7 t3 BYOK hosted tier: OpenRouter's
    ``openrouter:web_search`` server tool (Firecrawl default engine, Exa
    optional; :mod:`services.search.hosted`). Needs the per-request OpenRouter
    key (``openrouter_key``).

The concrete backends live in :mod:`services.search.exa` /
:mod:`services.search.searxng` and are **lazy-imported** here (guarded) so the
two backends can be built in parallel — a missing or half-built module yields
``None`` instead of an import error at resolve time.
"""

from __future__ import annotations

from collections.abc import Callable

from .base import SearchBackend

#: Known backend ids, in preference order (BYOK first, then local, then the
#: keyless multi-engine tier, then the bare DuckDuckGo floor it grew out of;
#: the hosted t3 tier last — only ever selected explicitly, never a fallback).
KNOWN_BACKENDS: tuple[str, ...] = ("exa", "searxng", "keyless", "ddg", "hosted")


def _build_exa(
    *, exa_key: str | None, searxng_url: str | None, region: str | None, **_: object
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
    *, exa_key: str | None, searxng_url: str | None, region: str | None, **_: object
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
    *, exa_key: str | None, searxng_url: str | None, region: str | None, **_: object
) -> SearchBackend | None:
    """Construct the keyless DuckDuckGo floor — UNCONDITIONAL (needs no credential)."""
    try:
        from .ddg import DdgSearchBackend
    except ImportError:
        return None
    return DdgSearchBackend(region=region)


def _build_keyless(
    *, exa_key: str | None, searxng_url: str | None, region: str | None, **_: object
) -> SearchBackend | None:
    """Construct the T1 keyless rotation tier — UNCONDITIONAL (needs no credential)."""
    try:
        from .keyless import KeylessSearchBackend
    except ImportError:
        return None
    return KeylessSearchBackend(region=region)


def _build_hosted(
    *,
    exa_key: str | None,
    searxng_url: str | None,
    region: str | None,
    openrouter_key: str | None = None,
    engine: str | None = None,
    **_: object,
) -> SearchBackend | None:
    """Construct the t3 hosted (OpenRouter) backend if a key is present, else ``None``.

    ``None`` without a key is the honest fallback signal — the caller prompts
    for the OpenRouter key rather than silently re-routing a tier the user
    explicitly chose (C.1 "never surprise routing/cost").
    """
    if not openrouter_key:
        return None
    try:
        from .hosted import HostedSearchBackend
    except ImportError:
        return None
    return HostedSearchBackend(api_key=openrouter_key, engine=engine, region=region)


# Each builder takes the full credential bundle by keyword and returns a backend
# or ``None``; keeping a uniform signature (extras swallowed via ``**_``) lets
# resolve() dispatch generically as new credential kinds are added.
_BUILDERS: dict[str, Callable[..., SearchBackend | None]] = {
    "exa": _build_exa,
    "searxng": _build_searxng,
    "keyless": _build_keyless,
    "ddg": _build_ddg,
    "hosted": _build_hosted,
}


def resolve(
    active_id: str | None,
    *,
    exa_key: str | None = None,
    searxng_url: str | None = None,
    region: str | None = None,
    openrouter_key: str | None = None,
    engine: str | None = None,
) -> SearchBackend | None:
    """Return the configured :class:`SearchBackend`, or ``None`` (honest fallback).

    ``None`` is returned when ``active_id`` is unknown/empty, or when the
    requested backend lacks its credential/URL — the caller treats ``None`` as
    "no usable search backend; prompt the user", never as a hard error.
    ``openrouter_key``/``engine`` feed the t3 ``hosted`` backend only.
    """
    if not active_id:
        return None
    builder = _BUILDERS.get(active_id.strip().lower())
    if builder is None:
        return None
    return builder(
        exa_key=exa_key,
        searxng_url=searxng_url,
        region=region,
        openrouter_key=openrouter_key,
        engine=engine,
    )


__all__ = ["KNOWN_BACKENDS", "resolve"]
