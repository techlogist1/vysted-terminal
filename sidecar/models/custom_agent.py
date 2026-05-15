"""Custom-agent Pydantic models.

The Custom Agent Builder (BLUEPRINT module 36 — separate from the 12 first-
party agents) lets the user define their own agent: id, display name, lens
description, system prompt, allow-listed tools, and a default provider/model.
The resulting record is persisted in a sidecar SQLite store
(``services.agents_store``) and surfaced alongside first-party agents in the
chat sidebar's picker.

Field names mirror the ``AgentSpec`` interface in ``types/plugin.ts`` (the
locked Tier-1 plugin contract) as closely as Pydantic conventions allow — the
Python snake_case names map to the TS camelCase fields via the
``model_dump(by_alias=False)`` default plus explicit aliasing on the read
model. Keeping these two shapes lockstep is a CLAUDE.md gotcha: change the
TS shape and this model in the same commit.

Custom-agent ids MUST start with ``custom:``. The router enforces that on
write; this module's validators enforce it on the wire too so a sidecar test
fails fast if the constraint regresses.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

#: The closed set of tool ids the host currently resolves. Mirrors the
#: discovery contract in ``sidecar/agents/`` and the Phase-3 plan brief —
#: keeping this list in code means the router rejects unknown tool ids at the
#: API boundary rather than letting an invalid agent slip into the store.
KNOWN_TOOL_IDS: frozenset[str] = frozenset(
    {
        "price_data",
        "fundamentals",
        "news",
        "backtest_summary",
        "macro",
    }
)

#: The seven BYOK provider ids accepted in ``default_provider``. Identical to
#: the ``LLMProviderId`` discriminated union in ``types/ai.ts``.
KNOWN_PROVIDER_IDS: frozenset[str] = frozenset(
    {
        "anthropic",
        "openai",
        "gemini",
        "groq",
        "ollama",
        "deepseek",
        "xai",
    }
)

#: Required prefix for every custom-agent id — prevents collisions with the
#: 12 first-party agent ids (``buffett``, ``graham``, …) and makes the chat
#: picker's "First-party" vs "Custom" grouping trivial.
CUSTOM_AGENT_ID_PREFIX = "custom:"


class _BaseCustomAgent(BaseModel):
    """Common validators shared between create and update payloads."""

    @field_validator("tools", check_fields=False)
    @classmethod
    def _validate_tools(cls, tools: list[str]) -> list[str]:
        """Reject any tool id that is not on the host's allow-list."""
        unknown = [tool for tool in tools if tool not in KNOWN_TOOL_IDS]
        if unknown:
            raise ValueError(
                f"unknown tool ids: {sorted(unknown)!r}; allowed: {sorted(KNOWN_TOOL_IDS)!r}"
            )
        # De-duplicate while preserving order — JSON serialization is more
        # ergonomic if the order matches the user's chosen list.
        seen: set[str] = set()
        ordered: list[str] = []
        for tool in tools:
            if tool not in seen:
                seen.add(tool)
                ordered.append(tool)
        return ordered

    @field_validator("default_provider", check_fields=False)
    @classmethod
    def _validate_provider(cls, value: str) -> str:
        """Reject provider ids the LLM layer does not recognise."""
        if value not in KNOWN_PROVIDER_IDS:
            raise ValueError(
                f"unknown provider id: {value!r}; allowed: {sorted(KNOWN_PROVIDER_IDS)!r}"
            )
        return value


class CustomAgentCreate(_BaseCustomAgent):
    """Body for ``POST /custom-agents``.

    The ``id`` field carries the user's chosen id and MUST start with
    ``custom:``; the router additionally checks that the id is unique against
    the existing rows so two creates can't collide.
    """

    id: str = Field(min_length=len(CUSTOM_AGENT_ID_PREFIX) + 1)
    name: str = Field(min_length=1)
    philosophy: str = Field(min_length=1)
    system_prompt: str = Field(min_length=1)
    tools: list[str] = Field(default_factory=list)
    default_provider: str
    default_model: str | None = None
    icon: str | None = None

    @field_validator("id")
    @classmethod
    def _validate_id_prefix(cls, value: str) -> str:
        """Reject any id that is not prefixed ``custom:``."""
        if not value.startswith(CUSTOM_AGENT_ID_PREFIX):
            raise ValueError(
                f"custom-agent id must start with {CUSTOM_AGENT_ID_PREFIX!r} (got {value!r})"
            )
        # The bit after the prefix must contain at least one character.
        if value == CUSTOM_AGENT_ID_PREFIX:
            raise ValueError("custom-agent id requires a body after the prefix")
        return value


class CustomAgentUpdate(_BaseCustomAgent):
    """Body for ``PUT /custom-agents/{id}``.

    The id comes from the URL path, never the body — that matches the
    plugins router's update shape and prevents a body-vs-path mismatch
    causing one create-then-rename via PUT.
    """

    name: str = Field(min_length=1)
    philosophy: str = Field(min_length=1)
    system_prompt: str = Field(min_length=1)
    tools: list[str] = Field(default_factory=list)
    default_provider: str
    default_model: str | None = None
    icon: str | None = None


class CustomAgentRead(BaseModel):
    """Read shape returned by every endpoint.

    Adds ``created_at`` / ``updated_at`` timestamps (epoch seconds) so the
    Custom Agent Builder UI can show "last saved" and sort by recency. The
    underlying SQLite columns are ``INTEGER`` so an integer is what the wire
    carries — the frontend converts to a JS ``Date`` if it needs one.
    """

    id: str
    name: str
    philosophy: str
    system_prompt: str
    tools: list[str] = Field(default_factory=list)
    default_provider: str
    default_model: str | None = None
    icon: str | None = None
    created_at: int
    updated_at: int
