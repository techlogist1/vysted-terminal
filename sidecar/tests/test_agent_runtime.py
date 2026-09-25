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
from services.agent_tools import research


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


def test_copilot_prompt_carries_the_corporate_action_directive() -> None:
    """R12: the copilot is the FAST-tier (depth='quick') brief narrator — that
    tier has no internal LLM synthesis call of its own (see
    ``services.research.fast`` and its NORMAL-depth PROFILE), so the copilot's
    OWN system prompt is the only guardrail against inventing a corporate
    action. The battery finding was a narrative that invented five specific
    filing dates matching no real filing, one chronologically impossible,
    stated with the same confidence as real cited data."""
    copilot = json.loads((agent_runtime.AGENTS_DIR / "copilot.json").read_text(encoding="utf-8"))
    prompt = copilot["systemPrompt"]
    assert "CORPORATE ACTIONS" in prompt
    assert "filing number" in prompt
    assert "record date" in prompt
    assert "unverified in this run" in prompt


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


def test_terminal_preamble_renders_prior_stated_values() -> None:
    """R13 JARVIS 3b: a research space carrying prior stated figures renders the
    'PRIOR STATED VALUES' line so a contradicting new figure is reconciled."""
    preamble = agent_runtime._render_terminal_preamble(
        {
            "focusedSymbol": "NVDA",
            "researchSpace": {
                "symbol": "NVDA",
                "priorTurns": 2,
                "claims": [
                    {
                        "symbol": "NVDA",
                        "metric": "P/E",
                        "value": 55.0,
                        "statedAt": 1_700_000_000_000,
                    },
                    {
                        "symbol": "NVDA",
                        "metric": "Price",
                        "value": 900.0,
                        "statedAt": 1_700_000_000_000,
                    },
                ],
            },
        }
    )
    assert "PRIOR STATED VALUES (this session):" in preamble
    assert "NVDA P/E=55" in preamble
    assert "NVDA Price=900" in preamble


def test_terminal_preamble_omits_prior_values_when_no_claims() -> None:
    """A research space with no claims renders no PRIOR STATED VALUES line."""
    preamble = agent_runtime._render_terminal_preamble(
        {"researchSpace": {"symbol": "NVDA", "priorTurns": 0}}
    )
    assert "PRIOR STATED VALUES" not in preamble


def test_capabilities_preamble_carries_self_consistency_instruction() -> None:
    """R13 JARVIS 3c: the shared capabilities preamble tells the agent to
    reconcile a contradicting figure openly, never silently switch."""
    text = agent_runtime.TERMINAL_CAPABILITIES_PREAMBLE
    assert "PRIOR STATED VALUE" in text
    assert "materially contradicts" in text
    assert "acknowledge both" in text.lower()


def test_every_first_party_agent_states_an_unavailable_fact_as_unavailable() -> None:
    """R15-AGENT-090: with no tool able to return SIFY's ADR ratio, the model
    invented one and cited "fundamentals data"; every loaded agent now carries
    the rule that such a fact is unavailable and never attributed to a source."""
    agent_runtime.reload()
    specs = agent_runtime.list_agents()
    assert specs
    for spec in specs:
        prompt = spec.system_prompt
        assert "no tool result you received contains is UNAVAILABLE" in prompt, spec.id
        assert "never attribute it to a tool, a data feed or any source" in prompt, spec.id


@pytest.mark.asyncio
async def test_invoke_agent_emits_plan_for_compound_on_capable_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A compound request on a capable model surfaces a visible plan whose
    host-action steps are flagged ``staged``."""
    agent_runtime.reload()
    provider = _FakeProvider()
    _patch_provider(monkeypatch, provider)

    async def _fake_complete(prov, model, key, messages, *, timeout=None):  # noqa: ANN001, ANN202
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
    # The provider-level native provider always qualifies (any model rides the
    # provider's own search), regardless of the per-model hint. Gemini and Groq
    # are per-model (R15-AGENT-005; see test_native_search.py).
    assert agent_runtime._native_search_enabled("anthropic", None) is True
    assert agent_runtime._native_search_enabled("anthropic", "none") is True


@pytest.mark.asyncio
async def test_ask_user_is_offered_only_to_a_delegate_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """R15-CODE-AGENT-011: ask_user pauses a durable run; a live turn asks in prose."""
    from services.agent_tools import catalog

    agent_runtime.reload()
    offered: dict[str, list[str]] = {}
    for mode in ("delegate", "agent", "ask"):
        provider = _FakeProvider()
        _patch_provider(monkeypatch, provider)
        async for _ in agent_runtime.invoke_agent(
            agent_id="buffett", prompt="compare the two", api_key="sk", mode=mode
        ):
            pass
        assert provider.captured_kwargs is not None
        offered[mode] = list(provider.captured_kwargs.get("tool_ids") or [])
    assert "ask_user" in offered["delegate"]
    assert "ask_user" not in offered["agent"]
    assert "ask_user" not in offered["ask"]
    assert "ask_user" not in catalog.mcp_tool_ids()


@pytest.mark.asyncio
async def test_xai_turn_keeps_the_local_web_search_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    # R15-LEAD-008: xAI's Live Search is retired (410), so an xAI turn gets no
    # native-search opt-in and keeps the local web_search tool to search with.
    agent_runtime.reload()
    provider = _FakeProvider()
    _patch_provider(monkeypatch, provider)
    async for _ in agent_runtime.invoke_agent(
        agent_id="copilot",
        prompt="what is the latest market news?",
        provider="xai",
        model="grok-4",
        api_key="sk-test",
        mode="ask",
    ):
        pass
    kwargs = provider.captured_kwargs
    assert kwargs is not None
    assert kwargs.get("web_search") is None
    assert "web_search" in (kwargs.get("tool_ids") or [])


def test_native_search_enabled_openai_is_per_model() -> None:
    # OpenAI chat-completions serves native search only on *-search-preview
    # models; anything else 400s on a web_search tool, so it keeps the local one.
    assert agent_runtime._native_search_enabled("openai", None, "gpt-4o-search-preview") is True
    assert agent_runtime._native_search_enabled("openai", None, "gpt-5.6-luna") is False
    assert agent_runtime._native_search_enabled("openai", "native", "gpt-4.1-mini") is False
    assert agent_runtime._native_search_enabled("openai", None, None) is False


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
            model="gpt-4o-search-preview",
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
async def test_invoke_scrubs_unknown_options_and_aliases_depth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stray option key used to crash the whole round: POST /invoke with
    options {"depth": "normal"} rode ``depth`` into the OpenAI SDK
    ("AsyncCompletions.create() got an unexpected keyword argument depth"). The
    runtime now (a) treats ``depth`` as a tolerant alias for ``research_depth``
    and (b) scrubs any other non-whitelisted option key before the adapter call —
    so an unknown key can never reach the SDK."""
    import config

    agent_runtime.reload()
    provider = _FakeProvider()
    _patch_provider(monkeypatch, provider)
    async for _ in agent_runtime.invoke_agent(
        agent_id="copilot",
        prompt="what is AAPL doing?",
        provider="openai",
        model="gpt-4.1-mini",
        api_key="sk-test",
        mode="ask",
        options={"depth": "deep", "bogus_key": 1},
    ):
        pass  # no TypeError — the stray keys never reach the adapter
    kwargs = provider.captured_kwargs
    assert kwargs is not None
    assert "depth" not in kwargs
    assert "bogus_key" not in kwargs
    # ``depth`` resolved as the research-depth alias.
    assert config.get_request_research_depth() == "deep"


@pytest.mark.asyncio
async def test_invoke_openai_native_search_is_per_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # OpenAI serves native search on chat-completions only for *-search-preview
    # models; that model rides it with no per-model hint at all.
    agent_runtime.reload()
    provider = _FakeProvider()
    _patch_provider(monkeypatch, provider)
    async for _ in agent_runtime.invoke_agent(
        agent_id="copilot",
        prompt="what is the latest market news?",
        provider="openai",
        model="gpt-4o-search-preview",
        api_key="sk-test",
        mode="ask",
    ):
        pass
    kwargs = provider.captured_kwargs
    assert kwargs is not None
    assert kwargs.get("web_search") is True
    assert "web_search" not in (kwargs.get("tool_ids") or [])


@pytest.mark.asyncio
async def test_invoke_openai_non_search_model_keeps_local_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Regression: a normal OpenAI model must NOT get the native-search opt-in —
    # the adapter would otherwise send a web_search tools entry the API rejects
    # 400 — and must keep the local web_search tool (FR-082).
    agent_runtime.reload()
    provider = _FakeProvider()
    _patch_provider(monkeypatch, provider)
    async for _ in agent_runtime.invoke_agent(
        agent_id="copilot",
        prompt="what is the latest market news?",
        provider="openai",
        model="gpt-5.6-luna",
        api_key="sk-test",
        mode="ask",
    ):
        pass
    kwargs = provider.captured_kwargs
    assert kwargs is not None
    assert kwargs.get("web_search") is not True
    assert "web_search" in (kwargs.get("tool_ids") or [])


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
_COPILOT_MUTATORS = {"open_panel", "set_chart_symbol", "add_to_watchlist", "portfolio_add_position"}


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
    of the host-action mutators or portfolio writes survive, but read tools and the
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
    portfolio writes are present (the staging distinction is a frontend concern);
    a delegate run is also offered ask_user (R15-CODE-AGENT-011)."""
    tool_ids = await _capture_tool_ids(monkeypatch, mode=mode)
    spec = agent_runtime.get_agent("copilot")
    assert spec is not None
    assert tool_ids == list(spec.tools) + (["ask_user"] if mode == "delegate" else [])
    assert _COPILOT_MUTATORS.issubset(set(tool_ids))


@pytest.mark.asyncio
async def test_read_intent_retains_panel_allowlist_but_not_data_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A READ intent (inferred under mode='agent') keeps the read-safe panel
    host-actions so it can still ground the index chart — but the tracked-portfolio
    writes STAY stripped (Decision 4 loosening; §6.5 read-gate intact)."""
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
    # Tracked-portfolio writes are STILL stripped on a read intent.
    for write in (
        "portfolio_add_position",
        "portfolio_update_position",
        "portfolio_delete_position",
    ):
        assert write not in selected, f"data-write {write} survived a read intent"
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
# Truthful host-action narration (WS1 — autonomy-aware)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_autonomy_dispatches_non_order_host_action() -> None:
    """R10 E3.3: with autonomy='auto' a NON-ORDER host-action reports it
    DISPATCHED (not 'applied … past tense' — the synthesized result used to
    claim completion BEFORE the frontend ran applyHostAction, whose guards can
    keep prior state). The model must verify via get_terminal_state."""
    local = agent_runtime._build_local_tools(None, autonomy="auto")
    result = await local["set_chart_symbol"]({"symbol": "SPY"})
    assert result["ok"] is True
    assert result["status"] == "dispatched"
    assert "applied" not in result  # no premature completion claim
    assert "verify with get_terminal_state" in result["note"]
    assert "authoritative" in result["note"]
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


