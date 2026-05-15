"""Agent Pydantic models.

Mirrors the agent surface in ``types/ai.ts`` and ``types/plugin.ts`` (the
``AgentSpec`` interface is Tier-1 locked — these models stay faithful to it).

The first-party agent JSON files in ``sidecar/agents/`` validate against
``_schema.json`` (JSON Schema draft-07) at startup; that schema mirrors
``AgentSpec`` field-for-field. The Pydantic models below cover the runtime
surface (invocation requests, snapshots, results).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .llm import LLMModelId, LLMProviderId, LLMUsage


class AgentSpec(BaseModel):
    """Discovered agent config — mirrors the TS ``AgentSpec`` exactly.

    JSON Schema validation runs against ``sidecar/agents/_schema.json`` before
    construction; this model is the in-memory shape the agent runtime hands
    to the router.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    philosophy: str
    system_prompt: str = Field(alias="systemPrompt")
    tools: list[str]
    default_provider: LLMProviderId = Field(alias="defaultProvider")
    default_model: LLMModelId | None = Field(default=None, alias="defaultModel")
    icon: str | None = None


class AgentSummary(BaseModel):
    """Subset of :class:`AgentSpec` exposed via ``GET /agents``.

    The full ``system_prompt`` is intentionally NOT echoed back to the
    frontend — there is no UI surface that needs it, and keeping it
    sidecar-side avoids accidentally surfacing it to anything that scrapes
    the agent picker JSON.
    """

    id: str
    name: str
    philosophy: str
    tools: list[str]
    default_provider: LLMProviderId
    default_model: LLMModelId | None = None
    icon: str | None = None


class AgentContextSnapshot(BaseModel):
    """Panel-context snapshot attached to an agent invocation.

    Mirrors ``AgentContextSnapshot`` in ``types/ai.ts``. ``by_source`` is a
    free-form map keyed by panel ``source`` — each panel publishes its own
    shape so the model is intentionally loose.
    """

    focused_source: str | None = None
    by_source: dict[str, Any] = Field(default_factory=dict)
    captured_at: int = 0


class AgentInvocationRequest(BaseModel):
    """``POST /agents/{agent_id}/invoke`` request body."""

    model_config = ConfigDict(extra="forbid")

    prompt: str
    context_snapshot: AgentContextSnapshot | None = None
    provider: LLMProviderId | None = None
    model: LLMModelId | None = None
    api_key: str | None = None
    #: Provider-specific overrides.
    options: dict[str, Any] = Field(default_factory=dict)


class AgentInvocationResult(BaseModel):
    """Unary result returned by the MCP ``invoke_agent`` tool boundary."""

    ok: bool
    content: str
    usage: LLMUsage | None = None
    agent_id: str
    error: str | None = None
