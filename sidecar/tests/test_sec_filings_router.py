"""Tests for ``routers.sec_filings`` — REST surface over the sec-edgar-mcp provider.

The provider is mocked at the module level; the router routes are
exercised via TestClient so the FastAPI request/response binding is
verified end-to-end (Pydantic validation, HTTP status codes).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import create_app
from models.sec import (
    Filing,
    FilingDetail,
    FilingSection,
    FilingsListResponse,
    InsiderTransaction,
    InsiderTransactionsResponse,
)
from services import data_cache, sec_filings_provider


def _sample_filing(form: str = "10-K", accession: str = "0000320193-24-000123") -> Filing:
    return Filing(
        accession=accession,
        cik="0000320193",
        company_name="Apple Inc.",
        symbol="AAPL",
        form_type=form,  # type: ignore[arg-type]
        filed_date=date(2024, 11, 1),
        period_of_report=date(2024, 9, 28),
        edgar_url=f"https://www.sec.gov/Archives/edgar/data/320193/{accession.replace('-', '')}/",
    )


def _sample_section(idx: int) -> FilingSection:
    return FilingSection(
        id=f"item-{idx}", title=f"Item {idx}. Section", text="Body " * 50, word_count=50
    )


@pytest.fixture
def available_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> AsyncIterator[None]:
    """Pin the provider to 'available' + fresh data_cache for each test."""
    monkeypatch.setenv("VYSTED_SEC_EDGAR_MCP_PORT", "9876")
    sec_filings_provider._reset_for_tests()
    data_cache.reset_for_tests(tmp_path / "router_cache.db")
    yield
    data_cache.reset_for_tests(None)


@pytest.fixture
def unavailable_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the provider to 'unavailable' — the router must 501."""
    monkeypatch.delenv("VYSTED_SEC_EDGAR_MCP_PORT", raising=False)
    sec_filings_provider._reset_for_tests()


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# /sec/status
# ---------------------------------------------------------------------------


def test_status_when_unavailable(client: TestClient, unavailable_provider: None) -> None:
    response = client.get("/sec/status")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["provider"] == "sec-edgar-mcp"


def test_status_when_available(client: TestClient, available_provider: None) -> None:
    response = client.get("/sec/status")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["endpoint"] == "http://127.0.0.1:9876/mcp"


# ---------------------------------------------------------------------------
# /sec/filings
# ---------------------------------------------------------------------------


def test_filings_requires_cik_or_symbol(
    client: TestClient, available_provider: None
) -> None:
    response = client.get("/sec/filings")
    assert response.status_code == 400


def test_filings_501_when_provider_unavailable(
    client: TestClient, unavailable_provider: None
) -> None:
    response = client.get("/sec/filings", params={"symbol": "AAPL"})
    assert response.status_code == 501


