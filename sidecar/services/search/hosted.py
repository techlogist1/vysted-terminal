"""T3 BYOK hosted search — OpenRouter's ``openrouter:web_search`` server tool.

R7 Track R, Component 3. The hosted tier routes a web search through
OpenRouter's web-search **server tool** — the CURRENT shape per the live docs
(https://openrouter.ai/docs/guides/features/server-tools/web-search, verified
2026-06-10). The older ``plugins: [{"id": "web"}]`` array and the ``:online``
model suffix are **deprecated** ("Use the ``openrouter:web_search`` server tool
instead"), so this module never emits them. The tool rides the ``tools`` array
of a normal chat completion:

    {"type": "openrouter:web_search",
     "parameters": {"engine": "firecrawl", "max_results": 6, ...}}

Engines (live docs, 2026-06-10):

  * ``firecrawl`` — **our default**: searches bill to the user's Firecrawl
    credits directly (no OpenRouter charge); new Firecrawl accounts start with
    10,000 free credits (3-month expiry), so the t3 tier has a genuinely free
    on-ramp.
  * ``exa`` — $0.005 per request via OpenRouter credits, up to 10 results
    included, then $0.001 per additional result.
  * ``parallel`` — same OpenRouter-credit pricing as Exa.
  * ``auto`` — native search when the provider supports it, else Exa.
  * ``native`` — the provider's own search, pass-through pricing.

Results come back as OpenAI-style ``url_citation`` annotations on the
assistant message (``{"type": "url_citation", "url_citation": {"url", "title",
"content", ...}}``); :func:`_map_annotations` flattens them to the shared
:class:`SearchResult`/:class:`Citation` contract. Note the excerpt field is
``content`` for the server tool (``snippet``/``text`` are accepted as
fallbacks for older shapes).

Cost honesty (C.1 "never surprise routing/cost"): every response carries a
``metadata`` annex with ``search_cost_estimate_usd`` + ``cost_basis`` derived
from the documented per-search pricing above — flagged ``estimate: True``
because the model may run 0–N searches per request (we cap the spread with
``max_total_results`` and estimate one search per call).

BYOK: the OpenRouter key rides the request only (``Authorization: Bearer``);
it is never read from the environment or disk, never logged, and never echoed
in a response or error message — same handling as the Exa key in
:mod:`services.search.exa`. No test makes a live call — see
``tests/test_hosted_search.py`` (the HTTP client is stubbed).
"""

from __future__ import annotations

from typing import Any

import httpx

from services.search.base import (
    Citation,
    SearchError,
    SearchResponse,
    SearchResult,
    normalize_results_to_citations,
)

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

#: The CURRENT server-tool type (live docs, 2026-06-10). The ``plugins`` array /
#: ``:online`` suffix path is deprecated — never emitted here.
SERVER_TOOL_TYPE = "openrouter:web_search"

ENGINE_FIRECRAWL = "firecrawl"
ENGINE_EXA = "exa"
ENGINE_PARALLEL = "parallel"
ENGINE_AUTO = "auto"
ENGINE_NATIVE = "native"
KNOWN_ENGINES = frozenset(
    {ENGINE_FIRECRAWL, ENGINE_EXA, ENGINE_PARALLEL, ENGINE_AUTO, ENGINE_NATIVE}
)

#: Firecrawl is the default engine: it is the one with a FREE-credit tier
#: (10,000 Firecrawl credits at signup) and zero OpenRouter-side charge, so the
#: hosted tier's default can never surprise-bill OpenRouter credits.
DEFAULT_ENGINE = ENGINE_FIRECRAWL

#: The model that carries the search call. Any routable model works — OpenRouter
#: runs the search server-side and feeds results back as annotations. Default to
#: the project's known-routed cheap workhorse (the keyless research default per
#: CLAUDE.md); the caller may override per request via ``options["model"]``.
DEFAULT_HOSTED_MODEL = "minimax/minimax-m3"

# Live-docs bounds: "Maximum results per search call (1-25)"; default 5.
_DEFAULT_MAX_RESULTS = 6
_MIN_RESULTS = 1
_MAX_RESULTS = 25

#: Documented per-search pricing (live docs, 2026-06-10): Exa and Parallel bill
#: OpenRouter credits at $0.005/request including up to 10 results, then
#: $0.001 per additional result. Firecrawl bills Firecrawl credits directly
#: ($0 OpenRouter-side). Native is provider pass-through (unknown here).
_PER_REQUEST_USD = 0.005
_INCLUDED_RESULTS = 10
_EXTRA_RESULT_USD = 0.001

_HTTP_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


