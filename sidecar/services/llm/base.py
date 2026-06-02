"""LLM provider ABC.

Every provider adapter implements this contract — :meth:`stream_chat` yields
discriminated :class:`LLMStreamEvent` Pydantic models, and :meth:`validate_key`
returns ``True`` when a cheap probe against the provider succeeds.

Keys are NEVER persisted on the adapter — they are passed in per call so the
sidecar can hold them in memory only for the request lifecycle. The frontend
keychain (``src/lib/keychain.ts``) reads the key from the OS keychain and
attaches it to the request body; the router unwraps it and forwards into
``stream_chat``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from models.llm import (
    LLMAgentPlanEvent,
    LLMDeltaEvent,
    LLMDoneEvent,
    LLMErrorEvent,
    LLMMessage,
    LLMModelOption,
    LLMResearchStepEvent,
    LLMThinkingEvent,
    LLMToolUseEvent,
)

#: One streaming event — the discriminated union the SSE router serialises.
LLMStreamEvent = (
    LLMDeltaEvent
    | LLMToolUseEvent
    | LLMResearchStepEvent
    | LLMAgentPlanEvent
    | LLMThinkingEvent
    | LLMDoneEvent
    | LLMErrorEvent
)

#: Substring hints that mark a non-chat model id (embeddings, audio, image,
#: moderation, …) so the OpenAI-shaped + Groq live catalogs don't pollute a
#: chat-model picker with whisper/dall-e/embedding ids. Best-effort, lower-cased
#: match; the contract keeps model ids open strings so a missed filter is never
#: fatal (the user can still type any id).
_NON_CHAT_HINTS = (
    "embed",
    "whisper",
    "tts",
    "dall-e",
    "dalle",
    "moderation",
    "rerank",
    "audio",
    "transcrib",
    "speech",
    "image",
    "stable-diffusion",
    "flux",
    "guard",
)


def is_chat_model(model_id: str) -> bool:
    """Heuristic: ``True`` unless the id clearly names a non-chat model.

    Used to filter a provider's full ``/models`` list down to chat-capable
    entries for the dropdown. Conservative by design — it only drops ids that
    name a different modality (embeddings/audio/image/moderation).
    """
    low = model_id.lower()
    return not any(hint in low for hint in _NON_CHAT_HINTS)


class LLMProvider(ABC):
    """The shape every BYOK provider adapter implements.

    The constructor takes adapter-level config (currently just an optional
    ``base_url`` for the OpenAI-shaped providers); per-request fields like
    the API key and the model id are passed into :meth:`stream_chat`.
    """

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[LLMMessage],
        model: str,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[LLMStreamEvent]:
        """Stream a chat completion as discriminated :class:`LLMStreamEvent`s.

        Adapters MUST emit a final :class:`LLMDoneEvent` on clean completion or
        an :class:`LLMErrorEvent` on failure — the router relies on the
        terminator to close the SSE response.

        :param messages: The conversation, oldest first. The adapter may
            translate ``role="system"`` messages into the provider's native
            system-prompt slot.
        :param model: Provider-specific model id (e.g. ``"claude-opus-4-8"``,
            ``"gpt-4.1-mini"``, ``"llama3.1:70b"``).
        :param api_key: BYOK key; required for all providers except Ollama.
        :param kwargs: Provider-specific options (temperature, max tokens, …).
        """
        raise NotImplementedError

    @abstractmethod
    async def validate_key(self, api_key: str | None = None) -> bool:
        """Return ``True`` if ``api_key`` authenticates against the provider.

        Implementations should make the cheapest possible probe (typically a
        models-list call). They MUST NOT raise on a 401/403 — return ``False``.
        They MAY raise on a transport error so the router can surface a
        distinct "provider unreachable" status.
        """
        raise NotImplementedError

    async def list_models(self, api_key: str | None = None) -> list[LLMModelOption]:
        """Return the provider's LIVE model catalog (``GET /llm/models``).

        Default is ``[]`` — meaning "no live list; the router serves the
        registry ``known_models`` fallback". Adapters override to surface what
        their ``validate_key`` probe already fetches and throws away. Like
        ``validate_key`` this MUST NOT raise on a 401/403 (return ``[]`` so the
        fallback kicks in); it MAY raise on a transport error, which the router
        catches and degrades to the fallback list.
        """
        return []
