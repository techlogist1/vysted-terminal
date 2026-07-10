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
    assert meta.status == "ok"
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
    assert meta.status == "ok"
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