def _tool_result(bundle: dict[str, Any]) -> str:
    """The research tool's serialised result: the engine bundle plus the brief
    it attaches (C6), which the runtime publishes verbatim."""
    brief = research.brief_for(bundle)
    return json.dumps({**bundle, "brief": brief} if brief else bundle)


def _execution(loop: str = "fast", requested: str = "normal") -> dict[str, Any]:
    """A well-formed R10 execution record — every auto-publishable payload
    must carry one (E2: no execution → no auto-publish)."""
    return {
        "run_id": "run-exec-1",
        "requested_depth": requested,
        "loop": loop,
        "backend": None,
        "started_at": 1.0,
        "finished_at": 2.0,
        "degraded_reason": None,
    }


def test_auto_publish_maps_fast_web_round_into_brief_sources() -> None:
    """The keyless '0 sources / structured only' bug: a FAST bundle strands its web
    round under web.{citations,results} (no top-level `sources`). The synthetic
    publish_brief must surface those as brief sources so a quick research shows the
    REAL DuckDuckGo results — not an empty source list."""
    fast_bundle = {
        "ok": True,
        "query": "NVDA",
        "symbol": "NVDA",
        "execution": _execution(),  # R10: auto-publish requires the record
        "structured": {"price": {"ok": True}},
        "web": {
            "available": True,
            "citations": [
                {"url": "https://finance.yahoo.com/quote/NVDA/news/", "title": "NVDA News"},
                {"url": "https://stockanalysis.com/stocks/nvda/", "title": "NVDA", "snippet": "x"},
            ],
        },
    }
    event = agent_runtime._auto_publish_event(_StubToolCall(), _tool_result(fast_bundle))
    assert event is not None
    assert event.name == "publish_brief"
    sources = event.input["sources"]
    assert len(sources) == 2
    assert sources[0]["url"] == "https://finance.yahoo.com/quote/NVDA/news/"
    assert sources[1]["excerpt"] == "x"  # snippet → excerpt
    assert event.input["web_available"] is True


def test_auto_publish_fast_source_keeps_its_date_and_a_host_domain() -> None:
    """RESEARCH-024 (C4): a FAST web row with ``published_at`` and a URL yields a
    dated source labelled by its host, never the literal 'web'."""
    fast_bundle = {
        "ok": True,
        "query": "NVDA",
        "execution": _execution(),
        "structured": {"price": {"ok": True}},
        "web": {
            "available": True,
            "results": [
                {
                    "url": "https://www.reuters.com/markets/nvda",
                    "title": "NVDA",
                    "source": "web",
                    "published_at": "2026-09-20T10:00:00Z",
                },
                {"url": "https://ir.nvidia.com/q2", "title": "Q2", "domain": "ir.nvidia.com"},
            ],
        },
    }
    event = agent_runtime._auto_publish_event(_StubToolCall(), _tool_result(fast_bundle))
    assert event is not None
    first, second = event.input["sources"]
    assert first["domain"] == "www.reuters.com"
    assert first["published_at"] == "2026-09-20T10:00:00Z"
    assert second["domain"] == "ir.nvidia.com"
    assert second["published_at"] is None


def test_auto_publish_passes_through_deep_sources_and_honest_no_web() -> None:
    """A DEEP bundle's top-level `sources` pass through unchanged; a FAST bundle whose
    web round found nothing (web.available False) yields no sources + an honest
    web_available False (the structured-only banner survives)."""
    deep_bundle = {
        "ok": True,
        "query": "AAPL",
        "execution": _execution(loop="iter", requested="deep"),
        "markdown": "## Brief\nText [1].",
        "sources": [{"url": "https://sec.gov/x", "title": "10-K", "domain": "sec"}],
        "web_available": True,
    }
    deep_event = agent_runtime._auto_publish_event(_StubToolCall(), _tool_result(deep_bundle))
    assert deep_event is not None
    assert deep_event.input["sources"] == deep_bundle["sources"]
    assert deep_event.input["web_available"] is True

    no_web = {
        "ok": True,
        "query": "AAPL",
        "execution": _execution(),
        "structured": {"price": {"ok": True}},
        "web": {"available": False, "citations": [], "note": "structured only"},
    }
    no_web_event = agent_runtime._auto_publish_event(_StubToolCall(), _tool_result(no_web))
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
        "execution": _execution(),
        "structured": {"price": {"ok": True}},
        "web": {
            "available": False,
            "citations": [],
            "reason": "rate_limited",
            "note": "Web search was rate-limited — retry in a moment",
            "detail": "keyless web search is rate-limiting right now",
        },
    }
    event = agent_runtime._auto_publish_event(_StubToolCall(), _tool_result(throttled))
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
        "execution": _execution(loop="iter", requested="deep"),
        "markdown": "## Brief\nText [1].",
        "sources": [{"url": "https://sec.gov/x", "title": "10-K", "domain": "sec"}],
        "web_available": False,
    }
    event = agent_runtime._auto_publish_event(
        _StubToolCall(), _tool_result(sourced_but_flagged_no_web)
    )
    assert event is not None
    assert len(event.input["sources"]) == 1
    assert event.input["web_available"] is True  # reconciled — never contradictory

    sourceless = {
        "ok": True,
        "query": "AAPL",
        "execution": _execution(),
        "structured": {"price": {"ok": True}},
        "web": {"available": False, "citations": []},
    }
    sourceless_event = agent_runtime._auto_publish_event(_StubToolCall(), _tool_result(sourceless))
    assert sourceless_event is not None
    assert sourceless_event.input["sources"] == []
    assert sourceless_event.input["web_available"] is False  # honest no-web survives


def test_auto_publish_maps_depth_tier_from_execution_loop() -> None:
    """FR-115 + R10 E2: mode/depth derive ONLY from the execution record's loop
    (what RAN) — never from the payload's ``mode`` field, which the old read
    defaulted to 'fast' and stamped a DEEP run "Mode: FAST". A payload whose
    mode CONTRADICTS its loop renders the loop's truth."""
    fast = {
        "ok": True,
        "query": "NVDA",
        "execution": _execution(loop="fast"),
        "structured": {"price": {"ok": True}},
    }
    fast_event = agent_runtime._auto_publish_event(_StubToolCall(), _tool_result(fast))
    assert fast_event is not None
    assert fast_event.input["depth"] == "quick"
    assert fast_event.input["mode"] == "fast"

    # The E2 repro: a deep run whose payload LACKS a mode field — the loop wins.
    deep = {
        "ok": True,
        "query": "NVDA",
        "markdown": "x",
        "execution": _execution(loop="iter", requested="deep"),
    }
    deep_event = agent_runtime._auto_publish_event(_StubToolCall(), _tool_result(deep))
    assert deep_event is not None
    assert deep_event.input["depth"] == "deep"
    assert deep_event.input["mode"] == "deep"

    heavy = {
        "ok": True,
        "query": "NVDA",
        "markdown": "x",
        "mode": "fast",  # contradicting payload mode — the loop's truth wins
        "execution": _execution(loop="heavy", requested="ultra"),
    }
    heavy_event = agent_runtime._auto_publish_event(_StubToolCall(), _tool_result(heavy))
    assert heavy_event is not None
    assert heavy_event.input["depth"] == "heavy"
    assert heavy_event.input["mode"] == "deep"
    # The verbatim record rides the publish for the panel's badges/carry.
    assert heavy_event.input["execution"]["loop"] == "heavy"


def test_auto_publish_requires_an_execution_record() -> None:
    """R10 E2: a research payload WITHOUT an execution record is malformed and
    never auto-publishes — the depth stamp can no longer be guessed."""
    legacy = {"ok": True, "query": "NVDA", "markdown": "x", "mode": "deep"}
    assert agent_runtime._auto_publish_event(_StubToolCall(), _tool_result(legacy)) is None


def test_auto_publish_disambiguation_publishes_the_chooser() -> None:
    """R10 D37: a needs_disambiguation result publishes the candidate chooser —
    {query, disambiguation, execution} and NOTHING else (no markdown, no
    structured, no guessed entity)."""
    payload = {
        "ok": True,
        "needs_disambiguation": True,
        "query": "tata",
        "candidates": [
            {"symbol": "TCS", "name": "Tata Consultancy", "exchange": "NSE", "score": 0.6},
            {"symbol": "TATAMOTORS", "name": "Tata Motors", "exchange": "NSE", "score": 0.58},
        ],
        "message": "Which Tata did you mean?",
        "execution": _execution(),
    }
    event = agent_runtime._auto_publish_event(_StubToolCall(), _tool_result(payload))
    assert event is not None
    assert event.name == "publish_brief"
    assert set(event.input) == {"query", "disambiguation", "execution"}
    assert event.input["disambiguation"]["query"] == "tata"
    assert [c["symbol"] for c in event.input["disambiguation"]["candidates"]] == [
        "TCS",
        "TATAMOTORS",
    ]


# ---------------------------------------------------------------------------
# R10 E3.3 — end-of-stream publish read-back (the ack ledger divergence check)
# ---------------------------------------------------------------------------


