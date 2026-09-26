"""Pass B (B1) — symbol resolution against the bundled masters (FR-061)."""

from __future__ import annotations

import httpx
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


def test_bare_bse_scrip_code_resolves(monkeypatch) -> None:  # noqa: ANN001
    """A bare all-digit BSE scrip code (the header endpoint's native id) binds the
    one BSE row carrying it, exactly and with full confidence — a numeric code
    never appears in the alphabetic NSE/US masters, so it is unambiguous. Before
    this lane, ``/resolve?q=509470`` returned no match at all."""
    monkeypatch.setattr(symbol_resolver, "_live_lookup", _raise_if_network)
    r = symbol_resolver.resolve("509470", "IN")
    assert r.best is not None
    assert r.best.exchange == "BSE"
    assert r.best.symbol == "BOMOXY-B1"  # Bombay Oxygen Investments (BSE-only)
    assert r.best.yahoo_symbol == "BOMOXY-B1.BO"
    assert r.confidence >= 0.99
    assert not r.needs_disambiguation
    # Round-trips to the same scrip code regardless of the exact symbol spelling.
    assert symbol_resolver.bse_scrip_code(r.best.symbol) == "509470"
    # The explicit ``.BO`` form of the numeric code resolves the same way.
    r_bo = symbol_resolver.resolve("509470.BO", "IN")
    assert r_bo.best is not None and r_bo.best.symbol == "BOMOXY-B1"


def test_is_bse_symbol_and_scrip_code_accept_a_bare_code() -> None:
    """R15-LEAD-028: ``is_bse_symbol``/``bse_scrip_code`` (the hot-path helpers
    ``bse_provider._require_bse`` gates on) used to only key ``_bse_master()`` by
    ticker, so a data route addressed by scrip code alone (never through
    ``resolve()``) 404d even though the code was a known BSE listing. Both a
    ticker and its bare code now resolve identically, for a SECOND listing than
    the resolve()-path test above (KSE, 519421) so the fix isn't pinned to one row."""
    assert symbol_resolver.is_bse_symbol("KSE")
    assert symbol_resolver.is_bse_symbol("519421")
    assert symbol_resolver.bse_scrip_code("KSE") == "519421"
    assert symbol_resolver.bse_scrip_code("519421") == "519421"
    assert symbol_resolver.bse_symbol_for_code("519421") == "KSE"
    # An unknown code is a miss, not a false bind.
    assert not symbol_resolver.is_bse_symbol("999999")
    assert symbol_resolver.bse_scrip_code("999999") is None
    assert symbol_resolver.bse_symbol_for_code("999999") is None


def test_non_scrip_numeric_query_does_not_false_bind(monkeypatch) -> None:  # noqa: ANN001
    """A numeric query that matches no BSE scrip code stays unresolved — the lane
    binds only an EXACT code hit, never a nearest guess."""
    monkeypatch.setattr(symbol_resolver, "_live_lookup", lambda *_a, **_k: [])
    r = symbol_resolver.resolve("999999", "IN")
    assert r.best is None


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
    for sym, (_name, typ) in symbol_resolver._nse_master().items():
        inst = symbol_resolver._instrument_nse(sym, 1.0)
        # An NSE Emerge (SM) listing is Yahoo's -SM.NS form (R15-DATA-017).
        listing = f"{sym}-SM.NS" if typ == "SM" else f"{sym}.NS"
        assert inst.exchange == "NSE" and inst.yahoo_symbol == listing
    for sym, (_name, _group, code, _isin) in symbol_resolver._bse_master().items():
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


# ---------------------------------------------------------------------------
# R13 — full-legal-name resolution across the Ltd⟺Limited corporate-suffix seam.
# ---------------------------------------------------------------------------


