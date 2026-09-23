"""R7 Component 3 — corporate_disclosures service + the disclosure agent tools.

All network is mocked at the two seams (:mod:`services.nse_provider`'s raw
accessors and ``corporate_disclosures._bse_get_json``) so NO test hits a live
exchange. The fixtures are VERBATIM trims of live responses: the NSE ones from
the Component-2 probe (``tests/fixtures/nse/``) and the BSE
``AnnSubCategoryGetData`` one from the Component-3 probe (2026-06-10 IST, scrip
500325 RELIANCE — ``tests/fixtures/bse/ann_sub_category_get_data.json``).

Covered: the observed-shape parses for both lanes, the merged feed's
``(symbol, headline-hash, date)`` dedup, exchange filtering + master gating
(RELIANCE dual-listed, ICONIKSPEV BSE-only), the honest partial degrade when
one lane fails, the all-lanes-failed error, the results-calendar and
shareholding parses (FII/DII honest ``None``), and the two agent-tool handlers.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from config import DATA_DIR_ENV
from services import agent_tools, corporate_disclosures, data_cache, nse_provider, symbol_resolver
from services.errors import ProviderError

_NSE_FIXTURES = Path(__file__).parent / "fixtures" / "nse"
_BSE_FIXTURES = Path(__file__).parent / "fixtures" / "bse"

_NSE_ANNOUNCEMENTS = json.loads((_NSE_FIXTURES / "corporate_announcements.json").read_text())
_NSE_EVENTS = json.loads((_NSE_FIXTURES / "event_calendar.json").read_text())
_NSE_SHAREHOLDING = json.loads((_NSE_FIXTURES / "corporate_share_holdings_master.json").read_text())
_BSE_ANNOUNCEMENTS = json.loads((_BSE_FIXTURES / "ann_sub_category_get_data.json").read_text())


@pytest.fixture(autouse=True)
def _isolate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    symbol_resolver.reset_caches_for_tests()
    # The announcements tool reads through the service's data_cache
    # (R15-DATA-074): pin it to a per-test db so no run serves another's rows.
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    data_cache.reset_for_tests()
    yield
    data_cache.reset_for_tests()


def _patch_nse_announcements(monkeypatch: pytest.MonkeyPatch, rows: list[dict] | Exception) -> None:
    def fake(symbol: str, limit: int = 50) -> list[dict]:  # noqa: ARG001
        if isinstance(rows, Exception):
            raise rows
        return rows[: max(limit, 0)]

    monkeypatch.setattr(nse_provider, "get_corporate_announcements", fake)


def _patch_bse_payload(monkeypatch: pytest.MonkeyPatch, payload: object | Exception) -> list[dict]:
    """Serve ``payload`` as page 1 of the BSE feed; later pages are empty (the
    trimmed fixtures hold fewer rows than their ``ROWCNT``)."""
    calls: list[dict] = []

    def fake(url: str, params: dict[str, str]) -> object:
        calls.append({"url": url, "params": params})
        if isinstance(payload, Exception):
            raise payload
        if params.get("pageno") != "1" and isinstance(payload, dict):
            return dict(payload, Table=[])
        return payload

    monkeypatch.setattr(corporate_disclosures, "_bse_get_json", fake)
    return calls


# ---------------------------------------------------------------------------
# The merged announcement feed.
# ---------------------------------------------------------------------------


def test_merged_feed_combines_both_exchanges_newest_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_nse_announcements(monkeypatch, _NSE_ANNOUNCEMENTS)
    calls = _patch_bse_payload(monkeypatch, _BSE_ANNOUNCEMENTS)

    response = corporate_disclosures.get_announcements("RELIANCE")

    assert response.symbol == "RELIANCE"
    assert response.exchange is None
    assert response.sources == ["NSE", "BSE"]
    assert response.errors == {}
    # The fixtures' six rows are three filings on both exchanges: each BSE row
    # pairs with its NSE twin (R15-DATA-020), so three NSE items remain.
    assert response.count == len(response.announcements) == 3
    exchanges = {item.exchange for item in response.announcements}
    assert exchanges == {"NSE"}
    # Newest first.
    stamps = [item.ts for item in response.announcements if item.ts is not None]
    assert stamps == sorted(stamps, reverse=True)
    # The BSE lane was asked with the observed query contract, scrip-code keyed,
    # from page 1 (it pages on while the window's ROWCNT rows remain).
    params = calls[0]["params"]
    assert params["pageno"] == "1"
    assert params["strScrip"] == "500325"
    assert params["strSearch"] == "P" and params["strType"] == "C"


def test_observed_nse_row_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_nse_announcements(monkeypatch, _NSE_ANNOUNCEMENTS)
    _patch_bse_payload(monkeypatch, ProviderError("bse down"))

    response = corporate_disclosures.get_announcements("RELIANCE", exchange="NSE")
    first = response.announcements[0]
    assert first.exchange == "NSE"
    assert first.symbol == "RELIANCE"
    assert first.category == "Updates"
    assert first.headline.startswith("This is further to the disclosure dated June 4, 2026")
    assert first.attachment_url == (
        "https://nsearchives.nseindia.com/corporate/kavinavora_09062026194521_SE_09062026.pdf"
    )
    # sort_date "2026-06-09 19:45:31" is IST wall-clock → tz-aware.
    assert first.ts is not None and first.ts.tzinfo is not None
    assert (first.ts.year, first.ts.month, first.ts.day) == (2026, 6, 9)
    assert (first.ts.hour, first.ts.minute) == (19, 45)


def test_observed_bse_row_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_bse_payload(monkeypatch, _BSE_ANNOUNCEMENTS)

    response = corporate_disclosures.get_announcements("RELIANCE", exchange="BSE")
    assert response.sources == ["BSE"]
    first = response.announcements[0]
    assert first.exchange == "BSE"
    assert first.symbol == "RELIANCE"  # the payload has only SCRIP_CD — bare stamped
    assert first.headline == (
        "Update On Institutional Investors'' Meeting - "
        "ICICI Securities India Investor Conference 2026"
    )
    assert first.category == "Company Update"
    assert first.attachment_url == (
        "https://www.bseindia.com/xml-data/corpfiling/AttachLive/"
        "94035dd9-d667-49df-8161-a90b6c8cd851.pdf"
    )
    assert first.ts is not None and first.ts.tzinfo is not None
    assert (first.ts.year, first.ts.month, first.ts.day) == (2026, 6, 9)


@pytest.mark.parametrize(
    "index",
    [
        0,  # 2026-06-09 ICICI update: BSE HEADLINE truncated, quotes/spaces doubled
        1,  # 2026-06-08 AGM presentation: NSE wraps the title in "has informed ..."
    ],
)
def test_dedup_collapses_the_same_story_across_exchanges(
    monkeypatch: pytest.MonkeyPatch, index: int
) -> None:
    """R15-DATA-020: the UNMODIFIED NSE and BSE fixture rows of one RELIANCE
    filing (NSE's attchmntText body; BSE's short NEWSSUB subject plus its
    HEADLINE body) are ONE item, and NSE wins."""
    _patch_nse_announcements(monkeypatch, _NSE_ANNOUNCEMENTS[index : index + 1])
    bse_rows = _BSE_ANNOUNCEMENTS["Table"][index : index + 1]
    _patch_bse_payload(monkeypatch, {"Table": bse_rows, "Table1": [{"ROWCNT": 1}]})

    response = corporate_disclosures.get_announcements("RELIANCE")
    assert response.sources == ["NSE", "BSE"]
    assert response.count == 1
    assert response.announcements[0].exchange == "NSE"  # the NSE lane merges first


def test_dedup_keeps_two_distinct_same_day_filings(monkeypatch: pytest.MonkeyPatch) -> None:
    """A case the fix was not written against: two different filings by the same
    company on the same IST day stay two."""
    first = _NSE_ANNOUNCEMENTS[0]
    other = dict(
        first,
        attchmntText="Reliance Industries Limited has informed the Exchange regarding "
        "'Allotment of Non-Convertible Debentures on private placement basis'.",
        sort_date="2026-06-09 11:02:10",
    )
    _patch_nse_announcements(monkeypatch, [first, other])
    _patch_bse_payload(monkeypatch, ProviderError("bse down"))

    response = corporate_disclosures.get_announcements("RELIANCE")
    assert response.count == 2


# Live feeds captured 2026-09-23 IST (verbatim rows): each exchange's text for
# one filing differs (NSE's "has informed the Exchange about Credit Rating"
# against BSE's "Intimation of Credit Rating ..."; INFY's BSE body is just
# "Enclosed"), so only a fuzzy cross-feed pairing collapses them (R15-DATA-020).
_CROSSFEED_NSE = json.loads((_NSE_FIXTURES / "announcements_crossfeed_20260923.json").read_text())
_CROSSFEED_BSE = json.loads((_BSE_FIXTURES / "announcements_crossfeed_20260923.json").read_text())


def _serve_crossfeed(monkeypatch: pytest.MonkeyPatch, nse_rows: list, bse_rows: list) -> None:
    _patch_nse_announcements(monkeypatch, nse_rows)
    _patch_bse_payload(monkeypatch, {"Table": bse_rows, "Table1": [{"ROWCNT": len(bse_rows)}]})


@pytest.mark.parametrize(
    ("symbol", "day", "filings"),
    [
        ("RELIANCE", "2026-09-09", 1),  # credit rating: NSE 20:35, BSE 20:37
        ("RELIANCE", "2026-09-21", 2),  # two investor-meeting filings, each on both feeds
        ("TCS", "2026-09-05", 1),  # HyperVault press release: BSE body "Enclosed Press Release"
        (
            "INFY",
            "2026-07-28",
            2,
        ),  # earnings-call transcript + a press release, BSE body "Enclosed"
    ],
)
def test_live_cross_feed_pairs_collapse_to_the_nse_item(
    monkeypatch: pytest.MonkeyPatch, symbol: str, day: str, filings: int
) -> None:
    nse_rows = [r for r in _CROSSFEED_NSE[symbol] if r["sort_date"].startswith(day)]
    bse_rows = [r for r in _CROSSFEED_BSE[symbol] if r["NEWS_DT"].startswith(day)]
    assert len(nse_rows) == len(bse_rows) == filings
    _serve_crossfeed(monkeypatch, nse_rows, bse_rows)

    response = corporate_disclosures.get_announcements(symbol)
    assert response.count == filings
    assert {item.exchange for item in response.announcements} == {"NSE"}


def test_two_different_filings_minutes_apart_stay_separate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # RELIANCE 2026-09-21: NSE's 19:11 update on the J.P. Morgan meeting and BSE's
    # 19:08 notice of the BofA meeting are different filings 3 minutes apart
    # sharing the "Company executives ... Institutional Investors' Meeting" text.
    nse_rows = [r for r in _CROSSFEED_NSE["RELIANCE"] if r["sort_date"] == "2026-09-21 19:11:29"]
    bse_rows = [
        r for r in _CROSSFEED_BSE["RELIANCE"] if r["NEWS_DT"].startswith("2026-09-21T19:08")
    ]
    assert len(nse_rows) == len(bse_rows) == 1
    _serve_crossfeed(monkeypatch, nse_rows, bse_rows)

    response = corporate_disclosures.get_announcements("RELIANCE")
    assert [item.exchange for item in response.announcements] == ["NSE", "BSE"]


def test_live_hdfcbank_pairs_collapse(monkeypatch: pytest.MonkeyPatch) -> None:
    # A case the pairing was not written against: HDFCBANK's 09-06 stock-option
    # grant and its 08-19 credit rating + SEBI intimation (27 minutes apart, so
    # the rating never pairs with the other day-mate).
    _serve_crossfeed(monkeypatch, _CROSSFEED_NSE["HDFCBANK"], _CROSSFEED_BSE["HDFCBANK"])

    response = corporate_disclosures.get_announcements("HDFCBANK")
    assert response.count == 3
    assert {item.exchange for item in response.announcements} == {"NSE"}


# Live feeds captured 2026-09-24 (40 rows per lane, verbatim): NSE's templated
# text ("HDFC Bank Limited has informed the Exchange about Schedule of meet")
# shares under 60% of its words with BSE's subject ("Announcement under
# Regulation 30 (LODR)-Analyst / Investor Meet - Intimation"), so these pairs
# collapse on the exchanges' own category instead (R15-DATA-020 residual).
_HDFC_TCS_NSE = json.loads((_NSE_FIXTURES / "announcements_hdfcbank_tcs_20260924.json").read_text())
_HDFC_TCS_BSE = json.loads((_BSE_FIXTURES / "announcements_hdfcbank_tcs_20260924.json").read_text())


def _merged_live_feed(monkeypatch: pytest.MonkeyPatch, symbol: str) -> list[Any]:
    _serve_crossfeed(monkeypatch, _HDFC_TCS_NSE[symbol], _HDFC_TCS_BSE[symbol])
    return corporate_disclosures.get_announcements(symbol, limit=100).announcements


def test_live_hdfcbank_schedule_of_meet_pairs_collapse(monkeypatch: pytest.MonkeyPatch) -> None:
    items = _merged_live_feed(monkeypatch, "HDFCBANK")
    bse_meets = [
        i
        for i in items
        if i.exchange == "BSE" and i.headline.endswith("Analyst / Investor Meet - Intimation")
    ]
    assert bse_meets == []  # every one paired with NSE's "Schedule of meet"
    # 80 rows: 32 BSE copies of an NSE filing and one NSE re-dissemination.
    assert len(items) == 47


def test_live_tcs_pairs_collapse_on_category(monkeypatch: pytest.MonkeyPatch) -> None:
    """The case the category rule was not written against (TCS)."""
    items = _merged_live_feed(monkeypatch, "TCS")
    hypervault = [i for i in items if i.ts.strftime("%m-%d") == "09-05"]
    newspaper_0917 = [i for i in items if i.ts.strftime("%m-%d %H") == "09-17 18"]
    newspaper_0710 = [i for i in items if i.ts.strftime("%m-%d %H") == "07-10 18"]
    for rows in (hypervault, newspaper_0917, newspaper_0710):
        assert [i.exchange for i in rows] == ["NSE"]
    acquisition_day = [i for i in items if i.ts.strftime("%m-%d %H") == "08-24 16"]
    # NSE's acquisition, press release and order filings; BSE's copies of the
    # acquisition and the order collapse, its press release pairs on text.
    assert sorted(i.category for i in acquisition_day) == sorted(
        ["Acquisition", "Press Release", "Bagging/Receiving of orders/contracts"]
    )


def test_two_same_category_filings_in_one_window_stay_separate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A BSE analyst-meet item with two NSE analyst-meet candidates in its window
    is ambiguous: no category pairing, every row stays."""
    nse_recording = next(
        r for r in _HDFC_TCS_NSE["HDFCBANK"] if r["sort_date"] == "2026-07-18 21:41:03"
    )
    other_meet = next(
        r for r in _HDFC_TCS_NSE["HDFCBANK"] if r["sort_date"].startswith("2026-08-16")
    )
    other_meet = {**other_meet, "sort_date": "2026-07-18 21:46:00", "an_dt": "18-Jul-2026 21:46:00"}
    bse_outcome = next(
        r for r in _HDFC_TCS_BSE["HDFCBANK"] if r["NEWS_DT"].startswith("2026-07-18T21:44")
    )
    _serve_crossfeed(monkeypatch, [other_meet, nse_recording], [bse_outcome])

    response = corporate_disclosures.get_announcements("HDFCBANK")
    assert sorted(i.exchange for i in response.announcements) == ["BSE", "NSE", "NSE"]


