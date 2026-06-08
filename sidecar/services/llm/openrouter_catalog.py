"""OpenRouter live model catalog.

OpenRouter is a BROKER with hundreds of constantly-changing models, so a static
``known_models`` list goes stale immediately (the bug this fixes: the picker
still showed gpt-4o-mini / claude-3.5-sonnet). This fetches the live catalog and
— crucially for an agent that drives tools — marks each model's tool-calling
support so the UI can flag a model that would break host-actions.

Endpoint choice (verified against OpenRouter's docs + live API, JARVIS sprint):

- With a key we hit ``GET /api/v1/models/user`` (``Authorization: Bearer``),
  which narrows the ~340-model public catalog to what the caller's account can
  actually route given its provider preferences / privacy / guardrails — the
  right list for a BYOK user. Without a key we fall back to the public
  ``GET /api/v1/models`` (no auth, full catalog).
- Tool-capability uses the server-side ``?supported_parameters=tools`` filter
  (it reflects actually-routable-with-tools endpoints, not just the advertised
  union array), with a per-model ``supported_parameters`` check as the fallback
  when that second call fails.

The key is held only for the request and sent solely as the ``Authorization``
header — never logged, never persisted (the BYOK contract).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from models.llm import LLMModelOption

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
_TIMEOUT_SECS = 12.0
#: Attribution headers (leaderboard/analytics only; carry no secret).
_ATTRIBUTION = {"HTTP-Referer": "https://vysted.app", "X-Title": "Vysted Terminal"}


#: ``supported_parameters`` tokens that mean a model exposes its OWN server-side
#: web search (OpenRouter forwards these to the upstream's native search). Any one
#: present → ``web_search == "native"``.
_NATIVE_SEARCH_PARAMS = frozenset({"web_search_options", "web_search"})
#: ``supported_parameters`` tokens that mean the model can emit structured output.
_STRUCTURED_OUTPUT_PARAMS = frozenset({"structured_outputs", "response_format"})
#: ``supported_parameters`` tokens that mean the model exposes reasoning/thinking.
_REASONING_PARAMS = frozenset({"reasoning", "include_reasoning"})


def _params_set(model: dict[str, Any]) -> frozenset[str]:
    """The model's ``supported_parameters`` as a lower-cased string set."""
    params = model.get("supported_parameters") or []
    if not isinstance(params, (list, tuple)):
        return frozenset()
    return frozenset(str(p).lower() for p in params)


def _derive_web_search(params: frozenset[str], pricing: Any) -> str:
    """Per-model web-search capability (WS5): native > plugin > none.

    ``native`` — the model advertises its own server-side search param. ``plugin``
    — no native param, but OpenRouter prices a ``web_search`` plugin row for it (it
    can run the billed ``web`` plugin in front of any model). ``none`` — neither,
    so the agent keeps the local/BYOK search tool (FR-082 fallback).
    """
    if params & _NATIVE_SEARCH_PARAMS:
        return "native"
    # Match _format_pricing's numeric parse — a "0" string is truthy but is not a
    # real billed plugin, so coerce-and-compare rather than raw truthiness.
    if isinstance(pricing, dict) and float(pricing.get("web_search") or 0) > 0:
        return "plugin"
    return "none"


def _format_pricing(pricing: Any) -> str | None:
    """Render OpenRouter's per-token USD pricing as a compact ``per 1M`` hint."""
    if not isinstance(pricing, dict):
        return None
    try:
        prompt = float(pricing.get("prompt", 0) or 0) * 1_000_000
        completion = float(pricing.get("completion", 0) or 0) * 1_000_000
    except (TypeError, ValueError):
        return None
    if prompt == 0 and completion == 0:
        return "free"
    return f"${prompt:.2f} / ${completion:.2f} per 1M"


async def _get_data(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    tools_only: bool,
) -> list[dict[str, Any]]:
    """GET a models endpoint and return its ``data`` array (raises on non-2xx)."""
    params = {"supported_parameters": "tools"} if tools_only else None
    resp = await client.get(url, headers=headers, params=params)
    resp.raise_for_status()
    body = resp.json()
    data = body.get("data") if isinstance(body, dict) else None
    return data if isinstance(data, list) else []


async def fetch_openrouter_catalog(
    api_key: str | None,
    base_url: str | None = None,
) -> list[LLMModelOption]:
    """Fetch the live OpenRouter catalog as :class:`LLMModelOption`s.

    Returns ``[]`` (so the router serves the registry fallback) if the catalog
    can't be reached at all. Sorts tool-capable models first — the agent picker
    should surface them — then alphabetically by label.
    """
    base = (base_url or _DEFAULT_BASE_URL).rstrip("/")
    headers = dict(_ATTRIBUTION)
    use_user = bool(api_key)
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    path = "/models/user" if use_user else "/models"
    url = f"{base}{path}"

    async with httpx.AsyncClient(timeout=_TIMEOUT_SECS) as client:
        try:
            full = await _get_data(client, url, headers, tools_only=False)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            # A configured key that can't read the user-scoped list (401/403)
            # still deserves a live catalog — fall back to the public endpoint.
            if use_user and status in (401, 403):
                logger.info("openrouter /models/user rejected (%s); using public catalog", status)
                url = f"{base}/models"
                try:
                    full = await _get_data(client, url, headers, tools_only=False)
                except (httpx.HTTPError, ValueError):
                    return []
            else:
                logger.warning("openrouter catalog fetch failed: HTTP %s", status)
                return []
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("openrouter catalog fetch failed: %s", type(exc).__name__)
            return []

        # Authoritative tool-capable set from the server-side filter; on failure
        # we fall back to each model's advertised supported_parameters array.
        tool_ids: set[str] | None = None
        try:
            tool_data = await _get_data(client, url, headers, tools_only=True)
            tool_ids = {str(m["id"]) for m in tool_data if m.get("id")}
        except (httpx.HTTPError, ValueError):
            tool_ids = None

    options: list[LLMModelOption] = []
    for model in full:
        model_id = model.get("id")
        if not model_id:
            continue
        params = _params_set(model)
        # Tool support: the authoritative server-side filter when it answered,
        # else the model's advertised supported_parameters array.
        if tool_ids is not None:
            supports_tools: bool | None = model_id in tool_ids
        else:
            supports_tools = "tools" in params if params else None
        pricing_raw = model.get("pricing")
        options.append(
            LLMModelOption(
                id=str(model_id),
                label=str(model.get("name") or model_id),
                context_length=model.get("context_length"),
                supports_tools=supports_tools,
                pricing=_format_pricing(pricing_raw),
                # Per-model capability flags (WS5). Absent supported_parameters →
                # leave the metadata flags None (unknown), but web_search still
                # resolves (a missing array means no native param and, unless the
                # pricing carries a web_search row, "none").
                web_search=_derive_web_search(params, pricing_raw),
                supports_structured_outputs=(
                    bool(params & _STRUCTURED_OUTPUT_PARAMS) if params else None
                ),
                supports_reasoning=(bool(params & _REASONING_PARAMS) if params else None),
            )
        )

    options.sort(key=lambda opt: (opt.supports_tools is not True, opt.label.lower()))
    return options