def test_full_legal_name_binds_across_ltd_limited_seam(monkeypatch) -> None:  # noqa: ANN001
    """A company's own legal name ("Bilcare Ltd") must BIND its instrument even
    though the NSE master spells it "…Limited": normalizing the corporate-suffix
    seam BEFORE scoring lands the match in the name-exact band (4, score 1.0)
    instead of stranding it fuzzy under the accept band (the 0.846 bug). All six
    dual-listed battery names bind at their correct NSE instrument."""
    from services import resolution_policy

    monkeypatch.setattr(symbol_resolver, "_live_lookup", _raise_if_network)
    expected = {
        "Bilcare Ltd": "BI",
        "Standard Industries Ltd": "SIL",
        "UFO Moviez India Ltd": "UFO",
        "Paul Merchants Ltd": "PML",
        "Tilaknagar Industries Ltd": "TI",
        "Restaurant Brands Asia Ltd": "RBA",
    }
    for query, symbol in expected.items():
        r = symbol_resolver.resolve(query, "IN")
        decision = resolution_policy.decide(r)
        assert decision.outcome == "bound", (query, decision.outcome)
        assert r.best is not None and r.best.symbol == symbol, query
        assert r.best.exchange == "NSE" and r.best.band == resolution_policy.BAND_NAME_EXACT
        assert r.best.score == 1.0


def test_corporate_seam_canonicalizes_ltd_and_pvt_symmetrically() -> None:
    """The seam map normalizes Ltd⟺Limited, &⟺and, Pvt⟺Private on BOTH sides so an
    exact-modulo-suffix name scores name-exact — but a DIFFERENT multi-word name is
    NEVER promoted (it stays fuzzy: the E1 wrong-entity guard is untouched)."""
    from services.resolution_policy import BAND_NAME_EXACT

    # Exact modulo the seam → name-exact (band 4), full confidence.
    assert symbol_resolver._name_score("bilcare ltd", "bilcare limited", 2) == (
        BAND_NAME_EXACT,
        1.0,
    )
    assert symbol_resolver._name_score("larsen and toubro ltd", "larsen & toubro limited", 4) == (
        BAND_NAME_EXACT,
        1.0,
    )
    assert symbol_resolver._name_score("acme pvt ltd", "acme private limited", 3) == (
        BAND_NAME_EXACT,
        1.0,
    )
    # A genuinely different multi-word name is not promoted to name-exact.
    assert symbol_resolver._name_score("bilcare industries ltd", "bilcare limited", 3) is None
    diff = symbol_resolver._name_score("reliance power ltd", "reliance industries limited", 3)
    assert diff is not None and diff[0] < BAND_NAME_EXACT  # fuzzy, never bound outright


def test_ltd_seam_leaves_genuine_ambiguity_disambiguating(monkeypatch) -> None:  # noqa: ANN001
    """The seam fix must not collapse genuine ambiguity: a curated marquee family
    ("Bajaj") still forces an explicit choice rather than binding one member — the
    R10/R11 tie-guard + curated choosers are untouched."""
    from services import resolution_policy

    monkeypatch.setattr(symbol_resolver, "_live_lookup", _raise_if_network)
    r = symbol_resolver.resolve("Bajaj", "IN")
    assert resolution_policy.decide(r).outcome == "disambiguate"
    assert len(r.candidates) > 1


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


def test_live_lookup_empty_result_expires_and_a_hit_does_not(monkeypatch) -> None:  # noqa: ANN001
    """R15-DATA-097: a stock listed after the first miss is found once the empty
    result expires; a non-empty result stays in the LRU."""
    import yfinance as yf

    class _Search(_CountingSearch):
        quotes: list[dict] = []

    def age(key: tuple[str, str]) -> None:
        stamp, rows = symbol_resolver._live_cache[key]
        ttl = symbol_resolver._LIVE_EMPTY_TTL_SECONDS
        symbol_resolver._live_cache[key] = (stamp - ttl - 1, rows)

    _Search.calls = 0
    monkeypatch.setattr(yf, "Search", _Search)
    assert symbol_resolver._live_lookup("new listing ltd", "IN") == []
    _Search.quotes = [{"symbol": "NEWLIST.NS", "shortname": "New Listing Ltd"}]
    age(("new listing ltd", "IN"))
    rows = symbol_resolver._live_lookup("new listing ltd", "IN")
    assert [i.yahoo_symbol for i in rows] == ["NEWLIST.NS"]
    assert _Search.calls == 2

    age(("new listing ltd", "IN"))
    assert symbol_resolver._live_lookup("new listing ltd", "IN") == rows
    assert _Search.calls == 2


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