def test_bse_only_symbol_skips_the_nse_lane(monkeypatch: pytest.MonkeyPatch) -> None:
    """ICONIKSPEV is BSE-only — the NSE lane is not applicable, not an error."""

    def nse_must_not_run(symbol: str, limit: int = 50) -> list[dict]:  # noqa: ARG001
        raise AssertionError("NSE lane must not run for a BSE-only symbol")

    monkeypatch.setattr(nse_provider, "get_corporate_announcements", nse_must_not_run)
    bse_payload = {
        "Table": [dict(_BSE_ANNOUNCEMENTS["Table"][0], SCRIP_CD=511260)],
        "Table1": [{"ROWCNT": 1}],
    }
    calls = _patch_bse_payload(monkeypatch, bse_payload)

    response = corporate_disclosures.get_announcements("ICONIKSPEV")
    assert response.sources == ["BSE"]
    assert response.errors == {}
    assert response.count == 1
    assert response.announcements[0].symbol == "ICONIKSPEV"
    assert calls[0]["params"]["strScrip"] == "511260"  # scrip-code routed from the master


def test_partial_degrade_records_the_failed_lane(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_nse_announcements(monkeypatch, _NSE_ANNOUNCEMENTS)
    _patch_bse_payload(monkeypatch, ProviderError("bse announcements: HTTP 503"))

    response = corporate_disclosures.get_announcements("RELIANCE")
    assert response.sources == ["NSE"]
    assert "BSE" in response.errors and "503" in response.errors["BSE"]
    assert all(item.exchange == "NSE" for item in response.announcements)


def test_every_lane_failing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_nse_announcements(monkeypatch, ProviderError("nse_direct: blocked"))
    _patch_bse_payload(monkeypatch, ProviderError("bse announcements: HTTP 503"))

    with pytest.raises(ProviderError, match="every announcement source failed"):
        corporate_disclosures.get_announcements("RELIANCE")


def test_unknown_symbol_raises_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch_bse_payload(monkeypatch, _BSE_ANNOUNCEMENTS)

    with pytest.raises(ProviderError, match="not a known NSE/BSE instrument"):
        corporate_disclosures.get_announcements("ZZZNOTREAL")
    assert calls == []


def test_limit_trims_the_merged_feed(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_nse_announcements(monkeypatch, _NSE_ANNOUNCEMENTS)
    _patch_bse_payload(monkeypatch, _BSE_ANNOUNCEMENTS)

    response = corporate_disclosures.get_announcements("RELIANCE", limit=2)
    assert response.count == 2
    assert len(response.announcements) == 2


def test_malformed_bse_payload_is_a_lane_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_nse_announcements(monkeypatch, _NSE_ANNOUNCEMENTS)
    _patch_bse_payload(monkeypatch, {"unexpected": True})

    response = corporate_disclosures.get_announcements("RELIANCE")
    assert response.sources == ["NSE"]
    assert "malformed" in response.errors["BSE"]


def _bse_row(newsid: str, subject: str, day: date) -> dict:
    stamp = f"{day.isoformat()}T17:43:00.00"
    return {
        "NEWSID": newsid,
        "SCRIP_CD": 516078,
        "NEWSSUB": subject,
        "HEADLINE": subject,
        "NEWS_DT": stamp,
        "DT_TM": stamp,
        "CATEGORYNAME": "Company Update",
        "ATTACHMENTNAME": f"{newsid}.pdf",
        "PDFFLAG": 0,
    }


def _patch_bse_feed(
    monkeypatch: pytest.MonkeyPatch, rows: list[dict], page_size: int
) -> list[dict[str, str]]:
    """Emulate the BSE feed: only rows inside the requested strPrevDate..strToDate
    window, ``page_size`` per ``pageno``, with the window's ROWCNT."""
    calls: list[dict[str, str]] = []

    def fake(url: str, params: dict[str, str]) -> object:  # noqa: ARG001
        calls.append(params)
        lo = datetime.strptime(params["strPrevDate"], "%Y%m%d").date()
        hi = datetime.strptime(params["strToDate"], "%Y%m%d").date()
        window = [r for r in rows if lo <= date.fromisoformat(r["NEWS_DT"][:10]) <= hi]
        page = int(params["pageno"])
        return {
            "Table": window[(page - 1) * page_size : page * page_size],
            "Table1": [{"ROWCNT": len(window)}],
        }

    monkeypatch.setattr(corporate_disclosures, "_bse_get_json", fake)
    return calls


def test_bse_lane_reaches_an_infrequent_filers_older_filings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-DATA-019, JUMBO-shaped: a BSE-only filer whose newest filing is 50
    days old. The 30-day window served an empty feed as complete; the filings
    now arrive with the covered window stated."""
    today = corporate_disclosures._today_ist()
    newest = today - timedelta(days=50)
    rows = [
        _bse_row("a1", "Scrutinizers Report", newest),
        _bse_row("a2", "Outcome of AGM", newest - timedelta(days=1)),
        _bse_row("a3", "Financial Results for the quarter ended June 30, 2026", newest),
        _bse_row("a4", "Appointment of Director", newest - timedelta(days=1)),
    ]
    _patch_bse_feed(monkeypatch, rows, page_size=50)

    response = corporate_disclosures.get_announcements("JUMBO", limit=25)
    assert response.sources == ["BSE"]
    assert response.count == 4
    window = response.windows["BSE"]
    assert window.window_end == today
    assert window.window_start == today - timedelta(days=corporate_disclosures._BSE_ANN_WINDOW_DAYS)


def test_bse_lane_pages_until_the_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """A case the fix was not written against: two-row pages stop once the limit
    is reached, and the window starts at the oldest item kept."""
    today = corporate_disclosures._today_ist()
    rows = [_bse_row(f"r{i}", f"Filing number {i}", today - timedelta(days=i)) for i in range(6)]
    calls = _patch_bse_feed(monkeypatch, rows, page_size=2)

    response = corporate_disclosures.get_announcements("JUMBO", limit=3)
    assert [c["pageno"] for c in calls] == ["1", "2"]
    assert [a.headline for a in response.announcements] == [f"Filing number {i}" for i in range(3)]
    assert response.windows["BSE"].window_start == today - timedelta(days=2)


def test_bse_pdfflag_row_resolves_under_the_history_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The fixture's PDFFLAG 1 row (the 2026-06-05 Citi update) is filed under
    AttachHis; a PDFFLAG 0 row stays under AttachLive."""
    _patch_bse_payload(monkeypatch, _BSE_ANNOUNCEMENTS)

    response = corporate_disclosures.get_announcements("RELIANCE", exchange="BSE")
    by_file = {a.attachment_url.rsplit("/", 1)[1]: a.attachment_url for a in response.announcements}
    assert by_file["75dcb382-c995-429e-ac79-be791c57e7c8.pdf"] == (
        "https://www.bseindia.com/xml-data/corpfiling/AttachHis/"
        "75dcb382-c995-429e-ac79-be791c57e7c8.pdf"
    )
    assert by_file["94035dd9-d667-49df-8161-a90b6c8cd851.pdf"].startswith(
        "https://www.bseindia.com/xml-data/corpfiling/AttachLive/"
    )


# ---------------------------------------------------------------------------
# Results calendar.
# ---------------------------------------------------------------------------


def test_results_calendar_parses_and_sorts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nse_provider, "get_results_calendar", lambda symbol: _NSE_EVENTS)

    response = corporate_disclosures.get_results_calendar("RELIANCE")
    assert response.symbol == "RELIANCE"
    assert response.count == len(_NSE_EVENTS)
    purposes = {event.purpose for event in response.events}
    assert "Financial Results" in purposes
    results_event = next(e for e in response.events if e.purpose == "Financial Results")
    assert results_event.date == date(2007, 10, 18)
    assert results_event.company == "Reliance Industries Limited"
    assert results_event.description and "September 30, 2007" in results_event.description
    dates = [event.date for event in response.events if event.date is not None]
    assert dates == sorted(dates, reverse=True)


# ---------------------------------------------------------------------------
# Shareholding pattern.
# ---------------------------------------------------------------------------


def test_shareholding_parses_quarters_newest_first(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import bse_provider

    monkeypatch.setattr(nse_provider, "get_shareholding_master", lambda symbol: _NSE_SHAREHOLDING)
    # The BSE split-enrich lane carries nothing this run — the labeled NSE
    # patterns stand, split honestly None (never fabricated).
    monkeypatch.setattr(bse_provider, "get_shareholding", lambda symbol: [])

    response = corporate_disclosures.get_shareholding("RELIANCE")
    assert response.symbol == "RELIANCE"
    assert response.count == 2
    latest, prior = response.patterns
    assert latest.quarter_end == date(2026, 3, 31)
    assert latest.promoter_percent == 50.0
    assert latest.public_percent == 50.0
    # The NSE "public" bucket folds institutions in — it is labeled as such and
    # the non-institutional slice stays None until the BSE XBRL supplies it.
    assert latest.public_basis == "incl. institutions"
    assert latest.public_non_institutional_percent is None
    assert latest.employee_trusts_percent == 0.0
    # NSE-first for a dual-listed name — the source label + honest None FII/DII.
    assert latest.source == "NSE"
    assert latest.fii_percent is None and latest.dii_percent is None
    assert latest.institutions_percent is None
    assert latest.split_source is None and latest.split_as_of is None
    assert latest.xbrl_url and latest.xbrl_url.startswith("https://nsearchives.nseindia.com/")
    assert latest.submission_date == date(2026, 4, 21)
    assert prior.quarter_end == date(2025, 12, 31)
    assert prior.promoter_percent == 50.01


def test_shareholding_bse_split_enrich_unexpected_error_never_breaks_nse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The BSE split-enrich lane is best-effort over an already-successful NSE
    lane (R13 hardening): even an UNEXPECTED bug deep in the BSE lane (not a
    clean ``ProviderError`` — e.g. a ``KeyError`` from a malformed row) must
    degrade to "no split enrichment", never break the NSE-served result."""
    from services import bse_provider

    monkeypatch.setattr(nse_provider, "get_shareholding_master", lambda symbol: _NSE_SHAREHOLDING)

    def _explode(symbol: str) -> list[dict[str, object]]:  # noqa: ARG001
        raise KeyError("promoter_percent")

    monkeypatch.setattr(bse_provider, "get_shareholding", _explode)

    response = corporate_disclosures.get_shareholding("RELIANCE")
    assert response.symbol == "RELIANCE"
    assert response.count == 2
    latest = response.patterns[0]
    assert latest.source == "NSE"
    assert latest.promoter_percent == 50.0
    assert latest.fii_percent is None and latest.dii_percent is None
    assert latest.institutions_percent is None
    assert latest.split_source is None and latest.split_as_of is None


def test_shareholding_dual_listed_recovers_bse_split(monkeypatch: pytest.MonkeyPatch) -> None:
    """SIL-shaped: a dual-listed NSE name whose NSE master carries no FII/DII split
    and folds institutions into the public bucket (public 79.69) recovers the true
    split (FII 38.86 / DII 4.04 / institutions 42.90) + the non-institutional public
    (36.79) from the BSE SEBI XBRL for the matching quarter."""
    from services import bse_provider

    monkeypatch.setattr(
        nse_provider,
        "get_shareholding_master",
        lambda symbol: [
            {
                "symbol": "SIL",
                "date": "31-MAR-2026",
                "pr_and_prgrp": "20.31",
                "public_val": "79.69",
                "employeeTrusts": "0.0",
                "submissionDate": "05-Apr-2026",
                "xbrl": "https://nsearchives.nseindia.com/sil_SP.xml",
            }
        ],
    )
    monkeypatch.setattr(
        bse_provider,
        "get_shareholding",
        lambda symbol: [
            {
                "quarter_end": date(2026, 3, 31),
                "submission_date": date(2026, 4, 5),
                "xbrl_url": "https://www.bseindia.com/XBRLFILES/SHPXBRLDataXML/sil_SP.html",
                "source": "BSE",
                "promoter_percent": 20.31,
                "public_percent": 79.69,
                "public_non_institutional_percent": 36.79,
                "institutions_percent": 42.9,
                "fii_percent": 38.86,
                "dii_percent": 4.04,
                "split_basis": "filed",
                "promoter_pledged_percent": 0.0,
                "promoter_pledge_basis": "filed",
            }
        ],
    )
    response = corporate_disclosures.get_shareholding("SIL")
    latest = response.patterns[0]
    # The NSE master still serves the pattern (source NSE) with its labeled public.
    assert latest.source == "NSE"
    assert latest.public_percent == 79.69
    assert latest.public_basis == "incl. institutions"
    # ...but the FII/DII split + the true non-institutional public are recovered.
    assert latest.fii_percent == 38.86
    assert latest.dii_percent == 4.04
    assert latest.institutions_percent == 42.9
    assert latest.public_non_institutional_percent == 36.79
    # Provenance of the merged split is honest: from BSE, as-of the same quarter.
    assert latest.split_source == "BSE"
    assert latest.split_as_of == date(2026, 3, 31)
    assert latest.split_basis == "filed"  # the BSE row's basis rides the merge
    # ...and so does the filed promoter pledge (R15-DATA-023): a filed 0, not None.
    assert (latest.promoter_pledged_percent, latest.promoter_pledge_basis) == (0.0, "filed")


def test_shareholding_dual_listed_split_nearest_quarter(monkeypatch: pytest.MonkeyPatch) -> None:
    """RBA/UFO-shaped: the NSE lane carries a mid-quarter EVENT filing (2026-06-02)
    that has no exact BSE match — the split is merged from the NEAREST BSE quarter
    (2026-03-31) and stamped ``split_as_of`` so the as-of is never silently aligned."""
    from services import bse_provider

    monkeypatch.setattr(
        nse_provider,
        "get_shareholding_master",
        lambda symbol: [
            {
                "symbol": "RBA",
                "date": "02-JUN-2026",  # event-driven mid-quarter filing
                "pr_and_prgrp": "9.22",
                "public_val": "90.78",
                "submissionDate": "03-Jun-2026",
                "xbrl": "https://nsearchives.nseindia.com/rba_SP.xml",
            }
        ],
    )
    monkeypatch.setattr(
        bse_provider,
        "get_shareholding",
        lambda symbol: [
            {
                "quarter_end": date(2026, 3, 31),
                "source": "BSE",
                "promoter_percent": 11.26,
                "public_percent": 88.74,
                "public_non_institutional_percent": 42.6,
                "institutions_percent": 48.18,
                "fii_percent": 8.19,
                "dii_percent": 39.98,
            }
        ],
    )
    response = corporate_disclosures.get_shareholding("RBA")
    latest = response.patterns[0]
    assert latest.quarter_end == date(2026, 6, 2)
    assert latest.dii_percent == 39.98 and latest.fii_percent == 8.19
    assert latest.institutions_percent == 48.18
    # The split came from the nearest BSE quarter, honestly as-of-labeled.
    assert latest.split_source == "BSE"
    assert latest.split_as_of == date(2026, 3, 31)


@pytest.mark.parametrize(
    ("nse_quarter", "merged"),
    [
        # R15-DATA-021, SIL-shaped: two years from the only BSE split → no split.
        ("30-SEP-2022", False),
        # A case the fix was not written against: the adjacent quarter (92 days).
        ("30-SEP-2024", True),
    ],
)
def test_shareholding_split_merge_is_bounded_to_about_a_quarter(
    monkeypatch: pytest.MonkeyPatch, nse_quarter: str, merged: bool
) -> None:
    from services import bse_provider

    monkeypatch.setattr(
        nse_provider,
        "get_shareholding_master",
        lambda symbol: [
            {"symbol": "SIL", "date": nse_quarter, "pr_and_prgrp": "20.31", "public_val": "79.69"}
        ],
    )
    monkeypatch.setattr(
        bse_provider,
        "get_shareholding",
        lambda symbol: [
            {
                "quarter_end": date(2024, 12, 31),
                "source": "BSE",
                "institutions_percent": 42.91,
                "fii_percent": 38.87,
                "dii_percent": 4.04,
            }
        ],
    )
    pattern = corporate_disclosures.get_shareholding("SIL").patterns[0]
    assert pattern.promoter_percent == 20.31  # the NSE figure always stands
    if merged:
        assert pattern.institutions_percent == 42.91
        assert pattern.split_as_of == date(2024, 12, 31)
    else:
        assert pattern.institutions_percent is None and pattern.fii_percent is None
        assert pattern.split_source is None and pattern.split_as_of is None


def test_shareholding_never_merges_another_companys_bse_split(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-CODE-DATA-001: NSE FOCUS is Focus Lighting and Fixtures; BSE FOCUS
    (scrip 543312) is Focus Business Solution, a different company. The BSE split
    under the shared ticker is that other company's, so it is never fetched or
    merged: the NSE patterns keep an honest None split."""
    from services import bse_provider

    monkeypatch.setattr(
        nse_provider,
        "get_shareholding_master",
        lambda symbol: [
            {
                "symbol": "FOCUS",
                "date": "31-MAR-2026",
                "pr_and_prgrp": "54.1",
                "public_val": "45.9",
                "submissionDate": "05-Apr-2026",
            }
        ],
    )

    def bse_must_not_run(symbol: str) -> list[dict]:
        raise AssertionError("the other company's BSE split must not be fetched")

    monkeypatch.setattr(bse_provider, "get_shareholding", bse_must_not_run)
    latest = corporate_disclosures.get_shareholding("FOCUS").patterns[0]
    assert latest.source == "NSE" and latest.promoter_percent == 54.1
    assert latest.split_source is None and latest.split_as_of is None
    assert latest.fii_percent is None and latest.institutions_percent is None


def test_shareholding_bse_only_symbol_routes_to_bse_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # BOMOXY-B1 (scrip 509470) is BSE-only — the NSE lane is not applicable, so
    # the BSE SEBI-XBRL lane serves it (the R13 coverage gap now closed). The
    # BSE provider seam is mocked so this stays offline.
    from services import bse_provider

    def nse_must_not_run(symbol: str) -> list[dict]:
        raise AssertionError("NSE lane must not run for a BSE-only symbol")

    monkeypatch.setattr(nse_provider, "get_shareholding_master", nse_must_not_run)
    monkeypatch.setattr(
        bse_provider,
        "get_shareholding",
        lambda symbol: [
            {
                "quarter_end": date(2026, 6, 30),
                "submission_date": date(2026, 7, 8),
                "xbrl_url": "https://www.bseindia.com/XBRLFILES/SHPXBRLDataXML/x_SP.html",
                "source": "BSE",
                "promoter_percent": 73.29,
                "public_percent": 26.71,
                "institutions_percent": 0.06,
                "dii_percent": 0.06,
            }
        ],
    )
    response = corporate_disclosures.get_shareholding("BOMOXY-B1")
    assert response.count == 1
    latest = response.patterns[0]
    assert latest.source == "BSE"
    assert latest.promoter_percent == 73.29
    assert latest.institutions_percent == 0.06
    assert latest.dii_percent == 0.06 and latest.fii_percent is None
    assert latest.quarter_end == date(2026, 6, 30)


@pytest.mark.parametrize(
    ("qtr", "quarter_end", "basis"),
    [
        # R15-DATA-022, SMR: BSE dates the listing-time (IPO) pattern to the day.
        ("04 Jun 2026", date(2026, 6, 4), None),
        # A case the fix was not written against: a full month name, day-dated.
        ("30 September 2026", date(2026, 9, 30), None),
        # A label no parser knows: kept, dated by its filing, and it says so.
        ("Pre-listing 2026", date(2026, 6, 8), "filing date"),
    ],
)
def test_shareholding_keeps_a_day_dated_or_unparsed_bse_pattern(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    qtr: str,
    quarter_end: date,
    basis: str | None,
) -> None:
    import httpx

    from services import bse_provider

    index = {
        "Table": [
            {
                "qtr": qtr,
                "filing_date_time": "2026-06-08T16:34:05.267",
                "XbrlFile": "544774_86202616343_SHP.xml",
                "xbrlurl": "/XBRLFILES/SHPXBRLDataXML/544774_86202616343_SP.html",
            }
        ]
    }

    def fake_get(url: str) -> httpx.Response:
        if "SHPQNewFormat" in url:
            return httpx.Response(200, json=index)
        return httpx.Response(404, content=b"")  # the XBRL itself is offline

    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))
    monkeypatch.setattr(bse_provider, "_http_get", fake_get)

    response = corporate_disclosures.get_shareholding("SMR")
    assert response.count == 1
    pattern = response.patterns[0]
    assert pattern.quarter_end == quarter_end
    assert pattern.xbrl_url is not None and pattern.source == "BSE"
    if basis is None:
        assert pattern.quarter_basis is None
    else:
        assert pattern.quarter_basis is not None and basis in pattern.quarter_basis
        assert qtr in pattern.quarter_basis


