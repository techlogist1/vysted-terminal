"""Agent runtime tests — discovery, validation, invocation.

The 12 first-party agent configs live in ``sidecar/agents/`` and are
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

from models.agent import AgentContextSnapshot
from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMMessage, LLMUsage
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


def test_first_party_roster_loads_twelve(tmp_path: Path) -> None:
    """The shipping ``sidecar/agents/`` directory loads all 12 first-party agents."""
    agent_runtime.reload()
    specs = agent_runtime.list_agents()
    ids = {spec.id for spec in specs}
    expected = {
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
    assert len(specs) == 12


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
    # 1 system (agent prompt) + 1 system (context preamble) + 1 user.
    assert [m.role for m in msgs] == ["system", "system", "user"]
    assert "AAPL" in msgs[1].content  # context preamble carries the symbol
    assert msgs[2].content == "is AAPL cheap?"
    assert provider.captured_kwargs is not None
    assert provider.captured_kwargs["api_key"] == "sk-test"


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
    # Just system + user when no context is supplied.
    assert [m.role for m in msgs] == ["system", "user"]


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