def test_live_lookup_passes_an_explicit_short_search_timeout(monkeypatch) -> None:  # noqa: ANN001
    """R15-AGENT-010: yf.Search must not inherit yfinance's timeout=30 default —
    a hung Yahoo would otherwise hold the resolver's worker thread (and its
    caller) for 30 s per miss."""
    import yfinance as yf

    recorded_kwargs: dict[str, object] = {}

    class _KwargsRecordingSearch:
        quotes: list[dict] = []

        def __init__(self, *_a: object, **kwargs: object) -> None:
            recorded_kwargs.update(kwargs)

    monkeypatch.setattr(yf, "Search", _KwargsRecordingSearch)
    symbol_resolver._live_cache.clear()
    symbol_resolver._live_cooldown_until = 0.0
    assert symbol_resolver._live_lookup("zzqx nonexistent co", "IN") == []
    assert recorded_kwargs["timeout"] <= 10


def test_live_lookup_is_wall_clock_bounded_when_search_hangs(monkeypatch) -> None:  # noqa: ANN001
    """R15-AGENT-010 (verdict-corrected): yfinance's cookie/crumb leg
    (_get_cookie_and_crumb / _get_crumb_basic / _get_crumb_csrf) keeps the
    hard-coded 30 s default even when Search's own timeout= kwarg is short —
    the kwarg never reaches those legs. _live_lookup must bound the call by
    wall clock (the pool future's timeout=) instead of trusting the kwarg
    alone, and the cooldown must still arm on that timeout."""
    import threading
    import time

    import yfinance as yf

    release = threading.Event()

    class _HangingSearch:
        quotes: list[dict] = []

        def __init__(self, *_a: object, **_k: object) -> None:
            release.wait()  # released in the test's finally so the worker exits

    monkeypatch.setattr(symbol_resolver, "_LIVE_SEARCH_TIMEOUT_SECONDS", 0.2)
    monkeypatch.setattr(yf, "Search", _HangingSearch)
    symbol_resolver._live_cache.clear()
    symbol_resolver._live_cooldown_until = 0.0

    try:
        start = time.monotonic()
        assert symbol_resolver._live_lookup("zzqx hung co", "IN") == []
        elapsed = time.monotonic() - start
    finally:
        release.set()
    assert elapsed < 1.0, f"took {elapsed:.2f}s, must be wall-clock bounded near 0.2s"
    assert symbol_resolver._live_cooldown_until > time.monotonic(), (
        "a search timeout must arm the cooldown"
    )


def test_live_lookup_hung_misses_do_not_serialize_behind_each_other(monkeypatch) -> None:  # noqa: ANN001
    """The class case the fix was not written against: only 4 pool workers
    back the live-lookup, but 8 concurrent hung misses must not serialise
    behind each other — a still-queued submit is cancelled at its own
    deadline rather than waiting for the workers ahead of it to give up."""
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor

    import yfinance as yf

    release = threading.Event()

    class _HangingSearch:
        quotes: list[dict] = []

        def __init__(self, *_a: object, **_k: object) -> None:
            release.wait()  # released in the test's finally so the workers exit

    monkeypatch.setattr(symbol_resolver, "_LIVE_SEARCH_TIMEOUT_SECONDS", 0.2)
    monkeypatch.setattr(yf, "Search", _HangingSearch)
    symbol_resolver._live_cache.clear()
    symbol_resolver._live_cooldown_until = 0.0

    queries = [f"zzqx hung co {i}" for i in range(8)]
    try:
        start = time.monotonic()
        with ThreadPoolExecutor(max_workers=8) as caller_pool:
            results = list(
                caller_pool.map(lambda q: symbol_resolver._live_lookup(q, "IN"), queries)
            )
        elapsed = time.monotonic() - start
    finally:
        release.set()
    assert results == [[]] * 8
    assert elapsed < 1.2, f"took {elapsed:.2f}s, hung misses must not serialise (budget 0.2 + 1.0s)"


#: The real network seam, captured at import — before conftest's autouse
#: fixture swaps it for an offline stub.
_REAL_US_ISIN_HTTP_GET = symbol_resolver._us_isin_http_get


