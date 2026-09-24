"""R15-DATA-050 / R15-DATA-060: disclosures outside NSE coverage answer 200.

A BSE-only name's results calendar is served from BSE's board-meeting feed; a
symbol neither Indian exchange lists answers ``coverage: not_applicable`` with
a note (C3); a US-listed ADR's shareholding answers its 20-F major holders.
A real transport failure still answers 502.

No network: the BSE feed rides ``corporate_disclosures._bse_get_json``, the NSE
calendar ``nse_provider.get_results_calendar`` and EDGAR
``sec_ownership._fetch_text``. Fixtures are live captures from 2026-09-24:
``fixtures/bse/board_meeting_*``, ``fixtures/nse/event_calendar_elcidin_*`` and
``fixtures/sec/`` (the SIFY 20-F index page and the Item 7.A text of the SIFY,
WIT and INFY 20-Fs).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import create_app
from config import DATA_DIR_ENV
from models.sec import Filing, FilingsListResponse
from services import (
    corporate_disclosures,
    data_cache,
    nse_provider,
    sec_filings_provider,
    sec_ownership,
    symbol_resolver,
)
from services.errors import ProviderError

_FIXTURES = Path(__file__).parent / "fixtures"
_SIFY_FILING = Filing(
    accession="0001554855-26-001437",
    cik="1094324",
    company_name="SIFY TECHNOLOGIES LTD",
    form_type="20-F",
    filed_date=date(2026, 6, 26),
    edgar_url="https://www.sec.gov/Archives/edgar/data/1094324/000155485526001437/",
)
_SIFY_DOC = "https://www.sec.gov/Archives/edgar/data/1094324/000155485526001437/sify-20260331.htm"


def _json(name: str) -> Any:
    return json.loads((_FIXTURES / name).read_text())


def _item7a(name: str) -> str:
    return (_FIXTURES / "sec" / f"20f_item7a_{name}_20260924.txt").read_text()


@pytest.fixture(autouse=True)
def _isolate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    symbol_resolver.reset_caches_for_tests()
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    data_cache.reset_for_tests()
    monkeypatch.setattr(sec_filings_provider, "is_available", lambda: False)
    yield
    data_cache.reset_for_tests()


@pytest.fixture
def client() -> TestClient:
    """The real app: its one ProviderError handler maps provider failures
    (R15-DATA-061)."""
    return TestClient(create_app())


def _serve_board_meetings(monkeypatch: pytest.MonkeyPatch, by_code: dict[str, Any]) -> None:
    def fake(url: str, params: dict[str, str]) -> Any:
        assert url == corporate_disclosures._BSE_BOARD_MEETING_URL
        payload = by_code[params["scripcode"]]
        if isinstance(payload, Exception):
            raise payload
        return payload

    monkeypatch.setattr(corporate_disclosures, "_bse_get_json", fake)


def _nse_must_not_run(symbol: str) -> list[dict]:
    raise AssertionError(f"NSE calendar must not run for BSE-only {symbol}")


# ---------------------------------------------------------------------------
# Results calendar: BSE board-meeting lane.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("symbol", "code", "fixture", "latest"),
    [
        ("JONJUA", "542446", "board_meeting_542446_jonjua_20260924.json", date(2026, 9, 7)),
        ("DAL", "539681", "board_meeting_539681_dal_20260924.json", date(2026, 8, 12)),
    ],
)
def test_a_bse_only_results_calendar_is_served_from_bse(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    symbol: str,
    code: str,
    fixture: str,
    latest: date,
) -> None:
    monkeypatch.setattr(nse_provider, "get_results_calendar", _nse_must_not_run)
    _serve_board_meetings(monkeypatch, {code: _json(f"bse/{fixture}")})

    resp = client.get("/disclosures/results", params={"symbol": symbol})
    assert resp.status_code == 200
    body = resp.json()
    assert body["coverage"] == "covered" and body["sources"] == ["BSE"]
    assert body["count"] == len(body["events"]) > 0
    assert body["events"][0]["date"] == latest.isoformat()
    assert {e["exchange"] for e in body["events"]} == {"BSE"}
    assert any(e["purpose"] == "Results" for e in body["events"])


def test_elcidins_bse_q1_results_meeting_is_served_when_nse_has_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        nse_provider,
        "get_results_calendar",
        lambda symbol: _json("nse/event_calendar_elcidin_20260924.json"),
    )
    _serve_board_meetings(
        monkeypatch, {"503681": _json("bse/board_meeting_503681_elcidin_20260924.json")}
    )

    response = corporate_disclosures.get_results_calendar("ELCIDIN")
    assert response.sources == ["NSE", "BSE"]
    latest = response.events[0]
    assert (latest.date, latest.purpose, latest.exchange) == (date(2026, 8, 13), "Results", "BSE")


def test_a_dual_listed_meeting_on_both_feeds_is_one_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The NSE calendar row is the verbatim observed shape re-dated onto the
    BSE feed's 17 Jul 2026 RELIANCE results meeting."""
    nse_row = dict(_json("nse/event_calendar.json")[1], date="17-Jul-2026")
    monkeypatch.setattr(nse_provider, "get_results_calendar", lambda symbol: [nse_row])
    _serve_board_meetings(
        monkeypatch, {"500325": _json("bse/board_meeting_500325_reliance_20260924.json")}
    )

    events = corporate_disclosures.get_results_calendar("RELIANCE").events
    on_the_day = [e for e in events if e.date == date(2026, 7, 17)]
    assert len(on_the_day) == 1
    assert on_the_day[0].exchange == "NSE+BSE"
    assert on_the_day[0].purpose == "Financial Results"