class _PublishThenAnswerProvider:
    """Round 1 issues a model publish_brief; round 2 streams the final text."""

    def __init__(self) -> None:
        self._round = 0

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        model: str,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        if self._round == 0:
            self._round += 1
            yield LLMToolUseEvent(
                tool_call_id="pub-1", name="publish_brief", input={"markdown": "## x"}
            )
            yield LLMDoneEvent(usage=LLMUsage(input_tokens=5, output_tokens=1))
            return
        yield LLMDeltaEvent(text="Published.")
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=3, output_tokens=2))


async def _collect_auto_publish_events(
    monkeypatch: pytest.MonkeyPatch, ack: str | None = None
) -> list[Any]:
    """Drive one publish turn; ``ack`` is the status the panel POSTs for the
    streamed publish_brief id (the runtime mints it, so the ack keys on it)."""
    from services import action_ledger

    agent_runtime.reload()
    _patch_provider(monkeypatch, _PublishThenAnswerProvider())
    monkeypatch.setattr(agent_runtime, "_ACK_GRACE_SECONDS", 0.0)  # no grace wait in tests
    events: list[Any] = []
    async for event in agent_runtime.invoke_agent(
        agent_id="copilot",
        prompt="publish a brief",
        api_key="sk-test",
        mode="edit",
        autonomy="auto",
    ):
        if ack and isinstance(event, LLMToolUseEvent) and event.name == "publish_brief":
            action_ledger.record(event.tool_call_id, ack)
        events.append(event)
    return events


def _notice_details(events: list[Any]) -> list[str]:
    return [
        e.detail
        for e in events
        if getattr(e, "kind", None) == "research_step"
        and getattr(e, "tool", None) == "publish_brief"
    ]


@pytest.mark.asyncio
async def test_unconfirmed_publish_yields_divergence_notice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No ack in the ledger → an honest 'panel did not confirm' notice rides the
    step channel BEFORE the terminal done (E3.3: publish claims are read back,
    never assumed)."""
    from services import action_ledger

    action_ledger.reset_for_tests()
    events = await _collect_auto_publish_events(monkeypatch)
    details = _notice_details(events)
    assert any("did not confirm" in d for d in details)
    # The notice precedes the terminator.
    kinds = [e.kind for e in events]
    assert kinds[-1] == "done"
    assert kinds.index("research_step") < len(kinds) - 1


@pytest.mark.asyncio
async def test_kept_previous_ack_yields_kept_notice(monkeypatch: pytest.MonkeyPatch) -> None:
    """A kept_previous ack (the D33 shrink guard kept the richer brief) surfaces
    as its own quiet notice — the agent can stop claiming the new one rendered."""
    from services import action_ledger

    action_ledger.reset_for_tests()
    events = await _collect_auto_publish_events(monkeypatch, ack="kept_previous")
    details = _notice_details(events)
    # R13 JARVIS 1c: the hardcoded "richer" wording is gone — the notice now
    # names the artifact ACTUALLY on screen (falls back to a bare phrase when the
    # ack carried no brief identity, as here).
    assert any("kept the brief already on screen" in d for d in details)
    action_ledger.reset_for_tests()


@pytest.mark.asyncio
async def test_applied_ack_yields_no_notice(monkeypatch: pytest.MonkeyPatch) -> None:
    """An 'applied' ack means the optimistic dispatch was right — no notice."""
    from services import action_ledger

    action_ledger.reset_for_tests()
    events = await _collect_auto_publish_events(monkeypatch, ack="applied")
    assert _notice_details(events) == []
    action_ledger.reset_for_tests()


@pytest.mark.asyncio
async def test_no_divergence_check_outside_auto_autonomy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Under ask/review autonomy the publish is STAGED (the model already says
    'proposed') — the ledger read-back is an AUTO-mode honesty device only."""
    from services import action_ledger

    action_ledger.reset_for_tests()
    agent_runtime.reload()
    _patch_provider(monkeypatch, _PublishThenAnswerProvider())
    monkeypatch.setattr(agent_runtime, "_ACK_GRACE_SECONDS", 0.0)
    events: list[Any] = []
    async for event in agent_runtime.invoke_agent(
        agent_id="copilot",
        prompt="publish a brief",
        api_key="sk-test",
        mode="edit",
        autonomy="ask",
    ):
        events.append(event)
    assert _notice_details(events) == []


@pytest.mark.asyncio
async def test_superseded_publish_emits_no_contradicting_notice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R13 JARVIS 1c: a publish that ended kept_previous but was SUPERSEDED by a
    later successful publish of the same symbol in the same turn emits NO notice
    — the panel shows the applied one, so a contradiction would lie (tonight's
    false 'kept the previous' chip firing next to the NEW brief)."""
    from services import action_ledger

    action_ledger.reset_for_tests()
    monkeypatch.setattr(agent_runtime, "_ACK_GRACE_SECONDS", 0.0)
    # Call A shrank (kept_previous); call B published the richer brief (applied).
    action_ledger.record("pub-A", "kept_previous", {"symbol": "NVDA", "source_count": 3})
    action_ledger.record("pub-B", "applied", {"symbol": "NVDA", "source_count": 8})
    notices = await agent_runtime._publish_divergence_notices(["pub-A", "pub-B"])
    assert notices == []
    action_ledger.reset_for_tests()


@pytest.mark.asyncio
async def test_kept_previous_notice_names_what_is_on_screen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R13 JARVIS 1c: a genuine kept_previous (no later apply) DOES notice, and
    the notice NAMES the artifact on screen from the ack — never the old
    hardcoded 'richer brief' claim."""
    from services import action_ledger

    action_ledger.reset_for_tests()
    monkeypatch.setattr(agent_runtime, "_ACK_GRACE_SECONDS", 0.0)
    action_ledger.record("pub-A", "kept_previous", {"symbol": "NVDA", "source_count": 5})
    notices = await agent_runtime._publish_divergence_notices(["pub-A"])
    assert len(notices) == 1
    assert "kept the brief already on screen" in notices[0].detail
    assert "NVDA" in notices[0].detail
    assert "5 sources" in notices[0].detail
    assert "richer" not in notices[0].detail
    action_ledger.reset_for_tests()


# ---------------------------------------------------------------------------
# R13 JARVIS 1b — in-loop grounded host-action read-back
# ---------------------------------------------------------------------------


class _HostActionThenAnswerProvider:
    """Round 1 issues ONE host-action tool call; round 2 streams the final text.
    Records the messages handed to each round so a test can inspect the grounded
    tool-result the runtime rewrote from the panel's ack."""

    def __init__(self, *, call_id: str = "hact-1", name: str = "set_chart_symbol") -> None:
        self._round = 0
        self._call_id = call_id
        self._name = name
        self.round_messages: list[list[LLMMessage]] = []

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        model: str,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        self.round_messages.append(list(messages))
        if self._round == 0:
            self._round += 1
            yield LLMToolUseEvent(
                tool_call_id=self._call_id, name=self._name, input={"symbol": "SPY"}
            )
            yield LLMDoneEvent(usage=LLMUsage(input_tokens=5, output_tokens=1))
            return
        yield LLMDeltaEvent(text="Done.")
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=3, output_tokens=2))


def _tool_result_for(messages: list[LLMMessage], call_id: str) -> LLMMessage | None:
    for msg in messages:
        if msg.role == "tool" and msg.tool_call_id == call_id:
            return msg
    return None


async def _run_host_action_readback(
    monkeypatch: pytest.MonkeyPatch,
    ack: str | None = None,
    detail: dict[str, Any] | None = None,
    autonomy: str = "auto",
) -> tuple[_HostActionThenAnswerProvider, str]:
    """Drive one host-action turn and return the provider plus the streamed
    (runtime-minted) call id; ``ack`` is what the panel POSTs for that id."""
    from services import action_ledger

    agent_runtime.reload()
    provider = _HostActionThenAnswerProvider()
    _patch_provider(monkeypatch, provider)
    monkeypatch.setattr(agent_runtime, "_ACK_GRACE_SECONDS", 0.0)  # no grace wait in tests
    call_id = ""
    async for event in agent_runtime.invoke_agent(
        agent_id="copilot",
        prompt="load SPY",
        api_key="sk-test",
        mode="edit",
        autonomy=autonomy,
    ):
        if isinstance(event, LLMToolUseEvent):
            call_id = event.tool_call_id
            if ack:
                action_ledger.record(call_id, ack, detail=detail)
    return provider, call_id


@pytest.mark.asyncio
async def test_failed_ack_grounds_host_action_tool_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """R13 JARVIS 1b (the required unit-level end-to-end): a host action whose
    ack=failed produces a GROUNDED tool-result the model's NEXT round sees — 'did
    not happen', not the optimistic 'dispatched'."""
    from services import action_ledger

    action_ledger.reset_for_tests()
    provider, call_id = await _run_host_action_readback(
        monkeypatch, "failed", {"action": "set_chart_symbol", "symbol": "SPY"}
    )
    assert len(provider.round_messages) == 2
    msg = _tool_result_for(provider.round_messages[1], call_id)
    assert msg is not None, "the round-2 prompt must carry the grounded tool-result"
    payload = json.loads(msg.content)
    assert payload["ok"] is False
    assert payload["status"] == "failed"
    assert "did not happen" in payload["note"]
    assert payload["detail"] == {"action": "set_chart_symbol", "symbol": "SPY"}
    action_ledger.reset_for_tests()


