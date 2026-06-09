"""Pass B (B3) agent tool — ``web_search`` (the BYOK / local search path).

Grounds an answer in current web context (FR-080/082/083/084). This handler
serves the **BYOK** (Exa) and **local** (SearXNG) tiers: it resolves the active
backend from the per-request search config (set by the region/search middleware
from the user's headers — tier + Exa key + SearXNG URL, all process-memory-only)
and returns normalized results + citations.

The **native** tier (the model's own server-side search) does NOT come through
here — the agent runtime injects the provider's native search instead and this
tool is withheld from the allow-list for native-capable runs. When no backend is
configured the handler returns an honest, human "unavailable" naming exactly what
would unlock it (FR-082) — it never fabricates a source.

R7 (Track R, Component 3): an EXPLICIT per-request R7 tier selection
(``t1_local`` / ``t2_searxng`` / ``t3_hosted`` via
:func:`config.get_research_search_tier`) is authoritative and routes ahead of
the legacy tier mapping: t1 → the keyless rotation floor, t2 → the (managed)
SearXNG instance, t3 → OpenRouter's hosted web-search server tool (BYOK key,
per-search cost estimate passed through under ``metadata``). An explicit tier
that cannot be served fails HONESTLY with the unlock named — never a silent
re-route (C.1). No selection → the legacy routing below, which already floors
to the keyless t1 tier.
"""

from __future__ import annotations

from typing import Any

from services.agent_tools import register_tool

# Map the user's chosen tier to a concrete BYOK/local backend id.
_TIER_BACKEND = {"byok-exa": "exa", "local-searxng": "searxng"}

_NO_BACKEND_MESSAGE = (
    "No web-search backend is configured for this query. Add an Exa API key "
    "(BYOK search) or point Vysted at a local SearXNG instance in Settings → Web "
    "search, or switch to a model with native web search. I won't invent sources."
)

_HOSTED_NEEDS_KEY_MESSAGE = (
    "Hosted search (t3) is selected but no OpenRouter API key is configured. "
    "Add one in Settings → Web search, or switch back to the built-in local "
    "tier. I won't invent sources."
)

_SEARXNG_NOT_READY_MESSAGE = (
    "SearXNG search (t2) is selected but no SearXNG instance is reachable. "
    "Finish the one-click setup in Settings → Web search (or start the "
    "vysted-searxng container), or switch back to the built-in local tier. "
    "I won't invent sources."
)


async def _resolve_r7_tier(tier: str, region: str) -> tuple[Any, str | None]:
    """Resolve the backend for an EXPLICIT R7 tier selection (Component 3).

    Returns ``(backend, error_message)``. An explicit tier that cannot be
    served returns ``(None, <honest message naming the unlock>)`` rather than
    silently re-routing — the user chose the tier; swapping it behind their
    back would be surprise routing (C.1). Exception: t1 IS the floor, so it
    keeps the keyless → ddg defensive chain.
    """
    import config
    from services.search import registry

    if tier == config.SEARCH_TIER_T3_HOSTED:
        openrouter_key = config.get_openrouter_search_key()
        if not openrouter_key:
            return None, _HOSTED_NEEDS_KEY_MESSAGE
        backend = registry.resolve(
            "hosted",
            openrouter_key=openrouter_key,
            engine=config.get_hosted_search_engine(),
            region=region,
        )
        return backend, None if backend is not None else _HOSTED_NEEDS_KEY_MESSAGE

    if tier == config.SEARCH_TIER_T2_SEARXNG:
        searxng_url = config.get_searxng_url()
        if not searxng_url:
            # The managed instance (services.searxng_manager) and the pip/docker
            # conventional ports are probed by the same autodetect.
            from services.search.searxng import detect_searxng

            searxng_url = await detect_searxng()
        backend = registry.resolve("searxng", searxng_url=searxng_url, region=region)
        return backend, None if backend is not None else _SEARXNG_NOT_READY_MESSAGE

    # t1_local — the keyless floor, with the bare ddg chain as the defensive
    # fallback (same chain the legacy path floors to).
    backend = registry.resolve("keyless", region=region) or registry.resolve("ddg", region=region)
    return backend, None


