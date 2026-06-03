"""Tongyi-DeepResearch remote backend (Track C — the frontier DEEP engine).

Tongyi-DeepResearch-30B-A3B is Alibaba's open agentic deep-research model. Phase 0
(FINDINGS §2.4) settled the path: the MoE holds all ~30.5B params resident, so it
does NOT fit this 16 GB M1 (the fit-scorer marks it RED) — the verified path is
REMOTE via OpenRouter. This backend therefore drives Vysted's OWN bounded deep loop
(:func:`services.research.deep.run_deep_research`, so the live step-log still feeds
the activity surface) but binds the loop's LLM to OpenRouter's Tongyi model.

Two reality checks baked in (FINDINGS §2.4, verified against the live OpenRouter API):

- The ``alibaba/tongyi-deepresearch-30b-a3b`` slug is currently *unrouted* — a real
  call returns OpenRouter's own 404 "No endpoints found" (verified 2026-06-03 with a
  live key; the listing PAGE still shows pricing, which is not the same as a serving
  provider). So the model is **runtime-probed by a real minimal completion** (NOT the
  ``/endpoints`` listing, which lags and is account-scoped): a 200 with a `choices`
  payload → use it; a 404/error → fall back to the closest live A3B analog
  (``qwen/qwen3-coder-30b-a3b-instruct`` — a NON-thinking instruct model, so it
  won't stall the loop with long reasoning streams), then the strongest live
  agentic Qwen. The brief's provenance always names the model actually used, and the probe flips to
  Tongyi automatically the instant a provider serves it again.
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
#: Leads with the NON-THINKING instruct A3B: it's the closest live analog to the
#: unrouted Tongyi-DeepResearch-30B-A3B and, unlike a "thinking" variant, it does
#: NOT emit long reasoning streams that stall a multi-round research loop (the
#: 8-minutes-unfinished bug). ``resolve_model`` returns ``FALLBACK_SLUGS[0]`` on a
#: probe miss, so the first entry is the one that actually runs.
FALLBACK_SLUGS: tuple[str, ...] = (
    "qwen/qwen3-coder-30b-a3b-instruct",
    "qwen/qwen3-30b-a3b",
    "qwen/qwen3-235b-a22b-thinking-2507",
)

#: Provenance label stamped on a Tongyi-backed brief (the resolved model appended).
PROVENANCE_NOTE = "via Tongyi-DeepResearch (OpenRouter)"

#: Probe timeout — a minimal live completion; failure just means "use the fallback".
_PROBE_TIMEOUT_SECS = 8.0

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
    """Return the model slug to use: the dedicated Tongyi slug if it is ACTUALLY
    CALLABLE on OpenRouter right now, else the first live fallback.

    Routability is checked the HONEST way — a minimal `/chat/completions` (the same
    call a real run makes, capped at one token) — NOT the `/models/.../endpoints`
    listing. The listing lags/omits served models and is account-scoped, so it
    can both (a) report `[]` for a model that is in fact callable and (b) be masked
    by a BYOK provider whose catalog excludes the author (verified 2026-06-03: a
    real call to the Tongyi slug returns OpenRouter's own 404 "No endpoints found"
    while the Qwen-A3B fallback completes on the same key — a genuine routing gap,
    not a probe artefact). A 200 with a real `choices` payload → routable; a 404 /
    error / 200-with-error-body → fall back. Best-effort: never raises (a deep run
    must not dead-end on a probe miss). The instant a provider serves Tongyi again,
    this flips to the dedicated slug with no code change.
    """

    payload = {
        "model": TONGYI_SLUG,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
        "temperature": 0,
    }

    async def _probe(http: httpx.AsyncClient) -> bool:
        try:
            resp = await http.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
        except httpx.HTTPError:
            return False
        if resp.status_code != 200:
            return False  # 404 "No endpoints found" / 4xx / 5xx → not callable
        try:
            data = resp.json()
        except ValueError:
            return False
        # OpenRouter can return 200 with an error body; a routable model returns
        # a non-empty `choices` array.
        if not isinstance(data, dict) or data.get("error"):
            return False
        return bool(data.get("choices"))

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
