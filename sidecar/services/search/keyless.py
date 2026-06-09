"""The T1 keyless search tier — multi-engine rotation (R7 Component 1).

ONE :class:`SearchBackend` that fans a query across the keyless scrape engines
— DuckDuckGo (primary; its own token-bucket + Lite fallback stay intact),
Brave HTML, Mojeek HTML — with the hardening the single-engine floor lacked:

  * **Provider-chain rotation**: primary → fallbacks, in order. An engine
    whose circuit breaker is OPEN is SKIPPED without a network round-trip.
  * **Per-engine circuit breakers** (:mod:`services.search.breaker`): two
    consecutive failures bench an engine for the cooldown; a half-open probe
    re-admits it.
  * **Pacing + bounded retry** (:mod:`services.search.pacing`): every hit
    waits for the engine's process-global min-interval slot; a retryable
    failure gets exponential backoff + jitter for at most
    ``ATTEMPTS_PER_ENGINE`` tries, then the chain rotates.
  * **URL dedup per run**: a result URL already returned by an earlier engine
    in THIS search is dropped.
  * **Quality filter**: results whose visible text is consent/cookie/block
    boilerplate are dropped (markers list adapted from odysseus (MIT)
    github.com/pewdiepie-archdaemon/odysseus).
  * **Honest cross-engine errors**: when every engine fails, the raised
    :class:`SearchError` names each engine's actual state ("brave: cooling
    down (24s)") and carries ``reason="rate_limited"`` if ANY engine was
    throttling — never a fake global "no backend".

The per-engine truth is exported via :func:`tier_status` so the UI can render
"DuckDuckGo cooling down (24s)" instead of a fake outage banner.
"""

from __future__ import annotations

import asyncio

from .base import (
    SEARCH_REASON_RATE_LIMITED,
    SEARCH_REASON_UNREACHABLE,
    SearchBackend,
    SearchError,
    SearchResponse,
    SearchResult,
    normalize_results_to_citations,
)
from .breaker import breaker_for
from .pacing import ATTEMPTS_PER_ENGINE, backoff_delay, get_queue, min_interval_for

#: Identifier this tier reports (suffixed with the engine that actually served:
#: ``keyless:ddg`` / ``keyless:brave`` / ``keyless:mojeek``).
BACKEND_ID = "keyless"

#: Rotation order. DDG first (richest snippets, proven parser), Brave second
#: (big index behind the impersonation lane), Mojeek last (independent index —
#: the engine most likely UP when the other two throttle in lockstep).
ENGINE_CHAIN: tuple[str, ...] = ("ddg", "brave", "mojeek")

#: Human labels for the status surface.
ENGINE_LABELS: dict[str, str] = {
    "ddg": "DuckDuckGo",
    "brave": "Brave",
    "mojeek": "Mojeek",
}

#: Low-quality text markers — a result whose title+snippet is dominated by
#: consent/cookie/block boilerplate carries no information for the researcher.
#: Phrases (not bare "cookie") so a legitimate article ABOUT cookies survives.
#: Adapted from odysseus (MIT) github.com/pewdiepie-archdaemon/odysseus.
LOW_QUALITY_MARKERS: tuple[str, ...] = (
    "cookie consent",
    "cookie banner",
    "cookie notice",
    "consent to the use of cookies",
    "we use cookies",
    "accept all cookies",
    "manage your preferences",
    "enable javascript",
    "javascript is disabled",
    "access denied",
    "verify you are a human",
    "are you a robot",
    "unusual traffic",
    "all rights reserved",
)


def is_low_quality(text: str) -> bool:
    """True when ``text`` reads as consent/block boilerplate, not content."""
    if not text or not text.strip():
        return False  # an empty snippet is thin, not boilerplate — keep it
    low = text.lower()
    return any(marker in low for marker in LOW_QUALITY_MARKERS)


def _filter_results(results: list[SearchResult], seen_urls: set[str]) -> list[SearchResult]:
    """Apply the per-run URL dedup + the low-quality boilerplate filter."""
    out: list[SearchResult] = []
    for result in results:
        if result.url in seen_urls:
            continue
        if is_low_quality(f"{result.title} {result.snippet}"):
            continue
        seen_urls.add(result.url)
        out.append(result)
    return out


def _build_engines(region: str | None) -> dict[str, SearchBackend]:
    """Construct the default engine adapters (lazy imports — a half-built
    module costs that one engine, never the whole tier)."""
    engines: dict[str, SearchBackend] = {}
    try:
        from .ddg import DdgSearchBackend

        engines["ddg"] = DdgSearchBackend(region=region)
    except ImportError:
        pass
    try:
        from .brave import BraveSearchBackend

        engines["brave"] = BraveSearchBackend(region=region)
    except ImportError:
        pass
    try:
        from .mojeek import MojeekSearchBackend

        engines["mojeek"] = MojeekSearchBackend(region=region)
    except ImportError:
        pass
    return engines


