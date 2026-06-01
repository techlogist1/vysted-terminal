"""Exa BYOK search backend (FR-083 — the default BYOK search tier).

Exa (https://exa.ai) is the default bring-your-own-key web-search backend for the
agent research layer. The user's key lives in the OS keychain and rides the
request from the renderer; it is handed to :class:`ExaBackend` at construction
(``ExaBackend(api_key=..., region=...)``) and used only as the ``x-api-key``
header on the outbound Exa request. The key is **never** read from the
environment or disk, **never** logged, and **never** echoed back in a response or
error message.

The backend maps Exa's ``POST /search`` response onto the shared search contract
(:class:`SearchResult` / :class:`SearchResponse` / :class:`Citation` from
``services.search.base``): each ``results[]`` entry becomes a
:class:`SearchResult`, and the top results are projected to :class:`Citation`
via :func:`normalize_results_to_citations`. Any upstream failure (HTTP error,
malformed body) surfaces as a :class:`SearchError` carrying a human-readable
message — never a raw vendor JSON blob.

Finance-suitability (FR-083): when the caller's options request a ``news`` or
``financial`` category, the matching Exa ``category`` is passed so results skew
to news / financial-report sources; when a region is active, the region's
locale-native domain allow-list is applied via Exa's ``includeDomains`` so an IN
session prefers Indian sources and a US session prefers US ones.

Network I/O uses the shared-``httpx.AsyncClient`` pattern: callers may pass a
pooled client (owned by the FastAPI lifespan); absent one, a short-lived client
is opened for the single request. No test makes a live call — see
``tests/test_exa_backend.py`` (httpx is monkeypatched).
"""

from __future__ import annotations

from typing import Any

import httpx

from services.search.base import (
    Citation,
    SearchError,
    SearchResponse,
    SearchResult,
    locale_domains,
    normalize_results_to_citations,
)

EXA_SEARCH_URL = "https://api.exa.ai/search"

# Default number of results when the caller does not specify one.
_DEFAULT_NUM_RESULTS = 6
# Exa caps numResults; keep the request sane regardless of caller input.
_MAX_NUM_RESULTS = 25
# Snippet length requested from Exa (chars of page text per result).
_TEXT_MAX_CHARACTERS = 512
_HTTP_TIMEOUT = httpx.Timeout(20.0, connect=8.0)

# Caller-facing category aliases → Exa's vocabulary. Exa exposes a small set of
# curated categories; "news" and "financial report" are the finance-relevant
# ones (FR-083). The agent passes a coarse "news"/"financial" hint; we translate.
_CATEGORY_ALIASES: dict[str, str] = {
    "news": "news",
    "financial": "financial report",
    "financial report": "financial report",
    "financial_report": "financial report",
    "company": "company",
    "research": "research paper",
    "research paper": "research paper",
}


def _resolve_category(options: dict[str, Any]) -> str | None:
    """Map a caller's coarse category hint to Exa's category vocabulary.

    Returns ``None`` (Exa decides) when no recognized finance category is asked
    for, so a plain web query is not forced into a narrow bucket.
    """
    raw = options.get("category")
    if not isinstance(raw, str):
        return None
    return _CATEGORY_ALIASES.get(raw.strip().lower())


def _resolve_include_domains(options: dict[str, Any], region: str | None) -> list[str]:
    """Resolve the ``includeDomains`` allow-list for this request (C.2).

    An explicit ``locale_domains`` list in the options wins; otherwise the active
    region — ``options["region"]`` first, then the backend's construction-time
    region — selects the bundled native allow-list via
    :func:`services.search.base.locale_domains`. Absent any region signal, an
    empty list (Exa searches the open web).
    """
    explicit = options.get("locale_domains")
    if isinstance(explicit, (list, tuple)):
        domains = [str(d).strip() for d in explicit if str(d).strip()]
        if domains:
            return domains
    active_region = options.get("region") or region
    if isinstance(active_region, str) and active_region.strip():
        return locale_domains(active_region)
    return []


def _num_results(options: dict[str, Any]) -> int:
    """Clamp the requested result count into a sane range (default 6)."""
    requested = options.get("numResults", _DEFAULT_NUM_RESULTS)
    try:
        count = int(requested)
    except (TypeError, ValueError):
        count = _DEFAULT_NUM_RESULTS
    return max(1, min(count, _MAX_NUM_RESULTS))


