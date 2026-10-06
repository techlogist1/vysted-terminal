"""R9 Track A — two-tier research config + middleware threading.

Covers the ``tier_a | tier_b`` ContextVar contract in :mod:`config` (the
effective-tier truth incl. the legacy-header migration), the per-stop
research-model map (header parse, defaults, model-agnostic slugs), and the
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
    assert config.normalize_research_search_tier("tier_a") == "tier_a"
    assert config.normalize_research_search_tier("tier_b") == "tier_b"


def test_tier_normalization_is_case_and_space_insensitive() -> None:
    assert config.normalize_research_search_tier("  TIER_B ") == "tier_b"


def test_legacy_r7_ids_fold_into_two_tiers() -> None:
    # The R7/R8 vocabulary migrates: local/keyless-class → tier_a; the hosted
    # key boundary → tier_b. Graceful (logged once), never an error.
    assert config.normalize_research_search_tier("t1_local") == "tier_a"
    assert config.normalize_research_search_tier("t2_searxng") == "tier_a"
    assert config.normalize_research_search_tier("t3_hosted") == "tier_b"


def test_tier_aliases_resolve() -> None:
    assert config.normalize_research_search_tier("t2") == "tier_a"
    assert config.normalize_research_search_tier("searxng") == "tier_a"
    assert config.normalize_research_search_tier("keyless") == "tier_a"
    assert config.normalize_research_search_tier("hosted") == "tier_b"
    assert config.normalize_research_search_tier("openrouter") == "tier_b"


def test_unknown_and_empty_default_to_tier_a() -> None:
    # tier_a is the only tier that can never surprise-bill or require setup, so
    # a malformed header floors there.
    assert config.normalize_research_search_tier("warpdrive") == "tier_a"
    assert config.normalize_research_search_tier("") == "tier_a"
    assert config.normalize_research_search_tier(None) == "tier_a"


def test_no_keyless_tier_in_the_user_facing_enum() -> None:
    # R9 kill: "keyless" is an invisible FALLBACK, not a tier. The known set is
    # exactly the two tiers.
    assert config.KNOWN_RESEARCH_SEARCH_TIERS == frozenset({"tier_a", "tier_b"})


# --- ContextVar round-trips (the deep-research pattern) -----------------------


def test_tier_defaults_to_none_meaning_no_explicit_selection() -> None:
    assert config.get_research_search_tier() is None


def test_tier_set_reset_round_trip() -> None:
    token = config.set_request_research_search_tier("tier_b")
    try:
        assert config.get_research_search_tier() == "tier_b"
    finally:
        config.reset_request_research_search_tier(token)
    assert config.get_research_search_tier() is None


def test_blank_tier_header_stays_unselected() -> None:
    token = config.set_request_research_search_tier("   ")
    try:
        assert config.get_research_search_tier() is None
    finally:
        config.reset_request_research_search_tier(token)


def test_garbage_tier_value_normalizes_to_tier_a_not_unknown() -> None:
    token = config.set_request_research_search_tier("warpdrive")
    try:
        assert config.get_research_search_tier() == "tier_a"
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


# --- get_effective_research_tier — the ONE tier truth --------------------------


def test_effective_tier_defaults_to_tier_a() -> None:
    assert config.get_effective_research_tier() == "tier_a"


def test_effective_tier_explicit_selection_is_authoritative() -> None:
    token = config.set_request_research_search_tier("tier_b")
    try:
        assert config.get_effective_research_tier() == "tier_b"
    finally:
        config.reset_request_research_search_tier(token)


def test_effective_tier_legacy_byok_exa_maps_across_the_key_boundary() -> None:
    # byok-exa + an OpenRouter key on the request → tier_b; without → tier_a.
    tokens = config.set_request_search(tier="byok-exa", searxng_url=None)
    key_token = config.set_request_openrouter_search_key("sk-or-1")
    try:
        assert config.get_effective_research_tier() == "tier_b"
    finally:
        config.reset_request_openrouter_search_key(key_token)
    try:
        assert config.get_effective_research_tier() == "tier_a"
    finally:
        config.reset_request_search(tokens)


def test_effective_tier_legacy_local_searxng_and_native_map_to_tier_a() -> None:
    for legacy in ("local-searxng", "native"):
        tokens = config.set_request_search(tier=legacy, searxng_url=None)
        try:
            assert config.get_effective_research_tier() == "tier_a", legacy
        finally:
            config.reset_request_search(tokens)


def test_effective_tier_explicit_wins_over_legacy() -> None:
    tokens = config.set_request_search(tier="byok-exa", searxng_url=None)
    key_token = config.set_request_openrouter_search_key("sk-or-1")
    r9_token = config.set_request_research_search_tier("tier_a")
    try:
        assert config.get_effective_research_tier() == "tier_a"
    finally:
        config.reset_request_research_search_tier(r9_token)
        config.reset_request_openrouter_search_key(key_token)
        config.reset_request_search(tokens)


# --- The per-stop research-model map -------------------------------------------


def test_default_models_are_the_verified_pins() -> None:
    assert config.DEFAULT_RESEARCH_MODELS == {
        "normal": "perplexity/sonar",
        "deep": "perplexity/sonar-reasoning-pro",
        "ultra": "perplexity/sonar-deep-research",
    }


def test_parse_research_models_full_header() -> None:
    parsed = config.parse_research_models(
        "normal=perplexity/sonar-pro,deep=openai/o4-mini-deep-research,ultra=x-ai/grok-4.3"
    )
    assert parsed == {
        "normal": "perplexity/sonar-pro",
        "deep": "openai/o4-mini-deep-research",
        "ultra": "x-ai/grok-4.3",
    }


def test_parse_research_models_partial_floors_missing_stops_to_defaults() -> None:
    parsed = config.parse_research_models("deep=openai/o3-deep-research")
    assert parsed["deep"] == "openai/o3-deep-research"
    assert parsed["normal"] == config.DEFAULT_RESEARCH_MODELS["normal"]
    assert parsed["ultra"] == config.DEFAULT_RESEARCH_MODELS["ultra"]


def test_parse_research_models_drops_garbage_defensively() -> None:
    parsed = config.parse_research_models(
        "normal=has spaces,bogus_stop=x/y,deep==,ultra=perplexity/sonar,not-a-pair"
    )
    # Garbled entries floor to defaults; the one valid pair lands.
    assert parsed["normal"] == config.DEFAULT_RESEARCH_MODELS["normal"]
    assert parsed["deep"] == config.DEFAULT_RESEARCH_MODELS["deep"]
    assert parsed["ultra"] == "perplexity/sonar"


def test_parse_research_models_none_and_blank_yield_defaults() -> None:
    assert config.parse_research_models(None) == config.DEFAULT_RESEARCH_MODELS
    assert config.parse_research_models("") == config.DEFAULT_RESEARCH_MODELS


def test_get_research_model_for_reads_the_request_map() -> None:
    token = config.set_request_research_models("ultra=openai/o3-deep-research")
    try:
        assert config.get_research_model_for("ultra") == "openai/o3-deep-research"
        assert config.get_research_model_for("deep") == config.DEFAULT_RESEARCH_MODELS["deep"]
    finally:
        config.reset_request_research_models(token)
    assert config.get_research_model_for("ultra") == config.DEFAULT_RESEARCH_MODELS["ultra"]


def test_get_research_model_for_unknown_stop_floors_to_normal() -> None:
    # Never a silent escalation — an unknown stop gets the cheapest slot.
    assert config.get_research_model_for("warp") == config.DEFAULT_RESEARCH_MODELS["normal"]
    assert config.get_research_model_for("") == config.DEFAULT_RESEARCH_MODELS["normal"]


# --- Middleware threading ------------------------------------------------------


def _scope_with(headers: list[tuple[bytes, bytes]]) -> dict:
    return {"type": "http", "headers": headers}


def test_middleware_threads_r9_headers_into_contextvars() -> None:
    from app import _RegionMiddleware

    seen: dict[str, object] = {}

    async def inner(scope, receive, send):  # noqa: ANN001
        seen["tier"] = config.get_research_search_tier()
        seen["effective"] = config.get_effective_research_tier()
        seen["key"] = config.get_openrouter_search_key()
        seen["ultra_model"] = config.get_research_model_for("ultra")

    middleware = _RegionMiddleware(inner)
    scope = _scope_with(
        [
            (b"x-vysted-research-tier", b"tier_b"),
            (b"x-vysted-openrouter-key", b"sk-or-abc"),
            (b"x-vysted-research-models", b"ultra=openai/o3-deep-research"),
        ]
    )
    _run(middleware(scope, None, None))
    assert seen == {
        "tier": "tier_b",
        "effective": "tier_b",
        "key": "sk-or-abc",
        "ultra_model": "openai/o3-deep-research",
    }
    # Reset on the way out — nothing leaks past the request.
    assert config.get_research_search_tier() is None
    assert config.get_openrouter_search_key() is None
    assert config.get_research_model_for("ultra") == config.DEFAULT_RESEARCH_MODELS["ultra"]


def test_middleware_legacy_tier_header_still_threads() -> None:
    from app import _RegionMiddleware

    seen: dict[str, object] = {}

    async def inner(scope, receive, send):  # noqa: ANN001
        seen["effective"] = config.get_effective_research_tier()

    middleware = _RegionMiddleware(inner)
    scope = _scope_with(
        [
            (b"x-vysted-search-tier", b"byok-exa"),
            (b"x-vysted-openrouter-key", b"sk-or-abc"),
        ]
    )
    _run(middleware(scope, None, None))
    assert seen["effective"] == "tier_b"


def test_middleware_without_headers_leaves_no_selection() -> None:
    from app import _RegionMiddleware

    seen: dict[str, object] = {"tier": "sentinel"}

    async def inner(scope, receive, send):  # noqa: ANN001
        seen["tier"] = config.get_research_search_tier()
        seen["effective"] = config.get_effective_research_tier()
        seen["key"] = config.get_openrouter_search_key()

    middleware = _RegionMiddleware(inner)
    _run(middleware(_scope_with([]), None, None))
    assert seen["tier"] is None
    assert seen["effective"] == "tier_a"
    assert seen["key"] is None


def test_middleware_resets_even_when_endpoint_raises() -> None:
    from app import _RegionMiddleware

    async def inner(scope, receive, send):  # noqa: ANN001
        raise RuntimeError("endpoint blew up")

    middleware = _RegionMiddleware(inner)
    scope = _scope_with(
        [
            (b"x-vysted-openrouter-key", b"sk-or-secret"),
            (b"x-vysted-research-models", b"deep=x/y"),
        ]
    )
    try:
        _run(middleware(scope, None, None))
    except RuntimeError:
        pass
    assert config.get_openrouter_search_key() is None
    assert config.get_research_model_for("deep") == config.DEFAULT_RESEARCH_MODELS["deep"]


def test_dead_exa_and_engine_headers_are_no_longer_read() -> None:
    # The R7 Exa-direct lane and hosted-engine knob are DEAD: their headers must
    # not surface anywhere (no ContextVar reader exists anymore).
    assert not hasattr(config, "get_exa_key")
    assert not hasattr(config, "get_hosted_search_engine")