def test_us_isin_lookup_http_error_is_a_cooldown_not_a_cached_miss(monkeypatch) -> None:  # noqa: ANN001
    """A 429/5xx from the suggest endpoint must not be cached for the process
    as a definite 'no ISIN' — it opens the transport cooldown instead."""
    real_client = httpx.Client
    monkeypatch.setattr(symbol_resolver, "_us_isin_http_get", _REAL_US_ISIN_HTTP_GET)
    monkeypatch.setattr(
        symbol_resolver.httpx,
        "Client",
        lambda **kw: real_client(
            transport=httpx.MockTransport(lambda r: httpx.Response(429)), **kw
        ),
    )
    assert symbol_resolver._us_isin("SIFY") is None
    assert "SIFY" not in symbol_resolver._us_isin_cache
    assert symbol_resolver._us_isin_cooldown_until > 0


def _fake_isin_suggest_response(text: str):  # noqa: ANN201
    return lambda symbol: httpx.Response(200, text=text)


@pytest.mark.parametrize(
    ("symbol", "suggest_text", "expected_isin"),
    [
        # The live one first, the retired one second — take the first exact token.
        (
            "SIFY",
            '"SIFY|US82655M2061|Sify Technologies Limited|Aktie|SIFY.OQ",'
            '"SIFY|US82655M1071|Sify Technologies Limited (Retired)|Aktie|old"',
            "US82655M2061",
        ),
        ("ONC", '"ONC|US07725L1026|BeiGene Ltd|Aktie|ONC.OQ"', "US07725L1026"),
        # The fresh case: not one of the two register-cited tickers.
        ("AAPL", '"AAPL|US0378331005|Apple Inc|Aktie|AAPL.OQ"', "US0378331005"),
        # No exact "<SYMBOL>|" token at all (only a longer ticker's row).
        ("SIFY", '"SIFYX|US1234567890|Some Other Co|Aktie|X"', None),
        # An Indian ISIN must never land on a US namesake (the R13 TCI guard).
        ("SIFY", '"SIFY|INE154A01025|Some Other Co|Aktie|X"', None),
        # Right format, wrong Luhn check digit.
        ("SIFY", '"SIFY|US0378331000|Some Other Co|Aktie|X"', None),
    ],
)
def test_us_isin_lookup_parses_the_first_exact_token(
    monkeypatch,  # noqa: ANN001
    symbol: str,
    suggest_text: str,
    expected_isin: str | None,
) -> None:
    """R15-DATA-059: the lookup takes the FIRST exact ``"<SYMBOL>|<ISIN>|"``
    token (the retired ISIN sorts second), and only a format- and check-digit-
    valid, non-``IN``-prefixed value is accepted."""
    monkeypatch.setattr(
        symbol_resolver, "_us_isin_http_get", _fake_isin_suggest_response(suggest_text)
    )
    assert symbol_resolver._us_isin(symbol) == expected_isin


def test_us_isin_lookup_transport_failure_opens_its_own_cooldown(monkeypatch) -> None:  # noqa: ANN001
    calls = 0

    def _boom(symbol: str) -> httpx.Response:  # noqa: ARG001
        nonlocal calls
        calls += 1
        raise RuntimeError("connection reset")

    monkeypatch.setattr(symbol_resolver, "_us_isin_http_get", _boom)
    assert symbol_resolver._us_isin("SIFY") is None
    assert calls == 1
    # Inside the cooldown window, even a DIFFERENT symbol short-circuits.
    assert symbol_resolver._us_isin("ONC") is None
    assert calls == 1, "cooldown must skip the network entirely"


def test_us_isin_lookup_caches_a_hit_per_symbol(monkeypatch) -> None:  # noqa: ANN001
    calls = 0

    def _search(symbol: str) -> httpx.Response:  # noqa: ARG001
        nonlocal calls
        calls += 1
        return httpx.Response(200, text='"SIFY|US82655M2061|Sify Technologies Limited"')

    monkeypatch.setattr(symbol_resolver, "_us_isin_http_get", _search)
    assert symbol_resolver._us_isin("SIFY") == "US82655M2061"
    assert symbol_resolver._us_isin("SIFY") == "US82655M2061"
    assert calls == 1, "a repeated symbol must not re-hit the network"


def test_resolve_applies_the_looked_up_isin_only_to_the_us_best(monkeypatch) -> None:  # noqa: ANN001
    """R15-DATA-059: ``resolve()`` fills a US best's missing ISIN and keeps the
    matching candidate row in sync, without touching any non-US candidate."""
    monkeypatch.setattr(symbol_resolver, "_live_lookup", _raise_if_network)
    monkeypatch.setattr(
        symbol_resolver,
        "_us_isin_http_get",
        _fake_isin_suggest_response('"AAPL|US0378331005|Apple Inc|Aktie|AAPL.OQ"'),
    )
    res = symbol_resolver.resolve("AAPL", "US")
    assert res.best is not None
    assert res.best.isin == "US0378331005"
    assert res.candidates[0] is res.best


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


