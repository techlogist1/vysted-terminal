"""Workflow engine Pydantic models — mirror of ``types/workflow.ts``.

Phase 4 ships a custom asyncio workflow engine (``services/workflow_engine.py``)
that walks a DAG of nodes with per-node observability and SSE event emission.
This file defines the wire shapes the engine speaks; concrete node handlers
live in ``services/workflow_nodes/`` (Teammate W).

CLAUDE.md Gotcha applies: TS types in ``types/data.ts`` (and now
``types/workflow.ts``) mirror these Pydantic models by hand. Field renames
require a same-commit TypeScript update on the matching interface.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class NodePosition(BaseModel):
    """Canvas position — node-editor only; engine ignores."""

    model_config = ConfigDict(extra="forbid")

    x: float
    y: float


class WorkflowNode(BaseModel):
    """A node in a workflow graph."""

    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    position: NodePosition
    config: dict[str, Any] = Field(default_factory=dict)


class WorkflowEdge(BaseModel):
    """An edge connecting two nodes' ports."""

    model_config = ConfigDict(extra="forbid")

    id: str
    source_node: str = Field(alias="sourceNode")
    source_port: str = Field(alias="sourcePort")
    target_node: str = Field(alias="targetNode")
    target_port: str = Field(alias="targetPort")


class WorkflowSpec(BaseModel):
    """A complete workflow — the unit of save / load / run."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    name: str
    description: str | None = None
    version: int = 1
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
    updated_at: int = Field(alias="updatedAt", default=0)


class WorkflowRunRequest(BaseModel):
    """``POST /workflow/run`` request body."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    spec: WorkflowSpec
    inputs: dict[str, Any] = Field(default_factory=dict)
    mode: Literal["full", "resume-from"] = "full"
    resume_from: str | None = Field(default=None, alias="resumeFrom")


class WorkflowRunEvent(BaseModel):
    """One SSE event in a workflow run.

    Mirrors the discriminated-union shape of ``WorkflowRunEvent`` in
    ``types/workflow.ts`` — when serialised the consumer narrows on ``kind``.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    kind: Literal[
        "run-start",
        "node-start",
        "node-output",
        "node-error",
        "run-complete",
        "run-error",
    ]
    run_id: str = Field(alias="runId")
    node_id: str | None = Field(default=None, alias="nodeId")
    node_type: str | None = Field(default=None, alias="nodeType")
    started_at: int | None = Field(default=None, alias="startedAt")
    outputs: dict[str, Any] | None = None
    message: str | None = None
    duration_ms: float | None = Field(default=None, alias="durationMs")


class NodeRunResult(BaseModel):
    """Per-node result captured for replay + run-log display."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    node_id: str = Field(alias="nodeId")
    node_type: str = Field(alias="nodeType")
    status: Literal["ok", "error"]
    outputs: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    duration_ms: float = Field(alias="durationMs")
    started_at: int = Field(alias="startedAt")


class WorkflowRunResult(BaseModel):
    """Final result of a workflow run."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    run_id: str = Field(alias="runId")
    workflow_id: str = Field(alias="workflowId")
    status: Literal["ok", "error"]
    started_at: int = Field(alias="startedAt")
    duration_ms: float = Field(alias="durationMs")
    nodes: list[NodeRunResult]
    error: str | None = None
