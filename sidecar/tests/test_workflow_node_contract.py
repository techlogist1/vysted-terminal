"""The built-in node contract the palette and the handlers share (R15-CODE-PLATFORM-002).

``node-registry.ts`` copies port ids and config keys verbatim into the spec
(``graph-state.flowToSpec``), so every name must be one the handler reads.
``fixtures/workflow_node_types.json`` is the declared contract; this file pins
it to the sidecar, ``node-registry.test.ts`` pins the palette to it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from models.workflow import WorkflowSpec
from services import workflow_engine, workflow_nodes
from services.workflow_nodes import builtin

FIXTURE = Path(__file__).parent / "fixtures" / "workflow_node_types.json"


@pytest.fixture(autouse=True)
def _builtins() -> None:
    workflow_engine.reset_registry_for_tests()
    workflow_nodes.register_all()
    yield
    workflow_engine.reset_registry_for_tests()


def _palette_spec(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> WorkflowSpec:
    """A spec in the exact wire shape ``flowToSpec`` builds."""
    return WorkflowSpec.model_validate(
        {
            "id": "wf-palette",
            "name": "palette",
            "version": 1,
            "nodes": [{"position": {"x": 0, "y": 0}, **n} for n in nodes],
            "edges": edges,
            "updatedAt": 0,
        }
    )


def test_fixture_is_the_declared_builtin_contract() -> None:
    assert json.loads(FIXTURE.read_text(encoding="utf-8")) == workflow_nodes.BUILTIN_NODE_SPECS


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("type_id", "handler", "inputs", "config"),
    [
        ("logic.branch", builtin.logic_branch, {"value": 1}, {}),
        ("logic.compare", builtin.logic_compare, {"a": 1, "b": 2}, {"op": "neq"}),
        ("action.log", builtin.action_log, {"value": "x"}, {}),
        ("action.notify_desktop", builtin.action_notify_desktop, {"value": "x"}, {}),
        ("transform.json_path", builtin.transform_json_path, {"value": {"a": 1}}, {"path": "a"}),
        ("flow.sleep", builtin.flow_sleep, {"value": 1}, {"seconds": 0}),
    ],
)
async def test_declared_outputs_are_what_the_handler_returns(
    type_id: str, handler: Any, inputs: dict[str, Any], config: dict[str, Any]
) -> None:
    outputs = await handler(inputs, config)
    assert sorted(outputs) == sorted(workflow_nodes.BUILTIN_NODE_SPECS[type_id]["outputs"])


@pytest.mark.asyncio
async def test_palette_invoke_agent_runs_with_the_typed_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from models.llm import LLMDeltaEvent, LLMDoneEvent

    seen: list[str] = []

    async def _fake_invoke(agent_id: str, prompt: str, **_: Any):
        seen.append(prompt)
        yield LLMDeltaEvent(text="ok")
        yield LLMDoneEvent()

    monkeypatch.setattr("services.agent_runtime.invoke_agent", _fake_invoke)
    spec = _palette_spec(
        [
            {
                "id": "a",
                "type": "ai.agent_invoke",
                "config": {"agent_id": "buffett", "prompt_template": "Outlook for NVDA?"},
            }
        ],
        [],
    )
    result = await workflow_engine.run_workflow(spec)
    assert result.status == "ok"
    assert seen == ["Outlook for NVDA?"]


@pytest.mark.asyncio
async def test_palette_json_path_to_log_carries_the_extracted_value() -> None:
    spec = _palette_spec(
        [
            {"id": "src", "type": "flow.sleep", "config": {"seconds": 0}},
            {"id": "jp", "type": "transform.json_path", "config": {"path": "quote.price"}},
            {"id": "log", "type": "action.log", "config": {"level": "info"}},
        ],
        [
            {
                "id": "e1",
                "sourceNode": "src",
                "sourcePort": "value",
                "targetNode": "jp",
                "targetPort": "value",
            },
            {
                "id": "e2",
                "sourceNode": "jp",
                "sourcePort": "extracted",
                "targetNode": "log",
                "targetPort": "value",
            },
        ],
    )
    result = await workflow_engine.run_workflow(spec, inputs={"value": {"quote": {"price": 192.5}}})
    by_id = {n.node_id: n for n in result.nodes}
    assert by_id["jp"].outputs["extracted"] == 192.5
    assert by_id["log"].outputs["message"] == "192.5"
