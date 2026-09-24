"""The disclosure agent tools (``corporate_announcements``,
``shareholding_pattern``): the announcements cache lives in the service, so the
tool, research and the panel route share one fetch (R15-DATA-074)."""

from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from config import DATA_DIR_ENV
from models.announcements import AnnouncementWindow, ShareholdingPattern, ShareholdingResponse
from routers import disclosures
from services import corporate_disclosures, data_cache, nse_provider, symbol_resolver
from services.agent_tools import disclosure_tools
from services.agent_tools.catalog import CAPABILITY_CATALOG
from services.search import extract


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> object:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    data_cache.reset_for_tests()
    yield tmp_path
    data_cache.reset_for_tests()


@pytest.fixture
def lane_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Count the exchange-lane fetches behind the merged feed."""
    calls: list[str] = []

    def lane(name: str):  # noqa: ANN202
        def fetch(bare: str, limit: int):  # noqa: ANN202
            calls.append(name)
            return [], AnnouncementWindow(window_start=None, window_end=date(2026, 9, 23))

        return fetch

    monkeypatch.setattr(symbol_resolver, "is_nse_symbol", lambda s: True)
    monkeypatch.setattr(symbol_resolver, "is_bse_symbol", lambda s: True)
    monkeypatch.setattr(corporate_disclosures, "_fetch_nse_announcements", lane("NSE"))
    monkeypatch.setattr(corporate_disclosures, "_fetch_bse_announcements", lane("BSE"))
    return calls


def test_two_tool_calls_fetch_the_lanes_once(lane_calls: list[str]) -> None:
    for _ in range(2):
        result = asyncio.run(disclosure_tools._corporate_announcements({"symbol": "RELIANCE"}))
        assert result["ok"] is True
    assert lane_calls == ["NSE", "BSE"]


def test_router_then_tool_fetch_the_lanes_once(lane_calls: list[str]) -> None:
    app = FastAPI()
    app.include_router(disclosures.router)
    resp = TestClient(app).get(
        "/disclosures/announcements", params={"symbol": "RELIANCE", "limit": 20}
    )
    assert resp.status_code == 200

    result = asyncio.run(
        disclosure_tools._corporate_announcements({"symbol": "RELIANCE", "limit": 20})
    )
    assert result["ok"] is True
    assert lane_calls == ["NSE", "BSE"]


def test_shareholding_payload_with_a_bse_split_carries_no_contradicting_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-AGENT-060: the split rides the typed fields; no prose note denies it."""
    pattern = ShareholdingPattern(
        symbol="RELIANCE",
        quarter_end=date(2026, 6, 30),
        promoter_percent=50.0,
        fii_percent=19.1,
        dii_percent=19.4,
        institutions_percent=38.5,
        source="NSE",
        split_source="BSE",
        split_as_of=date(2026, 6, 30),
        split_basis="filed",
    )
    monkeypatch.setattr(
        corporate_disclosures,
        "get_shareholding",
        lambda symbol: ShareholdingResponse(symbol="RELIANCE", count=1, patterns=[pattern]),
    )
    result = asyncio.run(disclosure_tools._shareholding_pattern({"symbol": "RELIANCE"}))

    assert result["ok"] is True
    assert "note" not in result
    assert result["patterns"][0]["split_source"] == "BSE"
    description = CAPABILITY_CATALOG["shareholding_pattern"].description
    assert "FII/DII" in description and "pledge" in description
    assert "xbrl" not in description.lower()


# --- R15-RESEARCH-030: earnings_call_transcript over the recorded TCS feeds ---

_FIXTURES = Path(__file__).parent / "fixtures"
_TCS_NSE = json.loads(
    (_FIXTURES / "nse" / "announcements_hdfcbank_tcs_20260924.json").read_text(encoding="utf-8")
)["TCS"]
_TCS_BSE = json.loads(
    (_FIXTURES / "bse" / "announcements_hdfcbank_tcs_20260924.json").read_text(encoding="utf-8")
)["TCS"]
#: The first three pages of TCS's filed Q1 FY27 transcript (verbatim trim).
_TCS_TRANSCRIPT_PDF = _FIXTURES / "nse" / "transcript_tcs_20260715_trimmed.pdf"
_TCS_TRANSCRIPT_URL = (
    "https://nsearchives.nseindia.com/corporate/TCS_CORPCS_15072026193646_SEInt15072026_Signed.pdf"
)


@pytest.fixture
def recorded_tcs(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Serve the recorded TCS feeds and transcript PDF; return the fetched URLs."""
    fetched: list[str] = []

    async def pdf_fetch(url: str, **_: object) -> tuple[int, bytes]:
        fetched.append(url)
        return 200, _TCS_TRANSCRIPT_PDF.read_bytes()

    def bse_json(url: str, params: dict[str, str]) -> dict:  # noqa: ARG001
        rows = _TCS_BSE if params.get("pageno") == "1" else []
        return {"Table": rows, "Table1": [{"ROWCNT": len(_TCS_BSE)}]}

    monkeypatch.setattr(
        nse_provider, "get_corporate_announcements", lambda s, limit=50: _TCS_NSE[:limit]
    )
    monkeypatch.setattr(corporate_disclosures, "_bse_get_json", bse_json)
    monkeypatch.setattr(extract, "_default_resolver", lambda host: ["23.40.0.10"])
    monkeypatch.setattr(extract, "_default_pdf_fetch", pdf_fetch)
    return fetched


def test_earnings_call_transcript_reads_the_recorded_concall(recorded_tcs: list[str]) -> None:
    result = asyncio.run(disclosure_tools._earnings_call_transcript({"symbol": "TCS"}))

    assert result["ok"] is True and result["available"] is True
    assert (result["symbol"], result["filing_date"], result["source"]) == (
        "TCS",
        "2026-07-15",
        "NSE",
    )
    assert result["url"] == _TCS_TRANSCRIPT_URL
    assert recorded_tcs == [_TCS_TRANSCRIPT_URL]
    assert "Transcript for Earnings Conference Call" in result["text"]
    assert "K Krithivasan" in result["text"]


def test_earnings_call_transcript_selects_by_quarter(recorded_tcs: list[str]) -> None:
    june = asyncio.run(
        disclosure_tools._earnings_call_transcript({"symbol": "TCS", "quarter": "2026-06-30"})
    )
    assert june["filing_date"] == "2026-07-15"
    march = asyncio.run(
        disclosure_tools._earnings_call_transcript({"symbol": "TCS", "quarter": "2026-03-31"})
    )
    assert march["ok"] is True and march["available"] is False
    assert "quarter ended 2026-03-31" in march["reason"]


def test_earnings_call_transcript_for_a_us_symbol_is_honestly_unavailable() -> None:
    result = asyncio.run(disclosure_tools._earnings_call_transcript({"symbol": "AAPL"}))

    assert result["ok"] is True and result["available"] is False
    assert "not an NSE/BSE instrument" in result["reason"]
