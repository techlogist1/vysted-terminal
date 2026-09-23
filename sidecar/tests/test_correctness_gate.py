"""Pass B (B1) — the correctness gate (FR-063): reject wrong/empty/mismatched data."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from models.fundamentals import FieldMeta, Fundamentals
from models.market import OHLCVBar, OHLCVSeries, Quote
from services import correctness_gate
from services.correctness_gate import CorrectnessError


def _quote(symbol: str, price: float, *, days_old: int = 0) -> Quote:
    return Quote(
        symbol=symbol,
        price=price,
        change=0.0,
        change_percent=0.0,
        currency="INR",
        timestamp=datetime.now(tz=UTC) - timedelta(days=days_old),
        provider="nse",
    )


def _series(symbol: str, last_close: float, n: int = 3) -> OHLCVSeries:
    bars = [
        OHLCVBar(
            timestamp=datetime.now(tz=UTC) - timedelta(days=n - i),
            open=last_close,
            high=last_close,
            low=last_close,
            close=last_close,
            volume=1000.0,
        )
        for i in range(n)
    ]
    return OHLCVSeries(symbol=symbol, timeframe="1d", bars=bars, provider="nse")


def test_symbols_match_normalises_suffix_and_dash() -> None:
    assert correctness_gate.symbols_match("GOLDBEES", "GOLDBEES.NS")
    assert correctness_gate.symbols_match("GOLDBEES", "GOLDBEES-NS")  # yfinance dash form
    assert correctness_gate.symbols_match("BRK.B", "BRK-B")
    assert correctness_gate.symbols_match("aapl", "AAPL")
    assert not correctness_gate.symbols_match("AAPL", "MSFT")
    assert not correctness_gate.symbols_match("CNS", "C")  # does not over-strip "NS"


def test_validate_quote_accepts_good() -> None:
    q = _quote("GOLDBEES", 128.5)
    assert correctness_gate.validate_quote(q, "GOLDBEES", "IN") is q
    # Matches across the .NS form the resolver may have requested.
    assert correctness_gate.validate_quote(q, "GOLDBEES.NS", "IN") is q


def test_validate_quote_rejects_non_positive() -> None:
    with pytest.raises(CorrectnessError):
        correctness_gate.validate_quote(_quote("GOLDBEES", 0.0), "GOLDBEES", "IN")
    with pytest.raises(CorrectnessError):
        correctness_gate.validate_quote(_quote("GOLDBEES", -5.0), "GOLDBEES", "IN")


def test_validate_quote_rejects_symbol_mismatch() -> None:
    with pytest.raises(CorrectnessError):
        correctness_gate.validate_quote(_quote("WRONG", 100.0), "GOLDBEES", "IN")


def test_validate_quote_rejects_broken_feed_staleness() -> None:
    with pytest.raises(CorrectnessError):
        correctness_gate.validate_quote(_quote("GOLDBEES", 100.0, days_old=40), "GOLDBEES", "IN")


def test_validate_series_rejects_empty_and_mismatch() -> None:
    empty = OHLCVSeries(symbol="GOLDBEES", timeframe="1d", bars=[], provider="nse")
    with pytest.raises(CorrectnessError):
        correctness_gate.validate_series(empty, "GOLDBEES", "IN")
    with pytest.raises(CorrectnessError):
        correctness_gate.validate_series(_series("WRONG", 100.0), "GOLDBEES", "IN")


def test_validate_series_accepts_old_but_valid() -> None:
    # Staleness is a label on a series, not a rejection — an old-but-valid series passes.
    old = _series("GOLDBEES", 100.0)
    old.bars[-1] = OHLCVBar(
        timestamp=datetime(2024, 1, 2, tzinfo=UTC),
        open=100,
        high=100,
        low=100,
        close=100,
        volume=1,
    )
    assert correctness_gate.validate_series(old, "GOLDBEES", "IN") is old


def test_validate_series_rejects_an_all_flat_zero_volume_series() -> None:
    # R15-LIFECYCLE-004: open = high = low = close with zero volume on every bar
    # is a parser filling missing fields (or no trade at all), never a price
    # history. One real bar in the series keeps it.
    flat = _series("GOLDBEES", 100.0, n=5)
    flat.bars = [b.model_copy(update={"volume": 0.0}) for b in flat.bars]
    with pytest.raises(CorrectnessError, match="flat with zero volume"):
        correctness_gate.validate_series(flat, "GOLDBEES", "IN")

    traded = flat.model_copy(deep=True)
    traded.bars[2] = traded.bars[2].model_copy(update={"high": 101.0, "volume": 10.0})
    assert correctness_gate.validate_series(traded, "GOLDBEES", "IN") is traded


# ---------------------------------------------------------------------------
# validate_fundamentals — identity + numeric plausibility bounds (R13, D4)
# ---------------------------------------------------------------------------


def _fund(symbol: str = "KSE.BO", provider: str = "yfinance", **fields: object) -> Fundamentals:
    return Fundamentals(symbol=symbol, provider=provider, **fields)  # type: ignore[arg-type]


def test_validate_fundamentals_rejects_symbol_mismatch() -> None:
    """Identity is still fatal — a wrong-instrument result advances providers."""
    with pytest.raises(CorrectnessError):
        correctness_gate.validate_fundamentals(_fund(symbol="WRONG.BO"), "KSE", "IN")


def test_validate_fundamentals_passes_plausible_result_untouched() -> None:
    """A wholly-plausible result is returned as the SAME object (identity), so
    callers keep using it inline and nothing is needlessly copied."""
    good = _fund(
        pe_ratio=6.93,
        eps=32.9,  # implied price ~228, inside the band
        fifty_two_week_high=284.9,
        fifty_two_week_low=174.0,
        dividend_yield=0.03,
        held_percent_insiders=0.489,
    )
    assert correctness_gate.validate_fundamentals(good, "KSE.BO", "IN") is good


def test_validate_fundamentals_withholds_absurd_ownership_fraction() -> None:
    """An ownership fraction of 84.55 (i.e. 8455%) is impossible for a [0,1]
    fraction — WITHHELD (nulled) with a recorded reason, not a whole-result reject."""
    f = _fund(pe_ratio=6.93, held_percent_institutions=84.55)
    out = correctness_gate.validate_fundamentals(f, "KSE.BO", "IN")
    assert out.held_percent_institutions is None  # nulled
    assert out.pe_ratio == 6.93  # the good field survives
    assert out.field_meta is not None
    meta = out.field_meta["held_percent_institutions"]
    assert meta.status == "withheld"
    assert "8455" in meta.reason or "84.55" in meta.reason


def test_validate_fundamentals_withholds_ambiguous_dividend_yield() -> None:
    """A dividend yield of 0.55 as a FRACTION (55%) exceeds the plausible bound
    (0.25) → withheld as ambiguous-unit."""
    out = correctness_gate.validate_fundamentals(_fund(dividend_yield=0.55), "KSE.BO", "IN")
    assert out.dividend_yield is None
    assert out.field_meta["dividend_yield"].status == "withheld"


def test_validate_fundamentals_withholds_inverted_52_week_pair() -> None:
    """A 52-week high below the low is internally inconsistent → both withheld."""
    f = _fund(fifty_two_week_high=100.0, fifty_two_week_low=200.0)
    out = correctness_gate.validate_fundamentals(f, "KSE.BO", "IN")
    assert out.fifty_two_week_high is None
    assert out.fifty_two_week_low is None
    assert out.field_meta["fifty_two_week_high"].status == "withheld"
    assert out.field_meta["fifty_two_week_low"].status == "withheld"


def test_validate_fundamentals_flags_price_13x_outside_52_week_range() -> None:
    """A pe x eps implied price of 2,492 sits ~13x outside a 174–285 52-week band
    → the 52-week pair is FLAGGED but KEPT (a single field can't arbitrate which
    of price/ratios/pair is wrong)."""
    f = _fund(
        pe_ratio=10.0,
        eps=249.2,  # implied price 2492
        fifty_two_week_high=284.9,
        fifty_two_week_low=174.0,
    )
    out = correctness_gate.validate_fundamentals(f, "KSE.BO", "IN")
    # Kept, not withheld.
    assert out.fifty_two_week_high == 284.9
    assert out.fifty_two_week_low == 174.0
    meta = out.field_meta["fifty_two_week_high"]
    assert meta.status == "flagged"
    assert meta.reason is not None and "outside" in meta.reason


def test_validate_fundamentals_flags_market_cap_divergence() -> None:
    """market_cap far from (pe x eps) x shares outstanding → market cap FLAGGED,
    kept (not withheld)."""
    f = _fund(
        pe_ratio=10.0,
        eps=20.0,  # implied price 200
        shares_outstanding=1_000_000_000,  # implied cap 2.0e11
        market_cap=5_000_000_000,  # 25x too small → divergence
    )
    out = correctness_gate.validate_fundamentals(f, "KSE.BO", "IN")
    assert out.market_cap == 5_000_000_000  # kept
    meta = out.field_meta["market_cap"]
    assert meta.status == "flagged"
    assert meta.reason is not None and "diverges" in meta.reason


def test_validate_fundamentals_merges_onto_provider_provenance() -> None:
    """The gate MERGES onto a provider-populated field_meta: a withheld field
    flips ok→withheld while untouched fields keep their provider provenance."""
    f = _fund(
        pe_ratio=6.93,
        held_percent_institutions=84.55,
        field_meta={
            "pe_ratio": FieldMeta(
                status="ok", provider="yfinance", as_of="2026-07-10T00:00:00+00:00"
            ),
            "held_percent_institutions": FieldMeta(
                status="ok", provider="yfinance", as_of="2026-07-10T00:00:00+00:00"
            ),
        },
    )
    out = correctness_gate.validate_fundamentals(f, "KSE.BO", "IN")
    # Untouched field keeps its provider provenance intact.
    assert out.field_meta["pe_ratio"].status == "ok"
    assert out.field_meta["pe_ratio"].as_of == "2026-07-10T00:00:00+00:00"
    # Withheld field flips status but the provider/as_of provenance survives.
    withheld = out.field_meta["held_percent_institutions"]
    assert withheld.status == "withheld"
    assert withheld.provider == "yfinance"
    assert withheld.as_of == "2026-07-10T00:00:00+00:00"


# ---------------------------------------------------------------------------
# R15-DATA-005: the share basis — market cap / price vs shares outstanding
# ---------------------------------------------------------------------------

_PER_SHARE_FIELDS = ("shares_outstanding", "book_value", "price_to_book")


def test_share_basis_divergence_flags_the_per_share_fields() -> None:
    """VERTEX (R15 battery): 74.0M shares (pre-rights) vs the 148.0M implied by
    its own market cap at the ratio price 3.27 — BVPS 1.369 and P/B 2.3886 sit on
    the stale count, so all three are flagged, kept, with both counts named."""
    f = _fund(
        symbol="VERTEX.BO",
        shares_outstanding=74_012_189,
        market_cap=484_039_744,
        ratio_price=3.27,
        book_value=1.369,
        price_to_book=2.3886,
    )
    out = correctness_gate.validate_fundamentals(f, "VERTEX.BO", "IN")
    for field_name in _PER_SHARE_FIELDS:
        meta = out.field_meta[field_name]
        assert meta.status == "flagged"
        assert "74,012,189" in meta.reason and "148,0" in meta.reason
    assert out.book_value == 1.369  # never substituted


def test_share_basis_covers_a_loss_maker_without_trailing_pe() -> None:
    """A case the fix was not written against: a loss-maker (no P/E, negative
    EPS) with a stale share count 14% off. The old pe x eps price proxy was blind
    to it; the ratio price is not."""
    f = _fund(
        symbol="LOSSCO.NS",
        pe_ratio=None,
        eps=-2.5,
        ratio_price=40.0,
        market_cap=4_000_000_000,  # implies 100M shares
        shares_outstanding=86_000_000,
        book_value=55.0,
        price_to_book=0.727,
    )
    out = correctness_gate.validate_fundamentals(f, "LOSSCO.NS", "IN")
    for field_name in _PER_SHARE_FIELDS:
        assert out.field_meta[field_name].status == "flagged"


def test_consistent_share_basis_is_untouched() -> None:
    f = _fund(
        symbol="VERTEX.BO",
        shares_outstanding=148_024_378,
        market_cap=484_039_744,
        ratio_price=3.27,
        book_value=0.684,
        price_to_book=4.78,
    )
    assert correctness_gate.validate_fundamentals(f, "VERTEX.BO", "IN") is f


# ---------------------------------------------------------------------------
# R15-DATA-013: trailing EPS vs the payload's net income / shares outstanding
# ---------------------------------------------------------------------------


def test_stale_eps_flags_eps_and_pe_with_the_payload_implied_figure() -> None:
    """DAL (R15 battery): trailingEps 8.9 / P/E 5.6 while the same payload's net
    income 10.2M over 5.01M shares gives 2.04 (P/E ~24.5 at 49.88)."""
    f = _fund(
        symbol="DAL.BO",
        eps=8.9,
        pe_ratio=5.6044946,
        net_income_ttm=10_200_000,
        shares_outstanding=5_010_000,
        ratio_price=49.88,
    )
    out = correctness_gate.validate_fundamentals(f, "DAL.BO", "IN")
    assert out.eps == 8.9 and out.pe_ratio == 5.6044946  # kept, never substituted
    for field_name in ("eps", "pe_ratio"):
        meta = out.field_meta[field_name]
        assert meta.status == "flagged"
        assert "2.04" in meta.reason and "24.5" in meta.reason


def test_stale_eps_on_a_second_listing_is_flagged() -> None:
    """A case the fix was not written against: SMR's 5.58 is a full fiscal year
    behind the 13.27 its own payload implies."""
    f = _fund(
        symbol="SMR.NS",
        eps=5.58,
        pe_ratio=17.02509,
        net_income_ttm=247_484_992,
        shares_outstanding=18_653_743,
        ratio_price=95.0,
    )
    out = correctness_gate.validate_fundamentals(f, "SMR.NS", "IN")
    assert out.field_meta["eps"].status == "flagged"
    assert "13.27" in out.field_meta["eps"].reason
    assert out.field_meta["pe_ratio"].status == "flagged"


def test_consistent_eps_is_untouched() -> None:
    f = _fund(
        symbol="SMR.NS",
        eps=13.1,
        pe_ratio=7.25,
        net_income_ttm=247_484_992,
        shares_outstanding=18_653_743,
        ratio_price=95.0,
    )
    assert correctness_gate.validate_fundamentals(f, "SMR.NS", "IN") is f


# ---------------------------------------------------------------------------
# R15-DATA-033: a NaN price never passes the gate (``nan <= 0`` is False)
# ---------------------------------------------------------------------------


def _two_lanes(monkeypatch: pytest.MonkeyPatch, model_key: str, bad: object, good: object) -> None:
    """Replace the registry's providers with a first lane serving ``bad`` and a
    second serving ``good``, both for any equity request."""
    from services import provider_registry
    from services.provider_registry import ProviderDeclaration

    monkeypatch.setattr(
        provider_registry,
        "_PROVIDERS",
        (
            ProviderDeclaration(id="first", rank=10, serves={model_key: lambda *a: bad}),
            ProviderDeclaration(id="second", rank=20, serves={model_key: lambda *a: good}),
        ),
    )


def test_nan_quote_falls_through_to_the_next_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import provider_registry

    nan_quote = _quote("GOLDBEES", float("nan")).model_copy(update={"provider": "first"})
    good = _quote("GOLDBEES", 128.5).model_copy(update={"provider": "second"})
    _two_lanes(monkeypatch, "quote", nan_quote, good)
    assert provider_registry.get_quote("GOLDBEES", region="IN") is good


def test_nan_last_close_falls_through_to_the_next_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services import provider_registry

    nan_series = _series("GOLDBEES", float("nan")).model_copy(update={"provider": "first"})
    good = _series("GOLDBEES", 128.5).model_copy(update={"provider": "second"})
    _two_lanes(monkeypatch, "ohlcv", nan_series, good)
    assert provider_registry.get_history("GOLDBEES", "1d", region="IN") is good


def test_institutions_flag_names_the_merged_split_lane_and_quarter() -> None:
    """R15-RESEARCH-011, the gate's copy of the provenance: an institutions
    figure merged from the BSE XBRL of March is not the NSE June filing's."""
    from services.ownership_check import ExchangeOwnership

    exchange = ExchangeOwnership(
        promoter_percent=20.31,
        institutions_percent=42.9,
        public_percent=79.69,
        as_of_quarter="2026-06-30",
        source="NSE",
        institutions_source="BSE",
        institutions_as_of="2026-03-31",
    )
    f = _fund(symbol="SIL.NS", held_percent_insiders=0.2031, held_percent_institutions=0.05)
    out = correctness_gate.reconcile_ownership(f, exchange)
    reason = out.field_meta["held_percent_institutions"].reason
    assert "the BSE shareholding filing for the quarter ended 2026-03-31" in reason
    assert out.field_meta.get("held_percent_insiders") is None  # 20.31 vs 20.31


