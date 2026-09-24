"""The T1 keyless search tier — multi-engine rotation (R7 Component 1).

ONE :class:`SearchBackend` that fans a query across the keyless scrape engines
— DuckDuckGo (primary; its own token-bucket + Lite fallback stay intact),
Brave HTML, Mojeek HTML — with the hardening the single-engine floor lacked:

  * **Provider-chain rotation**: primary → fallbacks, in order. An engine
    whose circuit breaker is OPEN is SKIPPED without a network round-trip.
  * **Per-engine circuit breakers** (:mod:`services.search.breaker`): two
    consecutive failed searches bench an engine for the cooldown; a half-open probe
    re-admits it.
  * **Pacing + bounded retry** (:mod:`services.search.pacing`): every hit
    waits for the engine's process-global min-interval slot; a fast failure
    gets exponential backoff + jitter for at most ``ATTEMPTS_PER_ENGINE``
    tries, then the chain rotates.
  * **Per-engine deadline**: everything one engine costs a search (pacing
    wait, attempts, backoff, its own fallbacks) runs under
    :data:`ENGINE_DEADLINE_SECS`; an engine that does not answer in time is
    abandoned with no second attempt and the chain rotates, so rotation
    reaches all three engines inside the 25 s ``web_search`` tool cap.
  * **URL dedup per run**: a result URL already returned by an earlier engine
    in THIS search is dropped.
  * **Block-page filter**: results whose visible text is an anti-bot
    interstitial are dropped, and an engine that answers ONLY with those is
    counted as a failure (a block), never as "found nothing". Consent/footer
    boilerplate is filtered per page paragraph in :mod:`.extract`, not here
    (markers list adapted from odysseus (MIT)
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

#: Wall budget for ONE engine inside one search. Three engines x 6 s = 18 s,
#: inside the 25 s ``web_search`` tool cap, so a hanging engine (DuckDuckGo
#: measured ~20 s per failing attempt, R15-RESEARCH-008) can never keep a
#: healthy later engine (Brave answered in 0.9 s) from being tried.
ENGINE_DEADLINE_SECS = 6.0

#: Human labels for the status surface.
ENGINE_LABELS: dict[str, str] = {
    "ddg": "DuckDuckGo",
    "brave": "Brave",
    "mojeek": "Mojeek",
}

#: Interstitial markers — the text of an anti-bot challenge / block page. On a
#: SERP result they are the block-page signal (the engine answered 200 but served
#: a wall, not results), so they act at RESULT level and count as a failure.
INTERSTITIAL_MARKERS: tuple[str, ...] = (
    "access denied",
    "verify you are a human",
    "are you a robot",
    "unusual traffic",
)

#: Low-quality text markers — consent/cookie/footer boilerplate plus the
#: interstitials. Applied per PARAGRAPH of an extracted page only: a SERP
#: snippet carrying a footer ("All rights reserved") is still a real result.
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
    "all rights reserved",
    *INTERSTITIAL_MARKERS,
)


def _has_marker(text: str, markers: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(marker in low for marker in markers)


def is_low_quality(text: str) -> bool:
    """True when a page paragraph reads as consent/block boilerplate, not content."""
    if not text or not text.strip():
        return False  # an empty snippet is thin, not boilerplate — keep it
    return _has_marker(text, LOW_QUALITY_MARKERS)


def _filter_results(
    results: list[SearchResult], seen_urls: set[str]
) -> tuple[list[SearchResult], int]:
    """Apply the per-run URL dedup + the interstitial (block-page) filter.

    Returns ``(kept, blocked)`` where ``blocked`` counts rows dropped as a
    challenge page — the caller treats an all-blocked answer as a failure.
    """
    out: list[SearchResult] = []
    blocked = 0
    for result in results:
        if result.url in seen_urls:
            continue
        if _has_marker(f"{result.title} {result.snippet}", INTERSTITIAL_MARKERS):
            blocked += 1
            continue
        seen_urls.add(result.url)
        out.append(result)
    return out, blocked


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
                results, blocked = _filter_results(outcome.results, seen_urls)
                if blocked and not results:
                    # A 200 challenge page is a block, not an answer: count it
                    # against the breaker and never report it as "found nothing".
                    breaker.record_failure()
                    any_rate_limited = True
                    engine_notes[engine_id] = "blocked (challenge page)"
                    continue
                breaker.record_success()
                any_engine_answered = True
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

            # SearchError (already counted against the breaker, once) — note
            # the typed reason and rotate.
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
        """Run one engine with pacing + bounded backoff retry, under a deadline.

        Returns the response on success, or the LAST :class:`SearchError` after
        the retry budget — never raises (the caller folds the error into the
        rotation accounting). A failed engine turn counts ONE failure against
        the breaker however many attempts it spent, so the breaker benches an
        engine after ``fail_threshold`` bad SEARCHES, not one search's retries;
        a failed HALF_OPEN probe gets no second attempt. The whole engine turn
        runs under :data:`ENGINE_DEADLINE_SECS`: an engine still silent at the
        deadline is abandoned (no second attempt) and the chain rotates.
        """
        last_error = SearchError(f"{engine_id} produced no attempt")
        try:
            async with asyncio.timeout(ENGINE_DEADLINE_SECS):
                for attempt in range(ATTEMPTS_PER_ENGINE):
                    await get_queue().acquire(engine_id)
                    try:
                        return await engine.search(query, options=options)
                    except SearchError as exc:
                        last_error = exc
                    except Exception as exc:  # noqa: BLE001 — any engine crash is a soft miss
                        last_error = SearchError(f"{engine_id} engine failed: {exc}")
                    if attempt + 1 < ATTEMPTS_PER_ENGINE:
                        if breaker.state != "closed":
                            break  # a failed probe, or benched meanwhile — rotate
                        await self._sleep(backoff_delay(attempt))
        except TimeoutError:
            last_error = SearchError(
                f"{engine_id} did not answer within {ENGINE_DEADLINE_SECS:g}s",
                reason=SEARCH_REASON_UNREACHABLE,
            )
        breaker.record_failure()
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
    "ENGINE_DEADLINE_SECS",
    "ENGINE_LABELS",
    "INTERSTITIAL_MARKERS",
    "LOW_QUALITY_MARKERS",
    "KeylessSearchBackend",
    "is_low_quality",
    "tier_status",
]