def _build_payload(query: str, options: dict[str, Any], region: str | None) -> dict[str, Any]:
    """Assemble the Exa ``/search`` JSON body for ``query`` under ``options``."""
    payload: dict[str, Any] = {
        "query": query,
        "numResults": _num_results(options),
        "type": "auto",
        "contents": {"text": {"maxCharacters": _TEXT_MAX_CHARACTERS}},
    }
    category = _resolve_category(options)
    if category:
        payload["category"] = category
    include_domains = _resolve_include_domains(options, region)
    if include_domains:
        payload["includeDomains"] = include_domains
    return payload


def _map_result(raw: dict[str, Any]) -> SearchResult | None:
    """Map one Exa ``results[]`` entry to a :class:`SearchResult`.

    Skips entries without a usable url (a result with no link is unciteable).
    """
    url = raw.get("url")
    if not isinstance(url, str) or not url.strip():
        return None
    title = raw.get("title") or url
    snippet = raw.get("text") or raw.get("snippet") or ""
    published_at = raw.get("publishedDate") or raw.get("published_at")
    source = raw.get("author") or raw.get("source")
    return SearchResult(
        url=url.strip(),
        title=str(title).strip(),
        snippet=str(snippet).strip(),
        published_at=str(published_at).strip() if isinstance(published_at, str) else None,
        source=str(source).strip() if isinstance(source, str) and source.strip() else None,
    )


def _human_http_error(exc: httpx.HTTPStatusError) -> str:
    """Translate an Exa HTTP error into a clean, key-free, human message."""
    status = exc.response.status_code
    if status in (401, 403):
        return "Exa rejected the request — check that your Exa API key is valid and active."
    if status == 429:
        return "Exa rate limit reached — slow down or check your plan's quota."
    if status == 400:
        return "Exa could not process the search request (bad query or parameters)."
    if status >= 500:
        return "Exa is temporarily unavailable (server error) — try again shortly."
    return f"Exa search failed with HTTP {status}."


class ExaSearchBackend:
    """Exa-backed implementation of the shared ``SearchBackend`` protocol.

    ``api_key`` is the BYOK Exa key (keychain-sourced; used only as the
    ``x-api-key`` header). ``region`` is the active locale, used to pick a
    native domain allow-list. ``client`` is an optional shared pooled
    ``httpx.AsyncClient``; when omitted a short-lived client is used per call.

    Conforms structurally to ``services.search.base.SearchBackend`` (a
    ``runtime_checkable`` Protocol) — ``isinstance(ExaSearchBackend(...),
    SearchBackend)`` holds — without inheriting it, so its ``__init__`` stays
    free. The registry (:mod:`services.search.registry`) imports this by name.
    """

    name = "exa"

    def __init__(
        self,
        *,
        api_key: str,
        region: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        key = (api_key or "").strip()
        if not key:
            raise SearchError("Exa search requires an API key, but none was supplied.")
        self._api_key = key
        self._region = region
        self._client = client

    async def search(self, query: str, *, options: dict | None = None) -> SearchResponse:
        """Run an Exa search for ``query`` and map it to a :class:`SearchResponse`.

        Raises :class:`SearchError` (human message, never raw vendor JSON, never
        the key) on any HTTP or transport failure.
        """
        text = (query or "").strip()
        if not text:
            raise SearchError("Search query is empty.")
        opts = options or {}
        payload = _build_payload(text, opts, self._region)
        headers = {"x-api-key": self._api_key, "content-type": "application/json"}

        try:
            if self._client is not None:
                response = await self._client.post(
                    EXA_SEARCH_URL, json=payload, headers=headers, timeout=_HTTP_TIMEOUT
                )
            else:
                async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                    response = await client.post(EXA_SEARCH_URL, json=payload, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise SearchError(_human_http_error(exc)) from exc
        except httpx.HTTPError as exc:
            raise SearchError("Could not reach Exa — check your network connection.") from exc

        try:
            body: dict[str, Any] = response.json()
        except ValueError as exc:
            raise SearchError("Exa returned a response that could not be parsed.") from exc

        raw_results = body.get("results")
        if not isinstance(raw_results, list):
            raw_results = []

        results: list[SearchResult] = []
        for raw in raw_results:
            if isinstance(raw, dict):
                mapped = _map_result(raw)
                if mapped is not None:
                    results.append(mapped)

        citations: list[Citation] = normalize_results_to_citations(results)
        return SearchResponse(results=results, citations=citations, backend=self.name, query=text)


#: Back-compat / task alias — ``ExaBackend`` and ``ExaSearchBackend`` are the same
#: class (the registry imports the latter; the spec refers to the former).
ExaBackend = ExaSearchBackend

__all__ = ["EXA_SEARCH_URL", "ExaBackend", "ExaSearchBackend"]
