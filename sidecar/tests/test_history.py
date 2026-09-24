"""Tests for the /history router."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_get_history(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/history/AAPL", params={"timeframe": "1d"}).json()
    assert body["symbol"] == "AAPL"
    assert body["timeframe"] == "1d"
    assert body["provider"] == "yfinance"
    assert len(body["bars"]) == 3
    first = body["bars"][0]
    assert first["open"] == 188.0
    assert first["close"] == 190.0
    assert first["volume"] == 48_000_000.0


def test_get_history_default_timeframe(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/history/AAPL").json()
    assert body["timeframe"] == "1d"
    assert len(body["bars"]) == 3


def test_get_history_carries_freshness(client: TestClient, mock_yfinance: object) -> None:
    """The series carries a calendar-aware freshness label for its last bar so the
    chart never shows a stale series as current (SC-019)."""
    body = client.get("/history/AAPL", params={"timeframe": "1d"}).json()
    assert body["freshness"] in {"live", "eod", "stale"}


def test_get_history_empty_series_returns_clean_200(client: TestClient, monkeypatch) -> None:
    """Bug-2: when every provider yields an EMPTY series the route downgrades to a
    clean 200 empty series (the chart renders its honest "No price data" state),
    NOT a scary (502)."""
    from services import provider_registry
    from services.correctness_gate import EmptySeriesError

    def _all_empty(symbol: str, timeframe: str, range_, asset_class: str):
        raise EmptySeriesError(f"correctness gate: empty series for {symbol!r} from 'yfinance'")

    monkeypatch.setattr(provider_registry, "get_history", _all_empty)
    resp = client.get("/history/ZZZZ", params={"timeframe": "1d"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "ZZZZ"
    assert body["timeframe"] == "1d"
    assert body["bars"] == []
    assert body["provider"] == "none"


def test_empty_series_in_symbol_carries_eod_only_reason(client: TestClient, monkeypatch) -> None:
    """WS6 Step 4: an IN symbol producing an all-empty series carries a typed
    `reason=="in_eod_only"` through the /history route so ChartPanel can show the
    region-aware "EOD only" message instead of the generic
    "No price data". Guards the chain region_hint → _empty_series_reason → the
    serialized model field against silent regression."""
    from services import provider_registry
    from services.correctness_gate import EmptySeriesError

    def _all_empty(symbol: str, timeframe: str, range_, asset_class: str):
        raise EmptySeriesError(f"correctness gate: empty series for {symbol!r} from 'bse'")

    monkeypatch.setattr(provider_registry, "get_history", _all_empty)

    # A bare BSE-only ticker resolves to IN → the typed reason for an intraday
    # timeframe (R15-DATA-064: an empty DAILY series is not an EOD-only cause).
    body = client.get("/history/ICONIKSPEV", params={"timeframe": "5m"}).json()
    assert body["bars"] == []
    assert body["provider"] == "none"
    assert body["reason"] == "in_eod_only"

    # A .BO-suffixed symbol is decisively IN → same typed reason.
    body_bo = client.get("/history/RELIANCE.BO", params={"timeframe": "15m"}).json()
    assert body_bo["reason"] == "in_eod_only"

    # A US symbol carries no IN reason (the generic message stays correct).
    body_us = client.get("/history/AAPL", params={"timeframe": "5m"}).json()
    assert body_us["bars"] == []
    assert body_us.get("reason") is None


def test_empty_series_reason_unit() -> None:
    """Direct unit guard on the typed-reason helper (no route)."""
    from routers.history import _empty_series_reason

    assert _empty_series_reason("ICONIKSPEV", "5m") == "in_eod_only"
    assert _empty_series_reason("RELIANCE.BO", "1h") == "in_eod_only"
    assert _empty_series_reason("AAPL", "5m") is None


def test_in_eod_only_is_only_for_intraday_on_a_known_in_listing() -> None:
    """R15-DATA-064: a daily no-trade series (DAL), an unknown symbol and a caret
    index are not "BSE/NSE serve EOD only"; a 5m RELIANCE.NS series is."""
    import config
    from routers.history import _empty_series_reason

    token = config.set_request_region("IN")
    try:
        assert _empty_series_reason("DAL.BO", "1d") is None
        assert _empty_series_reason("ZZUNKNOWNXQ", "5m") is None
        assert _empty_series_reason("^NSEI", "30m") is None
        assert _empty_series_reason("RELIANCE.NS", "5m") == "in_eod_only"
    finally:
        config.reset_request_region(token)


def test_history_iconikspev_serves_real_bars_from_bhavcopy(
    client: TestClient, monkeypatch, tmp_path
) -> None:
    """R7 Component 4 acceptance — /history/ICONIKSPEV returns REAL EOD bars
    assembled from the (fixture) BSE bhavcopy via scrip-code routing, end to end
    through the route → registry → bse_provider chain. The NSE lanes fast-fail
    (ICONIKSPEV is BSE-only, not in the NSE master) without a network call; the
    bhavcopy HTTP seam is mocked with the observed 2026-06-09 row, so the test
    is fully offline. Before the master regeneration this returned
    ``bars:[], provider:"none", reason:null`` — the live defect."""
    import httpx

    from services import bse_provider

    bhav_csv = (
        "TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,"
        "FininstrmActlXpryDt,StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,"
        "LastPric,PrvsClsgPric,UndrlygPric,SttlmPric,OpnIntrst,ChngInOpnIntrst,TtlTradgVol,"
        "TtlTrfVal,TtlNbOfTxsExctd,SsnId,NewBrdLotQty,Rmks,Rsvd1,Rsvd2,Rsvd3,Rsvd4\n"
        "2026-06-09,2026-06-09,CM,BSE,STK,511260,INE088P01015,ICONIKSPEV,X,,,,,"
        "ICONIK SPORTS AND EVENTS LIMIT,44.99,44.99,42.31,43.09,43.48,44.44,,43.09,,,"
        "5757,251369.00,88,F1,1,,,,,\n"
    )
    monkeypatch.setattr(bse_provider, "_cache_dir", lambda: str(tmp_path))
    monkeypatch.setattr(
        bse_provider, "_http_get", lambda url: httpx.Response(200, content=bhav_csv.encode())
    )

    resp = client.get("/history/ICONIKSPEV", params={"timeframe": "1d", "range": "1mo"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "ICONIKSPEV"
    assert body["provider"] == "bse"
    assert body["bars"], "expected real EOD bars from the fixture bhavcopy"
    assert all(b["close"] == 43.09 for b in body["bars"])
    assert body.get("reason") is None  # bars present → no empty-series reason


def test_get_history_integrity_failure_still_502(client: TestClient, monkeypatch) -> None:
    """A genuine data-integrity failure (a non-empty CorrectnessError — non-positive
    close / symbol mismatch) still surfaces as 502; only the empty-series case is
    softened (the recon's "distinguish on the specific failure" rule)."""
    from services import provider_registry
    from services.correctness_gate import CorrectnessError

    def _integrity_fail(symbol: str, timeframe: str, range_, asset_class: str):
        raise CorrectnessError("correctness gate: non-positive last close -1.0 for 'AAPL'")

    monkeypatch.setattr(provider_registry, "get_history", _integrity_fail)
    resp = client.get("/history/AAPL", params={"timeframe": "1d"})
    assert resp.status_code == 502


def test_us_series_in_an_in_session_reads_the_us_calendar(client: TestClient, monkeypatch) -> None:
    # R15-UI-090: an AAPL intraday series whose last bar is from NSE hours, read
    # in an IN session, is dated against the (closed) US session, not NSE's.
    from datetime import UTC, datetime

    from models.market import OHLCVBar, OHLCVSeries
    from services import locale, provider_registry

    now = datetime(2026, 9, 23, 5, 0, tzinfo=UTC)

    class _Frozen(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001, ANN206
            return now.astimezone(tz) if tz else now

    monkeypatch.setattr(locale, "datetime", _Frozen)
    bar = OHLCVBar(timestamp=now, open=1.0, high=2.0, low=1.0, close=1.5, volume=10.0)

    def series(symbol, timeframe, range_=None, asset_class="equity"):  # noqa: ANN001, ANN202, ARG001
        return OHLCVSeries(symbol=symbol, timeframe=timeframe, bars=[bar], provider="yfinance")

    monkeypatch.setattr(provider_registry, "get_history", series)
    headers = {"X-Vysted-Region": "IN"}
    body = client.get("/history/AAPL", params={"timeframe": "5m"}, headers=headers).json()
    assert body["freshness"] != "live"
    body = client.get("/history/RELIANCE.NS", params={"timeframe": "5m"}, headers=headers).json()
    assert body["freshness"] == "live"


def _crypto_series(monkeypatch, asked: list) -> None:  # noqa: ANN001
    from datetime import UTC, datetime

    from models.market import OHLCVBar, OHLCVSeries
    from services import provider_registry

    bars = [
        OHLCVBar(
            timestamp=datetime(2026, 9, day, tzinfo=UTC),
            open=1.0,
            high=2.0,
            low=1.0,
            close=1.5 + day,
            volume=10.0,
        )
        for day in range(1, 30)
    ]

    def series(symbol, timeframe, range_=None, asset_class="equity"):  # noqa: ANN001, ANN202
        asked.append((symbol, asset_class))
        return OHLCVSeries(symbol=symbol, timeframe=timeframe, bars=bars, provider="ccxt:binance")

    monkeypatch.setattr(provider_registry, "get_history", series)


def test_a_crypto_pair_routes_through_the_history_path(client: TestClient, monkeypatch) -> None:
    """R15-DATA-081: ``BTC/USDT`` arrives as ``BTC%2FUSDT``; Starlette decodes it
    before matching, so the route takes a path parameter."""
    asked: list = []
    _crypto_series(monkeypatch, asked)
    resp = client.get("/history/BTC%2FUSDT", params={"asset_class": "crypto"})
    assert resp.status_code == 200
    assert asked == [("BTC/USDT", "crypto")]


def test_a_crypto_pair_routes_through_the_indicators_path(client: TestClient, monkeypatch) -> None:
    """The class case the history fix was not written against: the indicators
    route takes the same slash-carrying symbol."""
    asked: list = []
    _crypto_series(monkeypatch, asked)
    resp = client.get(
        "/indicators/BTC%2FUSDT", params={"indicators": "rsi", "asset_class": "crypto"}
    )
    assert resp.status_code == 200
    assert asked == [("BTC/USDT", "crypto")]