def normalize_engine(value: str | None) -> str:
    """Coerce an engine id to the known set, defaulting to Firecrawl.

    Unknown / empty values land on the default rather than raising — and the
    default is the engine with the free-credit tier, so a malformed setting can
    never silently switch the user onto a paid engine.
    """
    if not value:
        return DEFAULT_ENGINE
    candidate = value.strip().lower()
    return candidate if candidate in KNOWN_ENGINES else DEFAULT_ENGINE


def _clamp_results(options: dict[str, Any]) -> int:
    """Clamp the requested result count into the documented 1–25 range."""
    requested = options.get("numResults", _DEFAULT_MAX_RESULTS)
    try:
        count = int(requested)
    except (TypeError, ValueError):
        count = _DEFAULT_MAX_RESULTS
    return max(_MIN_RESULTS, min(count, _MAX_RESULTS))


def web_search_server_tool(
    *,
    engine: str = DEFAULT_ENGINE,
    max_results: int = _DEFAULT_MAX_RESULTS,
    allowed_domains: list[str] | None = None,
) -> dict[str, Any]:
    """Build the ``tools`` array entry for OpenRouter's web-search server tool.

    The exact request shape per the live docs (verified 2026-06-10):
    ``{"type": "openrouter:web_search", "parameters": {...}}`` where
    ``parameters`` carries ``engine`` / ``max_results`` / ``max_total_results``
    (+ optional ``allowed_domains``). ``max_total_results`` is pinned to
    ``max_results`` so the model cannot multiply searches past the estimate the
    user was shown.
    """
    parameters: dict[str, Any] = {
        "engine": normalize_engine(engine),
        "max_results": max(_MIN_RESULTS, min(int(max_results), _MAX_RESULTS)),
        "max_total_results": max(_MIN_RESULTS, min(int(max_results), _MAX_RESULTS)),
    }
    if allowed_domains:
        parameters["allowed_domains"] = [str(d).strip() for d in allowed_domains if str(d).strip()]
    return {"type": SERVER_TOOL_TYPE, "parameters": parameters}


def estimate_search_cost_usd(engine: str, max_results: int) -> float | None:
    """Estimate the USD cost of ONE hosted search (documented pricing).

    * Firecrawl → ``0.0`` OpenRouter-side (bills the user's Firecrawl credits
      directly; the free tier is 10,000 credits at signup).
    * Exa / Parallel / Auto → $0.005 per request including 10 results, then
      $0.001 per additional result (auto worst-cases to the Exa fallback).
    * Native → ``None`` — provider pass-through; the price is the upstream
      provider's, unknown here, and we never fabricate a number.

    This is an ESTIMATE of the documented per-search rate, not a billed
    figure — the authoritative charge is OpenRouter's/Firecrawl's.
    """
    eng = normalize_engine(engine)
    if eng == ENGINE_FIRECRAWL:
        return 0.0
    if eng == ENGINE_NATIVE:
        return None
    count = max(_MIN_RESULTS, min(int(max_results), _MAX_RESULTS))
    extra = max(0, count - _INCLUDED_RESULTS)
    return round(_PER_REQUEST_USD + extra * _EXTRA_RESULT_USD, 6)


def _cost_basis(engine: str) -> str:
    """One human line naming what the estimate is based on (cost honesty)."""
    eng = normalize_engine(engine)
    if eng == ENGINE_FIRECRAWL:
        return (
            "Firecrawl engine: $0 OpenRouter-side — searches use your Firecrawl "
            "credits (new accounts include 10,000 free credits)."
        )
    if eng == ENGINE_NATIVE:
        return "Native provider search: pricing is passed through from the upstream provider."
    return (
        f"{eng.capitalize()} engine: $0.005 per search (up to 10 results included), "
        "then $0.001 per additional result, billed to OpenRouter credits."
    )


def _human_http_error(exc: httpx.HTTPStatusError) -> str:
    """Translate an OpenRouter HTTP error into a clean, key-free human message."""
    status = exc.response.status_code
    if status in (401, 403):
        return (
            "OpenRouter rejected the request — check that your OpenRouter API "
            "key is valid and active."
        )
    if status == 402:
        return "OpenRouter reports insufficient credits — top up your account to keep searching."
    if status == 429:
        return "OpenRouter rate limit reached — slow down or check your plan's quota."
    if status == 400:
        return "OpenRouter could not process the search request (bad query or parameters)."
    if status >= 500:
        return "OpenRouter is temporarily unavailable (server error) — try again shortly."
    return f"OpenRouter hosted search failed with HTTP {status}."


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Read ``key`` from a dict or attribute-style object (mirrors native_search)."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _map_annotations(annotations: Any) -> list[SearchResult]:
    """Flatten ``url_citation`` annotations to deduplicated :class:`SearchResult`.

    Handles both the nested shape (``{"type": "url_citation", "url_citation":
    {...}}``) and a flat one; the excerpt field is ``content`` for the server
    tool (live docs), with ``snippet``/``text`` accepted as fallbacks. Entries
    without a url are unciteable and skipped; duplicates (the model citing one
    page twice) keep the first occurrence.
    """
    results: list[SearchResult] = []
    seen: set[str] = set()
    if not isinstance(annotations, (list, tuple)):
        return results
    for ann in annotations:
        ann_type = _get(ann, "type")
        if ann_type is not None and ann_type != "url_citation":
            continue
        inner = _get(ann, "url_citation")
        src = inner if inner is not None else ann
        url = _get(src, "url")
        if not isinstance(url, str) or not url.strip():
            continue
        url = url.strip()
        if url in seen:
            continue
        seen.add(url)
        title = _get(src, "title") or url
        excerpt = _get(src, "content") or _get(src, "snippet") or _get(src, "text") or ""
        results.append(
            SearchResult(url=url, title=str(title).strip(), snippet=str(excerpt).strip())
        )
    return results


