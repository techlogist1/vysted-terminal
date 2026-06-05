"""Pass B (Pillar B) — the ONE ``research`` agent-tool handler + oneshot.

After the R4 research collapse (FR-115 / SC-028) there is a SINGLE ``research``
handler with an INTERNAL ``depth`` arg (``quick`` | ``deep`` | ``heavy``):
``quick`` runs the fast gather, ``deep``/``heavy`` run the ONE deep loop via the
internal ``deep_research.run_deep_brief`` engine. There is no ``deep_research``
tool and no user/model ``mode`` knob.

The research service (``services.research.fast`` / ``.deep`` / ``.iter`` /
``.perplexity``) is built in parallel; these tests inject lightweight fake modules
into ``sys.modules`` so the handler's lazy imports resolve to the fakes. Every
seam the handler touches — ``gather_fast``, ``run_iter_research`` /
``run_heavy_research`` / ``run_deep_research``, ``config.get_llm_creds``,
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
    """Inject fake ``services.research.{fast,deep,iter,perplexity}`` modules.

    Returns a namespace exposing the fakes' record/override hooks so each test
    can assert call args and steer the return value.
    """
    parent = types.ModuleType("services.research")
    fast_mod = types.ModuleType("services.research.fast")
    deep_mod = types.ModuleType("services.research.deep")
    iter_mod = types.ModuleType("services.research.iter")
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
        # The single-pass loop is the NAMED internal fallback only — it should NOT
        # be reached on the normal deep path (iter never raises). A test asserts so.
        calls["run_deep_research"] = {"query": query}
        return _FakeBrief({"summary": "single-pass brief", "citations": [{"url": "https://x"}]})

    async def _run_iter_research(
        query,  # noqa: ANN001
        *,
        region,  # noqa: ANN001
        tool_call,  # noqa: ANN001
        llm_call,  # noqa: ANN001
        budget,  # noqa: ANN001
        on_step=None,  # noqa: ANN001
        max_researchers=3,  # noqa: ANN001
    ):
        calls["run_iter_research"] = {
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
            on_step("distill")
            on_step("synthesize")
        return _FakeBrief({"summary": "iter brief", "citations": [{"url": "https://x"}]})

    async def _run_heavy_research(
        query,  # noqa: ANN001
        *,
        angles=3,  # noqa: ANN001
        region,  # noqa: ANN001
        tool_call,  # noqa: ANN001
        llm_call,  # noqa: ANN001
        budget,  # noqa: ANN001
        on_step=None,  # noqa: ANN001
        max_researchers=3,  # noqa: ANN001
    ):
        calls["run_heavy_research"] = {
            "query": query,
            "angles": angles,
            "budget": budget,
            "on_step": on_step,
            "max_researchers": max_researchers,
        }
        return _FakeBrief({"summary": "heavy brief", "citations": [{"url": "https://x"}]})

    fast_mod.gather_fast = _gather_fast  # type: ignore[attr-defined]
    deep_mod.run_deep_research = _run_deep_research  # type: ignore[attr-defined]
    deep_mod.ResearchBrief = _FakeBrief  # type: ignore[attr-defined]
    iter_mod.run_iter_research = _run_iter_research  # type: ignore[attr-defined]
    iter_mod.run_heavy_research = _run_heavy_research  # type: ignore[attr-defined]

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

    # Keep the REAL ``services.research.models`` reachable under the shadowed
    # parent — the deep engine's honest "engine" step (``_emit_backend_step``)
    # imports ``ResearchStep`` from it, and it carries no heavy deps.
    from services.research import models as models_mod

    monkeypatch.setitem(sys.modules, "services.research", parent)
    monkeypatch.setitem(sys.modules, "services.research.fast", fast_mod)
    monkeypatch.setitem(sys.modules, "services.research.deep", deep_mod)
    monkeypatch.setitem(sys.modules, "services.research.iter", iter_mod)
    monkeypatch.setitem(sys.modules, "services.research.perplexity", perplexity_mod)
    monkeypatch.setitem(sys.modules, "services.research.models", models_mod)
    # Make the submodules reachable as attributes of the parent (belt + braces).
    parent.fast = fast_mod  # type: ignore[attr-defined]
    parent.deep = deep_mod  # type: ignore[attr-defined]
    parent.iter = iter_mod  # type: ignore[attr-defined]
    parent.perplexity = perplexity_mod  # type: ignore[attr-defined]
    parent.models = models_mod  # type: ignore[attr-defined]

    return types.SimpleNamespace(calls=calls, perplexity_state=perplexity_state)


# ---------------------------------------------------------------------------
# research handler — quick depth (the default, fast gather)
# ---------------------------------------------------------------------------


def test_research_missing_query_is_rejected(research_modules) -> None:  # noqa: ARG001
    out = _run(_research({}))
    assert out["ok"] is False
    assert "query" in out["message"].lower()


def test_research_quick_returns_the_bundle(
    research_modules, monkeypatch: pytest.MonkeyPatch
) -> None:
    from services import agent_tools

    sentinel = object()
    monkeypatch.setattr(agent_tools, "invoke_tool", sentinel)
    monkeypatch.setattr(config, "get_region", lambda: "IN")

    # Track A: the handler forwards the runtime's live step-sink to the loop.
    def _sink(_step) -> None:  # noqa: ANN001
        return None

    token = config.set_step_sink(_sink)
    try:
        # No depth -> defaults to quick (the fast gather).
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
    # …and the live step-sink (Track A).
    assert call["on_step"] is _sink
    # No deep loop touched on the quick path.
    assert "run_iter_research" not in research_modules.calls
    assert "run_heavy_research" not in research_modules.calls


# ---------------------------------------------------------------------------
# research handler — deep depth (the ONE deep loop, native backend)
# ---------------------------------------------------------------------------


def test_research_deep_no_creds_is_human_message(
    research_modules, monkeypatch: pytest.MonkeyPatch
) -> None:  # noqa: ARG001
    monkeypatch.setattr(config, "get_llm_creds", lambda: None)
    out = _run(_research({"query": "rate cuts", "depth": "deep"}))
    assert out["ok"] is False
    assert out["message"] == "No model configured for deep research."


def test_research_deep_runs_the_iter_loop_and_returns_brief(
    research_modules, monkeypatch: pytest.MonkeyPatch
) -> None:
    from services import agent_tools

    monkeypatch.setattr(config, "get_llm_creds", lambda: ("anthropic", "claude-x", "sk-test"))
    monkeypatch.setattr(config, "get_region", lambda: "US")
    monkeypatch.setattr(config, "get_deep_research_backend", lambda: None)
    seam = object()
    monkeypatch.setattr(agent_tools, "invoke_tool", seam)

    streamed: list[Any] = []
    sink = streamed.append
    token = config.set_step_sink(sink)
    try:
        out = _run(_research({"query": "rate cuts", "depth": "deep", "rounds": 2}))
    finally:
        config.reset_step_sink(token)

    assert out["ok"] is True
    assert out["backend"] == "native"
    # depth='deep' runs the IterResearch loop (the ONE deep loop), reported as "deep".
    assert out["mode"] == "deep"
    assert out["summary"] == "iter brief"
    call = research_modules.calls["run_iter_research"]
    assert call["query"] == "rate cuts"
    assert call["region"] == "US"
    assert call["tool_call"] is seam
    assert call["max_researchers"] == 3
    from services.budget_guard import BudgetGuard

    assert isinstance(call["budget"], BudgetGuard)
    assert callable(call["llm_call"])
    assert call["on_step"] is sink
    # The handler emits an honest "engine" step first (naming IterResearch).
    from services.research.models import ResearchStep

    assert isinstance(streamed[0], ResearchStep)
    assert streamed[0].kind == "engine"
    assert "anthropic/claude-x" in streamed[0].detail
    assert "IterResearch" in streamed[0].detail
    assert streamed[1:] == ["plan", "distill", "synthesize"]


def test_research_deep_is_the_one_loop_single_pass_is_not_reached(
    research_modules, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SC-028 / S-9: the normal deep path runs the iter loop ONLY — the single-pass
    ``run_deep_research`` is the internal fallback and never runs when iter
    succeeds."""
    monkeypatch.setattr(config, "get_llm_creds", lambda: ("anthropic", "claude-x", "sk-test"))
    monkeypatch.setattr(config, "get_deep_research_backend", lambda: None)
    out = _run(_research({"query": "q", "depth": "deep"}))
    assert out["ok"] is True
    assert "run_iter_research" in research_modules.calls
    assert "run_deep_research" not in research_modules.calls


