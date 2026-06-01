"""Perplexity Sonar deep-research BYOK backend (FR-073 — the opt-in DEEP engine).

Perplexity's ``sonar-deep-research`` model runs a multi-step, web-grounded
research pass and returns a synthesised markdown brief plus a flat list of
citation urls. Vysted exposes it as an **optional, opt-in-per-run** DEEP
research backend: it is **never auto-selected**, it shows an estimated cost
before running, and its citations carry the provenance label "via Perplexity
Sonar" (FR-073, spec §1324).

This backend ships **present but unconfigured**: the user's Perplexity key lives
in the OS keychain and rides the request from the renderer; it is handed to
:class:`PerplexityDeepBackend` at construction (``PerplexityDeepBackend(api_key=
...)``) and used only as the ``Authorization: Bearer`` header on the outbound
Perplexity request. The key is **never** read from the environment or disk,
**never** logged, and **never** echoed back in a response or error message. When
no key is present the backend is *not configured* (:func:`is_configured` returns
``False``) — the handler renders a "needs a key" state and the path stays inert.

Selection guard (the module-level invariant): nothing here auto-selects this
backend. It is only reachable when the caller explicitly asks for
``backend == "perplexity"`` **and** :func:`is_configured` is ``True`` — the
research handler enforces that gate; this module supplies the gate
(:func:`is_configured`), the pre-run cost estimate (:func:`estimate_cost_usd`),
and the backend itself.

The response maps onto the shared research contract
(:class:`services.research.models.ResearchBrief` /
:class:`~services.research.models.ResearchSource`): ``choices[0].message.content``
becomes the brief ``markdown``; each top-level ``citations[]`` url (with
``search_results[]`` as a fallback) becomes a :class:`ResearchSource` tagged
``"via Perplexity Sonar"``. Any upstream failure (missing key, HTTP error,
malformed body) surfaces as a human-readable
:class:`~services.search.base.SearchError` — never a raw vendor JSON blob, never
the key. No test makes a live call — see ``tests/test_perplexity_backend.py``
(httpx is mocked).
"""

from __future__ import annotations

from typing import Any

import httpx

from services.research.models import ResearchBrief, ResearchSource
from services.search.base import SearchError

#: Perplexity's OpenAI-compatible chat-completions endpoint.
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"

#: The deep-research model id (FR-073).
PERPLEXITY_DEEP_MODEL = "sonar-deep-research"

#: Provenance label stamped on every brief/source this backend produces (FR-073).
PROVENANCE_NOTE = "via Perplexity Sonar"

#: ``ResearchBrief.mode`` value for a DEEP run (lowercase per ``RESEARCH_MODES``).
DEEP_MODE = "deep"

#: Deep research is a long, multi-step pass — give it a generous ceiling.
_HTTP_TIMEOUT = httpx.Timeout(180.0, connect=10.0)

# --- Pre-run cost estimate (FR-073: cost shown before running) --------------
#
# sonar-deep-research bills per request plus per token across its multi-step
# search/reason/synthesise pass. A single deep run lands roughly in the
# $0.20–0.40 band; we surface a flat mid-band ESTIMATE so the user sees a number
# before opting in. This is intentionally a coarse heuristic, NOT a billed
# figure — the real charge comes from Perplexity. A small per-character nudge
# lets a longer brief read slightly pricier without overstating it.
_ESTIMATE_BASE_USD = 0.25
_ESTIMATE_PER_CHAR_USD = 0.00015
_ESTIMATE_CEILING_USD = 0.40


def is_configured(api_key: str | None) -> bool:
    """Return ``True`` only when a non-empty Perplexity key is present.

    This is the configuration gate: the DEEP backend is *present but
    unconfigured* until a key arrives (FR-073). The handler calls this before
    ever constructing the backend — a falsy/blank key keeps the path inert and
    the UI shows a "needs a key" state. Never auto-selected regardless.
    """
    return bool(api_key and api_key.strip())


def estimate_cost_usd(query: str) -> float:
    """Estimate the USD cost of one ``sonar-deep-research`` run for ``query``.

    Returns a coarse, positive per-run figure in the documented ~$0.20–0.40
    band (FR-073), shown to the user **before** they opt in. This is an
    ESTIMATE, not a billed amount — the authoritative charge is Perplexity's.
    The estimate scales mildly with query length and is clamped to the band
    ceiling so it never overstates.
    """
    length = len((query or "").strip())
    estimate = _ESTIMATE_BASE_USD + (length * _ESTIMATE_PER_CHAR_USD)
    return round(min(estimate, _ESTIMATE_CEILING_USD), 4)


def _human_http_error(exc: httpx.HTTPStatusError) -> str:
    """Translate a Perplexity HTTP error into a clean, key-free human message."""
    status = exc.response.status_code
    if status in (401, 403):
        return (
            "Perplexity rejected the request — check that your Perplexity API "
            "key is valid and active."
        )
    if status == 429:
        return "Perplexity rate limit reached — slow down or check your plan's quota."
    if status == 400:
        return "Perplexity could not process the research request (bad query or parameters)."
    if status >= 500:
        return "Perplexity is temporarily unavailable (server error) — try again shortly."
    return f"Perplexity deep research failed with HTTP {status}."


