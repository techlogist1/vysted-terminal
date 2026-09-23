"""R13 / D57 — ``services.dividend_actions``: the declared-but-unpaid seam.

No live network: ``nse_provider.get_corporate_actions`` and the BSE
corporate-action seam are monkeypatched and the IST clock is pinned to
2026-07-10 (the R13 probe date, when PFC's ₹3.95 final dividend record date
2026-07-31 is still in the future). The seam reads the merged NSE+BSE lane
(R15-DATA-025), so the selection tests take typed ``CorporateAction`` rows.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path

import pytest

from models.announcements import CorporateAction
from services import (
    corporate_disclosures,
    dividend_actions,
    nse_provider,
    provider_health,
    symbol_resolver,
)
from services.errors import ProviderError

# Verbatim-shaped NSE corporate-actions rows (live probe 2026-07-10, PFC).
_PFC_ACTIONS = [
    {"subject": "Dividend - Rs 3.95 Per Share", "exDate": "31-Jul-2026", "recDate": "31-Jul-2026"},
    {"subject": "Interim Dividend - Rs 3.25 Per Share", "recDate": "23-Mar-2026"},
    {"subject": "Interim Dividend - Rs 4 Per Share", "recDate": "20-Feb-2026"},
]


def _dividend(
    purpose: str, amount: float | None, record: date, kind: str = "dividend"
) -> CorporateAction:
    return CorporateAction(
        symbol="PFC",
        kind=kind,
        purpose=purpose,
        amount_per_share=amount,
        record_date=record,
        exchange="NSE",
    )


#: The typed rows the merged lane builds from ``_PFC_ACTIONS``.
_PFC_TYPED = [
    _dividend("Dividend - Rs 3.95 Per Share", 3.95, date(2026, 7, 31)),
    _dividend("Interim Dividend - Rs 3.25 Per Share", 3.25, date(2026, 3, 23)),
    _dividend("Interim Dividend - Rs 4 Per Share", 4.0, date(2026, 2, 20)),
]


@pytest.fixture(autouse=True)
def _reset(monkeypatch: pytest.MonkeyPatch) -> None:
    provider_health.reset_for_tests()
    symbol_resolver.reset_caches_for_tests()
    monkeypatch.setattr(dividend_actions, "_ist_today", lambda: date(2026, 7, 10))
    # The BSE half of the merged lane: an empty action list unless a test serves one.
    monkeypatch.setattr(corporate_disclosures, "_bse_get_json", lambda url, params: {"Table2": []})


def test_select_declared_picks_the_future_record_dividend() -> None:
    declared = dividend_actions._select_declared(_PFC_TYPED, date(2026, 7, 10))
    assert declared is not None
    assert declared.amount == 3.95
    assert declared.record_date == "2026-07-31"
    assert "3.95" in declared.subject


def test_select_declared_ignores_past_and_non_dividend_actions() -> None:
    rows = [
        _dividend("Interim Dividend - Rs 3.25 Per Share", 3.25, date(2026, 3, 23)),  # past
        _dividend("Bonus 1:1", None, date(2026, 12, 31), kind="bonus"),  # not a dividend
        _dividend("Face Value Split", None, date(2026, 12, 31), kind="split"),
    ]
    assert dividend_actions._select_declared(rows, date(2026, 7, 10)) is None


def test_select_declared_takes_the_nearest_upcoming_when_multiple() -> None:
    rows = [
        _dividend("Special Dividend - Rs 10 Per Share", 10.0, date(2026, 9, 30)),
        _dividend("Final Dividend - Rs 5 Per Share", 5.0, date(2026, 8, 15)),
    ]
    declared = dividend_actions._select_declared(rows, date(2026, 7, 10))
    assert declared is not None
    assert declared.record_date == "2026-08-15" and declared.amount == 5.0


def test_is_applicable_to_nse_and_bse_listings() -> None:
    assert dividend_actions.is_applicable("PFC.NS")
    assert dividend_actions.is_applicable("JONJUA.BO")  # BSE-only (R15-DATA-025)
    assert not dividend_actions.is_applicable("AAPL")
    assert not dividend_actions.is_applicable("")


def test_get_declared_unpaid_dividend_round_trips(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nse_provider, "get_corporate_actions", lambda symbol: _PFC_ACTIONS)
    declared = asyncio.run(dividend_actions.get_declared_unpaid_dividend("PFC.NS"))
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
        assert asyncio.run(dividend_actions.get_declared_unpaid_dividend("PFC.NS")) is None
    assert provider_health.is_open(dividend_actions.EXCHANGE)


def test_bse_only_listing_gets_the_declared_dividend(monkeypatch: pytest.MonkeyPatch) -> None:
    """R15-DATA-025: the merged lane serves a BSE-only name (JONJUA's Rs 0.10
    final, record 2025-09-20, live BSE feed 2026-09-24) the NSE lane never had."""
    fixture = Path(__file__).parent / "fixtures" / "bse"
    payload = json.loads((fixture / "corporate_action_542446_jonjua_20260924.json").read_text())
    monkeypatch.setattr(corporate_disclosures, "_bse_get_json", lambda url, params: payload)
    monkeypatch.setattr(dividend_actions, "_ist_today", lambda: date(2025, 9, 1))

    declared = asyncio.run(dividend_actions.get_declared_unpaid_dividend("JONJUA.BO"))
    assert declared is not None
    assert (declared.amount, declared.record_date) == (0.1, "2025-09-20")
