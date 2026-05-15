"""Tests for the ``agents_store`` service — Custom Agent Builder persistence.

Mirrors the ``test_plugins.py`` shape: ``temp_data_dir`` redirects
``VYSTED_DATA_DIR`` at a ``tmp_path``; the store resolves the database path
per call so each test gets its own isolated SQLite file.
"""

from __future__ import annotations

import pytest

from config import DATA_DIR_ENV
from models.custom_agent import CustomAgentCreate, CustomAgentUpdate
from services import agents_store


@pytest.fixture
def temp_data_dir(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> object:
    """Redirect the sidecar data directory to an isolated temp path."""
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    return tmp_path


def _sample_create(agent_id: str = "custom:macro-quant") -> CustomAgentCreate:
    return CustomAgentCreate(
        id=agent_id,
        name="Macro Quant",
        philosophy="Mean reversion across macro asset classes.",
        system_prompt="You are a macro quant analyst. Reason from regime first.",
        tools=["price_data", "macro"],
        default_provider="anthropic",
        default_model="claude-opus-4-7",
        icon="brain",
    )


def _sample_update() -> CustomAgentUpdate:
    return CustomAgentUpdate(
        name="Macro Quant v2",
        philosophy="Regime-aware allocation.",
        system_prompt="You are a regime-aware macro allocator. Quote drawdowns.",
        tools=["price_data", "macro", "news"],
        default_provider="openai",
        default_model="gpt-4.1",
        icon="line-chart",
    )


def test_ensure_schema_is_idempotent(temp_data_dir: object) -> None:
    agents_store._ensure_schema()
    agents_store._ensure_schema()
    assert agents_store.list_agents() == []


def test_create_and_list_agent(temp_data_dir: object) -> None:
    stored = agents_store.create_agent(_sample_create(), now=1_700_000_000)
    assert stored.id == "custom:macro-quant"
    assert stored.name == "Macro Quant"
    assert stored.tools == ["price_data", "macro"]
    assert stored.default_provider == "anthropic"
    assert stored.created_at == 1_700_000_000
    assert stored.updated_at == 1_700_000_000

    agents = agents_store.list_agents()
    assert len(agents) == 1
    assert agents[0].id == "custom:macro-quant"


def test_list_agents_is_ordered_by_id(temp_data_dir: object) -> None:
    agents_store.create_agent(_sample_create("custom:zeta"))
    agents_store.create_agent(_sample_create("custom:alpha"))
    agents_store.create_agent(_sample_create("custom:mu"))
    ids = [agent.id for agent in agents_store.list_agents()]
    assert ids == ["custom:alpha", "custom:mu", "custom:zeta"]


def test_get_agent_roundtrip(temp_data_dir: object) -> None:
    agents_store.create_agent(_sample_create())
    fetched = agents_store.get_agent("custom:macro-quant")
    assert fetched is not None
    assert fetched.philosophy == "Mean reversion across macro asset classes."


def test_get_missing_agent_returns_none(temp_data_dir: object) -> None:
    assert agents_store.get_agent("custom:does-not-exist") is None


def test_create_duplicate_id_raises(temp_data_dir: object) -> None:
    agents_store.create_agent(_sample_create())
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        agents_store.create_agent(_sample_create())


def test_update_agent_replaces_mutable_fields(temp_data_dir: object) -> None:
    agents_store.create_agent(_sample_create(), now=1_700_000_000)
    updated = agents_store.update_agent("custom:macro-quant", _sample_update(), now=1_700_000_500)
    assert updated is not None
    assert updated.name == "Macro Quant v2"
    assert updated.default_provider == "openai"
    assert updated.tools == ["price_data", "macro", "news"]
    # created_at MUST be immutable; updated_at MUST advance.
    assert updated.created_at == 1_700_000_000
    assert updated.updated_at == 1_700_000_500


def test_update_missing_agent_returns_none(temp_data_dir: object) -> None:
    assert agents_store.update_agent("custom:nope", _sample_update()) is None


def test_delete_agent(temp_data_dir: object) -> None:
    agents_store.create_agent(_sample_create())
    assert agents_store.delete_agent("custom:macro-quant") is True
    assert agents_store.list_agents() == []


def test_delete_missing_agent_returns_false(temp_data_dir: object) -> None:
    assert agents_store.delete_agent("custom:nope") is False


def test_tools_json_roundtrips_empty_list(temp_data_dir: object) -> None:
    payload = CustomAgentCreate(
        id="custom:tool-less",
        name="Minimal",
        philosophy="No-tool reasoner.",
        system_prompt="Answer only from the conversation.",
        tools=[],
        default_provider="ollama",
    )
    stored = agents_store.create_agent(payload)
    assert stored.tools == []
    # Fetch round-trips the empty list verbatim, not as None.
    fetched = agents_store.get_agent("custom:tool-less")
    assert fetched is not None
    assert fetched.tools == []


def test_optional_fields_persist_as_null(temp_data_dir: object) -> None:
    payload = CustomAgentCreate(
        id="custom:bare",
        name="Bare",
        philosophy="Defaults only.",
        system_prompt="Be concise.",
        tools=[],
        default_provider="anthropic",
    )
    stored = agents_store.create_agent(payload)
    assert stored.default_model is None
    assert stored.icon is None
