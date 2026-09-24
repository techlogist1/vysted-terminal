"""Delegate-run Pydantic models (P3 / FR-026/027/028, US9, SC-008).

A *Delegate run* is an autonomous BACKGROUND agent task. Unlike a synchronous
``POST /agents/{id}/invoke`` SSE stream — which lives and dies with the HTTP
connection — a run is DURABLE: it is persisted in SQLite (``runs_store``),
driven by a detached asyncio task (``run_manager``), governed by a hard
``BudgetGuard`` spend ceiling (``budget_guard``), and observable / cancellable /
resumable through ``routers.runs`` long after the launching request closed.

These models are the wire contract the frontend consumes. The poller reads BOTH
snake_case and camelCase for cost (``spend_usd`` / ``spendUsd``) — we emit
camelCase aliases via ``Field(alias=...)`` + ``populate_by_name=True``, and the
router serialises ``by_alias=True``, so the wire shape is the camelCase one the
frontend expects while Python keeps snake_case attribute names.

CLAUDE.md gotcha: ``types/data.ts`` mirrors ``sidecar/models/`` by hand — a
field rename here requires a same-commit TypeScript update.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .llm import LLMProviderId

#: A run's lifecycle state (legal changes: ``runs_store.TRANSITIONS``).
#: - ``planned``   — a compound task's plan waits for the user's Start/Discard.
#: - ``running``   — the detached task is executing the agent loop.
#: - ``paused``    — a human-in-the-loop question is outstanding (FR-028); no
#:                   task runs until ``answer_run`` resumes from the checkpoint.
#: - ``done``      — the agent completed naturally.
#: - ``error``     — a BudgetGuard ceiling was breached (SC-008) or the agent
#:                   raised; ``detail`` carries the stated reason.
#: - ``cancelled`` — the user cancelled the run (``cancel_run``).
RunStatus = Literal["planned", "running", "paused", "done", "error", "cancelled"]


class RunBudget(BaseModel):
    """The hard spend ceilings for a Delegate run (US9 / FR-026).

    A request may omit any ceiling; ``run_manager`` fills every omitted one from
    :data:`DEFAULT_RUN_BUDGET` before the run starts, so a run is never
    unbounded (R15-AGENT-034). A given ceiling must be positive. The
    :class:`~services.budget_guard.BudgetGuard` aborts the run on the FIRST
    breach with a stated reason (SC-008: a breach aborts 100% of the time).
    The guard governs SPEND only; a Delegate run uses the same agent loop, in
    which no trading path exists.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    #: Hard cap on total tokens (input + output, summed across rounds).
    max_tokens: int | None = Field(default=None, gt=0, alias="maxTokens")
    #: Hard cap on estimated USD spend (see ``budget_guard.PRICE_TABLE``).
    max_spend_usd: float | None = Field(default=None, gt=0, alias="maxSpendUsd")
    #: Hard cap on wall-clock seconds from run start (monotonic).
    max_wall_seconds: float | None = Field(default=None, gt=0, alias="maxWallSeconds")
    #: Hard cap on provider rounds (also bounded by ``_MAX_TOOL_ROUNDS``).
    max_steps: int | None = Field(default=None, gt=0, alias="maxSteps")


#: The server floor for an omitted ceiling. Equal to the composer's
#: ``DEFAULT_DELEGATE_BUDGET`` (``src/modules/chat/BudgetConfig.tsx``).
DEFAULT_RUN_BUDGET = RunBudget(
    max_tokens=120_000, max_spend_usd=1.0, max_wall_seconds=600, max_steps=12
)


class RunCost(BaseModel):
    """The accumulated cost of a run so far — the BudgetGuard's running total.

    ``spend_usd`` is a best-effort ESTIMATE from a per-provider/model price
    table; it is NOT a billed figure (the sidecar holds no provider invoice).
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    tokens: int = 0
    spend_usd: float = Field(default=0.0, alias="spendUsd")
    steps: int = 0


class RunLaunchRequest(BaseModel):
    """``POST /agents/{agent_id}/runs`` request body.

    ``api_key`` is BYOK — it crosses for the lifetime of THIS run only and is
    never stored in the runs database, never logged, never echoed back in any
    response (asserted in ``test_runs_router``).
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    prompt: str
    context_snapshot: dict[str, Any] | None = Field(default=None, alias="contextSnapshot")
    provider: LLMProviderId | None = None
    model: str | None = None
    api_key: str | None = Field(default=None, alias="apiKey")
    budget: RunBudget = Field(default_factory=RunBudget)
    options: dict[str, Any] = Field(default_factory=dict)


class RunLaunchResponse(BaseModel):
    """``POST /agents/{agent_id}/runs`` 201 response.

    Emits BOTH ``runId`` (camelCase, the alias the frontend reads) and accepts
    ``run_id`` on the way in via ``populate_by_name``.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    run_id: str = Field(alias="runId")


class RunSummary(BaseModel):
    """One row in ``GET /runs`` — the run-tray list shape.

    Serialised ``by_alias=True`` so cost is ``{tokens, spendUsd, steps}`` and
    timestamps are ``createdAt`` / ``updatedAt`` on the wire.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    agent_id: str = Field(alias="agentId")
    agent_name: str = Field(alias="agentName")
    mode: str
    status: RunStatus
    cost: RunCost
    budget: RunBudget
    #: The launch's provider/model (``None`` = the agent default); a resume
    #: re-uses them (R15-AGENT-035).
    provider: str | None = None
    model: str | None = None
    detail: str | None = None
    question: str | None = None
    created_at: int = Field(alias="createdAt")
    updated_at: int = Field(alias="updatedAt")


class RunDetail(RunSummary):
    """``GET /runs/{run_id}`` — a run plus a summary of its transcript.

    ``transcript`` is a terse, role-tagged digest of the messages the agent loop
    accumulated (system prompts elided) so the foreground view can show what the
    background run has been doing; ``checkpoint_messages`` is the count of
    messages persisted to ``checkpoint_json`` for a resume.

    The collectable output, set once the run ends (R15-AGENT-013): ``answer`` is
    the full final text (untruncated), ``brief`` the last ``publish_brief``
    input, and ``host_actions`` the proposed host actions as
    ``{tool_call_id, name, input}``. None of it is applied by the sidecar.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    transcript: list[dict[str, Any]] = Field(default_factory=list)
    checkpoint_messages: int = Field(default=0, alias="checkpointMessages")
    answer: str | None = None
    brief: dict[str, Any] | None = None
    host_actions: list[dict[str, Any]] = Field(default_factory=list, alias="hostActions")


class RunAnswerRequest(BaseModel):
    """``POST /runs/{run_id}/answer`` body — a human-in-the-loop reply (FR-028)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    answer: str
