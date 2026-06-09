"""Tests for the T1 keyless multi-engine rotation (``services.search.keyless``)."""

from __future__ import annotations

import asyncio

import pytest

from services.search.base import (
    SEARCH_REASON_RATE_LIMITED,
    SEARCH_REASON_UNREACHABLE,
    Citation,
    SearchError,
    SearchResponse,
    SearchResult,
)
from services.search.breaker import breaker_for, reset_breakers
from services.search.keyless import (
    BACKEND_ID,
    ENGINE_CHAIN,
    KeylessSearchBackend,
    is_low_quality,
    tier_status,
)
from services.search.pacing import reset_queue


@pytest.fixture(autouse=True)
def _isolate_globals():
    """Each test gets fresh process-global breakers + queue."""
    reset_breakers()
    reset_queue()
    yield
    reset_breakers()
    reset_queue()


def _result(url: str, *, title: str = "T", snippet: str = "S") -> SearchResult:
    return SearchResult(url=url, title=title, snippet=snippet)


def _response(engine: str, results: list[SearchResult]) -> SearchResponse:
    return SearchResponse(
        results=results,
        citations=[Citation(url=r.url, title=r.title, excerpt=r.snippet) for r in results],
        backend=engine,
        query="q",
    )


class _Engine:
    """A scripted fake engine: each search() pops the next outcome."""

    def __init__(self, outcomes: list) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    async def search(self, query, *, options=None):  # noqa: ANN001, ANN201
        self.calls += 1
        outcome = self.outcomes.pop(0) if self.outcomes else SearchError("exhausted")
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


async def _no_sleep(_secs: float) -> None:
    return None


def _backend(engines: dict) -> KeylessSearchBackend:
    return KeylessSearchBackend(engines=engines, sleeper=_no_sleep)


def _run(coro):
    return asyncio.run(coro)


# --- happy path + rotation ----------------------------------------------------


def test_primary_engine_serves_and_backend_names_it() -> None:
    ddg = _Engine([_response("ddg", [_result("https://a.com/1")])])
    backend = _backend({"ddg": ddg, "brave": _Engine([]), "mojeek": _Engine([])})
    resp = _run(backend.search("q"))
    assert resp.backend == "keyless:ddg"
    assert [r.url for r in resp.results] == ["https://a.com/1"]
    assert resp.citations[0].url == "https://a.com/1"


def test_rotation_skips_failed_primary_to_fallback() -> None:
    ddg = _Engine([SearchError("down"), SearchError("down")])  # both attempts fail
    brave = _Engine([_response("brave", [_result("https://b.com/1")])])
    backend = _backend({"ddg": ddg, "brave": brave, "mojeek": _Engine([])})
    resp = _run(backend.search("q"))
    assert resp.backend == "keyless:brave"
    assert ddg.calls == 2  # the bounded per-engine retry budget was spent
    assert brave.calls == 1


def test_retry_then_success_within_same_engine() -> None:
    ddg = _Engine([SearchError("blip"), _response("ddg", [_result("https://a.com/1")])])
    backend = _backend({"ddg": ddg, "brave": _Engine([]), "mojeek": _Engine([])})
    resp = _run(backend.search("q"))
    assert resp.backend == "keyless:ddg"
    assert ddg.calls == 2


def test_empty_engine_rotates_to_cross_check_then_returns_empty_success() -> None:
    ddg = _Engine([_response("ddg", [])])
    brave = _Engine([_response("brave", [])])
    mojeek = _Engine([_response("mojeek", [])])
    backend = _backend({"ddg": ddg, "brave": brave, "mojeek": mojeek})
    resp = _run(backend.search("q"))
    # All engines genuinely found nothing → an empty SUCCESS, not an error.
    assert resp.backend == BACKEND_ID
    assert resp.results == []
    assert ddg.calls == 1 and brave.calls == 1 and mojeek.calls == 1


def test_empty_primary_but_fallback_results_serve() -> None:
    ddg = _Engine([_response("ddg", [])])
    brave = _Engine([_response("brave", [_result("https://b.com/1")])])
    backend = _backend({"ddg": ddg, "brave": brave, "mojeek": _Engine([])})
    resp = _run(backend.search("q"))
    assert resp.backend == "keyless:brave"


# --- breaker integration --------------------------------------------------------


def test_two_failures_trip_breaker_and_next_run_skips_engine() -> None:
    ddg = _Engine([SearchError("down"), SearchError("down")])
    brave = _Engine(
        [
            _response("brave", [_result("https://b.com/1")]),
            _response("brave", [_result("https://b.com/2")]),
        ]
    )
    backend = _backend({"ddg": ddg, "brave": brave, "mojeek": _Engine([])})

    _run(backend.search("q1"))  # spends ddg's 2 attempts → breaker OPEN
    assert breaker_for("ddg").state == "open"

    _run(backend.search("q2"))  # OPEN breaker → ddg skipped without a call
    assert ddg.calls == 2  # unchanged — no third network attempt


def test_open_breaker_engine_is_skipped_without_network_call() -> None:
    breaker_for("ddg").record_failure()
    breaker_for("ddg").record_failure()
    ddg = _Engine([_response("ddg", [_result("https://a.com/1")])])
    brave = _Engine([_response("brave", [_result("https://b.com/1")])])
    backend = _backend({"ddg": ddg, "brave": brave, "mojeek": _Engine([])})
    resp = _run(backend.search("q"))
    assert ddg.calls == 0
    assert resp.backend == "keyless:brave"


