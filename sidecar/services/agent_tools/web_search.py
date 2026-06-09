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
    from services.search.base import SearchError

    region = config.get_region()
    tier = config.get_search_tier()
    exa_key = config.get_exa_key()
    searxng_url = config.get_searxng_url()

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

    return {
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


def register() -> None:
    """Register the ``web_search`` tool in the package registry."""
    register_tool("web_search", _web_search)


__all__ = ["_web_search", "register"]
