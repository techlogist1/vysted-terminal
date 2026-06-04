"""Data-depth rebuild (003): Yahoo-symbol NSE resolution + masters autocomplete.

Locks the root-cause fix for the all-dashes Indian Equity Overview — a bare NSE
ticker must get the ``.NS`` Yahoo suffix and a ``.NS``/``.BO`` form must NOT be
dot→dash mangled — plus the network-free autocomplete used by the symbol search.
"""

from __future__ import annotations

import pytest

import config
from services import symbol_resolver, yfinance_provider


def test_yahoo_symbol_preserves_india_suffix() -> None:
    assert yfinance_provider._yahoo_symbol("ROUTE.NS") == "ROUTE.NS"
    assert yfinance_provider._yahoo_symbol("tata.bo") == "TATA.BO"


def test_yahoo_symbol_adds_ns_for_bare_nse(monkeypatch: pytest.MonkeyPatch) -> None:
    # The bug: the old _normalize_symbol left a bare NSE ticker bare, so Yahoo
    # resolved an empty US lookup → all dashes. Now it gets the .NS suffix.
    monkeypatch.setattr(symbol_resolver, "is_nse_symbol", lambda s: True)
    monkeypatch.setattr(symbol_resolver, "is_us_symbol", lambda s: False)
    assert yfinance_provider._yahoo_symbol("ROUTE") == "ROUTE.NS"


def test_yahoo_symbol_keeps_us_dot_quirk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(symbol_resolver, "is_nse_symbol", lambda s: False)
    monkeypatch.setattr(symbol_resolver, "is_us_symbol", lambda s: True)
    assert yfinance_provider._yahoo_symbol("BRK.B") == "BRK-B"


def test_yahoo_symbol_in_session_dual_listed(monkeypatch: pytest.MonkeyPatch) -> None:
    # IN session: a DUAL-listed ticker (INFY trades on both NSE and NYSE) takes the
    # INR NSE listing, not the USD ADR — the locale-correct result for an IN user.
    monkeypatch.setattr(config, "get_region", lambda: "IN")
    assert yfinance_provider._yahoo_symbol("INFY") == "INFY.NS"
    # ...but a clearly-US ticker still resolves US even in an IN session (hint wins).
    monkeypatch.setattr(symbol_resolver, "region_hint", lambda s: "US")
    assert yfinance_provider._yahoo_symbol("AAPL") == "AAPL"


def test_yahoo_symbol_in_session_master_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    # A bare ticker NOT in the bundled master still gets .NS in an IN session, so a
    # master gap no longer silently dead-ends to an empty US lookup (Yahoo 404s an
    # unknown .NS -> honest "unavailable", never a wrong row).
    monkeypatch.setattr(symbol_resolver, "region_hint", lambda s: None)
    monkeypatch.setattr(symbol_resolver, "is_nse_symbol", lambda s: False)
    monkeypatch.setattr(symbol_resolver, "is_us_symbol", lambda s: False)
    monkeypatch.setattr(config, "get_region", lambda: "IN")
    assert yfinance_provider._yahoo_symbol("TATAMOTORS") == "TATAMOTORS.NS"


def test_autocomplete_matches_ticker_prefix() -> None:
    rows = symbol_resolver.autocomplete("AAP", region="US", limit=8)
    assert any(r.symbol == "AAPL" for r in rows)
    assert all(0.0 <= r.score <= 1.0 for r in rows)


def test_autocomplete_blank_is_empty() -> None:
    assert symbol_resolver.autocomplete("", region="US") == []
    assert symbol_resolver.autocomplete("   ", region="US") == []
