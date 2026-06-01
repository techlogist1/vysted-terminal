"""One-shot LLM completion helper for the deep-research loop.

The native ``deep_research`` loop (``services.research.deep``) needs to call the
SAME model the user is talking to for plan/synthesis steps, but it never wants
the streaming/tool-use machinery the chat router uses — it just wants the final
text of one completion. :func:`complete` is that seam: it builds an
:class:`~models.llm.LLMMessage` list from plain dicts, drives the provider's
:meth:`~services.llm.base.LLMProvider.stream_chat`, JOINS the streamed delta
text into one string, ignores any tool-use events, and stops at the ``done``
terminator.

It is deliberately defensive — the research loop tolerates an empty completion,
so any adapter/transport error returns ``""`` rather than propagating. The loop
re-plans or degrades gracefully instead of crashing a long-running run.
"""

from __future__ import annotations

import logging
from typing import Any

from models.llm import LLMMessage
from services.llm import get_provider

logger = logging.getLogger(__name__)


def _to_messages(messages: list[dict[str, Any]]) -> list[LLMMessage]:
    """Build the typed :class:`LLMMessage` list from plain role/content dicts.

    Unknown keys are ignored; ``role`` defaults to ``"user"`` and ``content`` to
    ``""`` so a slightly-malformed dict never crashes the completion.
    """
    out: list[LLMMessage] = []
    for msg in messages:
        out.append(
            LLMMessage(
                role=msg.get("role", "user"),
                content=str(msg.get("content", "")),
            )
        )
    return out


async def complete(
    provider: str,
    model: str,
    api_key: str | None,
    messages: list[dict[str, Any]],
) -> str:
    """Run one non-streaming completion and return the joined text.

    Resolves the provider adapter, streams a chat completion, concatenates every
    :class:`~models.llm.LLMDeltaEvent` text, ignores tool-use/thinking events,
    and stops at the ``done`` terminator. On ANY adapter or transport error
    returns ``""`` — the deep-research loop tolerates an empty completion.

    :param provider: BYOK provider id (``"anthropic"``, ``"openai"``, …).
    :param model: Provider-specific model id.
    :param api_key: BYOK key (held in memory for the call only; never persisted).
    :param messages: Conversation as plain ``{"role", "content"}`` dicts.
    """
    parts: list[str] = []
    try:
        adapter = get_provider(provider)  # type: ignore[arg-type]
        stream = adapter.stream_chat(
            messages=_to_messages(messages),
            model=model,
            api_key=api_key,
        )
        async for event in stream:
            kind = getattr(event, "kind", None)
            if kind == "delta":
                parts.append(getattr(event, "text", "") or "")
            elif kind == "done":
                break
            elif kind == "error":
                # An error terminator ends the stream; return whatever we have.
                break
            # tool_use / thinking events are ignored — this is a one-shot text call.
    except Exception:  # noqa: BLE001 - the loop tolerates an empty completion
        logger.debug("oneshot.complete failed for provider=%s model=%s", provider, model)
        return "".join(parts)
    return "".join(parts)


__all__ = ["complete"]