# --- R13 identity enrichment: the read-only ISIN / scrip / industry join ------


def test_bse_only_collision_ticker_resolves_with_isin_and_bse_code() -> None:
    """The collision case: BMW Industries Ltd (BSE-only scrip 542669, ISIN
    INE374E01021) is anchored to the ONE real company by its ISIN + numeric
    scrip, not its BMW AG ticker collision. (KSE, the old example, listed on NSE
    in 2026-08 and is no longer BSE-only in the regenerated master.)"""
    best = symbol_resolver.resolve("BMW", "IN").best
    assert best is not None
    assert best.symbol == "BMW"
    assert best.exchange == "BSE"
    assert best.isin == "INE374E01021"
    assert best.bse_code == "542669"


def test_scrip_code_query_carries_identity() -> None:
    """Resolving by the bare BSE scrip code also carries the enriched identity."""
    best = symbol_resolver.resolve("519421", "IN").best
    assert best is not None and best.symbol == "KSE" and best.isin == "INE953E01022"


def test_industry_join_populates_for_a_covered_name() -> None:
    """The sector-map join fills a real industry for a covered large-cap — proof
    the mechanism works even though KSE's own industry is legitimately absent."""
    reliance = symbol_resolver.resolve("RELIANCE", "IN").best
    assert reliance is not None
    assert reliance.industry is not None and reliance.industry.strip()
    assert reliance.isin == "INE002A01018" and reliance.bse_code == "500325"


def test_uncovered_micro_cap_industry_stays_none_never_fabricated() -> None:
    """KSE is present in the sector map with industry_raw None (a group-X data
    gap) — the join surfaces None honestly, never an invented sector."""
    best = symbol_resolver.resolve("KSE", "IN").best
    assert best is not None and best.industry is None


def test_us_ticker_enrichment_is_all_none(monkeypatch) -> None:  # noqa: ANN001
    """A US listing has no India identity data — ``bse_code``/``industry`` stay
    None (India-only fields). ``isin`` is the exception (R15-DATA-059): it is
    filled by the lazy US ISIN lookup, mocked here so the test stays offline."""
    monkeypatch.setattr(
        symbol_resolver,
        "_us_isin_http_get",
        lambda symbol: httpx.Response(200, text='"AAPL|US0378331005|Apple Inc|Aktie|AAPL.OQ"'),
    )
    best = symbol_resolver.resolve("AAPL", "US").best
    assert best is not None
    assert best.isin == "US0378331005"
    assert best.bse_code is None and best.industry is None


def test_enrichment_flows_to_candidates() -> None:
    """Enrichment is applied to every candidate, not just the best."""
    res = symbol_resolver.resolve("ITC", "IN")
    assert res.best is not None and res.best.isin == "INE154A01025"
    for cand in res.candidates:
        # every India candidate that is BSE-listed carries its scrip code
        if cand.exchange in ("NSE", "BSE") and symbol_resolver.is_bse_symbol(cand.symbol):
            assert cand.bse_code is not None, cand.symbol


def test_mixed_collision_candidates_enrich_only_the_indian_row() -> None:
    """The ISIN-leak fix (R13 hardening): TCI collides across exchanges — NSE/BSE
    "TCI" is Transport Corporation of India, but the ticker string ALSO matches a
    US listing. Both land in the same candidate list (a bare ticker query under
    GLOBAL carries every exchange hit); only the Indian row may carry the Indian
    identity join — the US row must keep every enrichment field ``None`` even
    though ``_bse_master()`` has an entry for the bare string "TCI"."""
    res = symbol_resolver.resolve("TCI", "GLOBAL")
    assert res.best is not None
    exchanges = {cand.exchange for cand in res.candidates}
    assert "US" in exchanges, "fixture assumption: TCI collides with a US listing"
    for cand in res.candidates:
        if cand.exchange in ("NSE", "BSE"):
            assert cand.isin is not None, cand.symbol
        else:
            assert cand.isin is None
            assert cand.bse_code is None
            assert cand.industry is None