@pytest.mark.asyncio
async def test_ackless_host_action_says_not_yet_confirmed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R13 JARVIS 1b: a dispatched host action with NO ack in the grace window is
    rewritten to 'dispatched, not yet confirmed — verify before claiming success'
    (strengthened from today's soft advisory)."""
    from services import action_ledger

    action_ledger.reset_for_tests()
    provider, call_id = await _run_host_action_readback(monkeypatch)
    msg = _tool_result_for(provider.round_messages[1], call_id)
    assert msg is not None
    payload = json.loads(msg.content)
    assert payload["status"] == "dispatched_unconfirmed"
    assert "not yet confirmed" in payload["note"].lower()
    assert "verify" in payload["note"].lower()
    # The descriptor still names the action + symbol from the call args.
    assert payload["detail"]["action"] == "set_chart_symbol"
    assert payload["detail"]["symbol"] == "SPY"
    action_ledger.reset_for_tests()


@pytest.mark.asyncio
async def test_applied_ack_grounds_host_action_as_done(monkeypatch: pytest.MonkeyPatch) -> None:
    """R13 JARVIS 1b: an applied ack rewrites the tool-result to a confirmed
    'applied' so the model may truthfully state the action landed."""
    from services import action_ledger

    action_ledger.reset_for_tests()
    provider, call_id = await _run_host_action_readback(
        monkeypatch, "applied", {"action": "set_chart_symbol", "symbol": "SPY"}
    )
    msg = _tool_result_for(provider.round_messages[1], call_id)
    assert msg is not None
    payload = json.loads(msg.content)
    assert payload["ok"] is True
    assert payload["status"] == "applied"
    action_ledger.reset_for_tests()


@pytest.mark.asyncio
async def test_host_action_readback_skipped_outside_auto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Under ask/review autonomy the action is STAGED (never dispatched), so the
    in-loop read-back does NOT run — the staged awaiting_user_review result is
    left untouched for the model."""
    from services import action_ledger

    action_ledger.reset_for_tests()
    provider, call_id = await _run_host_action_readback(monkeypatch, autonomy="ask")
    msg = _tool_result_for(provider.round_messages[1], call_id)
    assert msg is not None
    payload = json.loads(msg.content)
    assert payload["status"] == "awaiting_user_review"
    assert payload.get("status") != "dispatched_unconfirmed"
    action_ledger.reset_for_tests()


class _EmptyIdHostActionProvider:
    """Ollama-shaped: two rounds each issue a host action with ``tool_call_id=''``,
    then a final answer."""

    def __init__(self) -> None:
        self.round_messages: list[list[LLMMessage]] = []

    async def stream_chat(self, messages: list[LLMMessage], model: str, **_: Any) -> Any:
        self.round_messages.append(list(messages))
        if len(self.round_messages) <= 2:
            yield LLMToolUseEvent(tool_call_id="", name="set_chart_symbol", input={"symbol": "SPY"})
            yield LLMDoneEvent(usage=LLMUsage(input_tokens=5, output_tokens=1))
            return
        yield LLMDeltaEvent(text="Done.")
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=3, output_tokens=2))


@pytest.mark.asyncio
async def test_runtime_mints_distinct_ids_for_empty_provider_ids_and_acks_resolve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-AGENT-046: two Ollama rounds whose host actions carry '' get distinct,
    non-empty runtime ids, and the panel's ack for each grounds it as applied."""
    from services import action_ledger

    action_ledger.reset_for_tests()
    agent_runtime.reload()
    provider = _EmptyIdHostActionProvider()
    _patch_provider(monkeypatch, provider)
    monkeypatch.setattr(agent_runtime, "_ACK_GRACE_SECONDS", 0.0)
    ids: list[str] = []
    async for event in agent_runtime.invoke_agent(
        agent_id="copilot", prompt="load SPY", mode="edit", autonomy="auto"
    ):
        if isinstance(event, LLMToolUseEvent):
            ids.append(event.tool_call_id)
            action_ledger.record(event.tool_call_id, "applied")  # the panel's ack
    assert len(ids) == 2 and all(ids) and ids[0] != ids[1]
    for round_index, call_id in ((1, ids[0]), (2, ids[1])):
        msg = _tool_result_for(provider.round_messages[round_index], call_id)
        assert msg is not None
        assert json.loads(msg.content)["status"] == "applied"
    action_ledger.reset_for_tests()


@pytest.mark.asyncio
async def test_a_prior_autobrief_ack_does_not_confirm_a_later_brief(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-AGENT-046: an ack grounds one read. A later publish reusing the id
    (a provider id reset per stream) is not confirmed by the earlier ack."""
    from services import action_ledger

    action_ledger.reset_for_tests()
    monkeypatch.setattr(agent_runtime, "_ACK_GRACE_SECONDS", 0.0)
    action_ledger.record("research_0__autobrief", "applied")
    assert await agent_runtime._publish_divergence_notices(["research_0__autobrief"]) == []
    later = await agent_runtime._publish_divergence_notices(["research_0__autobrief"])
    assert len(later) == 1 and "did not confirm" in later[0].detail
    action_ledger.reset_for_tests()


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


# ---------------------------------------------------------------------------
# R10 E7 — per-tool dispatch timeouts (honest message, loop continues)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_timeout_returns_honest_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A registry tool that exceeds its budget returns the honest timeout
    payload (error='timeout', message naming the tool, the budget, and a next
    step) — never an unbounded silent hang (E7)."""
    import asyncio as _asyncio

    from services import agent_tools
    from services.agent_tools import catalog

    async def _slow(_args: dict[str, Any]) -> dict[str, Any]:
        await _asyncio.sleep(5)
        return {"ok": True}  # pragma: no cover — never reached

    agent_tools.register_tool("slow_probe_tool", _slow)
    try:
        monkeypatch.setattr(
            catalog, "timeout_for", lambda tid: 0.05 if tid == "slow_probe_tool" else None
        )
        event = LLMToolUseEvent(tool_call_id="call-slow", name="slow_probe_tool", input={})
        result = json.loads(await agent_runtime._dispatch_tool(event))
    finally:
        agent_tools.reset_for_tests()
        agent_tools.register_v0_5_0_tools()
        agent_tools.register_v0_6_0_tools()
    assert result["ok"] is False
    assert result["error"] == "timeout"
    assert "slow_probe_tool timed out after 0s" in result["message"]
    assert "—" in result["message"]  # the per-domain hint rides the message


@pytest.mark.asyncio
async def test_dispatch_timeout_loop_continues(monkeypatch: pytest.MonkeyPatch) -> None:
    """The E7 core: a timed-out tool round does NOT kill the stream — the
    result reaches the model as a relayable error and the loop finishes the
    turn normally."""
    import asyncio as _asyncio

    from services import agent_tools
    from services.agent_tools import catalog

    async def _slow(_args: dict[str, Any]) -> dict[str, Any]:
        await _asyncio.sleep(5)
        return {"ok": True}  # pragma: no cover — never reached

    agent_tools.register_tool("slow_probe_tool", _slow)
    monkeypatch.setattr(
        catalog, "timeout_for", lambda tid: 0.05 if tid == "slow_probe_tool" else None
    )

    class _SlowToolProvider:
        def __init__(self) -> None:
            self._round = 0
            self.round_messages: list[list[LLMMessage]] = []

        async def stream_chat(
            self,
            messages: list[LLMMessage],
            model: str,
            api_key: str | None = None,
            **kwargs: Any,
        ) -> AsyncIterator[Any]:
            self.round_messages.append(list(messages))
            if self._round == 0:
                self._round += 1
                yield LLMToolUseEvent(tool_call_id="call-1", name="slow_probe_tool", input={})
                yield LLMDoneEvent(usage=LLMUsage(input_tokens=5, output_tokens=1))
                return
            yield LLMDeltaEvent(text="That tool timed out; here is what I know.")
            yield LLMDoneEvent(usage=LLMUsage(input_tokens=3, output_tokens=2))

    agent_runtime.reload()
    provider = _SlowToolProvider()
    _patch_provider(monkeypatch, provider)
    events: list[Any] = []
    try:
        async for event in agent_runtime.invoke_agent(
            agent_id="copilot",
            prompt="probe",
            api_key="sk-test",
            mode="edit",
        ):
            events.append(event)
    finally:
        agent_tools.reset_for_tests()
        agent_tools.register_v0_5_0_tools()
        agent_tools.register_v0_6_0_tools()
    # The stream completed (loop continued past the timeout)…
    assert [e.kind for e in events][-1] == "done"
    # …and the model's second round saw the honest timeout result.
    tool_turns = [m for m in provider.round_messages[1] if m.role == "tool"]
    assert len(tool_turns) == 1
    timeout_payload = json.loads(tool_turns[0].content)
    assert timeout_payload["error"] == "timeout"
    assert "timed out" in timeout_payload["message"]


def test_research_guard_scales_with_args_and_depth() -> None:
    """The research outer guard = max(arg wall, profile wall, engine floor) + 90
    — it can never fire before a legitimately-running engine (tier_a profile
    walls AND tier_b research-model walls both fit under it)."""
    event_cls = LLMToolUseEvent
    # normal: floor 120 + 90.
    assert (
        agent_runtime._tool_timeout_seconds(
            event_cls(tool_call_id="c", name="research", input={"query": "x"})
        )
        == 210.0
    )
    # deep: tier_b research-model wall 300 beats the 120 profile wall.
    assert (
        agent_runtime._tool_timeout_seconds(
            event_cls(tool_call_id="c", name="research", input={"query": "x", "depth": "deep"})
        )
        == 390.0
    )
    # ultra: 480 floor (tier_b) beats the 360 profile wall.
    assert (
        agent_runtime._tool_timeout_seconds(
            event_cls(tool_call_id="c", name="research", input={"query": "x", "depth": "ultra"})
        )
        == 570.0
    )
    # An explicit wall_seconds above every floor wins.
    assert (
        agent_runtime._tool_timeout_seconds(
            event_cls(
                tool_call_id="c",
                name="research",
                input={"query": "x", "depth": "deep", "wall_seconds": 600},
            )
        )
        == 690.0
    )


def test_host_actions_and_per_invocation_tools_have_no_timeout() -> None:
    """Host-action locals (frontend round-trips) and per-invocation reads are
    EXEMPT from dispatch timeouts; every registry read tool carries one."""
    from services.agent_tools import catalog

    for cap in catalog.CAPABILITY_CATALOG.values():
        if cap.kind in ("host_action", "per_invocation"):
            assert cap.timeout_seconds is None, f"{cap.id}: locals must be exempt"
        elif cap.kind == "read_handler" and cap.id != "research":
            assert cap.timeout_seconds is not None, f"{cap.id}: registry tool needs a budget"
    # research's guard is computed from args, not the catalog.
    assert catalog.timeout_for("research") is None


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


# ---------------------------------------------------------------------------
# R11 — a provider content-filter finish is explained honestly (V2 evidence)
# ---------------------------------------------------------------------------


class _ContentFilterProvider:
    """Adapter emitting an unexplained refusal + finish_reason=content_filter —
    the live DeepSeek-V4-Flash behaviour on host-action asks (captured in
    verification/r11/v2-redrive/)."""

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        model: str,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        yield LLMDeltaEvent(text="你好，我无法给到相关内容。")
        yield LLMDoneEvent(usage=LLMUsage(), finish_reason="content_filter")


@pytest.mark.asyncio
async def test_content_filter_finish_yields_honest_error_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent_runtime.reload()
    _patch_provider(monkeypatch, _ContentFilterProvider())
    events: list[Any] = []
    async for event in agent_runtime.invoke_agent(
        agent_id="copilot",
        prompt="Add 5 RELIANCE at 1400 to my portfolio",
        api_key="sk-test",
    ):
        events.append(event)
    kinds = [e.kind for e in events]
    assert kinds == ["delta", "error", "done"], kinds
    error = events[1]
    assert error.code == "content_filter"
    assert "declined" in error.message
    assert error.action and "switch" in error.action
    assert "content_filter" in (error.detail or "")


# ---------------------------------------------------------------------------
# R15-AGENT-011: an agent-started backtest opens in the backtest panel (C1)
# ---------------------------------------------------------------------------


class _BacktestThenAnswerProvider:
    def __init__(self) -> None:
        self._round = 0

    async def stream_chat(self, messages, model, api_key=None, **kwargs):  # noqa: ANN001, ANN003, ANN201
        self._round += 1
        if self._round == 1:
            yield LLMToolUseEvent(
                tool_call_id="call-bt",
                name="run_custom_backtest",
                input={"entry": "sma(20) > sma(50)", "exit": "rsi(14) > 70", "symbols": ["AAPL"]},
            )
            yield LLMDoneEvent()
            return
        yield LLMDeltaEvent(text="Backtest is up.")
        yield LLMDoneEvent()


async def _backtest_events(monkeypatch: pytest.MonkeyPatch, result: str) -> list[Any]:
    agent_runtime.reload()
    _stub_tool_dispatch(monkeypatch, result)
    monkeypatch.setattr(
        agent_runtime, "get_provider", lambda *_a, **_k: _BacktestThenAnswerProvider()
    )
    return [
        e
        async for e in agent_runtime.invoke_agent(
            agent_id="copilot", prompt="backtest a golden cross", api_key="sk-test", mode="edit"
        )
    ]


@pytest.mark.asyncio
async def test_successful_custom_backtest_opens_its_run(monkeypatch: pytest.MonkeyPatch) -> None:
    events = await _backtest_events(monkeypatch, '{"ok": true, "runId": "bt-1"}')
    opens = [e for e in events if getattr(e, "name", None) == "open_panel"]
    backtest = next(e for e in events if getattr(e, "name", None) == "run_custom_backtest")
    assert len(opens) == 1
    assert opens[0].input == {"panel": "backtest", "run_id": "bt-1"}
    assert opens[0].tool_call_id == f"auto-backtest-{backtest.tool_call_id}"


@pytest.mark.asyncio
async def test_failed_custom_backtest_opens_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    events = await _backtest_events(monkeypatch, '{"ok": false, "error": "no bars"}')
    assert not [e for e in events if getattr(e, "name", None) == "open_panel"]


@pytest.mark.asyncio
async def test_the_final_done_carries_the_whole_turns_spend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-AGENT-082 (C11): the invoke done frame prices EVERY round of the
    turn, not only the last one; an unpriced model reports None."""

    class _TwoRounds:
        def __init__(self) -> None:
            self.calls = 0

        async def stream_chat(self, messages: list[LLMMessage], **_: Any) -> AsyncIterator[Any]:
            self.calls += 1
            if self.calls == 1:
                yield LLMToolUseEvent(tool_call_id="x", name="price_data", input={"symbol": "SPY"})
                yield LLMDoneEvent(usage=LLMUsage(input_tokens=600, output_tokens=0))
                return
            yield LLMDeltaEvent(text="SPY is up.")
            yield LLMDoneEvent(usage=LLMUsage(input_tokens=300, output_tokens=100))

    async def _dispatch(_call: Any, _local: Any = None) -> AsyncIterator[Any]:
        yield agent_runtime._ToolDone(json.dumps({"ok": True, "price": 1}))

    monkeypatch.setattr(agent_runtime, "_dispatch_tool_with_progress", _dispatch)

    async def _done(provider: str, model: str) -> LLMDoneEvent:
        monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: _TwoRounds())
        events = [
            e
            async for e in agent_runtime.invoke_agent(
                agent_id="copilot",
                prompt="price of SPY",
                provider=provider,
                model=model,
                api_key="k",
                mode="edit",
            )
        ]
        [done] = [e for e in events if isinstance(e, LLMDoneEvent)]
        return done

    priced = await _done("deepseek", "deepseek-chat")  # 1,000 tokens at $0.9/1M
    assert priced.spend_usd == pytest.approx(0.0009)
    assert (await _done("xai", "mystery-1")).spend_usd is None


class _RecordingRoundsProvider:
    """Scripted rounds; records a deep copy of every request's messages."""

    def __init__(self, rounds: list[list[Any]]) -> None:
        self._rounds = rounds
        self.requests: list[list[dict[str, Any]]] = []

    async def stream_chat(
        self, messages: list[LLMMessage], model: str, api_key: str | None = None, **_: Any
    ) -> AsyncIterator[Any]:
        self.requests.append([m.model_dump() for m in messages])
        for event in self._rounds[len(self.requests) - 1]:
            yield event


@pytest.mark.asyncio
async def test_sent_tool_results_are_never_rewritten(monkeypatch: pytest.MonkeyPatch) -> None:
    """R15-AGENT-050 / D-B10-10: a round only appends, so the Anthropic cache
    prefix survives. Round 2 truncates a long result and round 1 carried an
    AUTO host action whose result is grounded from the ack ledger; every
    message a round sent is byte-identical in the next round's request."""
    agent_runtime.reload()
    done = LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))
    provider = _RecordingRoundsProvider(
        [
            [
                LLMToolUseEvent(tool_call_id="a", name="set_chart_symbol", input={"symbol": "TCS"}),
                LLMToolUseEvent(tool_call_id="b", name="price_data", input={"symbol": "TCS"}),
                done,
            ],
            [LLMToolUseEvent(tool_call_id="c", name="price_data", input={"symbol": "INFY"}), done],
            [LLMDeltaEvent(text="Done."), done],
        ]
    )
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: provider)
    monkeypatch.setattr(agent_runtime, "_ACK_GRACE_SECONDS", 0.0)

    async def _tool(tool_call: LLMToolUseEvent, *_a: Any, **_k: Any) -> str:
        return json.dumps({"ok": True, "rows": "x" * 70_000, "symbol": tool_call.input})

    monkeypatch.setattr(agent_runtime, "_dispatch_tool", _tool)

    async for _ in agent_runtime.invoke_agent(
        agent_id="copilot",
        prompt="chart TCS and show me TCS then INFY prices",
        provider="anthropic",
        model="claude-sonnet-4-6",
        api_key="sk-test",
        mode="agent",
        autonomy="auto",
    ):
        pass

    assert len(provider.requests) == 3
    assert "dispatched_unconfirmed" in provider.requests[1][-2]["content"]  # grounded
    assert "chars elided" in provider.requests[2][-1]["content"]  # round 2 truncated
    for earlier, later in zip(provider.requests, provider.requests[1:], strict=False):
        assert later[: len(earlier)] == earlier


