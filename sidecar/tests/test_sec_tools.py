"""Tests for ``services.agent_tools.sec_tools`` — three SEC agent tools."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from models.sec import (
    Filing,
    FilingDetail,
    FilingSection,
    FilingsListResponse,
    InsiderTransaction,
    InsiderTransactionsResponse,
)
from services import agent_tools, sec_filings_provider
from services.agent_tools import sec_tools


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    agent_tools.reset_for_tests()
    sec_tools.register()


@pytest.fixture
def available_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VYSTED_SEC_EDGAR_MCP_PORT", "9876")
    sec_filings_provider._reset_for_tests()


def _filing(form: str = "10-K", accession: str = "0000320193-24-000123") -> Filing:
    return Filing(
        accession=accession,
        cik="0000320193",
        company_name="Apple Inc.",
        symbol="AAPL",
        form_type=form,  # type: ignore[arg-type]
        filed_date=date(2024, 11, 1),
        period_of_report=date(2024, 9, 28),
        edgar_url="https://www.sec.gov/Archives/edgar/data/320193/.../",
    )


def test_register_adds_three_tools() -> None:
    """register() puts all three tool ids in the registry."""
    ids = agent_tools.registered_tools()
    assert "sec_filings_list" in ids
    assert "sec_filing_content" in ids
    assert "sec_insider_transactions" in ids


@pytest.mark.asyncio
async def test_sec_filings_list_returns_payload(
    available_provider: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = FilingsListResponse(
        cik="0000320193",
        company_name="Apple Inc.",
        symbol="AAPL",
        filings=[_filing("10-K"), _filing("10-Q", "0000320193-24-000100")],
    )

    async def _fake(identifier: str, **_: Any) -> FilingsListResponse:
        return fixture

    monkeypatch.setattr(sec_filings_provider, "list_filings", _fake)

    result = await agent_tools.invoke_tool(
        "sec_filings_list", {"symbol": "AAPL", "form_type": "10-K", "limit": 5}
    )
    assert result["ok"] is True
    assert result["filings"]["company_name"] == "Apple Inc."
    assert len(result["filings"]["filings"]) == 2


@pytest.mark.asyncio
async def test_sec_filings_list_missing_id_errors() -> None:
    result = await agent_tools.invoke_tool("sec_filings_list", {})
    assert result["ok"] is False
    assert "missing" in result["error"]


@pytest.mark.asyncio
async def test_sec_filings_list_when_provider_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VYSTED_SEC_EDGAR_MCP_PORT", raising=False)
    sec_filings_provider._reset_for_tests()
    result = await agent_tools.invoke_tool("sec_filings_list", {"symbol": "AAPL"})
    assert result["ok"] is False
    assert "not bundled" in result["error"]


@pytest.mark.asyncio
async def test_sec_filing_content(
    available_provider: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sections = [
        FilingSection(id=f"item-{i}", title=f"Item {i}", text="Body " * 20, word_count=20)
        for i in range(1, 4)
    ]
    fixture = FilingDetail(
        filing=_filing("10-K"),
        sections=sections,
        total_chars=sum(len(s.text) for s in sections),
    )

    async def _fake(accession: str, *, cik_or_symbol: str | None = None) -> FilingDetail:
        return fixture

    monkeypatch.setattr(sec_filings_provider, "get_filing", _fake)
    result = await agent_tools.invoke_tool(
        "sec_filing_content",
        {"accession": "0000320193-24-000123", "identifier": "AAPL"},
    )
    assert result["ok"] is True
    assert result["filing"]["filing"]["form_type"] == "10-K"
    assert len(result["filing"]["sections"]) == 3


@pytest.mark.asyncio
async def test_sec_filing_content_missing_args() -> None:
    result = await agent_tools.invoke_tool("sec_filing_content", {})
    assert result["ok"] is False


@pytest.mark.asyncio
async def test_sec_insider_transactions(
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

    async def _fake(
        identifier: str, form_type: Any = None, limit: int = 30
    ) -> InsiderTransactionsResponse:
        return fixture

    monkeypatch.setattr(sec_filings_provider, "list_insider_transactions", _fake)
    result = await agent_tools.invoke_tool(
        "sec_insider_transactions", {"symbol": "AAPL", "form": "4", "limit": 25}
    )
    assert result["ok"] is True
    assert len(result["transactions"]["transactions"]) == 1
    assert result["transactions"]["transactions"][0]["direction"] == "disposed"


def test_tool_ids_have_no_execution_substrings() -> None:
    """§6.5 audit grep — none of our tool ids touch broker execution."""
    ids = agent_tools.registered_tools()
    for forbidden in ("place_order", "submit_order", "execute_order", "auto_approve"):
        assert not any(forbidden in tid for tid in ids), (
            f"sec_tools introduced disallowed tool id substring {forbidden!r}"
        )
