"""Pass B (B1) — symbol resolution against the bundled masters (FR-061)."""

from __future__ import annotations

import pytest

from services import provider_health, symbol_resolver


@pytest.fixture(autouse=True)
def _fresh_live_lookup_budget():
    """The D58d live-lookup LRU/cooldown must never leak between tests."""
    symbol_resolver._reset_live_lookup_for_tests()
    yield
    symbol_resolver._reset_live_lookup_for_tests()


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
    # R10: the live lookup returns ALL hits as candidates (a list).
    rows = symbol_resolver._live_lookup("Something", "IN")
    assert len(rows) == 1
    inst = rows[0]
    assert inst.exchange == "BSE"
    assert inst.yahoo_symbol == "SOMETHING.BO"
    assert inst.symbol == "SOMETHING"
    assert inst.score == 0.6


def test_live_lookup_collects_all_quotes_india_first_and_never_binds(monkeypatch) -> None:  # noqa: ANN001
    """R10 (E1): the live fallback collects EVERY hit (not just the first),
    ranks .NS/.BO first under an IN session, and every row rides 0.6 — which
    the resolution policy maps to disambiguate, never bound."""

    class _FakeSearch:
        quotes = [
            {"symbol": "SOMETHING", "shortname": "Something Inc", "exchange": "NMS"},
            {"symbol": "SOMETHING.BO", "shortname": "Something Ltd"},
            {"symbol": "SOMETHING.NS", "shortname": "Something Ltd"},
        ]

        def __init__(self, *_a: object, **_k: object) -> None: ...

    import yfinance as yf

    from services.resolution_policy import decide

    monkeypatch.setattr(yf, "Search", _FakeSearch)
    rows = symbol_resolver._live_lookup("Something", "IN")
    assert [r.yahoo_symbol for r in rows] == ["SOMETHING.BO", "SOMETHING.NS", "SOMETHING"]
    assert all(r.score == 0.6 for r in rows)
    resolution = symbol_resolver.Resolution(query="Something", best=rows[0], candidates=rows)
    assert decide(resolution).outcome == "disambiguate"
    # A US session keeps the engine's own ranking.
    us_rows = symbol_resolver._live_lookup("Something", "US")
    assert us_rows[0].yahoo_symbol == "SOMETHING"


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


# ---------------------------------------------------------------------------
# R10 (E1) — band tie-break, first-token normalization, fuzzy demotion.
# ---------------------------------------------------------------------------


def test_first_token_normalization_lands_same_band_locale_breaks_tie() -> None:
    """US "RELIANCE, INC." and NSE "Reliance Industries Limited" must land in
    the SAME band for a one-word query (trailing punctuation + corporate
    suffixes stripped) — so locale, not punctuation, breaks the tie."""
    from services.resolution_policy import BAND_FIRST_WORD

    us = symbol_resolver._name_score("reliance", "reliance, inc.", 1)
    nse = symbol_resolver._name_score("reliance", "reliance industries limited", 1)
    assert us == (BAND_FIRST_WORD, 0.97)
    assert nse == (BAND_FIRST_WORD, 0.97)


def test_band_beats_locale_cross_locale_higher_band_wins(monkeypatch) -> None:  # noqa: ANN001
    """A cross-locale higher band ALWAYS beats a same-locale lower band: under
    an IN session "Apple" still resolves to AAPL (US, first-word band) — never
    an Indian fuzzy hit promoted by the old additive locale bonus."""
    monkeypatch.setattr(symbol_resolver, "_live_lookup", _raise_if_network)
    r = symbol_resolver.resolve("Apple", "IN")
    assert r.best is not None
    assert r.best.symbol == "AAPL"
    assert r.best.region == "US"
    # Reported confidence is the RAW band score — no bonus, no clamp.
    assert r.best.score == 0.97


