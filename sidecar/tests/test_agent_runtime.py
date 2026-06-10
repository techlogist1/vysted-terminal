"""Agent runtime tests — discovery, validation, invocation.

The first-party agent configs live in ``sidecar/agents/`` and are
loaded at import time; these tests reach in via :func:`agent_runtime.reload`
to exercise the discovery path against a controllable directory layout
(including malformed files and id collisions).

Provider streaming is mocked at the provider-factory boundary so the
invocation path is exercised end-to-end without a real network call.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from models.agent import AgentContextSnapshot, AgentInvocationRequest
from models.llm import (
    LLMDeltaEvent,
    LLMDoneEvent,
    LLMMessage,
    LLMThinkingEvent,
    LLMToolUseEvent,
    LLMUsage,
)
from services import agent_runtime


def _write_agent(directory: Path, agent_id: str, **overrides: Any) -> Path:
    """Write a minimal valid agent config under ``directory``."""
    payload: dict[str, Any] = {
        "id": agent_id,
        "name": agent_id.title(),
        "philosophy": f"{agent_id} philosophy",
        "systemPrompt": "x" * 60,
        "tools": ["price_data"],
        "defaultProvider": "anthropic",
    }
    payload.update(overrides)
    path = directory / f"{agent_id}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.fixture
def isolated_agents_dir(tmp_path: Path) -> Path:
    """Create a tmp agents directory containing the canonical schema."""
    # Copy the real schema so the validator has something to validate against.
    schema_src = Path(agent_runtime.SCHEMA_PATH)
    schema_dst = tmp_path / "_schema.json"
    schema_dst.write_text(schema_src.read_text(encoding="utf-8"), encoding="utf-8")
    # Point the runtime's SCHEMA_PATH at the tmp location so its loader picks
    # up the same schema in the isolated directory.
    return tmp_path


_REAL_AGENTS_DIR = Path(agent_runtime.__file__).resolve().parent.parent / "agents"
_REAL_SCHEMA_PATH = _REAL_AGENTS_DIR / "_schema.json"


def _restore_real_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the module-level constants back at the shipping directory."""
    monkeypatch.setattr(agent_runtime, "AGENTS_DIR", _REAL_AGENTS_DIR)
    monkeypatch.setattr(agent_runtime, "SCHEMA_PATH", _REAL_SCHEMA_PATH)
    agent_runtime.reload()


def test_first_party_roster_loads_all(tmp_path: Path) -> None:
    """The shipping ``sidecar/agents/`` directory loads all 13 first-party
    agents (12 personas + the Phase-10 copilot router)."""
    agent_runtime.reload()
    specs = agent_runtime.list_agents()
    ids = {spec.id for spec in specs}
    expected = {
        "copilot",  # Phase 10 — the default terminal-aware router/concierge
        "buffett",
        "graham",
        "lynch",
        "munger",
        "marks",
        "klarman",
        "dalio",
        "druckenmiller",
        "soros",
        "researcher",
        "portfolio_advisor",
        "strategy_critic",
    }
    assert ids == expected
    assert len(specs) == 13


def test_first_party_agents_have_substantive_prompts(tmp_path: Path) -> None:
    """Every first-party prompt should be at least 800 chars (~200 words)."""
    agent_runtime.reload()
    short = [s for s in agent_runtime.list_agents() if len(s.system_prompt) < 800]
    assert short == [], f"agents with thin prompts: {[s.id for s in short]}"