class KeylessSearchBackend(SearchBackend):
    """The rebuilt T1 keyless tier: DDG → Brave → Mojeek rotation."""

    def __init__(
        self,
        *,
        region: str | None = None,
        engines: dict[str, SearchBackend] | None = None,
        sleeper=None,  # noqa: ANN001 — injectable backoff sleep for tests
    ) -> None:
        self.region = region
        self._engines = engines if engines is not None else _build_engines(region)
        self._sleep = sleeper or asyncio.sleep

    async def search(self, query: str, *, options: dict | None = None) -> SearchResponse:
        seen_urls: set[str] = set()
        engine_notes: dict[str, str] = {}
        any_rate_limited = False
        any_engine_answered = False

        for engine_id in ENGINE_CHAIN:
            engine = self._engines.get(engine_id)
            if engine is None:
                engine_notes[engine_id] = "unavailable"
                continue

            breaker = breaker_for(engine_id)
            if not breaker.allow():
                engine_notes[engine_id] = f"cooling down ({breaker.cooldown_remaining():.0f}s)"
                continue

            outcome = await self._try_engine(engine_id, engine, breaker, query, options)
            if isinstance(outcome, SearchResponse):
                breaker.record_success()
                any_engine_answered = True
                results = _filter_results(outcome.results, seen_urls)
                if results:
                    return SearchResponse(
                        results=results,
                        citations=normalize_results_to_citations(results, limit=len(results)),
                        backend=f"{BACKEND_ID}:{engine_id}",
                        query=query,
                    )
                # Transport + parse worked, just nothing useful — the engine is
                # HEALTHY; rotate to cross-check before declaring "found nothing".
                engine_notes[engine_id] = "no results"
                continue

            # SearchError (already counted against the breaker per attempt) —
            # note the typed reason and rotate.
            if outcome.reason == SEARCH_REASON_RATE_LIMITED:
                any_rate_limited = True
                engine_notes[engine_id] = "rate-limiting"
            else:
                engine_notes[engine_id] = "unreachable"

        if any_engine_answered:
            # At least one engine genuinely searched and found nothing — an
            # empty result set is a valid answer, not an outage.
            return SearchResponse(results=[], citations=[], backend=BACKEND_ID, query=query)

        detail = "; ".join(
            f"{ENGINE_LABELS.get(eid, eid)}: {note}" for eid, note in engine_notes.items()
        )
        raise SearchError(
            "keyless web search has no engine available right now — "
            f"{detail or 'no engines built'}. Wait a moment and retry, or add an "
            "Exa key / local SearXNG for a dedicated route.",
            reason=SEARCH_REASON_RATE_LIMITED if any_rate_limited else SEARCH_REASON_UNREACHABLE,
        )

    async def _try_engine(
        self,
        engine_id: str,
        engine: SearchBackend,
        breaker,  # noqa: ANN001 — CircuitBreaker
        query: str,
        options: dict | None,
    ) -> SearchResponse | SearchError:
        """Run one engine with pacing + bounded backoff retry.

        Returns the response on success, or the LAST :class:`SearchError` after
        the retry budget — never raises (the caller folds the error into the
        rotation accounting). EVERY failed attempt is counted against the
        breaker, so two consecutive misses inside one search bench the engine
        (fail_threshold=2); a benched-mid-retry engine stops being hammered
        immediately (and a failed HALF_OPEN probe never gets a second attempt).
        """
        last_error = SearchError(f"{engine_id} produced no attempt")
        for attempt in range(ATTEMPTS_PER_ENGINE):
            await get_queue().acquire(engine_id)
            try:
                return await engine.search(query, options=options)
            except SearchError as exc:
                last_error = exc
            except Exception as exc:  # noqa: BLE001 — any engine crash is a soft miss
                last_error = SearchError(f"{engine_id} engine failed: {exc}")
            breaker.record_failure()
            if attempt + 1 < ATTEMPTS_PER_ENGINE:
                if breaker.state == "open":
                    break  # benched mid-retry — rotate instead of hammering
                await self._sleep(backoff_delay(attempt))
        return last_error


def tier_status() -> dict[str, object]:
    """The honest per-engine T1 status for the UI (GET /search/status).

    Per engine: breaker state, cooldown remaining, the human label, and the
    pacing interval — so the surface can say "DuckDuckGo cooling down (24s)"
    instead of a fake global outage.
    """
    engines: list[dict[str, object]] = []
    for engine_id in ENGINE_CHAIN:
        breaker = breaker_for(engine_id)
        state = breaker.state
        remaining = breaker.cooldown_remaining()
        label = ENGINE_LABELS.get(engine_id, engine_id)
        if state == "open":
            detail = f"{label} cooling down ({remaining:.0f}s)"
        elif state == "half_open":
            detail = f"{label} probing after cooldown"
        else:
            detail = f"{label} available"
        engines.append(
            {
                "id": engine_id,
                "label": label,
                "state": state,
                "cooldown_remaining_s": round(remaining, 1),
                "min_interval_s": min_interval_for(engine_id),
                "detail": detail,
            }
        )
    return {
        "tier": "t1_keyless",
        "available": any(e["state"] != "open" for e in engines),
        "engines": engines,
    }


__all__ = [
    "BACKEND_ID",
    "ENGINE_CHAIN",
    "ENGINE_LABELS",
    "LOW_QUALITY_MARKERS",
    "KeylessSearchBackend",
    "is_low_quality",
    "tier_status",
]
