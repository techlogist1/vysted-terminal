"""R15-LEAD-020 — negative-cache pin for :func:`exchange_financials.get_filed_periods`.

``get_filed_periods`` cached only a successful lookup; a transient NSE miss
fell back to Yahoo and the very next call for the same symbol served NSE
instead, because nothing remembered the failure. These tests pin the fix at
the boundary that matters: two calls a beat apart stay on one answer while
the negative-cache window holds, and a later call past it re-fetches.
"""

from __future__ import annotations

import asyncio
from datetime import date

import pytest

from services import exchange_financials
from services.exchange_financials import FiledPeriod, FiledPeriods

# conftest's ``_no_network_exchange_financials`` autouse fixture stubs
# ``get_filed_periods`` to a constant ``None`` for every module except
# ``test_b7_exchange_*`` — captured here at collection time (before that
# fixture runs) so these tests can restore the real function under test.
_REAL_GET_FILED_PERIODS = exchange_financials.get_filed_periods


@pytest.fixture(autouse=True)
def _fresh_lane(monkeypatch: pytest.MonkeyPatch) -> None:
    exchange_financials.reset_for_tests()
    monkeypatch.setattr(exchange_financials, "get_filed_periods", _REAL_GET_FILED_PERIODS)


def _periods() -> FiledPeriods:
    period = FiledPeriod(
        start=date(2026, 4, 1), end=date(2026, 6, 30), revenue=100.0, net_profit=10.0, eps=1.0
    )
    return FiledPeriods("nse", "standalone", (period,))


def test_failed_then_succeeded_lookup_stays_stable_within_ttl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A miss then a real filing available a moment later must NOT flip the
    answer within the negative-cache TTL — the caller sees a stable None."""
    calls = {"n": 0}

    def fake_fetch(bare: str) -> FiledPeriods | None:  # noqa: ARG001
        calls["n"] += 1
        return None if calls["n"] == 1 else _periods()

    monkeypatch.setattr(exchange_financials, "_fetch", fake_fetch)

    first = asyncio.run(exchange_financials.get_filed_periods("TCS.NS"))
    second = asyncio.run(exchange_financials.get_filed_periods("TCS.NS"))
    assert first is None
    assert second is None  # stays on the miss, not the now-available filing
    assert calls["n"] == 1  # the second call served the negative cache, no refetch


def test_negative_cache_expires_and_serves_the_now_available_filing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Once the negative-cache TTL has elapsed, the next call re-fetches and
    the now-available filing is served."""
    calls = {"n": 0}

    def fake_fetch(bare: str) -> FiledPeriods | None:  # noqa: ARG001
        calls["n"] += 1
        return None if calls["n"] == 1 else _periods()

    monkeypatch.setattr(exchange_financials, "_fetch", fake_fetch)

    first = asyncio.run(exchange_financials.get_filed_periods("TCS.NS"))
    assert first is None

    # Fast-forward past the negative-cache window without a real sleep.
    key = "TCS.NS"
    missed_at = exchange_financials._negative_cache[key]  # noqa: SLF001
    exchange_financials._negative_cache[key] = (  # noqa: SLF001
        missed_at - exchange_financials._NEGATIVE_TTL_SECONDS - 1  # noqa: SLF001
    )

    second = asyncio.run(exchange_financials.get_filed_periods("TCS.NS"))
    assert second is not None
    assert second.venue == "nse"
    assert calls["n"] == 2
