"""Option chain with exchange-published open interest (R15-DATA-079).

No test touches the network: the NSE leg is served by an ``httpx.MockTransport``
on the shared nse_bhavcopy client, the US leg by a stubbed yfinance seam. The
fixture is a verbatim trim of the live ``BhavCopy_NSE_FO_0_0_0_20260924_F_0000.csv``
(NIFTY index options over two expiries, RELIANCE stock options, and one future
each, which the parser must drop).
"""

from __future__ import annotations

import io
import zipfile
from datetime import date
from pathlib import Path

import httpx
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import quant
from services import data_cache, nse_bhavcopy, option_chain
from services.agent_tools import quant_tools

_FIXTURE = Path(__file__).parent / "fixtures" / "nse" / "fo_bhavcopy_udiff_20260924_trimmed.csv"


def _fixture_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "BhavCopy_NSE_FO_0_0_0_20260924_F_0000.csv", _FIXTURE.read_text(encoding="utf-8")
        )
    return buf.getvalue()


@pytest.fixture
def nse_calls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Serve the fixture for 24 Sep 2026; 25 Sep (IST-today) is not yet published."""
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if "20260924" in str(request.url):
            return httpx.Response(200, content=_fixture_zip())
        return httpx.Response(404)

    data_cache.reset_for_tests(tmp_path / "cache.db")
    nse_bhavcopy.reset_for_tests(httpx.MockTransport(handler))
    monkeypatch.setattr(nse_bhavcopy, "_MIN_REQUEST_INTERVAL_SECONDS", 0.0)
    monkeypatch.setattr(nse_bhavcopy, "_ist_today", lambda: date(2026, 9, 25))
    yield calls
    data_cache.reset_for_tests(None)
    nse_bhavcopy.reset_for_tests()


def test_parse_keeps_option_rows_keyed_by_underlying() -> None:
    rows = option_chain.parse_fo_bhavcopy(_FIXTURE.read_text(encoding="utf-8"))
    assert set(rows) == {"NIFTY", "RELIANCE"}
    assert len(rows["NIFTY"]) == 9  # the IDF future is dropped
    assert len(rows["RELIANCE"]) == 4  # the STF future is dropped


@pytest.mark.asyncio
async def test_nifty_chain_carries_exchange_oi(nse_calls: list[str]) -> None:
    chain = await option_chain.get_option_chain("NIFTY")
    assert chain is not None
    assert chain.provider == "nse-fo-bhavcopy"
    assert chain.as_of == date(2026, 9, 24)  # walked back from the unpublished 25th
    assert chain.expiry == date(2026, 9, 29)  # nearest when none is asked
    assert chain.expiries == [date(2026, 9, 29), date(2026, 10, 6)]
    assert chain.underlying_price == 23063.10
    assert chain.currency == "INR"
    assert [c.strike for c in chain.contracts] == [
        22900,
        22900,
        23000,
        23000,
        23100,
        23100,
        23200,
        23200,
    ]
    put = next(c for c in chain.contracts if c.strike == 23000 and c.option_type == "put")
    assert (put.open_interest, put.change_in_oi, put.settle_price, put.volume) == (
        11757550,
        -918215,
        82.05,
        2432163,
    )
    # The parsed day is cached: a second read re-checks only the unpublished today.
    later = await option_chain.get_option_chain("NIFTY", date(2026, 10, 6))
    assert sum("20260924" in url for url in nse_calls) == 1
    assert later is not None and [c.open_interest for c in later.contracts] == [585585]


@pytest.mark.asyncio
async def test_stock_option_chain_and_unlisted_expiry(nse_calls: list[str]) -> None:
    chain = await option_chain.get_option_chain("RELIANCE.NS")
    assert chain is not None and chain.symbol == "RELIANCE"
    call = next(c for c in chain.contracts if c.strike == 1220 and c.option_type == "call")
    assert (call.open_interest, call.change_in_oi) == (876000, 526000)
    with pytest.raises(ValueError, match="no 2026-10-01 expiry"):
        await option_chain.get_option_chain("RELIANCE", date(2026, 10, 1))


def test_route_404_for_a_non_fo_symbol(nse_calls: list[str]) -> None:
    app = FastAPI()
    app.include_router(quant.router)
    with TestClient(app) as client:
        ok = client.get("/quant/option/chain/NIFTY")
        missing = client.get("/quant/option/chain/GOLDBEES")
    assert ok.status_code == 200
    assert ok.json()["contracts"][0]["open_interest"] == 376545
    assert missing.status_code == 404
    assert "not_found" in missing.json()["detail"]


@pytest.mark.asyncio
async def test_us_leg_from_a_stubbed_yfinance_chain(
    nse_calls: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    traded = pd.Timestamp("2026-09-24 19:59:00", tz="UTC")

    def fake(symbol: str, expiry: date | None) -> dict:
        assert (symbol, expiry) == ("AAPL", None)
        return {
            "expiries": [date(2026, 10, 2), date(2026, 10, 9)],
            "expiry": date(2026, 10, 2),
            "calls": [
                {
                    "strike": 250.0,
                    "openInterest": 12034.0,
                    "impliedVolatility": 0.27,
                    "lastPrice": 4.1,
                    "volume": 900.0,
                    "lastTradeDate": traded,
                }
            ],
            "puts": [
                {
                    "strike": 250.0,
                    "openInterest": float("nan"),
                    "impliedVolatility": 0.29,
                    "lastPrice": 3.2,
                    "volume": float("nan"),
                    "lastTradeDate": traded,
                }
            ],
            "underlying": 251.3,
        }

    monkeypatch.setattr(option_chain, "_yf_option_chain", fake)
    chain = await option_chain.get_option_chain("AAPL")
    assert nse_calls == []  # a US-pinned ticker never reads the NSE file
    assert chain is not None and chain.provider == "yfinance" and chain.currency == "USD"
    assert chain.as_of == date(2026, 9, 24)
    call, put = chain.contracts
    assert (call.option_type, call.open_interest, call.implied_volatility) == ("call", 12034, 0.27)
    assert (put.option_type, put.open_interest, put.volume) == ("put", None, None)


@pytest.mark.asyncio
async def test_agent_tool_trims_to_strikes_nearest_spot(nse_calls: list[str]) -> None:
    out = await quant_tools._option_chain({"symbol": "NIFTY", "max_strikes": 2})
    assert out["ok"] is True and out["strikes_listed"] == 4
    assert sorted({c["strike"] for c in out["result"]["contracts"]}) == [23000, 23100]
    missing = await quant_tools._option_chain({"symbol": "GOLDBEES"})
    assert missing["ok"] is False and missing["error"].startswith("not_found")


# ---------------------------------------------------------------------------
# R15-DATA-114: today's negative probe (404 or a transport/HTTP failure) is
# cached briefly, and a failed (not merely missing) today-probe walks back
# cache-only instead of returning None while a good cached day sits unused.
# ---------------------------------------------------------------------------


@pytest.fixture
def option_chain_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_cache.reset_for_tests(tmp_path / "cache.db")
    monkeypatch.setattr(nse_bhavcopy, "_ist_today", lambda: date(2026, 9, 25))
    yield
    data_cache.reset_for_tests(None)


@pytest.mark.asyncio
async def test_failed_today_probe_falls_back_to_a_cached_previous_day(
    option_chain_cache: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    yesterday = date(2026, 9, 24)
    cached_rows = {"NIFTY": [["2026-10-01", 23000, "call", 100, 10, 1.0, 1.0, 5, 23000.0]]}
    await data_cache.set(option_chain._cache_key(yesterday), {"rows": cached_rows})

    async def fake_fetch(day: date) -> tuple[str, None]:
        # Cache-only from here: the walk must never re-probe an older day
        # once today's probe has failed outright.
        assert day == date(2026, 9, 25)
        return "failed", None

    monkeypatch.setattr(option_chain, "_fetch_fo_day", fake_fetch)
    result = await option_chain.fetch_latest_fo()
    assert result is not None
    assert result.trade_date == yesterday
    assert result.rows == cached_rows


@pytest.mark.asyncio
async def test_two_calls_with_todays_404_probe_the_network_once(
    option_chain_cache: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[date] = []

    async def fake_fetch(day: date) -> tuple[str, None]:
        calls.append(day)
        return "missing", None

    monkeypatch.setattr(option_chain, "_fetch_fo_day", fake_fetch)
    first = await option_chain.fetch_latest_fo(max_lookback_days=0)
    second = await option_chain.fetch_latest_fo(max_lookback_days=0)
    assert first is None and second is None
    assert calls == [date(2026, 9, 25)]  # the second call reused the cached probe
