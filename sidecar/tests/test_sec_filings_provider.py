"""Tests for ``services.sec_filings_provider`` — MCP-client mapping.

The sec-edgar-mcp subprocess is never launched live; instead the tests
install a fake :class:`McpClient` whose ``call_tool`` returns canned
payloads. The assertions cover:

  - is_available + status track the VYSTED_SEC_EDGAR_MCP_PORT env var.
  - list_filings invokes ``get_recent_filings`` with the right args and
    maps the upstream shape into a :class:`FilingsListResponse`.
  - get_filing combines ``get_filing_sections`` + ``get_recent_filings``
    into a :class:`FilingDetail`.
  - list_insider_transactions invokes ``get_insider_transactions`` and
    maps Form-4 codes into the right ``acquired`` / ``disposed``
    direction.
  - The data_cache TTL layer is consulted (hit + miss verified).
  - Provider errors translate to :class:`ProviderError`.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from services import data_cache, mcp_client, sec_filings_provider
from services.errors import ProviderError


class _RecordingClient:
    """Captures every ``call_tool`` invocation on the SEC EDGAR provider."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.responses: dict[str, Any] = {}
        self.errors: dict[str, str] = {}

    def respond(self, tool_name: str, body: Any) -> None:
        self.responses[tool_name] = body

    def error(self, tool_name: str, message: str) -> None:
        self.errors[tool_name] = message

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append({"name": name, "arguments": dict(arguments)})
        if name in self.errors:
            raise RuntimeError(self.errors[name])
        if name not in self.responses:
            raise AssertionError(f"unexpected sec-edgar-mcp tool: {name!r}")
        return {
            "isError": False,
            "content": [{"type": "text", "text": json.dumps(self.responses[name])}],
        }


@pytest.fixture
def recorder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> _RecordingClient:
    """Install a recording fake client + pin port env var + fresh cache db."""
    rec = _RecordingClient()

    async def _fake_get_client(
        server_id: str, *, transport: str, endpoint: str | None = None, **_: Any
    ) -> _RecordingClient:
        return rec

    monkeypatch.setattr(mcp_client, "get_client", _fake_get_client)
    monkeypatch.setenv("VYSTED_SEC_EDGAR_MCP_PORT", "9876")
    monkeypatch.setenv("VYSTED_SEC_EDGAR_MCP_HOST", "127.0.0.1")
    sec_filings_provider._reset_for_tests()
    data_cache.reset_for_tests(tmp_path / "test_cache.db")
    yield rec
    data_cache.reset_for_tests(None)


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------


def test_is_available_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """``is_available`` toggles with VYSTED_SEC_EDGAR_MCP_PORT."""
    sec_filings_provider._reset_for_tests()
    monkeypatch.delenv("VYSTED_SEC_EDGAR_MCP_PORT", raising=False)
    assert sec_filings_provider.is_available() is False

    sec_filings_provider._reset_for_tests()
    monkeypatch.setenv("VYSTED_SEC_EDGAR_MCP_PORT", "9000")
    assert sec_filings_provider.is_available() is True

    # Tauri Rust signals "binary missing" by setting port=0 — provider
    # must treat it as unavailable so the router 501s cleanly.
    sec_filings_provider._reset_for_tests()
    monkeypatch.setenv("VYSTED_SEC_EDGAR_MCP_PORT", "0")
    assert sec_filings_provider.is_available() is False


@pytest.mark.asyncio
async def test_status_returns_endpoint_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sec_filings_provider._reset_for_tests()
    monkeypatch.setenv("VYSTED_SEC_EDGAR_MCP_PORT", "9000")
    status = await sec_filings_provider.status()
    assert status["available"] is True
    assert status["endpoint"] == "http://127.0.0.1:9000/mcp"
    assert status["provider"] == "sec-edgar-mcp"


# ---------------------------------------------------------------------------
# list_filings
# ---------------------------------------------------------------------------


