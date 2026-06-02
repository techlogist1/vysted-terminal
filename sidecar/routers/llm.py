"""LLM router — BYOK chat streaming, key validation, provider catalog.

The chat sidebar (Teammate A frontend) calls these endpoints:

- ``GET /llm/providers`` — list the seven BYOK providers (id, label, needs-key
  flag, default base URL). Populates the provider dropdown.
- ``POST /llm/keys/validate`` — cheap probe (provider's models-list) so the
  Key Entry Dialog can confirm a key before saving it to the keychain.
- ``POST /llm/chat`` — open a Server-Sent Events stream of
  :class:`LLMStreamEvent` JSON frames. The native browser ``EventSource``
  re-assembles the deltas into a chat message.

Streaming protocol: ``text/event-stream`` with ``data: <json>\\n\\n`` framing.
Each ``data:`` line is one Pydantic-serialised event from the adapter; the
terminator is a ``done`` event (success) or ``error`` event (failure).
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from models.llm import (
    LLMChatRequest,
    LLMKeyValidationRequest,
    LLMKeyValidationResponse,
    LLMModelCatalog,
    LLMModelOption,
    LLMProviderId,
    LLMProviderInfo,
)
from services import model_registry
from services.llm import get_provider, list_provider_info
from services.llm.base import LLMStreamEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/providers")
def get_providers() -> list[LLMProviderInfo]:
    """Return the seven BYOK provider catalog entries."""
    return list_provider_info()


@router.get("/models")
async def get_models(
    provider: LLMProviderId,
    base_url: str | None = None,
    x_llm_key: str | None = Header(default=None, alias="X-LLM-Key"),
) -> LLMModelCatalog:
    """Return a provider's LIVE model catalog, with a registry fallback.

    The BYOK key rides the ``X-LLM-Key`` header (read-only-plugin pattern: secret
    in a header, never the body/query/log) so the OpenRouter path can narrow to
    the caller's account-routable models. When the live fetch fails or returns
    nothing, the registry ``known_models`` are served with ``source="fallback"``
    so the picker is never empty. GET-only, never echoes the key.
    """
    try:
        adapter = get_provider(provider, base_url=base_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    models: list[LLMModelOption] = []
    try:
        models = await adapter.list_models(x_llm_key)
    except Exception as exc:  # noqa: BLE001 — any transport failure degrades to fallback
        logger.warning("provider %s model-list error: %s", provider, type(exc).__name__)

    if models:
        tool_count = sum(1 for model in models if model.supports_tools)
        if provider == "openrouter":
            scope = "routable on your key" if x_llm_key else "full catalog"
            note = f"Live · {scope} · {len(models)} models, {tool_count} tool-capable"
        elif tool_count:
            note = f"Live · {len(models)} models, {tool_count} tool-capable"
        else:
            note = f"Live · {len(models)} models"
        return LLMModelCatalog(provider=provider, models=models, source="live", note=note)

    fallback = [
        LLMModelOption(id=mid, label=mid) for mid in model_registry.known_models_for(provider)
    ]
    return LLMModelCatalog(
        provider=provider,
        models=fallback,
        source="fallback",
        note="Live catalog unavailable — showing known models",
    )


@router.post("/keys/validate")
async def validate_key(payload: LLMKeyValidationRequest) -> LLMKeyValidationResponse:
    """Probe the provider with the supplied key; return a binary OK / not-OK."""
    adapter = get_provider(payload.provider, base_url=payload.base_url)
    try:
        ok = await adapter.validate_key(payload.api_key)
    except Exception as exc:  # noqa: BLE001 — surface any transport failure
        logger.warning("provider %s validation transport error: %s", payload.provider, exc)
        return LLMKeyValidationResponse(ok=False, detail=f"transport error: {exc}")
    return LLMKeyValidationResponse(
        ok=ok,
        detail=None if ok else "unauthorized or no key supplied",
    )


@router.post("/chat")
async def chat_stream(payload: LLMChatRequest) -> StreamingResponse:
    """Open an SSE stream of :class:`LLMStreamEvent` JSON frames."""
    try:
        adapter = get_provider(payload.provider, base_url=payload.base_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async def _generator() -> AsyncIterator[bytes]:
        try:
            async for event in adapter.stream_chat(
                messages=payload.messages,
                model=payload.model,
                api_key=payload.api_key,
                **payload.options,
            ):
                yield _encode_event(event)
        except Exception as exc:  # noqa: BLE001 — last-resort guard
            logger.exception("chat stream crashed: %s", exc)
            yield _encode_event_dict({"kind": "error", "message": str(exc)})
            yield _encode_event_dict({"kind": "done"})

    return StreamingResponse(_generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# SSE encoding helpers
# ---------------------------------------------------------------------------


def _encode_event(event: LLMStreamEvent) -> bytes:
    """Serialise one :class:`LLMStreamEvent` as an SSE ``data:`` frame."""
    return _encode_event_dict(event.model_dump())


def _encode_event_dict(payload: dict) -> bytes:
    """Encode an already-dict event payload as an SSE ``data:`` frame."""
    return f"data: {json.dumps(payload)}\n\n".encode()
