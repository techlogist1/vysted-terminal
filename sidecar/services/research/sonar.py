"""Sonar one-call research lane via OpenRouter (R7 Track R — Component 3).

The t3 hosted tier's ONE-CALL research-model lane: Perplexity's sonar family —
``perplexity/sonar-deep-research`` and siblings — routed through OpenRouter on
the user's OpenRouter BYOK key, so a user with a single OpenRouter key gets a
hosted deep-research engine without also holding a Perplexity key. Slug + routing
confirmed live 2026-06-10 (pass-through pricing: $2/M input, $8/M output,
$5/1000 searches for sonar-deep-research).

This mirrors :mod:`services.research.perplexity` (the DIRECT Perplexity lane)
on the same contract — opt-in-per-run, never auto-selected, estimated cost
shown before/with the run, provenance-labelled sources — but maps citations
through the existing :func:`services.llm.native_search.normalize_openai` path:
OpenRouter returns Perplexity citations as OpenAI-style ``url_citation``
annotations on the assistant message (with a top-level ``citations[]`` url list
passed through on most responses as a fallback), so briefs render sources with
the SAME normalizer every other OpenAI-shaped backend uses.

Note on Tongyi-DeepResearch: ``alibaba/tongyi-deepresearch-30b-a3b`` is
confirmed DELISTED from OpenRouter (live check 2026-06-10) and is deliberately
NOT in :data:`SONAR_MODELS` or any picker. The only remaining sources for that
model are direct (Alibaba Bailian / WaveSpeed) — out of scope for the
OpenRouter lane.

BYOK hygiene (identical to the direct lane): the OpenRouter key rides the
request only (``Authorization: Bearer``), never read from the environment or
disk, never logged, never echoed in a response or error message. No test makes
a live call — see ``tests/test_sonar_lane.py`` (the HTTP client is stubbed).
"""

from __future__ import annotations

from typing import Any

import httpx

from services.llm.native_search import normalize_openai
from services.research.models import ResearchBrief, ResearchSource
from services.search.base import SearchError

#: OpenRouter's OpenAI-compatible chat-completions endpoint.
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

#: The default lane model — the deep multi-step researcher (slug confirmed
#: routable on OpenRouter, live check 2026-06-10).
SONAR_DEEP_MODEL = "perplexity/sonar-deep-research"

#: The routable sonar family (one-call research models with citations).
SONAR_MODELS: tuple[str, ...] = (
    "perplexity/sonar",
    "perplexity/sonar-pro",
    "perplexity/sonar-reasoning",
    "perplexity/sonar-reasoning-pro",
    SONAR_DEEP_MODEL,
)

#: Provenance label stamped on every brief/source this lane produces.
PROVENANCE_NOTE = "via Perplexity Sonar (OpenRouter)"

#: ``ResearchBrief.mode`` value — the lane is a DEEP one-call engine.
DEEP_MODE = "deep"

#: Deep research is a long, multi-step pass — same generous ceiling as the
#: direct Perplexity lane.
_HTTP_TIMEOUT = httpx.Timeout(180.0, connect=10.0)

# --- Pre-run cost estimate (cost shown before running — FR-073 parity) -------
#
# sonar-deep-research via OpenRouter is pass-through priced ($2/M in, $8/M out,
# $5/1000 searches; a deep run fires tens of searches plus reasoning tokens) —
# one run lands in the same ~$0.20-0.40 band as the direct lane, so the SAME
# coarse heuristic is surfaced: a flat mid-band estimate with a mild per-char
# nudge, clamped at the band ceiling. The lighter sonar models are a single
# search-grounded completion — centi-dollar territory.
_DEEP_BASE_USD = 0.25
_DEEP_PER_CHAR_USD = 0.00015
_DEEP_CEILING_USD = 0.40
_LIGHT_BASE_USD = 0.01
_LIGHT_PER_CHAR_USD = 0.00001
_LIGHT_CEILING_USD = 0.05


def is_configured(api_key: str | None) -> bool:
    """``True`` only when a non-empty OpenRouter key is present (the opt-in gate)."""
    return bool(api_key and api_key.strip())


