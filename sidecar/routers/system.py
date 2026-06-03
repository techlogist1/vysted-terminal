"""System router — hardware capability + local-model fit (Track D).

``GET /system/hardware`` reports the detected device and scores models for the
local-vs-remote gate (FINDINGS §2.5): the installed ollama models (best-effort,
keyless) plus a few reference candidates so the UI can show, e.g., "your 16 GB
M1 can't run Tongyi-DeepResearch locally — using the remote path." The frontend
gates the heavy LOCAL toggles on these verdicts; the agent/research engine reuses
the same scorer so the gate is single-sourced.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import StreamingResponse

from services.hardware_fit import ModelCandidate, detect_device, score
from services.research import tongyi

router = APIRouter(prefix="/system", tags=["system"])

#: Default local ollama endpoint (keyless). Best-effort — absent in most installs.
_OLLAMA_URL = "http://127.0.0.1:11434"
_OLLAMA_TIMEOUT = 1.5

#: Small chat models scored for the first-run "use a local model" path (Path B).
#: Each is a reliable OpenAI-style tool-caller that fits a typical laptop; the
#: onboarding flow offers the best-fitting one for the detected device. Sized by
#: total params + a Q4_K_M quant (the ollama default), 8K context for the score.
_ONBOARDING_CANDIDATES: tuple[ModelCandidate, ...] = (
    ModelCandidate(name="qwen3:8b", total_params_b=8.2, quant="q4_k_m", desired_ctx=8192),
    ModelCandidate(name="qwen2.5-coder:7b", total_params_b=7.6, quant="q4_k_m", desired_ctx=8192),
    ModelCandidate(name="llama3.1:8b", total_params_b=8.0, quant="q4_k_m", desired_ctx=8192),
)


def _attr(obj: Any, key: str, default: Any = None) -> Any:
    """Read a field from a dict or an attr-styled SDK object (ollama ProgressResponse)."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


#: Reference candidates that illustrate the gate regardless of what's installed.
#: Tongyi-DeepResearch is the load-bearing one (Track C's local-vs-remote fork).
_REFERENCE_CANDIDATES: tuple[ModelCandidate, ...] = (
    ModelCandidate(
        name="Tongyi-DeepResearch-30B-A3B (IQ3_S)",
        file_size_bytes=int(13.3 * 1e9),
        total_params_b=30.5,
        active_params_b=3.3,
        quant="iq3_s",
    ),
    ModelCandidate(
        name="Tongyi-DeepResearch-30B-A3B (Q4_K_M)",
        file_size_bytes=int(18.6 * 1e9),
        total_params_b=30.5,
        active_params_b=3.3,
        quant="q4_k_m",
    ),
    ModelCandidate(name="Llama-3.x 14B (Q4_K_M)", total_params_b=14, quant="q4_k_m"),
)


def _parse_params_b(label: str | None) -> float | None:
    """Parse an ollama ``parameter_size`` label ("7.6B", "30.5B") to a float."""
    if not label:
        return None
    m = re.search(r"([\d.]+)\s*B", label, re.IGNORECASE)
    return float(m.group(1)) if m else None


async def _score_ollama_models(device: Any) -> list[dict[str, Any]]:
    """Query the local ollama daemon (if any) and score each installed model.

    Best-effort + keyless: any failure (no daemon, timeout) yields an empty list —
    ollama is an optional local accelerator, never a hard dependency.
    """
    try:
        async with httpx.AsyncClient(timeout=_OLLAMA_TIMEOUT) as client:
            resp = await client.get(f"{_OLLAMA_URL}/api/tags")
            resp.raise_for_status()
            data = resp.json()
    except Exception:  # noqa: BLE001 — ollama is optional; never surface an error
        return []

    scored: list[dict[str, Any]] = []
    for model in data.get("models", []) or []:
        details = model.get("details") or {}
        candidate = ModelCandidate(
            name=model.get("name", "unknown"),
            file_size_bytes=model.get("size"),
            total_params_b=_parse_params_b(details.get("parameter_size")),
            quant=(details.get("quantization_level") or "").lower() or None,
            desired_ctx=8192,
        )
        scored.append(score(candidate, device).to_dict())
    return scored


@router.get("/hardware")
async def get_hardware() -> dict[str, Any]:
    """Report the device profile + fit verdicts for the local-model gate."""
    device = detect_device()
    return {
        "device": device.to_dict(),
        "ollama": {
            "endpoint": _OLLAMA_URL,
            "models": await _score_ollama_models(device),
        },
        "referenceCandidates": [score(c, device).to_dict() for c in _REFERENCE_CANDIDATES],
    }


@router.get("/local-model-recommendation")
async def local_model_recommendation() -> dict[str, Any]:
    """Score the first-run local-model candidates against this device (Path B).

    Returns the device profile, every candidate's fit verdict, and the RECOMMENDED
    model to pull — the first GREEN (best tool-caller first), else the first
    MARGINAL, else ``null`` (the device can't comfortably host any small model, so
    onboarding should steer the user to the cloud-key path instead). Keyless +
    pure-compute (no daemon needed): it scores by spec, it does not require Ollama.
    """
    device = detect_device()
    scored = [score(c, device) for c in _ONBOARDING_CANDIDATES]
    recommended = next((v for v in scored if v.verdict == "green"), None) or next(
        (v for v in scored if v.verdict == "marginal"), None
    )
    return {
        "device": device.to_dict(),
        "candidates": [v.to_dict() for v in scored],
        "recommended": recommended.to_dict() if recommended else None,
    }


