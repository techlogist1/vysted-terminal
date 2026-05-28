"""TestClient end-to-end tests for the /quant router."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _option_payload(**overrides: object) -> dict:
    base = {
        "exercise": "european",
        "payoff": "call",
        "spot": 100.0,
        "strike": 100.0,
        "risk_free_rate": 0.05,
        "dividend_yield": 0.02,
        "volatility": 0.20,
        "valuation_date": "2026-05-16",
        "expiry_date": "2027-05-16",
        "method": "black-scholes",
    }
    base.update(overrides)
    return base


def test_post_option_price_bs(client: TestClient) -> None:
    response = client.post("/quant/option/price", json=_option_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["method"] == "black-scholes"
    assert body["price"] > 0
    assert body["greeks"] is not None
    assert "delta" in body["greeks"]
    assert body["monte_carlo_std_error"] is None


def test_post_option_price_binomial(client: TestClient) -> None:
    response = client.post(
        "/quant/option/price",
        json=_option_payload(method="binomial", binomial_steps=100),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["method"] == "binomial"
    assert body["price"] > 0
    assert body["greeks"] is not None


def test_post_option_price_mc(client: TestClient) -> None:
    response = client.post(
        "/quant/option/price",
        json=_option_payload(method="monte-carlo", monte_carlo_paths=10_000),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["method"] == "monte-carlo"
    assert body["price"] > 0
    assert body["monte_carlo_std_error"] is not None and body["monte_carlo_std_error"] > 0


def test_post_option_price_american_bs_rejected_400(client: TestClient) -> None:
    response = client.post(
        "/quant/option/price",
        json=_option_payload(exercise="american"),
    )
    assert response.status_code == 400


def test_post_option_greeks(client: TestClient) -> None:
    response = client.post(
        "/quant/option/greeks",
        json={
            "payoff": "call",
            "spot": 100.0,
            "strike": 100.0,
            "risk_free_rate": 0.05,
            "dividend_yield": 0.02,
            "volatility": 0.20,
            "valuation_date": "2026-05-16",
            "expiry_date": "2027-05-16",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["price"] > 0
    assert {"delta", "gamma", "vega", "theta", "rho"} <= set(body["greeks"].keys())


def test_post_bond_price(client: TestClient) -> None:
    response = client.post(
        "/quant/bond/price",
        json={
            "face_value": 1000.0,
            "coupon_rate": 0.05,
            "coupons_per_year": 2,
            "issue_date": "2026-05-16",
            "maturity_date": "2036-05-16",
            "settlement_date": "2026-05-16",
            "yield_to_maturity": 0.05,
        },
    )
    assert response.status_code == 200
    body = response.json()
    # Par bond at coupon == YTM ≈ face.
    assert abs(body["clean_price"] - 1000.0) < 1.0
    assert body["duration"] > 0
    assert body["modified_duration"] > 0
    assert body["convexity"] > 0


def test_post_bond_price_invalid_400(client: TestClient) -> None:
    response = client.post(
        "/quant/bond/price",
        json={
            "face_value": 1000.0,
            "coupon_rate": 0.05,
            "coupons_per_year": 2,
            "issue_date": "2026-05-16",
            "maturity_date": "2025-05-16",  # before issue!
            "settlement_date": "2026-05-16",
            "yield_to_maturity": 0.05,
        },
    )
    assert response.status_code == 400


def test_post_yield_curve(client: TestClient) -> None:
    response = client.post(
        "/quant/yield-curve",
        json={
            "valuation_date": "2026-05-16",
            "instruments": [
                {"type": "deposit", "tenor": 1, "tenor_unit": "months", "rate": 0.041},
                {"type": "deposit", "tenor": 3, "tenor_unit": "months", "rate": 0.043},
                {"type": "swap", "tenor": 5, "tenor_unit": "years", "rate": 0.047},
                {"type": "swap", "tenor": 10, "tenor_unit": "years", "rate": 0.050},
            ],
            "sample_count": 10,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["curve"]) == 10
    assert body["valuation_date"] == "2026-05-16"
    for point in body["curve"]:
        assert "zero_rate" in point
        assert "discount_factor" in point


def test_post_yield_curve_empty_instruments_400(client: TestClient) -> None:
    response = client.post(
        "/quant/yield-curve",
        json={
            "valuation_date": "2026-05-16",
            "instruments": [],
            "sample_count": 10,
        },
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Input-domain validation (Phase 9.5 F4-1) — economically-invalid inputs must
# return HTTP 400 with a clear message, NOT 200 with degenerate/garbage output.
# ---------------------------------------------------------------------------


def test_post_option_negative_volatility_400(client: TestClient) -> None:
    response = client.post("/quant/option/price", json=_option_payload(volatility=-0.5))
    assert response.status_code == 400
    assert "volatility" in response.json()["detail"]


def test_post_option_zero_strike_400(client: TestClient) -> None:
    response = client.post("/quant/option/price", json=_option_payload(strike=0.0))
    assert response.status_code == 400
    assert "strike" in response.json()["detail"]


def test_post_option_zero_spot_400(client: TestClient) -> None:
    response = client.post("/quant/option/price", json=_option_payload(spot=0.0))
    assert response.status_code == 400
    assert "spot" in response.json()["detail"]


def test_post_option_expiry_not_after_valuation_400(client: TestClient) -> None:
    response = client.post(
        "/quant/option/price",
        json=_option_payload(valuation_date="2026-05-16", expiry_date="2026-05-16"),
    )
    assert response.status_code == 400
    assert "expiry_date" in response.json()["detail"]


def test_post_greeks_negative_volatility_400(client: TestClient) -> None:
    response = client.post(
        "/quant/option/greeks",
        json={
            "payoff": "call",
            "spot": 100.0,
            "strike": 100.0,
            "risk_free_rate": 0.05,
            "dividend_yield": 0.02,
            "volatility": -0.2,
            "valuation_date": "2026-05-16",
            "expiry_date": "2027-05-16",
        },
    )
    assert response.status_code == 400
    assert "volatility" in response.json()["detail"]


def test_post_bond_negative_ytm_400(client: TestClient) -> None:
    """ytm = -500% previously returned 200 with clean_price ~ -1.99e20."""
    response = client.post(
        "/quant/bond/price",
        json={
            "face_value": 1000.0,
            "coupon_rate": 0.05,
            "coupons_per_year": 2,
            "issue_date": "2026-05-16",
            "maturity_date": "2036-05-16",
            "settlement_date": "2026-05-16",
            "yield_to_maturity": -5.0,
        },
    )
    assert response.status_code == 400
    assert "yield_to_maturity" in response.json()["detail"]


def test_post_bond_zero_face_value_400(client: TestClient) -> None:
    response = client.post(
        "/quant/bond/price",
        json={
            "face_value": 0.0,
            "coupon_rate": 0.05,
            "coupons_per_year": 2,
            "issue_date": "2026-05-16",
            "maturity_date": "2036-05-16",
            "settlement_date": "2026-05-16",
            "yield_to_maturity": 0.05,
        },
    )
    assert response.status_code == 400
    assert "face_value" in response.json()["detail"]


def test_post_bond_absurd_coupon_400(client: TestClient) -> None:
    """coupon_rate = 1e6 (100,000,000%) is garbage, not a real coupon."""
    response = client.post(
        "/quant/bond/price",
        json={
            "face_value": 1000.0,
            "coupon_rate": 1e6,
            "coupons_per_year": 2,
            "issue_date": "2026-05-16",
            "maturity_date": "2036-05-16",
            "settlement_date": "2026-05-16",
            "yield_to_maturity": 0.05,
        },
    )
    assert response.status_code == 400
    assert "coupon_rate" in response.json()["detail"]


def test_post_yield_curve_negative_tenor_400(client: TestClient) -> None:
    response = client.post(
        "/quant/yield-curve",
        json={
            "valuation_date": "2026-05-16",
            "instruments": [{"type": "deposit", "tenor": -1, "tenor_unit": "months", "rate": 0.04}],
            "sample_count": 10,
        },
    )
    assert response.status_code == 400
    assert "tenor" in response.json()["detail"]


def test_post_option_valid_still_200(client: TestClient) -> None:
    """Sanity: a normal request is unaffected by the new validation."""
    response = client.post("/quant/option/price", json=_option_payload())
    assert response.status_code == 200
    assert response.json()["price"] > 0
