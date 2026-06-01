"""Tongyi-DeepResearch remote backend (Track C — the frontier DEEP engine).

Tongyi-DeepResearch-30B-A3B is Alibaba's open agentic deep-research model. Phase 0
(FINDINGS §2.4) settled the path: the MoE holds all ~30.5B params resident, so it
does NOT fit this 16 GB M1 (the fit-scorer marks it RED) — the verified path is
REMOTE via OpenRouter. This backend therefore drives Vysted's OWN bounded deep loop
(:func:`services.research.deep.run_deep_research`, so the live step-log still feeds
the activity surface) but binds the loop's LLM to OpenRouter's Tongyi model.

Two reality checks baked in (FINDINGS §2.4, verified against the live OpenRouter API):

- The ``alibaba/tongyi-deepresearch-30b-a3b`` slug is *listed but currently
  unreachable* (0 live endpoints). So the model is **runtime-probed**: if its
  ``/endpoints`` is non-empty we use it, otherwise we fall back to the closest
  live A3B analog (``qwen/qwen3-30b-a3b-thinking-2507``), then the strongest live
  agentic Qwen. The brief's provenance always names the model actually used.
- It is **opt-in + BYOK** (an OpenRouter key) and **never auto-selected** — the
  handler only reaches it on an explicit ``backend == "tongyi"`` with a key
  present (the same guard shape as the Perplexity backend).

No test makes a live call — the probe + completion seams are injected/mocked.
"""

from __future__ import annotations

import httpx

#: OpenRouter — the broker this backend rides (one BYOK key, OpenAI-shaped).
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

#: The dedicated Tongyi-DeepResearch slug (probe-gated — see module docstring).
TONGYI_SLUG = "alibaba/tongyi-deepresearch-30b-a3b"

#: Live, tool-capable fallbacks in preference order (closest A3B analog first).
FALLBACK_SLUGS: tuple[str, ...] = (
    "qwen/qwen3-30b-a3b-thinking-2507",
    "qwen/qwen3-235b-a22b-thinking-2507",
)

#: Provenance label stamped on a Tongyi-backed brief (the resolved model appended).
PROVENANCE_NOTE = "via Tongyi-DeepResearch (OpenRouter)"

#: Probe timeout — a quick endpoints check; failure just means "use the fallback".
_PROBE_TIMEOUT_SECS = 4.0

# Coarse pre-run cost estimate. Tongyi/Qwen-A3B on OpenRouter bill ~$0.09/1M in,
# ~$0.40/1M out; a multi-round deep run lands in a few cents. Surfaced before opt-in.
_ESTIMATE_BASE_USD = 0.03
_ESTIMATE_PER_CHAR_USD = 0.00004
_ESTIMATE_CEILING_USD = 0.15


def is_configured(api_key: str | None) -> bool:
    """Tongyi-remote needs an OpenRouter key (BYOK). Blank/absent → not configured
    (the handler shows a "needs a key" state and the path stays inert)."""
    return bool(api_key and api_key.strip())


def estimate_cost_usd(query: str) -> float:
    """Coarse per-run USD estimate (shown before opt-in). An ESTIMATE, not a bill —
    the real charge is OpenRouter's. Scales mildly with query length, clamped."""
    length = len((query or "").strip())
    return round(
        min(_ESTIMATE_CEILING_USD, _ESTIMATE_BASE_USD + length * _ESTIMATE_PER_CHAR_USD), 3
    )


async def resolve_model(api_key: str, *, client: httpx.AsyncClient | None = None) -> str:
    """Return the model slug to use: the dedicated Tongyi slug if it is reachable
    on OpenRouter right now, else the first live fallback.

    Best-effort: any probe error (network, non-2xx, malformed body) resolves to the
    fallback rather than raising — a deep run must never dead-end on a probe miss.
    """

    async def _probe(http: httpx.AsyncClient) -> bool:
        try:
            resp = await http.get(
                f"{OPENROUTER_BASE_URL}/models/{TONGYI_SLUG}/endpoints",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError):
            return False
        # OpenRouter shape: {"data": {"endpoints": [...]}} (or {"endpoints": [...]}).
        body = data.get("data", data) if isinstance(data, dict) else {}
        endpoints = body.get("endpoints") if isinstance(body, dict) else None
        return bool(isinstance(endpoints, list) and endpoints)

    reachable = False
    if client is not None:
        reachable = await _probe(client)
    else:
        async with httpx.AsyncClient(timeout=_PROBE_TIMEOUT_SECS) as http:
            reachable = await _probe(http)

    return TONGYI_SLUG if reachable else FALLBACK_SLUGS[0]


__all__ = [
    "FALLBACK_SLUGS",
    "OPENROUTER_BASE_URL",
    "PROVENANCE_NOTE",
    "TONGYI_SLUG",
    "estimate_cost_usd",
    "is_configured",
    "resolve_model",
]
