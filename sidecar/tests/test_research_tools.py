"""Pass B (Pillar B) — the research + deep_research agent-tool handlers + oneshot.

The research service (``services.research.fast`` / ``.deep`` / ``.perplexity``)
is built in parallel; these tests inject lightweight fake modules into
``sys.modules`` so the handlers' lazy imports resolve to the fakes. Every seam
the handlers touch — ``gather_fast``, ``run_deep_research``, ``config.get_llm_creds``,
``agent_tools.invoke_tool``, the Perplexity backend, and the LLM provider — is
faked; no test makes a live call.
"""

from __future__ import annotations

import asyncio
import sys
import types
from typing import Any

import pytest

import config
from services.agent_tools.deep_research import _deep_research
from services.agent_tools.research import _research
from services.llm import oneshot


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Fake research service modules (built in parallel — injected here)
# ---------------------------------------------------------------------------


class _FakeBrief:
    """Stand-in for ``services.research.deep.ResearchBrief`` with ``to_dict``."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def to_dict(self) -> dict[str, Any]:
        return dict(self._payload)


@pytest.fixture
def research_modules(monkeypatch: pytest.MonkeyPatch):
    """Inject fake ``services.research.{fast,deep,perplexity}`` modules.

    Returns a namespace exposing the fakes' record/override hooks so each test
    can assert call args and steer the return value.
    """
    parent = types.ModuleType("services.research")
    fast_mod = types.ModuleType("services.research.fast")
    deep_mod = types.ModuleType("services.research.deep")
    perplexity_mod = types.ModuleType("services.research.perplexity")

    calls: dict[str, Any] = {}

    async def _gather_fast(query, *, region, tool_call, on_step=None):  # noqa: ANN001
        calls["gather_fast"] = {
            "query": query,
            "region": region,
            "tool_call": tool_call,
            "on_step": on_step,
        }
        return {"ok": True, "query": query, "region": region, "bundle": ["news", "quote"]}

    async def _run_deep_research(
        query,  # noqa: ANN001
        *,
        region,  # noqa: ANN001
        tool_call,  # noqa: ANN001
        llm_call,  # noqa: ANN001
        budget,  # noqa: ANN001
        on_step=None,  # noqa: ANN001
        max_researchers=3,  # noqa: ANN001
    ):
        calls["run_deep_research"] = {
            "query": query,
            "region": region,
            "tool_call": tool_call,
            "llm_call": llm_call,
            "budget": budget,
            "on_step": on_step,
            "max_researchers": max_researchers,
        }
        if on_step is not None:
            on_step("plan")
            on_step("synthesize")
        return _FakeBrief({"summary": "deep brief", "citations": [{"url": "https://x"}]})

    fast_mod.gather_fast = _gather_fast  # type: ignore[attr-defined]
    deep_mod.run_deep_research = _run_deep_research  # type: ignore[attr-defined]
    deep_mod.ResearchBrief = _FakeBrief  # type: ignore[attr-defined]

    # Perplexity fake — default: NOT configured (no key).
    perplexity_state: dict[str, Any] = {"configured": False, "research_query": None}

    def _is_configured(api_key):  # noqa: ANN001
        return perplexity_state["configured"] and bool(api_key)

    def _estimate_cost_usd(query):  # noqa: ANN001
        return 0.42

    class _PerplexityDeepBackend:
        def __init__(self, api_key) -> None:  # noqa: ANN001
            self.api_key = api_key

        async def research(self, query, region="US"):  # noqa: ANN001
            perplexity_state["research_query"] = query
            return _FakeBrief({"summary": "perplexity brief", "citations": []})

    perplexity_mod.is_configured = _is_configured  # type: ignore[attr-defined]
    perplexity_mod.estimate_cost_usd = _estimate_cost_usd  # type: ignore[attr-defined]
    perplexity_mod.PerplexityDeepBackend = _PerplexityDeepBackend  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "services.research", parent)
    monkeypatch.setitem(sys.modules, "services.research.fast", fast_mod)
    monkeypatch.setitem(sys.modules, "services.research.deep", deep_mod)
    monkeypatch.setitem(sys.modules, "services.research.perplexity", perplexity_mod)
    # Make the submodules reachable as attributes of the parent (belt + braces).
    parent.fast = fast_mod  # type: ignore[attr-defined]
    parent.deep = deep_mod  # type: ignore[attr-defined]
    parent.perplexity = perplexity_mod  # type: ignore[attr-defined]

    return types.SimpleNamespace(calls=calls, perplexity_state=perplexity_state)


# ---------------------------------------------------------------------------
# research handler
# ---------------------------------------------------------------------------


def test_research_missing_query_is_rejected(research_modules) -> None:  # noqa: ARG001
    out = _run(_research({}))
    assert out["ok"] is False
    assert "query" in out["message"].lower()


def test_research_returns_the_bundle(research_modules, monkeypatch: pytest.MonkeyPatch) -> None:
    from services import agent_tools

    sentinel = object()
    monkeypatch.setattr(agent_tools, "invoke_tool", sentinel)
    monkeypatch.setattr(config, "get_region", lambda: "IN")

    # Track A: the handler forwards the runtime's live step-sink to the loop.
    def _sink(_step) -> None:  # noqa: ANN001
        return None

    token = config.set_step_sink(_sink)
    try:
        out = _run(_research({"query": "  nvidia earnings  "}))
    finally:
        config.reset_step_sink(token)

    assert out["ok"] is True
    assert out["bundle"] == ["news", "quote"]
    call = research_modules.calls["gather_fast"]
    assert call["query"] == "nvidia earnings"  # trimmed
    assert call["region"] == "IN"
    # The handler wires the real agent_tools.invoke_tool seam through.
    assert call["tool_call"] is sentinel
    # …and the live step-sink (Track A) — None when no sink is set.
    assert call["on_step"] is _sink


# ---------------------------------------------------------------------------
# deep_research handler — native backend
# ---------------------------------------------------------------------------


def test_deep_research_no_creds_is_human_message(
    research_modules, monkeypatch: pytest.MonkeyPatch
) -> None:  # noqa: ARG001
    monkeypatch.setattr(config, "get_llm_creds", lambda: None)
    out = _run(_deep_research({"query": "rate cuts"}))
    assert out["ok"] is False
    assert out["message"] == "No model configured for deep research."


def test_deep_research_native_runs_and_returns_brief(
    research_modules, monkeypatch: pytest.MonkeyPatch
) -> None:
    from services import agent_tools

    monkeypatch.setattr(config, "get_llm_creds", lambda: ("anthropic", "claude-x", "sk-test"))
    monkeypatch.setattr(config, "get_region", lambda: "US")
    seam = object()
    monkeypatch.setattr(agent_tools, "invoke_tool", seam)

    # Track A: the handler forwards the runtime's live step-sink as the loop's
    # on_step, so steps stream to the SSE consumer while the loop runs.
    streamed: list[Any] = []
    sink = streamed.append
    token = config.set_step_sink(sink)
    try:
        out = _run(_deep_research({"query": "rate cuts", "rounds": 2, "wall_seconds": 60}))
    finally:
        config.reset_step_sink(token)

    assert out["ok"] is True
    assert out["backend"] == "native"
    assert out["summary"] == "deep brief"
    call = research_modules.calls["run_deep_research"]
    assert call["query"] == "rate cuts"
    assert call["region"] == "US"
    assert call["tool_call"] is seam
    assert call["max_researchers"] == 3
    # A BudgetGuard was constructed and passed in.
    from services.budget_guard import BudgetGuard

    assert isinstance(call["budget"], BudgetGuard)
    # llm_call is an awaitable that proxies oneshot.complete.
    assert callable(call["llm_call"])
    # on_step IS the runtime sink, and the loop's steps streamed through it.
    assert call["on_step"] is sink
    # The handler emits an honest "engine" step first (which backend ran), then
    # the loop's own steps stream through the same sink.
    from services.research.models import ResearchStep

    assert isinstance(streamed[0], ResearchStep)
    assert streamed[0].kind == "engine"
    assert "anthropic/claude-x" in streamed[0].detail
    assert streamed[1:] == ["plan", "synthesize"]


def test_deep_research_clamps_rounds_and_wall(
    research_modules, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config, "get_llm_creds", lambda: ("anthropic", "claude-x", "sk-test"))
    # Out-of-range rounds/wall must not raise; the handler clamps them.
    out = _run(_deep_research({"query": "q", "rounds": 99, "wall_seconds": 5}))
    assert out["ok"] is True
    assert research_modules.calls["run_deep_research"]["query"] == "q"


def test_deep_research_native_llm_call_proxies_oneshot(
    research_modules, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The injected llm_call must drive oneshot.complete with the active creds."""
    monkeypatch.setattr(config, "get_llm_creds", lambda: ("openai", "gpt-x", "sk-key"))
    captured: dict[str, Any] = {}

    async def _fake_complete(provider, model, api_key, messages):  # noqa: ANN001
        captured.update(
            {"provider": provider, "model": model, "api_key": api_key, "messages": messages}
        )
        return "joined-completion"

    monkeypatch.setattr(oneshot, "complete", _fake_complete)

    _run(_deep_research({"query": "q"}))

    llm_call = research_modules.calls["run_deep_research"]["llm_call"]
    result = _run(llm_call([{"role": "user", "content": "hi"}]))
    assert result == "joined-completion"
    assert captured["provider"] == "openai"
    assert captured["model"] == "gpt-x"
    assert captured["api_key"] == "sk-key"
    assert captured["messages"] == [{"role": "user", "content": "hi"}]


