"""R15 final pass, data-fundamentals round: money-relevant figure fixes."""

from __future__ import annotations

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
