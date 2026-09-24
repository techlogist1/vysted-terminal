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
# OpenAI-shaped base URLs for DeepSeek + xAI + OpenRouter dispatch
# ---------------------------------------------------------------------------
# Read from ``default_base_url`` in config/model_registry.json (the one source,
# R15-CODE-AGENT-007); ``get_provider`` reads the registry at call time and these
# names stay as the import-time view. OpenRouter is a unified BROKER (one key,
# all upstreams): the adapter adds its attribution headers + cheapest-capable
# provider routing when provider_id is ``"openrouter"``.

DEEPSEEK_BASE_URL = model_registry.default_base_url_for("deepseek")
XAI_BASE_URL = model_registry.default_base_url_for("xai")
OPENROUTER_BASE_URL = model_registry.default_base_url_for("openrouter")


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
    if provider_id in ("deepseek", "xai", "openrouter"):
        return OpenAIProvider(
            base_url=base_url or model_registry.default_base_url_for(provider_id),
            provider_id=provider_id,
        )
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