def test_shareholding_nse_first_falls_back_to_bse_on_nse_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A dual-listed name whose NSE lane errors falls back to BSE (still served).
    from services import bse_provider

    monkeypatch.setattr(
        nse_provider,
        "get_shareholding_master",
        lambda symbol: (_ for _ in ()).throw(ProviderError("nse_direct: blocked")),
    )
    monkeypatch.setattr(symbol_resolver, "is_nse_symbol", lambda symbol: True)
    monkeypatch.setattr(symbol_resolver, "is_bse_symbol", lambda symbol: True)
    monkeypatch.setattr(
        bse_provider,
        "get_shareholding",
        lambda symbol: [
            {"quarter_end": date(2026, 6, 30), "source": "BSE", "promoter_percent": 50.0}
        ],
    )
    response = corporate_disclosures.get_shareholding("RELIANCE")
    assert response.count == 1 and response.patterns[0].source == "BSE"


def test_shareholding_for_a_non_listed_symbol_raises() -> None:
    # A symbol on NEITHER exchange fast-fails without a network call.
    with pytest.raises(ProviderError, match="not a known NSE/BSE instrument"):
        corporate_disclosures.get_shareholding("AAPL")


# ---------------------------------------------------------------------------
# Agent tools — corporate_announcements / shareholding_pattern handlers.
# ---------------------------------------------------------------------------