_AAPL_FILINGS_PAYLOAD = {
    "cik": "320193",
    "company_name": "Apple Inc.",
    "ticker": "AAPL",
    "filings": [
        {
            "accession": "0000320193-24-000123",
            "form": "10-K",
            "filed_date": "2024-11-01",
            "period_of_report": "2024-09-28",
            "cik": "320193",
        },
        {
            "accession": "0000320193-24-000100",
            "form": "10-Q",
            "filed_date": "2024-08-02",
            "period_of_report": "2024-06-29",
        },
        {
            "accession": "0000320193-24-000080",
            "form": "8-K",
            "filed_date": "2024-07-15",
        },
    ],
}


@pytest.mark.asyncio
async def test_list_filings_invokes_correct_tool(recorder: _RecordingClient) -> None:
    """list_filings calls get_recent_filings with the right identifier + form filter."""
    recorder.respond("get_recent_filings", _AAPL_FILINGS_PAYLOAD)

    response = await sec_filings_provider.list_filings(
        "AAPL", form_type="10-K", limit=20
    )

    assert recorder.calls[0]["name"] == "get_recent_filings"
    assert recorder.calls[0]["arguments"]["identifier"] == "AAPL"
    assert recorder.calls[0]["arguments"]["form_type"] == "10-K"
    assert recorder.calls[0]["arguments"]["limit"] == 20

    assert response.cik == "0000320193"
    assert response.company_name == "Apple Inc."
    assert response.symbol == "AAPL"
    assert len(response.filings) == 3
    assert response.filings[0].accession == "0000320193-24-000123"
    assert response.filings[0].form_type == "10-K"
    assert response.filings[0].filed_date == date(2024, 11, 1)
    # edgar_url is synthesised from accession + CIK
    assert "320193" in response.filings[0].edgar_url


@pytest.mark.asyncio
async def test_list_filings_cache_hit_skips_tool(recorder: _RecordingClient) -> None:
    """Second list_filings call within TTL returns the cached payload."""
    recorder.respond("get_recent_filings", _AAPL_FILINGS_PAYLOAD)

    await sec_filings_provider.list_filings("AAPL", limit=10)
    await sec_filings_provider.list_filings("AAPL", limit=10)

    # Only one upstream call — second was a cache hit.
    assert sum(1 for c in recorder.calls if c["name"] == "get_recent_filings") == 1


@pytest.mark.asyncio
async def test_list_filings_zero_pads_numeric_cik(recorder: _RecordingClient) -> None:
    recorder.respond("get_recent_filings", _AAPL_FILINGS_PAYLOAD)
    await sec_filings_provider.list_filings("320193")
    # Identifier passed through verbatim (zero-padded).
    assert recorder.calls[0]["arguments"]["identifier"] == "0000320193"


@pytest.mark.asyncio
async def test_list_filings_provider_error(recorder: _RecordingClient) -> None:
    recorder.error("get_recent_filings", "boom")
    with pytest.raises(ProviderError) as exc:
        await sec_filings_provider.list_filings("AAPL")
    assert "boom" in str(exc.value)


# ---------------------------------------------------------------------------
# get_filing
# ---------------------------------------------------------------------------


_AAPL_SECTIONS_PAYLOAD = {
    "sections": [
        {"id": "item-1", "title": "Item 1. Business", "text": "We design, " * 100},
        {"id": "item-1a", "title": "Item 1A. Risk Factors", "text": "Macro " * 50},
        {"id": "item-2", "title": "Item 2. Properties", "text": "We own " * 30},
        {"id": "item-3", "title": "Item 3. Legal Proceedings", "text": "None " * 20},
        {"id": "item-7", "title": "Item 7. MD&A", "text": "Revenue " * 200},
        {"id": "item-8", "title": "Item 8. Financial Statements", "text": "BS " * 100},
    ]
}


@pytest.mark.asyncio
async def test_get_filing_assembles_detail(recorder: _RecordingClient) -> None:
    """get_filing calls sections + filings list and builds a FilingDetail."""
    recorder.respond("get_filing_sections", _AAPL_SECTIONS_PAYLOAD)
    recorder.respond("get_recent_filings", _AAPL_FILINGS_PAYLOAD)

    detail = await sec_filings_provider.get_filing(
        "0000320193-24-000123", cik_or_symbol="AAPL"
    )

    assert detail.filing.accession == "0000320193-24-000123"
    assert detail.filing.form_type == "10-K"
    assert len(detail.sections) == 6
    assert detail.sections[1].title == "Item 1A. Risk Factors"
    assert detail.total_chars > 0


