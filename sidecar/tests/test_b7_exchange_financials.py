"""The exchange-filed results lane (R15-DATA-014/027/076, R15-LEAD-004; D-B7-1/2).

Every lane runs for real over payloads recorded live on 2026-09-24
(``fixtures/{nse,bse}/filed_results_*.json``); only the exchange accessors are
replayed. The yfinance side is stubbed to the figures the battery observed.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from models.fundamentals import Fundamentals, IncomeStatement, StatementLine
from services import (
    bse_provider,
    exchange_financials,
    nse_provider,
    provider_registry,
    symbol_resolver,
    yfinance_provider,
)
from services.symbol_resolver import Resolution

_FIXTURES = Path(__file__).parent / "fixtures"
_DAL = "bse/filed_results_539681_dal_20260924.json"
_JONJUA = "bse/filed_results_542446_jonjua_20260924.json"
_FUSION = "nse/filed_results_fusion_20260924.json"
_DHANBANK = "nse/filed_results_dhanbank_20260924.json"


@pytest.fixture(autouse=True)
def _fresh_lane() -> None:
    exchange_financials.reset_for_tests()


def _replay(monkeypatch: pytest.MonkeyPatch, *fixtures: str) -> list[str]:
    """Serve the exchange accessors from recorded payloads; returns the call log.
    Any accessor with no recording raises (a lane never reaches the network)."""
    recorded: dict[str, dict] = {}
    for name in fixtures:
        for accessor, calls in json.loads((_FIXTURES / name).read_text()).items():
            recorded.setdefault(accessor, {}).update(calls)
    log: list[str] = []

    def player(accessor: str):  # noqa: ANN202
        def play(*args: object) -> object:
            log.append(accessor)
            return recorded[accessor]["|".join(str(a) for a in args)]

        return play

    for module, names in (
        (nse_provider, ("get_financial_filings", "get_archive_text")),
        (bse_provider, ("get_results_summary", "get_result_detail", "get_nbfc_profit_loss")),
    ):
        for accessor in names:
            monkeypatch.setattr(module, accessor, player(accessor))
    return log


def _route(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    symbol: str,
    fields: dict,
    annual_revenue: float,
    quarter_ends: list[str],
) -> dict:
    """GET /fundamentals for a stubbed Yahoo payload and its own statements."""

    async def fake_fundamentals(requested: str) -> Fundamentals:  # noqa: ARG001
        return Fundamentals(symbol=symbol, name="X Ltd", provider="yfinance", **fields)

    def fake_income(listing: str) -> IncomeStatement:  # noqa: ARG001
        line = StatementLine(label="Total Revenue", values={"2026": annual_revenue})
        return IncomeStatement(symbol=symbol, periods=["2026"], lines=[line], provider="yfinance")

    def fake_quarters(listing: str) -> list[date]:  # noqa: ARG001
        return [date.fromisoformat(d) for d in quarter_ends]

    def fake_resolve(query: str, region: str) -> Resolution:  # noqa: ARG001
        return Resolution(query=query, best=None, candidates=[])

    monkeypatch.setattr(provider_registry, "get_fundamentals", fake_fundamentals)
    monkeypatch.setattr(yfinance_provider, "get_income_statement", fake_income)
    monkeypatch.setattr(yfinance_provider, "get_quarterly_period_ends", fake_quarters)
    monkeypatch.setattr(symbol_resolver, "resolve", fake_resolve)
    return client.get(f"/fundamentals/{symbol}").json()


_QUARTERS = ["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30"]


# --- R15-DATA-014: the served TTM is the filed-period sum --------------------------


def test_dal_revenue_ttm_is_the_bse_filed_sum(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DAL: Yahoo 2.76 Cr (its own FY 2.07 Cr agrees, so no Yahoo witness sees
    it); BSE's filed Sep-25..Jun-26 quarters sum to 9.97 Cr (screener 9.97)."""
    _replay(monkeypatch, _DAL)
    fields = {"revenue_ttm": 27_600_000, "net_income_ttm": 10_200_000, "profit_margin": 0.36957}
    body = _route(client, monkeypatch, "DAL.BO", fields, 20_668_000, _QUARTERS)
    assert body["revenue_ttm"] == pytest.approx(99_700_000)
    assert body["net_income_ttm"] == pytest.approx(10_200_000)  # screener 1.02 Cr
    meta = body["field_meta"]["revenue_ttm"]
    assert (meta["status"], meta["provider"], meta["as_of"]) == ("ok", "bse", "2026-06-30")
    assert "sum of 4 filed quarters" in meta["label"]
    assert "27,600,000" in meta["reason"]  # Yahoo's figure disclosed, not served


