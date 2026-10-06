"""Tests for the /custom-agents router.

Covers the full CRUD lifecycle and every validation rule the Custom Agent
Builder UI depends on:

- ``custom:`` prefix enforced on create body, URL path, and update body
  consistency.
- Unknown tool ids rejected at the wire boundary.
- Unknown provider ids rejected at the wire boundary.
- Uniqueness on ``id`` surfaces as 409, not 500.
- 404 for missing rows on get/update/delete.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from config import DATA_DIR_ENV


@pytest.fixture
def temp_data_dir(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> object:
    """Redirect the sidecar data directory to an isolated temp path."""
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    return tmp_path


def _valid_create_body(agent_id: str = "custom:macro-quant") -> dict:
    return {
        "id": agent_id,
        "name": "Macro Quant",
        "philosophy": "Mean reversion across macro asset classes.",
        "system_prompt": "You are a macro quant analyst.",
        "tools": ["price_data", "macro_series"],
        "default_provider": "anthropic",
        "default_model": "claude-opus-4-8",
        "icon": "brain",
    }


def _valid_update_body() -> dict:
    return {
        "name": "Macro Quant v2",
        "philosophy": "Regime-aware allocator.",
        "system_prompt": "You are a regime-aware allocator.",
        "tools": ["price_data", "earnings_history"],
        "default_provider": "openai",
        "default_model": "gpt-4.1",
        "icon": "line-chart",
    }


# --------------------------------------------------------------------------
# List
# --------------------------------------------------------------------------


def test_list_custom_agents_empty(client: TestClient, temp_data_dir: object) -> None:
    response = client.get("/custom-agents")
    assert response.status_code == 200
    assert response.json() == []


def test_list_custom_agents_after_create(client: TestClient, temp_data_dir: object) -> None:
    client.post("/custom-agents", json=_valid_create_body())
    body = client.get("/custom-agents").json()
    assert len(body) == 1
    assert body[0]["id"] == "custom:macro-quant"


# --------------------------------------------------------------------------
# Tool ids (R15-UI-003 / R15-CODE-FRONTEND-020)
# --------------------------------------------------------------------------


def test_tool_ids_equals_agent_selectable_tool_ids(client: TestClient) -> None:
    """The route is the ONE source the builder reads — it must equal the
    same function `models.custom_agent.KNOWN_TOOL_IDS` derives from, so the
    builder can never drift from the host's actual capability catalog."""
    from services.agent_tools.catalog import agent_selectable_tool_ids

    response = client.get("/custom-agents/tool-ids")
    assert response.status_code == 200
    assert response.json() == sorted(agent_selectable_tool_ids())


def test_tool_ids_route_not_swallowed_by_agent_id_path(client: TestClient) -> None:
    """`/tool-ids` must resolve to the dedicated route, not `/{agent_id:path}`
    (which would 400 on a non-`custom:`-prefixed id)."""
    response = client.get("/custom-agents/tool-ids")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# --------------------------------------------------------------------------
# Create
# --------------------------------------------------------------------------


def test_create_custom_agent(client: TestClient, temp_data_dir: object) -> None:
    response = client.post("/custom-agents", json=_valid_create_body())
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == "custom:macro-quant"
    assert body["name"] == "Macro Quant"
    assert body["tools"] == ["price_data", "macro_series"]
    assert body["default_provider"] == "anthropic"
    assert body["default_model"] == "claude-opus-4-8"
    assert isinstance(body["created_at"], int)
    assert body["created_at"] == body["updated_at"]


def test_create_rejects_id_without_custom_prefix(client: TestClient, temp_data_dir: object) -> None:
    body = _valid_create_body()
    body["id"] = "buffett"  # collision with a first-party id
    response = client.post("/custom-agents", json=body)
    assert response.status_code == 422


def test_create_rejects_bare_custom_prefix(client: TestClient, temp_data_dir: object) -> None:
    body = _valid_create_body()
    body["id"] = "custom:"
    response = client.post("/custom-agents", json=body)
    assert response.status_code == 422


