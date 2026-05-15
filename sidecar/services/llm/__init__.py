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

from models.llm import LLMProviderId, LLMProviderInfo

from .anthropic import AnthropicProvider
from .base import LLMProvider
from .gemini import GeminiProvider
from .groq import GroqProvider
from .ollama import OllamaProvider
from .openai import OpenAIProvider

# ---------------------------------------------------------------------------
# OpenAI-shaped base URLs for DeepSeek + xAI dispatch
# ---------------------------------------------------------------------------

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
XAI_BASE_URL = "https://api.x.ai/v1"


PROVIDER_INFO: tuple[LLMProviderInfo, ...] = (
    LLMProviderInfo(id="anthropic", label="Anthropic", requires_key=True),
    LLMProviderInfo(id="openai", label="OpenAI", requires_key=True),
    LLMProviderInfo(id="gemini", label="Google Gemini", requires_key=True),
    LLMProviderInfo(id="groq", label="Groq", requires_key=True),
    LLMProviderInfo(
        id="ollama",
        label="Ollama (local)",
        requires_key=False,
        default_base_url="http://127.0.0.1:11434",
    ),
    LLMProviderInfo(
        id="deepseek",
        label="DeepSeek",
        requires_key=True,
        default_base_url=DEEPSEEK_BASE_URL,
    ),
    LLMProviderInfo(
        id="xai",
        label="xAI",
        requires_key=True,
        default_base_url=XAI_BASE_URL,
    ),
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
    raise ValueError(f"Unknown LLM provider id: {provider_id!r}")


__all__ = [
    "DEEPSEEK_BASE_URL",
    "PROVIDER_INFO",
    "XAI_BASE_URL",
    "LLMProvider",
    "get_provider",
    "list_provider_info",
]