def test_fusion_revenue_ttm_is_the_nse_filed_sum(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The class case not written against (the NSE lane): FUSION's filed
    quarters sum to 1,714 Cr (screener ~1,699 Cr) against Yahoo's 858 Cr."""
    _replay(monkeypatch, _FUSION)
    fields = {"revenue_ttm": 8_582_000_128, "net_income_ttm": 1_685_100_032}
    body = _route(client, monkeypatch, "FUSION.NS", fields, 15_131_300_000, _QUARTERS)
    assert body["revenue_ttm"] == pytest.approx(17_144_200_000)
    assert body["net_income_ttm"] == pytest.approx(1_685_100_000)
    meta = body["field_meta"]["revenue_ttm"]
    assert (meta["provider"], meta["label"]) == (
        "nse",
        "standalone, sum of 4 filed quarters to 2026-06-30",
    )
    assert "8,582,000,128" in meta["reason"]


# --- R15-DATA-027: the two single-name seams only ------------------------------


def test_agent_fundamentals_tool_serves_the_exchange_figure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services.agent_tools import fundamentals as fundamentals_tool

    log = _replay(monkeypatch, _DAL)

    async def fake(symbol: str) -> Fundamentals:
        return Fundamentals(symbol=symbol, provider="yfinance", revenue_ttm=27_600_000)

    monkeypatch.setattr(provider_registry, "get_fundamentals", fake)
    out = asyncio.run(fundamentals_tool._fundamentals({"symbol": "DAL.BO"}))
    served = out["fundamentals"]
    assert served["revenue_ttm"] == pytest.approx(99_700_000)
    assert served["field_meta"]["revenue_ttm"]["provider"] == "bse"
    assert log  # the lane ran

    log.clear()
    out = asyncio.run(fundamentals_tool._fundamentals({"symbol": "AAPL"}))
    assert out["fundamentals"]["revenue_ttm"] == 27_600_000
    assert log == []  # a US listing never calls the lane


def test_the_registry_bulk_path_never_calls_the_lane(
    monkeypatch: pytest.MonkeyPatch, mock_yfinance: object
) -> None:
    """The screener/warm crawlers read ``provider_registry.get_fundamentals``;
    the exchange lane must never ride it (one NSE hit per universe symbol)."""
    calls: list[str] = []

    async def spy(listing: str) -> None:
        calls.append(listing)

    monkeypatch.setattr(exchange_financials, "get_filed_periods", spy)
    asyncio.run(provider_registry.get_fundamentals("RELIANCE.NS"))
    assert calls == []


# --- R15-LEAD-004: the cadence label comes from the filings -----------------------


def test_jonjua_keeps_the_half_yearly_label(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BSE holds no filed quarter for Sep-25 (JONJUA filed that half-year), so
    no trailing-4Q sum exists: Yahoo's value stays, labelled half-yearly."""
    _replay(monkeypatch, _JONJUA)
    fields = {"revenue_ttm": 239_033_504, "net_income_ttm": 87_482_000, "profit_margin": 0.36598}
    body = _route(client, monkeypatch, "JONJUA.BO", fields, 212_051_000, _QUARTERS)
    assert body["revenue_ttm"] == 239_033_504
    reason = body["field_meta"]["revenue_ttm"]["reason"]
    assert "half-yearly filer" in reason and "annual, not trailing-4Q" in reason


def test_a_quarterly_filer_with_a_yahoo_gap_is_not_half_yearly(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DHANBANK-shaped: Yahoo's frame skips 2025-09-30. Without the lane the
    median period gap says quarterly (a provider gap); with it the four filed
    quarters are served."""
    gap = ["2026-06-30", "2026-03-31", "2025-12-31", "2025-06-30"]
    fields = {"revenue_ttm": 18_000_000_000, "net_income_ttm": 1_150_000_000}

    async def no_lane(listing: str) -> None:  # noqa: ARG001
        return None

    with monkeypatch.context() as m:
        m.setattr(exchange_financials, "get_filed_periods", no_lane)
        body = _route(client, monkeypatch, "DHANBANK.NS", fields, 17_500_000_000, gap)
    reason = body["field_meta"]["revenue_ttm"]["reason"]
    assert "spans a provider gap" in reason and "half-yearly" not in reason

    _replay(monkeypatch, _DHANBANK)
    body = _route(client, monkeypatch, "DHANBANK.NS", fields, 17_500_000_000, gap)
    meta = body["field_meta"]["revenue_ttm"]
    assert (meta["provider"], meta["reason"]) == ("nse", None)
    assert body["revenue_ttm"] == pytest.approx(18_710_600_000)
