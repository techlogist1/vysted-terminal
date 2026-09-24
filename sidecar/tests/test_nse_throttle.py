"""R15-DATA-066 + R15-DATA-062: the NSE quote lane under a watchlist batch.

An IN EOD close is cached until the next session closes, so a warm 20-name
batch never re-enters the 1 req/s throttle; the throttle sleeps outside its lock;
and ``/quotes`` answers each quote under the spelling that was requested.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from models.market import Quote
from services import locale, nse_provider, provider_registry, symbol_resolver
from services.errors import ProviderError

_NIFTY_20 = (
    "RELIANCE TCS HDFCBANK INFY ICICIBANK HINDUNILVR ITC SBIN BHARTIARTL KOTAKBANK "
    "LT AXISBANK ASIANPAINT MARUTI SUNPHARMA TITAN ULTRACEMCO BAJFINANCE WIPRO NESTLEIND"
).split()


class _Resp:
    def __init__(self, status_code: int, payload: object = None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> object:
        return self._payload


def _row(symbol: str, day: str, close: float) -> dict[str, object]:
    return {
        "CH_SYMBOL": symbol,
        "CH_TIMESTAMP": day,
        "CH_OPENING_PRICE": close,
        "CH_TRADE_HIGH_PRICE": close + 5,
        "CH_TRADE_LOW_PRICE": close - 5,
        "CH_CLOSING_PRICE": close,
        "CH_PREVIOUS_CLS_PRICE": close - 10,
        "CH_TOT_TRADED_QTY": 1000,
    }


class _Session:
    """An NSE edge that serves historicalOR and Akamai-blocks quote-equity."""

    calls = 0

    def get(self, url: str, params=None, headers=None, timeout=None):  # noqa: ANN001, ANN201
        _Session.calls += 1
        if url.endswith("/api/historicalOR/cm/equity"):
            day = locale.last_closed_session(locale.REGION_IN).isoformat()
            return _Resp(200, {"data": [_row(params["symbol"], day, 2500.0)]})
        if url.endswith("/api/quote-equity"):
            return _Resp(403)
        return _Resp(200)

    def close(self) -> None:
        pass


@pytest.fixture
def nse_edge(monkeypatch: pytest.MonkeyPatch) -> None:
    symbol_resolver.reset_caches_for_tests()
    nse_provider.reset_for_tests()
    _Session.calls = 0
    monkeypatch.setattr(nse_provider, "_new_session", _Session)
    monkeypatch.setattr(nse_provider, "_throttle", nse_provider._Throttle(sleep=lambda _s: None))
    monkeypatch.setattr(locale, "is_market_open", lambda *_a, **_k: False)
    yield
    nse_provider.reset_for_tests()


def test_throttle_sleeps_outside_its_lock() -> None:
    held: list[bool] = []
    clock = {"t": 0.0}
    throttle = nse_provider._Throttle(
        sleep=lambda _s: held.append(throttle._lock.locked()), clock=lambda: clock["t"]
    )
    throttle.wait()
    throttle.wait()
    assert held == [False]


def test_warm_20_symbol_batch_is_served_under_a_second(
    client: TestClient, nse_edge: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    requested = [f"{name}.NS" for name in _NIFTY_20]
    for symbol in requested:  # cold: one upstream round per name
        assert nse_provider.get_quote(symbol).provider == "nse_direct"
    upstream = _Session.calls
    # A real 1 req/s pacer from here on: any upstream call would cost ~1 s each.
    monkeypatch.setattr(nse_provider, "_throttle", nse_provider._Throttle())

    started = time.monotonic()
    resp = client.get("/quotes", params={"symbols": ",".join(requested)})
    elapsed = time.monotonic() - started

    assert resp.status_code == 200
    assert elapsed < 1.0
    assert _Session.calls == upstream
    body = resp.json()
    assert [q["symbol"] for q in body] == requested
    assert {q["provider"] for q in body} == {"nse_direct"}


def test_cached_close_expires_when_the_next_session_closes(nse_edge: None) -> None:
    nse_provider.get_quote("RELIANCE")
    before = _Session.calls
    nse_provider.get_quote("RELIANCE")
    assert _Session.calls == before  # served from the EOD cache
    stale = nse_provider._eod_quotes["RELIANCE"]
    nse_provider._eod_quotes["RELIANCE"] = stale.model_copy(
        update={"timestamp": stale.timestamp - timedelta(days=7)}
    )
    nse_provider.get_quote("RELIANCE")
    assert _Session.calls > before  # an older close is re-fetched


def test_last_closed_session_is_the_prior_day_before_the_close() -> None:
    ist = locale.market_timezone(locale.REGION_IN)
    wed_noon = datetime(2026, 9, 23, 12, 0, tzinfo=ist)
    wed_evening = datetime(2026, 9, 23, 16, 0, tzinfo=ist)
    assert locale.last_closed_session(locale.REGION_IN, wed_noon).isoformat() == "2026-09-22"
    assert locale.last_closed_session(locale.REGION_IN, wed_evening).isoformat() == "2026-09-23"


@pytest.mark.parametrize("requested", ["RELIANCE.NS", "TATASTEEL.BO"])
def test_batch_answers_under_the_requested_spelling(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, requested: str
) -> None:
    """R15-DATA-062: the lanes answer the bare symbol; the route stamps what was
    asked for, and a failed symbol is absent (the client shows it unavailable)."""

    def lane_quote(symbol: str, _asset_class: str = "equity") -> Quote:
        if symbol == "ZZZZNOPE":
            raise ProviderError("no provider has ZZZZNOPE", kind="not_found")
        return Quote(
            symbol=locale.strip_exchange_suffix(symbol),
            price=100.0,
            change=1.0,
            change_percent=1.0,
            currency="INR",
            timestamp=datetime.now(tz=UTC),
            provider="nse_direct",
        )

    monkeypatch.setattr(provider_registry, "get_quote", lane_quote)
    body = client.get("/quotes", params={"symbols": f"{requested},ZZZZNOPE"}).json()
    assert [q["symbol"] for q in body] == [requested]