@pytest.mark.parametrize(
    ("ticker", "bse_isin"),
    [
        ("FOCUS", "INE0DXR01010"),  # Focus Lighting (NSE) / Focus Business Solution (BSE)
        ("KALYANI", "INE0N6U01018"),  # Kalyani Commercials (NSE) / Kalyani Cast-Tech (BSE)
    ],
)
def test_same_ticker_different_companies_keep_their_own_identity(
    ticker: str, bse_isin: str
) -> None:
    """R15-CODE-DATA-001: the NSE and BSE rows under one ticker string are two
    companies. The NSE row must not borrow the BSE company's ISIN / scrip code /
    industry through the ticker-keyed join, and the two exact-ticker rows are a
    residual tie between distinct instruments (an explicit choice, never a silent
    bind of whichever row ranked first). KALYANI is the case the fix was not
    written against."""
    res = symbol_resolver.resolve(ticker, "IN")
    by_exchange = {c.exchange: c for c in res.candidates}
    nse, bse = by_exchange["NSE"], by_exchange["BSE"]
    assert bse.isin == bse_isin and bse.bse_code is not None
    assert nse.isin != bse.isin
    assert nse.bse_code is None and nse.industry is None
    assert res.needs_disambiguation


# ---------------------------------------------------------------------------
# R15-DATA-059 — former-company-name resolution (the bundled former_names.json
# former-name scan lane) + the private/pvt corporate-suffix strip.
# ---------------------------------------------------------------------------


def test_former_name_resolves_a_us_rename(monkeypatch) -> None:  # noqa: ANN001
    """The acceptance case: a query by BeiGene's RETIRED legal name used to miss
    entirely (the resolver only ever compared against CURRENT names) — it now
    binds the listing now named ONC/BeOne Medicines, and the match carries WHICH
    former name it was answered under, never silently indistinguishable from a
    current-name hit. BeiGene, Ltd. also carries an OTC line (BEIGF) that once
    shared the same legal name, so this is a genuine residual tie (R11/D58b) —
    the lead candidate is still the prominent Nasdaq listing (ONC), but an
    explicit choice is correctly required rather than an arbitrary silent bind."""
    monkeypatch.setattr(symbol_resolver, "_live_lookup", _raise_if_network)
    r = symbol_resolver.resolve("BeiGene", "US")
    assert r.best is not None
    assert r.best.symbol == "ONC"
    assert r.best.former_name == "BeiGene, Ltd."
    assert r.needs_disambiguation
    assert r.candidates[0].symbol == "ONC"


def test_us_ticker_resolve_carries_its_most_recent_former_name(monkeypatch) -> None:  # noqa: ANN001
    """R15-DATA-059 regression: a US ticker resolve (not a former-name query)
    used to return before any former-name join, so ONC/SIFY showed
    ``former_name=None`` although the bundled SEC index holds their renames. The
    newest SEC former name that is not a respelling of the current name wins
    (AAPL's "APPLE INC" beside "Apple Inc." is skipped); no Indian field leaks in."""
    monkeypatch.setattr(symbol_resolver, "_live_lookup", _raise_if_network)
    # The US ISIN lookup (R15-DATA-059) is a separate concern from former-name
    # resolution; give it a definite no-token miss so this test stays offline
    # and its own assertions are not coupled to the lookup's own fixtures.
    monkeypatch.setattr(
        symbol_resolver, "_us_isin_http_get", lambda symbol: httpx.Response(200, text="")
    )
    cases = {"ONC": "BeiGene, Ltd.", "SIFY": "SIFY LTD", "AAPL": "APPLE COMPUTER INC"}
    for ticker, former in cases.items():
        best = symbol_resolver.resolve(ticker, "US").best
        assert best is not None and best.symbol == ticker
        assert best.former_name == former
        assert best.isin is None and best.bse_code is None and best.industry is None


