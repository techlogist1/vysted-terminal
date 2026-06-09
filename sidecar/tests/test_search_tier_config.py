"""R7 Track R (Component 3) — search-tier selection config + middleware threading.

Covers the ``t1_local | t2_searxng | t3_hosted`` tier ContextVar trio in
:mod:`config` (mirroring the deep-research backend pattern) and the
``_RegionMiddleware`` header threading in :mod:`app`. Offline — the middleware
is exercised as a bare ASGI callable around a stub app; no network, no docker.
"""

from __future__ import annotations

import asyncio

import config


def _run(coro):
    return asyncio.run(coro)


# --- normalize_research_search_tier ------------------------------------------


def test_known_tiers_pass_through() -> None:
    assert config.normalize_research_search_tier("t1_local") == "t1_local"
    assert config.normalize_research_search_tier("t2_searxng") == "t2_searxng"
    assert config.normalize_research_search_tier("t3_hosted") == "t3_hosted"


def test_tier_normalization_is_case_and_space_insensitive() -> None:
    assert config.normalize_research_search_tier("  T3_HOSTED ") == "t3_hosted"


def test_tier_aliases_resolve() -> None:
    assert config.normalize_research_search_tier("t2") == "t2_searxng"
    assert config.normalize_research_search_tier("searxng") == "t2_searxng"
    assert config.normalize_research_search_tier("hosted") == "t3_hosted"
    assert config.normalize_research_search_tier("openrouter") == "t3_hosted"
    assert config.normalize_research_search_tier("keyless") == "t1_local"


def test_unknown_and_empty_default_to_t1_floor() -> None:
    # t1 is the only tier that can never surprise-bill or require setup, so a
    # malformed header floors there (defaulting t1, per the R7 brief).
    assert config.normalize_research_search_tier("warpdrive") == "t1_local"
    assert config.normalize_research_search_tier("") == "t1_local"
    assert config.normalize_research_search_tier(None) == "t1_local"


# --- ContextVar round-trips (the deep-research pattern) -----------------------


def test_tier_defaults_to_none_meaning_no_explicit_selection() -> None:
    assert config.get_research_search_tier() is None


def test_tier_set_reset_round_trip() -> None:
    token = config.set_request_research_search_tier("t3_hosted")
    try:
        assert config.get_research_search_tier() == "t3_hosted"
    finally:
        config.reset_request_research_search_tier(token)
    assert config.get_research_search_tier() is None


def test_blank_tier_header_stays_unselected() -> None:
    token = config.set_request_research_search_tier("   ")
    try:
        assert config.get_research_search_tier() is None
    finally:
        config.reset_request_research_search_tier(token)


def test_garbage_tier_value_normalizes_to_t1_not_unknown() -> None:
    # A PRESENT but unknown value is an explicit selection that floors to t1 —
    # downstream readers never see an unknown id.
    token = config.set_request_research_search_tier("warpdrive")
    try:
        assert config.get_research_search_tier() == "t1_local"
    finally:
        config.reset_request_research_search_tier(token)


def test_openrouter_key_set_strips_and_resets() -> None:
    assert config.get_openrouter_search_key() is None
    token = config.set_request_openrouter_search_key("  sk-or-test-123  ")
    try:
        assert config.get_openrouter_search_key() == "sk-or-test-123"
    finally:
        config.reset_request_openrouter_search_key(token)
    assert config.get_openrouter_search_key() is None


def test_blank_openrouter_key_is_none() -> None:
    token = config.set_request_openrouter_search_key("   ")
    try:
        assert config.get_openrouter_search_key() is None
    finally:
        config.reset_request_openrouter_search_key(token)


def test_hosted_engine_lowercases_and_resets() -> None:
    assert config.get_hosted_search_engine() is None
    token = config.set_request_hosted_search_engine(" Firecrawl ")
    try:
        assert config.get_hosted_search_engine() == "firecrawl"
    finally:
        config.reset_request_hosted_search_engine(token)
    assert config.get_hosted_search_engine() is None


# --- Middleware threading ------------------------------------------------------


def _scope_with(headers: list[tuple[bytes, bytes]]) -> dict:
    return {"type": "http", "headers": headers}


def test_middleware_threads_r7_headers_into_contextvars() -> None:
    from app import _RegionMiddleware

    seen: dict[str, object] = {}

    async def inner(scope, receive, send):  # noqa: ANN001
        seen["tier"] = config.get_research_search_tier()
        seen["key"] = config.get_openrouter_search_key()
        seen["engine"] = config.get_hosted_search_engine()

    middleware = _RegionMiddleware(inner)
    scope = _scope_with(
        [
            (b"x-vysted-research-tier", b"t3_hosted"),
            (b"x-vysted-openrouter-key", b"sk-or-abc"),
            (b"x-vysted-search-engine", b"exa"),
        ]
    )
    _run(middleware(scope, None, None))
    assert seen == {"tier": "t3_hosted", "key": "sk-or-abc", "engine": "exa"}
    # Reset on the way out — nothing leaks past the request.
    assert config.get_research_search_tier() is None
    assert config.get_openrouter_search_key() is None
    assert config.get_hosted_search_engine() is None


def test_middleware_without_r7_headers_leaves_no_selection() -> None:
    from app import _RegionMiddleware

    seen: dict[str, object] = {"tier": "sentinel"}

    async def inner(scope, receive, send):  # noqa: ANN001
        seen["tier"] = config.get_research_search_tier()
        seen["key"] = config.get_openrouter_search_key()

    middleware = _RegionMiddleware(inner)
    _run(middleware(_scope_with([]), None, None))
    assert seen["tier"] is None and seen["key"] is None


def test_middleware_resets_even_when_endpoint_raises() -> None:
    from app import _RegionMiddleware

    async def inner(scope, receive, send):  # noqa: ANN001
        raise RuntimeError("endpoint blew up")

    middleware = _RegionMiddleware(inner)
    scope = _scope_with([(b"x-vysted-openrouter-key", b"sk-or-secret")])
    try:
        _run(middleware(scope, None, None))
    except RuntimeError:
        pass
    assert config.get_openrouter_search_key() is None
