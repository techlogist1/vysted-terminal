"""Tongyi-DeepResearch remote backend tests (Track C).

The model resolver is probe-gated against OpenRouter; every probe here is served
by an ``httpx.MockTransport`` through the ``client`` seam, so no live call is made.
The load-bearing case: the Tongyi slug is unreachable today (0 endpoints) → the
resolver falls back to the live Qwen-A3B analog (FINDINGS §2.4).
"""

from __future__ import annotations

import httpx
import pytest

from services.research import tongyi


def _mock(handler) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


def test_is_configured_requires_a_key() -> None:
    assert tongyi.is_configured("sk-or-123") is True
    assert tongyi.is_configured(" ") is False
    assert tongyi.is_configured(None) is False


def test_estimate_cost_is_a_small_positive_band() -> None:
    cost = tongyi.estimate_cost_usd("what is NVIDIA's data-center outlook?")
    assert 0 < cost <= 0.15


@pytest.mark.asyncio
async def test_resolve_uses_tongyi_when_endpoints_are_live() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        assert tongyi.TONGYI_SLUG in request.url.path
        return httpx.Response(200, json={"data": {"endpoints": [{"name": "alibaba"}]}})

    async with httpx.AsyncClient(transport=_mock(_handler)) as client:
        model = await tongyi.resolve_model("sk-or", client=client)
    assert model == tongyi.TONGYI_SLUG


@pytest.mark.asyncio
async def test_resolve_falls_back_when_tongyi_has_zero_endpoints() -> None:
    # The real OpenRouter state today: listed but unrouted (empty endpoints).
    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"endpoints": []}})

    async with httpx.AsyncClient(transport=_mock(_handler)) as client:
        model = await tongyi.resolve_model("sk-or", client=client)
    assert model == tongyi.FALLBACK_SLUGS[0]


@pytest.mark.asyncio
async def test_resolve_falls_back_on_probe_error() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network down")

    async with httpx.AsyncClient(transport=_mock(_handler)) as client:
        model = await tongyi.resolve_model("sk-or", client=client)
    assert model == tongyi.FALLBACK_SLUGS[0]


@pytest.mark.asyncio
async def test_resolve_falls_back_on_non_2xx() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    async with httpx.AsyncClient(transport=_mock(_handler)) as client:
        model = await tongyi.resolve_model("sk-or", client=client)
    assert model == tongyi.FALLBACK_SLUGS[0]


# ---------------------------------------------------------------------------
# deep_research handler — backend="tongyi" dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_tongyi_needs_an_openrouter_key(monkeypatch: pytest.MonkeyPatch) -> None:
    import config
    from services.agent_tools import deep_research

    # No active creds and no passed key → honest "needs an OpenRouter key".
    monkeypatch.setattr(config, "get_llm_creds", lambda: None)
    out = await deep_research._run_tongyi("research NVDA", None, 2, 60)
    assert out["ok"] is False
    assert "OpenRouter" in out["message"]


@pytest.mark.asyncio
async def test_run_tongyi_reuses_openrouter_creds_and_runs_the_deep_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import config
    from services.agent_tools import deep_research
    from services.research import iter as iter_research

    monkeypatch.setattr(
        config, "get_llm_creds", lambda: ("openrouter", "openai/gpt-4o-mini", "sk-or-key")
    )
    monkeypatch.setattr(config, "get_region", lambda: "US")
    monkeypatch.setattr(config, "get_step_sink", lambda: None)

    async def _fake_resolve(_key: str, *, client=None) -> str:  # noqa: ANN001
        return "qwen/qwen3-30b-a3b-thinking-2507"

    monkeypatch.setattr(tongyi, "resolve_model", _fake_resolve)

    captured: dict[str, object] = {}

    class _Brief:
        def to_dict(self) -> dict[str, object]:
            return {"markdown": "the brief", "sources": [], "steps": []}

    async def _fake_loop(query, **kwargs):  # noqa: ANN001, ANN003
        captured["query"] = query
        captured["llm_call"] = kwargs.get("llm_call")
        return _Brief()

    # tongyi now runs the IterResearch loop by default (the upgraded path).
    monkeypatch.setattr(iter_research, "run_iter_research", _fake_loop)

    out = await deep_research._run_tongyi("research NVDA", None, 2, 60)
    assert out["ok"] is True
    assert out["backend"] == "tongyi"
    assert out["model"] == "qwen/qwen3-30b-a3b-thinking-2507"
    assert "Tongyi" in out["provenance"]
    assert out["cost_estimate_usd"] > 0
    assert captured["query"] == "research NVDA"
    assert callable(captured["llm_call"])


@pytest.mark.asyncio
async def test_run_tongyi_emits_honest_engine_fallback_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the Tongyi slug isn't routing, the live trace says so honestly."""
    import config
    from services.agent_tools import deep_research
    from services.research import iter as iter_research
    from services.research.models import ResearchStep

    monkeypatch.setattr(config, "get_llm_creds", lambda: ("openrouter", "x", "sk-or-key"))
    monkeypatch.setattr(config, "get_region", lambda: "US")

    streamed: list[object] = []
    monkeypatch.setattr(config, "get_step_sink", lambda: streamed.append)

    async def _fake_resolve(_key: str, *, client=None) -> str:  # noqa: ANN001 — fell back
        return tongyi.FALLBACK_SLUGS[0]

    monkeypatch.setattr(tongyi, "resolve_model", _fake_resolve)

    class _Brief:
        def to_dict(self) -> dict[str, object]:
            return {"markdown": "b", "sources": [], "steps": []}

    async def _fake_loop(query, **kwargs):  # noqa: ANN001, ANN003, ARG001
        return _Brief()

    monkeypatch.setattr(iter_research, "run_iter_research", _fake_loop)

    await deep_research._run_tongyi("research NVDA", "sk-or-key", 2, 60)

    engine = [s for s in streamed if isinstance(s, ResearchStep) and s.kind == "engine"]
    assert engine, "expected an honest engine step"
    detail = engine[0].detail
    assert tongyi.FALLBACK_SLUGS[0] in detail
    assert "fallback" in detail.lower()
    assert tongyi.TONGYI_SLUG in detail  # names the slug that isn't routing yet
    assert "isn't routing" in detail
