"""Agent tool — ``web_search`` (the ONE retrieval resolution path; R9 two-tier).

Grounds an answer in current web context (FR-080/082/083/084) and returns
normalized results + citations. R9 (Track A) collapses retrieval to ONE local
lane shared by BOTH research tiers — the tier governs where RESEARCH routes
(see :mod:`services.agent_tools.research`), never where retrieval happens:

(a) an explicit custom SearXNG URL (``X-Vysted-Searxng-Url`` →
    :func:`config.get_searxng_url`) is used as-is;
(b) else a READY managed SearXNG (:mod:`services.searxng_manager` — an instant
    in-process ``ready_base_url()`` read, no network probe) serves the query;
(c) else the keyless engine rotation serves it SILENTLY with the honest
    ``backend="keyless-fallback"`` id on the result — the UI renders a nudge
    banner off that id (Team C), and a stopped SearXNG NEVER yields a "no web
    backend" error state (R9 rule 1, extending R8 D20/D25).

A SearXNG instance that resolves but fails AT SEARCH TIME (stopped container,
dead custom URL) degrades the same way: one retry on the keyless floor, stamped
``keyless-fallback`` — same local/keyless privacy class, no key/cost boundary
crossed, and the honest id means no banner can claim SearXNG served the run.

Legacy headers map per the R9 migration (``config.get_effective_research_tier``
folds them); the dead R7/R8 lanes (Exa-direct, the OpenRouter web-plugin
hosted scraper) are GONE — no legacy lane reaches a paid backend from here.

When the model's native server-side search rides instead (tier_a with a
native-capable model), the runtime withholds this tool — see
``agent_runtime``. When even the defensive floor cannot resolve, the handler
returns an honest, human "unavailable" naming the unlock (FR-082) — it never
fabricates a source.
"""

from __future__ import annotations

from typing import Any

from services.agent_tools import register_tool

#: The honest backend id stamped when the keyless rotation served a query in
#: FALLBACK position (SearXNG selected-but-unavailable). The UI's nudge banner
#: keys off this id; mirrored by the frontend brief/banner consumers (Team C).
KEYLESS_FALLBACK_BACKEND_ID = "keyless-fallback"

_NO_BACKEND_MESSAGE = (
    "No web-search backend is available for this query. Set up Unlimited "
    "(Local) research in Settings → Research, or switch to a model with "
    "native web search. I won't invent sources."
)


async def _resolve_backend(region: str) -> tuple[Any, str | None]:
    """The ONE retrieval-resolution path (R9 Track A).

    Returns ``(backend, label)``: ``label`` is the honest backend id override
    (:data:`KEYLESS_FALLBACK_BACKEND_ID`) when the keyless floor serves in
    fallback position, else ``None`` (the backend's own id stands). ``backend``
    is ``None`` only on the defensive everything-failed-to-import path — never
    because SearXNG is down (rule 1: a stopped SearXNG NEVER yields "no web
    backend").
    """
    import config
    from services.search import registry

    # (a) An explicit custom instance URL is used as-is — the user pointed at it.
    searxng_url = config.get_searxng_url()
    if searxng_url:
        backend = registry.resolve("searxng", searxng_url=searxng_url, region=region)
        if backend is not None:
            return backend, None

    # (b) The managed instance, when READY — an instant in-process read (no
    # network probe on the hot path); a green SearXNG is never bypassed.
    from services import searxng_manager

    managed_url = searxng_manager.manager.ready_base_url()
    if managed_url:
        backend = registry.resolve("searxng", searxng_url=managed_url, region=region)
        if backend is not None:
            return backend, None

    # (c) The keyless rotation floor (DDG → Brave → Mojeek) — needs no key/URL
    # and ALWAYS resolves, stamped with the honest fallback id. The bare
    # single-engine ddg floor stays as the defensive fallback should the
    # keyless module ever fail to import.
    backend = registry.resolve("keyless", region=region) or registry.resolve("ddg", region=region)
    return backend, KEYLESS_FALLBACK_BACKEND_ID


async def _keyless_floor(region: str) -> Any:
    """The keyless floor backend (or the bare-ddg defensive fallback), or None."""
    from services.search import registry

    return registry.resolve("keyless", region=region) or registry.resolve("ddg", region=region)


async def _web_search(args: dict[str, Any]) -> dict[str, Any]:
    """Run a web search via the resolved local backend; cite the results.

    Returns ``{"ok": True, "backend": ..., "results": [...], "citations": [...]}``
    or, when nothing can serve / the backend fails, ``{"ok": False,
    "message": <human reason>}`` — never raw JSON, never a fabricated source.
    A SearXNG backend that fails at search time degrades ONCE to the keyless
    floor (stamped ``keyless-fallback``) instead of erring.
    """
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {"ok": False, "error": "missing or non-string query"}
    num_results = int(args.get("num_results", 6) or 6)
    category = str(args.get("category", "general"))

    import config

    region = config.get_region()
    backend, label = await _resolve_backend(region)
    if backend is None:
        return {"ok": False, "query": query, "message": _NO_BACKEND_MESSAGE}

    out = await _dispatch(backend, query, num_results, category, region)

    # A SearXNG instance that resolved but failed at SEARCH time (stopped
    # container / dead custom URL) degrades to the keyless floor instead of
    # surfacing an error state — same local privacy class, honest fallback id.
    # ``label is None`` ⟺ a SearXNG lane served (by construction the keyless
    # floor always carries the fallback label), so only SearXNG retries here.
    if out.get("ok") is False and label is None and out.get("reason") == "unreachable":
        floor = await _keyless_floor(region)
        if floor is not None:
            out = await _dispatch(floor, query, num_results, category, region)
            label = KEYLESS_FALLBACK_BACKEND_ID

    if out.get("ok") is True and label is not None:
        out["backend"] = label
        # R9 gate 2: record the floor hit on the run's shared telemetry (when a
        # research parent opened one) so the published brief can carry the
        # honest keyless-fallback id even though researchers run in child tasks.
        if label == KEYLESS_FALLBACK_BACKEND_ID:
            telemetry = config.get_search_telemetry()
            if telemetry is not None:
                telemetry["keyless_fallback_searches"] = (
                    telemetry.get("keyless_fallback_searches", 0) + 1
                )
    return out


async def _dispatch(
    backend: Any, query: str, num_results: int, category: str, region: str
) -> dict[str, Any]:
    """Run the resolved backend and shape the tool result.

    A backend that annotates its response has that annex passed through under
    ``metadata`` so the caller can show honest provenance alongside the
    results (C.1).
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


__all__ = ["KEYLESS_FALLBACK_BACKEND_ID", "_web_search", "register"]