def test_former_name_tie_break_prefers_the_prominent_listing(monkeypatch) -> None:  # noqa: ANN001
    """The defect class BeiGene/ONC surfaced (a company with two US listings —
    e.g. a common line and an OTC/preferred line — can carry the same former
    legal name on both rows): the former-name scan must break the tie by the
    SAME master prominence order the current-name scan already uses, not by
    ``former_names.json``'s own (SEC-crawl-ordered) dict iteration. Algonquin
    Power & Utilities is the case the fix was not written against — its common
    stock (AQN) and OTC line (AGQPF) both carry the retired "Algonquin Power
    Income Fund" name, and AGQPF sorts first in the bundled file's own key
    order, so this fails again if the tie-break regresses to that order."""
    monkeypatch.setattr(symbol_resolver, "_live_lookup", _raise_if_network)
    r = symbol_resolver.resolve("Algonquin Power Income Fund", "US")
    assert r.best is not None
    assert r.best.symbol == "AQN"
    assert r.best.former_name == "ALGONQUIN POWER INCOME FUND"


def test_former_name_resolves_an_nse_rename(monkeypatch) -> None:  # noqa: ANN001
    """The class case (an NSE company whose LEGAL NAME changed while its ticker
    symbol never did — distinct from the NSE ticker-rename lane): INFY's name
    changed from "Infosys Technologies Limited" to "Infosys Limited" in 2011, a
    row :mod:`services.nse_symbol_change` never carries (that lane only tracks
    SYMBOL changes)."""
    monkeypatch.setattr(symbol_resolver, "_live_lookup", _raise_if_network)
    r = symbol_resolver.resolve("Infosys Technologies Limited", "IN")
    assert r.best is not None
    assert r.best.symbol == "INFY"
    assert r.best.former_name == "Infosys Technologies Limited"
    assert r.confidence >= 0.99


def test_private_limited_to_limited_ipo_conversion_binds_generically(monkeypatch) -> None:  # noqa: ANN001
    """R15-DATA-059: "private"/"pvt" now strip as a corporate suffix exactly
    like "ltd"/"limited" already do, so the standard Indian private-to-public
    IPO-conversion rename ("X Private Limited" → "X Limited") binds the CURRENT
    listing for every company that made the conversion, not just a one-off
    former-names row per company. TTC (BSE SME, scrip 544303) is the register's
    verified instance: its RHP-era name was "Toss the Coin Private Limited"."""
    monkeypatch.setattr(symbol_resolver, "_live_lookup", _raise_if_network)
    r = symbol_resolver.resolve("Toss the Coin Private Limited", "IN")
    assert r.best is not None
    assert r.best.symbol == "TTC"
    assert r.best.exchange == "BSE"
    assert r.confidence >= 0.99


@pytest.mark.parametrize(
    ("query", "lead", "listed"),
    [
        ("Sify Technologies Ltd (ADR)", None, ("SIFY", "US")),
        # Not written against: the IN lead survives; a better US ADR stays listed.
        ("Infosys Ltd ADR", ("INFY", "NSE"), ("INFY", "US")),
        ("Wipro ADR", ("WIPRO", "NSE"), ("WIT", "US")),
    ],
)
def test_a_better_cross_region_fuzzy_match_keeps_the_last_slot(
    monkeypatch: pytest.MonkeyPatch,
    query: str,
    lead: tuple[str, str] | None,
    listed: tuple[str, str],
) -> None:
    """R15-DATA-058: under IN every IN fuzzy row sorts above a better US row
    (D58c), and the cap cut SIFY (0.91) out behind six weaker IN rows."""
    monkeypatch.setattr(symbol_resolver, "_live_lookup", lambda query, region: [])
    res = symbol_resolver.resolve(query, "IN")
    rows = [(c.symbol, c.exchange) for c in res.candidates]
    assert listed in rows
    assert res.candidates[0].region == "IN"
    if lead is not None:
        assert rows[0] == lead


