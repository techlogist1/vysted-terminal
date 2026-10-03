"""R15 final pass, data-fundamentals round: money-relevant figure fixes."""

from __future__ import annotations

import asyncio
from datetime import date

import pytest

from models.fundamentals import Fundamentals
from services import correctness_gate
from services.exchange_financials import FiledPeriod, FiledPeriods


def _quarters(*eps: float, net: float = 305_000.0) -> FiledPeriods:
    ends = (date(2026, 6, 30), date(2026, 3, 31), date(2025, 12, 31), date(2025, 9, 30))
    starts = (date(2026, 4, 1), date(2026, 1, 1), date(2025, 10, 1), date(2025, 7, 1))
    return FiledPeriods(
        venue="bse",
        basis="standalone",
        periods=tuple(
            FiledPeriod(s, e, 10_000_000.0, net, q)
            for s, e, q in zip(starts, ends, eps, strict=True)
        ),
    )


# --- R15-FINAL-003: P/E follows the served (exchange-filed) EPS ---------------


def test_sunrajdi_pe_is_rederived_on_the_filed_eps() -> None:
    provider = Fundamentals(
        symbol="SUNRAJDI.BO",
        provider="yfinance",
        currency="INR",
        ratio_price=12.44,
        eps=0.08,
        pe_ratio=155.5,
        net_income_ttm=470_000.0,
        shares_outstanding=5_330_400.0,
    )
    gated = correctness_gate.validate_fundamentals(provider, "SUNRAJDI.BO", "IN")
    assert gated.field_meta["pe_ratio"].status == "flagged"  # the stale 141.1 reason

    served = correctness_gate.overlay_filed_periods(gated, _quarters(0.05, 0.06, 0.06, 0.06))

    assert served.eps == pytest.approx(0.23)
    assert served.pe_ratio == pytest.approx(12.44 / 0.23)
    assert round(served.pe_ratio, 1) == 54.1
    meta = served.field_meta["pe_ratio"]
    assert meta.status == "ok"
    assert meta.provider == "derived"
    assert "exchange-filed TTM EPS" in (meta.basis_note or "")
    assert meta.reason is None
    assert "141.1" not in str(served.field_meta)


def test_a_filed_eps_above_the_providers_lowers_the_pe() -> None:
    provider = Fundamentals(
        symbol="ICON.NS",
        provider="yfinance",
        currency="INR",
        ratio_price=80.0,
        eps=2.0,
        pe_ratio=40.0,
    )
    served = correctness_gate.overlay_filed_periods(provider, _quarters(1.0, 1.0, 1.0, 1.0))
    assert served.pe_ratio == pytest.approx(20.0)
    assert served.field_meta["pe_ratio"].provider == "derived"


def test_a_non_positive_filed_eps_withholds_the_providers_pe() -> None:
    provider = Fundamentals(
        symbol="ICON.NS",
        provider="yfinance",
        currency="INR",
        ratio_price=80.0,
        eps=2.0,
        pe_ratio=40.0,
    )
    served = correctness_gate.overlay_filed_periods(provider, _quarters(-1.0, 0.2, 0.2, 0.1))
    assert served.pe_ratio is None
    assert served.field_meta["pe_ratio"].status == "withheld"


# --- R15-FINAL-024: no ownership flag inside the 3pp band ---------------------


def _amal_exchange(institutions: float):  # noqa: ANN202
    from services.ownership_check import ExchangeOwnership

    return ExchangeOwnership(
        promoter_percent=63.4,
        institutions_percent=institutions,
        public_percent=36.6,
        as_of_quarter="2026-06-30",
        source="BSE",
    )


def test_zero_beside_a_small_filed_institutions_figure_is_not_flagged() -> None:
    f = Fundamentals(
        symbol="AMAL.NS",
        provider="yfinance",
        held_percent_insiders=0.634,
        held_percent_institutions=0.0,
    )
    out = correctness_gate.reconcile_ownership(f, _amal_exchange(0.03))
    assert (out.field_meta or {}).get("held_percent_institutions") is None


def test_zero_beside_a_large_filed_institutions_figure_is_flagged_truthfully() -> None:
    f = Fundamentals(
        symbol="AMAL.NS",
        provider="yfinance",
        held_percent_insiders=0.634,
        held_percent_institutions=0.0,
    )
    out = correctness_gate.reconcile_ownership(f, _amal_exchange(12.0))
    meta = out.field_meta["held_percent_institutions"]
    assert meta.status == "flagged"
    assert "0.00%" in meta.reason and "12.00%" in meta.reason and "beyond 3pp" in meta.reason


# --- R15-FINAL-009: missing market cap derived from the BSE master count -------


def _no_filings(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import exchange_financials

    async def none(_listing: str) -> None:
        return None

    monkeypatch.setattr(exchange_financials, "get_filed_periods", none)
    correctness_gate.reset_witness_cache_for_tests()


def _served(symbol: str, **fields: float) -> Fundamentals:
    return Fundamentals(symbol=symbol, provider="nse", currency="INR", ratio_price=703.0, **fields)


def test_amal_ns_market_cap_is_derived_from_the_master_share_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services import market_cap_witness

    _no_filings(monkeypatch)
    master = market_cap_witness._lookup("AMAL.NS")
    assert master is not None and master.scrip_code == "506597"

    out = asyncio.run(correctness_gate.apply_witnesses(_served("AMAL.NS")))

    assert out.shares_outstanding == master.shares_outstanding
    assert out.market_cap == pytest.approx(703.0 * master.shares_outstanding)
    meta = out.field_meta["market_cap"]
    assert meta.status == "ok" and meta.provider == "derived"
    assert "master share count" in meta.basis_note and "BSE ListOfScripData" in meta.basis_note
    assert out.field_meta["shares_outstanding"].provider == "derived"


def test_a_served_market_cap_is_never_overridden(monkeypatch: pytest.MonkeyPatch) -> None:
    _no_filings(monkeypatch)
    out = asyncio.run(
        correctness_gate.apply_witnesses(
            _served("AMAL.NS", market_cap=8_690_951_168.0, shares_outstanding=12_362_662.0)
        )
    )
    assert out.market_cap == 8_690_951_168.0
    assert out.shares_outstanding == 12_362_662.0
    assert out.field_meta is None


def test_another_companys_bse_row_under_the_same_ticker_is_not_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NSE ZEAL (Zeal Global) vs BSE ZEAL (Zeal Aqua): the master row keyed by
    the ticker is the other company's share count."""
    _no_filings(monkeypatch)
    out = asyncio.run(correctness_gate.apply_witnesses(_served("ZEAL.NS")))
    assert out.market_cap is None
    assert out.shares_outstanding is None
