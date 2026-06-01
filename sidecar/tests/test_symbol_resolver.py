"""Pass B (B1) — symbol resolution against the bundled masters (FR-061)."""

from __future__ import annotations

from services import symbol_resolver


def test_region_hint_decisive_and_ambiguous() -> None:
    assert symbol_resolver.region_hint("GOLDBEES") == "IN"  # NSE-only ETF
    assert symbol_resolver.region_hint("TATASTEEL") == "IN"  # NSE-only
    assert symbol_resolver.region_hint("AAPL") == "US"  # US-only
    assert symbol_resolver.region_hint("RELIANCE.NS") == "IN"  # suffix decisive
    assert symbol_resolver.region_hint("TATASTEEL.BO") == "IN"
    # INFY lists on both NSE and as a US ADR → ambiguous → defer to user locale.
    assert symbol_resolver.region_hint("INFY") is None


def test_membership_helpers() -> None:
    assert symbol_resolver.is_nse_symbol("GOLDBEES")
    assert symbol_resolver.is_nse_symbol("RELIANCE.NS")  # suffix stripped
    assert not symbol_resolver.is_nse_symbol("AAPL")
    assert symbol_resolver.is_us_symbol("AAPL")
    assert not symbol_resolver.is_us_symbol("GOLDBEES")


def test_resolve_exact_ticker() -> None:
    r = symbol_resolver.resolve("GOLDBEES", "IN")
    assert r.best is not None
    assert r.best.symbol == "GOLDBEES"
    assert r.best.exchange == "NSE"
    assert r.best.asset_class == "etf"
    assert r.best.region == "IN"
    assert r.best.yahoo_symbol == "GOLDBEES.NS"
    assert r.confidence >= 0.99


def test_resolve_name_locale_ranked() -> None:
    r = symbol_resolver.resolve("Tata Steel", "IN")
    assert r.best is not None and r.best.symbol == "TATASTEEL"
    # Prominence ordering: "Apple" resolves to AAPL, not a microcap "Apple ...".
    r2 = symbol_resolver.resolve("Apple", "US")
    assert r2.best is not None and r2.best.symbol == "AAPL"


def test_resolve_us_ticker() -> None:
    r = symbol_resolver.resolve("NVDA", "US")
    assert r.best is not None and r.best.region == "US" and r.best.symbol == "NVDA"


def test_resolve_unknown_returns_none(monkeypatch) -> None:  # noqa: ANN001
    # A nonsense string resolves to nothing (the tool surfaces an honest message).
    # Stub the live network fallback so the test is offline + deterministic.
    monkeypatch.setattr(symbol_resolver, "_live_lookup", lambda query, region: None)
    r = symbol_resolver.resolve("zzzqqqxnotathing", "US")
    assert r.best is None
    assert r.candidates == []


def test_suffix_pins_exchange_even_for_us_locale() -> None:
    r = symbol_resolver.resolve("RELIANCE.NS", "US")
    assert r.best is not None and r.best.exchange == "NSE" and r.best.region == "IN"
