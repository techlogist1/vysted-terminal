"""First-party agent runtime.

Discovers, validates, and invokes the 12 first-party agents shipped under
``sidecar/agents/`` (BLUEPRINT §3.4 roster + AI Strategy Critic per the
Phase-3 plan's Tier-3 §3.4-vs-§4 resolution).

Discovery: every ``<id>.json`` file in the agents directory whose schema
validates against ``_schema.json`` becomes a registered agent at module
import time. A single malformed file disqualifies that one agent without
blocking the rest — the runtime emits a structured log line and continues.

Invocation: :func:`invoke_agent` resolves the agent, composes the LLM
messages list (system prompt + optional context preamble + user prompt),
selects a provider (override or agent default), and yields a stream of
:class:`LLMStreamEvent` Pydantic models. The router serialises them onto
SSE; the MCP server tool aggregates them into a unary string.

The runtime holds no API keys — they ride on the request body and are
passed straight through to the provider adapter. Sidecar never persists.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import jsonschema

from models.agent import (
    AgentContextSnapshot,
    AgentSpec,
)
from models.llm import (
    LLMDoneEvent,
    LLMErrorEvent,
    LLMMessage,
    LLMProviderId,
    LLMToolUseEvent,
)
from services import agent_tools
from services.llm import get_provider
from services.llm.base import LLMStreamEvent

logger = logging.getLogger(__name__)

AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"
SCHEMA_PATH = AGENTS_DIR / "_schema.json"

#: Sentinel filenames in the agents directory that are NOT agent configs.
_RESERVED = {"_schema.json"}


def _load_schema() -> dict[str, Any]:
    """Read the AgentSpec JSON Schema; raise loudly if missing or malformed."""
    with SCHEMA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _discover_specs(agents_dir: Path = AGENTS_DIR) -> dict[str, AgentSpec]:
    """Enumerate the agents directory and return validated :class:`AgentSpec`s.

    Malformed files log a warning and are skipped — they MUST NOT block the
    rest of the roster from loading. Tests rely on partial-load resilience.
    """
    if not agents_dir.exists():
        return {}
    try:
        schema = _load_schema()
    except FileNotFoundError:
        logger.error("agent schema not found at %s; no agents will load", SCHEMA_PATH)
        return {}
    validator = jsonschema.Draft7Validator(schema)
    specs: dict[str, AgentSpec] = {}
    for path in sorted(agents_dir.glob("*.json")):
        if path.name in _RESERVED:
            continue
        try:
            with path.open(encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("agent %s: failed to read JSON (%s)", path.name, exc)
            continue
        errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
        if errors:
            for err in errors:
                logger.warning(
                    "agent %s: schema violation at %s: %s",
                    path.name,
                    list(err.path) or "<root>",
                    err.message,
                )
            continue
        try:
            spec = AgentSpec.model_validate(payload)
        except Exception as exc:  # pragma: no cover — schema covers this
            logger.warning("agent %s: pydantic validation failed (%s)", path.name, exc)
            continue
        if spec.id in specs:
            logger.warning("agent %s: duplicate id %r; keeping first", path.name, spec.id)
            continue
        specs[spec.id] = spec
    return specs


# Cached at module import — refreshes on a deliberate :func:`reload` call.
_specs: dict[str, AgentSpec] = _discover_specs()


def list_agents() -> list[AgentSpec]:
    """Return every registered first-party agent, ordered by id."""
    return [spec for _, spec in sorted(_specs.items())]


def get_agent(agent_id: str) -> AgentSpec | None:
    """Return one agent's spec, or ``None`` if unknown."""
    return _specs.get(agent_id)


def reload(agents_dir: Path = AGENTS_DIR) -> None:
    """Refresh the agent registry from disk; primarily for tests."""
    global _specs
    _specs = _discover_specs(agents_dir)


# ---------------------------------------------------------------------------
# Invocation
# ---------------------------------------------------------------------------


def _build_context_preamble(snapshot: AgentContextSnapshot | None) -> str | None:
    """Render the focused panel + per-panel context into a system-prompt blob.

    The agent reads this so its reasoning is grounded in actual terminal
    state — what symbol the chart is on, which articles the user has open,
    the positions in the portfolio. Keep the format compact JSON-ish so
    token cost stays bounded.
    """
    if snapshot is None:
        return None
    if not snapshot.by_source and snapshot.focused_source is None:
        return None
    sections = ["## Terminal context (read-only — describe accurately, do not invent fields)"]
    if snapshot.focused_source:
        sections.append(f"Focused panel: `{snapshot.focused_source}`")
    if snapshot.by_source:
        sections.append("Per-panel state:")
        for source, payload in sorted(snapshot.by_source.items()):
            sections.append(f"- `{source}`: {json.dumps(payload, default=str)}")
    return "\n".join(sections)


def _compose_messages(
    spec: AgentSpec,
    prompt: str,
    context: AgentContextSnapshot | None,
) -> list[LLMMessage]:
    """Build the system + context + user message list for the provider call."""
    messages: list[LLMMessage] = [LLMMessage(role="system", content=spec.system_prompt)]
    preamble = _build_context_preamble(context)
    if preamble:
        messages.append(LLMMessage(role="system", content=preamble))
    messages.append(LLMMessage(role="user", content=prompt))
    return messages


