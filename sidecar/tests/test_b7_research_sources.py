"""Batch-7 research-funnel pins: web sources keep their date and a bare-host domain."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx

from services import agent_runtime
from services.agent_tools import web_search
from services.research import deep
from services.research.sonar import PROVENANCE_NOTE, _extract_sources
from services.search.searxng import SearxngBackend

_ROW = {
    "url": "https://www.reuters.com/markets/nvidia-q4",
    "title": "Nvidia Q4 revenue beats",
    "content": "Nvidia reported record data-center revenue.",
    "publishedDate": "2026-02-26T21:05:00",
}


def _searxng() -> SearxngBackend:
    transport = httpx.MockTransport(lambda _req: httpx.Response(200, json={"results": [_ROW]}))
    return SearxngBackend("http://127.0.0.1:8888", client=httpx.AsyncClient(transport=transport))


def _web_out() -> dict[str, Any]:
    return asyncio.run(web_search._dispatch(_searxng(), "nvidia q4", 5, "general", "US"))


def test_a_dated_searxng_row_reaches_the_web_rows_and_the_brief_source() -> None:
    """R15-RESEARCH-024: the date and the bare host survive web_search and the
    DEEP source recorder (the domain used to read as the literal 'web')."""
    out = _web_out()
    for row in (out["citations"][0], out["results"][0]):
        assert row["domain"] == "reuters.com"
        assert row["published_at"] == "2026-02-26T21:05:00"

    findings = deep._Findings()
    deep._record_web(findings, out, query="nvidia q4 revenue")
    (source,) = findings.web_sources
    assert source.domain == "reuters.com"
    assert source.published_at == "2026-02-26T21:05:00"
    assert source.to_dict()["published_at"] == "2026-02-26T21:05:00"


def test_the_fast_auto_publish_forwards_the_date_and_host() -> None:
    """The runtime half (C4, already on base) now receives the keys it reads."""

    class _Call:
        tool_call_id = "tc-1"

    bundle = {
        "ok": True,
        "query": "NVDA",
        "symbol": "NVDA",
        "execution": {"run_id": "run-1", "loop": "fast", "requested_depth": "normal"},
        "structured": {"price": {"ok": True}},
        "web": {"available": True, **_web_out()},
    }
    event = agent_runtime._auto_publish_event(_Call(), json.dumps(bundle))
    assert event is not None
    (source,) = event.input["sources"]
    assert source["domain"] == "reuters.com"
    assert source["published_at"] == "2026-02-26T21:05:00"


def test_a_sonar_sec_citation_keeps_a_bare_host_and_moves_provenance() -> None:
    """R15-UI-038: provenance rides `provider`; `domain` is the host alone."""
    body = {"choices": [{"message": {"content": "x"}}], "citations": ["https://www.sec.gov/a"]}
    (source,) = _extract_sources(body)
    assert source.domain == "sec.gov"
    assert source.provider == PROVENANCE_NOTE