# ---------------------------------------------------------------------------
# deep_research handler — perplexity backend (opt-in, never auto-run)
# ---------------------------------------------------------------------------


def test_deep_research_perplexity_without_key_returns_optin_message(
    research_modules, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No Perplexity key configured -> is_configured False -> opt-in message.
    research_modules.perplexity_state["configured"] = False
    monkeypatch.setattr(config, "get_llm_creds", lambda: ("anthropic", "claude-x", "sk-test"))

    out = _run(_deep_research({"query": "fed policy", "backend": "perplexity"}))

    assert out["ok"] is False
    assert "Perplexity deep research needs an API key" in out["message"]
    assert "opt-in" in out["message"]
    # NEVER auto-ran the backend.
    assert research_modules.perplexity_state["research_query"] is None


def test_deep_research_perplexity_with_key_runs_backend(
    research_modules, monkeypatch: pytest.MonkeyPatch
) -> None:
    research_modules.perplexity_state["configured"] = True
    monkeypatch.setattr(config, "get_region", lambda: "US")

    out = _run(
        _deep_research({"query": "fed policy", "backend": "perplexity", "api_key": "pplx-123"})
    )

    assert out["ok"] is True
    assert out["backend"] == "perplexity"
    assert out["summary"] == "perplexity brief"
    assert out["cost_estimate_usd"] == 0.42
    assert research_modules.perplexity_state["research_query"] == "fed policy"


def test_deep_research_perplexity_never_selected_for_native_default(
    research_modules, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default backend is native — Perplexity is never auto-selected."""
    research_modules.perplexity_state["configured"] = True
    monkeypatch.setattr(config, "get_llm_creds", lambda: ("anthropic", "claude-x", "sk-test"))

    out = _run(_deep_research({"query": "anything"}))  # no backend -> native

    assert out["backend"] == "native"
    # The paid backend was untouched.
    assert research_modules.perplexity_state["research_query"] is None


def test_deep_research_missing_query_is_rejected(research_modules) -> None:  # noqa: ARG001
    out = _run(_deep_research({"backend": "native"}))
    assert out["ok"] is False
    assert "query" in out["message"].lower()


# ---------------------------------------------------------------------------
# oneshot.complete
# ---------------------------------------------------------------------------


class _Event:
    def __init__(self, kind: str, text: str = "") -> None:
        self.kind = kind
        self.text = text


class _FakeAdapter:
    """Yields delta events then a done terminator; tool_use is ignored."""

    def __init__(self, events) -> None:
        self._events = events

    async def stream_chat(self, *, messages, model, api_key=None, **kwargs):  # noqa: ANN001, ARG002
        for ev in self._events:
            yield ev


def test_oneshot_joins_delta_text(monkeypatch: pytest.MonkeyPatch) -> None:
    events = [
        _Event("delta", "Hello"),
        _Event("tool_use"),  # ignored
        _Event("delta", ", world"),
        _Event("thinking", "(ignored)"),
        _Event("delta", "!"),
        _Event("done"),
        _Event("delta", "after-done"),  # never reached
    ]
    from services.llm import oneshot as oneshot_mod

    monkeypatch.setattr(oneshot_mod, "get_provider", lambda *a, **k: _FakeAdapter(events))

    out = _run(
        oneshot_mod.complete("anthropic", "claude-x", "sk", [{"role": "user", "content": "hi"}])
    )
    assert out == "Hello, world!"


def test_oneshot_error_event_stops_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    events = [_Event("delta", "partial"), _Event("error"), _Event("delta", "unreached")]
    from services.llm import oneshot as oneshot_mod

    monkeypatch.setattr(oneshot_mod, "get_provider", lambda *a, **k: _FakeAdapter(events))
    out = _run(oneshot_mod.complete("openai", "gpt-x", "sk", [{"role": "user", "content": "x"}]))
    assert out == "partial"


def test_oneshot_adapter_failure_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.llm import oneshot as oneshot_mod

    def _boom(*a, **k):  # noqa: ANN002, ANN003
        raise RuntimeError("adapter exploded")

    monkeypatch.setattr(oneshot_mod, "get_provider", _boom)
    out = _run(oneshot_mod.complete("anthropic", "m", "sk", [{"role": "user", "content": "x"}]))
    assert out == ""


# ---------------------------------------------------------------------------
# registration
# ---------------------------------------------------------------------------


def test_research_tools_register() -> None:
    import services.agent_tools as agent_tools
    from services.agent_tools import deep_research as deep_mod
    from services.agent_tools import research as research_mod

    research_mod.register()
    deep_mod.register()
    assert "research" in agent_tools.registered_tools()
    assert "deep_research" in agent_tools.registered_tools()