def _resolve_provider_id(spec: AgentSpec, override: LLMProviderId | None) -> LLMProviderId:
    return override or spec.default_provider


def _resolve_model(spec: AgentSpec, override: str | None) -> str:
    if override:
        return override
    if spec.default_model:
        return spec.default_model
    # Fallback default per provider — kept narrow to today's leading models.
    defaults: dict[str, str] = {
        "anthropic": "claude-opus-4-7",
        "openai": "gpt-4.1-mini",
        "gemini": "gemini-2.5-pro",
        "groq": "llama-3.3-70b-versatile",
        "ollama": "llama3.1:8b",
        "deepseek": "deepseek-chat",
        "xai": "grok-2-latest",
    }
    return defaults.get(spec.default_provider, "gpt-4.1-mini")


#: Hard cap on tool-call rounds in a single invocation. Strategy Critic
#: typically calls one to three tools (backtest_summary + optionally
#: price_data + fundamentals); a runaway agent that loops on the same
#: tool is bounded by this constant.
_MAX_TOOL_ROUNDS = 6


async def _dispatch_tool(event: LLMToolUseEvent) -> str:
    """Invoke the registered tool and serialise the result to a string.

    Tool handlers return JSON-serialisable dicts; we encode them as a
    string so they can ride the existing :class:`LLMMessage` ``content``
    field (a single string by contract). The provider adapter for
    Anthropic translates a ``role="tool"`` message into a
    ``tool_result`` content block keyed on ``tool_call_id``; other
    adapters use the same role surface.

    A handler that raises (or the tool is unregistered) surfaces a
    structured error so the model can recover gracefully on the next
    turn rather than crashing the stream.
    """
    try:
        if not agent_tools.is_registered(event.name):
            payload: dict[str, Any] = {
                "ok": False,
                "error": f"tool {event.name!r} is not available in this build",
            }
        else:
            payload = await agent_tools.invoke_tool(event.name, event.input)
    except Exception as exc:  # noqa: BLE001 — surface failures to the model
        payload = {"ok": False, "error": f"tool {event.name!r} raised: {exc}"}
    try:
        return json.dumps(payload, default=str)
    except (TypeError, ValueError):
        return str(payload)


async def invoke_agent(
    agent_id: str,
    prompt: str,
    context_snapshot: AgentContextSnapshot | None = None,
    api_key: str | None = None,
    provider: LLMProviderId | None = None,
    model: str | None = None,
    options: dict[str, Any] | None = None,
) -> AsyncIterator[LLMStreamEvent]:
    """Invoke a registered agent and stream its response.

    The runtime dispatches :class:`LLMToolUseEvent`s mid-stream: when a
    provider emits a tool_use block, the event is yielded to the caller
    (so the UI can show "using tool X…"), the corresponding handler in
    :mod:`services.agent_tools` is invoked, the result is pushed back
    into the conversation as a ``role="tool"`` message keyed on the
    ``tool_call_id``, and the provider is re-called for a continuation.
    The loop is capped at :data:`_MAX_TOOL_ROUNDS` to bound a runaway
    tool-spam agent.

    Unknown agent ids surface as a single :class:`LLMErrorEvent` followed
    by a terminal :class:`LLMDoneEvent` so the SSE response always
    closes cleanly — clients only need one terminator.
    """
    spec = get_agent(agent_id)
    if spec is None:
        yield LLMErrorEvent(message=f"unknown agent: {agent_id!r}")
        yield LLMDoneEvent()
        return
    provider_id = _resolve_provider_id(spec, provider)
    resolved_model = _resolve_model(spec, model)
    messages = _compose_messages(spec, prompt, context_snapshot)
    adapter = get_provider(provider_id)

    rounds = 0
    while True:
        pending_tools: list[LLMToolUseEvent] = []
        seen_done = False
        async for event in adapter.stream_chat(
            messages=messages,
            model=resolved_model,
            api_key=api_key,
            **(options or {}),
        ):
            if isinstance(event, LLMToolUseEvent):
                pending_tools.append(event)
                yield event
                continue
            if isinstance(event, LLMDoneEvent):
                seen_done = True
                # If tools fired this round and we have budget left,
                # swallow the per-round terminator and loop. Otherwise
                # this is the final terminator and the SSE consumer
                # needs it.
                if pending_tools and rounds < _MAX_TOOL_ROUNDS:
                    break
                yield event
                return
            yield event
        if not seen_done:
            # Provider closed without a terminator — emit one so the SSE
            # framing stays well-formed for the consumer.
            yield LLMDoneEvent()
            return
        if not pending_tools:
            return

        # Dispatch every pending tool, append tool-result messages keyed
        # on the call ids, and re-enter the loop.
        for tool_call in pending_tools:
            result_str = await _dispatch_tool(tool_call)
            messages.append(
                LLMMessage(
                    role="tool",
                    content=result_str,
                    tool_call_id=tool_call.tool_call_id,
                )
            )
        rounds += 1
        if rounds >= _MAX_TOOL_ROUNDS:
            # Hit the cap — let the next provider stream finalise. The
            # subsequent loop iteration sees no pending tools and exits
            # via the ``not pending_tools`` branch above.
            continue
