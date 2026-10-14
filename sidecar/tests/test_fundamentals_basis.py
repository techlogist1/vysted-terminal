"""The filed accounting basis on /fundamentals (R15-DATA-054).

``basis`` is read from the exchange filings, never defaulted: the exchange
accessors are replayed from payloads recorded live on 2026-09-24; a call with
no recording raises, so no case reaches the network.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from models.fundamentals import Fundamentals
from services import (
    bse_provider,
    correctness_gate,
    exchange_financials,
    nse_provider,
    provider_registry,
    symbol_resolver,
)
from services.symbol_resolver import Resolution

_FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _fresh_lane() -> None:
    exchange_financials.reset_for_tests()


def _replay(monkeypatch: pytest.MonkeyPatch, *fixtures: str) -> list[str]:
    recorded: dict[str, dict] = {}
    for name in fixtures:
        for accessor, calls in json.loads((_FIXTURES / name).read_text(encoding="utf-8")).items():
            recorded.setdefault(accessor, {}).update(calls)
    log: list[str] = []

    def player(accessor: str):  # noqa: ANN202
        def play(*args: object) -> object:
            log.append(accessor)
            return recorded[accessor]["|".join(str(a) for a in args)]

        return play

    monkeypatch.setattr(nse_provider, "get_financial_filings", player("get_financial_filings"))
    monkeypatch.setattr(bse_provider, "get_results_summary", player("get_results_summary"))
    return log


def test_smr_a_bse_only_standalone_filer_is_standalone(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # SMR Jewels files only an audited standalone half-year/year result on BSE.
    _replay(monkeypatch, "bse/results_summary_544774_smr_20260924.json")

    async def fake_fundamentals(_symbol: str) -> Fundamentals:
        return Fundamentals(symbol="SMR.BO", name="SMR Jewels Ltd", provider="yfinance")

    async def passthrough(f: Fundamentals) -> Fundamentals:
        return f

    monkeypatch.setattr(provider_registry, "get_fundamentals", fake_fundamentals)
    monkeypatch.setattr(correctness_gate, "apply_witnesses", passthrough)
    monkeypatch.setattr(
        symbol_resolver, "resolve", lambda q, r: Resolution(query=q, best=None, candidates=[])
    )
    assert client.get("/fundamentals/SMR").json()["basis"] == "standalone"


@pytest.mark.parametrize("listing", ["CREST.NS", "CREST.BO"])
def test_a_consolidated_filer_is_consolidated_on_either_venue(
    monkeypatch: pytest.MonkeyPatch, listing: str
) -> None:
    # Crest Ventures files consolidated + standalone on NSE; its BSE listing
    # reads the same NSE index, not BSE's standalone-only result pages.
    log = _replay(monkeypatch, "nse/financial_filings_crest_20260924.json")
    assert asyncio.run(exchange_financials.filed_basis(listing)) == "consolidated"
    assert log == ["get_financial_filings"]


def test_a_us_listing_has_no_basis(monkeypatch: pytest.MonkeyPatch) -> None:
    log = _replay(monkeypatch)
    assert asyncio.run(exchange_financials.filed_basis("AAPL")) is None
    assert log == []
