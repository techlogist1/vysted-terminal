"""Fixed-rate bond pricing tests.

Reference values:

* A bond priced at YTM == coupon rate should price at par (clean = face).
* A bond priced at YTM < coupon rate should price at a premium (clean > face).
* A bond priced at YTM > coupon rate should price at a discount (clean < face).
* Macaulay duration < years-to-maturity.
* Modified duration ≈ Macaulay / (1 + YTM/freq).
* Convexity > 0.
"""

from __future__ import annotations

from datetime import date

import pytest

from models.quant import BondPricingRequest
from services.quant import bonds


def _make_req(**overrides: object) -> BondPricingRequest:
    base = {
        "face_value": 1000.0,
        "coupon_rate": 0.05,
        "coupons_per_year": 2,
        "issue_date": date(2026, 5, 16),
        "maturity_date": date(2036, 5, 16),
        "settlement_date": date(2026, 5, 16),
        "yield_to_maturity": 0.05,
    }
    base.update(overrides)
    return BondPricingRequest.model_validate(base)


def test_par_bond_prices_at_face() -> None:
    """YTM == coupon → clean price == face value."""
    result = bonds.price_bond(_make_req(yield_to_maturity=0.05))
    assert result.clean_price == pytest.approx(1000.0, rel=1e-4)


def test_premium_bond_when_ytm_below_coupon() -> None:
    """5 % coupon priced at 4 % YTM → premium."""
    result = bonds.price_bond(_make_req(yield_to_maturity=0.04))
    assert result.clean_price > 1000.0
    # 10y bond at 5 % coupon @ 4 % YTM ≈ $1081.76 per $1000 face.
    assert result.clean_price == pytest.approx(1081.76, abs=1.0)


def test_discount_bond_when_ytm_above_coupon() -> None:
    """5 % coupon priced at 6 % YTM → discount."""
    result = bonds.price_bond(_make_req(yield_to_maturity=0.06))
    assert result.clean_price < 1000.0


def test_macaulay_duration_less_than_maturity() -> None:
    result = bonds.price_bond(_make_req())
    # Maturity = 10 years; Macaulay duration must be strictly less.
    assert 0 < result.duration < 10.0


def test_modified_duration_approx_macaulay_over_1_plus_y() -> None:
    """Modified ≈ Macaulay / (1 + YTM / freq)."""
    result = bonds.price_bond(_make_req(yield_to_maturity=0.05))
    expected = result.duration / (1.0 + 0.05 / 2)
    assert result.modified_duration == pytest.approx(expected, rel=1e-2)


def test_convexity_positive() -> None:
    result = bonds.price_bond(_make_req())
    assert result.convexity > 0


def test_face_value_scaling() -> None:
    """Doubling face value doubles clean / dirty / accrued."""
    r1 = bonds.price_bond(_make_req(face_value=1000.0))
    r2 = bonds.price_bond(_make_req(face_value=2000.0))
    assert r2.clean_price == pytest.approx(2.0 * r1.clean_price, rel=1e-6)
    assert r2.dirty_price == pytest.approx(2.0 * r1.dirty_price, rel=1e-6)


def test_quarterly_bond_prices() -> None:
    result = bonds.price_bond(_make_req(coupons_per_year=4, yield_to_maturity=0.04))
    assert result.clean_price > 1000.0  # 5 % coupon @ 4 % YTM, quarterly compounding


def test_invalid_coupons_per_year_raises() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        _make_req(coupons_per_year=3)  # type: ignore[arg-type]


def test_settlement_before_issue_raises() -> None:
    with pytest.raises(ValueError, match="settlement_date"):
        bonds.price_bond(
            _make_req(
                issue_date=date(2026, 1, 1),
                settlement_date=date(2025, 6, 1),
            )
        )


def test_maturity_before_issue_raises() -> None:
    with pytest.raises(ValueError, match="maturity_date"):
        bonds.price_bond(
            _make_req(
                issue_date=date(2026, 5, 16),
                maturity_date=date(2025, 5, 16),
            )
        )


def test_duration_decreases_with_higher_coupon() -> None:
    """Higher coupon → lower duration (more cash flow earlier)."""
    low_coupon = bonds.price_bond(_make_req(coupon_rate=0.03, yield_to_maturity=0.05))
    high_coupon = bonds.price_bond(_make_req(coupon_rate=0.07, yield_to_maturity=0.05))
    assert high_coupon.duration < low_coupon.duration


def test_duration_ms_recorded() -> None:
    result = bonds.price_bond(_make_req())
    assert result.duration_ms > 0