def resolve_model(value: str | None) -> str:
    """Resolve a caller's model hint to a routable sonar-family slug.

    Accepts a full family slug or a short spelling (``"sonar-pro"``,
    ``"deep-research"``); anything unknown lands on the deep-research default
    rather than raising — a stale Settings value must never break a run. Tongyi
    is delisted from OpenRouter and deliberately unreachable here.
    """
    if not value:
        return SONAR_DEEP_MODEL
    candidate = value.strip().lower()
    if candidate in SONAR_MODELS:
        return candidate
    short = candidate.removeprefix("perplexity/")
    full = f"perplexity/{short}"
    if full in SONAR_MODELS:
        return full
    if short in ("deep-research", "deep", "sonar-deep"):
        return SONAR_DEEP_MODEL
    return SONAR_DEEP_MODEL


def estimate_cost_usd(query: str, model: str = SONAR_DEEP_MODEL) -> float:
    """Estimate the USD cost of one sonar run for ``query`` via OpenRouter.

    A coarse, positive per-run figure shown to the user BEFORE they opt in —
    an ESTIMATE, never a billed amount (the authoritative charge is
    OpenRouter's pass-through of Perplexity's metering). Deep-research runs
    land in the ~$0.20-0.40 band; the lighter sonar models in ~$0.01-0.05.
    """
    length = len((query or "").strip())
    if resolve_model(model) == SONAR_DEEP_MODEL:
        estimate = _DEEP_BASE_USD + (length * _DEEP_PER_CHAR_USD)
        return round(min(estimate, _DEEP_CEILING_USD), 4)
    estimate = _LIGHT_BASE_USD + (length * _LIGHT_PER_CHAR_USD)
    return round(min(estimate, _LIGHT_CEILING_USD), 4)


def _human_http_error(exc: httpx.HTTPStatusError) -> str:
    """Translate an OpenRouter HTTP error into a clean, key-free human message."""
    status = exc.response.status_code
    if status in (401, 403):
        return (
            "OpenRouter rejected the request — check that your OpenRouter API "
            "key is valid and active."
        )
    if status == 402:
        return (
            "OpenRouter reports insufficient credits for the Sonar run — top up "
            "your account to use the hosted research lane."
        )
    if status == 429:
        return "OpenRouter rate limit reached — slow down or check your plan's quota."
    if status == 400:
        return "OpenRouter could not process the research request (bad query or parameters)."
    if status >= 500:
        return "OpenRouter is temporarily unavailable (server error) — try again shortly."
    return f"OpenRouter Sonar research failed with HTTP {status}."


def _message_of(body: dict[str, Any]) -> dict[str, Any]:
    """The first choice's message dict, or ``{}`` — mapping never raises on a thin body."""
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return {}
    first = choices[0]
    if not isinstance(first, dict):
        return {}
    message = first.get("message")
    return message if isinstance(message, dict) else {}


def _extract_markdown(body: dict[str, Any]) -> str:
    """Pull the synthesised brief markdown from ``choices[0].message.content``."""
    content = _message_of(body).get("content")
    return content.strip() if isinstance(content, str) else ""


def _domain_of(url: str) -> str | None:
    """Best-effort host label for a citation url (display only, never required)."""
    try:
        host = httpx.URL(url).host
    except (httpx.InvalidURL, ValueError, TypeError):
        return None
    if not host:
        return None
    return host[4:] if host.startswith("www.") else host


def _extract_sources(body: dict[str, Any]) -> list[ResearchSource]:
    """Map message annotations (+ ``citations[]`` fallback) to ``ResearchSource``.

    The PRIMARY path is the existing OpenAI ``url_citation`` normalizer
    (:func:`normalize_openai`) over ``choices[0].message.annotations`` — the
    same citation path every OpenAI-shaped backend uses, so briefs render
    sources identically. OpenRouter additionally passes Perplexity's top-level
    ``citations[]`` url list through on most responses; any url the
    annotations missed is still a gathered source. Merged, de-duplicated by
    url, order-preserved; every source carries the OpenRouter-lane provenance
    in its ``domain`` label.
    """
    sources: list[ResearchSource] = []
    seen: set[str] = set()

    def _add(url: str, title: str = "", excerpt: str = "") -> None:
        url = (url or "").strip()
        if not url or url in seen:
            return
        seen.add(url)
        host = _domain_of(url)
        domain = f"{host} ({PROVENANCE_NOTE})" if host else PROVENANCE_NOTE
        sources.append(
            ResearchSource(
                url=url,
                title=(title or host or url).strip(),
                excerpt=(excerpt or "").strip(),
                domain=domain,
            )
        )

    # The existing normalize_openai citation path (url_citation annotations).
    for record in normalize_openai(_message_of(body).get("annotations")):
        _add(record.get("url", ""), record.get("title", ""), record.get("excerpt", ""))

    # Pass-through Perplexity ``citations[]`` (top-level OR message-level) —
    # plain url strings; anything the annotations already covered is skipped.
    for container in (body, _message_of(body)):
        citations = container.get("citations")
        if isinstance(citations, list):
            for entry in citations:
                if isinstance(entry, str):
                    _add(entry)

    return sources


