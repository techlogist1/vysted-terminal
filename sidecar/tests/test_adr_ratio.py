"""R15-AGENT-090: the depositary ratio is read off the 20-F cover page, never
guessed, and rides the ``fundamentals`` result of a foreign reporter only."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from models.fundamentals import Fundamentals
from services import adr_ratio, data_cache
from services.agent_tools import fundamentals as fundamentals_tool

#: SIFY's 20-F cover page (0001554855-26-001437), tags stripped.
_SIFY_COVER = (
    "Securities registered or to be registered pursuant to Section 12(b) of the Act "
    "Title of each class Trading Symbol Name of each Exchange on which registered "
    "American Depositary Shares, each represented by Six Equity Shares, par value ₹ 10per "
    "share SIFY NASDAQ Capital Market (NASDAQ-CM) Securities registered or to be "
    "registered pursuant to Section 12(g) of the Act Title of each class Not Applicable"
)
#: Spotify's (a 20-F filer that lists ordinary shares, no ADS).
_SPOT_COVER = (
    "Securities registered or to be registered, pursuant to Section 12(b) of the Act "
    "Title of Each Class Trading Symbol(s) Name of Each Exchange on Which Registered "
    "Ordinary Shares (par value of €0.000625 per share) SPOT New York Stock Exchange "
    "Securities registered or to be registered pursuant to Section 12(g) of the Act: None"
)


def test_the_cover_page_statement_is_parsed_exactly() -> None:
    assert adr_ratio.parse_cover_ratio(f"<html><body><p>{_SIFY_COVER}</p></body></html>") == {
        "ordinary_shares_per_ads": 6,
        "statement": "American Depositary Shares, each represented by Six Equity Shares",
    }
    infy = (
        "pursuant to Section 12(b) of the Act ... "
        "American Depositary Shares each represented by one Equity Share"
    )
    assert adr_ratio.parse_cover_ratio(infy)["ordinary_shares_per_ads"] == 1
    digits = "Section 12(b) ... Each American Depositary Share represents two (2) Ordinary Shares"
    assert adr_ratio.parse_cover_ratio(digits)["ordinary_shares_per_ads"] == 2


@pytest.mark.parametrize(
    "document",
    [
        _SPOT_COVER,
        # The body's historical rights-offering ADS is outside the cover page.
        "Item 4. In 2024 the Company issued 59,730,265 ADSs (each representing one equity share).",
        # Two different ratios on one cover: not guessed at.
        "Section 12(b) ... ADSs, each representing six equity shares ... "
        "Each ADS represents two equity shares",
        # A fraction is not parsed into a guess.
        "Section 12(b) ... American Depositary Shares, each representing one-half of one "
        "ordinary share",
        "",
    ],
)
def test_a_page_without_one_statement_yields_none(document: str) -> None:
    assert adr_ratio.parse_cover_ratio(document) is None


def _fundamentals(**fields: Any) -> Fundamentals:
    return Fundamentals(symbol="SIFY", provider="yfinance", currency="USD", **fields)


def _serve(monkeypatch: pytest.MonkeyPatch, fundamentals: Fundamentals, ratio: dict | None) -> list:
    looked_up: list[str] = []

    async def fetch(_symbol: str) -> fundamentals_tool._FetchResult:
        return fundamentals_tool._FetchResult(fundamentals, None)

    async def lookup(symbol: str) -> dict | None:
        looked_up.append(symbol)
        return ratio

    monkeypatch.setattr(fundamentals_tool, "_fetch_once", fetch)
    monkeypatch.setattr(adr_ratio, "lookup", lookup)
    return looked_up


def test_a_foreign_reporter_carries_its_depositary_ratio(monkeypatch: pytest.MonkeyPatch) -> None:
    ratio = {
        "ordinary_shares_per_ads": 6,
        "statement": "American Depositary Shares, each represented by Six Equity Shares",
        "provenance": {"source": "SEC 20-F cover page", "filed": "2026-06-26", "url": "x"},
    }
    looked_up = _serve(monkeypatch, _fundamentals(financial_currency="INR"), ratio)
    out = asyncio.run(fundamentals_tool._fundamentals({"symbol": "SIFY"}))
    assert out["ok"] is True and out["ads_ratio"] == ratio
    assert looked_up == ["SIFY"]


def test_a_domestic_reporter_or_a_miss_carries_none(monkeypatch: pytest.MonkeyPatch) -> None:
    looked_up = _serve(monkeypatch, _fundamentals(), {"ordinary_shares_per_ads": 6})
    assert "ads_ratio" not in asyncio.run(fundamentals_tool._fundamentals({"symbol": "AAPL"}))
    assert looked_up == []
    _serve(monkeypatch, _fundamentals(financial_currency="INR"), None)
    assert "ads_ratio" not in asyncio.run(fundamentals_tool._fundamentals({"symbol": "SIFY"}))


def test_a_foreign_reporters_statement_carries_the_ratio_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live (batch-15 sify-1) the model reached for financial_statements on the
    revenue half of the question and stated the ratio beside it."""
    from models.fundamentals import FinancialStatement, StatementLine
    from services import provider_registry

    ratio = {"ordinary_shares_per_ads": 6, "statement": "each represented by Six Equity Shares"}

    async def sify(symbol: str) -> Fundamentals:
        return _fundamentals(financial_currency="INR")

    async def income(symbol: str, period: str) -> FinancialStatement:
        return FinancialStatement(
            symbol=symbol,
            periods=["2026-03-31"],
            lines=[StatementLine(label="Total Revenue", values={"2026-03-31": 4.6e10})],
            provider="yfinance",
        )

    async def lookup(symbol: str) -> dict:
        return ratio

    monkeypatch.setattr(provider_registry, "get_fundamentals", sify)
    monkeypatch.setattr(provider_registry, "get_income_statement", income)
    monkeypatch.setattr(adr_ratio, "lookup", lookup)
    out = asyncio.run(
        fundamentals_tool._financial_statements({"symbol": "SIFY", "statement": "income"})
    )
    assert out["ok"] is True and out["currency"] == "INR" and out["ads_ratio"] == ratio
    assert list(out)[:2] == ["ok", "ads_ratio"]  # leads, so the window cap keeps it


def test_lookup_caches_a_hit_and_a_miss_and_never_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    data_cache.reset_for_tests(tmp_path / "cache.sqlite")
    calls: list[str] = []
    answers: dict[str, Any] = {"SIFY": {"ordinary_shares_per_ads": 6}, "SPOT": None}

    async def fetch(symbol: str) -> dict | None:
        calls.append(symbol)
        if symbol == "DOWN":
            raise OSError("edgar unreachable")
        return answers[symbol]

    monkeypatch.setattr(adr_ratio, "_fetch", fetch)
    try:
        for _ in range(2):
            assert asyncio.run(adr_ratio.lookup("SIFY")) == {"ordinary_shares_per_ads": 6}
            assert asyncio.run(adr_ratio.lookup("SPOT")) is None
        assert asyncio.run(adr_ratio.lookup("DOWN")) is None
    finally:
        data_cache.reset_for_tests()
    assert calls == ["SIFY", "SPOT", "DOWN"]