def test_fundamentals_money_reads_in_the_statement_currency() -> None:
    """rc1-scenarios:5: SIFY trades in USD but reports in INR. The model read the
    raw revenue float next to ``currency: USD`` and said "$46.5B USD"."""
    result = json.dumps(
        {
            "ok": True,
            "fundamentals": {
                "symbol": "SIFY",
                "currency": "USD",
                "financial_currency": "INR",
                "market_cap": 1204567890.0,
                "revenue_ttm": 46506049536.0,
                "pe_ratio": None,
                "provider": "yfinance",
            },
        }
    )
    fund = json.loads(agent_runtime._model_facing_content("fundamentals", result))["fundamentals"]
    assert fund["revenue_ttm"] == "₹4,651 cr"
    assert fund["market_cap"] == "USD 1.20B"
    assert fund["currency"] == "USD"


def _statement_result(currency: str | None, lines: dict[str, float | None]) -> str:
    return json.dumps(
        {
            "ok": True,
            "symbol": "X",
            "statement": "income",
            "period": "annual",
            "currency": currency,
            "periods": ["2025-03-31"],
            "lines": [
                {"label": label, "values": {"2025-03-31": value}} for label, value in lines.items()
            ],
        }
    )


def _statement_lines(content: str) -> dict[str, object]:
    return {line["label"]: line["values"]["2025-03-31"] for line in json.loads(content)["lines"]}


def test_financial_statements_money_reads_in_the_reporting_currency() -> None:
    """rc1-scenarios:5: SIFY's INR income ``total_revenue 44877000000.0`` reached
    the model bare and was stated as "$44.9B". Money lines become displays;
    per-share, share-count and rate lines stay numeric."""
    result = _statement_result(
        "INR",
        {
            "total_revenue": 44877000000.0,
            "Basic EPS": -0.6,
            "Diluted Average Shares": 438000000.0,
            "Tax Rate For Calcs": 0.21,
            "Net Income Common Stockholders": None,
        },
    )
    lines = _statement_lines(agent_runtime._model_facing_content("financial_statements", result))
    assert lines == {
        "total_revenue": "₹4,488 cr",
        "Basic EPS": -0.6,
        "Diluted Average Shares": 438000000.0,
        "Tax Rate For Calcs": 0.21,
        "Net Income Common Stockholders": None,
    }


def test_financial_statements_usd_cash_flow_scales_and_unknown_currency_stays_raw() -> None:
    usd = _statement_result(
        "USD", {"Free Cash Flow": 108807000000.0, "Repurchase Of Capital Stock": -94949000000.0}
    )
    lines = _statement_lines(agent_runtime._model_facing_content("financial_statements", usd))
    assert lines == {
        "Free Cash Flow": "USD 108.81B",
        "Repurchase Of Capital Stock": "USD -94.95B",
    }
    unknown = _statement_result(None, {"Free Cash Flow": 108807000000.0})
    assert _statement_lines(
        agent_runtime._model_facing_content("financial_statements", unknown)
    ) == {"Free Cash Flow": 108807000000.0}


