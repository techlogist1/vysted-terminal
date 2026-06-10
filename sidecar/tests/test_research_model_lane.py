"""R9 Track A — the Tier B hosted research-model lane.

Pins the brief's rule 2 evidence: with ``tier_b`` configured, a research run on
ANY chat model routes to the per-stop research model, and the brief AND the
live steps carry ``backend="research-model:<model-id>"``. Also pins per-stop
model dispatch, the key boundary (honest stop, never a demotion), citation
mapping (annotations → sources, url-list fallback), the generous ULTRA wall,
and the ``research`` tool-boundary routing (tier_b owns ALL depth stops,
outranking model-passed backend args). Offline — the OpenRouter HTTP client is
stubbed; no test makes a live call and no test ever logs/echoes the key.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any

import httpx
import pytest

import config
from services.agent_tools import deep_research
from services.agent_tools.research import _research


def _run(coro):
    return asyncio.run(coro)


@contextlib.contextmanager
def _request(
    *,
    r7: str | None = None,
    legacy: str | None = None,
    openrouter_key: str | None = None,
    models: str | None = None,
    depth: str | None = None,
):
    """Set the per-request tier state; reset on exit (the middleware contract)."""
    r7_token = config.set_request_research_search_tier(r7)
    search_tokens = config.set_request_search(tier=legacy, searxng_url=None)
    or_token = config.set_request_openrouter_search_key(openrouter_key)
    models_token = config.set_request_research_models(models)
    depth_token = config.set_request_research_depth(depth)
    try:
        yield
    finally:
        config._research_depth_ctx.reset(depth_token)  # type: ignore[attr-defined]
        config.reset_request_research_models(models_token)
        config.reset_request_openrouter_search_key(or_token)
        config.reset_request_search(search_tokens)
        config.reset_request_research_search_tier(r7_token)


def _openrouter_body(
    markdown: str = "## Brief\nNVDA is fine. [1]",
    *,
    annotations: list[dict[str, Any]] | None = None,
    citations: list[str] | None = None,
) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant", "content": markdown}
    if annotations is not None:
        message["annotations"] = annotations
    body: dict[str, Any] = {"choices": [{"message": message}]}
    if citations is not None:
        body["citations"] = citations
    return body


class _StubAsyncClient:
    """Stand-in for ``httpx.AsyncClient`` capturing the request; canned reply."""

    last: dict[str, Any] = {}

    def __init__(self, *, timeout: Any = None) -> None:
        _StubAsyncClient.last["timeout"] = timeout

    async def __aenter__(self) -> _StubAsyncClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def post(self, url: str, *, json: Any = None, headers: Any = None) -> httpx.Response:
        _StubAsyncClient.last.update({"url": url, "payload": json, "headers": headers})
        status = _StubAsyncClient.last.get("status", 200)
        body = _StubAsyncClient.last.get("body", _openrouter_body())
        return httpx.Response(
            status_code=status,
            json=body,
            request=httpx.Request("POST", url),
        )


@pytest.fixture
def stub_openrouter(monkeypatch: pytest.MonkeyPatch) -> type[_StubAsyncClient]:
    _StubAsyncClient.last = {"status": 200, "body": _openrouter_body()}
    monkeypatch.setattr(httpx, "AsyncClient", _StubAsyncClient)
    return _StubAsyncClient


# --- run_research_model_brief — dispatch + evidence ---------------------------


def test_brief_and_steps_carry_research_model_backend_id(stub_openrouter) -> None:
    sunk: list[Any] = []
    token = config.set_step_sink(sunk.append)
    try:
        with _request(openrouter_key="sk-or-1"):
            out = _run(deep_research.run_research_model_brief("nvda outlook", depth="deep"))
    finally:
        config.reset_step_sink(token)

    assert out["ok"] is True
    assert out["backend"] == "research-model:perplexity/sonar-reasoning-pro"
    assert out["depth"] == "deep"
    # The live steps AND the brief's step trace carry the honest id.
    assert any("research-model:perplexity/sonar-reasoning-pro" in s.detail for s in sunk)
    assert any("research-model:" in s["detail"] for s in out["steps"])


def test_per_stop_default_models_dispatch(stub_openrouter) -> None:
    expected = {
        "normal": "perplexity/sonar",
        "deep": "perplexity/sonar-reasoning-pro",
        "ultra": "perplexity/sonar-deep-research",
    }
    for stop, model in expected.items():
        with _request(openrouter_key="sk-or-1"):
            out = _run(deep_research.run_research_model_brief("q", depth=stop))
        assert out["backend"] == f"research-model:{model}", stop
        assert stub_openrouter.last["payload"]["model"] == model, stop


def test_user_swapped_per_stop_model_wins(stub_openrouter) -> None:
    with _request(
        openrouter_key="sk-or-1",
        models="deep=openai/o4-mini-deep-research",
    ):
        out = _run(deep_research.run_research_model_brief("q", depth="deep"))
    assert out["backend"] == "research-model:openai/o4-mini-deep-research"
    assert stub_openrouter.last["payload"]["model"] == "openai/o4-mini-deep-research"


def test_legacy_depth_spellings_map_to_stops(stub_openrouter) -> None:
    with _request(openrouter_key="sk-or-1"):
        out = _run(deep_research.run_research_model_brief("q", depth="heavy"))
    assert out["depth"] == "ultra"
    assert out["backend"] == "research-model:perplexity/sonar-deep-research"


def test_ultra_wall_clock_is_generous(stub_openrouter) -> None:
    # The brief mandates >=360s for the ULTRA lane (sonar-deep-research can take
    # minutes); pin the constant AND the timeout actually handed to httpx.
    assert deep_research._RESEARCH_MODEL_WALL_SECONDS["ultra"] >= 360
    with _request(openrouter_key="sk-or-1"):
        _run(deep_research.run_research_model_brief("q", depth="ultra"))
    timeout = stub_openrouter.last["timeout"]
    assert isinstance(timeout, httpx.Timeout)
    assert (timeout.read or 0) >= 360


def test_needs_key_is_an_honest_stop_never_a_demotion(stub_openrouter) -> None:
    with _request():
        out = _run(deep_research.run_research_model_brief("q", depth="deep"))
    assert out["ok"] is False
    assert "OpenRouter" in out["message"]
    # No call was made and no other lane served the run.
    assert "payload" not in stub_openrouter.last or stub_openrouter.last.get("url") is None


def test_key_is_never_echoed_in_result(stub_openrouter) -> None:
    with _request(openrouter_key="sk-or-supersecret"):
        out = _run(deep_research.run_research_model_brief("q", depth="normal"))
    assert "sk-or-supersecret" not in json.dumps(out)


def test_citations_from_annotations_become_sources(stub_openrouter) -> None:
    stub_openrouter.last["body"] = _openrouter_body(
        annotations=[
            {
                "type": "url_citation",
                "url_citation": {"url": "https://nvidia.com/ir", "title": "NVDA IR"},
            }
        ],
        citations=["https://nvidia.com/ir", "https://reuters.com/nvda"],
    )
    with _request(openrouter_key="sk-or-1"):
        out = _run(deep_research.run_research_model_brief("q", depth="deep"))
    urls = [s["url"] for s in out["sources"]]
    # Annotation first; the url-list fallback adds only what annotations missed.
    assert urls == ["https://nvidia.com/ir", "https://reuters.com/nvda"]
    assert out["source_count"] == 2
    assert out["web_available"] is True
    assert all("OpenRouter" in (s["domain"] or "") for s in out["sources"])


def test_http_error_becomes_human_message(stub_openrouter) -> None:
    stub_openrouter.last["status"] = 402
    with _request(openrouter_key="sk-or-1"):
        out = _run(deep_research.run_research_model_brief("q", depth="deep"))
    assert out["ok"] is False
    assert "credits" in out["message"]
    assert "sk-or-1" not in out["message"]


def test_empty_brief_is_an_honest_failure(stub_openrouter) -> None:
    stub_openrouter.last["body"] = _openrouter_body(markdown="")
    with _request(openrouter_key="sk-or-1"):
        out = _run(deep_research.run_research_model_brief("q", depth="deep"))
    assert out["ok"] is False
    assert "empty" in out["message"]


def test_cost_is_a_flagged_estimate(stub_openrouter) -> None:
    with _request(openrouter_key="sk-or-1"):
        out = _run(deep_research.run_research_model_brief("q", depth="ultra"))
    assert out["cost"]["estimate"] is True
    assert out["cost"]["spend_usd"] > 0
    assert "OpenRouter" in out["cost"]["provider"]


# --- The research tool boundary — tier_b owns ALL depth stops ------------------


def test_tier_b_routes_normal_depth_to_the_research_model(stub_openrouter) -> None:
    # Rule 2: a tier_b run routes research to the research model even at the
    # NORMAL stop (where tier_a would run the no-LLM fast gather) and regardless
    # of the chat model (none is configured here at all).
    with _request(r7="tier_b", openrouter_key="sk-or-1"):
        out = _run(_research({"query": "nvda earnings"}))
    assert out["ok"] is True
    assert out["backend"] == "research-model:perplexity/sonar"
    assert out["depth"] == "normal"


def test_tier_b_routes_deep_slider_to_the_per_stop_model(stub_openrouter) -> None:
    # The composer slider (request default) is the floor; tier_b serves it on
    # the DEEP stop's model.
    with _request(r7="tier_b", openrouter_key="sk-or-1", depth="deep"):
        out = _run(_research({"query": "nvda earnings"}))
    assert out["backend"] == "research-model:perplexity/sonar-reasoning-pro"


def test_tier_b_outranks_model_passed_backend_arg(stub_openrouter) -> None:
    # A model filling backend="perplexity" must not divert a tier_b run off the
    # user's configured lane (the setting outranks tool-arg whims).
    with _request(r7="tier_b", openrouter_key="sk-or-1"):
        out = _run(_research({"query": "q", "depth": "deep", "backend": "perplexity"}))
    assert out["backend"] == "research-model:perplexity/sonar-reasoning-pro"


def test_tier_b_without_key_stops_honestly_at_the_tool_boundary(stub_openrouter) -> None:
    with _request(r7="tier_b"):
        out = _run(_research({"query": "q", "depth": "deep"}))
    assert out["ok"] is False
    assert "OpenRouter" in out["message"]


def test_legacy_t3_hosted_header_maps_to_tier_b(stub_openrouter) -> None:
    # Legacy explicit t3_hosted normalizes to tier_b at the header boundary.
    with _request(r7="t3_hosted", openrouter_key="sk-or-1"):
        out = _run(_research({"query": "q", "depth": "deep"}))
    assert out["ok"] is True
    assert out["backend"].startswith("research-model:")


def test_legacy_byok_exa_with_key_maps_to_tier_b(stub_openrouter) -> None:
    # The dead Exa-direct lane folds across the same key boundary: with an
    # OpenRouter key on the request it lands on tier_b.
    with _request(legacy="byok-exa", openrouter_key="sk-or-1"):
        out = _run(_research({"query": "q", "depth": "deep"}))
    assert out["ok"] is True
    assert out["backend"].startswith("research-model:")


def test_tier_a_keeps_the_builtin_deep_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    # tier_a never reaches OpenRouter from the research boundary — the built-in
    # engine serves deep/ultra (stubbed here; its own tests cover the loop).
    async def _fake_deep_brief(query: str, **kwargs: Any) -> dict[str, Any]:
        return {"ok": True, "backend": "native", "depth": kwargs.get("depth")}

    monkeypatch.setattr(deep_research, "run_deep_brief", _fake_deep_brief)
    with _request(r7="tier_a"):
        out = _run(_research({"query": "q", "depth": "deep"}))
    assert out["backend"] == "native"
