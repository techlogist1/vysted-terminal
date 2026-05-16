"""Custom asyncio workflow engine — Phase 4 foundation.

Topologically sorts a :class:`WorkflowSpec` DAG, runs nodes with no
upstream deps concurrently via ``asyncio.gather``, runs downstream nodes
when their inputs are available, and emits :class:`WorkflowRunEvent`
events through an optional ``on_event`` callback for SSE streaming.

The engine is intentionally minimal — concrete node-type handlers are
the v0.5.0 Teammate W deliverable, registered via :func:`register_node_type`
into a module-level registry. Plugin-contributed nodes (via the
``contributesNodes`` capability on the locked ``VystedPlugin`` contract)
register through the same surface.

Why custom, not Prefect/Dagster:
- Prefect/Dagster are server orchestrators, wrong shape for a desktop
  sidecar that needs zero-config local execution.
- asyncio + Pydantic gives per-node observability + parallel waves +
  partial replay in <300 lines of focused code.
- Sidecar bundle stays lean (no orchestrator deps; v0.4.0 main is 67 MB,
  budget 120 MB).
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from models.workflow import (
    NodeRunResult,
    WorkflowEdge,
    WorkflowNode,
    WorkflowRunEvent,
    WorkflowRunResult,
    WorkflowSpec,
)

logger = logging.getLogger(__name__)

#: Node-handler signature. Receives (inputs_by_port, node_config) and
#: returns outputs_by_port. Free-form ``dict[str, Any]`` because each node
#: type owns its own schema. Handlers are async so they can fire HTTP,
#: invoke an agent, sleep, etc.
NodeHandler = Callable[[dict[str, Any], dict[str, Any]], Awaitable[dict[str, Any]]]

EventCallback = Callable[[WorkflowRunEvent], Awaitable[None]]


class WorkflowEngineError(RuntimeError):
    """Raised on spec validation or runtime failures."""


# ---------------------------------------------------------------------------
# Node-type registry
# ---------------------------------------------------------------------------

_HANDLERS: dict[str, NodeHandler] = {}


def register_node_type(type_id: str, handler: NodeHandler) -> None:
    """Register a node-type handler. Overwrites any prior registration."""
    _HANDLERS[type_id] = handler
    logger.debug("workflow_engine: registered node type %r", type_id)


def unregister_node_type(type_id: str) -> None:
    """Remove a previously registered handler (test helper)."""
    _HANDLERS.pop(type_id, None)


def registered_node_types() -> list[str]:
    """List currently registered node type ids."""
    return sorted(_HANDLERS)


def reset_registry_for_tests() -> None:
    """Drop all registered handlers — test helper."""
    _HANDLERS.clear()


# ---------------------------------------------------------------------------
# DAG validation + topological waves
# ---------------------------------------------------------------------------


def _validate_spec(spec: WorkflowSpec) -> dict[str, WorkflowNode]:
    """Validate the spec is well-formed; return a {id: node} map.

    Checks:
      - node ids unique
      - edges reference existing node ids
      - no cycles (via topological sort attempt)
      - every node type is registered (or we'll fail at run time anyway,
        but catching it now gives a clearer error)
    """
    nodes_by_id: dict[str, WorkflowNode] = {}
    for node in spec.nodes:
        if node.id in nodes_by_id:
            raise WorkflowEngineError(f"duplicate node id {node.id!r}")
        nodes_by_id[node.id] = node

    for edge in spec.edges:
        if edge.source_node not in nodes_by_id:
            raise WorkflowEngineError(
                f"edge {edge.id} references unknown source node {edge.source_node!r}"
            )
        if edge.target_node not in nodes_by_id:
            raise WorkflowEngineError(
                f"edge {edge.id} references unknown target node {edge.target_node!r}"
            )

    for node in spec.nodes:
        if node.type not in _HANDLERS:
            raise WorkflowEngineError(
                f"node {node.id!r} uses unregistered type {node.type!r}; "
                f"registered: {registered_node_types()}"
            )

    # Cycle detection via Kahn's algorithm; we re-use the result to drive
    # execution waves later.
    _topological_order(nodes_by_id, spec.edges)
    return nodes_by_id


def _topological_order(
    nodes_by_id: dict[str, WorkflowNode],
    edges: list[WorkflowEdge],
) -> list[str]:
    """Return a stable topological order of node ids; raise on cycle."""
    in_degree: dict[str, int] = {nid: 0 for nid in nodes_by_id}
    children: dict[str, list[str]] = {nid: [] for nid in nodes_by_id}
    for edge in edges:
        in_degree[edge.target_node] += 1
        children[edge.source_node].append(edge.target_node)

    ready = sorted(nid for nid, deg in in_degree.items() if deg == 0)
    order: list[str] = []
    while ready:
        node_id = ready.pop(0)
        order.append(node_id)
        for child in sorted(children[node_id]):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                ready.append(child)
        ready.sort()

    if len(order) != len(nodes_by_id):
        # Some nodes never reached in-degree 0 — cycle present.
        remaining = sorted(nid for nid, deg in in_degree.items() if deg > 0)
        raise WorkflowEngineError(f"workflow contains a cycle (could not order {remaining})")
    return order


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


async def _emit(callback: EventCallback | None, event: WorkflowRunEvent) -> None:
    """Fire an event callback if one is provided; swallow callback errors."""
    if callback is None:
        return
    try:
        await callback(event)
    except Exception as exc:  # noqa: BLE001 — caller error must not abort the run
        logger.warning("workflow_engine: on_event callback raised %s", exc)


def _input_edges_for(node_id: str, edges: list[WorkflowEdge]) -> list[WorkflowEdge]:
    """Return the subset of edges whose target is ``node_id``."""
    return [edge for edge in edges if edge.target_node == node_id]


async def run_workflow(
    spec: WorkflowSpec,
    *,
    inputs: dict[str, Any] | None = None,
    on_event: EventCallback | None = None,
) -> WorkflowRunResult:
    """Run a workflow end-to-end. Returns the aggregated result.

    Concurrency model: at every iteration, runs every node whose upstream
    inputs are all available, concurrently via ``asyncio.gather``. Errors
    in one node mark its downstream as unreachable but do NOT cancel
    siblings already running. This matches the operator-brief
    "Sequential AND parallel execution semantics, error handling".
    """
    nodes_by_id = _validate_spec(spec)
    run_id = str(uuid.uuid4())
    started_at = int(time.time() * 1000)
    started_ns = time.perf_counter_ns()

    await _emit(
        on_event,
        WorkflowRunEvent(kind="run-start", runId=run_id, startedAt=started_at),
    )

    # Per-node output cache; populated as nodes complete.
    node_outputs: dict[str, dict[str, Any]] = {}
    node_results: list[NodeRunResult] = []
    failed_ids: set[str] = set()
    workflow_inputs = dict(inputs or {})

    # Mark a node as "pending" until it has run (or been skipped).
    pending = set(nodes_by_id.keys())

    while pending:
        # Find every node whose dependencies have completed (success OR
        # failure — failed upstream propagates as failure downstream).
        ready: list[str] = []
        for node_id in list(pending):
            deps = {edge.source_node for edge in _input_edges_for(node_id, spec.edges)}
            if deps.issubset(node_outputs.keys() | failed_ids):
                ready.append(node_id)
        if not ready:
            # Shouldn't happen — _validate_spec rejects cycles — but guard
            # against logic bugs.
            raise WorkflowEngineError(
                f"workflow stalled with pending={pending} (no node has all dependencies satisfied)"
            )

        # If any of the upstream of a ready node failed, mark the ready
        # node as failed without running its handler.
        runnable: list[str] = []
        for node_id in ready:
            upstream_failed = any(
                edge.source_node in failed_ids for edge in _input_edges_for(node_id, spec.edges)
            )
            if upstream_failed:
                node = nodes_by_id[node_id]
                node_results.append(
                    NodeRunResult(
                        nodeId=node_id,
                        nodeType=node.type,
                        status="error",
                        outputs={},
                        error="upstream node failed",
                        durationMs=0.0,
                        startedAt=int(time.time() * 1000),
                    )
                )
                failed_ids.add(node_id)
                await _emit(
                    on_event,
                    WorkflowRunEvent(
                        kind="node-error",
                        runId=run_id,
                        nodeId=node_id,
                        message="upstream node failed",
                        durationMs=0.0,
                    ),
                )
                pending.discard(node_id)
            else:
                runnable.append(node_id)

        # Run the runnable nodes concurrently.
        if runnable:
            tasks = [
                asyncio.create_task(
                    _run_one_node(
                        nodes_by_id[node_id],
                        spec.edges,
                        node_outputs,
                        workflow_inputs,
                        run_id,
                        on_event,
                    )
                )
                for node_id in runnable
            ]
            results = await asyncio.gather(*tasks)
            for result in results:
                node_results.append(result)
                pending.discard(result.node_id)
                if result.status == "ok":
                    node_outputs[result.node_id] = result.outputs
                else:
                    failed_ids.add(result.node_id)

    overall_status: str = "error" if failed_ids else "ok"
    overall_error: str | None = None
    if failed_ids:
        overall_error = f"failures in nodes: {sorted(failed_ids)}"

    duration_ms = (time.perf_counter_ns() - started_ns) / 1_000_000

    if overall_status == "ok":
        await _emit(
            on_event,
            WorkflowRunEvent(kind="run-complete", runId=run_id, durationMs=duration_ms),
        )
    else:
        await _emit(
            on_event,
            WorkflowRunEvent(
                kind="run-error",
                runId=run_id,
                message=overall_error or "workflow errored",
                durationMs=duration_ms,
            ),
        )

    return WorkflowRunResult(
        runId=run_id,
        workflowId=spec.id,
        status=overall_status,  # type: ignore[arg-type]
        startedAt=started_at,
        durationMs=duration_ms,
        nodes=node_results,
        error=overall_error,
    )


async def _run_one_node(
    node: WorkflowNode,
    edges: list[WorkflowEdge],
    node_outputs: dict[str, dict[str, Any]],
    workflow_inputs: dict[str, Any],
    run_id: str,
    on_event: EventCallback | None,
) -> NodeRunResult:
    """Run one node's handler; capture outputs / errors / timing."""
    started_at = int(time.time() * 1000)
    started_ns = time.perf_counter_ns()

    await _emit(
        on_event,
        WorkflowRunEvent(
            kind="node-start",
            runId=run_id,
            nodeId=node.id,
            nodeType=node.type,
            startedAt=started_at,
        ),
    )

    # Wire inputs: for each input edge, pull the upstream node's
    # ``output[source_port]`` value into ``inputs[target_port]``. If the
    # node has no input edges, fall back to the global workflow inputs
    # (only the source nodes of the DAG see these).
    inputs: dict[str, Any] = {}
    input_edges = _input_edges_for(node.id, edges)
    if input_edges:
        for edge in input_edges:
            upstream = node_outputs.get(edge.source_node, {})
            inputs[edge.target_port] = upstream.get(edge.source_port)
    else:
        inputs = dict(workflow_inputs)

    handler = _HANDLERS.get(node.type)
    if handler is None:  # pragma: no cover - _validate_spec already checks this
        return NodeRunResult(
            nodeId=node.id,
            nodeType=node.type,
            status="error",
            outputs={},
            error=f"no handler registered for type {node.type!r}",
            durationMs=0.0,
            startedAt=started_at,
        )

    try:
        outputs = await handler(inputs, node.config)
        duration_ms = (time.perf_counter_ns() - started_ns) / 1_000_000
        await _emit(
            on_event,
            WorkflowRunEvent(
                kind="node-output",
                runId=run_id,
                nodeId=node.id,
                outputs=outputs,
                durationMs=duration_ms,
            ),
        )
        return NodeRunResult(
            nodeId=node.id,
            nodeType=node.type,
            status="ok",
            outputs=outputs,
            durationMs=duration_ms,
            startedAt=started_at,
        )
    except Exception as exc:  # noqa: BLE001 — handler errors must not abort the run
        duration_ms = (time.perf_counter_ns() - started_ns) / 1_000_000
        await _emit(
            on_event,
            WorkflowRunEvent(
                kind="node-error",
                runId=run_id,
                nodeId=node.id,
                message=str(exc),
                durationMs=duration_ms,
            ),
        )
        return NodeRunResult(
            nodeId=node.id,
            nodeType=node.type,
            status="error",
            outputs={},
            error=str(exc),
            durationMs=duration_ms,
            startedAt=started_at,
        )
