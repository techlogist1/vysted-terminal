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


# ---------------------------------------------------------------------------
# R7 Component 4 — master hygiene + deterministic BSE resolution.
# ---------------------------------------------------------------------------


def _raise_if_network(*_a: object, **_k: object) -> None:
    raise AssertionError("live lookup must not fire for a bundled-master symbol")


def test_iconikspev_resolves_deterministically_to_bse(monkeypatch) -> None:  # noqa: ANN001
    """The acceptance defect: ICONIKSPEV used to fall through to the live lookup
    and come back as a CONTRADICTION (exchange 'NSE' + yahoo 'ICONIKSPEV.BO',
    confidence 0.6). The regenerated BSE master makes it a deterministic exact
    hit: consistent BSE identity, real scrip code, confidence 1.0, NO network."""
    monkeypatch.setattr(symbol_resolver, "_live_lookup", _raise_if_network)
    r = symbol_resolver.resolve("ICONIKSPEV", "IN")
    assert r.best is not None
    assert r.best.symbol == "ICONIKSPEV"
    assert r.best.exchange == "BSE"
    assert r.best.region == "IN"
    assert r.best.yahoo_symbol == "ICONIKSPEV.BO"
    assert r.confidence >= 0.99
    assert not r.needs_disambiguation
    # The same identity carries its real scrip code for bhavcopy routing.
    assert symbol_resolver.bse_scrip_code("ICONIKSPEV") == "511260"
    assert symbol_resolver.is_bse_symbol("ICONIKSPEV")
    assert symbol_resolver.region_hint("ICONIKSPEV") == "IN"


def test_dual_listed_carries_both_exchanges_nse_preferred(monkeypatch) -> None:  # noqa: ANN001
    """A dual-listed name (RELIANCE) resolves best to NSE (trading data) but the
    BSE row rides along as a candidate (retained for BSE-only fundamentals)."""
    monkeypatch.setattr(symbol_resolver, "_live_lookup", _raise_if_network)
    r = symbol_resolver.resolve("RELIANCE", "IN")
    assert r.best is not None
    assert r.best.exchange == "NSE"
    assert r.best.yahoo_symbol == "RELIANCE.NS"
    exchanges = [c.exchange for c in r.candidates]
    assert "NSE" in exchanges and "BSE" in exchanges
    assert exchanges.index("NSE") < exchanges.index("BSE")  # NSE preferred
    bse_row = next(c for c in r.candidates if c.exchange == "BSE")
    assert bse_row.symbol == "RELIANCE"
    assert bse_row.yahoo_symbol == "RELIANCE.BO"


def test_bo_suffix_pins_bse_identity(monkeypatch) -> None:  # noqa: ANN001
    """An explicit .BO suffix pins the BSE identity — it must NOT be silently
    rewritten to the NSE listing (the old behaviour for dual-listed names)."""
    monkeypatch.setattr(symbol_resolver, "_live_lookup", _raise_if_network)
    r = symbol_resolver.resolve("RELIANCE.BO", "US")
    assert r.best is not None
    assert r.best.exchange == "BSE"
    assert r.best.region == "IN"
    assert r.best.yahoo_symbol == "RELIANCE.BO"
    assert all(c.exchange == "BSE" for c in r.candidates)


def test_bse_only_name_fuzzy_resolves(monkeypatch) -> None:  # noqa: ANN001
    """A BSE-only company NAME (not just its ticker) resolves via the fuzzy scan."""
    monkeypatch.setattr(symbol_resolver, "_live_lookup", _raise_if_network)
    r = symbol_resolver.resolve("Iconik Sports", "IN")
    assert r.best is not None
    assert r.best.symbol == "ICONIKSPEV"
    assert r.best.exchange == "BSE"
    assert r.best.yahoo_symbol == "ICONIKSPEV.BO"


def test_live_lookup_bo_suffix_maps_to_bse_exchange(monkeypatch) -> None:  # noqa: ANN001
    """Regression for the live-lookup contradiction: a .BO search hit must carry
    exchange 'BSE' (it used to hardcode 'NSE' for any India suffix)."""

    class _FakeSearch:
        quotes = [{"symbol": "SOMETHING.BO", "shortname": "Something Ltd"}]

        def __init__(self, *_a: object, **_k: object) -> None: ...

    import yfinance as yf

    monkeypatch.setattr(yf, "Search", _FakeSearch)
    inst = symbol_resolver._live_lookup("Something", "IN")
    assert inst is not None
    assert inst.exchange == "BSE"
    assert inst.yahoo_symbol == "SOMETHING.BO"
    assert inst.symbol == "SOMETHING"
    assert inst.score == 0.6