def test_filings_returns_provider_payload(
    client: TestClient,
    available_provider: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = FilingsListResponse(
        cik="0000320193",
        company_name="Apple Inc.",
        symbol="AAPL",
        filings=[_sample_filing("10-K"), _sample_filing("10-Q", "0000320193-24-000100")],
    )

    async def _fake(identifier: str, **_: Any) -> FilingsListResponse:
        assert identifier == "AAPL"
        return fixture

    monkeypatch.setattr(sec_filings_provider, "list_filings", _fake)
    response = client.get("/sec/filings", params={"symbol": "AAPL"})
    assert response.status_code == 200
    body = response.json()
    assert body["company_name"] == "Apple Inc."
    assert len(body["filings"]) == 2
    assert body["filings"][0]["form_type"] == "10-K"


def test_filings_passes_form_type_and_limit(
    client: TestClient,
    available_provider: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def _fake(identifier: str, form_type: Any = None, limit: int = 40) -> FilingsListResponse:
        captured["identifier"] = identifier
        captured["form_type"] = form_type
        captured["limit"] = limit
        return FilingsListResponse(
            cik="0000320193", company_name="Apple Inc.", symbol="AAPL", filings=[]
        )

    monkeypatch.setattr(sec_filings_provider, "list_filings", _fake)
    response = client.get(
        "/sec/filings", params={"cik": "320193", "form_type": "10-K", "limit": 5}
    )
    assert response.status_code == 200
    assert captured["form_type"] == "10-K"
    assert captured["limit"] == 5


# ---------------------------------------------------------------------------
# /sec/filings/{accession}
# ---------------------------------------------------------------------------


def test_filing_detail(
    client: TestClient,
    available_provider: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sections = [_sample_section(i) for i in range(1, 7)]
    fixture = FilingDetail(
        filing=_sample_filing("10-K"),
        sections=sections,
        total_chars=sum(len(s.text) for s in sections),
    )

    async def _fake(accession: str, *, cik_or_symbol: str | None = None) -> FilingDetail:
        assert accession == "0000320193-24-000123"
        assert cik_or_symbol == "AAPL"
        return fixture

    monkeypatch.setattr(sec_filings_provider, "get_filing", _fake)
    response = client.get(
        "/sec/filings/0000320193-24-000123", params={"identifier": "AAPL"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["filing"]["form_type"] == "10-K"
    assert len(body["sections"]) == 6


def test_filing_detail_requires_identifier(
    client: TestClient, available_provider: None
) -> None:
    response = client.get("/sec/filings/0000320193-24-000123")
    assert response.status_code == 422  # FastAPI's missing-query error


def test_filing_sections_route(
    client: TestClient,
    available_provider: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sections = [_sample_section(i) for i in range(1, 4)]

    async def _fake(
        accession: str, *, cik_or_symbol: str | None = None
    ) -> list[FilingSection]:
        return sections

    monkeypatch.setattr(sec_filings_provider, "get_filing_sections", _fake)
    response = client.get(
        "/sec/filings/0000320193-24-000123/sections", params={"identifier": "AAPL"}
    )
    assert response.status_code == 200
    body = response.json()
    assert "sections" in body
    assert len(body["sections"]) == 3


# ---------------------------------------------------------------------------
# /sec/insider
# ---------------------------------------------------------------------------


def test_insider_transactions_route(
    client: TestClient,
    available_provider: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = InsiderTransactionsResponse(
        cik="0000320193",
        issuer_name="Apple Inc.",
        transactions=[
            InsiderTransaction(
                accession="0000320193-24-001000",
                reporter_name="Cook Timothy D",
                reporter_cik="0001214156",
                issuer_cik="0000320193",
                issuer_name="Apple Inc.",
                issuer_symbol="AAPL",
                form_type="4",
                transaction_date=date(2024, 12, 1),
                direction="disposed",
                shares="511000",
                price_per_share="190.50",
                transaction_value="97345500",
                transaction_code="S",
                reporter_title="CEO",
            ),
        ],
    )

    async def _fake(
        identifier: str, form_type: Any = None, limit: int = 50
    ) -> InsiderTransactionsResponse:
        assert form_type == "4"
        return fixture

    monkeypatch.setattr(sec_filings_provider, "list_insider_transactions", _fake)
    response = client.get("/sec/insider/AAPL", params={"form": "4", "limit": 50})
    assert response.status_code == 200
    body = response.json()
    assert body["issuer_name"] == "Apple Inc."
    assert body["transactions"][0]["direction"] == "disposed"


# ---------------------------------------------------------------------------
# /sec/filings/search
# ---------------------------------------------------------------------------


def test_search_route(
    client: TestClient,
    available_provider: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake(query: str, limit: int = 10) -> list[dict[str, Any]]:
        return [{"cik": "0000320193", "name": "Apple Inc.", "ticker": "AAPL"}]

    monkeypatch.setattr(sec_filings_provider, "search_companies", _fake)
    response = client.get("/sec/filings/search", params={"q": "apple"})
    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert body["results"][0]["ticker"] == "AAPL"