@pytest.fixture
def _registered_tools() -> Any:
    from services.agent_tools import disclosure_tools

    disclosure_tools.register()
    yield
    agent_tools.reset_for_tests()


def test_corporate_announcements_tool_round_trip(
    monkeypatch: pytest.MonkeyPatch, _registered_tools: Any
) -> None:
    _patch_nse_announcements(monkeypatch, _NSE_ANNOUNCEMENTS)
    _patch_bse_payload(monkeypatch, _BSE_ANNOUNCEMENTS)

    # limit 3: the fixtures' six rows are three filings on both exchanges, and
    # the cross-exchange dedup collapses the pairs it can match.
    result = asyncio.run(
        agent_tools.invoke_tool("corporate_announcements", {"symbol": "RELIANCE", "limit": 3})
    )
    assert result["ok"] is True
    assert result["symbol"] == "RELIANCE"
    assert result["sources"] == ["NSE", "BSE"]
    assert result["count"] == len(result["announcements"]) == 3
    item = result["announcements"][0]
    assert {"symbol", "exchange", "headline", "category", "attachment_url", "ts"} <= set(item)


def test_corporate_announcements_tool_validates_args(_registered_tools: Any) -> None:
    missing = asyncio.run(agent_tools.invoke_tool("corporate_announcements", {}))
    assert missing["ok"] is False and "symbol" in missing["error"]

    bad_exchange = asyncio.run(
        agent_tools.invoke_tool(
            "corporate_announcements", {"symbol": "RELIANCE", "exchange": "NYSE"}
        )
    )
    assert bad_exchange["ok"] is False and "NYSE" in bad_exchange["error"]