# ---------------------------------------------------------------------------
# R15-LEAD-002: witness inputs are cached per listing, flags recomputed
# ---------------------------------------------------------------------------


def _count_witness_fetches(
    monkeypatch: pytest.MonkeyPatch, *, fail: bool = False
) -> dict[str, int]:
    """Stub the four witness fetches with counters (``fail`` → each one fails)."""
    from datetime import date

    from models.fundamentals import IncomeStatement
    from services import ownership_check, yfinance_provider
    from services.errors import ProviderError

    calls = {"ownership": 0, "income": 0, "quarters": 0, "equity": 0}

    def counted(name: str, value: object) -> object:
        def fetch(symbol: str) -> object:  # noqa: ARG001
            calls[name] += 1
            if fail:
                raise ProviderError(f"yfinance {name} failed: upstream 500")
            return value

        return fetch

    async def ownership(symbol: str) -> object:  # noqa: ARG001
        calls["ownership"] += 1
        return (
            None
            if fail
            else ownership_check.ExchangeOwnership(55.0, 10.0, 45.0, "2026-06-30", "NSE")
        )

    annual = IncomeStatement(symbol="TCS.NS", periods=["2026"], lines=[], provider="yfinance")
    quarters = [date(2026, 6, 30), date(2026, 3, 31), date(2025, 12, 31), date(2025, 9, 30)]
    monkeypatch.setattr(ownership_check, "get_exchange_ownership", ownership)
    monkeypatch.setattr(yfinance_provider, "get_income_statement", counted("income", annual))
    monkeypatch.setattr(
        yfinance_provider, "get_quarterly_period_ends", counted("quarters", quarters)
    )
    monkeypatch.setattr(
        yfinance_provider, "get_newest_equity", counted("equity", (date(2026, 6, 30), 9.0e11))
    )
    return calls