def test_success_closes_breaker() -> None:
    breaker_for("ddg").record_failure()  # one strike, still closed
    ddg = _Engine([_response("ddg", [_result("https://a.com/1")])])
    backend = _backend({"ddg": ddg, "brave": _Engine([]), "mojeek": _Engine([])})
    _run(backend.search("q"))
    assert breaker_for("ddg").state == "closed"


# --- all-engines-down honesty ---------------------------------------------------


def test_all_engines_rate_limited_raises_typed_rate_limit_with_detail() -> None:
    throttle = SearchError("throttled", reason=SEARCH_REASON_RATE_LIMITED)
    engines = {
        eid: _Engine([throttle, throttle])  # 2 attempts each
        for eid in ENGINE_CHAIN
    }
    backend = _backend(engines)
    with pytest.raises(SearchError) as err:
        _run(backend.search("q"))
    assert err.value.reason == SEARCH_REASON_RATE_LIMITED
    msg = str(err.value)
    assert "DuckDuckGo" in msg and "Brave" in msg and "Mojeek" in msg
    assert "rate-limiting" in msg


def test_all_engines_unreachable_raises_unreachable() -> None:
    down = SearchError("down")
    engines = {eid: _Engine([down, down]) for eid in ENGINE_CHAIN}
    backend = _backend(engines)
    with pytest.raises(SearchError) as err:
        _run(backend.search("q"))
    assert err.value.reason == SEARCH_REASON_UNREACHABLE


def test_benched_engines_named_with_cooldown_in_error() -> None:
    for eid in ENGINE_CHAIN:
        breaker_for(eid).record_failure()
        breaker_for(eid).record_failure()
    backend = _backend({eid: _Engine([]) for eid in ENGINE_CHAIN})
    with pytest.raises(SearchError) as err:
        _run(backend.search("q"))
    assert "cooling down" in str(err.value)


# --- dedup + quality filter -----------------------------------------------------


def test_urls_deduped_within_a_run() -> None:
    ddg = _Engine(
        [
            _response(
                "ddg",
                [
                    _result("https://a.com/1"),
                    _result("https://a.com/1", title="dupe"),
                    _result("https://a.com/2"),
                ],
            )
        ]
    )
    backend = _backend({"ddg": ddg, "brave": _Engine([]), "mojeek": _Engine([])})
    resp = _run(backend.search("q"))
    assert [r.url for r in resp.results] == ["https://a.com/1", "https://a.com/2"]


def test_low_quality_boilerplate_filtered_out() -> None:
    ddg = _Engine(
        [
            _response(
                "ddg",
                [
                    _result("https://a.com/cookie", snippet="We use cookies — accept all cookies"),
                    _result("https://a.com/real", snippet="NVDA datacenter revenue grew 94%"),
                ],
            )
        ]
    )
    backend = _backend({"ddg": ddg, "brave": _Engine([]), "mojeek": _Engine([])})
    resp = _run(backend.search("q"))
    assert [r.url for r in resp.results] == ["https://a.com/real"]


def test_is_low_quality_markers() -> None:
    assert is_low_quality("Please enable JavaScript to continue") is True
    assert is_low_quality("Verify you are a human to proceed") is True
    assert is_low_quality("NVIDIA reports record Q4 results") is False
    assert is_low_quality("") is False  # thin, not boilerplate


def test_all_results_filtered_rotates_onward() -> None:
    ddg = _Engine(
        [_response("ddg", [_result("https://a.com/x", snippet="cookie banner only page")])]
    )
    brave = _Engine([_response("brave", [_result("https://b.com/1")])])
    backend = _backend({"ddg": ddg, "brave": brave, "mojeek": _Engine([])})
    resp = _run(backend.search("q"))
    assert resp.backend == "keyless:brave"


# --- tier status surface ---------------------------------------------------------


def test_tier_status_reports_every_engine_closed_by_default() -> None:
    status = tier_status()
    assert status["tier"] == "t1_keyless"
    assert status["available"] is True
    assert [e["id"] for e in status["engines"]] == list(ENGINE_CHAIN)
    for engine in status["engines"]:
        assert engine["state"] == "closed"
        assert engine["cooldown_remaining_s"] == 0.0
        assert "available" in engine["detail"]


def test_tier_status_names_a_cooling_engine_honestly() -> None:
    breaker_for("ddg").record_failure()
    breaker_for("ddg").record_failure()
    status = tier_status()
    ddg_row = next(e for e in status["engines"] if e["id"] == "ddg")
    assert ddg_row["state"] == "open"
    assert ddg_row["cooldown_remaining_s"] > 0
    assert "DuckDuckGo cooling down (" in ddg_row["detail"]
    # One benched engine is NOT a global outage — the tier stays available.
    assert status["available"] is True


def test_tier_status_unavailable_only_when_every_engine_open() -> None:
    for eid in ENGINE_CHAIN:
        breaker_for(eid).record_failure()
        breaker_for(eid).record_failure()
    assert tier_status()["available"] is False
