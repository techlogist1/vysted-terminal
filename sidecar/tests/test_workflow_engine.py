"""Tests for the workflow engine.

The engine is registry-driven (concrete node types are Teammate W work).
These tests register stub handlers per-test so the engine surface is
exercised end-to-end without depending on any production node-type
implementations.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from config import DATA_DIR_ENV
from models.workflow import (
    WorkflowEdge,
    WorkflowNode,
    WorkflowRunEvent,
    WorkflowSpec,
)
from services import workflow_engine, workflow_store
from services.workflow_engine import WorkflowEngineError


@pytest.fixture
def temp_data_dir(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> object:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    return tmp_path


@pytest.fixture(autouse=True)
def isolated_registry() -> None:
    workflow_engine.reset_registry_for_tests()
    yield
    workflow_engine.reset_registry_for_tests()


def _node(node_id: str, type_id: str, config: dict[str, Any] | None = None) -> WorkflowNode:
    return WorkflowNode(
        id=node_id,
        type=type_id,
        position={"x": 0.0, "y": 0.0},  # type: ignore[arg-type]
        config=config or {},
    )


def _edge(
    eid: str, source: str, target: str, sport: str = "out", tport: str = "in"
) -> WorkflowEdge:
    return WorkflowEdge(
        id=eid,
        sourceNode=source,
        sourcePort=sport,
        targetNode=target,
        targetPort=tport,
    )


def _spec(nodes: list[WorkflowNode], edges: list[WorkflowEdge]) -> WorkflowSpec:
    return WorkflowSpec(
        id="wf-test",
        name="Test workflow",
        version=1,
        nodes=nodes,
        edges=edges,
        updatedAt=0,
    )


# ---------------------------------------------------------------------------
# Spec validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unregistered_node_type_raises() -> None:
    spec = _spec([_node("a", "no.such.type")], [])
    with pytest.raises(WorkflowEngineError, match="unregistered type"):
        await workflow_engine.run_workflow(spec)


@pytest.mark.asyncio
async def test_cycle_detection() -> None:
    workflow_engine.register_node_type("t", _passthrough())
    spec = _spec(
        [_node("a", "t"), _node("b", "t")],
        [_edge("e1", "a", "b"), _edge("e2", "b", "a")],
    )
    with pytest.raises(WorkflowEngineError, match="cycle"):
        await workflow_engine.run_workflow(spec)


@pytest.mark.asyncio
async def test_unknown_node_in_edge_raises() -> None:
    workflow_engine.register_node_type("t", _passthrough())
    spec = _spec([_node("a", "t")], [_edge("e1", "a", "ghost")])
    with pytest.raises(WorkflowEngineError, match="unknown target node"):
        await workflow_engine.run_workflow(spec)


# ---------------------------------------------------------------------------
# Happy paths + observability
# ---------------------------------------------------------------------------


def _passthrough():
    async def _h(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        return {"out": inputs.get("in", config.get("default"))}

    return _h


@pytest.mark.asyncio
async def test_single_node_runs_and_emits_events() -> None:
    workflow_engine.register_node_type("t", _passthrough())
    events: list[WorkflowRunEvent] = []

    async def _on(event: WorkflowRunEvent) -> None:
        events.append(event)

    spec = _spec([_node("a", "t", {"default": "hello"})], [])
    result = await workflow_engine.run_workflow(spec, inputs={"in": "world"}, on_event=_on)

    assert result.status == "ok"
    assert len(result.nodes) == 1
    assert result.nodes[0].outputs == {"out": "world"}

    kinds = [e.kind for e in events]
    assert kinds == ["run-start", "node-start", "node-output", "run-complete"]


@pytest.mark.asyncio
async def test_chain_passes_outputs() -> None:
    async def _emit_value(_inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        return {"out": config["value"]}

    async def _double(inputs: dict[str, Any], _config: dict[str, Any]) -> dict[str, Any]:
        return {"out": inputs["in"] * 2}

    workflow_engine.register_node_type("emit", _emit_value)
    workflow_engine.register_node_type("double", _double)

    spec = _spec(
        [_node("a", "emit", {"value": 5}), _node("b", "double")],
        [_edge("e1", "a", "b")],
    )
    result = await workflow_engine.run_workflow(spec)
    assert result.status == "ok"
    by_id = {n.node_id: n for n in result.nodes}
    assert by_id["b"].outputs == {"out": 10}


@pytest.mark.asyncio
async def test_parallel_nodes_run_concurrently() -> None:
    async def _slow(_inputs: dict[str, Any], _config: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0.05)
        return {"out": True}

    workflow_engine.register_node_type("slow", _slow)
    spec = _spec(
        [_node(f"n{i}", "slow") for i in range(5)],
        [],  # no edges — all source nodes
    )

    start = asyncio.get_event_loop().time()
    result = await workflow_engine.run_workflow(spec)
    elapsed = asyncio.get_event_loop().time() - start

    assert result.status == "ok"
    # 5 nodes * 50ms each would be 250ms sequential. Concurrent should be ~50ms.
    assert elapsed < 0.2


# ---------------------------------------------------------------------------
# Error propagation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_node_error_marks_downstream_failed() -> None:
    async def _bad(_inputs: dict[str, Any], _config: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("boom")

    async def _good(_inputs: dict[str, Any], _config: dict[str, Any]) -> dict[str, Any]:
        return {"out": "ok"}

    workflow_engine.register_node_type("bad", _bad)
    workflow_engine.register_node_type("good", _good)

    spec = _spec(
        [_node("a", "bad"), _node("b", "good")],
        [_edge("e1", "a", "b")],
    )
    result = await workflow_engine.run_workflow(spec)
    assert result.status == "error"
    by_id = {n.node_id: n for n in result.nodes}
    assert by_id["a"].status == "error"
    assert by_id["a"].error == "boom"
    assert by_id["b"].status == "error"
    assert by_id["b"].error == "upstream node failed"


# ---------------------------------------------------------------------------
# Control flow: branch skip, per-node scheduling, per-node timeout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_branch_skips_the_untaken_path_and_its_descendants() -> None:
    from services import workflow_nodes

    workflow_nodes.register_all()
    events: list[WorkflowRunEvent] = []

    async def _on(event: WorkflowRunEvent) -> None:
        events.append(event)

    spec = _spec(
        [
            _node("branch", "logic.branch"),
            _node("notify", "action.notify_desktop"),
            _node("log", "action.log"),
            _node("taken", "action.log"),
        ],
        [
            _edge("e1", "branch", "notify", "false_path", "value"),
            _edge("e2", "notify", "log", "message", "value"),
            _edge("e3", "branch", "taken", "true_path", "value"),
        ],
    )
    result = await workflow_engine.run_workflow(spec, inputs={"value": "yes"}, on_event=_on)

    by_id = {n.node_id: n for n in result.nodes}
    assert result.status == "ok"
    assert by_id["notify"].status == "skipped"
    # Two hops below the un-taken port: the skip propagates.
    assert by_id["log"].status == "skipped"
    assert by_id["taken"].status == "ok"
    assert by_id["branch"].outputs == {"true_path": "yes"}
    started = {e.node_id for e in events if e.kind == "node-start"}
    assert started == {"branch", "taken"}
    skipped = {e.node_id for e in events if e.kind == "node-skipped"}
    assert skipped == {"notify", "log"}


@pytest.mark.asyncio
async def test_a_completion_releases_its_dependants_without_waiting_for_slow_siblings() -> None:
    release_a = asyncio.Event()
    c_started = asyncio.Event()

    async def _slow(_inputs: dict[str, Any], _config: dict[str, Any]) -> dict[str, Any]:
        await release_a.wait()
        return {"out": "a"}

    async def _fast(_inputs: dict[str, Any], _config: dict[str, Any]) -> dict[str, Any]:
        return {"out": "b"}

    async def _dependant(inputs: dict[str, Any], _config: dict[str, Any]) -> dict[str, Any]:
        c_started.set()
        return {"out": inputs["in"]}

    workflow_engine.register_node_type("slow", _slow)
    workflow_engine.register_node_type("fast", _fast)
    workflow_engine.register_node_type("dep", _dependant)
    spec = _spec(
        [_node("a", "slow"), _node("b", "fast"), _node("c", "dep")],
        [_edge("e1", "b", "c")],
    )
    run = asyncio.create_task(workflow_engine.run_workflow(spec))
    # C starts while A is still blocked (it would deadlock under a wave barrier).
    await asyncio.wait_for(c_started.wait(), timeout=2)
    assert not run.done()
    release_a.set()
    result = await run
    assert result.status == "ok"


@pytest.mark.asyncio
async def test_hung_handler_ends_the_node_in_error_at_its_timeout() -> None:
    async def _hang(_inputs: dict[str, Any], _config: dict[str, Any]) -> dict[str, Any]:
        await asyncio.Event().wait()
        return {}

    workflow_engine.register_node_type("hang", _hang)
    workflow_engine.register_node_type("t", _passthrough())
    spec = _spec(
        [_node("a", "hang", {"timeout_seconds": 0.05}), _node("b", "t")],
        [_edge("e1", "a", "b")],
    )
    result = await asyncio.wait_for(workflow_engine.run_workflow(spec), timeout=2)
    by_id = {n.node_id: n for n in result.nodes}
    assert result.status == "error"
    assert by_id["a"].status == "error"
    assert by_id["a"].error == "node timed out after 0.05s"
    assert by_id["b"].error == "upstream node failed"


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


def test_workflow_store_round_trip(temp_data_dir: object) -> None:
    spec = _spec([_node("a", "t")], [])
    # Register the type so spec validation passes when the store reload
    # runs a fresh engine validation cycle.
    workflow_engine.register_node_type("t", _passthrough())

    stored = workflow_store.save_workflow(spec)
    assert stored.id == spec.id
    assert stored.updated_at > 0

    loaded = workflow_store.get_workflow(spec.id)
    assert loaded is not None
    assert loaded.name == spec.name
    assert len(loaded.nodes) == 1


def test_workflow_store_list_and_delete(temp_data_dir: object) -> None:
    workflow_engine.register_node_type("t", _passthrough())
    a = _spec([_node("a", "t")], [])
    a = a.model_copy(update={"id": "wf-a"})
    b = a.model_copy(update={"id": "wf-b", "name": "Other"})

    workflow_store.save_workflow(a)
    workflow_store.save_workflow(b)

    saved = workflow_store.list_workflows()
    assert {s.id for s in saved} == {"wf-a", "wf-b"}

    assert workflow_store.delete_workflow("wf-a") is True
    assert workflow_store.delete_workflow("wf-a") is False  # idempotent
    remaining = workflow_store.list_workflows()
    assert {s.id for s in remaining} == {"wf-b"}
