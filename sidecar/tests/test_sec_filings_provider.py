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
def recorder(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> _RecordingClient:
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


@pytest.mark.asyncio
async def test_is_error_payload_marks_the_provider_down(
    recorder: _RecordingClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An ``isError`` tool result is a failed call: the health flags record it and
    status reports unavailable until the next success (R15-DATA-083)."""
    recorder.respond("search_companies", {"results": []})
    await sec_filings_provider.search_companies("apple")
    assert (await sec_filings_provider.status())["lastToolCallOk"] is True

    async def _is_error(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return {"isError": True, "content": [{"type": "text", "text": "upstream 500"}]}

    monkeypatch.setattr(recorder, "call_tool", _is_error)
    with pytest.raises(ProviderError, match="upstream 500"):
        await sec_filings_provider.search_companies("nvidia")
    status = await sec_filings_provider.status()
    assert status["lastToolCallOk"] is False
    assert "upstream 500" in status["lastError"]
    assert status["available"] is False


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

    response = await sec_filings_provider.list_filings("AAPL", form_type="10-K", limit=20)

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

    detail = await sec_filings_provider.get_filing("0000320193-24-000123", cik_or_symbol="AAPL")

    assert detail.filing.accession == "0000320193-24-000123"
    assert detail.filing.form_type == "10-K"
    assert len(detail.sections) == 6
    assert detail.sections[1].title == "Item 1A. Risk Factors"
    assert detail.total_chars > 0
    # R15-DATA-007: metadata is resolved BEFORE sectioning, so the section
    # call carries the filing's real form_type, not a hard-coded "10-K".
    sections_call = next(c for c in recorder.calls if c["name"] == "get_filing_sections")
    assert sections_call["arguments"]["form_type"] == "10-K"


@pytest.mark.asyncio
async def test_get_filing_sections_with_the_real_form_type(recorder: _RecordingClient) -> None:
    """R15-DATA-007 (case the fix was not written against): a 10-Q inside the
    listing window is sectioned with form_type "10-Q" (not the old hard-coded
    "10-K"), and its edgar_url carries the numeric CIK."""
    recorder.respond("get_filing_sections", _AAPL_SECTIONS_PAYLOAD)
    recorder.respond("get_recent_filings", _AAPL_FILINGS_PAYLOAD)

    detail = await sec_filings_provider.get_filing("0000320193-24-000100", cik_or_symbol="AAPL")

    assert detail.filing.form_type == "10-Q"
    assert "320193" in detail.filing.edgar_url
    sections_call = next(c for c in recorder.calls if c["name"] == "get_filing_sections")
    assert sections_call["arguments"]["form_type"] == "10-Q"


@pytest.mark.asyncio
async def test_get_filing_raises_not_found_when_metadata_is_unavailable(
    recorder: _RecordingClient,
) -> None:
    """R15-DATA-007: an accession outside the issuer's recent-filings window
    must raise a not_found ProviderError, never synthesise a fabricated
    Filing ("10-K filed today", company_name ""). Nothing is cached on a
    miss, and get_filing_sections (upstream) is never even called, since
    metadata resolution now runs first.

    (Was ``test_get_filing_synthesises_metadata_on_miss``, which pinned the
    fabrication this fix removes — rewritten to pin the honest failure.)
    """
    recorder.respond("get_filing_sections", _AAPL_SECTIONS_PAYLOAD)
    recorder.respond("get_recent_filings", {"filings": []})

    with pytest.raises(ProviderError) as exc:
        await sec_filings_provider.get_filing("0000000000-99-999999", cik_or_symbol="AAPL")
    assert exc.value.kind == "not_found"
    assert not any(c["name"] == "get_filing_sections" for c in recorder.calls)
    assert await data_cache.get("sec:filing:0000000000-99-999999", 86400.0) is None


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

    response = await sec_filings_provider.list_insider_transactions("AAPL", form_type="4", limit=20)

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


@pytest.mark.asyncio
async def test_search_companies_decodes_the_live_tool_shape(recorder: _RecordingClient) -> None:
    """R15-UI-032: the real sec-edgar-mcp tool answers
    ``{"success": True, "companies": [...], "count": N}`` with a plural
    ``tickers`` LIST per row (dual-listed companies can carry more than
    one) — not the singular ``ticker``/``symbol`` key the old decode read."""
    recorder.respond(
        "search_companies",
        {
            "success": True,
            "companies": [{"cik": "320193", "name": "Apple Inc.", "tickers": ["AAPL"]}],
            "count": 1,
        },
    )
    rows = await sec_filings_provider.search_companies("Apple", limit=5)
    assert rows == [{"cik": "0000320193", "name": "Apple Inc.", "ticker": "AAPL"}]


@pytest.mark.asyncio
async def test_search_companies_empty_result_is_not_cached(recorder: _RecordingClient) -> None:
    """A query that matches nothing (e.g. a search-as-you-type prefix) must
    not poison the cache for the rest of the TTL window — the next keystroke
    that DOES match has to re-hit the tool, not replay a cached []."""
    recorder.respond("search_companies", {"success": True, "companies": [], "count": 0})
    first = await sec_filings_provider.search_companies("zzz", limit=5)
    assert first == []

    recorder.respond(
        "search_companies",
        {"success": True, "companies": [{"cik": "1", "name": "Zzz Corp", "tickers": ["ZZZ"]}]},
    )
    second = await sec_filings_provider.search_companies("zzz", limit=5)
    assert second == [{"cik": "0000000001", "name": "Zzz Corp", "ticker": "ZZZ"}]
    assert len([c for c in recorder.calls if c["name"] == "search_companies"]) == 2


# ---------------------------------------------------------------------------
# R15-DATA-038: the shapes sec-edgar-mcp 1.0.8 actually sends
# (docs/redesign/verification/r15/surface/panels-layouts/P-sec-parser-check.txt)
# ---------------------------------------------------------------------------


_EDGAR_SECTIONS_PAYLOAD = {
    "success": True,
    "form_type": "10-K",
    "sections": {
        "business": "Apple designs smartphones. " * 370,
        "risk_factors": "Macro conditions may harm demand. " * 290,
        "has_financials": True,
    },
    "available_sections": ["business", "risk_factors", "has_financials"],
}

_EDGAR_INSIDER_PAYLOAD = {
    "success": True,
    "cik": 320193,
    "name": "Apple Inc.",
    "transactions": [
        {
            "filing_date": f"2026-09-{day:02d}",
            "form_type": "4",
            "accession_number": f"0001140361-26-03{n:04d}",
            "company_name": "Apple Inc.",
            "cik": 320193,
            "url": f"https://www.sec.gov/Archives/edgar/data/320193/00011403612603{n:04d}/",
            "sec_url": "https://www.sec.gov/Archives/edgar/data/320193/x.txt",
            "data_source": "SEC EDGAR Filing, extracted directly from insider filing data",
        }
        for n, day in ((7020, 17), (6226, 10), (5636, 3), (5362, 1), (4741, 1))
    ],
    "count": 5,
    "form_types": ["4"],
    "days_back": 90,
    "filing_reference": {"data_source": "SEC EDGAR Insider Trading Filings (Forms 3, 4, 5)"},
}


@pytest.mark.asyncio
async def test_dict_of_sections_parses_to_sections(recorder: _RecordingClient) -> None:
    """The upstream's dict of section strings becomes titled sections; the
    non-text ``has_financials`` flag is not a section."""
    recorder.respond("get_filing_sections", _EDGAR_SECTIONS_PAYLOAD)
    recorder.respond("get_recent_filings", _AAPL_FILINGS_PAYLOAD)

    detail = await sec_filings_provider.get_filing("0000320193-24-000123", cik_or_symbol="AAPL")

    assert [(s.id, s.title) for s in detail.sections] == [
        ("business", "Business"),
        ("risk_factors", "Risk Factors"),
    ]
    assert detail.total_chars > 19000


@pytest.mark.asyncio
async def test_filing_level_form4_rows_are_listed(recorder: _RecordingClient) -> None:
    """Filing-level Form-4 rows (no trade date/code/shares) are kept with their
    filing date, the issuer from the top-level ``name`` and no guessed direction."""
    recorder.respond("get_insider_transactions", _EDGAR_INSIDER_PAYLOAD)

    response = await sec_filings_provider.list_insider_transactions("AAPL", form_type="4")

    assert response.issuer_name == "Apple Inc."
    assert response.cik == "0000320193"
    assert len(response.transactions) == 5
    first = response.transactions[0]
    assert first.accession == "0001140361-26-037020"
    assert first.issuer_cik == "0000320193"
    assert first.transaction_date == date(2026, 9, 17)
    assert first.direction is None and first.shares is None


@pytest.mark.asyncio
async def test_unparseable_success_payload_raises_and_is_not_cached(
    recorder: _RecordingClient,
) -> None:
    """A success payload in a shape the parser does not know is a logged parse
    error, never a cached empty (case the fix was not written against)."""
    recorder.respond("get_insider_transactions", {"success": True, "filings": [{"x": 1}]})
    with pytest.raises(ProviderError, match="could not parse"):
        await sec_filings_provider.list_insider_transactions("AAPL", form_type="4")
    assert await data_cache.get("sec:insider:AAPL:4:50", 3600.0) is None

    recorder.respond("get_filing_sections", {"success": True, "items": {"business": "text"}})
    recorder.respond("get_recent_filings", _AAPL_FILINGS_PAYLOAD)
    with pytest.raises(ProviderError, match="could not parse"):
        await sec_filings_provider.get_filing("0000320193-24-000123", cik_or_symbol="AAPL")
    assert await data_cache.get("sec:filing:0000320193-24-000123", 86400.0) is None


@pytest.mark.asyncio
async def test_in_band_upstream_failure_raises(recorder: _RecordingClient) -> None:
    """sec-edgar-mcp's own ``{"success": false}`` is an error, not an empty list."""
    recorder.respond("get_insider_transactions", {"success": False, "error": "no CIK for XYZ"})
    with pytest.raises(ProviderError, match="no CIK for XYZ"):
        await sec_filings_provider.list_insider_transactions("XYZ")
    assert await data_cache.get("sec:insider:XYZ:all:50", 3600.0) is None


# ---------------------------------------------------------------------------
# R15-DATA-039: a filing's form type is an open string, rows are never dropped
# ---------------------------------------------------------------------------


def _edgar_filings(company: str, cik: str, forms: list[tuple[str, str]]) -> dict[str, Any]:
    """``get_recent_filings`` as sec-edgar-mcp 1.0.8 sends it (FilingInfo.to_dict rows)."""
    return {
        "success": True,
        "filings": [
            {
                "accession_number": accession,
                "filing_date": "2026-06-20T00:00:00",
                "form_type": form,
                "company_name": company,
                "cik": cik,
                "file_number": None,
                "acceptance_datetime": None,
                "period_of_report": None,
                "items": None,
            }
            for form, accession in forms
        ],
        "count": len(forms),
    }


@pytest.mark.asyncio
async def test_foreign_private_issuer_forms_are_listed(recorder: _RecordingClient) -> None:
    """An India ADR files only 20-F and 6-K; every row is listed."""
    recorder.respond(
        "get_recent_filings",
        _edgar_filings(
            "Infosys Ltd",
            "1067491",
            [("20-F", "0001067491-26-000010"), ("6-K", "0001067491-26-000011")],
        ),
    )
    response = await sec_filings_provider.list_filings("INFY")
    assert [f.form_type for f in response.filings] == ["20-F", "6-K"]


@pytest.mark.asyncio
async def test_amendments_and_schedules_are_listed(recorder: _RecordingClient) -> None:
    """Case the fix was not written against: AAPL's 10-K/A and SC 13D rows."""
    recorder.respond(
        "get_recent_filings",
        _edgar_filings(
            "Apple Inc.",
            "320193",
            [
                ("10-K/A", "0000320193-26-000020"),
                ("SC 13D", "0000320193-26-000021"),
                ("10-K", "0000320193-26-000022"),
            ],
        ),
    )
    response = await sec_filings_provider.list_filings("AAPL", limit=3)
    assert [f.form_type for f in response.filings] == ["10-K/A", "SC 13D", "10-K"]


# ---------------------------------------------------------------------------
# R15-LEAD-010 — a listed 10-K resolves outside the unfiltered 40-row window
# ---------------------------------------------------------------------------

#: AAPL-shaped issuer history, newest first: 59 Form 4/144 rows push the
#: 10-K to position 60 and the 10-Q to position 75 of the unfiltered list.
_HEAVY_FILER_FORMS = (
    [("4" if n % 3 else "144", f"0000320193-26-{n:06d}") for n in range(59)]
    + [("10-K", "0000320193-25-000079")]
    + [("4", f"0000320193-25-{n:06d}") for n in range(100, 114)]
    + [("10-Q", "0000320193-25-000071")]
)


def _emulate_upstream(
    recorder: _RecordingClient, forms: list[tuple[str, str]] = _HEAVY_FILER_FORMS
) -> None:
    """sec-edgar-mcp 1.0.8: filter by ``form_type``, then cut to ``limit``."""
    original = recorder.call_tool

    async def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "get_recent_filings":
            form = arguments.get("form_type")
            rows = [(f, a) for f, a in forms if form is None or f == form]
            recorder.respond(
                name, _edgar_filings("Apple Inc.", "320193", rows[: arguments["limit"]])
            )
        return await original(name, arguments)

    recorder.call_tool = call_tool  # type: ignore[method-assign]
    recorder.respond("get_filing_sections", _AAPL_SECTIONS_PAYLOAD)


@pytest.mark.asyncio
@pytest.mark.parametrize("hint", ["10-K", None])
async def test_get_filing_resolves_a_10k_outside_the_unfiltered_window(
    recorder: _RecordingClient, hint: str | None
) -> None:
    _emulate_upstream(recorder)
    detail = await sec_filings_provider.get_filing(
        "0000320193-25-000079", cik_or_symbol="AAPL", form_type=hint
    )
    assert detail.filing.form_type == "10-K"
    sections_call = next(c for c in recorder.calls if c["name"] == "get_filing_sections")
    assert sections_call["arguments"]["form_type"] == "10-K"


@pytest.mark.asyncio
@pytest.mark.parametrize("hint", ["10-Q", None])
async def test_get_filing_resolves_a_deep_10q_too(
    recorder: _RecordingClient, hint: str | None
) -> None:
    """The case the fix was not written against: a 10-Q at position 75."""
    _emulate_upstream(recorder)
    detail = await sec_filings_provider.get_filing(
        "0000320193-25-000071", cik_or_symbol="AAPL", form_type=hint
    )
    assert detail.filing.form_type == "10-Q"


def _emulate_upstream_failing_over_100(
    recorder: _RecordingClient, forms: list[tuple[str, str]] = _HEAVY_FILER_FORMS
) -> None:
    """sec-edgar-mcp 1.0.8 on a heavy filer: every window over 100 rows fails."""
    _emulate_upstream(recorder, forms)
    emulated = recorder.call_tool

    async def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "get_recent_filings" and arguments["limit"] > 100:
            recorder.calls.append({"name": name, "arguments": dict(arguments)})
            return {
                "isError": True,
                "content": [{"type": "text", "text": "cannot unpack non-iterable NoneType object"}],
            }
        return await emulated(name, arguments)

    recorder.call_tool = call_tool  # type: ignore[method-assign]


@pytest.mark.asyncio
@pytest.mark.parametrize("form_type", [None, "10-K"])
async def test_sec_filing_content_tool_opens_with_a_small_window(
    recorder: _RecordingClient, form_type: str | None
) -> None:
    """R15-LEAD-010 regression: the agent/MCP tool must load a filing that
    loaded at base. sec-edgar-mcp fails every window over 100 rows ("cannot
    unpack non-iterable NoneType"), so no lookup may open with one, and the
    tool forwards the caller's form hint."""
    from services.agent_tools import sec_tools

    _emulate_upstream_failing_over_100(recorder)
    args = {"accession": "0000320193-25-000079", "identifier": "AAPL"}
    if form_type:
        args["form_type"] = form_type
    result = await sec_tools._sec_filing_content(args)

    lookups = [c["arguments"] for c in recorder.calls if c["name"] == "get_recent_filings"]
    assert all(lookup["limit"] <= 100 for lookup in lookups), lookups
    assert lookups[0].get("form_type") == form_type
    assert result["ok"] is True, result
    assert result["filing"]["filing"]["form_type"] == "10-K"


@pytest.mark.asyncio
async def test_get_filing_never_widens_past_what_the_upstream_serves(
    recorder: _RecordingClient,
) -> None:
    """A heavy filer's miss past row 100 is an honest not_found after the
    40- and 100-row windows, never a request the upstream cannot serve."""
    older = [("4", f"0000320193-24-{n:06d}") for n in range(60)]
    _emulate_upstream_failing_over_100(recorder, _HEAVY_FILER_FORMS + older)
    with pytest.raises(ProviderError) as info:
        await sec_filings_provider.get_filing("0000320193-99-999999", cik_or_symbol="AAPL")
    assert info.value.kind == "not_found"
    limits = [c["arguments"]["limit"] for c in recorder.calls if c["name"] == "get_recent_filings"]
    assert limits == [40, 100]