def test_reload_picks_up_new_agent(
    isolated_agents_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_agent(isolated_agents_dir, "alpha")
    _write_agent(isolated_agents_dir, "beta", defaultProvider="openai")
    monkeypatch.setattr(agent_runtime, "AGENTS_DIR", isolated_agents_dir)
    monkeypatch.setattr(agent_runtime, "SCHEMA_PATH", isolated_agents_dir / "_schema.json")
    agent_runtime.reload(isolated_agents_dir)
    try:
        specs = agent_runtime.list_agents()
        assert {s.id for s in specs} == {"alpha", "beta"}
        assert agent_runtime.get_agent("alpha") is not None
        assert agent_runtime.get_agent("beta") is not None
        assert agent_runtime.get_agent("missing") is None
    finally:
        # Restore the real registry for sibling tests in the same process.
        _restore_real_registry(monkeypatch)


def test_reload_skips_malformed_json(
    isolated_agents_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_agent(isolated_agents_dir, "good")
    (isolated_agents_dir / "bad.json").write_text("{ not valid json", encoding="utf-8")
    monkeypatch.setattr(agent_runtime, "AGENTS_DIR", isolated_agents_dir)
    monkeypatch.setattr(agent_runtime, "SCHEMA_PATH", isolated_agents_dir / "_schema.json")
    agent_runtime.reload(isolated_agents_dir)
    try:
        ids = {s.id for s in agent_runtime.list_agents()}
        assert ids == {"good"}
    finally:
        _restore_real_registry(monkeypatch)


def test_reload_skips_schema_violations(
    isolated_agents_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_agent(isolated_agents_dir, "ok")
    # systemPrompt too short, and tools is the wrong type.
    bad = {
        "id": "bad",
        "name": "Bad",
        "philosophy": "thin",
        "systemPrompt": "too short",
        "tools": "not-an-array",
        "defaultProvider": "anthropic",
    }
    (isolated_agents_dir / "bad.json").write_text(json.dumps(bad), encoding="utf-8")
    monkeypatch.setattr(agent_runtime, "AGENTS_DIR", isolated_agents_dir)
    monkeypatch.setattr(agent_runtime, "SCHEMA_PATH", isolated_agents_dir / "_schema.json")
    agent_runtime.reload(isolated_agents_dir)
    try:
        ids = {s.id for s in agent_runtime.list_agents()}
        assert ids == {"ok"}
    finally:
        _restore_real_registry(monkeypatch)


def test_first_party_ids_do_not_use_custom_prefix() -> None:
    """The ``custom:`` prefix is reserved for the Custom Agent Builder."""
    agent_runtime.reload()
    bad = [s.id for s in agent_runtime.list_agents() if s.id.startswith("custom:")]
    assert bad == []


# ---------------------------------------------------------------------------
# D21 — loader-level host-action parity (persona = voice only)
# ---------------------------------------------------------------------------


def test_first_party_effective_tools_superset_of_catalog_host_actions() -> None:
    """Every first-party agent's EFFECTIVE tools ⊇ the catalog's host-action ids
    (projected from ``kind == "host_action"``, never a hand-list) + ``research``
    — so no persona can claim "I can't open panels" while the copilot can."""
    from services.agent_tools import catalog

    agent_runtime.reload()
    host_actions = {c.id for c in catalog.CAPABILITY_CATALOG.values() if c.kind == "host_action"}
    assert host_actions, "catalog projects no host actions — the parity gate is vacuous"
    specs = agent_runtime.list_agents()
    assert specs, "no first-party agents loaded"
    for spec in specs:
        missing = host_actions - set(spec.tools)
        assert missing == set(), f"{spec.id}: effective tools missing host actions {missing}"
        assert "research" in spec.tools, f"{spec.id}: effective tools missing 'research'"
        # The union never duplicates an id the JSON already carried.
        assert len(spec.tools) == len(set(spec.tools)), f"{spec.id}: duplicate tool ids"


def test_grant_first_party_hands_is_idempotent_and_order_preserving() -> None:
    """The union keeps the persona's own tool order first and is idempotent."""
    agent_runtime.reload()
    spec = agent_runtime.get_agent("graham")
    assert spec is not None
    # The persona's JSON voice tools lead the effective list.
    assert spec.tools[:3] == ["price_data", "fundamentals", "news"]
    again = agent_runtime._grant_first_party_hands(spec)
    assert again.tools == spec.tools


def test_every_agent_json_tool_id_resolves_to_a_catalog_capability() -> None:
    """Every tool id written in every first-party agent JSON file resolves to a
    real internal catalog capability (0 unresolvable ids — the roster analogue
    of SC-006)."""
    from services.agent_tools.catalog import CAPABILITY_CATALOG

    json_files = sorted(p for p in agent_runtime.AGENTS_DIR.glob("*.json") if p.name[0] != "_")
    assert len(json_files) == 13  # the roster — keep in sync with the count tests
    for path in json_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        unresolved = [
            tid
            for tid in payload.get("tools", [])
            if tid not in CAPABILITY_CATALOG or not CAPABILITY_CATALOG[tid].internal
        ]
        assert unresolved == [], f"{path.name}: unresolvable tool ids {unresolved}"


def test_loader_appends_terminal_capabilities_preamble_to_every_first_party_prompt() -> None:
    """D21 deliverable 2: every first-party agent's EFFECTIVE system prompt
    carries the shared terminal-capabilities note (it knows its hands and the
    truthful applied-vs-proposed narration rule) — appended at the LOADER
    level, exactly once."""
    agent_runtime.reload()
    for spec in agent_runtime.list_agents():
        assert agent_runtime.TERMINAL_CAPABILITIES_PREAMBLE in spec.system_prompt, (
            f"{spec.id}: system prompt missing the terminal-capabilities preamble"
        )
        assert spec.system_prompt.count("## Terminal capabilities") == 1, (
            f"{spec.id}: the capabilities preamble must appear exactly once"
        )
        # The voice text still LEADS the prompt; the preamble is an appendix.
        assert not spec.system_prompt.startswith("## Terminal capabilities")


def test_capabilities_preamble_is_loader_level_not_in_the_json_files() -> None:
    """The persona JSON files keep their voice — the preamble never leaks onto
    disk (per-JSON edits are exactly what D21 forbids)."""
    for path in sorted(agent_runtime.AGENTS_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert "## Terminal capabilities" not in payload["systemPrompt"], (
            f"{path.name}: the loader-level preamble leaked into the JSON file"
        )
    # And graham's voice/specialty JSON is byte-level intact on the seams the
    # operator evidence named: voice tools only, no host actions on disk.
    graham = json.loads((agent_runtime.AGENTS_DIR / "graham.json").read_text(encoding="utf-8"))
    assert graham["tools"] == ["price_data", "fundamentals", "news"]
    assert "Mr. Market" in graham["systemPrompt"]


def test_custom_agents_are_not_unioned_with_host_actions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The D21 union is FIRST-PARTY only: a custom agent's tools stay exactly
    what its author selected (the builder allow-list still validates them)."""
    from config import DATA_DIR_ENV
    from models.custom_agent import CustomAgentCreate
    from services import agents_store

    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    agent_runtime.reload()
    agents_store.create_agent(
        CustomAgentCreate(
            id="custom:narrow-lens",
            name="Narrow Lens",
            philosophy="One tool only.",
            system_prompt="You are a narrow analytical lens grounded in price data only.",
            tools=["price_data"],
            default_provider="anthropic",
        )
    )
    spec = agent_runtime.get_agent("custom:narrow-lens")
    assert spec is not None
    assert spec.tools == ["price_data"]


# ---------------------------------------------------------------------------
# invoke_agent
# ---------------------------------------------------------------------------


class _FakeProvider:
    """Stand-in adapter that records the call and yields canned events."""

    def __init__(self) -> None:
        self.captured_messages: list[LLMMessage] | None = None
        self.captured_kwargs: dict[str, Any] | None = None

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        model: str,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        self.captured_messages = messages
        self.captured_kwargs = {"model": model, "api_key": api_key, **kwargs}
        yield LLMDeltaEvent(text="Hello")
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=10, output_tokens=2))


def _patch_provider(monkeypatch: pytest.MonkeyPatch, provider: _FakeProvider) -> None:
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_args, **_kw: provider)


@pytest.mark.asyncio
async def test_invoke_agent_composes_system_and_context(monkeypatch: pytest.MonkeyPatch) -> None:
    agent_runtime.reload()
    provider = _FakeProvider()
    _patch_provider(monkeypatch, provider)
    snapshot = AgentContextSnapshot(
        focused_source="chart-1",
        by_source={"chart-1": {"symbol": "AAPL", "timeframe": "1D"}},
        captured_at=12345,
    )
    events: list[Any] = []
    async for event in agent_runtime.invoke_agent(
        agent_id="buffett",
        prompt="is AAPL cheap?",
        context_snapshot=snapshot,
        api_key="sk-test",
    ):
        events.append(event)
    assert [e.kind for e in events] == ["delta", "done"]
    msgs = provider.captured_messages
    assert msgs is not None
    # 1 system (agent prompt) + 1 system (session/date preamble) + 1 system
    # (context preamble) + 1 user.
    assert [m.role for m in msgs] == ["system", "system", "system", "user"]
    assert "Current date:" in msgs[1].content  # session preamble anchors the clock
    assert "AAPL" in msgs[2].content  # context preamble carries the symbol
    assert msgs[3].content == "is AAPL cheap?"
    assert provider.captured_kwargs is not None
    assert provider.captured_kwargs["api_key"] == "sk-test"


def test_terminal_preamble_anchors_to_active_research_space() -> None:
    """The terminal preamble leads with the research-space symbol + its prior-
    research memory so the agent 'remembers' what it investigated there (S-19)."""
    preamble = agent_runtime._render_terminal_preamble(
        {
            "focusedSymbol": "NVDA",
            "charts": [{"symbol": "NVDA", "timeframe": "1D", "indicators": ["RSI"]}],
            "researchSpace": {
                "symbol": "NVDA",
                "memory": "Prior research on NVDA (2 questions). Recent: is NVDA cheap?",
                "priorTurns": 4,
            },
        }
    )
    assert "Research space: dedicated to NVDA" in preamble
    assert "Prior research memory:" in preamble
    assert "is NVDA cheap?" in preamble


def test_terminal_preamble_omits_research_space_when_absent() -> None:
    """A non-research cockpit renders no research-space anchor."""
    preamble = agent_runtime._render_terminal_preamble(
        {"focusedSymbol": "AAPL", "charts": [{"symbol": "AAPL", "timeframe": "1D"}]}
    )
    assert "Research space" not in preamble


@pytest.mark.asyncio
async def test_invoke_agent_emits_plan_for_compound_on_capable_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A compound request on a capable model surfaces a visible plan whose
    host-action steps are flagged ``staged`` and never include an order verb."""
    agent_runtime.reload()
    provider = _FakeProvider()
    _patch_provider(monkeypatch, provider)

    async def _fake_complete(prov, model, key, messages):  # noqa: ANN001, ANN202
        return (
            '[{"action":"set_chart_symbol","args":{"symbol":"AAPL"},"rationale":"chart AAPL"},'
            '{"action":"add_to_watchlist","args":{"symbol":"NVDA"},"rationale":"watch NVDA"}]'
        )

    monkeypatch.setattr(agent_runtime.oneshot, "complete", _fake_complete)

    events: list[Any] = []
    async for event in agent_runtime.invoke_agent(
        agent_id="copilot",
        prompt="open a chart of AAPL and add NVDA to my watchlist",
        provider="openai",
        model="gpt-4.1-mini",
        api_key="sk-test",
        mode="agent",
    ):
        events.append(event)

    plans = [e for e in events if e.kind == "agent_plan"]
    assert len(plans) == 1
    plan = plans[0]
    assert len(plan.steps) == 2
    assert all(s["staged"] for s in plan.steps)  # both host-actions pre-stage
    assert all(s["action"] != "propose_order" for s in plan.steps)  # §6.5: no order verb
    # The plan precedes the loop's own stream.
    kinds = [e.kind for e in events]
    assert kinds.index("agent_plan") < kinds.index("done")


@pytest.mark.asyncio
async def test_invoke_agent_no_plan_on_local_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """The unreliable local (ollama) path skips the plan surface entirely."""
    agent_runtime.reload()
    _patch_provider(monkeypatch, _FakeProvider())
    events: list[Any] = []
    async for event in agent_runtime.invoke_agent(
        agent_id="copilot",
        prompt="open a chart of AAPL and add NVDA to my watchlist",
        provider="ollama",
        mode="agent",
    ):
        events.append(event)
    assert [e for e in events if e.kind == "agent_plan"] == []


@pytest.mark.asyncio
async def test_invoke_agent_no_plan_for_simple_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-compound (single) request shows no plan surface."""
    agent_runtime.reload()
    _patch_provider(monkeypatch, _FakeProvider())
    events: list[Any] = []
    async for event in agent_runtime.invoke_agent(
        agent_id="copilot",
        prompt="what is AAPL's PE ratio?",
        provider="openai",
        model="gpt-4.1-mini",
        api_key="sk-test",
        mode="agent",
    ):
        events.append(event)
    assert [e for e in events if e.kind == "agent_plan"] == []


@pytest.mark.asyncio
async def test_invoke_agent_omits_context_when_none(monkeypatch: pytest.MonkeyPatch) -> None:
    agent_runtime.reload()
    provider = _FakeProvider()
    _patch_provider(monkeypatch, provider)
    async for _ in agent_runtime.invoke_agent(
        agent_id="buffett",
        prompt="hello",
        context_snapshot=None,
        api_key="sk-test",
    ):
        pass
    msgs = provider.captured_messages
    assert msgs is not None
    # System (agent prompt) + system (session/date preamble) + user when no panel
    # context is supplied — the session preamble always rides every turn.
    assert [m.role for m in msgs] == ["system", "system", "user"]
    assert "Current date:" in msgs[1].content


# ---------------------------------------------------------------------------
# Native web-search gate (WS5) — per-MODEL, not per-provider
# ---------------------------------------------------------------------------


def test_native_search_enabled_provider_level() -> None:
    # The five provider-level native providers always qualify (any model rides
    # the provider's own search), regardless of the per-model hint.
    for prov in ("anthropic", "openai", "gemini", "groq", "xai"):
        assert agent_runtime._native_search_enabled(prov, None) is True
        assert agent_runtime._native_search_enabled(prov, "none") is True


def test_native_search_enabled_openrouter_is_per_model() -> None:
    # OpenRouter is gated on the resolved model's web_search capability.
    assert agent_runtime._native_search_enabled("openrouter", "native") is True
    assert agent_runtime._native_search_enabled("openrouter", "plugin") is False
    assert agent_runtime._native_search_enabled("openrouter", "none") is False
    assert agent_runtime._native_search_enabled("openrouter", None) is False


def test_native_search_enabled_unknown_provider() -> None:
    # deepseek/ollama have no native search rung at all.
    assert agent_runtime._native_search_enabled("deepseek", "native") is False
    assert agent_runtime._native_search_enabled("ollama", None) is False


@pytest.mark.asyncio
async def test_invoke_openrouter_native_model_rides_native_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # An OpenRouter model marked web_search=="native" enables the provider's
    # server-side search AND withholds the local web_search tool (no double-run).
    agent_runtime.reload()
    provider = _FakeProvider()
    _patch_provider(monkeypatch, provider)
    async for _ in agent_runtime.invoke_agent(
        agent_id="copilot",
        prompt="what is the latest market news?",
        provider="openrouter",
        model="anthropic/claude-opus-4-8",
        api_key="sk-test",
        mode="ask",
        options={"modelWebSearch": "native"},
    ):
        pass
    kwargs = provider.captured_kwargs
    assert kwargs is not None
    assert kwargs.get("web_search") is True
    assert kwargs.get("web_search_max_uses") == agent_runtime._WEB_SEARCH_CAP
    # The local web_search tool is withheld so search isn't double-run.
    assert "web_search" not in (kwargs.get("tool_ids") or [])
    # The per-model hint is consumed, never forwarded to the adapter.
    assert "modelWebSearch" not in kwargs


@pytest.mark.asyncio
async def test_invoke_tier_b_suppresses_native_search_entirely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # R9 rule 3: tier_b ignores chat-model native search ENTIRELY — the hosted
    # research model owns research, and the local web_search tool stays so plain
    # retrieval serves locally (never a double-run / double-bill). Pinned for
    # the explicit tier_b id AND the legacy t3_hosted spelling that folds in.
    import config

    for tier in ("tier_b", "t3_hosted"):
        agent_runtime.reload()
        provider = _FakeProvider()
        _patch_provider(monkeypatch, provider)
        token = config.set_request_research_search_tier(tier)
        try:
            async for _ in agent_runtime.invoke_agent(
                agent_id="copilot",
                prompt="what is the latest market news?",
                provider="openrouter",
                model="anthropic/claude-opus-4-8",
                api_key="sk-test",
                mode="ask",
                options={"modelWebSearch": "native"},
            ):
                pass
        finally:
            config.reset_request_research_search_tier(token)
        kwargs = provider.captured_kwargs
        assert kwargs is not None
        assert kwargs.get("web_search") is None, tier
        assert "web_search" in (kwargs.get("tool_ids") or []), tier


@pytest.mark.asyncio
async def test_invoke_tier_a_compounds_native_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # R9 rule 3: on tier_a a native-capable model RIDES its own search (it
    # compounds with the local retrieval lane — Team B cross-verifies between
    # the channels). The explicit tier_a selection must not suppress it (the
    # R8 t2-suppression semantics are deliberately retired with the t2 tier).
    import config

    agent_runtime.reload()
    provider = _FakeProvider()
    _patch_provider(monkeypatch, provider)
    token = config.set_request_research_search_tier("tier_a")
    try:
        async for _ in agent_runtime.invoke_agent(
            agent_id="copilot",
            prompt="what is the latest market news?",
            provider="openai",
            model="gpt-4.1-mini",
            api_key="sk-test",
            mode="ask",
        ):
            pass
    finally:
        config.reset_request_research_search_tier(token)
    kwargs = provider.captured_kwargs
    assert kwargs is not None
    assert kwargs.get("web_search") is True
    assert "web_search" not in (kwargs.get("tool_ids") or [])


@pytest.mark.asyncio
async def test_depth_is_invisible_to_non_research_llm_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # R9 rule 4 (depth-cost parity): the composer depth ContextVar is readable
    # ONLY by research tools. A non-research turn (e.g. an arrange-layout ask)
    # must produce a BYTE-IDENTICAL LLM request — system prompt, tools schema,
    # messages, every adapter kwarg — at normal vs ultra. Depth must never
    # inflate the cost of a turn that does no research.
    async def _request_bytes(depth: str) -> bytes:
        agent_runtime.reload()
        provider = _FakeProvider()
        _patch_provider(monkeypatch, provider)
        async for _ in agent_runtime.invoke_agent(
            agent_id="copilot",
            prompt="arrange my layout for chart analysis",
            provider="openai",
            model="gpt-4.1-mini",
            api_key="sk-test",
            mode="ask",
            options={"research_depth": depth},
        ):
            pass
        assert provider.captured_messages is not None
        assert provider.captured_kwargs is not None
        return json.dumps(
            {
                "messages": [m.model_dump() for m in provider.captured_messages],
                "kwargs": provider.captured_kwargs,
            },
            sort_keys=True,
            default=str,
        ).encode()

    assert await _request_bytes("normal") == await _request_bytes("ultra")


@pytest.mark.asyncio
async def test_invoke_openrouter_none_model_keeps_local_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # An OpenRouter model with no native search keeps the local web_search tool
    # (the FR-082 fallback) and does NOT enable native search.
    agent_runtime.reload()
    provider = _FakeProvider()
    _patch_provider(monkeypatch, provider)
    async for _ in agent_runtime.invoke_agent(
        agent_id="copilot",
        prompt="what is the latest market news?",
        provider="openrouter",
        model="some/cheap-model",
        api_key="sk-test",
        mode="ask",
        options={"modelWebSearch": "none"},
    ):
        pass
    kwargs = provider.captured_kwargs
    assert kwargs is not None
    assert "web_search" not in kwargs  # native search NOT enabled
    assert "web_search" in (kwargs.get("tool_ids") or [])  # local tool retained
    assert "modelWebSearch" not in kwargs


@pytest.mark.asyncio
async def test_invoke_openai_provider_level_native_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A provider-level native provider (openai) rides native search with no
    # per-model hint at all — the existing five must not regress.
    agent_runtime.reload()
    provider = _FakeProvider()
    _patch_provider(monkeypatch, provider)
    async for _ in agent_runtime.invoke_agent(
        agent_id="copilot",
        prompt="what is the latest market news?",
        provider="openai",
        model="gpt-4.1-mini",
        api_key="sk-test",
        mode="ask",
    ):
        pass
    kwargs = provider.captured_kwargs
    assert kwargs is not None
    assert kwargs.get("web_search") is True
    assert "web_search" not in (kwargs.get("tool_ids") or [])


@pytest.mark.asyncio
async def test_invoke_agent_emits_error_for_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    agent_runtime.reload()
    events: list[Any] = []
    async for event in agent_runtime.invoke_agent(
        agent_id="not-a-real-agent",
        prompt="hi",
        api_key="sk-test",
    ):
        events.append(event)
    kinds = [e.kind for e in events]
    assert kinds == ["error", "done"]


@pytest.mark.asyncio
async def test_invoke_agent_provider_override_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    agent_runtime.reload()
    chosen: dict[str, Any] = {}

    def factory(provider_id: str, **_: Any) -> _FakeProvider:
        chosen["provider_id"] = provider_id
        return _FakeProvider()

    monkeypatch.setattr(agent_runtime, "get_provider", factory)
    async for _ in agent_runtime.invoke_agent(
        agent_id="buffett",
        prompt="x",
        provider="openai",
        api_key="sk-test",
    ):
        pass
    assert chosen["provider_id"] == "openai"


@pytest.mark.asyncio
async def test_invoke_agent_model_override_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    agent_runtime.reload()
    provider = _FakeProvider()
    _patch_provider(monkeypatch, provider)
    async for _ in agent_runtime.invoke_agent(
        agent_id="buffett",
        prompt="x",
        model="claude-haiku-4-5",
        api_key="sk-test",
    ):
        pass
    assert provider.captured_kwargs is not None
    assert provider.captured_kwargs["model"] == "claude-haiku-4-5"


# ---------------------------------------------------------------------------
# Mode gate (FR-003 four-mode spine / FR-005 / FR-013)
#
# `mode` gates the effective tool set SERVER-SIDE. Ask is read-only by default:
# the runtime strips every mutating capability before the adapter call so an
# external MCP client cannot bypass it. edit/build/delegate pass the full set.
# ---------------------------------------------------------------------------

#: The four mutating capabilities on the copilot's tool list — all read_only=False.
#: Ask MUST strip every one; edit/build/delegate MUST keep them.
_COPILOT_MUTATORS = {"open_panel", "set_chart_symbol", "add_to_watchlist", "propose_order"}


async def _capture_tool_ids(monkeypatch: pytest.MonkeyPatch, **invoke_kwargs: Any) -> list[str]:
    """Invoke the copilot through the fake provider and return the tool_ids the
    runtime handed the adapter."""
    agent_runtime.reload()
    provider = _FakeProvider()
    _patch_provider(monkeypatch, provider)
    prompt = invoke_kwargs.pop("prompt", "x")
    async for _ in agent_runtime.invoke_agent(
        agent_id="copilot",
        prompt=prompt,
        api_key="sk-test",
        **invoke_kwargs,
    ):
        pass
    assert provider.captured_kwargs is not None
    tool_ids = provider.captured_kwargs["tool_ids"]
    assert isinstance(tool_ids, list)
    return tool_ids


@pytest.mark.asyncio
async def test_ask_mode_strips_all_mutators(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ask mode filters the adapter's tool_ids to read-only capabilities — none
    of the host-action mutators or propose_order survive, but read tools and the
    per-invocation reads do."""
    tool_ids = await _capture_tool_ids(monkeypatch, mode="ask")
    selected = set(tool_ids)
    # No mutating capability reaches the adapter.
    assert selected.isdisjoint(_COPILOT_MUTATORS), (
        f"Ask leaked mutators: {selected & _COPILOT_MUTATORS}"
    )
    # Read tools + per-invocation reads survive.
    assert "price_data" in selected
    assert "get_terminal_state" in selected
    assert "get_portfolio" in selected
    # Every surviving id is genuinely read-only per the catalog (source of truth).
    from services.agent_tools import catalog

    assert all(catalog.is_read_only(t) is True for t in tool_ids)


@pytest.mark.asyncio
async def test_default_mode_is_ask_and_read_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """Omitting ``mode`` defaults to Ask — the read-only gate applies."""
    tool_ids = await _capture_tool_ids(monkeypatch)
    assert set(tool_ids).isdisjoint(_COPILOT_MUTATORS)
    assert "price_data" in tool_ids


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["edit", "build", "delegate"])
async def test_action_modes_keep_full_tool_set(monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    """edit/build/delegate pass the agent's tool set UNCHANGED — host actions and
    propose_order are present (the staging distinction is a frontend concern)."""
    tool_ids = await _capture_tool_ids(monkeypatch, mode=mode)
    spec = agent_runtime.get_agent("copilot")
    assert spec is not None
    assert tool_ids == list(spec.tools)
    assert _COPILOT_MUTATORS.issubset(set(tool_ids))


@pytest.mark.asyncio
async def test_read_intent_retains_panel_allowlist_but_not_propose_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A READ intent (inferred under mode='agent') keeps the read-safe panel
    host-actions so it can still ground the index chart — but propose_order STAYS
    stripped (Decision 4 loosening; §6.5 read-gate intact)."""
    tool_ids = await _capture_tool_ids(monkeypatch, prompt="how is the market today?", mode="agent")
    selected = set(tool_ids)
    # The 5 read-safe panel actions survive a read intent.
    for action in (
        "open_panel",
        "set_chart_symbol",
        "set_chart_indicators",
        "arrange_layout",
        "add_to_watchlist",
    ):
        assert action in selected, f"read-safe panel action {action} stripped on a read intent"
    # The §6.5 broker mutation is STILL stripped on a read intent.
    assert "propose_order" not in selected
    # Data/search read tools were never stripped.
    assert "price_data" in selected
    assert "market_overview" in selected


def test_invocation_request_round_trips_mode() -> None:
    """``AgentInvocationRequest`` accepts and round-trips ``mode``; it defaults to
    Ask when omitted, and ``extra='forbid'`` still rejects unknown fields."""
    # Default.
    assert AgentInvocationRequest(prompt="hi").mode == "ask"
    # Explicit, every allowed value.
    for m in ("ask", "edit", "build", "delegate"):
        req = AgentInvocationRequest(prompt="hi", mode=m)
        assert req.mode == m
        assert req.model_dump()["mode"] == m
    # Invalid value rejected.
    with pytest.raises(ValidationError):
        AgentInvocationRequest(prompt="hi", mode="god")


def test_invocation_request_round_trips_autonomy() -> None:
    """``AgentInvocationRequest`` accepts an optional ``autonomy`` axis; it
    defaults to None, round-trips ask/auto, and rejects an unknown value."""
    assert AgentInvocationRequest(prompt="hi").autonomy is None
    for a in ("ask", "auto"):
        req = AgentInvocationRequest(prompt="hi", autonomy=a)
        assert req.autonomy == a
        assert req.model_dump()["autonomy"] == a
    with pytest.raises(ValidationError):
        AgentInvocationRequest(prompt="hi", autonomy="yolo")


# ---------------------------------------------------------------------------
# Truthful host-action narration (WS1 — autonomy-aware, orders exempt)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_autonomy_applies_non_order_host_action() -> None:
    """With autonomy='auto' a NON-ORDER host-action reports it APPLIED (the
    frontend auto-applies it) so the model narrates it in past tense."""
    local = agent_runtime._build_local_tools(None, autonomy="auto")
    result = await local["set_chart_symbol"]({"symbol": "SPY"})
    assert result["ok"] is True
    assert result["status"] == "applied"
    assert result["applied"] is True
    assert result["host_action"] == {"type": "set_chart_symbol", "args": {"symbol": "SPY"}}


@pytest.mark.asyncio
async def test_ask_autonomy_stages_non_order_host_action() -> None:
    """With autonomy='ask' (or omitted) a non-order host-action stays STAGED for
    the user's review — the model must not claim it is done."""
    for autonomy in ("ask", None):
        local = agent_runtime._build_local_tools(None, autonomy=autonomy)
        result = await local["open_panel"]({"panel": "news"})
        assert result["status"] == "awaiting_user_review"
        assert result["staged_for_review"] is True


@pytest.mark.asyncio
async def test_propose_order_always_awaits_review_even_in_auto() -> None:
    """SAFETY (§6.5): propose_order returns awaiting_user_review in EVERY autonomy
    mode — the AI has NO path to auto-apply an order."""
    for autonomy in ("auto", "ask", None):
        local = agent_runtime._build_local_tools(None, autonomy=autonomy)
        result = await local["propose_order"]({"symbol": "AAPL", "side": "buy", "quantity": 1})
        assert result["status"] == "awaiting_user_review", (
            f"propose_order auto-applied under autonomy={autonomy!r} — §6.5 VIOLATION"
        )
        assert result.get("applied") is not True
        assert result.get("status") != "applied"


def test_session_preamble_anchors_the_server_clock() -> None:
    """The session preamble leads with the live server date + the stale-data
    directive so a time-sensitive turn must fetch live data, not recall it."""
    preamble = agent_runtime._render_session_preamble()
    assert "Current date:" in preamble
    assert "training data is STALE" in preamble
    assert "MUST call a tool" in preamble


@pytest.mark.asyncio
async def test_composed_messages_carry_the_session_date_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The composed message list handed to the adapter contains a 'Current date:'
    system line on every turn (the grounding fix for symptom #1)."""
    agent_runtime.reload()
    provider = _FakeProvider()
    _patch_provider(monkeypatch, provider)
    async for _ in agent_runtime.invoke_agent(
        agent_id="copilot",
        prompt="hello",
        api_key="sk-test",
    ):
        pass
    msgs = provider.captured_messages
    assert msgs is not None
    assert any("Current date:" in m.content for m in msgs if m.role == "system")


def test_get_agent_resolves_a_custom_agent(
    tmp_path: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """get_agent falls back to the custom-agent store so user-authored AND
    marketplace-registered plugin agents are invokable (FR-050 agent slice).
    A truly-unknown id still returns None; first-party still resolves."""
    from config import DATA_DIR_ENV
    from models.custom_agent import CustomAgentCreate
    from services import agents_store

    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    agent_runtime.reload()
    agents_store.create_agent(
        CustomAgentCreate(
            id="custom:vysted-lenses-quant-tutor",
            name="Quant Tutor",
            philosophy="Teaches as it analyzes.",
            system_prompt="You are an educational finance lens. Ground every claim in a tool call.",
            tools=["price_data", "fundamentals"],
            default_provider="anthropic",
        )
    )
    spec = agent_runtime.get_agent("custom:vysted-lenses-quant-tutor")
    assert spec is not None
    assert spec.id == "custom:vysted-lenses-quant-tutor"
    assert spec.default_provider == "anthropic"
    assert "price_data" in spec.tools
    # First-party still resolves; an unknown custom id resolves to None.
    assert agent_runtime.get_agent("copilot") is not None
    assert agent_runtime.get_agent("custom:does-not-exist") is None


class _StubToolCall:
    """Minimal stand-in for the LLMToolUseEvent _auto_publish_event reads."""

    def __init__(self, tool_call_id: str = "tc-1") -> None:
        self.tool_call_id = tool_call_id


def test_auto_publish_maps_fast_web_round_into_brief_sources() -> None:
    """The keyless '0 sources / structured only' bug: a FAST bundle strands its web
    round under web.{citations,results} (no top-level `sources`). The synthetic
    publish_brief must surface those as brief sources so a quick research shows the
    REAL DuckDuckGo results — not an empty source list."""
    fast_bundle = {
        "ok": True,
        "query": "NVDA",
        "symbol": "NVDA",
        "structured": {"price": {"ok": True}},
        "web": {
            "available": True,
            "citations": [
                {"url": "https://finance.yahoo.com/quote/NVDA/news/", "title": "NVDA News"},
                {"url": "https://stockanalysis.com/stocks/nvda/", "title": "NVDA", "snippet": "x"},
            ],
        },
    }
    event = agent_runtime._auto_publish_event(_StubToolCall(), json.dumps(fast_bundle))
    assert event is not None
    assert event.name == "publish_brief"
    sources = event.input["sources"]
    assert len(sources) == 2
    assert sources[0]["url"] == "https://finance.yahoo.com/quote/NVDA/news/"
    assert sources[1]["excerpt"] == "x"  # snippet → excerpt
    assert event.input["web_available"] is True


def test_auto_publish_passes_through_deep_sources_and_honest_no_web() -> None:
    """A DEEP bundle's top-level `sources` pass through unchanged; a FAST bundle whose
    web round found nothing (web.available False) yields no sources + an honest
    web_available False (the structured-only banner survives)."""
    deep_bundle = {
        "ok": True,
        "query": "AAPL",
        "markdown": "## Brief\nText [1].",
        "sources": [{"url": "https://sec.gov/x", "title": "10-K", "domain": "sec"}],
        "web_available": True,
    }
    deep_event = agent_runtime._auto_publish_event(_StubToolCall(), json.dumps(deep_bundle))
    assert deep_event is not None
    assert deep_event.input["sources"] == deep_bundle["sources"]
    assert deep_event.input["web_available"] is True

    no_web = {
        "ok": True,
        "query": "AAPL",
        "structured": {"price": {"ok": True}},
        "web": {"available": False, "citations": [], "note": "structured only"},
    }
    no_web_event = agent_runtime._auto_publish_event(_StubToolCall(), json.dumps(no_web))
    assert no_web_event is not None
    assert no_web_event.input["sources"] == []
    assert no_web_event.input["web_available"] is False
    # WS3: the nested web.note is forwarded onto the brief so the banner states WHY
    # (previously web.note was stranded — never read by the auto-publish).
    assert no_web_event.input["note"] == "structured only"


def test_auto_publish_forwards_transient_rate_limit_reason() -> None:
    """WS3 symptom #2: a FAST bundle whose web round was a TRANSIENT throttle must
    forward web.note AND the typed web.reason onto the brief, so the panel shows
    "rate-limited, retrying" — not the false "no backend configured" banner."""
    throttled = {
        "ok": True,
        "query": "AAPL",
        "structured": {"price": {"ok": True}},
        "web": {
            "available": False,
            "citations": [],
            "reason": "rate_limited",
            "note": "Web search was rate-limited — retry in a moment",
            "detail": "keyless web search is rate-limiting right now",
        },
    }
    event = agent_runtime._auto_publish_event(_StubToolCall(), json.dumps(throttled))
    assert event is not None
    assert event.input["web_available"] is False  # zero sources → honest no-web
    assert event.input["web_reason"] == "rate_limited"
    assert event.input["note"] == "Web search was rate-limited — retry in a moment"
    assert "no backend" not in event.input["note"].lower()


def test_auto_publish_reconciles_web_available_with_sources() -> None:
    """WS3 symptom #2 core: a bundle that surfaced sources but carries
    web_available False (structured citations, no web round) must be reconciled to
    True — a brief that cites N sources can NOT also claim the web was unavailable.
    A truly sourceless bundle keeps the honest False."""
    sourced_but_flagged_no_web = {
        "ok": True,
        "query": "AAPL",
        "markdown": "## Brief\nText [1].",
        "sources": [{"url": "https://sec.gov/x", "title": "10-K", "domain": "sec"}],
        "web_available": False,
    }
    event = agent_runtime._auto_publish_event(
        _StubToolCall(), json.dumps(sourced_but_flagged_no_web)
    )
    assert event is not None
    assert len(event.input["sources"]) == 1
    assert event.input["web_available"] is True  # reconciled — never contradictory

    sourceless = {
        "ok": True,
        "query": "AAPL",
        "structured": {"price": {"ok": True}},
        "web": {"available": False, "citations": []},
    }
    sourceless_event = agent_runtime._auto_publish_event(_StubToolCall(), json.dumps(sourceless))
    assert sourceless_event is not None
    assert sourceless_event.input["sources"] == []
    assert sourceless_event.input["web_available"] is False  # honest no-web survives


def test_auto_publish_maps_depth_tier_from_result_mode() -> None:
    """FR-115: the auto-publish carries the true depth TIER so the brief panel's
    'Go deeper' affordance knows the next tier. A FAST bundle (no mode) → 'quick';
    a deep run → 'deep'; a heavy run → 'heavy'."""
    fast = {"ok": True, "query": "NVDA", "structured": {"price": {"ok": True}}}
    fast_event = agent_runtime._auto_publish_event(_StubToolCall(), json.dumps(fast))
    assert fast_event is not None
    assert fast_event.input["depth"] == "quick"

    deep = {"ok": True, "query": "NVDA", "markdown": "x", "mode": "deep"}
    deep_event = agent_runtime._auto_publish_event(_StubToolCall(), json.dumps(deep))
    assert deep_event is not None
    assert deep_event.input["depth"] == "deep"

    heavy = {"ok": True, "query": "NVDA", "markdown": "x", "mode": "heavy"}
    heavy_event = agent_runtime._auto_publish_event(_StubToolCall(), json.dumps(heavy))
    assert heavy_event is not None
    assert heavy_event.input["depth"] == "heavy"


# ---------------------------------------------------------------------------
# WS8 — DeepSeek/OpenRouter tool-loop resilience (runtime side)
# ---------------------------------------------------------------------------


class _ToolThenAnswerProvider:
    """Two-round provider: round 1 streams reasoning + a tool call, round 2
    streams the final text. Records the messages handed to EACH round so a test
    can inspect the reconstructed assistant tool-use turn appended between them.
    """

    def __init__(self, *, reasoning: str) -> None:
        self._reasoning = reasoning
        self._round = 0
        self.round_messages: list[list[LLMMessage]] = []

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        model: str,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        # Snapshot the messages for this round (a shallow copy is enough — the
        # runtime mutates the list in place between rounds).
        self.round_messages.append(list(messages))
        if self._round == 0:
            self._round += 1
            if self._reasoning:
                yield LLMThinkingEvent(text=self._reasoning)
            yield LLMToolUseEvent(
                tool_call_id="call-1", name="price_data", input={"symbol": "AAPL"}
            )
            yield LLMDoneEvent(usage=LLMUsage(input_tokens=5, output_tokens=1))
            return
        yield LLMDeltaEvent(text="AAPL looks fine.")
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=3, output_tokens=2))


def _stub_tool_dispatch(monkeypatch: pytest.MonkeyPatch, result: str = '{"ok": true}') -> None:
    """Replace the live tool dispatch with a canned result so no real tool runs."""

    async def _fake_dispatch(tool_call: Any, local_tools: Any = None) -> AsyncIterator[Any]:
        yield agent_runtime._ToolDone(result)

    monkeypatch.setattr(agent_runtime, "_dispatch_tool_with_progress", _fake_dispatch)


def _reconstructed_assistant_turn(messages: list[LLMMessage]) -> LLMMessage | None:
    """Find the reconstructed assistant tool-use turn (carries tool_calls meta)."""
    for msg in messages:
        if msg.role == "assistant" and msg.metadata and msg.metadata.get("tool_calls"):
            return msg
    return None


@pytest.mark.asyncio
async def test_deepseek_reasoner_echoes_reasoning_on_reconstructed_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WS8 Step 4 (echo default): for a *reasoner* model the reconstructed
    assistant tool-use turn carries the round's reasoning_content (not content="")
    so a multi-round reasoner turn is well-formed."""
    agent_runtime.reload()
    provider = _ToolThenAnswerProvider(reasoning="Let me check the price first.")
    _patch_provider(monkeypatch, provider)
    _stub_tool_dispatch(monkeypatch)
    async for _ in agent_runtime.invoke_agent(
        agent_id="copilot",
        prompt="is AAPL ok?",
        provider="deepseek",
        model="deepseek-reasoner",
        api_key="sk-test",
        mode="agent",
    ):
        pass
    # The SECOND round's message list contains the reconstructed assistant turn.
    assert len(provider.round_messages) == 2
    turn = _reconstructed_assistant_turn(provider.round_messages[1])
    assert turn is not None
    assert turn.content == "Let me check the price first."


@pytest.mark.asyncio
async def test_non_reasoner_reconstructed_turn_stays_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WS8 Step 4 must NOT regress non-reasoner behaviour: the same two-round
    flow on a non-reasoner model keeps content="" on the reconstructed turn even
    if a (spurious) thinking event was streamed."""
    agent_runtime.reload()
    provider = _ToolThenAnswerProvider(reasoning="should be ignored for non-reasoner")
    _patch_provider(monkeypatch, provider)
    _stub_tool_dispatch(monkeypatch)
    async for _ in agent_runtime.invoke_agent(
        agent_id="copilot",
        prompt="is AAPL ok?",
        provider="deepseek",
        model="deepseek-chat",
        api_key="sk-test",
        mode="agent",
    ):
        pass
    assert len(provider.round_messages) == 2
    turn = _reconstructed_assistant_turn(provider.round_messages[1])
    assert turn is not None
    assert turn.content == ""


@pytest.mark.asyncio
async def test_dispatch_unknown_tool_returns_relayable_error() -> None:
    """Grounded narration (R8 seams): a tool call to an unknown/disallowed tool
    id returns a structured, RELAYABLE error result — the model can narrate the
    failure honestly ("that tool isn't available") instead of crashing the
    stream or silently no-opping."""
    event = LLMToolUseEvent(tool_call_id="call-bad", name="open_wormhole", input={})
    result = json.loads(await agent_runtime._dispatch_tool(event))
    assert result["ok"] is False
    assert "open_wormhole" in result["error"]
    assert "not available" in result["error"]


@pytest.mark.asyncio
async def test_dispatch_handler_exception_returns_relayable_error() -> None:
    """A handler that raises surfaces a structured error keyed to the tool name
    so the model recovers next round — never an unhandled exception."""

    async def _boom(_args: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("upstream exploded")

    event = LLMToolUseEvent(tool_call_id="call-x", name="fragile_tool", input={})
    result = json.loads(await agent_runtime._dispatch_tool(event, {"fragile_tool": _boom}))
    assert result["ok"] is False
    assert "fragile_tool" in result["error"]
    assert "upstream exploded" in result["error"]


@pytest.mark.asyncio
async def test_invalid_args_sentinel_dispatches_graceful_error_not_empty() -> None:
    """WS8 Step 1: a tool call the adapter could not repair carries the
    INVALID_ARGS_SENTINEL; _dispatch_tool surfaces the structured error keyed on
    the call id and NEVER dispatches the tool with coerced-to-{} args."""
    from services.llm.openai import INVALID_ARGS_SENTINEL

    event = LLMToolUseEvent(
        tool_call_id="call-9",
        name="price_data",
        input={INVALID_ARGS_SENTINEL: "invalid arguments for price_data: 'symbol' is required"},
    )
    result_str = await agent_runtime._dispatch_tool(event)
    result = json.loads(result_str)
    assert result["ok"] is False
    assert "invalid arguments for price_data" in result["error"]
