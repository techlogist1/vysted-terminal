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
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from services import agent_tools, corporate_disclosures, nse_provider, symbol_resolver
from services.errors import ProviderError

_NSE_FIXTURES = Path(__file__).parent / "fixtures" / "nse"
_BSE_FIXTURES = Path(__file__).parent / "fixtures" / "bse"

_NSE_ANNOUNCEMENTS = json.loads((_NSE_FIXTURES / "corporate_announcements.json").read_text())
_NSE_EVENTS = json.loads((_NSE_FIXTURES / "event_calendar.json").read_text())
_NSE_SHAREHOLDING = json.loads((_NSE_FIXTURES / "corporate_share_holdings_master.json").read_text())
_BSE_ANNOUNCEMENTS = json.loads((_BSE_FIXTURES / "ann_sub_category_get_data.json").read_text())


@pytest.fixture(autouse=True)
def _isolate() -> None:
    symbol_resolver.reset_caches_for_tests()


def _patch_nse_announcements(monkeypatch: pytest.MonkeyPatch, rows: list[dict] | Exception) -> None:
    def fake(symbol: str, limit: int = 50) -> list[dict]:  # noqa: ARG001
        if isinstance(rows, Exception):
            raise rows
        return rows[: max(limit, 0)]

    monkeypatch.setattr(nse_provider, "get_corporate_announcements", fake)


def _patch_bse_payload(monkeypatch: pytest.MonkeyPatch, payload: object | Exception) -> list[dict]:
    calls: list[dict] = []

    def fake(url: str, params: dict[str, str]) -> object:
        calls.append({"url": url, "params": params})
        if isinstance(payload, Exception):
            raise payload
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
    assert response.count == len(response.announcements) > 0
    exchanges = {item.exchange for item in response.announcements}
    assert exchanges == {"NSE", "BSE"}
    # Newest first (the fixtures' distinct headlines never collide in dedup).
    stamps = [item.ts for item in response.announcements if item.ts is not None]
    assert stamps == sorted(stamps, reverse=True)
    # The BSE lane was asked with the observed query contract, scrip-code keyed.
    assert len(calls) == 1
    params = calls[0]["params"]
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


def test_dedup_collapses_the_same_story_across_exchanges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same symbol + same (normalised) headline + same IST day → ONE item, NSE wins."""
    nse_row = _NSE_ANNOUNCEMENTS[0]
    duplicate_headline = "  " + str(nse_row["attchmntText"]).upper() + "  "  # cosmetic drift
    bse_payload = {
        "Table": [
            dict(
                _BSE_ANNOUNCEMENTS["Table"][0],
                NEWSSUB=duplicate_headline,
                NEWS_DT="2026-06-09T19:44:02.21",  # same IST calendar day as the NSE row
            )
        ],
        "Table1": [{"ROWCNT": 1}],
    }
    _patch_nse_announcements(monkeypatch, [nse_row])
    _patch_bse_payload(monkeypatch, bse_payload)

    response = corporate_disclosures.get_announcements("RELIANCE")
    assert response.sources == ["NSE", "BSE"]
    assert response.count == 1
    assert response.announcements[0].exchange == "NSE"  # the NSE lane merges first


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

    result = asyncio.run(
        agent_tools.invoke_tool("corporate_announcements", {"symbol": "RELIANCE", "limit": 5})
    )
    assert result["ok"] is True
    assert result["symbol"] == "RELIANCE"
    assert result["sources"] == ["NSE", "BSE"]
    assert result["count"] == len(result["announcements"]) == 5
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
    assert "xbrl_url" in result["note"]


def test_shareholding_pattern_tool_surfaces_provider_error(_registered_tools: Any) -> None:
    # AAPL is on neither Indian exchange — fast-fails without a network call.
    result = asyncio.run(agent_tools.invoke_tool("shareholding_pattern", {"symbol": "AAPL"}))
    assert result["ok"] is False
    assert "not a known NSE/BSE instrument" in result["error"]
