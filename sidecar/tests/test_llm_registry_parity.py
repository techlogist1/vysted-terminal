"""The LLM dispatch and the agent schema derive from config/model_registry.json.

R15-CODE-AGENT-007 / R15-CODE-AGENT-016: the base URLs and the agent schema's
provider enum were hand copies beside the registry.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services import agent_runtime, model_registry
from services.llm import get_provider


def test_registry_base_url_reaches_get_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    row = model_registry._PROVIDERS_BY_ID["deepseek"]
    monkeypatch.setitem(row, "default_base_url", "https://deepseek.example/v9")
    assert get_provider("deepseek")._base_url == "https://deepseek.example/v9"


def test_loaded_schema_provider_enum_is_the_registry() -> None:
    enum = agent_runtime._load_schema()["properties"]["defaultProvider"]["enum"]
    assert set(enum) == set(model_registry.provider_ids())


def test_an_openrouter_agent_json_loads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "id": "router",
        "name": "Router",
        "philosophy": "p",
        "systemPrompt": "x" * 60,
        "tools": ["price_data"],
        "defaultProvider": "openrouter",
    }
    (tmp_path / "router.json").write_text(json.dumps(payload), encoding="utf-8")
    specs, _ = agent_runtime._discover_specs(tmp_path)
    assert specs["router"].default_provider == "openrouter"