def _extract_markdown(body: dict[str, Any]) -> str:
    """Pull the synthesised brief markdown from ``choices[0].message.content``.

    Returns an empty string if the shape is missing — the caller decides whether
    that is an error; mapping never raises on a thin body.
    """
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
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
    """Map ``citations[]`` (preferred) + ``search_results[]`` to ``ResearchSource``.

    Perplexity returns a top-level ``citations`` list of url strings; some
    responses additionally carry ``search_results`` (objects with ``url`` and
    often a ``title``/``snippet``). Both are merged, de-duplicated by url, and
    order-preserved so no source is dropped and none is listed twice. Every
    source carries the ``"via Perplexity Sonar"`` provenance in its ``domain``
    label alongside the host (FR-073).
    """
    sources: list[ResearchSource] = []
    seen: set[str] = set()

    # search_results, keyed by url, supply a richer title/excerpt when present.
    meta: dict[str, dict[str, Any]] = {}
    search_results = body.get("search_results")
    if isinstance(search_results, list):
        for entry in search_results:
            if isinstance(entry, dict):
                url = entry.get("url")
                if isinstance(url, str) and url.strip():
                    meta.setdefault(url.strip(), entry)

    def _add(url: str) -> None:
        url = url.strip()
        if not url or url in seen:
            return
        seen.add(url)
        info = meta.get(url, {})
        title = info.get("title") if isinstance(info.get("title"), str) else None
        excerpt = info.get("snippet") if isinstance(info.get("snippet"), str) else None
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

    citations = body.get("citations")
    if isinstance(citations, list):
        for entry in citations:
            if isinstance(entry, str):
                _add(entry)

    # Any search_results url not already cited is still a gathered source.
    for url in meta:
        _add(url)

    return sources


def _cost_snapshot(query: str) -> dict[str, Any]:
    """The brief's ``cost`` dict — an ESTIMATE, flagged as such (FR-073).

    Mirrors :meth:`BudgetGuard.cost`'s ``{tokens, spend_usd, steps}`` shape so a
    consumer reads it uniformly, plus ``estimate: True`` and the ``provider``
    label so the cockpit shows "~$0.xx (estimate, via Perplexity Sonar)" rather
    than presenting it as a billed charge. Token/step counts are unknown for a
    vendor deep run (Perplexity meters internally), so they are ``None``.
    """
    return {
        "tokens": None,
        "spend_usd": estimate_cost_usd(query),
        "steps": None,
        "estimate": True,
        "provider": PROVENANCE_NOTE,
    }


class PerplexityDeepBackend:
    """Perplexity ``sonar-deep-research`` DEEP backend (FR-073).

    ``api_key`` is the BYOK Perplexity key (keychain-sourced; used only as the
    ``Authorization: Bearer`` header). ``client`` is an optional shared pooled
    ``httpx.AsyncClient``; when omitted a short-lived client is opened per call.

    The key is validated lazily — construction succeeds even with a blank key so
    the handler can construct-then-explain; :meth:`research` raises a human
    :class:`~services.search.base.SearchError` if the key is missing at call
    time. This backend is **never auto-selected**: the handler reaches it only
    after an explicit ``backend == "perplexity"`` request gated on
    :func:`is_configured`.
    """

    name = "perplexity"

    def __init__(self, api_key: str | None, *, client: httpx.AsyncClient | None = None) -> None:
        self._api_key = (api_key or "").strip()
        self._client = client

    async def research(self, query: str, *, region: str | None = None) -> ResearchBrief:
        """Run a deep-research pass for ``query`` and map it to a ``ResearchBrief``.

        ``region`` is accepted for interface parity with the native research path
        (Perplexity does region selection internally; it is not forwarded as a
        vendor parameter). Raises :class:`~services.search.base.SearchError` —
        human message, never raw vendor JSON, never the key — when the key is
        missing or the upstream call fails.
        """
        if not self._api_key:
            raise SearchError(
                "Perplexity needs an API key to run deep research — add one to opt in."
            )

        text = (query or "").strip()
        if not text:
            raise SearchError("Research query is empty.")

        payload: dict[str, Any] = {
            "model": PERPLEXITY_DEEP_MODEL,
            "messages": [{"role": "user", "content": text}],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            if self._client is not None:
                response = await self._client.post(
                    PERPLEXITY_URL, json=payload, headers=headers, timeout=_HTTP_TIMEOUT
                )
            else:
                async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                    response = await client.post(PERPLEXITY_URL, json=payload, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise SearchError(_human_http_error(exc)) from exc
        except httpx.HTTPError as exc:
            raise SearchError(
                "Could not reach Perplexity — check your network connection."
            ) from exc

        try:
            body: dict[str, Any] = response.json()
        except ValueError as exc:
            raise SearchError("Perplexity returned a response that could not be parsed.") from exc

        markdown = _extract_markdown(body)
        if not markdown:
            raise SearchError("Perplexity returned an empty research brief.")

        sources = _extract_sources(body)

        return ResearchBrief(
            query=text,
            symbol="",
            mode=DEEP_MODE,
            markdown=markdown,
            sources=sources,
            source_count=len(sources),
            cost=_cost_snapshot(text),
            web_available=True,
            note=None,
        )


__all__ = [
    "DEEP_MODE",
    "PERPLEXITY_DEEP_MODEL",
    "PERPLEXITY_URL",
    "PROVENANCE_NOTE",
    "PerplexityDeepBackend",
    "estimate_cost_usd",
    "is_configured",
]
