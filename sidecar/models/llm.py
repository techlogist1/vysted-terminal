"""LLM Pydantic models.

Mirrors the TypeScript types in ``types/ai.ts`` field-for-field (CLAUDE.md
gotcha: ``types/data.ts`` mirrors ``sidecar/models/`` by hand). The wire
contract for ``POST /llm/chat`` (SSE), ``POST /llm/keys/validate``,
``GET /llm/providers``, and ``POST /agents/{agent_id}/invoke`` (SSE).

Streaming events emitted over SSE are JSON-serialised :class:`LLMStreamEvent`
discriminated unions; the FastAPI router yields one event per ``data:`` line
of the SSE body and the frontend's native ``EventSource`` re-assembles them
into a chat conversation.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Provider + model identifiers
# ---------------------------------------------------------------------------

#: Closed set of the seven BYOK providers Phase 3 ships.
LLMProviderId = Literal["anthropic", "openai", "gemini", "groq", "ollama", "deepseek", "xai"]

#: Free-form model identifier — providers ship new models between Vysted
#: releases, so the host does not enumerate. Strings keep the contract open.
LLMModelId = str


class LLMProviderInfo(BaseModel):
    """One row in ``GET /llm/providers`` — what the chat sidebar enumerates."""

    id: LLMProviderId
    label: str
    requires_key: bool
    default_base_url: str | None = None
    #: Registry default model id for this provider (served to the frontend
    #: dropdown). Single-sourced from ``config/model_registry.json``.
    default_model: str = ""
    #: Selectable model ids for this provider (offline fallback for the UI).
    known_models: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Chat messages
# ---------------------------------------------------------------------------

LLMRole = Literal["system", "user", "assistant", "tool"]


class LLMMessage(BaseModel):
    """One message in a chat conversation; mirrors OpenAI/Anthropic shape."""

    role: LLMRole
    content: str
    tool_call_id: str | None = None
    metadata: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Streaming protocol — emitted as ``data: <json>\n\n`` SSE frames
# ---------------------------------------------------------------------------


class LLMUsage(BaseModel):
    """Token usage reported on ``done``; optional per provider."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int | None = None
    cache_creation_input_tokens: int | None = None


class LLMDeltaEvent(BaseModel):
    """Streaming text delta."""

    kind: Literal["delta"] = "delta"
    text: str


class LLMToolUseEvent(BaseModel):
    """Provider invoked a tool; the host resolves the call."""

    kind: Literal["tool_use"] = "tool_use"
    tool_call_id: str
    name: str
    input: dict[str, Any] = Field(default_factory=dict)


class LLMResearchStepEvent(BaseModel):
    """A live research-pipeline step, surfaced WHILE a long tool runs (Track A).

    The deep/fast research tools run for many seconds inside a single tool round;
    without this the SSE consumer sees the tool fire and then silence until the
    result. The runtime drains each :class:`~services.research.models.ResearchStep`
    the tool emits and forwards it as one of these events, so the agent surface
    can animate a "thinking/working" trace (plan → search → synthesize) in real
    time. Read-only/cosmetic — it never gates a mutation and carries no secrets.
    """

    kind: Literal["research_step"] = "research_step"
    #: The tool round this step belongs to (the originating ``tool_use`` call id).
    tool_call_id: str
    #: The tool emitting the step (e.g. ``"deep_research"`` / ``"research"``).
    tool: str
    #: One of :data:`services.research.models.STEP_KINDS`
    #: (plan/tool/search/compress/reflect/synthesize).
    step_kind: str
    #: A short human line, e.g. ``"researcher: demand outlook?"``.
    detail: str
    #: Wall time of the stage in ms, when measured.
    latency_ms: int | None = None
    #: ``"ok"`` / ``"error"`` / ``"skipped"`` — a non-fatal sub-failure is recorded.
    status: str = "ok"
    #: Monotonic 1-based step counter within the run (UI ordering/keys).
    index: int = 0


class LLMThinkingEvent(BaseModel):
    """Provider streamed extended-thinking text (Anthropic, OpenAI o-series)."""

    kind: Literal["thinking"] = "thinking"
    text: str


class LLMDoneEvent(BaseModel):
    """Stream complete; final usage + finish reason if available."""

    kind: Literal["done"] = "done"
    usage: LLMUsage | None = None
    finish_reason: str | None = None


class LLMErrorEvent(BaseModel):
    """Stream aborted; human-readable detail surfaced to the chat sidebar."""

    kind: Literal["error"] = "error"
    message: str


# ---------------------------------------------------------------------------
# Request envelopes
# ---------------------------------------------------------------------------


class LLMChatRequest(BaseModel):
    """``POST /llm/chat`` request body.

    ``api_key`` is BYOK — read from the OS keychain on the frontend and passed
    per request. The sidecar holds it in memory only for the lifetime of the
    request; never persisted, never logged.
    """

    model_config = ConfigDict(extra="forbid")

    provider: LLMProviderId
    model: LLMModelId
    messages: list[LLMMessage]
    api_key: str | None = None
    base_url: str | None = None
    #: Provider-specific overrides (e.g. ``temperature``, ``max_tokens``).
    options: dict[str, Any] = Field(default_factory=dict)


class LLMKeyValidationRequest(BaseModel):
    """``POST /llm/keys/validate`` request body."""

    model_config = ConfigDict(extra="forbid")

    provider: LLMProviderId
    api_key: str | None = None
    base_url: str | None = None


class LLMKeyValidationResponse(BaseModel):
    """Validation result — sidecar performs a cheap GET against the provider."""

    ok: bool
    detail: str | None = None