def test_compare_symbols_market_cap_reads_in_each_row_quote_currency() -> None:
    result = json.dumps(
        {
            "ok": True,
            "symbols": [
                {
                    "symbol": "TCS.NS",
                    "quote": {"price": 3100.0, "currency": "INR"},
                    "fundamentals": {"market_cap": 11216000000000.0, "pe_ratio": 22.4},
                },
                {
                    "symbol": "ACN",
                    "quote": {"price": 250.0, "currency": "USD"},
                    "fundamentals": {"market_cap": 156000000000.0, "pe_ratio": 20.1},
                },
                {"symbol": "ZZZZ", "error": "no quote"},
            ],
        }
    )
    rows = json.loads(agent_runtime._model_facing_content("compare_symbols", result))["symbols"]
    assert rows[0]["fundamentals"] == {"market_cap": "₹1,121,600 cr", "pe_ratio": 22.4}
    assert rows[1]["fundamentals"]["market_cap"] == "USD 156.00B"
    assert rows[2] == {"symbol": "ZZZZ", "error": "no quote"}


async def _scripted_answer(
    monkeypatch: pytest.MonkeyPatch,
    tool: str | dict[str, dict[str, Any]] | None,
    result: dict[str, Any],
    deltas: list[str],
    history: list[dict[str, str]] | None = None,
) -> str:
    """Round 1 calls ``tool`` (stubbed to return ``result``; or each tool of a
    {name: result} dict); round 2 streams ``deltas``. With no ``tool`` the only
    round streams them. ``history`` rides the invoke options as the client
    sends it. Returns the joined answer the consumer saw."""
    agent_runtime.reload()
    results = tool if isinstance(tool, dict) else {tool: result} if tool else {}
    done = LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))
    rounds: list[list[Any]] = [[*(LLMDeltaEvent(text=d) for d in deltas), done]]
    if results:
        calls = [
            LLMToolUseEvent(tool_call_id=name, name=name, input={"symbol": "SIFY"})
            for name in results
        ]
        rounds.insert(0, [*calls, done])
    provider = _RecordingRoundsProvider(rounds)
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: provider)

    async def _tool(call: LLMToolUseEvent, *_a: Any, **_k: Any) -> str:
        return json.dumps(results[call.name])

    monkeypatch.setattr(agent_runtime, "_dispatch_tool", _tool)
    return "".join(
        [
            e.text
            async for e in agent_runtime.invoke_agent(
                agent_id="copilot",
                prompt="SIFY ADR ratio?",
                api_key="sk-test",
                autonomy="ask",
                options={"history": history} if history else None,
            )
            if isinstance(e, LLMDeltaEvent)
        ]
    )


_SIFY_FUNDAMENTALS = {
    "ok": True,
    "fundamentals": {
        "symbol": "SIFY",
        "financial_currency": "INR",
        "shares_outstanding": 144869230,
    },
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("deltas", "claim"),
    [
        (
            ["One SIFY ADR repre", "sents 1", " ordinary share, per fundam", "entals data. Rev"],
            "represents 1 ordinary share",
        ),
        (["Each ADS equals approximately 1448", "69230 ordinary shares.\nRev"], "144869230"),
    ],
)
async def test_an_untraced_adr_ratio_claim_is_replaced(
    monkeypatch: pytest.MonkeyPatch, deltas: list[str], claim: str
) -> None:
    """R15-AGENT-090: llama3.1:8b stated SIFY's ADR ratio (1:1, and one read off
    ``shares_outstanding``) and cited "fundamentals data", which carries no ADR
    field. The runtime replaces the claim sentence; the rest streams as is."""
    answer = await _scripted_answer(
        monkeypatch, "fundamentals", _SIFY_FUNDAMENTALS, [*deltas, "enue was ₹4,651 cr."]
    )
    assert agent_runtime.RATIO_UNAVAILABLE in answer
    assert claim not in answer
    assert "fundamentals data" not in answer
    assert answer.endswith("Revenue was ₹4,651 cr.")


_ERRORED = {"ok": False, "error": "yfinance has no instrument data for 'SIFY.NS'"}
_LIVE_1_DUMP = [
    "- fundamentals returned: {",
    '\n "trailing_12m_revenue": {"display": "$13',
    '20 m"}\n',
    "}\n",
    "Revenue is shown above.",
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("result", "deltas", "answer"),
    [
        (
            _ERRORED,
            _LIVE_1_DUMP,
            "The fundamentals tool returned no data for this in this turn.\n\n"
            "Revenue is shown above.",
        ),
        (
            {"ok": True, "fundamentals": {"trailing_12m_revenue": {"display": "$1320 m"}}},
            _LIVE_1_DUMP,
            "".join(_LIVE_1_DUMP),
        ),
        (_ERRORED, ["You mentioned revenue ", "of $1.3 bn."], "You mentioned revenue of $1.3 bn."),
        (
            _SIFY_FUNDAMENTALS,
            ["According to the `financial_", "statements` tool, revenue was ₹4,411 cr. Done."],
            "The financial_statements tool returned no data for this in this turn. Done.",
        ),
        (_ERRORED, ["I'll call `price_data` next."], "I'll call `price_data` next."),
    ],
)
async def test_a_citation_of_a_tool_that_returned_nothing_ok_is_replaced(
    monkeypatch: pytest.MonkeyPatch, result: dict[str, Any], deltas: list[str], answer: str
) -> None:
    """R15-LEAD-030: live-1, llama3.1:8b wrote a 'fundamentals returned: {...}'
    dump with '$1320 m' for a fundamentals call that errored. A citation of a
    tool with no ok result this turn is replaced and its dump dropped; an ok
    tool's citation, a user's figure and a plain mention stream as is."""
    assert await _scripted_answer(monkeypatch, "fundamentals", result, deltas) == answer


_FOLLOWUP_1 = [
    "The tool that provided the market cap figure was `fundamentals`, which returned:\n\n",
    "{\n",
    ' "market_cap": 3440000000000\n',
    "}",
]
_FS_CITATION = "The financial_statements output shows revenue of ₹4,411 cr."
_FS_TRAILER = "SIFY's revenue is ₹4,411 cr.\n\n[tool steps: Using financial statements]"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("history", "deltas", "answer"),
    [
        (
            [
                {"role": "user", "content": "AAPL market cap?"},
                {
                    "role": "assistant",
                    "content": "AAPL's market cap is $3.44 T.\n\n[tool steps: Using fundamentals]",
                },
            ],
            _FOLLOWUP_1,
            "".join(_FOLLOWUP_1),
        ),
        (
            [
                {"role": "user", "content": "SIFY revenue?"},
                {"role": "assistant", "content": _FS_TRAILER},
            ],
            [_FS_CITATION],
            _FS_CITATION,
        ),
        (
            [
                {"role": "user", "content": "SIFY revenue?"},
                {"role": "assistant", "content": _FS_TRAILER},
                *[{"role": r, "content": "ok"} for _ in range(4) for r in ("user", "assistant")],
            ],
            [_FS_CITATION],
            _FS_CITATION,
        ),
        (
            [
                {"role": "user", "content": "SIFY revenue?"},
                {"role": "assistant", "content": "SIFY's revenue is ₹4,411 cr."},
            ],
            [_FS_CITATION],
            "The financial_statements tool returned no data for this in this turn.",
        ),
    ],
)
async def test_a_citation_of_a_tool_an_earlier_turn_ran_is_kept(
    monkeypatch: pytest.MonkeyPatch,
    history: list[dict[str, str]],
    deltas: list[str],
    answer: str,
) -> None:
    """R15-LEAD-030 followup-1: turn 2 called no tool and truly cited turn 1's
    ``fundamentals``; the per-turn ok set replaced it with a false "returned no
    data ... in this session". The history's ``[tool steps: ...]`` trailer
    (verbatim, or folded into the summary of older turns) seeds the turn; with
    no trailer the citation is replaced with the "in this turn" note."""
    assert await _scripted_answer(monkeypatch, None, {}, deltas, history) == answer