class HostedSearchBackend:
    """OpenRouter-hosted implementation of the shared ``SearchBackend`` protocol.

    ``api_key`` is the BYOK OpenRouter key (keychain-sourced; used only as the
    ``Authorization: Bearer`` header — never logged, never echoed). ``engine``
    picks the hosted search engine (Firecrawl default — the free-credit tier);
    ``model`` the carrier model for the completion. ``client`` is an optional
    shared pooled ``httpx.AsyncClient``; absent one, a short-lived client is
    opened per call. Conforms structurally to
    :class:`services.search.base.SearchBackend` without inheriting it.
    """

    name = "hosted"

    def __init__(
        self,
        *,
        api_key: str,
        engine: str | None = None,
        model: str | None = None,
        region: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        key = (api_key or "").strip()
        if not key:
            raise SearchError(
                "OpenRouter hosted search requires an API key, but none was supplied."
            )
        self._api_key = key
        self._engine = normalize_engine(engine)
        self._model = (model or "").strip() or DEFAULT_HOSTED_MODEL
        self._region = region
        self._client = client

    async def search(self, query: str, *, options: dict | None = None) -> SearchResponse:
        """Run one hosted search for ``query`` via the web-search server tool.

        Raises :class:`SearchError` (human message, never raw vendor JSON,
        never the key) on any HTTP or transport failure. The returned
        :class:`SearchResponse` carries the per-search cost estimate in
        ``metadata``.
        """
        text = (query or "").strip()
        if not text:
            raise SearchError("Search query is empty.")
        opts = options or {}
        engine = normalize_engine(str(opts.get("engine") or self._engine))
        model = str(opts.get("model") or self._model).strip() or DEFAULT_HOSTED_MODEL
        max_results = _clamp_results(opts)

        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Search the web for: {text}\n"
                        "Report the most relevant findings, citing every source."
                    ),
                }
            ],
            "tools": [web_search_server_tool(engine=engine, max_results=max_results)],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            if self._client is not None:
                response = await self._client.post(
                    OPENROUTER_CHAT_URL, json=payload, headers=headers, timeout=_HTTP_TIMEOUT
                )
            else:
                async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                    response = await client.post(OPENROUTER_CHAT_URL, json=payload, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise SearchError(_human_http_error(exc)) from exc
        except httpx.HTTPError as exc:
            raise SearchError(
                "Could not reach OpenRouter — check your network connection."
            ) from exc

        try:
            body: dict[str, Any] = response.json()
        except ValueError as exc:
            raise SearchError("OpenRouter returned a response that could not be parsed.") from exc

        message: Any = {}
        choices = body.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            message = choices[0].get("message") or {}

        results = _map_annotations(_get(message, "annotations"))
        citations: list[Citation] = normalize_results_to_citations(results)

        metadata: dict[str, Any] = {
            "tier": "t3_hosted",
            "engine": engine,
            "model": model,
            "search_cost_estimate_usd": estimate_search_cost_usd(engine, max_results),
            "estimate": True,
            "cost_basis": _cost_basis(engine),
        }
        return SearchResponse(
            results=results,
            citations=citations,
            backend=self.name,
            query=text,
            metadata=metadata,
        )


__all__ = [
    "DEFAULT_ENGINE",
    "DEFAULT_HOSTED_MODEL",
    "ENGINE_AUTO",
    "ENGINE_EXA",
    "ENGINE_FIRECRAWL",
    "ENGINE_NATIVE",
    "ENGINE_PARALLEL",
    "KNOWN_ENGINES",
    "OPENROUTER_CHAT_URL",
    "SERVER_TOOL_TYPE",
    "HostedSearchBackend",
    "estimate_search_cost_usd",
    "normalize_engine",
    "web_search_server_tool",
]
