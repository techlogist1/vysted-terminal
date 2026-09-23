"""Custom asyncio workflow engine — Phase 4 foundation.

Validates a :class:`WorkflowSpec` DAG, starts each node as soon as its own
inputs are available (independent branches run concurrently), bounds every
handler with a per-node timeout, skips the un-taken side of a branch, and
emits :class:`WorkflowRunEvent` events through an optional ``on_event``
callback for SSE streaming.

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

#: Handler bound when a node's config sets no ``timeout_seconds``. Above
#: ``flow.sleep``'s 300 s cap and a deep-research agent's wall budget.
DEFAULT_NODE_TIMEOUT_SECONDS = 600.0


class _Skip:
    def __repr__(self) -> str:
        return "SKIP"


#: Output value marking a port whose path was not taken (``logic.branch``).
#: A node whose every input edge carries it is skipped, not run.
SKIP: Any = _Skip()


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


def _wire_outputs(outputs: dict[str, Any]) -> dict[str, Any]:
    """The outputs as recorded and streamed: a ``SKIP`` port is omitted."""
    return {port: value for port, value in outputs.items() if value is not SKIP}


async def run_workflow(
    spec: WorkflowSpec,
    *,
    inputs: dict[str, Any] | None = None,
    on_event: EventCallback | None = None,
) -> WorkflowRunResult:
    """Run a workflow end-to-end. Returns the aggregated result.

    Concurrency model: a node starts as soon as its own upstream nodes have
    settled (``asyncio.wait(FIRST_COMPLETED)``), so a slow node never stalls
    an unrelated branch, and each handler is bounded by its node timeout. A
    failed upstream fails its dependants without running them; a node whose
    every input edge carries :data:`SKIP` (the un-taken ``logic.branch``
    port, or a skipped upstream) is recorded ``skipped`` and propagates the
    skip. Errors do NOT cancel siblings already running.
    """
    nodes_by_id = _validate_spec(spec)
    run_id = str(uuid.uuid4())
    started_at = int(time.time() * 1000)
    started_ns = time.perf_counter_ns()

    await _emit(
        on_event,
        WorkflowRunEvent(kind="run-start", runId=run_id, startedAt=started_at),
    )

    # Raw per-node outputs (SKIP markers kept) for wiring dependants.
    node_outputs: dict[str, dict[str, Any]] = {}
    node_results: list[NodeRunResult] = []
    failed_ids: set[str] = set()
    skipped_ids: set[str] = set()
    workflow_inputs = dict(inputs or {})
    pending = set(nodes_by_id.keys())
    running: dict[asyncio.Task[tuple[NodeRunResult, dict[str, Any]]], str] = {}

    def edge_value(edge: WorkflowEdge) -> Any:
        if edge.source_node in skipped_ids:
            return SKIP
        return node_outputs[edge.source_node].get(edge.source_port)

    while pending or running:
        # Settle every pending node whose upstream has settled: fail it on a
        # failed upstream, skip it when every input carries SKIP, else start
        # it. Failing or skipping can unblock more nodes, so repeat.
        progressed = True
        while progressed:
            progressed = False
            for node_id in sorted(pending):
                in_edges = _input_edges_for(node_id, spec.edges)
                settled = node_outputs.keys() | failed_ids | skipped_ids
                if not {edge.source_node for edge in in_edges} <= settled:
                    continue
                pending.discard(node_id)
                progressed = True
                node = nodes_by_id[node_id]
                if any(edge.source_node in failed_ids for edge in in_edges):
                    failed_ids.add(node_id)
                    node_results.append(
                        NodeRunResult(
                            nodeId=node_id,
                            nodeType=node.type,
                            status="error",
                            error="upstream node failed",
                            durationMs=0.0,
                            startedAt=int(time.time() * 1000),
                        )
                    )
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
                    continue
                values = {edge.target_port: edge_value(edge) for edge in in_edges}
                if in_edges and all(edge_value(edge) is SKIP for edge in in_edges):
                    skipped_ids.add(node_id)
                    node_results.append(
                        NodeRunResult(
                            nodeId=node_id,
                            nodeType=node.type,
                            status="skipped",
                            durationMs=0.0,
                            startedAt=int(time.time() * 1000),
                        )
                    )
                    await _emit(
                        on_event,
                        WorkflowRunEvent(
                            kind="node-skipped", runId=run_id, nodeId=node_id, nodeType=node.type
                        ),
                    )
                    continue
                # A merge fed partly by a skipped path sees that input as None.
                node_inputs = (
                    {port: None if value is SKIP else value for port, value in values.items()}
                    if in_edges
                    else dict(workflow_inputs)
                )
                task = asyncio.create_task(_run_one_node(node, node_inputs, run_id, on_event))
                running[task] = node_id

        if not running:
            if pending:
                # Shouldn't happen — _validate_spec rejects cycles.
                raise WorkflowEngineError(
                    f"workflow stalled with pending={pending} "
                    "(no node has all dependencies satisfied)"
                )
            break

        done, _ = await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            node_id = running.pop(task)
            result, raw_outputs = task.result()
            node_results.append(result)
            if result.status == "ok":
                node_outputs[node_id] = raw_outputs
            else:
                failed_ids.add(node_id)

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


def _node_timeout(node: WorkflowNode) -> float:
    """The node's handler bound: ``config["timeout_seconds"]`` or the default."""
    raw = node.config.get("timeout_seconds", DEFAULT_NODE_TIMEOUT_SECONDS)
    try:
        timeout = float(raw)
    except (TypeError, ValueError):
        timeout = 0.0
    if not timeout > 0:
        raise ValueError(f"'timeout_seconds' must be a positive number; got {raw!r}")
    return timeout


async def _run_one_node(
    node: WorkflowNode,
    inputs: dict[str, Any],
    run_id: str,
    on_event: EventCallback | None,
) -> tuple[NodeRunResult, dict[str, Any]]:
    """Run one node's handler under its timeout.

    Returns the result (wire outputs: SKIP ports omitted) and the raw outputs
    (SKIP kept) the scheduler wires into dependants.
    """
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

    handler = _HANDLERS[node.type]  # _validate_spec checked registration
    try:
        timeout = _node_timeout(node)
        try:
            raw_outputs = await asyncio.wait_for(handler(inputs, node.config), timeout)
        except TimeoutError as exc:
            raise TimeoutError(f"node timed out after {timeout:g}s") from exc
        outputs = _wire_outputs(raw_outputs)
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
        result = NodeRunResult(
            nodeId=node.id,
            nodeType=node.type,
            status="ok",
            outputs=outputs,
            durationMs=duration_ms,
            startedAt=started_at,
        )
        return result, raw_outputs
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
        result = NodeRunResult(
            nodeId=node.id,
            nodeType=node.type,
            status="error",
            outputs={},
            error=str(exc),
            durationMs=duration_ms,
            startedAt=started_at,
        )
        return result, {}
