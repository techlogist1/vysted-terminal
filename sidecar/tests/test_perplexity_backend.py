"""Tests for the Perplexity Sonar deep-research BYOK backend (FR-073).

No test makes a live Perplexity call: ``httpx`` is mocked at the transport level
(``httpx.MockTransport`` via an injected fake client), so the request the backend
*would* send is captured and a canned Perplexity JSON body is mapped back through
the real ``services.research.perplexity`` code. The operator validates against the
real API separately with a real key — these tests are fully offline, and spend
nothing.

Coverage:
  * :func:`is_configured` is the key gate — ``None``/blank → ``False``, a real
    key → ``True`` (this is what keeps the backend "present but unconfigured" and
    never auto-selected);
  * :func:`estimate_cost_usd` returns a positive, in-band float (cost shown
    before the run, FR-073);
  * a canned Perplexity response maps to a ``ResearchBrief`` with ``mode="deep"``,
    sources drawn from ``citations[]`` (+ ``search_results[]``), and the
    "via Perplexity Sonar" provenance carried through;
  * a missing key raises a human ``SearchError`` ("needs an API key");
  * an HTTP 401 raises a human ``SearchError`` with no raw vendor JSON;
  * the key is never echoed in the request-derived response or in any error.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from services.research.perplexity import (
    PERPLEXITY_DEEP_MODEL,
    PERPLEXITY_URL,
    PROVENANCE_NOTE,
    PerplexityDeepBackend,
    estimate_cost_usd,
    is_configured,
)
from services.search.base import SearchError

# The model module is owned by a sibling agent; import the real dataclasses when
# available, else fall back to local stand-ins with the SAME required signature
# so this test file is self-contained at collection time.
try:
    from services.research.models import ResearchBrief, ResearchSource
except ImportError:  # pragma: no cover - only when the model module is absent
    from dataclasses import dataclass, field

    @dataclass
    class ResearchSource:  # type: ignore[no-redef]
        url: str
        title: str
        excerpt: str
        domain: str | None = None

    @dataclass
    class ResearchBrief:  # type: ignore[no-redef]
        query: str
        symbol: str
        mode: str
        markdown: str
        sources: list = field(default_factory=list)
        structured: dict = field(default_factory=dict)
        steps: list = field(default_factory=list)
        source_count: int = 0
        cost: dict = field(default_factory=dict)
        web_available: bool = False
        note: str | None = None


_SECRET_KEY = "pplx-secret-key-do-not-leak"

# A canned sonar-deep-research response: the synthesised markdown brief in
# choices[0].message.content, a top-level citations[] of url strings, and a
# richer search_results[] (one overlapping citation, one citation-only).
_FAKE_BODY: dict[str, Any] = {
    "id": "resp-123",
    "model": PERPLEXITY_DEEP_MODEL,
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": (
                    "## NVIDIA demand outlook\n\n"
                    "Data-center revenue continues to lead [1], with supply "
                    "constraints easing into the next quarter [2]."
                ),
            },
        }
    ],
    "citations": [
        "https://www.reuters.com/technology/nvidia-datacenter",
        "https://www.bloomberg.com/news/nvidia-supply",
    ],
    "search_results": [
        {
            "url": "https://www.reuters.com/technology/nvidia-datacenter",
            "title": "Nvidia data-center revenue surges",
            "snippet": "Revenue from data-center GPUs set another record.",
        }
    ],
}


class _Captured:
    """Records the single request the backend issues so the test can assert on it."""

    def __init__(self) -> None:
        self.request: httpx.Request | None = None


def _mock_client(captured: _Captured, *, status: int = 200) -> httpx.AsyncClient:
    """An ``httpx.AsyncClient`` whose transport records the request + returns canned JSON."""

    def handler(request: httpx.Request) -> httpx.Response:
        captured.request = request
        if status != 200:
            return httpx.Response(status, json={"error": {"message": "Unauthorized"}})
        return httpx.Response(status, json=_FAKE_BODY)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# is_configured — the never-auto-select gate (FR-073)
# ---------------------------------------------------------------------------


def test_is_configured_false_without_key() -> None:
    assert is_configured(None) is False
    assert is_configured("") is False
    assert is_configured("   ") is False


def test_is_configured_true_with_key() -> None:
    assert is_configured("k") is True
    assert is_configured(_SECRET_KEY) is True


# ---------------------------------------------------------------------------
# estimate_cost_usd — cost shown before the run (FR-073)
# ---------------------------------------------------------------------------


def test_estimate_cost_is_positive_float_in_band() -> None:
    cost = estimate_cost_usd("what is the demand outlook for nvidia data-center gpus")
    assert isinstance(cost, float)
    assert cost > 0.0
    # Documented as a rough ~$0.20–0.40 per-run estimate.
    assert 0.20 <= cost <= 0.40


def test_estimate_cost_handles_empty_query() -> None:
    # Even an empty query yields a positive base estimate (still a real run).
    assert estimate_cost_usd("") > 0.0


# ---------------------------------------------------------------------------
# research() — happy path mapping to a ResearchBrief
# ---------------------------------------------------------------------------


def test_research_maps_to_deep_brief_with_sources() -> None:
    captured = _Captured()
    client = _mock_client(captured)
    backend = PerplexityDeepBackend(_SECRET_KEY, client=client)
    brief = _run(backend.research("nvidia demand outlook"))

    assert isinstance(brief, ResearchBrief)
    assert brief.mode == "deep"
    assert brief.web_available is True
    assert "NVIDIA demand outlook" in brief.markdown

    # Sources come from citations[] (+ search_results[]), deduped by url.
    urls = [s.url for s in brief.sources]
    assert "https://www.reuters.com/technology/nvidia-datacenter" in urls
    assert "https://www.bloomberg.com/news/nvidia-supply" in urls
    assert len(urls) == len(set(urls)) == 2
    assert brief.source_count == len(brief.sources)
    assert all(isinstance(s, ResearchSource) for s in brief.sources)

    # The richer search_results entry supplies a real title/excerpt.
    reuters = next(s for s in brief.sources if "reuters" in s.url)
    assert reuters.title == "Nvidia data-center revenue surges"
    assert "data-center GPUs" in reuters.excerpt

    # Provenance "via Perplexity Sonar" rides every source + the cost snapshot.
    assert all(PROVENANCE_NOTE in (s.domain or "") for s in brief.sources)
    assert brief.cost.get("provider") == PROVENANCE_NOTE
    assert brief.cost.get("estimate") is True
    assert brief.cost.get("spend_usd", 0) > 0.0


def test_research_sends_bearer_key_and_model_without_leaking() -> None:
    captured = _Captured()
    client = _mock_client(captured)
    backend = PerplexityDeepBackend(_SECRET_KEY, client=client)
    brief = _run(backend.research("nvidia demand outlook"))

    req = captured.request
    assert req is not None
    assert str(req.url) == PERPLEXITY_URL
    # The key rides ONLY as the Authorization: Bearer header, never elsewhere.
    assert req.headers.get("authorization") == f"Bearer {_SECRET_KEY}"
    body = req.content.decode()
    assert PERPLEXITY_DEEP_MODEL in body
    assert _SECRET_KEY not in body
    # And the key never surfaces in the mapped brief.
    assert _SECRET_KEY not in brief.markdown
    assert _SECRET_KEY not in str(brief.cost)
    assert all(_SECRET_KEY not in (s.url + s.title + s.excerpt) for s in brief.sources)


# ---------------------------------------------------------------------------
# research() — error paths (human messages, never raw JSON, never the key)
# ---------------------------------------------------------------------------


def test_missing_key_raises_human_error() -> None:
    backend = PerplexityDeepBackend(None)
    with pytest.raises(SearchError) as exc:
        _run(backend.research("anything"))
    message = str(exc.value)
    assert "API key" in message
    assert "Perplexity" in message
    # No raw JSON / stack noise.
    assert "{" not in message


def test_blank_key_raises_human_error() -> None:
    backend = PerplexityDeepBackend("   ")
    with pytest.raises(SearchError):
        _run(backend.research("anything"))


def test_http_401_raises_human_error_without_leaking_key() -> None:
    captured = _Captured()
    client = _mock_client(captured, status=401)
    backend = PerplexityDeepBackend(_SECRET_KEY, client=client)
    with pytest.raises(SearchError) as exc:
        _run(backend.research("nvidia demand outlook"))
    message = str(exc.value)
    assert "Perplexity" in message
    assert _SECRET_KEY not in message
    # A clean human message, not the vendor's raw error JSON.
    assert "Unauthorized" not in message
    assert "{" not in message


def test_empty_query_raises_human_error() -> None:
    captured = _Captured()
    client = _mock_client(captured)
    backend = PerplexityDeepBackend(_SECRET_KEY, client=client)
    with pytest.raises(SearchError) as exc:
        _run(backend.research("   "))
    assert "empty" in str(exc.value).lower()


def test_empty_brief_body_raises_human_error() -> None:
    captured = _Captured()

    def handler(request: httpx.Request) -> httpx.Response:
        captured.request = request
        return httpx.Response(200, json={"choices": [{"message": {"content": ""}}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    backend = PerplexityDeepBackend(_SECRET_KEY, client=client)
    with pytest.raises(SearchError) as exc:
        _run(backend.research("nvidia demand outlook"))
    assert "empty" in str(exc.value).lower()