def test_a_repeat_resolve_reuses_the_name_scan_until_the_masters_refresh(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    """R15-CODE-DATA-002: the banded name scan (~17.9k scores) ran on every
    resolve. A repeat query scores nothing; a master refresh re-arms the scan."""
    import config

    symbol_resolver.reset_caches_for_tests()
    monkeypatch.setattr(symbol_resolver, "_live_lookup", lambda query, region: [])
    real_score = symbol_resolver._name_score
    calls: list[int] = []

    def counting(*args: object) -> object:
        calls.append(1)
        return real_score(*args)  # type: ignore[arg-type]

    monkeypatch.setattr(symbol_resolver, "_name_score", counting)
    first = symbol_resolver.resolve("Tata Steel", "IN")
    scanned = len(calls)
    assert scanned > 10_000
    assert symbol_resolver.resolve("Tata Steel", "IN") == first
    assert len(calls) == scanned

    monkeypatch.setenv(config.DATA_DIR_ENV, str(tmp_path))
    monkeypatch.setattr(
        symbol_resolver,
        "_REFRESH_FETCHERS",
        {"nse_instruments.json": lambda: symbol_resolver._load_master("nse_instruments.json")},
    )
    symbol_resolver.refresh_masters()
    assert symbol_resolver.resolve("Tata Steel", "IN") == first
    assert len(calls) == 2 * scanned


def test_nse_listing_date_is_the_exchange_date_of_listing() -> None:
    """R15-DATA-055: the NSE lists' DATE OF LISTING (three spellings across the
    main board, Emerge and ETF files) lands in the master; a BSE-only scrip has
    none."""
    from services.resolver_masters import regenerate_nse_master

    parsed = [regenerate_nse_master.listing_date(v) for v in ("17-AUG-2026", "02-Sep-26", "")]
    assert parsed == ["2026-08-17", "2026-09-02", None]
    assert symbol_resolver.nse_listing_date("DHOOTTRANS.NS") == "2026-08-17"
    assert symbol_resolver.nse_listing_date("NAPEROL") is None


# --- R15-LEAD-040: resolve/autocomplete run off a dedicated pool ------------


@pytest.mark.asyncio
async def test_resolve_async_does_not_starve_the_shared_to_thread_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """12-way (the default shared-pool size on most boxes) concurrent
    ``resolve_async`` calls, all blocked, must not delay an UNRELATED
    ``asyncio.to_thread`` call — the defect was routing resolve on that same
    shared pool, so N blocked resolves filled every worker and queued
    everything else behind them (R15-LEAD-040)."""
    import asyncio
    import os
    import threading

    event = threading.Event()

    def _blocking_resolve(query: str, region: str) -> symbol_resolver.Resolution:
        event.wait(timeout=5)
        return symbol_resolver.Resolution(query=query, best=None)

    # resolve_async looks ``resolve`` up as a module global at call time, so
    # this monkeypatch (like the production ``monkeypatch.setattr`` pattern)
    # is picked up by tasks already scheduled on ``_RESOLVE_POOL``.
    monkeypatch.setattr(symbol_resolver, "resolve", _blocking_resolve)
    try:
        pool_size = min(32, (os.cpu_count() or 1) + 4)
        tasks = [
            asyncio.create_task(symbol_resolver.resolve_async(f"Q{i}", "US"))
            for i in range(pool_size)
        ]
        # Let every task actually reach the blocking call before checking that
        # an unrelated to_thread call is unaffected.
        await asyncio.sleep(0.05)
        unrelated = await asyncio.wait_for(asyncio.to_thread(lambda: 1), 2)
        assert unrelated == 1
        event.set()
        results = await asyncio.gather(*tasks)
        assert len(results) == pool_size
    finally:
        event.set()


def test_no_shared_pool_to_thread_call_sites_for_symbol_resolver() -> None:
    """Class pin: every call site — including ``autocomplete``, which the
    register entry never named — must route through ``resolve_async`` /
    ``autocomplete_async`` on the dedicated ``_RESOLVE_POOL``, never
    ``asyncio.to_thread(symbol_resolver.*, ...)`` on the shared default pool.
    An AST audit over every module under ``routers``/``services``, not a grep
    of the five sites the entry named, so a sixth call site added later trips
    it too."""
    import ast
    from pathlib import Path

    sidecar_root = Path(__file__).resolve().parents[1]
    offenders: list[str] = []
    for base in ("routers", "services"):
        for path in (sidecar_root / base).rglob("*.py"):
            tree = ast.parse(path.read_text(), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                is_to_thread = (
                    isinstance(func, ast.Attribute)
                    and func.attr == "to_thread"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "asyncio"
                )
                if not is_to_thread or not node.args:
                    continue
                first_arg = node.args[0]
                if (
                    isinstance(first_arg, ast.Attribute)
                    and isinstance(first_arg.value, ast.Name)
                    and first_arg.value.id == "symbol_resolver"
                ):
                    offenders.append(f"{path.relative_to(sidecar_root)}:{node.lineno}")
    assert offenders == []
