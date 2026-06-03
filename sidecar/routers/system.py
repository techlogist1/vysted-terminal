"""System router — hardware capability + local-model fit (Track D).

``GET /system/hardware`` reports the detected device and scores models for the
local-vs-remote gate (FINDINGS §2.5): the installed ollama models (best-effort,
keyless) plus a few reference candidates so the UI can show, e.g., "your 16 GB
M1 can't run Tongyi-DeepResearch locally — using the remote path." The frontend
gates the heavy LOCAL toggles on these verdicts; the agent/research engine reuses
the same scorer so the gate is single-sourced.
"""

from __future__ import annotations

import re
from typing import Any

import httpx
from fastapi import APIRouter, Header

from services.hardware_fit import ModelCandidate, detect_device, score
from services.research import tongyi

router = APIRouter(prefix="/system", tags=["system"])

#: Default local ollama endpoint (keyless). Best-effort — absent in most installs.
_OLLAMA_URL = "http://127.0.0.1:11434"
_OLLAMA_TIMEOUT = 1.5

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
