"""Bulk deals, block deals and SAST disclosures (R15-DATA-024).

Fixtures are verbatim trims of live feeds captured 2026-09-24: NSE bulk deals
(KOPRAN), NSE block deals (ADANIENT), NSE SAST Reg 29 (KOPRAN) and BSE bulk deals
for a BSE-only scrip (539091 CCDL). No test reaches the network: the NSE seam
(``nse_provider._get_json``) and the BSE seam (``corporate_disclosures._bse_get_json``)
are monkeypatched.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from config import DATA_DIR_ENV
from routers import disclosures
from services import corporate_disclosures, data_cache, nse_provider, symbol_resolver
from services.agent_tools import disclosure_tools

_FIXTURES = Path(__file__).parent / "fixtures"


def _load(path: str) -> Any:
    return json.loads((_FIXTURES / path).read_text(encoding="utf-8"))


_NSE_PAYLOADS = {
    ("bulk_deals", "KOPRAN"): _load("nse/deals_bulk_kopran_20260924.json"),
    ("block_deals", "ADANIENT"): _load("nse/deals_block_adanient_20260924.json"),
    ("sast", "KOPRAN"): _load("nse/deals_sast_kopran_20260924.json"),
}
_BSE_CCDL_BULK = _load("bse/deals_bulk_539091_ccdl_20260924.json")


@pytest.fixture(autouse=True)
def _isolate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    symbol_resolver.reset_caches_for_tests()
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    data_cache.reset_for_tests()

    def nse(path: str, params: dict[str, str], referer: str) -> object:
        option = "sast" if path.endswith("sast-reg29") else params["optionType"]
        return _NSE_PAYLOADS.get((option, params["symbol"]), {"data": []})

    def bse(url: str, params: dict[str, str]) -> object:
        if params["scripcode"] == "539091" and params["type"] == "1":
            return _BSE_CCDL_BULK
        return {"Table": [], "Table1": []}

    monkeypatch.setattr(nse_provider, "_get_json", nse)
    monkeypatch.setattr(corporate_disclosures, "_bse_get_json", bse)
    yield
    data_cache.reset_for_tests()


def test_nse_bulk_deals_parse_to_typed_rows() -> None:
    response = corporate_disclosures.get_deals("KOPRAN", "bulk")
    assert response.sources == ["NSE bulk"]
    first = response.deals[0]
    assert (first.kind, first.date, first.party) == ("bulk", date(2026, 9, 17), "QE SECURITIES LLP")
    assert (first.side, first.quantity, first.price) == ("sell", 257185.0, 265.59)
    assert first.value == round(257185 * 265.59, 2)
    assert first.percent_after is None and first.exchange == "NSE"


def test_nse_block_deals_parse_to_typed_rows() -> None:
    deals = corporate_disclosures.get_deals("ADANIENT", "block").deals
    gqg = next(d for d in deals if d.party == "GQG PARTNERS EMERGING MARKETS EQUITY CIT")
    assert (gqg.kind, gqg.date, gqg.side) == ("block", date(2025, 11, 18), "buy")
    assert (gqg.quantity, gqg.price) == (1528520.0, 2462.0)


def test_nse_sast_disclosures_parse_to_typed_rows() -> None:
    first = corporate_disclosures.get_deals("KOPRAN", "sast").deals[0]
    assert (first.kind, first.party, first.side) == ("sast", "United Shippers Limited", "sell")
    assert (first.date, first.quantity, first.percent_after) == (date(2026, 9, 7), 1200000.0, 2.07)
    assert first.price is None
    assert first.source_url.startswith("https://nsearchives.nseindia.com/corporate/")


def test_route_and_tool_serve_every_kind() -> None:
    app = FastAPI()
    app.include_router(disclosures.router)
    body = TestClient(app).get("/disclosures/deals", params={"symbol": "kopran"}).json()
    assert body["sources"] == ["NSE bulk", "NSE block", "NSE sast"]
    assert {d["kind"] for d in body["deals"]} == {"bulk", "sast"}  # KOPRAN has no block deal

    result = asyncio.run(disclosure_tools._exchange_deals({"symbol": "KOPRAN", "kind": "sast"}))
    assert result["ok"] is True and result["count"] == 4
    assert result["deals"][0]["percent_after"] == 2.07


def test_bse_only_scrip_goes_through_the_bse_feed() -> None:
    """The case not written against: CCDL is BSE-only, so NSE is never asked."""
    response = corporate_disclosures.get_deals("CCDL")
    assert response.sources == ["BSE bulk", "BSE block"]
    first = response.deals[0]
    assert (first.exchange, first.kind, first.date, first.side) == (
        "BSE",
        "bulk",
        date(2026, 9, 23),
        "buy",
    )
    assert first.party == "METROCITY HEART CARE AND CRITICAL CARE PRIVATE LIMITED"
    assert response.count == 6


def test_a_block_deal_question_admits_the_deals_tool_on_a_small_window() -> None:
    """On a window-bound lane the filings domain joins only on a cue word; a
    block-deal or dividend question must reach exchange_deals / corporate_actions."""
    from models.llm import LLMMessage
    from services import agent_runtime
    from services.agent_tools.catalog import default_grant_tool_ids

    tools = default_grant_tool_ids()
    for prompt, tool in (
        ("who bought the block deal in KOPRAN last week?", "exchange_deals"),
        ("when is the next dividend for ELCIDIN?", "corporate_actions"),
    ):
        messages = [LLMMessage(role="user", content=prompt)]
        assert tool in agent_runtime._window_tool_subset(tools, messages, window=4096)