def _witnessed_twice() -> Fundamentals:
    import asyncio

    f = _fund(
        symbol="TCS.NS",
        held_percent_insiders=0.72,
        revenue_ttm=2.5e12,
        book_value=250.0,
        shares_outstanding=3.6e9,
    )
    asyncio.run(correctness_gate.apply_witnesses(f))
    return asyncio.run(correctness_gate.apply_witnesses(f))


def test_witness_inputs_are_fetched_once_within_the_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _count_witness_fetches(monkeypatch)
    second = _witnessed_twice()
    assert calls == {"ownership": 1, "income": 1, "quarters": 1, "equity": 1}
    # The flags are still recomputed from the cached inputs on the second call.
    assert second.field_meta["held_percent_insiders"].status == "flagged"


def test_witness_inputs_are_fetched_again_after_the_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    """A case the fix was not written against: an expired entry is re-fetched."""
    calls = _count_witness_fetches(monkeypatch)
    monkeypatch.setattr(correctness_gate, "_WITNESS_TTL_SECONDS", 0.0)
    _witnessed_twice()
    assert calls == {"ownership": 2, "income": 2, "quarters": 2, "equity": 2}


def test_a_failed_witness_fetch_is_not_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _count_witness_fetches(monkeypatch, fail=True)
    _witnessed_twice()
    assert calls == {"ownership": 2, "income": 2, "quarters": 2, "equity": 2}


