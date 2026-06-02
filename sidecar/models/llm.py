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

#: Closed set of the BYOK providers. ``openrouter`` (added in the JARVIS sprint)
#: is a unified BROKER — one key, all upstreams — that rides the OpenAI-shaped
#: adapter via a base-url override, exactly like deepseek/xai.
LLMProviderId = Literal[
    "anthropic", "openai", "gemini", "groq", "ollama", "deepseek", "xai", "openrouter"
]

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


class LLMModelOption(BaseModel):
    """One model in a LIVE provider catalog (``GET /llm/models``).

    Richer than the bare ``known_models`` string list: carries the metadata the
    model picker needs to mark a model — most importantly ``supports_tools`` so
    the agent surface can flag a model that would break host-actions (the whole
    point of the OpenRouter live-catalog fix). All fields beyond ``id``/``label``
    are best-effort: ``None`` means "the provider's catalog did not say", never
    "false".
    """

    #: The routable model id passed back as ``model`` in a chat request.
    id: str
    #: Human-friendly name for the dropdown (falls back to ``id``).
    label: str
    #: Max context window, when the catalog reports it.
    context_length: int | None = None
    #: ``True``/``False`` when known; ``None`` when the provider's catalog is
    #: silent on tool-calling support (so the UI marks "unknown", not "no").
    supports_tools: bool | None = None
    #: Short human price hint (e.g. ``"$0.30 / $1.20 per 1M"``), when available.
    pricing: str | None = None


class LLMModelCatalog(BaseModel):
    """``GET /llm/models`` payload — a provider's live (or fallback) model list.

    ``source`` is ``"live"`` when the provider's catalog API answered and
    ``"fallback"`` when we served the registry ``known_models`` because the live
    fetch failed or returned nothing. ``note`` is a short honest line for the UI
    (e.g. "routable on your key · 247 tool-capable" or "live catalog
    unavailable"). Read-only; carries no credential.
    """

    provider: LLMProviderId
    models: list[LLMModelOption] = Field(default_factory=list)
    source: Literal["live", "fallback"] = "fallback"
    note: str | None = None


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
