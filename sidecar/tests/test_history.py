"""Tests for the /history router."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_get_history(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/history/AAPL", params={"timeframe": "1d"}).json()
    assert body["symbol"] == "AAPL"
    assert body["timeframe"] == "1d"
    assert body["provider"] == "yfinance"
    assert len(body["bars"]) == 3
    first = body["bars"][0]
    assert first["open"] == 188.0
    assert first["close"] == 190.0
    assert first["volume"] == 48_000_000.0


def test_get_history_default_timeframe(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/history/AAPL").json()
    assert body["timeframe"] == "1d"
    assert len(body["bars"]) == 3


def test_get_history_carries_freshness(client: TestClient, mock_yfinance: object) -> None:
    """The series carries a calendar-aware freshness label for its last bar so the
    chart never shows a stale series as current (SC-019)."""
    body = client.get("/history/AAPL", params={"timeframe": "1d"}).json()
    assert body["freshness"] in {"live", "eod", "stale"}


def test_get_history_empty_series_returns_clean_200(client: TestClient, monkeypatch) -> None:
    """Bug-2: when every provider yields an EMPTY series the route downgrades to a
    clean 200 empty series (the chart renders its honest "No price data" state),
    NOT a scary (502)."""
    from services import provider_registry
    from services.correctness_gate import EmptySeriesError

    def _all_empty(symbol: str, timeframe: str, range_, asset_class: str):
        raise EmptySeriesError(f"correctness gate: empty series for {symbol!r} from 'yfinance'")

    monkeypatch.setattr(provider_registry, "get_history", _all_empty)
    resp = client.get("/history/ZZZZ", params={"timeframe": "1d"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "ZZZZ"
    assert body["timeframe"] == "1d"
    assert body["bars"] == []
    assert body["provider"] == "none"


def test_empty_series_in_symbol_carries_eod_only_reason(client: TestClient, monkeypatch) -> None:
    """WS6 Step 4: an IN symbol producing an all-empty series carries a typed
    `reason=="in_eod_only"` through the /history route so ChartPanel can show the
    region-aware "EOD only — add a BYOK broker" message instead of the generic
    "No price data". Guards the chain region_hint → _empty_series_reason → the
    serialized model field against silent regression."""
    from services import provider_registry
    from services.correctness_gate import EmptySeriesError

    def _all_empty(symbol: str, timeframe: str, range_, asset_class: str):
        raise EmptySeriesError(f"correctness gate: empty series for {symbol!r} from 'bse'")

    monkeypatch.setattr(provider_registry, "get_history", _all_empty)

    # A bare BSE-only ticker resolves to IN → the typed reason.
    body = client.get("/history/TIRUPATI", params={"timeframe": "1d"}).json()
    assert body["bars"] == []
    assert body["provider"] == "none"
    assert body["reason"] == "in_eod_only"

    # A .BO-suffixed symbol is decisively IN → same typed reason.
    body_bo = client.get("/history/RELIANCE.BO", params={"timeframe": "1d"}).json()
    assert body_bo["reason"] == "in_eod_only"

    # A US symbol carries no IN reason (the generic message stays correct).
    body_us = client.get("/history/AAPL", params={"timeframe": "1d"}).json()
    assert body_us["bars"] == []
    assert body_us.get("reason") is None


def test_empty_series_reason_unit() -> None:
    """Direct unit guard on the typed-reason helper (no route)."""
    from routers.history import _empty_series_reason

    assert _empty_series_reason("TIRUPATI") == "in_eod_only"
    assert _empty_series_reason("RELIANCE.BO") == "in_eod_only"
    assert _empty_series_reason("AAPL") is None


def test_get_history_integrity_failure_still_502(client: TestClient, monkeypatch) -> None:
    """A genuine data-integrity failure (a non-empty CorrectnessError — non-positive
    close / symbol mismatch) still surfaces as 502; only the empty-series case is
    softened (the recon's "distinguish on the specific failure" rule)."""
    from services import provider_registry
    from services.correctness_gate import CorrectnessError

    def _integrity_fail(symbol: str, timeframe: str, range_, asset_class: str):
        raise CorrectnessError("correctness gate: non-positive last close -1.0 for 'AAPL'")

    monkeypatch.setattr(provider_registry, "get_history", _integrity_fail)
    resp = client.get("/history/AAPL", params={"timeframe": "1d"})
    assert resp.status_code == 502