# ---------------------------------------------------------------------------
# R15-DATA-015/016: the 52-week range is witnessed against both Indian venues
# ---------------------------------------------------------------------------

_TODAY = datetime(2026, 9, 23, tzinfo=UTC)


def _daily(start: datetime, days: int, high: float, low: float, **plant: float) -> OHLCVSeries:
    """Weekday bars from ``start`` for ``days`` calendar days in a flat ``low``..``high``
    band; ``plant`` puts an ISO-date ``high_<date>``/``low_<date>`` extreme on one day."""
    bars = []
    for i in range(days):
        ts = start + timedelta(days=i)
        if ts.weekday() >= 5:
            continue
        day = ts.date().isoformat()
        h = plant.get(f"high_{day}", high)
        lo = plant.get(f"low_{day}", low)
        bars.append(OHLCVBar(timestamp=ts, open=lo, high=h, low=lo, close=h, volume=500.0))
    return OHLCVSeries(symbol="X", timeframe="1d", bars=bars, provider="bse")


def _venues(monkeypatch: pytest.MonkeyPatch, nse: object, bse: object) -> object:
    import asyncio

    from services.research import range_check

    def serve(result: object) -> object:
        def fetch(symbol: str) -> object:  # noqa: ARG001
            if isinstance(result, Exception):
                raise result
            return result

        return fetch

    monkeypatch.setattr(range_check, "_fetch_nse_venue", serve(nse))
    monkeypatch.setattr(range_check, "_fetch_bse_venue", serve(bse))
    return asyncio.run(range_check.get_venue_history("ELCIDIN.NS"))


