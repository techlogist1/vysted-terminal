"""R15-RESEARCH-020: every web backend honours the caller's result cap the same way."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from services.search import brave, ddg, mojeek
from services.search.base import SearchResult, result_limit
from services.search.searxng import SearxngBackend
from services.search.transport import FetchResult

_ROWS = [SearchResult(url=f"https://ex{i}.com/a", title=f"T{i}", snippet="s") for i in range(10)]


def _parse(_text: str, *, limit: int) -> list[SearchResult]:
    return _ROWS[:limit]


async def _fetched(*_a: Any, **_k: Any) -> FetchResult:
    return FetchResult(status_code=200, text="<html></html>", url="u")


def _searxng(_mp: pytest.MonkeyPatch) -> Any:
    rows = [{"url": r.url, "title": r.title, "content": r.snippet} for r in _ROWS]
    transport = httpx.MockTransport(lambda _req: httpx.Response(200, json={"results": rows}))
    return SearxngBackend("http://127.0.0.1:8888", client=httpx.AsyncClient(transport=transport))


def _ddg(mp: pytest.MonkeyPatch) -> Any:
    async def _page(*_a: Any, **_k: Any) -> str:
        return "<html></html>"

    mp.setattr(ddg, "_fetch", _page)
    mp.setattr(ddg, "_parse", _parse)
    return ddg.DdgSearchBackend(client=httpx.AsyncClient())


def _brave(mp: pytest.MonkeyPatch) -> Any:
    mp.setattr(brave, "_parse", _parse)
    return brave.BraveSearchBackend(fetch=_fetched)


def _mojeek(mp: pytest.MonkeyPatch) -> Any:
    mp.setattr(mojeek, "_parse", _parse)
    return mojeek.MojeekSearchBackend(fetch=_fetched)


@pytest.mark.parametrize("build", [_searxng, _ddg, _brave, _mojeek])
def test_num_results_caps_results_and_citations(build: Any, monkeypatch) -> None:
    backend = build(monkeypatch)
    # The exact options dict web_search._dispatch sends.
    options = {"numResults": 3, "category": "general", "region": "IN"}
    resp = asyncio.run(backend.search("q", options=options))
    assert len(resp.results) == 3
    assert len(resp.citations) == 3


def test_result_limit_rule() -> None:
    assert result_limit({"maxResults": 2, "numResults": 5}) == 2
    assert result_limit({"numResults": "4"}) == 4
    assert result_limit({"numResults": 0}) == 8
    assert result_limit({"numResults": "x"}) == 8
    assert result_limit(None) == 8
