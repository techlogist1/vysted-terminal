"""Tests for ``services.workflow_nodes.sec_nodes`` — two SEC workflow nodes."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from models.sec import (
    Filing,
    FilingDetail,
    FilingSection,
    InsiderTransaction,
    InsiderTransactionsResponse,
)
from services import sec_filings_provider, workflow_engine
from services.workflow_nodes import sec_nodes


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    workflow_engine.reset_registry_for_tests()
    sec_nodes.register()


@pytest.fixture
def available_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VYSTED_SEC_EDGAR_MCP_PORT", "9876")
    sec_filings_provider._reset_for_tests()


def test_register_adds_two_node_types() -> None:
    types = workflow_engine.registered_node_types()
    assert "data.fetch_sec_filing" in types
    assert "data.fetch_insider_transactions" in types


@pytest.mark.asyncio
async def test_fetch_sec_filing_returns_detail(
    available_provider: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sections = [
        FilingSection(id="item-1", title="Item 1", text="Body " * 30, word_count=30)
    ]
    fixture = FilingDetail(
        filing=Filing(
            accession="0000320193-24-000123",
            cik="0000320193",
            company_name="Apple Inc.",
            symbol="AAPL",
            form_type="10-K",
            filed_date=date(2024, 11, 1),
            period_of_report=date(2024, 9, 28),
            edgar_url="https://example.com/",
        ),
        sections=sections,
        total_chars=sum(len(s.text) for s in sections),
    )

    async def _fake(accession: str, *, cik_or_symbol: str | None = None) -> FilingDetail:
        return fixture

    monkeypatch.setattr(sec_filings_provider, "get_filing", _fake)
    outputs = await sec_nodes.fetch_sec_filing(
        {}, {"accession": "0000320193-24-000123", "identifier": "AAPL"}
    )
    assert outputs["filing"]["filing"]["accession"] == "0000320193-24-000123"
    assert len(outputs["filing"]["sections"]) == 1


@pytest.mark.asyncio
async def test_fetch_sec_filing_missing_accession_raises() -> None:
    with pytest.raises(ValueError, match="accession"):
        await sec_nodes.fetch_sec_filing({}, {"identifier": "AAPL"})


@pytest.mark.asyncio
async def test_fetch_sec_filing_missing_identifier_raises() -> None:
    with pytest.raises(ValueError, match="identifier"):
        await sec_nodes.fetch_sec_filing({}, {"accession": "x"})


@pytest.mark.asyncio
async def test_fetch_insider_transactions(
    available_provider: None, monkeypatch: pytest.MonkeyPatch
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
                form_type="4",
                transaction_date=date(2024, 12, 1),
                direction="disposed",
                shares="511000",
                price_per_share="190.50",
                transaction_value="97345500",
                transaction_code="S",
                reporter_title="CEO",
            )
        ],
    )

    captured: dict[str, Any] = {}

    async def _fake(
        identifier: str, form_type: Any = None, limit: int = 30
    ) -> InsiderTransactionsResponse:
        captured["identifier"] = identifier
        captured["form_type"] = form_type
        captured["limit"] = limit
        return fixture

    monkeypatch.setattr(sec_filings_provider, "list_insider_transactions", _fake)
    outputs = await sec_nodes.fetch_insider_transactions(
        {"symbol": "AAPL"}, {"form": "4", "limit": 15}
    )
    assert outputs["transactions"]["issuer_name"] == "Apple Inc."
    assert captured["identifier"] == "AAPL"
    assert captured["form_type"] == "4"
    assert captured["limit"] == 15


@pytest.mark.asyncio
async def test_fetch_insider_transactions_missing_identifier_raises() -> None:
    with pytest.raises(ValueError, match="identifier"):
        await sec_nodes.fetch_insider_transactions({}, {})