def test_52w_low_printed_on_the_other_venue_is_flagged(monkeypatch: pytest.MonkeyPatch) -> None:
    """ELCIDIN: Yahoo's .NS range (1,02,210-1,37,000) covers NSE since the
    2026-04-20 listing; BSE printed 87,003 inside the year."""
    nse = _daily(datetime(2026, 4, 20, tzinfo=UTC), 156, 137000.0, 102210.0)
    bse = _daily(
        _TODAY - timedelta(days=364),
        364,
        130000.0,
        104000.0,
        **{"low_2025-12-15": 87003.0, "high_2026-02-02": 144500.0},
    )
    history = _venues(monkeypatch, nse, bse)
    f = _fund(symbol="ELCIDIN.NS", fifty_two_week_high=137000.0, fifty_two_week_low=102210.0)
    out = correctness_gate.reconcile_52w_range(f, history, today=_TODAY.date())

    assert out.fifty_two_week_low == 102210.0  # disclosed, never replaced
    low = out.field_meta["fifty_two_week_low"]
    assert low.status == "flagged"
    assert "87,003.00" in low.reason and "NSE + BSE" in low.reason
    assert "fifty_two_week_high" not in out.field_meta  # 1,37,000 is within 10% of 1,44,500


def test_short_exchange_series_flags_only_an_extreme_outside_the_range() -> None:
    """Three months of bars cannot contradict a provider high set before them,
    but a low below the provider's is a print the provider missed."""
    start = datetime(2026, 6, 22, tzinfo=UTC)
    bars = _daily(start, 90, 120.0, 95.0, **{"low_2026-07-01": 80.0}).bars
    f = _fund(symbol="X.NS", fifty_two_week_high=150.0, fifty_two_week_low=100.0)
    out = correctness_gate.reconcile_52w_range(f, (bars, ["NSE"]), today=_TODAY.date())

    assert "fifty_two_week_high" not in out.field_meta
    assert out.field_meta["fifty_two_week_low"].status == "flagged"
    assert "since 2026-06-22" in out.field_meta["fifty_two_week_low"].reason


