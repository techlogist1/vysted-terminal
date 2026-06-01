"""LLM provider dispatch.

Phase 3 ships seven BYOK providers, but only five have native SDK adapters
because DeepSeek and xAI are OpenAI-shaped — they ride on the OpenAI adapter
with a ``base_url`` override. Keeping that dispatch here (rather than in
two near-empty adapter files) is the Tier-3 documented choice (Phase 3 plan
§teammate-A).

The :func:`get_provider` factory resolves the ``LLMProviderId`` to a concrete
:class:`LLMProvider`. The factory is intentionally synchronous and stateless
— per-request API keys are passed into ``stream_chat`` / ``validate_key``,
not held on the adapter instance. The sidecar never persists a key.

Provider info table is the source of truth for ``GET /llm/providers``: the
chat sidebar reads it to populate the provider dropdown and the BYOK key
dialog.
"""

from __future__ import annotations

from typing import cast

from models.llm import LLMProviderId, LLMProviderInfo
from services import model_registry

from .anthropic import AnthropicProvider
from .base import LLMProvider
from .gemini import GeminiProvider
from .groq import GroqProvider
from .ollama import OllamaProvider
from .openai import OpenAIProvider

# ---------------------------------------------------------------------------
# OpenAI-shaped base URLs for DeepSeek + xAI dispatch
# ---------------------------------------------------------------------------
# These are the dispatch defaults baked into ``get_provider`` below. They must
# match the ``default_base_url`` for deepseek/xai in config/model_registry.json
# (the registry is the source of truth served to the frontend; these constants
# are the runtime dispatch fallback when no per-request override is supplied).

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
XAI_BASE_URL = "https://api.x.ai/v1"
#: OpenRouter — a unified BROKER (one key, all upstreams). OpenAI-shaped, so it
#: rides :class:`OpenAIProvider` with this base url; the adapter adds OpenRouter
#: attribution headers + cheapest-capable provider routing when provider_id is
#: ``"openrouter"`` (JARVIS sprint, FINDINGS §2.2).
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


#: Built from the single-source registry (``config/model_registry.json``) so
#: the provider list, labels, default base urls, default models, and selectable
#: model lists never drift from a second hardcoded copy. Source of truth for
#: ``GET /llm/providers``.
PROVIDER_INFO: tuple[LLMProviderInfo, ...] = tuple(
    LLMProviderInfo(
        id=cast(LLMProviderId, row["id"]),
        label=row["label"],
        requires_key=bool(row["requires_key"]),
        default_base_url=row.get("default_base_url"),
        default_model=row.get("default_model", ""),
        known_models=list(row.get("known_models", [])),
    )
    for row in model_registry.provider_rows()
)


def list_provider_info() -> list[LLMProviderInfo]:
    """Return the provider info rows in registry order."""
    return list(PROVIDER_INFO)


def get_provider(provider_id: LLMProviderId, base_url: str | None = None) -> LLMProvider:
    """Resolve a provider id to a concrete adapter instance.

    DeepSeek and xAI are dispatched to :class:`OpenAIProvider` with the
    appropriate ``base_url`` baked in — they speak the OpenAI chat-completions
    wire format end-to-end, so the SDK works as-is with the override.

    :param provider_id: One of the seven BYOK provider ids.
    :param base_url: Optional override; takes precedence over the dispatch
        default (used to point Ollama at a remote host, for example).
    :raises ValueError: When an unknown provider id is supplied.
    """
    if provider_id == "anthropic":
        return AnthropicProvider(base_url=base_url)
    if provider_id == "openai":
        return OpenAIProvider(base_url=base_url)
    if provider_id == "gemini":
        return GeminiProvider()
    if provider_id == "groq":
        return GroqProvider()
    if provider_id == "ollama":
        return OllamaProvider(base_url=base_url)
    if provider_id == "deepseek":
        return OpenAIProvider(base_url=base_url or DEEPSEEK_BASE_URL, provider_id="deepseek")
    if provider_id == "xai":
        return OpenAIProvider(base_url=base_url or XAI_BASE_URL, provider_id="xai")
    if provider_id == "openrouter":
        return OpenAIProvider(base_url=base_url or OPENROUTER_BASE_URL, provider_id="openrouter")
    raise ValueError(f"Unknown LLM provider id: {provider_id!r}")


__all__ = [
    "DEEPSEEK_BASE_URL",
    "OPENROUTER_BASE_URL",
    "PROVIDER_INFO",
    "XAI_BASE_URL",
    "LLMProvider",
    "get_provider",
    "list_provider_info",
]