@router.get("/ollama/status")
async def ollama_status() -> dict[str, Any]:
    """Report whether the local Ollama daemon is reachable + what models are pulled.

    Best-effort + keyless. ``running: false`` (with an empty model list) means the
    daemon is not installed / not started — the onboarding flow then shows install
    guidance; ``running: true`` with a model already present means it can be used
    immediately (no pull). Never raises — Ollama is an optional local accelerator.
    """
    try:
        async with httpx.AsyncClient(timeout=_OLLAMA_TIMEOUT) as client:
            resp = await client.get(f"{_OLLAMA_URL}/api/tags")
            resp.raise_for_status()
            data = resp.json()
    except Exception:  # noqa: BLE001 — daemon absent/unreachable is a normal state
        return {"running": False, "endpoint": _OLLAMA_URL, "models": []}
    models = [m.get("name") for m in (data.get("models") or []) if m.get("name")]
    return {"running": True, "endpoint": _OLLAMA_URL, "models": models}


@router.post("/ollama/pull")
async def pull_ollama_model(
    model: Annotated[str, Query(min_length=1, description="Ollama model tag to pull.")],
) -> StreamingResponse:
    """Stream the progress of pulling an Ollama model as SSE (Path B setup).

    Wraps ``ollama.AsyncClient.pull(stream=True)`` and re-frames each
    ``ProgressResponse`` as a ``data: {json}`` SSE event ``{status, total,
    completed}`` so the UI can render a live download bar (never a frozen wait).
    A terminal ``{done: true}`` event closes the stream; any failure (daemon down,
    unknown model) closes with ``{error, done: true}`` rather than a 500. Local +
    keyless: it pulls an open model to the user's own machine — no §6.5 surface.
    """
    model_tag = model.strip()
    if not model_tag:
        raise HTTPException(status_code=400, detail="model is required")

    async def _generator() -> AsyncIterator[bytes]:
        try:
            import ollama

            client = ollama.AsyncClient()
            async for progress in await client.pull(model_tag, stream=True):
                payload = {
                    "status": _attr(progress, "status", "") or "",
                    "total": _attr(progress, "total", None),
                    "completed": _attr(progress, "completed", None),
                }
                yield f"data: {json.dumps(payload)}\n\n".encode()
            yield f"data: {json.dumps({'status': 'success', 'done': True})}\n\n".encode()
        except Exception as exc:  # noqa: BLE001 — surface as a stream error, not a 500
            yield f"data: {json.dumps({'error': str(exc), 'done': True})}\n\n".encode()

    return StreamingResponse(_generator(), media_type="text/event-stream")


@router.get("/deepresearch/probe")
async def probe_deep_research(
    x_openrouter_key: str | None = Header(default=None, alias="X-OpenRouter-Key"),
) -> dict[str, Any]:
    """Live routing probe for the deep-research engine SELECTOR (Track 5).

    Honestly reports what each engine WILL run right now so the Settings UI never
    implies Tongyi works when it doesn't: the native loop is always available; the
    Tongyi backend is probed against OpenRouter's live ``/endpoints`` and reports
    whether the dedicated slug is routing or the run will fall back to Qwen-A3B
    (plus a coarse cost estimate). The BYOK OpenRouter key arrives in the
    ``X-OpenRouter-Key`` header (renderer reads the keychain); it is used for the
    probe only and NEVER logged, echoed, or persisted.
    """
    native = {
        "available": True,
        "label": "Native (IterResearch)",
        "note": "Vysted's own bounded deep loop on your configured model — always available.",
    }

    if not tongyi.is_configured(x_openrouter_key):
        return {
            "native": native,
            "tongyi": {
                "slug": tongyi.TONGYI_SLUG,
                "configured": False,
                "live": False,
                "usingFallback": False,
                "resolvedModel": None,
                "note": "Add an OpenRouter key (BYOK) to route deep research through Tongyi.",
            },
        }

    # is_configured already validated the key is non-empty.
    assert x_openrouter_key is not None
    try:
        resolved = await tongyi.resolve_model(x_openrouter_key)
    except Exception:  # noqa: BLE001 — a probe miss is "use the fallback", never an error
        resolved = tongyi.FALLBACK_SLUGS[0]
    live = resolved == tongyi.TONGYI_SLUG
    return {
        "native": native,
        "tongyi": {
            "slug": tongyi.TONGYI_SLUG,
            "configured": True,
            "live": live,
            "usingFallback": not live,
            "resolvedModel": resolved,
            "estimateUsd": tongyi.estimate_cost_usd("deep research run"),
            "note": (
                "Tongyi routing OK on OpenRouter."
                if live
                else f"Tongyi unavailable on OpenRouter right now — using {resolved}."
            ),
        },
    }