@pytest.mark.asyncio
async def test_get_filing_synthesises_metadata_on_miss(
    recorder: _RecordingClient,
) -> None:
    """If the listing no longer shows the accession, return a stub Filing."""
    recorder.respond("get_filing_sections", _AAPL_SECTIONS_PAYLOAD)
    recorder.respond("get_recent_filings", {"filings": []})

    detail = await sec_filings_provider.get_filing("0000000000-99-999999", cik_or_symbol="AAPL")
    assert detail.filing.accession == "0000000000-99-999999"
    assert len(detail.sections) == 6


# ---------------------------------------------------------------------------
# Insider transactions
# ---------------------------------------------------------------------------


_INSIDER_PAYLOAD = {
    "cik": "320193",
    "issuer_name": "Apple Inc.",
    "transactions": [
        # Form 4 sale — code "S" → disposed.
        {
            "accession": "0000320193-24-001000",
            "reporter_name": "Cook Timothy D",
            "reporter_cik": "1214156",
            "issuer_cik": "320193",
            "issuer_name": "Apple Inc.",
            "ticker": "AAPL",
            "form": "4",
            "transaction_date": "2024-12-01",
            "transaction_code": "S",
            "shares": "511000",
            "price_per_share": "190.50",
            "transaction_value": "97345500",
            "reporter_title": "CEO",
        },
        # Form 4 grant — code "A" → acquired.
        {
            "accession": "0000320193-24-001001",
            "reporter_name": "Maestri Luca",
            "reporter_cik": "1545330",
            "issuer_cik": "320193",
            "issuer_name": "Apple Inc.",
            "form": "4",
            "transaction_date": "2024-11-20",
            "transaction_code": "A",
            "shares": "75000",
            "price_per_share": None,
            "reporter_title": "SVP and CFO",
        },
    ],
}


@pytest.mark.asyncio
async def test_list_insider_transactions(recorder: _RecordingClient) -> None:
    recorder.respond("get_insider_transactions", _INSIDER_PAYLOAD)

    response = await sec_filings_provider.list_insider_transactions(
        "AAPL", form_type="4", limit=20
    )

    assert recorder.calls[0]["name"] == "get_insider_transactions"
    assert recorder.calls[0]["arguments"]["form_types"] == ["4"]
    assert recorder.calls[0]["arguments"]["limit"] == 20

    assert response.cik == "0000320193"
    assert response.issuer_name == "Apple Inc."
    assert len(response.transactions) == 2
    cook = response.transactions[0]
    assert cook.reporter_name == "Cook Timothy D"
    assert cook.direction == "disposed"
    assert cook.shares == "511000"
    assert cook.price_per_share == "190.50"
    assert cook.transaction_code == "S"

    maestri = response.transactions[1]
    assert maestri.direction == "acquired"


@pytest.mark.asyncio
async def test_search_companies_wraps_results(recorder: _RecordingClient) -> None:
    recorder.respond(
        "search_companies",
        {
            "results": [
                {"cik": "320193", "name": "Apple Inc.", "ticker": "AAPL"},
                {"cik": "789019", "name": "Microsoft Corporation", "ticker": "MSFT"},
            ]
        },
    )
    rows = await sec_filings_provider.search_companies("apple", limit=5)
    assert len(rows) == 2
    assert rows[0]["cik"] == "0000320193"
    assert rows[0]["ticker"] == "AAPL"


@pytest.mark.asyncio
async def test_search_companies_empty_query_returns_no_call(
    recorder: _RecordingClient,
) -> None:
    rows = await sec_filings_provider.search_companies("  ", limit=5)
    assert rows == []
    assert not any(c["name"] == "search_companies" for c in recorder.calls)