_FS_OK = {"ok": True, "statements": {"symbol": "SIFY", "revenue": "₹4,411 cr"}}
_PRICE_NOTE = "The price_data tool returned no data for this in this turn."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("deltas", "answer"),
    [
        (["Price data returned a close of $2.11."], _PRICE_NOTE),
        (
            [
                'Price Data: {"ok": true, "symbol": "SIFY.US", ',
                '"latest_price": 2.11}\n\nUnfortunately, I am unable.',
            ],
            f"{_PRICE_NOTE}\n\nUnfortunately, I am unable.",
        ),
        (
            ["The Fundamentals Tool shows revenue of $1320 m."],
            "The fundamentals tool returned no data for this in this turn.",
        ),
        (["Per `price data`, the close was $2.11."], _PRICE_NOTE),
        (["I don't have price data for SIFY yet."], "I don't have price data for SIFY yet."),
    ],
)
async def test_a_humanised_tool_name_citation_is_replaced(
    monkeypatch: pytest.MonkeyPatch, deltas: list[str], answer: str
) -> None:
    """R15-LEAD-030 lead030-1: llama3.1:8b called only financial_statements,
    then streamed a 'Price Data: {... "latest_price": 2.11 ...}' dump for a
    price_data call it never made (the real price was 13.41). A tool named
    with spaces, hyphens or capitals is the same tool; plain prose that only
    mentions price data streams as is."""
    assert await _scripted_answer(monkeypatch, "financial_statements", _FS_OK, deltas) == answer


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("deltas", "answer"),
    [
        (
            [
                "- fundamentals returned:\n",
                "{",
                '\n "trailing_12m_revenue": {"display": "$13',
                '20 m"}\n',
                "}\n",
                "Revenue is shown above.",
            ],
            "The fundamentals tool returned no data for this in this turn.\n\n"
            "Revenue is shown above.",
        ),
        (
            ["The price_data output =\n", '[\n {"close": 2.11}\n', "]\n", "Done."],
            f"{_PRICE_NOTE}\n\nDone.",
        ),
        (
            ["The fundamentals tool returned:\n", "Revenue grew."],
            "The fundamentals tool returned no data for this in this turn.\nRevenue grew.",
        ),
    ],
)
async def test_a_dump_on_the_line_after_a_replaced_citation_is_dropped(
    monkeypatch: pytest.MonkeyPatch, deltas: list[str], answer: str
) -> None:
    """R15-LEAD-030 probe3/followup-1: '- fundamentals returned:' was replaced
    but the dump opening on the next line streamed, because the bracket depth
    was counted only inside the replaced sentence. A replaced citation ending
    in ':'/'=' drops a dump that opens next; prose that follows it is kept."""
    assert await _scripted_answer(monkeypatch, "fundamentals", _ERRORED, deltas) == answer


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "result", "sentence", "answer"),
    [
        (None, {}, "Let me look up the fundamentals data for SIFY.", None),
        (None, {}, "Next I'll check the news data for any sentiment.", None),
        ("financial_statements", _FS_OK, "Let me look up the fundamentals data for SIFY.", None),
        ("financial_statements", _FS_OK, "Next I'll check the news data for any sentiment.", None),
        ("fundamentals", _SIFY_FUNDAMENTALS, "Let me fetch the `financial_statements` data.", None),
        (None, {}, "I'm going to pull the `financial_statements` data for SIFY next.", None),
        (
            None,
            {},
            "Let me recap: `news` data shows revenue of $5 bn.",
            "The news tool returned no data for this in this turn.",
        ),
    ],
)
async def test_a_figure_less_pre_call_narration_is_kept(
    monkeypatch: pytest.MonkeyPatch,
    tool: str | None,
    result: dict[str, Any],
    sentence: str,
    answer: str | None,
) -> None:
    """R15-LEAD-030 probe.out: 'Let me look up the fundamentals data for SIFY.'
    was replaced before the call ran. An intent with no figure, no bracket and
    no result verb is not a citation; a recap with a figure still is."""
    got = await _scripted_answer(monkeypatch, tool, result, [sentence])
    assert got == (answer or sentence)


_NEWS_OK = {"ok": True, "articles": []}
_FUND_NOTE = "the fundamentals tool returned no data for this in this turn"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tools", "sentence", "answer"),
    [
        ({"financial_statements": _FS_OK}, "PriceData returned a close of $2.11.", _PRICE_NOTE),
        (
            {"news": _NEWS_OK, "fundamentals": _ERRORED},
            'The news tool had nothing, but fundamentals returned: {"revenue": "$1320 m"}',
            f"The news tool had nothing, but {_FUND_NOTE}.",
        ),
        (
            {"news": _NEWS_OK, "fundamentals": _ERRORED},
            'Although the news tool had nothing, the fundamentals tool returned: {"rev": "$1 bn"}',
            f"Although the news tool had nothing, {_FUND_NOTE}.",
        ),
        (
            {},
            "Based on the earnings history, EPS came in at $0.42 last quarter.",
            "The earnings_history tool returned no data for this in this turn.",
        ),
        (
            {"financial_statements": _FS_OK},
            'The output of the fundamentals call: {"revenue": "$1320 m"}',
            "The fundamentals tool returned no data for this in this turn.",
        ),
        (
            {"financial_statements": _ERRORED},
            "These figures were obtained from the financial statements tool using the "
            "'annual' and 'quarterly' parameters respectively.",
            "The financial_statements tool returned no data for this in this turn.",
        ),
    ],
)
async def test_a_figure_attributed_to_a_tool_with_no_ok_result_is_replaced(
    monkeypatch: pytest.MonkeyPatch, tools: dict[str, dict[str, Any]], sentence: str, answer: str
) -> None:
    """R15-LEAD-030 batch-17 probe3 ``fab-camelcase``: 'PriceData returned a
    close of $2.11.' streamed. A camel-cased id is the same tool; and when one
    clause truly reports an ok tool's error while the next attributes a dump
    or figure to an errored tool, only the attributing clause is replaced."""
    assert await _scripted_answer(monkeypatch, tools, {}, [sentence]) == answer


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tools", "sentence"),
    [
        (
            {"fundamentals": _ERRORED, "financial_statements": _FS_OK},
            "The fundamentals tool returned an error, so I used financial statements, "
            "which shows revenue of ₹4,411 cr.",
        ),
        (
            {"fundamentals": _ERRORED, "price_data": {"ok": True, "latest_price": 13.41}},
            "fundamentals failed, but price_data shows $13.41.",
        ),
        (
            {"fundamentals": _ERRORED, "financial_statements": _FS_OK},
            "I could not get fundamentals data; financial statements report ₹4,411 cr of revenue.",
        ),
        (
            {"price_data": _ERRORED, "fundamentals": _SIFY_FUNDAMENTALS},
            "The `price_data` call errored on SIFY.NS, yet the fundamentals tool reports "
            "revenue of $1320 m.",
        ),
        (
            {"news": _ERRORED, "financial_statements": _FS_OK},
            "No luck with `news`; according to `financial_statements`, revenue was ₹4,411 cr.",
        ),
    ],
)
async def test_a_true_error_mention_beside_an_ok_tools_figure_is_kept(
    monkeypatch: pytest.MonkeyPatch, tools: dict[str, dict[str, Any]], sentence: str
) -> None:
    """R15-LEAD-030 batch-17 probe2 ``err-mention-plus-true-figure``: fundamentals
    errored and financial_statements returned ok, and the true sentence that
    mentioned both was replaced whole, losing the ok-sourced figure. A
    citation is judged by attribution, clause by clause: a negative report
    about a tool with no ok result is true, and the figure belongs to the ok
    tool, so the sentence streams verbatim."""
    assert await _scripted_answer(monkeypatch, tools, {}, [sentence]) == sentence


@pytest.mark.asyncio
async def test_an_adr_ratio_a_tool_result_carries_is_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    """R15-AGENT-090: a ratio the session's sources do carry ("Each Repr 6 Ords",
    stated as a number word) passes the guard untouched."""
    result = {"ok": True, "results": [{"title": "Sify Technologies Ltd ADS (Each Repr 6 Ords)"}]}
    answer = await _scripted_answer(
        monkeypatch, "web_search", result, ["Each ADS represents si", "x ordinary shares."]
    )
    assert answer == "Each ADS represents six ordinary shares."


def test_an_adr_price_range_or_time_is_not_a_ratio_claim() -> None:
    """R15-AGENT-090 review: an N to M / N:M beside "ADR" counts as a ratio
    only with a ratio cue, so a price range or a clock time streams as is."""
    kept = "SIFY's ADR traded from 5.20 to 7.10 this week, opening at 10:30 ET. "
    assert agent_runtime._guard_ratio_claims(kept, []) == kept
    claim = "The ADR ratio is 1:2. "
    assert agent_runtime._guard_ratio_claims(claim, []) == agent_runtime.RATIO_UNAVAILABLE + " "