def test_create_rejects_unknown_tool(client: TestClient, temp_data_dir: object) -> None:
    body = _valid_create_body()
    body["tools"] = ["price_data", "execute_order"]  # not on allow-list
    response = client.post("/custom-agents", json=body)
    assert response.status_code == 422


def test_create_rejects_unknown_provider(client: TestClient, temp_data_dir: object) -> None:
    body = _valid_create_body()
    body["default_provider"] = "cohere"
    response = client.post("/custom-agents", json=body)
    assert response.status_code == 422


def test_create_dedupes_tools(client: TestClient, temp_data_dir: object) -> None:
    body = _valid_create_body()
    body["tools"] = ["price_data", "macro_series", "price_data"]
    response = client.post("/custom-agents", json=body)
    assert response.status_code == 201
    assert response.json()["tools"] == ["price_data", "macro_series"]


def test_create_duplicate_id_returns_409(client: TestClient, temp_data_dir: object) -> None:
    client.post("/custom-agents", json=_valid_create_body())
    response = client.post("/custom-agents", json=_valid_create_body())
    assert response.status_code == 409


# --------------------------------------------------------------------------
# Read one
# --------------------------------------------------------------------------


def test_get_custom_agent(client: TestClient, temp_data_dir: object) -> None:
    client.post("/custom-agents", json=_valid_create_body())
    response = client.get("/custom-agents/custom:macro-quant")
    assert response.status_code == 200
    assert response.json()["id"] == "custom:macro-quant"


def test_get_missing_custom_agent_returns_404(client: TestClient, temp_data_dir: object) -> None:
    response = client.get("/custom-agents/custom:does-not-exist")
    assert response.status_code == 404


def test_get_non_prefixed_id_returns_400(client: TestClient, temp_data_dir: object) -> None:
    response = client.get("/custom-agents/buffett")
    assert response.status_code == 400


# --------------------------------------------------------------------------
# Update
# --------------------------------------------------------------------------


def test_update_custom_agent(client: TestClient, temp_data_dir: object) -> None:
    client.post("/custom-agents", json=_valid_create_body())
    response = client.put("/custom-agents/custom:macro-quant", json=_valid_update_body())
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Macro Quant v2"
    assert body["default_provider"] == "openai"
    assert body["tools"] == ["price_data", "earnings_history"]
    # updated_at should never be before created_at after an update.
    assert body["updated_at"] >= body["created_at"]


def test_update_missing_custom_agent_returns_404(client: TestClient, temp_data_dir: object) -> None:
    response = client.put("/custom-agents/custom:nope", json=_valid_update_body())
    assert response.status_code == 404


def test_update_rejects_non_prefixed_path(client: TestClient, temp_data_dir: object) -> None:
    response = client.put("/custom-agents/buffett", json=_valid_update_body())
    assert response.status_code == 400


def test_update_rejects_unknown_tool(client: TestClient, temp_data_dir: object) -> None:
    client.post("/custom-agents", json=_valid_create_body())
    body = _valid_update_body()
    body["tools"] = ["price_data", "execute_order"]
    response = client.put("/custom-agents/custom:macro-quant", json=body)
    assert response.status_code == 422


# --------------------------------------------------------------------------
# Delete
# --------------------------------------------------------------------------


def test_delete_custom_agent(client: TestClient, temp_data_dir: object) -> None:
    client.post("/custom-agents", json=_valid_create_body())
    response = client.delete("/custom-agents/custom:macro-quant")
    assert response.status_code == 204
    assert client.get("/custom-agents").json() == []


def test_delete_missing_custom_agent_returns_404(client: TestClient, temp_data_dir: object) -> None:
    response = client.delete("/custom-agents/custom:nope")
    assert response.status_code == 404


