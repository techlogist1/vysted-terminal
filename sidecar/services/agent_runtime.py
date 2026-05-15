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
)
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

    Unknown agent ids surface as a single :class:`LLMErrorEvent` followed by
    a terminal :class:`LLMDoneEvent` so the SSE response always closes
    cleanly — clients only need one terminator.
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
    async for event in adapter.stream_chat(
        messages=messages,
        model=resolved_model,
        api_key=api_key,
        **(options or {}),
    ):
        yield event
