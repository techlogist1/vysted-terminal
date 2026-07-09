"""R12 (D66) — the resolver answers a renamed NSE symbol as its CURRENT identity.

The battery finding: eight days after NSE renamed Gujarat Gas Ltd to Gujarat
Energy Limited (GUJGASLTD → GUJENERGY, effective 2026-07-01), the app still
resolved both the name and the old ticker to the stale identity. With the
symbol-change lane's map injected (no live network), the resolver must answer
GUJENERGY with an explicit rename annotation — never a silent swap, and never
the stale symbol.
"""

from __future__ import annotations

from datetime import date

import pytest

from services import nse_symbol_change, symbol_resolver


def _raise_if_network(*_a: object, **_k: object) -> None:
    raise AssertionError("live lookup must not fire for a bundled-master symbol")


@pytest.fixture(autouse=True)
def _rename_map(monkeypatch: pytest.MonkeyPatch):
    """Inject the GUJGASLTD → GUJENERGY hop directly (offline) and pin the date.

    Resets both the live-lookup budget and the symbol-change map so nothing
    leaks into (or out of) the shared resolver test suite.
    """
    symbol_resolver._reset_live_lookup_for_tests()
    monkeypatch.setattr(symbol_resolver, "_live_lookup", _raise_if_network)
    monkeypatch.setattr(nse_symbol_change, "_ist_today", lambda: date(2026, 7, 10))
    nse_symbol_change.set_active_map_for_tests(
        {
            "GUJGASLTD": nse_symbol_change.SymbolChange(
                old_symbol="GUJGASLTD",
                new_symbol="GUJENERGY",
                effective_date=date(2026, 7, 1),
                new_name="GUJARAT ENERGY LIMITED",
            ),
        }
    )
    yield
    nse_symbol_change.reset_for_tests()
    symbol_resolver._reset_live_lookup_for_tests()


def _assert_renamed_to_gujenergy(best: symbol_resolver.Instrument) -> None:
    assert best.symbol == "GUJENERGY"
    assert best.exchange == "NSE"
    assert best.region == "IN"
    assert best.yahoo_symbol == "GUJENERGY.NS"
    assert best.name == "GUJARAT ENERGY LIMITED"
    assert best.rename is not None
    assert best.rename.renamed_from == "GUJGASLTD"
    assert best.rename.renamed_to == "GUJENERGY"
    assert best.rename.effective_date == "2026-07-01"


def test_old_ticker_resolves_to_current_symbol() -> None:
    r = symbol_resolver.resolve("GUJGASLTD", "IN")
    assert r.best is not None
    _assert_renamed_to_gujenergy(r.best)
    # The stale NSE ticker must not survive anywhere in the answer.
    assert all(not (c.symbol == "GUJGASLTD" and c.exchange == "NSE") for c in r.candidates)


def test_old_name_resolves_to_current_symbol() -> None:
    r = symbol_resolver.resolve("gujarat gas", "IN")
    assert r.best is not None
    _assert_renamed_to_gujenergy(r.best)


def test_no_rename_when_map_empty() -> None:
    """A cold app with no symbol-change data answers exactly as before (stale but
    honest — never a fabricated rename)."""
    nse_symbol_change.reset_for_tests()  # empty the injected map
    r = symbol_resolver.resolve("GUJGASLTD", "IN")
    assert r.best is not None
    assert r.best.symbol == "GUJGASLTD"
    assert r.best.rename is None
