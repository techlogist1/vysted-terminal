"""Tests for the /fundamentals router."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_get_fundamentals(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/fundamentals/AAPL").json()
    assert body["symbol"] == "AAPL"
    assert body["name"] == "Apple Inc."
    assert body["sector"] == "Technology"
    assert body["pe_ratio"] == 31.2
    assert body["beta"] == 1.25
    # yfinance 1.3.0 returns ``dividendYield`` as a percentage number
    # (the fake supplies ``0.44``); the provider divides by 100 so the
    # ``dividend_yield`` field carries a true fraction.
    assert body["dividend_yield"] == pytest.approx(0.0044)
    assert body["provider"] == "yfinance"
    # D55: the growth-basis truth rides the raw REST response (the panel/agent
    # bypass semantics.py, so the contract itself must carry it).
    assert body["growth_basis"] == "mrq_yoy"


def test_get_fundamentals_provider_error_is_502(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A provider failure is an honest 502, never an unhandled 500."""
    from services import provider_registry
    from services.errors import ProviderError

    async def boom(symbol: str):  # noqa: ANN202
        raise ProviderError("yfinance fundamentals failed for 'AAPL': upstream 500")

    monkeypatch.setattr(provider_registry, "get_fundamentals", boom)
    resp = client.get("/fundamentals/AAPL")
    assert resp.status_code == 502
    assert "upstream 500" in resp.json()["detail"]


def test_get_fundamentals_rate_limited_is_429(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A throttle (ProviderError.kind == 'rate_limited') is a 429 with a human
    'try again shortly' detail — not a 502 or a no-data masquerade."""
    from services import provider_registry
    from services.errors import ProviderError

    async def throttled(symbol: str):  # noqa: ANN202
        raise ProviderError("429 Too Many Requests", kind="rate_limited")

    monkeypatch.setattr(provider_registry, "get_fundamentals", throttled)
    resp = client.get("/fundamentals/AAPL")
    assert resp.status_code == 429
    assert "throttled" in resp.json()["detail"].lower()


def test_get_fundamentals_dividend_yield_missing(
    client: TestClient,
    mock_yfinance: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing ``dividendYield`` stays ``None`` — no divide-by-100 crash."""
    from services import yfinance_provider

    class _NoYieldTicker(mock_yfinance):  # type: ignore[misc, valid-type]
        @property
        def info(self) -> dict:
            data = super().info.copy()
            data.pop("dividendYield", None)
            return data

    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _NoYieldTicker)
    body = client.get("/fundamentals/AAPL").json()
    assert body["dividend_yield"] is None


def test_get_income_statement(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/fundamentals/AAPL/income").json()
    assert body["symbol"] == "AAPL"
    assert body["periods"] == ["2025", "2024"]
    labels = {line["label"] for line in body["lines"]}
    assert "Total Revenue" in labels
    assert "Net Income" in labels


def test_get_balance_sheet(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/fundamentals/AAPL/balance").json()
    assert body["periods"] == ["2025", "2024"]
    assert len(body["lines"]) == 2


def test_get_cash_flow(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/fundamentals/AAPL/cashflow").json()
    assert len(body["lines"]) == 2


def test_get_analyst_rating(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/fundamentals/AAPL/ratings").json()
    assert body["symbol"] == "AAPL"
    assert body["strong_buy"] == 12
    assert body["buy"] == 20
    assert body["hold"] == 8
    assert body["consensus"] == "buy"
    assert body["target_mean"] == 225.0


def test_get_fundamentals_unknown_symbol_is_honest_404(client, monkeypatch) -> None:
    """R11 gate-7 catch: a garbage symbol used to serve an all-null 200 (a
    dishonest 'instrument exists, no data' shape). yfinance returns an EMPTY
    info dict for unknown symbols — the provider now raises kind="not_found"
    and the route answers an honest 404 with a human message."""
    from services import yfinance_provider

    class _EmptyTicker:
        def __init__(self, symbol: str) -> None:
            self.info = {}

    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _EmptyTicker)
    resp = client.get("/fundamentals/NOTAREALSYMBOL123")
    assert resp.status_code == 404
    assert "check the symbol" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# R13 — the additive field_meta contract (per-field provenance / coverage)
# ---------------------------------------------------------------------------


def test_field_meta_is_additive_and_absent_by_default() -> None:
    """A Fundamentals built without field_meta carries ``None`` and a legacy
    consumer that never reads the key is unaffected — the wire stays additive."""
    from models.fundamentals import Fundamentals

    fund = Fundamentals(symbol="AAPL", provider="yfinance", pe_ratio=31.2)
    assert fund.field_meta is None
    # An OLD payload (no field_meta key at all) still validates.
    legacy = Fundamentals.model_validate({"symbol": "AAPL", "provider": "yfinance"})
    assert legacy.field_meta is None


def test_field_meta_roundtrips_all_three_statuses() -> None:
    """FieldMeta serialises + revalidates for ok / withheld / unavailable."""
    from models.fundamentals import FieldMeta, Fundamentals

    fund = Fundamentals(
        symbol="KSE.BO",
        provider="yfinance",
        pe_ratio=6.93,
        field_meta={
            "pe_ratio": FieldMeta(
                status="ok", provider="yfinance", as_of="2026-07-10T00:00:00+00:00"
            ),
            "dividend_yield": FieldMeta(status="withheld", reason="ambiguous unit"),
            "beta": FieldMeta(status="unavailable"),
        },
    )
    wire = fund.model_dump(mode="json")
    back = Fundamentals.model_validate(wire)
    assert back.field_meta is not None
    assert back.field_meta["pe_ratio"].status == "ok"
    assert back.field_meta["pe_ratio"].as_of == "2026-07-10T00:00:00+00:00"
    assert back.field_meta["dividend_yield"].status == "withheld"
    assert back.field_meta["dividend_yield"].reason == "ambiguous unit"
    assert back.field_meta["beta"].status == "unavailable"