def test_exchange_agrees_with_yahoo_suffix_across_full_masters() -> None:
    """Master hygiene invariant, scanned over EVERY row of all three regenerated
    masters: the exchange field always agrees with the yahoo_symbol suffix
    (NSE ↔ .NS, BSE ↔ .BO, US ↔ no suffix) and each master carries one row per
    symbol with the fields the routing layer depends on."""
    suffix_by_exchange = {"NSE": ".NS", "BSE": ".BO", "US": ""}
    for sym in symbol_resolver._nse_master():
        inst = symbol_resolver._instrument_nse(sym, 1.0)
        assert inst.exchange == "NSE" and inst.yahoo_symbol == f"{sym}.NS"
    for sym, (_name, _group, code) in symbol_resolver._bse_master().items():
        inst = symbol_resolver._instrument_bse(sym, 1.0)
        assert inst.exchange == "BSE" and inst.yahoo_symbol == f"{sym}.BO"
        assert code.isdigit(), f"BSE master row {sym} lacks a numeric scrip code"
    for sym in symbol_resolver._us_master():
        inst = symbol_resolver._instrument_us(sym, 1.0)
        assert inst.exchange == "US" and inst.yahoo_symbol == sym
        assert suffix_by_exchange[inst.exchange] == ""


def test_region_hint_covers_full_regenerated_masters() -> None:
    """region_hint must hit for EVERY India-master symbol that is not a US
    collision: a bare BSE-only micro-cap → IN (this is what makes the /history
    route's honest in_eod_only reason fire), an NSE-only name → IN, and an
    ambiguous India+US ticker → None (the locale breaks the tie)."""
    us = set(symbol_resolver._us_master())
    for sym in symbol_resolver._bse_master():
        expected = None if sym in us else "IN"
        assert symbol_resolver.region_hint(sym) == expected, sym
    for sym in symbol_resolver._nse_master():
        expected = None if sym in us else "IN"
        assert symbol_resolver.region_hint(sym) == expected, sym


def test_fuzzy_and_autocomplete_emit_one_canonical_row_per_instrument() -> None:
    """One canonical row per instrument: a dual-listed name must never surface
    as both its NSE and BSE rows in the same fuzzy/autocomplete result set."""
    r = symbol_resolver.resolve("Reliance Industries", "IN")
    symbols = [(c.symbol, c.exchange) for c in r.candidates]
    assert ("RELIANCE", "NSE") in symbols
    assert ("RELIANCE", "BSE") not in symbols
    ac = symbol_resolver.autocomplete("RELIANCE", "IN", limit=20)
    ac_pairs = [(c.symbol, c.exchange) for c in ac]
    assert ("RELIANCE", "NSE") in ac_pairs
    assert ("RELIANCE", "BSE") not in ac_pairs


def test_autocomplete_route_mobile_still_resolves_route() -> None:
    """The acceptance check the brief names: adding 4,873 BSE rows to the scan
    must not displace 'Route Mobile' → ROUTE (NSE, the canonical dual-listed row)."""
    rows = symbol_resolver.autocomplete("Route Mobile", "IN", limit=8)
    assert rows, "autocomplete returned nothing for 'Route Mobile'"
    assert rows[0].symbol == "ROUTE"
    assert rows[0].exchange == "NSE"
    assert rows[0].yahoo_symbol == "ROUTE.NS"


def test_autocomplete_surfaces_bse_only_microcaps() -> None:
    rows = symbol_resolver.autocomplete("ICONIK", "IN", limit=8)
    assert rows
    assert rows[0].symbol == "ICONIKSPEV"
    assert rows[0].exchange == "BSE"
    assert rows[0].yahoo_symbol == "ICONIKSPEV.BO"


def test_autocomplete_stays_keystroke_fast_over_full_masters() -> None:
    """Autocomplete is the on-keystroke path: masters-only, no fuzzy matcher, no
    network. With the full BSE master in the scan (~18k rows across all three
    masters) a burst of 25 queries must stay well inside the keystroke budget —
    the bound is generous (40ms/query avg) so CI variance never flakes it."""
    import time

    queries = ["R", "RO", "ROU", "ROUT", "ROUTE", "REL", "ICON", "TATA", "A", "AAP"]
    symbol_resolver.autocomplete("warm", "IN")  # warm the lru_cache'd masters
    start = time.monotonic()
    for _ in range(25):
        symbol_resolver.autocomplete(queries[_ % len(queries)], "IN", limit=8)
    elapsed = time.monotonic() - start
    assert elapsed < 1.0, f"25 autocomplete calls took {elapsed:.2f}s (>1.0s budget)"