def _cost_snapshot(query: str, model: str) -> dict[str, Any]:
    """The brief's ``cost`` dict — an ESTIMATE, flagged as such.

    Mirrors :meth:`BudgetGuard.cost`'s ``{tokens, spend_usd, steps}`` shape plus
    ``estimate: True`` and the provider label, so the cockpit shows
    "~$0.xx (estimate, via Perplexity Sonar (OpenRouter))" rather than a billed
    charge. Token/step counts are unknown for a vendor one-call run.
    """
    return {
        "tokens": None,
        "spend_usd": estimate_cost_usd(query, model),
        "steps": None,
        "estimate": True,
        "provider": PROVENANCE_NOTE,
    }


class OpenRouterSonarBackend:
    """Sonar-family one-call research backend riding the user's OpenRouter key.

    ``api_key`` is the BYOK OpenRouter key (keychain-sourced; used only as the
    ``Authorization: Bearer`` header). ``model`` is resolved through
    :func:`resolve_model` (deep-research default). ``client`` is an optional
    shared pooled ``httpx.AsyncClient``; absent one, a short-lived client is
    opened per call.

    Construction succeeds with a blank key so the handler can
    construct-then-explain; :meth:`research` raises a human
    :class:`~services.search.base.SearchError` if the key is missing at call
    time. NEVER auto-selected — only reachable on an explicit
    ``backend == "sonar"`` opt-in gated on :func:`is_configured`.
    """

    name = "sonar"

    def __init__(
        self,
        api_key: str | None,
        *,
        model: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = (api_key or "").strip()
        self._model = resolve_model(model)
        self._client = client

    async def research(self, query: str, *, region: str | None = None) -> ResearchBrief:
        """Run one sonar research pass and map it to a ``ResearchBrief``.

        ``region`` is accepted for interface parity with the native research
        path (Perplexity does region selection internally). Raises
        :class:`~services.search.base.SearchError` — human message, never raw
        vendor JSON, never the key — when the key is missing or the upstream
        call fails.
        """
        if not self._api_key:
            raise SearchError(
                "The hosted Sonar research lane needs an OpenRouter API key — add one to opt in."
            )

        text = (query or "").strip()
        if not text:
            raise SearchError("Research query is empty.")

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "user", "content": text}],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            if self._client is not None:
                response = await self._client.post(
                    OPENROUTER_CHAT_URL, json=payload, headers=headers, timeout=_HTTP_TIMEOUT
                )
            else:
                async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                    response = await client.post(OPENROUTER_CHAT_URL, json=payload, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise SearchError(_human_http_error(exc)) from exc
        except httpx.HTTPError as exc:
            raise SearchError(
                "Could not reach OpenRouter — check your network connection."
            ) from exc

        try:
            body: dict[str, Any] = response.json()
        except ValueError as exc:
            raise SearchError("OpenRouter returned a response that could not be parsed.") from exc

        markdown = _extract_markdown(body)
        if not markdown:
            raise SearchError("OpenRouter returned an empty research brief.")

        sources = _extract_sources(body)

        return ResearchBrief(
            query=text,
            symbol="",
            mode=DEEP_MODE,
            markdown=markdown,
            sources=sources,
            source_count=len(sources),
            cost=_cost_snapshot(text, self._model),
            web_available=True,
            note=None,
        )


__all__ = [
    "DEEP_MODE",
    "OPENROUTER_CHAT_URL",
    "PROVENANCE_NOTE",
    "SONAR_DEEP_MODEL",
    "SONAR_MODELS",
    "OpenRouterSonarBackend",
    "estimate_cost_usd",
    "is_configured",
    "resolve_model",
]