def test_one_failing_results_lane_is_recorded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        nse_provider,
        "get_results_calendar",
        lambda symbol: (_ for _ in ()).throw(ProviderError("nse_direct: blocked (HTTP 401)")),
    )
    _serve_board_meetings(
        monkeypatch, {"503681": _json("bse/board_meeting_503681_elcidin_20260924.json")}
    )

    response = corporate_disclosures.get_results_calendar("ELCIDIN")
    assert response.sources == ["BSE"] and "NSE" in response.errors
    assert response.count > 0


def test_a_results_transport_failure_is_still_a_502(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(nse_provider, "get_results_calendar", _nse_must_not_run)
    _serve_board_meetings(
        monkeypatch, {"542446": ProviderError("bse announcements: transport failure: reset")}
    )

    resp = client.get("/disclosures/results", params={"symbol": "JONJUA"})
    assert resp.status_code == 502
    assert "every results source failed" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Out of coverage answers 200 (C3).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/disclosures/results",
        "/disclosures/shareholding",
        "/disclosures/corporate-actions",
        "/disclosures/deals",
        "/disclosures/announcements",
    ],
)
def test_a_us_symbol_is_not_applicable_not_a_502(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    def no_network(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("an out-of-coverage symbol must not reach an exchange")

    monkeypatch.setattr(corporate_disclosures, "_bse_get_json", no_network)
    resp = client.get(path, params={"symbol": "AAPL"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["coverage"] == "not_applicable"
    assert body["count"] == 0
    assert "AAPL is not an NSE/BSE instrument" in body["note"]


def test_sast_for_a_bse_only_name_is_venue_not_covered(client: TestClient) -> None:
    resp = client.get("/disclosures/deals", params={"symbol": "JONJUA", "kind": "sast"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["coverage"] == "venue_not_covered"
    assert "BSE-only" in body["note"]


# ---------------------------------------------------------------------------
# The 20-F major-holders lane (R15-DATA-060).
# ---------------------------------------------------------------------------


def test_sify_20f_holders_parse() -> None:
    holders, as_of = sec_ownership.parse_major_shareholders(_item7a("sify"))
    assert as_of == date(2026, 3, 31)
    assert [(h.holder, h.percent) for h in holders] == [
        ("Infinity Capital Ventures, LP", 7.56),
        ("Vegesna Family Trust, LP", 0.34),
        ("Raju Vegesna Infotech & Industries Private Limited, Visakhapatnam", 7.90),
        ("Ramanand Core Investment Company Private Limited, Visakhapatnam", 67.98),
    ]


def test_wit_20f_holders_parse_without_percent_signs() -> None:
    """Pinned on a layout the parser was not written against: a class column
    ("Equity") between name and shares, footnote markers, no % sign."""
    holders, as_of = sec_ownership.parse_major_shareholders(_item7a("wit"))
    assert as_of == date(2026, 3, 31)
    assert [(h.holder, h.percent) for h in holders] == [
        ("Azim H. Premji", 72.62),
        ("Hasham Traders", 17.99),
        ("Prazim Traders", 20.60),
        ("Zash Traders", 21.00),
        ("Azim Premji Trust", 6.49),
    ]


def test_infy_20f_holders_take_the_newest_of_three_columns() -> None:
    """Pinned on a multi-date table the parser was not written against: INFY
    reports May 20 2026, Mar 31 2025 and Mar 31 2024 newest-first."""
    holders, as_of = sec_ownership.parse_major_shareholders(_item7a("infy"))
    assert as_of == date(2026, 5, 20)
    assert [(h.holder, h.percent) for h in holders] == [
        ("Shareholding of all directors and officers as a group", 2.53),
        ("Life Insurance Corporation of India", 10.81),
    ]


def _serve_sify_20f(monkeypatch: pytest.MonkeyPatch, document: str | Exception) -> list[str]:
    fetched: list[str] = []

    async def list_filings(symbol: str, form_type: str | None = None, limit: int = 40) -> Any:
        assert (symbol, form_type) == ("SIFY", "20-F")
        return FilingsListResponse(
            cik="1094324", company_name="SIFY TECHNOLOGIES LTD", filings=[_SIFY_FILING]
        )

    async def fetch(url: str) -> str:
        fetched.append(url)
        if url.endswith("-index.htm"):
            return (_FIXTURES / "sec" / "20f_index_sify_20260924.htm").read_text()
        if isinstance(document, Exception):
            raise document
        return document

    monkeypatch.setattr(sec_filings_provider, "is_available", lambda: True)
    monkeypatch.setattr(sec_filings_provider, "list_filings", list_filings)
    monkeypatch.setattr(sec_ownership, "_fetch_text", fetch)
    return fetched


def test_sify_shareholding_serves_its_20f_holders(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fetched = _serve_sify_20f(monkeypatch, _item7a("sify"))

    resp = client.get("/disclosures/shareholding", params={"symbol": "SIFY"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["coverage"] == "covered" and body["provider"] == "sec-20f"
    assert body["patterns"] == []
    assert body["source_url"] == _SIFY_DOC
    assert fetched == [f"{_SIFY_FILING.edgar_url}{_SIFY_FILING.accession}-index.htm", _SIFY_DOC]
    assert len(body["major_shareholders"]) == 4
    assert body["major_shareholders"][3] == {
        "holder": "Ramanand Core Investment Company Private Limited, Visakhapatnam",
        "percent": 67.98,
        "as_of": "2026-03-31",
    }
    assert "20-F filed 2026-06-26" in body["note"]


def test_the_shareholding_tool_serves_the_20f_holders(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    from services import agent_tools
    from services.agent_tools import disclosure_tools

    _serve_sify_20f(monkeypatch, _item7a("sify"))
    disclosure_tools.register()
    try:
        result = asyncio.run(agent_tools.invoke_tool("shareholding_pattern", {"symbol": "SIFY"}))
    finally:
        agent_tools.reset_for_tests()
    assert result["ok"] is True and result["provider"] == "sec-20f"
    assert result["major_shareholders"][0]["holder"] == "Infinity Capital Ventures, LP"


def test_an_unreadable_20f_stays_not_applicable_and_says_why(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _serve_sify_20f(monkeypatch, ProviderError("sec 20-F: HTTP 503 for the document"))

    resp = client.get("/disclosures/shareholding", params={"symbol": "SIFY"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["coverage"] == "not_applicable" and body["major_shareholders"] == []
    assert "could not be read" in body["note"] and "HTTP 503" in body["note"]