def test_corporate_announcements_tool_surfaces_provider_error(
    monkeypatch: pytest.MonkeyPatch, _registered_tools: Any
) -> None:
    def boom(symbol: str, exchange: str | None = None, limit: int = 50):  # noqa: ANN202, ARG001
        raise ProviderError("every announcement source failed")

    monkeypatch.setattr(corporate_disclosures, "get_announcements", boom)
    result = asyncio.run(agent_tools.invoke_tool("corporate_announcements", {"symbol": "RELIANCE"}))
    assert result["ok"] is False
    assert "every announcement source failed" in result["error"]


def test_shareholding_pattern_tool_round_trip(
    monkeypatch: pytest.MonkeyPatch, _registered_tools: Any
) -> None:
    from services import bse_provider

    monkeypatch.setattr(nse_provider, "get_shareholding_master", lambda symbol: _NSE_SHAREHOLDING)
    monkeypatch.setattr(bse_provider, "get_shareholding", lambda symbol: [])

    result = asyncio.run(agent_tools.invoke_tool("shareholding_pattern", {"symbol": "RELIANCE"}))
    assert result["ok"] is True
    assert result["symbol"] == "RELIANCE"
    assert result["count"] == 2
    assert result["patterns"][0]["quarter_end"] == "2026-03-31"
    assert result["patterns"][0]["promoter_percent"] == 50.0
    assert result["patterns"][0]["fii_percent"] is None
    assert result["patterns"][0]["public_basis"] == "incl. institutions"
    # No prose note: the typed provenance fields say where the split came from
    # (R15-AGENT-060; the old note claimed the split lived only in the XBRL).
    assert "note" not in result


def test_shareholding_pattern_tool_surfaces_provider_error(_registered_tools: Any) -> None:
    # AAPL is on neither Indian exchange — fast-fails without a network call.
    result = asyncio.run(agent_tools.invoke_tool("shareholding_pattern", {"symbol": "AAPL"}))
    assert result["ok"] is False
    assert "not a known NSE/BSE instrument" in result["error"]