def test_research_deep_clamps_rounds_and_wall(
    research_modules, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config, "get_llm_creds", lambda: ("anthropic", "claude-x", "sk-test"))
    monkeypatch.setattr(config, "get_deep_research_backend", lambda: None)
    # Out-of-range rounds/wall must not raise; the engine clamps them.
    out = _run(_research({"query": "q", "depth": "deep", "rounds": 99, "wall_seconds": 5}))
    assert out["ok"] is True
    assert research_modules.calls["run_iter_research"]["query"] == "q"


def test_research_heavy_runs_the_panel(research_modules, monkeypatch: pytest.MonkeyPatch) -> None:
    """depth='heavy' routes to the expert-panel Heavy loop (angles=3)."""
    monkeypatch.setattr(config, "get_llm_creds", lambda: ("anthropic", "claude-x", "sk-test"))
    monkeypatch.setattr(config, "get_deep_research_backend", lambda: None)
    out = _run(_research({"query": "thesis", "depth": "heavy"}))
    assert out["ok"] is True
    assert out["mode"] == "heavy"
    assert out["summary"] == "heavy brief"
    call = research_modules.calls["run_heavy_research"]
    assert call["query"] == "thesis"
    assert call["angles"] == 3


def test_research_deep_llm_call_proxies_oneshot(
    research_modules, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The injected llm_call must drive oneshot.complete with the active creds."""
    monkeypatch.setattr(config, "get_llm_creds", lambda: ("openai", "gpt-x", "sk-key"))
    monkeypatch.setattr(config, "get_deep_research_backend", lambda: None)
    captured: dict[str, Any] = {}

    async def _fake_complete(provider, model, api_key, messages, *, timeout=None):  # noqa: ANN001
        captured.update(
            {
                "provider": provider,
                "model": model,
                "api_key": api_key,
                "messages": messages,
                "timeout": timeout,
            }
        )
        return "joined-completion"

    monkeypatch.setattr(oneshot, "complete", _fake_complete)

    _run(_research({"query": "q", "depth": "deep"}))

    llm_call = research_modules.calls["run_iter_research"]["llm_call"]
    result = _run(llm_call([{"role": "user", "content": "hi"}]))
    assert result == "joined-completion"
    assert captured["provider"] == "openai"
    assert captured["model"] == "gpt-x"
    assert captured["api_key"] == "sk-key"
    assert captured["messages"] == [{"role": "user", "content": "hi"}]
    # The per-call wall-clock cap is wired (so one slow round can't run unbounded).
    assert isinstance(captured["timeout"], (int, float)) and captured["timeout"] > 0


# ---------------------------------------------------------------------------
# research handler — perplexity backend (opt-in-per-run, NEVER auto-run)
# ---------------------------------------------------------------------------


def test_research_perplexity_without_key_returns_optin_message(
    research_modules, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No Perplexity key configured -> is_configured False -> opt-in message.
    research_modules.perplexity_state["configured"] = False
    monkeypatch.setattr(config, "get_llm_creds", lambda: ("anthropic", "claude-x", "sk-test"))

    out = _run(_research({"query": "fed policy", "depth": "deep", "backend": "perplexity"}))

    assert out["ok"] is False
    assert "Perplexity deep research needs an API key" in out["message"]
    assert "opt-in" in out["message"]
    # NEVER auto-ran the backend.
    assert research_modules.perplexity_state["research_query"] is None


def test_research_perplexity_with_key_runs_backend(
    research_modules, monkeypatch: pytest.MonkeyPatch
) -> None:
    research_modules.perplexity_state["configured"] = True
    monkeypatch.setattr(config, "get_region", lambda: "US")

    out = _run(
        _research(
            {
                "query": "fed policy",
                "depth": "deep",
                "backend": "perplexity",
                "api_key": "pplx-123",
            }
        )
    )

    assert out["ok"] is True
    assert out["backend"] == "perplexity"
    assert out["summary"] == "perplexity brief"
    assert out["cost_estimate_usd"] == 0.42
    assert research_modules.perplexity_state["research_query"] == "fed policy"


def test_research_perplexity_never_selected_for_native_default(
    research_modules, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default backend is native — Perplexity is never auto-selected (SC-028)."""
    research_modules.perplexity_state["configured"] = True
    monkeypatch.setattr(config, "get_llm_creds", lambda: ("anthropic", "claude-x", "sk-test"))
    monkeypatch.setattr(config, "get_deep_research_backend", lambda: None)

    out = _run(_research({"query": "anything", "depth": "deep"}))  # no backend -> native

    assert out["backend"] == "native"
    # The paid backend was untouched.
    assert research_modules.perplexity_state["research_query"] is None


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
# registration — ONE research tool (FR-115); deep_research is NOT a tool
# ---------------------------------------------------------------------------


def test_research_tools_register() -> None:
    import services.agent_tools as agent_tools
    from services.agent_tools import research as research_mod

    research_mod.register()
    assert "research" in agent_tools.registered_tools()
    # The collapse removed the second tool: there is no ``deep_research`` handler.
    assert "deep_research" not in agent_tools.registered_tools()