@pytest.mark.asyncio
async def test_each_dispatched_call_streams_its_tool_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-CODE-AGENT-033: the stream carried a call but not how it ended, so the
    eval grader passed a trial whose option_chain call returned 422."""
    agent_runtime.reload()
    done = LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))
    provider = _RecordingRoundsProvider(
        [
            [
                LLMToolUseEvent(tool_call_id="a", name="option_chain", input={"symbol": "SPY"}),
                LLMToolUseEvent(tool_call_id="b", name="price_data", input={"symbol": "SPY"}),
                done,
            ],
            [LLMDeltaEvent(text="Done."), done],
        ]
    )
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: provider)

    async def _tool(tool_call: LLMToolUseEvent, *_a: Any, **_k: Any) -> str:
        if tool_call.name == "option_chain":
            return json.dumps({"ok": False, "error": "422: expiry 'nearest' is not a date"})
        return json.dumps({"ok": True, "rows": [1, 2]})

    monkeypatch.setattr(agent_runtime, "_dispatch_tool", _tool)
    events = [
        e
        async for e in agent_runtime.invoke_agent(
            agent_id="copilot", prompt="SPY chain", api_key="sk-test", autonomy="ask"
        )
    ]
    calls = [e for e in events if e.kind == "tool_use"]
    results = [e for e in events if e.kind == "tool_result"]
    assert [(r.tool_call_id, r.name, r.ok, r.error) for r in results] == [
        (calls[0].tool_call_id, "option_chain", False, "422: expiry 'nearest' is not a date"),
        (calls[1].tool_call_id, "price_data", True, None),
    ]
    assert events.index(results[0]) > events.index(calls[1])


_SIFY_WEB_SEARCH = {
    "ok": True,
    "results": [{"title": "Sify Technologies Ltd ADS (Each Repr 6 Ords)"}],
}


@pytest.mark.parametrize(
    "claim",
    [
        "SIFY American Depositary Shares each represent six underlying equity shares. ",
        "Each ADR is equivalent to 2 shares of common stock. ",
        "The ADR-to-share ratio is 1 ADR : 6 shares. ",
        "One ADS equals fifteen ordinary shares. ",
        "Every SIFY ADS corresponds to 3 shares. ",
    ],
)
def test_a_depositary_ratio_claim_in_any_wording_is_replaced(claim: str) -> None:
    """R15-AGENT-090 batch 13: the claim was recognised by the shape of the
    number's neighbours, so each new wording escaped. A claim is now a depositary
    term, a ratio cue and a non-money quantity, whatever sits between them."""
    result = json.dumps(_SIFY_FUNDAMENTALS)
    assert (
        agent_runtime._guard_ratio_claims(claim, [result]) == agent_runtime.RATIO_UNAVAILABLE + " "
    )


@pytest.mark.parametrize(
    ("sentence", "result"),
    [
        ("The ADR traded between 10 and 12 dollars. ", _SIFY_FUNDAMENTALS),
        ("Each ADR closed at $12.50 on volume of 40,000 shares. ", _SIFY_FUNDAMENTALS),
        ("Revenue represents 12% of the total. ", _SIFY_FUNDAMENTALS),
        ("The PE ratio is 22.4. ", _SIFY_FUNDAMENTALS),
        # Traced: the unit side 1 is not part of the claim, the 6 is sourced.
        ("The ADR-to-share ratio is 1 ADR : 6 shares. ", _SIFY_WEB_SEARCH),
    ],
)
def test_a_price_volume_other_ratio_or_traced_ratio_streams_as_is(
    sentence: str, result: dict[str, Any]
) -> None:
    """R15-AGENT-090: money, a percent, a trade volume, a non-depositary ratio and
    a ratio a tool result carries are not replaced."""
    assert agent_runtime._guard_ratio_claims(sentence, [json.dumps(result)]) == sentence


@pytest.mark.parametrize(
    "claim",
    [
        "American Depositary Shares each represent six underlying equity shares. ",
        "Each ADR is equivalent to 2 shares of common stock. ",
        "The ADR-to-share ratio is 1 ADR : 6 shares. ",
        "1 ADR = 6 shares. ",
        "One ADR is worth 10 shares of Sify. ",
        "A single SIFY ADR gives you 2 shares. ",
        "Holders get four SIFY shares for every depositary receipt they own. ",
        "Converting 10 ADSs yields 60 equity shares. ",
        "Sify's ADS program: 1 receipt, 3 underlying shares. ",
    ],
)
def test_a_depositary_ratio_claim_is_replaced_whatever_its_wording(claim: str) -> None:
    """R15-AGENT-090 batch 15: batches 13/14 recognised the claim by wording and
    every fresh phrasing escaped. A claim is now any unmarked number in a
    depositary sentence, so no wording is needed to catch it."""
    result = json.dumps(_SIFY_FUNDAMENTALS)
    assert (
        agent_runtime._guard_ratio_claims(claim, [result]) == agent_runtime.RATIO_UNAVAILABLE + " "
    )


def test_a_claim_split_over_two_sentences_is_replaced() -> None:
    """R15-AGENT-090 batch-14 live bar: 'For SIFY, one ordinary share represents
    1 share.' followed a sentence naming the ADR. The depositary context extends
    one sentence to a following one that speaks of shares with a count."""
    text = "SIFY trades as an ADR on Nasdaq. For SIFY, one ordinary share represents 1 share. "
    guarded = agent_runtime._guard_ratio_claims(text, [json.dumps(_SIFY_FUNDAMENTALS)])
    assert guarded == f"SIFY trades as an ADR on Nasdaq. {agent_runtime.RATIO_UNAVAILABLE} "
    # One hop only, and only a sentence about shares with a count.
    kept = "SIFY trades as an ADR on Nasdaq. Volume was 40,000 shares. It has 3 segments. "
    assert agent_runtime._guard_ratio_claims(kept, []) == kept


def test_the_depositary_context_does_not_depend_on_how_prose_is_released() -> None:
    """R15-AGENT-090 batch-15 review: the context is one hop whether the three
    sentences are guarded in one release or one release each. It was read off the
    replacement text (which names the ADR), so one release reached a second hop."""
    sentences = [
        "SIFY trades as an ADR on Nasdaq. ",
        "For SIFY, one ordinary share represents 1 share. ",
        "Holders hold 2 shares each. ",
    ]
    whole = agent_runtime._guard_ratio_claims("".join(sentences), [])
    piecewise, context, released = "", False, ""
    for sentence in sentences:
        piecewise += agent_runtime._guard_ratio_claims(sentence, [], context)
        released += sentence
        context = agent_runtime._depositary_context(released, context)
    assert whole == piecewise
    assert whole.endswith("Holders hold 2 shares each. ")


@pytest.mark.asyncio
async def test_the_depositary_context_survives_the_stream_chunking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The split claim is released sentence by sentence; the context carries
    from one release to the next."""
    deltas = [
        "SIFY trades as an ADR on Nasdaq. ",
        "For SIFY, one ordinary share repre",
        "sents 1 share. TTM rev",
    ]
    answer = await _scripted_answer(
        monkeypatch, "fundamentals", _SIFY_FUNDAMENTALS, [*deltas, "enue was ₹4,651 cr."]
    )
    assert answer == (
        f"SIFY trades as an ADR on Nasdaq. {agent_runtime.RATIO_UNAVAILABLE} "
        "TTM revenue was ₹4,651 cr."
    )


@pytest.mark.parametrize(
    "sentence",
    [
        "Each ADR closed at 5.20 USD on Friday. ",
        "Each ADS's 52-week high was 12.4. ",
        "SIFY's ADSs each gained 3 points in 2024. ",
        "the ADR traded between 10 and 12 dollars. ",
        "Each ADR closed at $12.50 on volume of 40,000 shares. ",
        "The PE ratio is 22.4. ",
        "Revenue represents 12% of the segment. ",
        "SIFY filed its 2024 20-F in July. ",
        "SIFY's ADR is one of the few Indian tech listings; it files an F-6 and 6-K reports. ",
        "The ADS rose 4% in Q1 FY25, its 3rd gain in two months. ",
        # batch-15 live (sify-3): a resolver disambiguation is not a ratio.
        "There are two possible matches: SPIIY (SPIE SA/ADR) and SPIWF (SPIE SA/ADR). ",
        "The ADR has 3 analyst ratings across 2 exchanges. ",
    ],
)
def test_a_marked_number_beside_a_depositary_term_streams_as_is(sentence: str) -> None:
    """R15-AGENT-090 batch 15: money, a decimal, a period, points, a year, a
    percent, a form name, a fiscal tag and an idiom are excluded by their own
    marker — 'each' beside an ADR no longer makes true prose a claim."""
    assert agent_runtime._guard_ratio_claims(sentence, [json.dumps(_SIFY_FUNDAMENTALS)]) == sentence


@pytest.mark.parametrize(
    "claim",
    [
        "Sify's ADS is backed by 5 of its equity shares. ",
        "The ADS conversion stood at 6 as the depositary set it. ",
    ],
)
def test_a_function_word_after_a_count_does_not_mark_it(claim: str) -> None:
    """R15-AGENT-090 batch 15: the plural-noun marker read 'its' / 'as' / 'this'
    as a counted noun, so '6 of its shares' escaped as 'a count of its'."""
    result = json.dumps(_SIFY_FUNDAMENTALS)
    assert (
        agent_runtime._guard_ratio_claims(claim, [result]) == agent_runtime.RATIO_UNAVAILABLE + " "
    )


@pytest.mark.parametrize(
    "claim",
    [
        "Each ADS represents 6 class A shares. ",
        "Each ADS represents 6 class A ordinary shares. ",
        "Each ADR represents 2 bonus shares. ",
        "The ADR stands for 4 class B common shares. ",
        "Each ADS represents 3 series C shares. ",
        "Each ADR equals 8 bonus class A shares. ",
        "Each ADS represents 4 class A preferred shares. ",
        "Each ADR represents 5 founder shares. ",
        "Each ADS represents 2 deferred shares. ",
    ],
)
def test_a_qualifier_before_shares_does_not_mark_the_count(claim: str) -> None:
    """R15-AGENT-090 batch 16: the plural-noun marker read a class qualifier
    ('class', 'bonus') as the counted noun, so live 'Each ADS represents 6 class
    A shares.' streamed unguarded."""
    result = json.dumps(_SIFY_FUNDAMENTALS)
    assert (
        agent_runtime._guard_ratio_claims(claim, [result]) == agent_runtime.RATIO_UNAVAILABLE + " "
    )


def test_a_lower_case_class_qualified_source_traces_its_count() -> None:
    """R15-AGENT-090 batch 16: the source side reads the same marker, so a cover
    statement in lower case sourced no count and the TRUE claim was replaced."""
    statement = "American Depositary Shares, each representing six class A ordinary shares"
    result = json.dumps({"ok": True, "ads_ratio": {"statement": statement}})
    sentence = "Each ADS represents 6 class A ordinary shares. "
    assert agent_runtime._guard_ratio_claims(sentence, [result]) == sentence


_SIFY_FUNDAMENTALS_WITH_DEPOSITARY = {
    **_SIFY_FUNDAMENTALS,
    "ads_ratio": {
        "ordinary_shares_per_ads": 6,
        "statement": "American Depositary Shares, each represented by Six Equity Shares",
        "provenance": {"source": "SEC 20-F cover page", "filed": "2026-06-26", "url": "x"},
    },
}


def test_a_sourced_count_must_sit_beside_the_depositary_term() -> None:
    """A tool result is read in segments: the fundamentals share count next to
    the ``ads_ratio`` block, and the filing date inside it, never source a
    ratio claim of their own."""
    result = json.dumps(_SIFY_FUNDAMENTALS_WITH_DEPOSITARY)
    assert agent_runtime._sourced_counts(result) == {"6"}
    for claim in ("Each ADS equals 144869230 ordinary shares. ", "1 ADR = 26 shares. "):
        assert agent_runtime._guard_ratio_claims(claim, [result]) == (
            agent_runtime.RATIO_UNAVAILABLE + " "
        )


@pytest.mark.parametrize(
    ("sentence", "result"),
    [
        ("The ADR-to-share ratio is 1 ADR : 6 shares. ", {"text": "Each Repr 6 Ords"}),
        (
            "Each ADS represents six ordinary shares. ",
            {"text": "Each American Depositary Share represents six (6) Ordinary Shares"},
        ),
        ("One SIFY ADS represents 6 equity shares. ", _SIFY_FUNDAMENTALS_WITH_DEPOSITARY),
        ("1 ADR = 6 shares. ", _SIFY_FUNDAMENTALS_WITH_DEPOSITARY),
    ],
)
def test_a_ratio_a_tool_result_carries_is_traced_and_kept(
    sentence: str, result: dict[str, Any]
) -> None:
    """R15-AGENT-090: a ratio a tool result of the run carries — a listing title,
    a filing sentence, or the ``depositary`` block the fundamentals tool reads
    off the 20-F cover — streams as is; the same claims against the bare
    fundamentals result are replaced."""
    assert agent_runtime._guard_ratio_claims(sentence, [json.dumps(result)]) == sentence
    assert agent_runtime._guard_ratio_claims(sentence, [json.dumps(_SIFY_FUNDAMENTALS)]) == (
        agent_runtime.RATIO_UNAVAILABLE + " "
    )
