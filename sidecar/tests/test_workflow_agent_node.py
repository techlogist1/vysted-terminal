"""ai.agent_invoke credentials and failure semantics (R15-AGENT-016, R15-CODE-PLATFORM-003).

The run request carries the foreground provider/model/key; the node fails
visibly on any LLM error instead of returning placeholder text as the answer;
a node config never carries a key.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMErrorEvent
from models.workflow import WorkflowSpec
from services import workflow_engine, workflow_nodes


@pytest.fixture(autouse=True)
def _builtins() -> None:
    workflow_engine.reset_registry_for_tests()
    workflow_nodes.register_all()
    yield
    workflow_engine.reset_registry_for_tests()


def _spec_json(agent_config: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "wf-agent",
        "name": "agent",
        "version": 1,
        "nodes": [
            {
                "id": "a",
                "type": "ai.agent_invoke",
                "position": {"x": 0, "y": 0},
                "config": agent_config,
            }
        ],
        "edges": [],
        "updatedAt": 0,
    }


@pytest.mark.asyncio
async def test_adapter_error_fails_the_node_and_the_run(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_invoke(agent_id: str, prompt: str, **_: Any):
        yield LLMErrorEvent(message="401 invalid x-api-key")
        yield LLMDoneEvent()

    monkeypatch.setattr("services.agent_runtime.invoke_agent", _fake_invoke)
    spec = WorkflowSpec.model_validate(_spec_json({"agent_id": "buffett"}))
    result = await workflow_engine.run_workflow(spec)
    node = result.nodes[0]
    assert node.status == "error"
    assert "401 invalid x-api-key" in (node.error or "")
    assert result.status == "error"
    assert "'a'" in (result.error or "")


@pytest.mark.asyncio
async def test_unknown_agent_id_fails_the_node() -> None:
    spec = WorkflowSpec.model_validate(_spec_json({"agent_id": "no-such-agent"}))
    result = await workflow_engine.run_workflow(spec)
    assert result.status == "error"
    assert "unknown agent" in (result.nodes[0].error or "")


def test_config_api_key_is_rejected_on_save_and_run(client: TestClient) -> None:
    spec = _spec_json({"agent_id": "buffett", "api_key": "sk-plaintext"})
    assert client.post("/workflow/save", json=spec).status_code == 422
    assert client.post("/workflow/run", json={"spec": spec}).status_code == 422


def test_run_request_creds_reach_the_agent(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, Any] = {}

    async def _fake_invoke(agent_id: str, prompt: str, **kwargs: Any):
        seen.update(kwargs)
        yield LLMDeltaEvent(text="ok")
        yield LLMDoneEvent()

    monkeypatch.setattr("services.agent_runtime.invoke_agent", _fake_invoke)
    body = {
        "spec": _spec_json({"agent_id": "buffett", "prompt_template": "hi"}),
        "provider": "openai",
        "model": "gpt-4o-mini",
        "apiKey": "sk-test",
    }
    with client.stream("POST", "/workflow/run", json=body) as response:
        frames = [
            json.loads(line[len("data: ") :])
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]
    assert frames[-1]["kind"] == "run-complete"
    assert (seen["provider"], seen["model"], seen["api_key"]) == (
        "openai",
        "gpt-4o-mini",
        "sk-test",
    )
