"""Mojeek HTML search engine adapter — keyless T1 rotation member (R7 Component 1).

Scrapes the Mojeek SERP at ``https://www.mojeek.com/search?q=`` into the
uniform ``{title, url, snippet}`` result shape. Mojeek runs its OWN index (not
a Google/Bing meta-layer), which makes it the most independent member of the
keyless rotation — when DDG and Brave are both throttling, Mojeek usually is
not. It is friendly to plain httpx with browser headers, so it rides the
httpx lane (no impersonation needed).

Parsing is bs4 with layered selectors (``ul.results-standard li`` first, then
looser fallbacks) so markup drift degrades to fewer fields, never a crash.
Zero parsed rows → empty successful response; transport failure / block →
typed :class:`~services.search.base.SearchError` for the rotation layer.

The fetch/error-handling contract this shares with :mod:`.brave` lives in
:mod:`.html_serp` (R15-CODE-RESEARCH-010) — this module supplies only the
Mojeek-specific endpoint, region param and selector chain as configuration.
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
from .transport import httpx_fetch

#: Identifier this engine reports in :class:`SearchResponse.backend`.
BACKEND_ID = "mojeek"

_ENDPOINT = "https://www.mojeek.com/search"

#: Mojeek region bias (``arc`` param) by Vysted region.
_REGION_ARC = {"US": "us", "IN": "in"}

_SKIP_HOSTS = ("mojeek.com",)


def _node_to_result(node) -> SearchResult | None:  # noqa: ANN001 — bs4 Tag
    anchor = node.select_one("a.title") or (node.h2.find("a", href=True) if node.h2 else None)
    if anchor is None:
        anchor = node.find("a", href=True)
    if anchor is None or not anchor.get("href"):
        return None
    url = anchor["href"].strip()
    if not is_organic_url(url, skip_hosts=_SKIP_HOSTS):
        return None
    snippet_node = node.select_one("p.s") or node.select_one(".s")
    title = clean_text(anchor.get_text(" ", strip=True)) or url
    snippet = clean_text(snippet_node.get_text(" ", strip=True)) if snippet_node else ""
    return SearchResult(url=url, title=title, snippet=snippet, source="mojeek")


def _parse(html_text: str, limit: int) -> list[SearchResult]:
    """Parse the Mojeek SERP into normalized results (layered selectors)."""
    soup = BeautifulSoup(html_text, "html.parser")
    containers = soup.select("ul.results-standard li")
    if not containers:
        containers = soup.select("ul.results li") or soup.select("li.result")
    return parse_containers(containers, limit=limit, node_to_result=_node_to_result)


_CONFIG = HtmlSerpConfig(
    backend_id=BACKEND_ID,
    engine_label="Mojeek",
    endpoint=_ENDPOINT,
    default_fetch=httpx_fetch,
    parse=_parse,
    region_param="arc",
    region_map=_REGION_ARC,
)


class MojeekSearchBackend(_HtmlSerpBackend):
    """Keyless Mojeek HTML scrape over the friendly httpx lane."""

    def __init__(self, *, region: str | None = None, fetch=None) -> None:  # noqa: ANN001
        super().__init__(_CONFIG, region=region, fetch=fetch)


__all__ = ["BACKEND_ID", "MojeekSearchBackend"]
