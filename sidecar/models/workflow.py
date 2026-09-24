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

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.llm import LLMModelId, LLMProviderId


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

    @field_validator("config")
    @classmethod
    def _no_api_key(cls, value: dict[str, Any]) -> dict[str, Any]:
        # A saved spec is persisted as plaintext JSON: a key never rides it.
        # Credentials come from the run request (WorkflowRunRequest) only.
        if "api_key" in value:
            raise ValueError(
                "node config must not carry 'api_key'; the run uses the selected "
                "provider's key from the request"
            )
        return value


class WorkflowEdge(BaseModel):
    """An edge connecting two nodes' ports."""

    model_config = ConfigDict(extra="forbid")

    id: str
    source_node: str = Field(alias="sourceNode")
    source_port: str = Field(alias="sourcePort")
    target_node: str = Field(alias="targetNode")
    target_port: str = Field(alias="targetPort")


#: The spec schema major this build reads; a saved spec of another major is
#: refused on load (``workflow_store.UnsupportedWorkflowVersion``).
WORKFLOW_SPEC_VERSION = 1


class WorkflowSpec(BaseModel):
    """A complete workflow — the unit of save / load / run."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    name: str
    description: str | None = None
    version: int = WORKFLOW_SPEC_VERSION
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
    updated_at: int = Field(alias="updatedAt", default=0)


class UnreadableWorkflow(BaseModel):
    """A saved row this build cannot open (invalid spec or another major)."""

    id: str
    name: str
    reason: str


class SavedWorkflows(BaseModel):
    """``GET /workflow/saved`` — the openable specs plus the rows that are not."""

    workflows: list[WorkflowSpec]
    unreadable: list[UnreadableWorkflow] = Field(default_factory=list)


class WorkflowRunRequest(BaseModel):
    """``POST /workflow/run`` request body."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    spec: WorkflowSpec
    inputs: dict[str, Any] = Field(default_factory=dict)
    mode: Literal["full", "resume-from"] = "full"
    resume_from: str | None = Field(default=None, alias="resumeFrom")
    #: Foreground BYOK creds for ``ai.agent_invoke`` nodes, the same names as
    #: ``AgentInvocationRequest``. Held for the run only; never persisted or logged.
    provider: LLMProviderId | None = None
    model: LLMModelId | None = None
    api_key: str | None = Field(default=None, alias="apiKey", repr=False)


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
        "node-skipped",
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
    #: ``skipped``: every input came from an un-taken branch path; not run.
    status: Literal["ok", "error", "skipped"]
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


# ---------------------------------------------------------------------------
# Schedules (R15-AGENT-023) — a saved workflow fired unattended by the
# sidecar-resident scheduler (``services/workflow_scheduler.py``) while the app
# is open. Mirrored by hand in ``types/workflow.ts``.
# ---------------------------------------------------------------------------

#: The shortest interval a schedule may fire on.
MIN_INTERVAL_MINUTES = 5


class IntervalTrigger(BaseModel):
    """Fire every ``every_minutes`` (>= 5) after the last fire (or creation)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    kind: Literal["interval"]
    every_minutes: int = Field(alias="everyMinutes", ge=MIN_INTERVAL_MINUTES)


class AnnouncementTrigger(BaseModel):
    """Fire once per new exchange announcement for ``symbol`` whose headline
    contains ``phrase`` (case-insensitive); the announcement is the run input."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["announcement"]
    symbol: str = Field(min_length=1)
    phrase: str = Field(min_length=1)


ScheduleTrigger = Annotated[IntervalTrigger | AnnouncementTrigger, Field(discriminator="kind")]


class ScheduleCreate(BaseModel):
    """``POST /workflow/schedules`` body."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    workflow_id: str = Field(alias="workflowId", min_length=1)
    trigger: ScheduleTrigger
    enabled: bool = True


class ScheduleUpdate(BaseModel):
    """``PATCH /workflow/schedules/{id}`` body."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool


class WorkflowSchedule(BaseModel):
    """One persisted schedule plus its last outcome."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    workflow_id: str = Field(alias="workflowId")
    trigger: ScheduleTrigger
    enabled: bool
    created_at: int = Field(alias="createdAt")
    #: Epoch ms of the last fire; ``None`` until the first.
    last_fired_at: int | None = Field(default=None, alias="lastFiredAt")
    #: Announcement trigger: ISO timestamp of the newest announcement fired on.
    last_seen: str | None = Field(default=None, alias="lastSeen")
    last_status: Literal["running", "ok", "error"] | None = Field(default=None, alias="lastStatus")
    last_detail: str | None = Field(default=None, alias="lastDetail")


class WebhookRefs(BaseModel):
    """``GET /workflow/webhooks`` — the refs with a URL held in memory (never the URLs)."""

    refs: list[str]
