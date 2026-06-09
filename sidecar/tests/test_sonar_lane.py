"""R7 Track R (Component 3) — the Sonar one-call research lane via OpenRouter.

Offline: the HTTP layer is a stub client injected via the backend's ``client``
seam — no live OpenRouter call, ever. Covers model resolution (Tongyi stays
out), the normalize_openai citation path + the pass-through ``citations[]``
fallback merge, provenance labelling, cost estimates, BYOK key hygiene, and the
``run_deep_brief`` backend dispatch.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

import config
from services.research import sonar
from services.research.models import ResearchBrief
from services.research.sonar import (
    PROVENANCE_NOTE,
    SONAR_DEEP_MODEL,
    SONAR_MODELS,
    OpenRouterSonarBackend,
    estimate_cost_usd,
    is_configured,
    resolve_model,
)
from services.search.base import SearchError


def _run(coro):
    return asyncio.run(coro)


# --- Model resolution -----------------------------------------------------------


def test_default_model_is_deep_research() -> None:
    assert resolve_model(None) == "perplexity/sonar-deep-research"
    assert resolve_model("") == SONAR_DEEP_MODEL


def test_family_slugs_pass_through() -> None:
    for slug in SONAR_MODELS:
        assert resolve_model(slug) == slug


def test_short_spellings_resolve() -> None:
    assert resolve_model("sonar-pro") == "perplexity/sonar-pro"
    assert resolve_model("sonar") == "perplexity/sonar"
    assert resolve_model("deep-research") == SONAR_DEEP_MODEL
    assert resolve_model("SONAR-REASONING") == "perplexity/sonar-reasoning"


def test_unknown_model_floors_to_deep_default() -> None:
    assert resolve_model("warpdrive-9000") == SONAR_DEEP_MODEL


def test_tongyi_is_delisted_and_unreachable() -> None:
    # alibaba/tongyi-deepresearch-30b-a3b is DELISTED from OpenRouter (live
    # check 2026-06-10) — it must never appear in the family or resolve as-is.
    assert all("tongyi" not in slug for slug in SONAR_MODELS)
    assert resolve_model("alibaba/tongyi-deepresearch-30b-a3b") == SONAR_DEEP_MODEL


# --- Cost estimates --------------------------------------------------------------


def test_deep_estimate_sits_in_documented_band() -> None:
    assert 0.20 <= estimate_cost_usd("short query") <= 0.40
    # A long query nudges up but never exceeds the band ceiling.
    assert estimate_cost_usd("x" * 10_000) == 0.40


def test_light_sonar_models_estimate_centi_dollars() -> None:
    light = estimate_cost_usd("short query", model="perplexity/sonar")
    assert 0.0 < light <= 0.05
    assert light < estimate_cost_usd("short query")


def test_is_configured_gate() -> None:
    assert is_configured("sk-or-abc") is True
    assert is_configured("   ") is False
    assert is_configured(None) is False


# --- Backend behaviour ------------------------------------------------------------


class _StubResponse:
    def __init__(self, body: dict[str, Any], status: int = 200) -> None:
        self._body = body
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", sonar.OPENROUTER_CHAT_URL)
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("boom", request=request, response=response)

    def json(self) -> dict[str, Any]:
        return self._body


class _StubClient:
    def __init__(self, body: dict[str, Any], status: int = 200) -> None:
        self._body = body
        self._status = status
        self.captured: dict[str, Any] = {}

    async def post(self, url: str, *, json: dict, headers: dict, timeout: Any) -> _StubResponse:
        self.captured = {"url": url, "json": json, "headers": headers}
        return _StubResponse(self._body, self._status)


def _sonar_body() -> dict[str, Any]:
    return {
        "citations": [
            "https://sec.gov/filing",  # duplicate of an annotation — kept once
            "https://www.moneycontrol.com/story",  # annotation-missed url — still gathered
        ],
        "choices": [
            {
                "message": {
                    "content": "# Brief\n\nFindings with [1] markers.",
                    "annotations": [
                        {
                            "type": "url_citation",
                            "url_citation": {
                                "url": "https://sec.gov/filing",
                                "title": "10-K",
                                "content": "Revenue grew 12%...",
                            },
                        }
                    ],
                }
            }
        ],
    }


def test_research_maps_to_brief_with_merged_deduped_sources() -> None:
    client = _StubClient(_sonar_body())
    backend = OpenRouterSonarBackend("sk-or-test", client=client)  # type: ignore[arg-type]
    brief = _run(backend.research("tata motors outlook"))

    assert isinstance(brief, ResearchBrief)
    assert brief.markdown.startswith("# Brief")
    assert brief.mode == "deep"
    urls = [s.url for s in brief.sources]
    # Annotation-normalized source first (the normalize_openai path), then the
    # pass-through citations[] url the annotations missed — deduped by url.
    assert urls == ["https://sec.gov/filing", "https://www.moneycontrol.com/story"]
    assert brief.source_count == 2


def test_sources_carry_openrouter_lane_provenance() -> None:
    client = _StubClient(_sonar_body())
    backend = OpenRouterSonarBackend("sk-or-test", client=client)  # type: ignore[arg-type]
    brief = _run(backend.research("q"))
    assert all(PROVENANCE_NOTE in (s.domain or "") for s in brief.sources)
    # The annotation's excerpt rode through the normalize_openai path.
    assert brief.sources[0].title == "10-K"
    # www. is stripped for the host label.
    assert brief.sources[1].domain is not None
    assert brief.sources[1].domain.startswith("moneycontrol.com")


def test_cost_snapshot_is_flagged_estimate() -> None:
    client = _StubClient(_sonar_body())
    backend = OpenRouterSonarBackend("sk-or-test", client=client)  # type: ignore[arg-type]
    brief = _run(backend.research("q"))
    assert brief.cost["estimate"] is True
    assert brief.cost["provider"] == PROVENANCE_NOTE
    assert 0.20 <= brief.cost["spend_usd"] <= 0.40
    assert brief.cost["tokens"] is None and brief.cost["steps"] is None


def test_request_carries_model_and_bearer_key_only() -> None:
    client = _StubClient(_sonar_body())
    backend = OpenRouterSonarBackend("sk-or-test", model="sonar-pro", client=client)  # type: ignore[arg-type]
    _run(backend.research("q"))
    assert client.captured["url"] == sonar.OPENROUTER_CHAT_URL
    assert client.captured["json"]["model"] == "perplexity/sonar-pro"
    assert client.captured["headers"]["Authorization"] == "Bearer sk-or-test"


def test_missing_key_raises_human_error() -> None:
    backend = OpenRouterSonarBackend(None)
    with pytest.raises(SearchError) as excinfo:
        _run(backend.research("q"))
    assert "OpenRouter" in str(excinfo.value)


def test_empty_query_is_rejected() -> None:
    backend = OpenRouterSonarBackend("sk-or-test")
    with pytest.raises(SearchError):
        _run(backend.research("   "))


def test_empty_brief_is_an_error_not_a_blank_render() -> None:
    client = _StubClient({"choices": [{"message": {"content": ""}}]})
    backend = OpenRouterSonarBackend("sk-or-test", client=client)  # type: ignore[arg-type]
    with pytest.raises(SearchError) as excinfo:
        _run(backend.research("q"))
    assert "empty" in str(excinfo.value)


@pytest.mark.parametrize(
    ("status", "needle"),
    [(401, "key"), (402, "credits"), (429, "rate limit"), (503, "unavailable")],
)
def test_http_errors_become_human_messages_without_the_key(status: int, needle: str) -> None:
    client = _StubClient({}, status=status)
    backend = OpenRouterSonarBackend("sk-or-supersecret", client=client)  # type: ignore[arg-type]
    with pytest.raises(SearchError) as excinfo:
        _run(backend.research("q"))
    message = str(excinfo.value)
    assert needle in message
    assert "sk-or-supersecret" not in message


# --- run_deep_brief dispatch -------------------------------------------------------


class _FakeSonarBackend:
    last_init: dict[str, Any] = {}

    def __init__(self, api_key: str | None, *, model: str | None = None, client=None) -> None:  # noqa: ANN001
        _FakeSonarBackend.last_init = {"api_key": api_key, "model": model}

    async def research(self, query: str, *, region: str | None = None) -> ResearchBrief:
        return ResearchBrief(
            query=query,
            symbol="",
            mode="deep",
            markdown="# fake",
            sources=[],
            source_count=0,
            cost={"estimate": True},
            web_available=True,
            note=None,
        )


def test_run_deep_brief_dispatches_sonar_with_explicit_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services.agent_tools.deep_research import run_deep_brief

    monkeypatch.setattr(sonar, "OpenRouterSonarBackend", _FakeSonarBackend)
    out = _run(run_deep_brief("q", backend="sonar", api_key="sk-or-test"))
    assert out["ok"] is True and out["backend"] == "sonar"
    assert out["markdown"] == "# fake"
    assert "cost_estimate_usd" in out
    assert _FakeSonarBackend.last_init["api_key"] == "sk-or-test"


def test_run_deep_brief_sonar_uses_request_contextvar_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services.agent_tools.deep_research import run_deep_brief

    monkeypatch.setattr(sonar, "OpenRouterSonarBackend", _FakeSonarBackend)
    token = config.set_request_openrouter_search_key("sk-or-from-header")
    try:
        out = _run(run_deep_brief("q", backend="sonar"))
    finally:
        config.reset_request_openrouter_search_key(token)
    assert out["ok"] is True
    assert _FakeSonarBackend.last_init["api_key"] == "sk-or-from-header"


def test_run_deep_brief_sonar_without_key_is_honest(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.agent_tools.deep_research import run_deep_brief

    out = _run(run_deep_brief("q", backend="sonar"))
    assert out["ok"] is False
    assert "OpenRouter" in out["message"]


def test_settings_contextvar_resolves_sonar(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.agent_tools.deep_research import run_deep_brief

    monkeypatch.setattr(sonar, "OpenRouterSonarBackend", _FakeSonarBackend)
    backend_token = config.set_request_deep_research("sonar")
    key_token = config.set_request_openrouter_search_key("sk-or-settings")
    try:
        out = _run(run_deep_brief("q"))
    finally:
        config.reset_request_openrouter_search_key(key_token)
        config._deep_research_ctx.reset(backend_token)  # type: ignore[arg-type]
    assert out["ok"] is True and out["backend"] == "sonar"