def test_agreeing_dual_listed_range_is_untouched(monkeypatch: pytest.MonkeyPatch) -> None:
    year = _TODAY - timedelta(days=364)
    history = _venues(
        monkeypatch,
        _daily(year, 364, 1600.0, 1115.0),
        _daily(year, 364, 1601.0, 1114.0),
    )
    f = _fund(symbol="RELIANCE.NS", fifty_two_week_high=1608.8, fifty_two_week_low=1114.85)
    assert correctness_gate.reconcile_52w_range(f, history, today=_TODAY.date()) is f


def test_no_trade_in_52_weeks_withholds_the_range(monkeypatch: pytest.MonkeyPatch) -> None:
    """DAL.BO: last trade 2025-03-12, no exchange bar in the year; Yahoo still
    serves a 52-week range off its forward-filled bars."""
    import asyncio

    from services import dividend_history
    from services.research import range_check

    async def no_history(symbol: str) -> None:  # noqa: ARG001
        return None

    async def no_dividends(symbol: str) -> None:  # noqa: ARG001
        return None

    monkeypatch.setattr(range_check, "get_venue_history", no_history)
    monkeypatch.setattr(dividend_history, "get_dividend_ttm", no_dividends)
    correctness_gate.reset_witness_cache_for_tests()
    f = _fund(
        symbol="DAL.BO",
        fifty_two_week_high=46.58,
        fifty_two_week_low=46.58,
        ratio_price=46.58,
        field_meta={
            "ratio_price": FieldMeta(
                status="ok", provider="yfinance", as_of="2025-03-12T03:58:51+00:00"
            )
        },
    )
    out = asyncio.run(correctness_gate.apply_witnesses(f))
    for name in ("fifty_two_week_high", "fifty_two_week_low"):
        assert getattr(out, name) is None
        assert out.field_meta[name].status == "withheld"
        assert "last trade 2025-03-12" in out.field_meta[name].reason
