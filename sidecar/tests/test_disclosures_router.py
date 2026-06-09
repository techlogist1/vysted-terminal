"""Tests for the standalone /disclosures router (R7 Component 3).

The router is exercised over a minimal local FastAPI app (TestClient +
``include_router``) so the suite passes BEFORE the lead registers it in
``app.py`` (registration instructions: ``docs/redesign/INTEGRATION_NOTES_R7.md``).
The service layer is stubbed — no network; the service's own parsing/merging is
covered in ``test_corporate_disclosures.py``. Asserted here: the wire shapes,
the data_cache hit path (one upstream call per TTL window), the honest 502 on a
total provider failure, and the FastAPI param validation (bad exchange → 422).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from config import DATA_DIR_ENV
from models.announcements import (
    Announcement,
    AnnouncementsResponse,
    ResultsCalendarResponse,
    ResultsEvent,
    ShareholdingPattern,
    ShareholdingResponse,
)
from routers import disclosures
from services import corporate_disclosures, data_cache
from services.errors import ProviderError


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> object:
    """Pin the cache db to a per-test temp path."""
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    data_cache.reset_for_tests()
    yield tmp_path
    data_cache.reset_for_tests()


@pytest.fixture
def client() -> TestClient:
    """A TestClient over a minimal app: just the disclosures router."""
    app = FastAPI()
    app.include_router(disclosures.router)
    return TestClient(app)


def _announcement(exchange: str, headline: str) -> Announcement:
    return Announcement(
        symbol="RELIANCE",
        exchange=exchange,
        headline=headline,
        category="Updates",
        attachment_url="https://example.invalid/filing.pdf",
        ts=datetime(2026, 6, 9, 14, 15, 31, tzinfo=UTC),
    )


def _stub_announcements(calls: list[dict[str, Any]]) -> Any:
    def stub(symbol: str, exchange: str | None = None, limit: int = 50) -> AnnouncementsResponse:
        calls.append({"symbol": symbol, "exchange": exchange, "limit": limit})
        items = [_announcement("NSE", "NSE item"), _announcement("BSE", "BSE item")][:limit]
        return AnnouncementsResponse(
            symbol=symbol,
            exchange=exchange,
            count=len(items),
            announcements=items,
            sources=["NSE", "BSE"] if exchange is None else [exchange],
            errors={},
        )

    return stub


# ---------------------------------------------------------------------------
# /disclosures/announcements
# ---------------------------------------------------------------------------


def test_announcements_wire_shape(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(corporate_disclosures, "get_announcements", _stub_announcements(calls))

    resp = client.get("/disclosures/announcements", params={"symbol": "reliance"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "RELIANCE"  # router normalises before the service
    assert body["exchange"] is None
    assert body["count"] == 2
    assert body["sources"] == ["NSE", "BSE"]
    assert body["errors"] == {}
    item = body["announcements"][0]
    assert item["exchange"] == "NSE"
    assert item["headline"] == "NSE item"
    assert item["attachment_url"] == "https://example.invalid/filing.pdf"
    assert item["ts"].startswith("2026-06-09T14:15:31")
    assert calls == [{"symbol": "RELIANCE", "exchange": None, "limit": 50}]


def test_announcements_exchange_filter_and_limit(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(corporate_disclosures, "get_announcements", _stub_announcements(calls))

    resp = client.get(
        "/disclosures/announcements",
        params={"symbol": "RELIANCE", "exchange": "BSE", "limit": 1},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["exchange"] == "BSE"
    assert body["sources"] == ["BSE"]
    assert body["count"] == 1
    assert calls == [{"symbol": "RELIANCE", "exchange": "BSE", "limit": 1}]


def test_announcements_caches_within_ttl(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(corporate_disclosures, "get_announcements", _stub_announcements(calls))

    first = client.get("/disclosures/announcements", params={"symbol": "RELIANCE"})
    second = client.get("/disclosures/announcements", params={"symbol": "RELIANCE"})
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(calls) == 1  # the second hit was served from data_cache


def test_announcements_total_failure_is_a_502(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(symbol: str, exchange: str | None = None, limit: int = 50) -> AnnouncementsResponse:
        raise ProviderError("disclosures: every announcement source failed for 'RELIANCE'")

    monkeypatch.setattr(corporate_disclosures, "get_announcements", boom)
    resp = client.get("/disclosures/announcements", params={"symbol": "RELIANCE"})
    assert resp.status_code == 502
    assert "every announcement source failed" in resp.json()["detail"]


def test_announcements_validates_params(client: TestClient) -> None:
    # An unknown exchange and an out-of-range limit are FastAPI 422s, not 500s.
    assert (
        client.get(
            "/disclosures/announcements", params={"symbol": "RELIANCE", "exchange": "NYSE"}
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/disclosures/announcements", params={"symbol": "RELIANCE", "limit": 0}
        ).status_code
        == 422
    )
    assert client.get("/disclosures/announcements").status_code == 422  # symbol required


# ---------------------------------------------------------------------------
# /disclosures/results
# ---------------------------------------------------------------------------


def test_results_wire_shape(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def stub(symbol: str) -> ResultsCalendarResponse:
        return ResultsCalendarResponse(
            symbol=symbol,
            count=1,
            events=[
                ResultsEvent(
                    symbol=symbol,
                    company="Reliance Industries Limited",
                    purpose="Financial Results",
                    description="To consider the quarterly results.",
                    date=date(2026, 7, 18),
                )
            ],
        )

    monkeypatch.setattr(corporate_disclosures, "get_results_calendar", stub)
    resp = client.get("/disclosures/results", params={"symbol": "RELIANCE"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "RELIANCE"
    assert body["count"] == 1
    event = body["events"][0]
    assert event["purpose"] == "Financial Results"
    assert event["date"] == "2026-07-18"


def test_results_provider_error_is_a_502(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(symbol: str) -> ResultsCalendarResponse:
        raise ProviderError("nse_direct: 'ZZZ' is not a known NSE instrument")

    monkeypatch.setattr(corporate_disclosures, "get_results_calendar", boom)
    resp = client.get("/disclosures/results", params={"symbol": "ZZZ"})
    assert resp.status_code == 502
    assert "not a known NSE instrument" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# /disclosures/shareholding
# ---------------------------------------------------------------------------


def test_shareholding_wire_shape(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def stub(symbol: str) -> ShareholdingResponse:
        return ShareholdingResponse(
            symbol=symbol,
            count=1,
            patterns=[
                ShareholdingPattern(
                    symbol=symbol,
                    quarter_end=date(2026, 3, 31),
                    promoter_percent=50.0,
                    fii_percent=None,
                    dii_percent=None,
                    public_percent=50.0,
                    employee_trusts_percent=0.0,
                    submission_date=date(2026, 4, 21),
                    xbrl_url="https://nsearchives.nseindia.com/corporate/xbrl/SHP_test.xml",
                )
            ],
        )

    monkeypatch.setattr(corporate_disclosures, "get_shareholding", stub)
    resp = client.get("/disclosures/shareholding", params={"symbol": "RELIANCE"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "RELIANCE"
    pattern = body["patterns"][0]
    assert pattern["quarter_end"] == "2026-03-31"
    assert pattern["promoter_percent"] == 50.0
    # FII/DII honestly null on the wire (the split rides the XBRL link).
    assert pattern["fii_percent"] is None and pattern["dii_percent"] is None
    assert pattern["xbrl_url"].endswith(".xml")


def test_shareholding_caches_within_ttl(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def stub(symbol: str) -> ShareholdingResponse:
        calls.append(symbol)
        return ShareholdingResponse(symbol=symbol, count=0, patterns=[])

    monkeypatch.setattr(corporate_disclosures, "get_shareholding", stub)
    assert client.get("/disclosures/shareholding", params={"symbol": "RELIANCE"}).status_code == 200
    assert client.get("/disclosures/shareholding", params={"symbol": "RELIANCE"}).status_code == 200
    assert calls == ["RELIANCE"]
