"""Brave HTML search engine adapter — keyless T1 rotation member (R7 Component 1).

Scrapes the server-rendered Brave SERP at ``https://search.brave.com/search?q=``
into the uniform ``{title, url, snippet}`` result shape. No key, no setup —
but Brave fingerprint-blocks plain httpx TLS, so EVERY request rides the
curl_cffi Chrome-impersonation lane (:func:`services.search.transport
.impersonated_fetch`).

Parsing is bs4 with layered selectors: the precise current markup first
(``div.snippet[data-type="web"]``), then progressively looser heuristics so a
class-name drift degrades to "fewer fields" rather than zero rows. Zero parsed
rows is returned as an empty (successful) response — a valid "found nothing",
distinct from a transport failure or a block (which raise the typed
:class:`~services.search.base.SearchError` the rotation layer keys on).

The fetch/error-handling contract this shares with :mod:`.mojeek` lives in
:mod:`.html_serp` (R15-CODE-RESEARCH-010) — this module supplies only the
Brave-specific endpoint, region param and selector chain as configuration.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from .base import SearchResult
from .html_serp import (
    HtmlSerpConfig,
    _HtmlSerpBackend,
    clean_text,
    is_organic_url,
    parse_containers,
)
from .transport import impersonated_fetch

#: Identifier this engine reports in :class:`SearchResponse.backend`.
BACKEND_ID = "brave"

_ENDPOINT = "https://search.brave.com/search"

#: Brave SERP country codes by Vysted region (best-effort locale bias).
_REGION_COUNTRY = {"US": "us", "IN": "in"}

#: Hosts that are Brave chrome, not organic results (ad/redirect/self links).
_SKIP_HOSTS = ("search.brave.com", "brave.com")


def _node_to_result(node) -> SearchResult | None:  # noqa: ANN001 — bs4 Tag
    """Map one result container to a :class:`SearchResult` (or None)."""
    anchor = node.find("a", href=True)
    if anchor is None:
        return None
    url = anchor["href"].strip()
    if not is_organic_url(url, skip_hosts=_SKIP_HOSTS):
        return None
    title_node = node.select_one(".title") or anchor
    desc_node = node.select_one(".snippet-description") or node.select_one(".snippet-content")
    title = clean_text(title_node.get_text(" ", strip=True)) or url
    snippet = clean_text(desc_node.get_text(" ", strip=True)) if desc_node else ""
    return SearchResult(url=url, title=title, snippet=snippet, source="brave")


def _parse(html_text: str, limit: int) -> list[SearchResult]:
    """Parse the Brave SERP HTML into normalized results (layered selectors).

    Empty list when nothing parses — a valid "found nothing", never an error.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    containers = soup.select('div.snippet[data-type="web"]')
    if not containers:
        containers = soup.select("#results .snippet") or soup.select("div.snippet")
    return parse_containers(containers, limit=limit, node_to_result=_node_to_result)


_CONFIG = HtmlSerpConfig(
    backend_id=BACKEND_ID,
    engine_label="Brave HTML search",
    endpoint=_ENDPOINT,
    default_fetch=impersonated_fetch,
    parse=_parse,
    region_param="country",
    region_map=_REGION_COUNTRY,
    extra_params={"source": "web"},
)


class BraveSearchBackend(_HtmlSerpBackend):
    """Keyless Brave HTML scrape over the Chrome-impersonation transport."""

    def __init__(self, *, region: str | None = None, fetch=None) -> None:  # noqa: ANN001
        super().__init__(_CONFIG, region=region, fetch=fetch)


__all__ = ["BACKEND_ID", "BraveSearchBackend"]
