"""R13 / D57 — ``services.dividend_actions``: the declared-but-unpaid seam.

No live network: ``nse_provider.get_corporate_actions`` is monkeypatched and the
IST clock is pinned to 2026-07-10 (the R13 probe date, when PFC's ₹3.95 final
dividend record date 2026-07-31 is still in the future).
"""

from __future__ import annotations

import asyncio
from datetime import date

import pytest

from services import dividend_actions, nse_provider, provider_health, symbol_resolver
from services.errors import ProviderError

# Verbatim-shaped NSE corporate-actions rows (live probe 2026-07-10, PFC).
_PFC_ACTIONS = [
    {"subject": "Dividend - Rs 3.95 Per Share", "exDate": "31-Jul-2026", "recDate": "31-Jul-2026"},
    {"subject": "Interim Dividend - Rs 3.25 Per Share", "recDate": "23-Mar-2026"},
    {"subject": "Interim Dividend - Rs 4 Per Share", "recDate": "20-Feb-2026"},
]


@pytest.fixture(autouse=True)
def _reset(monkeypatch: pytest.MonkeyPatch) -> None:
    provider_health.reset_for_tests()
    symbol_resolver.reset_caches_for_tests()
    monkeypatch.setattr(dividend_actions, "_ist_today", lambda: date(2026, 7, 10))


def test_select_declared_picks_the_future_record_dividend() -> None:
    declared = dividend_actions._select_declared(_PFC_ACTIONS, date(2026, 7, 10))
    assert declared is not None
    assert declared.amount == 3.95
    assert declared.record_date == "2026-07-31"
    assert "3.95" in declared.subject


def test_select_declared_ignores_past_and_non_dividend_actions() -> None:
    rows = [
        {"subject": "Interim Dividend - Rs 3.25 Per Share", "recDate": "23-Mar-2026"},  # past
        {"subject": "Bonus 1:1", "recDate": "31-Dec-2026"},  # not a dividend
        {"subject": "Face Value Split", "recDate": "31-Dec-2026"},
    ]
    assert dividend_actions._select_declared(rows, date(2026, 7, 10)) is None


def test_select_declared_takes_the_nearest_upcoming_when_multiple() -> None:
    rows = [
        {"subject": "Special Dividend - Rs 10 Per Share", "recDate": "30-Sep-2026"},
        {"subject": "Final Dividend - Rs 5 Per Share", "recDate": "15-Aug-2026"},
    ]
    declared = dividend_actions._select_declared(rows, date(2026, 7, 10))
    assert declared is not None
    assert declared.record_date == "2026-08-15" and declared.amount == 5.0


def test_is_applicable_only_nse() -> None:
    assert dividend_actions.is_applicable("PFC")
    assert not dividend_actions.is_applicable("AAPL")
    assert not dividend_actions.is_applicable("")


def test_get_declared_unpaid_dividend_round_trips(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nse_provider, "get_corporate_actions", lambda symbol: _PFC_ACTIONS)
    declared = asyncio.run(dividend_actions.get_declared_unpaid_dividend("PFC"))
    assert declared is not None
    assert declared.as_wire() == {
        "amount": 3.95,
        "record_date": "2026-07-31",
        "subject": "Dividend - Rs 3.95 Per Share",
    }


def test_get_declared_non_nse_never_fetches(monkeypatch: pytest.MonkeyPatch) -> None:
    def must_not_run(symbol: str) -> list[dict]:
        raise AssertionError("non-NSE symbol must not reach the corporate-actions lane")

    monkeypatch.setattr(nse_provider, "get_corporate_actions", must_not_run)
    assert asyncio.run(dividend_actions.get_declared_unpaid_dividend("AAPL")) is None


def test_get_declared_block_opens_circuit_and_never_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        nse_provider,
        "get_corporate_actions",
        lambda symbol: (_ for _ in ()).throw(ProviderError("nse_direct: blocked (HTTP 401)")),
    )
    for _ in range(3):
        assert asyncio.run(dividend_actions.get_declared_unpaid_dividend("PFC")) is None
    assert provider_health.is_open(dividend_actions.EXCHANGE)