def test_delete_non_prefixed_id_returns_400(client: TestClient, temp_data_dir: object) -> None:
    response = client.delete("/custom-agents/buffett")
    assert response.status_code == 400


# --------------------------------------------------------------------------
# Round-trip — full CRUD lifecycle
# --------------------------------------------------------------------------


def test_full_crud_lifecycle(client: TestClient, temp_data_dir: object) -> None:
    """Create → read → list → update → delete in one test, to catch regressions
    in any single step that the per-endpoint tests might mask."""
    # Create
    created = client.post("/custom-agents", json=_valid_create_body()).json()
    assert created["id"] == "custom:macro-quant"

    # Read one
    fetched = client.get("/custom-agents/custom:macro-quant").json()
    assert fetched == created

    # List
    listing = client.get("/custom-agents").json()
    assert listing == [created]

    # Update
    updated = client.put("/custom-agents/custom:macro-quant", json=_valid_update_body()).json()
    assert updated["name"] == "Macro Quant v2"
    assert updated["created_at"] == created["created_at"]

    # Delete
    assert client.delete("/custom-agents/custom:macro-quant").status_code == 204
    assert client.get("/custom-agents").json() == []


# --------------------------------------------------------------------------
# Renamed / retired tool ids on a stored agent (R15-LIFECYCLE-025)
# --------------------------------------------------------------------------


def _store_agent_with_tools(tools: list[str]) -> None:
    """Persist an agent as an older build wrote it: its tool list is not
    re-validated against today's catalog."""
    from models.custom_agent import CustomAgentCreate
    from services import agents_store

    agents_store.create_agent(
        CustomAgentCreate.model_construct(**{**_valid_create_body(), "tools": tools})
    )


def _sent_tool_ids(monkeypatch: pytest.MonkeyPatch) -> tuple[list[str], list[object]]:
    """Run one turn of the stored agent; return the tool ids its adapter got."""
    import asyncio

    from models.llm import LLMDeltaEvent, LLMDoneEvent
    from services import agent_runtime

    sent: list[str] = []

    class _Provider:
        async def stream_chat(self, messages: object, **kwargs: object):  # noqa: ANN202
            sent.extend(kwargs["tool_ids"])  # type: ignore[arg-type]
            yield LLMDeltaEvent(text="ok")
            yield LLMDoneEvent()

    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: _Provider())

    async def _run() -> list[object]:
        return [
            e
            async for e in agent_runtime.invoke_agent(
                agent_id="custom:macro-quant", prompt="10y yield", api_key="k", mode="edit"
            )
        ]

    return sent, asyncio.run(_run())


def test_a_stored_agent_naming_a_renamed_tool_gets_it_and_puts_cleanly(
    client: TestClient, temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    from services.agent_tools import schemas

    _store_agent_with_tools(["price_data", "macro"])

    sent, _events = _sent_tool_ids(monkeypatch)
    assert "macro_series" in sent and "macro" not in sent
    assert "macro_series" in {t["function"]["name"] for t in schemas.openai_tools(sent)}

    stored = client.get("/custom-agents/custom:macro-quant").json()
    body = {k: stored[k] for k in _valid_update_body()}
    response = client.put("/custom-agents/custom:macro-quant", json=body)
    assert response.status_code == 200, response.text
    assert response.json()["tools"] == ["price_data", "macro_series"]


def test_a_stored_agent_naming_a_removed_tool_runs_without_it_and_says_so_once(
    client: TestClient, temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    from services import agent_runtime

    _store_agent_with_tools(["price_data", "options_flow_v0"])

    sent, events = _sent_tool_ids(monkeypatch)
    assert "options_flow_v0" not in sent and "price_data" in sent
    notices = [
        e for e in events if getattr(e, "tool", None) == agent_runtime.RETIRED_TOOLS_NOTICE_TOOL
    ]
    assert len(notices) == 1
    assert "options_flow_v0 is no longer available" in notices[0].detail  # type: ignore[attr-defined]