async def _web_search(args: dict[str, Any]) -> dict[str, Any]:
    """Run a web search via the configured BYOK/local backend; cite the results.

    Returns ``{"ok": True, "backend": ..., "results": [...], "citations": [...]}``
    or, when nothing is configured / the backend fails, ``{"ok": False,
    "message": <human reason>}`` — never raw JSON, never a fabricated source.
    """
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {"ok": False, "error": "missing or non-string query"}
    num_results = int(args.get("num_results", 6) or 6)
    category = str(args.get("category", "general"))

    import config
    from services.search import registry

    region = config.get_region()
    tier = config.get_search_tier()
    exa_key = config.get_exa_key()
    searxng_url = config.get_searxng_url()

    # R7 tier selection (Component 3): an EXPLICIT t1/t2/t3 selection on the
    # request is authoritative — per-request override mirroring the deep-research
    # backend ContextVar. ``None`` (no selection) keeps the legacy routing below,
    # which already floors to the keyless t1 tier, so the default IS t1.
    r7_tier = config.get_research_search_tier()
    if r7_tier is not None:
        backend, tier_error = await _resolve_r7_tier(r7_tier, region)
        if backend is None:
            return {"ok": False, "query": query, "message": tier_error or _NO_BACKEND_MESSAGE}
        return await _dispatch(backend, query, num_results, category, region)

    # Wire the real SearXNG autodetect: a local-searxng tier with no configured
    # URL probes the conventional local ports (8888 pip → 8080 docker) before
    # giving up — previously this autodetect was dead code, so the Settings copy
    # that promised it was lying.
    if tier == "local-searxng" and not searxng_url:
        from services.search.searxng import detect_searxng

        searxng_url = await detect_searxng()

    backend_id = _TIER_BACKEND.get(tier)
    backend = None
    if backend_id:
        backend = registry.resolve(
            backend_id, exa_key=exa_key, searxng_url=searxng_url, region=region
        )
    else:
        # Native tier but the tool was reachable (a native-incapable provider):
        # use any BYOK/local backend the user has configured.
        backend = registry.resolve("exa", exa_key=exa_key, region=region) or registry.resolve(
            "searxng", searxng_url=searxng_url, region=region
        )

    # The keyless FLOOR: the T1 multi-engine rotation (DDG → Brave → Mojeek with
    # per-engine breakers + pacing) needs no key/URL, so it ALWAYS resolves.
    # Wiring it last means web search is never dark on a fresh install (Track 1 —
    # "works out of the box") while never overriding a configured native/BYOK/
    # SearXNG route the user chose. The bare single-engine ddg floor stays as the
    # defensive fallback should the keyless module ever fail to import.
    if backend is None:
        backend = registry.resolve("keyless", region=region) or registry.resolve(
            "ddg", region=region
        )

    if backend is None:  # pragma: no cover — ddg always resolves; defensive only
        return {"ok": False, "query": query, "message": _NO_BACKEND_MESSAGE}

    return await _dispatch(backend, query, num_results, category, region)


async def _dispatch(
    backend: Any, query: str, num_results: int, category: str, region: str
) -> dict[str, Any]:
    """Run the resolved backend and shape the tool result (shared by both routes).

    A backend that annotates its response (the t3 hosted tier's per-search cost
    estimate) has that annex passed through under ``metadata`` so the caller can
    show honest cost alongside the results (C.1).
    """
    from services.search.base import SearchError

    options = {"numResults": num_results, "category": category, "region": region}
    try:
        response = await backend.search(query, options=options)
    except SearchError as exc:
        # Surface the TYPED reason ("rate_limited" vs "unreachable") so a transient
        # throttle is reported honestly as "rate-limited, retrying" rather than the
        # false global "no backend configured" (FR-082 honesty).
        return {
            "ok": False,
            "query": query,
            "message": str(exc),
            "reason": getattr(exc, "reason", "unreachable"),
        }
    except Exception as exc:  # noqa: BLE001 - any backend failure is a human message
        return {
            "ok": False,
            "query": query,
            "message": f"web search failed: {exc}",
            "reason": "unreachable",
        }

    out: dict[str, Any] = {
        "ok": True,
        "backend": response.backend,
        "query": query,
        "results": [
            {
                "url": r.url,
                "title": r.title,
                "snippet": r.snippet,
                "published_at": r.published_at,
                "source": r.source,
            }
            for r in response.results
        ],
        "citations": [
            {"url": c.url, "title": c.title, "excerpt": c.excerpt} for c in response.citations
        ],
    }
    metadata = getattr(response, "metadata", None)
    if isinstance(metadata, dict) and metadata:
        out["metadata"] = metadata
    return out


def register() -> None:
    """Register the ``web_search`` tool in the package registry."""
    register_tool("web_search", _web_search)


__all__ = ["_web_search", "register"]
