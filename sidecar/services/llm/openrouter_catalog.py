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
  right list for a BYOK user (e.g. an Amazon Bedrock integration). Without a key
  we fall back to the public ``GET /api/v1/models`` (no auth, full catalog).
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
        if tool_ids is not None:
            supports_tools: bool | None = model_id in tool_ids
        else:
            params = model.get("supported_parameters") or []
            supports_tools = "tools" in params if params else None
        options.append(
            LLMModelOption(
                id=str(model_id),
                label=str(model.get("name") or model_id),
                context_length=model.get("context_length"),
                supports_tools=supports_tools,
                pricing=_format_pricing(model.get("pricing")),
            )
        )

    options.sort(key=lambda opt: (opt.supports_tools is not True, opt.label.lower()))
    return options