def test_reported_scores_are_never_inflated(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(symbol_resolver, "_live_lookup", _raise_if_network)
    for query, region in (("Tata Steel", "IN"), ("Apple", "US"), ("Reliance Industries", "IN")):
        r = symbol_resolver.resolve(query, region)
        assert r.best is not None
        assert all(c.score <= 1.0 for c in r.candidates), (query, region)


def test_whole_query_fuzzy_disabled_beyond_four_words(monkeypatch) -> None:  # noqa: ANN001
    """A >4-word query never scores via whole-string SequenceMatcher — the
    Phase-0 "Reliance Industries Q4 FY26 results"→LNKS class. Such a query
    resolves to nothing here (the research prefix loop handles the binding)."""
    monkeypatch.setattr(symbol_resolver, "_live_lookup", lambda query, region: [])
    r = symbol_resolver.resolve("Reliance Industries Q4 FY26 results announced", "IN")
    assert all(c.band != 0 for c in r.candidates)  # no fuzzy rows at >4 words


def test_query_cleaning_strips_lead_verbs_and_trailing_punctuation(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(symbol_resolver, "_live_lookup", _raise_if_network)
    # "research Reliance" cleans to "Reliance" — the exact NSE ticker, never a
    # fuzzy hit on the verb (REFR, "Research Frontiers Inc" was the live bind).
    r = symbol_resolver.resolve("research Reliance", "IN")
    assert r.best is not None and r.best.symbol == "RELIANCE" and r.best.exchange == "NSE"
    # Trailing punctuation never blocks an exact hit.
    r2 = symbol_resolver.resolve("reliance,", "IN")
    assert r2.best is not None and r2.best.symbol == "RELIANCE"


def test_marquee_alias_two_word_generic_key(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(symbol_resolver, "_live_lookup", _raise_if_network)
    r = symbol_resolver.resolve("tata stock", "IN")
    assert r.best is not None
    assert r.best.band == 5  # marquee
    assert r.needs_disambiguation
    assert [c.symbol for c in r.candidates][:2] == ["TCS", "TMCV"]


def test_marquee_skipped_for_us_region(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(symbol_resolver, "_live_lookup", lambda query, region: [])
    r = symbol_resolver.resolve("tata", "US")
    # No marquee under US: whatever matches is band-scored, never the curated list.
    assert r.best is None or r.best.band != 5


# ---------------------------------------------------------------------------
# R11 (D58c) — region tie-break in chooser candidate ordering (V5).
# ---------------------------------------------------------------------------


def test_in_region_chooser_never_ranks_foreign_above_in_at_equal_band(monkeypatch) -> None:  # noqa: ANN001
    """V5: 'Reliance Q4 results' (region IN) listed [RELIANCE, FRLCY(US), FLNCF]
    in its chooser. The candidate ordering must never let a foreign ticker
    outrank an IN-listed candidate at the same band under an IN session."""
    monkeypatch.setattr(symbol_resolver, "_live_lookup", lambda *_a, **_k: [])
    for query in ("Reliance Q4 results", "Larsen and Toubro", "Tata Steel results"):
        r = symbol_resolver.resolve(query, "IN")
        assert r.best is not None, query
        assert r.best.region == "IN", (query, r.best)
        for i, earlier in enumerate(r.candidates):
            for later in r.candidates[i + 1 :]:
                if earlier.band == later.band and earlier.region != "IN":
                    assert later.region != "IN", (
                        f"{query!r}: foreign {earlier.symbol} outranks IN "
                        f"{later.symbol} at band {earlier.band}"
                    )


# ---------------------------------------------------------------------------
# R11 (D58d) — the live-lookup budget: LRU cache + failure cooldown +
# provider-health reporting.
# ---------------------------------------------------------------------------


class _CountingSearch:
    """A yfinance.Search stand-in that counts constructions."""

    calls = 0
    quotes = [{"symbol": "SOMETHING.NS", "shortname": "Something Ltd"}]

    def __init__(self, *_a: object, **_k: object) -> None:
        type(self).calls += 1


def test_live_lookup_caches_repeated_queries(monkeypatch) -> None:  # noqa: ANN001
    import yfinance as yf

    _CountingSearch.calls = 0
    monkeypatch.setattr(yf, "Search", _CountingSearch)
    first = symbol_resolver._live_lookup("Something Unlisted", "IN")
    second = symbol_resolver._live_lookup("Something Unlisted", "IN")
    assert _CountingSearch.calls == 1, "a repeated (query, region) must not re-hit the network"
    assert [i.yahoo_symbol for i in first] == [i.yahoo_symbol for i in second]
    # A different region is a different cache key — it MAY fetch again.
    symbol_resolver._live_lookup("Something Unlisted", "US")
    assert _CountingSearch.calls == 2


def test_live_lookup_caches_successful_empty_results(monkeypatch) -> None:  # noqa: ANN001
    import yfinance as yf

    class _EmptySearch(_CountingSearch):
        quotes: list[dict] = []

    _EmptySearch.calls = 0
    monkeypatch.setattr(yf, "Search", _EmptySearch)
    assert symbol_resolver._live_lookup("zzz nothing zzz", "IN") == []
    assert symbol_resolver._live_lookup("zzz nothing zzz", "IN") == []
    assert _EmptySearch.calls == 1, "a successful empty search is a cacheable negative"


def test_live_lookup_failure_opens_cooldown_and_skips_network(monkeypatch) -> None:  # noqa: ANN001
    import yfinance as yf

    class _ExplodingSearch:
        calls = 0

        def __init__(self, *_a: object, **_k: object) -> None:
            type(self).calls += 1
            raise RuntimeError("connection reset")

    monkeypatch.setattr(yf, "Search", _ExplodingSearch)
    assert symbol_resolver._live_lookup("first failing query", "IN") == []
    assert _ExplodingSearch.calls == 1
    # Inside the cooldown window EVERY live lookup — any query — short-circuits.
    assert symbol_resolver._live_lookup("a different query", "IN") == []
    assert symbol_resolver._live_lookup("yet another", "US") == []
    assert _ExplodingSearch.calls == 1, "cooldown must skip the network entirely"
    # After the cooldown lapses the live rung probes again.
    symbol_resolver._live_cooldown_until = 0.0
    assert symbol_resolver._live_lookup("post-cooldown query", "IN") == []
    assert _ExplodingSearch.calls == 2


def test_live_lookup_reports_rate_limit_to_provider_health(monkeypatch) -> None:  # noqa: ANN001
    import yfinance as yf
    from yfinance.exceptions import YFRateLimitError

    provider_health.reset_for_tests()

    class _ThrottledSearch:
        def __init__(self, *_a: object, **_k: object) -> None:
            raise YFRateLimitError()

    monkeypatch.setattr(yf, "Search", _ThrottledSearch)
    assert symbol_resolver._live_lookup("throttled query", "IN") == []
    status = provider_health.status()
    assert status["throttles_total"] >= 1, "a YFRateLimitError must reach provider_health"

    # A healthy round-trip reports success — the family streak fully resets.
    symbol_resolver._reset_live_lookup_for_tests()
    monkeypatch.setattr(yf, "Search", _CountingSearch)
    symbol_resolver._live_lookup("healthy query", "IN")
    status = provider_health.status()
    assert status["consecutive_throttles"] == 0
    assert not status["open"]
    provider_health.reset_for_tests()


def test_live_lookup_non_rate_limit_failure_does_not_count_as_throttle(monkeypatch) -> None:  # noqa: ANN001
    import yfinance as yf

    provider_health.reset_for_tests()

    class _BrokenSearch:
        def __init__(self, *_a: object, **_k: object) -> None:
            raise ValueError("bad JSON")

    monkeypatch.setattr(yf, "Search", _BrokenSearch)
    assert symbol_resolver._live_lookup("parse-broken query", "IN") == []
    assert provider_health.status()["throttles_total"] == 0
    provider_health.reset_for_tests()


def test_live_lookup_cache_is_bounded_lru(monkeypatch) -> None:  # noqa: ANN001
    import yfinance as yf

    _CountingSearch.calls = 0
    monkeypatch.setattr(yf, "Search", _CountingSearch)
    limit = symbol_resolver._LIVE_CACHE_MAX_ENTRIES
    for i in range(limit + 10):
        symbol_resolver._live_lookup(f"query number {i}", "IN")
    assert len(symbol_resolver._live_cache) == limit, "the LRU must stay bounded"
    # The oldest entries were evicted; the newest are still cached.
    assert ("query number 0", "IN") not in symbol_resolver._live_cache
    assert (f"query number {limit + 9}", "IN") in symbol_resolver._live_cache


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
