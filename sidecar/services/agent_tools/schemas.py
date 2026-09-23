"""Provider-neutral tool schemas — the contract the model sees.

This module is a **projection** of the single capability catalog
(:mod:`services.agent_tools.catalog`). It declares nothing of its own: it reads
the catalog's ``internal`` capabilities and serialises them into each provider's
native tool shape. Adding or changing a tool happens in ``catalog.py`` — the
serialisers below and every adapter that imports them pick the change up for free
(Constitution Principle II: define once, project to all consumers).

Read-tool ids (``price_data``, ``fundamentals``, …) map to the registered
handlers in this package. The per-invocation ids (``get_terminal_state``,
``get_portfolio``) and the host-action ids (``open_panel``, ``set_chart_symbol``,
``add_to_watchlist``, …) are resolved inside ``invoke_agent`` (they need request
scope / drive the frontend) — they appear here only so the model is told they
exist.

SAFETY (§6.5): host actions drive the cockpit and the user's local data writes
(tracked portfolio, notes, screens, layouts) through the proposed-changes gate.
No trading tool exists (D81).
"""

from __future__ import annotations

from typing import Any

from services.agent_tools.catalog import (
    CAPABILITY_CATALOG,
    internal_capabilities,
)

#: {tool_id: {description, input_schema}} — the internal-consumer projection of
#: the catalog. input_schema is JSON Schema (the draft-07 subset Anthropic +
#: OpenAI + Gemini all accept). Derived; do not hand-edit (edit catalog.py).
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    cap.id: {"description": cap.description, "input_schema": cap.input_schema}
    for cap in internal_capabilities()
}

#: Ids resolved inside invoke_agent rather than the global registry.
PER_INVOCATION_READ_TOOLS: tuple[str, ...] = tuple(
    cap.id for cap in CAPABILITY_CATALOG.values() if cap.kind == "per_invocation"
)
HOST_ACTION_TOOLS: tuple[str, ...] = tuple(
    cap.id for cap in CAPABILITY_CATALOG.values() if cap.kind == "host_action"
)


def _known(tool_ids: list[str]) -> list[str]:
    return [tid for tid in tool_ids if tid in TOOL_SCHEMAS]


def anthropic_tools(tool_ids: list[str]) -> list[dict[str, Any]]:
    """``[{name, description, input_schema}]`` for the Anthropic Messages API."""
    return [
        {
            "name": tid,
            "description": TOOL_SCHEMAS[tid]["description"],
            "input_schema": TOOL_SCHEMAS[tid]["input_schema"],
        }
        for tid in _known(tool_ids)
    ]


def openai_tools(tool_ids: list[str]) -> list[dict[str, Any]]:
    """``[{type:'function', function:{...}}]`` for OpenAI / DeepSeek / xAI / Groq."""
    return [
        {
            "type": "function",
            "function": {
                "name": tid,
                "description": TOOL_SCHEMAS[tid]["description"],
                "parameters": TOOL_SCHEMAS[tid]["input_schema"],
            },
        }
        for tid in _known(tool_ids)
    ]


def gemini_tools(tool_ids: list[str]) -> list[dict[str, Any]]:
    """Gemini ``function_declarations`` shape (single tool with N declarations)."""
    known = _known(tool_ids)
    if not known:
        return []
    return [
        {
            "function_declarations": [
                {
                    "name": tid,
                    "description": TOOL_SCHEMAS[tid]["description"],
                    "parameters": TOOL_SCHEMAS[tid]["input_schema"],
                }
                for tid in known
            ]
        }
    ]
