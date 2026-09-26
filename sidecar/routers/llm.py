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
    LLMDoneEvent,
    LLMKeyValidationRequest,
    LLMKeyValidationResponse,
    LLMModelCatalog,
    LLMModelOption,
    LLMProviderId,
    LLMProviderInfo,
)
from services import budget_guard, model_registry
from services.errors import error_frame, humanize
from services.llm import get_provider, list_provider_info, scrub_adapter_options
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

    This route alone carries the key in the ``X-LLM-Key`` header — a GET can't
    carry a body — so the OpenRouter path can narrow to the caller's
    account-routable models; ``POST /llm/chat`` and ``POST /llm/keys/validate``
    below carry it as an ``api_key`` JSON body field instead (never the query
    string or a log, on any of the three). When the live fetch fails or returns
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
    """Say whether the provider is usable now and, when not, why.

    ``reason`` tells apart a missing key (``not_configured``), a rejected key
    (``invalid``), a provider or daemon that cannot be reached (``unreachable``)
    and a local model that is not pulled (``model_not_pulled``). The key is
    stripped here: a pasted trailing newline is not a different key.
    """
    api_key = (payload.api_key or "").strip() or None
    info = next(p for p in list_provider_info() if p.id == payload.provider)
    if info.requires_key and api_key is None:
        return LLMKeyValidationResponse(
            ok=False, reason="not_configured", detail=f"No API key is set for {info.label}."
        )
    adapter = get_provider(payload.provider, base_url=payload.base_url)
    try:
        ok = await adapter.validate_key(api_key)
    except Exception as exc:  # noqa: BLE001 — any transport failure means unreachable
        logger.warning("provider %s validation transport error: %s", payload.provider, exc)
        # The raw SDK exception text (`{type(exc).__name__}: {exc}`) stays in the
        # log only — the Key Entry Dialog gets humanize()'s sentence + action,
        # same as every other failure surface in this subsystem (R15-CODE-AGENT-019).
        human = humanize(payload.provider, exc)
        detail = f"{human.message} {human.action}" if human.action else human.message
        return LLMKeyValidationResponse(ok=False, reason="unreachable", detail=detail)
    if not ok:
        return LLMKeyValidationResponse(
            ok=False, reason="invalid", detail=f"{info.label} rejected this key."
        )
    if not info.requires_key and payload.model:
        # A keyless provider's live catalog is what is installed locally.
        pulled = {m.id for m in await adapter.list_models(None)}
        if payload.model not in pulled and f"{payload.model}:latest" not in pulled:
            return LLMKeyValidationResponse(
                ok=False,
                reason="model_not_pulled",
                detail=f"{payload.model} is not downloaded in {info.label} yet.",
            )
    return LLMKeyValidationResponse(ok=True)


@router.post("/chat")
async def chat_stream(payload: LLMChatRequest) -> StreamingResponse:
    """Open an SSE stream of :class:`LLMStreamEvent` JSON frames."""
    try:
        adapter = get_provider(payload.provider, base_url=payload.base_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Only adapter kwargs reach the SDK: an OpenAI-shaped client raises
    # TypeError on an unknown one (live repro: `research_depth` killed a
    # DeepSeek stream). The same allowlist as the agent path.
    adapter_options = scrub_adapter_options(payload.options)

    async def _generator() -> AsyncIterator[bytes]:
        try:
            async for event in adapter.stream_chat(
                messages=payload.messages,
                model=payload.model,
                api_key=payload.api_key,
                **adapter_options,
            ):
                if isinstance(event, LLMDoneEvent):
                    event.spend_usd = budget_guard.spend_usd(
                        payload.provider, payload.model, event.usage
                    )
                yield _encode_event(event)
        except Exception as exc:  # noqa: BLE001 — last-resort guard
            logger.exception("chat stream crashed: %s", exc)
            # E9: humanize — plain message + action + code, raw text in detail.
            yield _encode_event_dict(error_frame(exc))
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
