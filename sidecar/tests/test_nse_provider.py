"""R7 Component 2 — the NSE exchange-direct anti-bot lane (nse_provider).

All network is mocked at the curl_cffi-session seam (``nse_provider._new_session``)
so NO test hits the live NSE. The JSON fixtures under ``tests/fixtures/nse/``
are VERBATIM trims of the live responses captured by the one-off scratch probe
(2026-06-10 IST, symbol RELIANCE) — including the OBSERVED Akamai
"Access Denied" body for the edge-blocked ``api/quote-equity`` path. These
tests assert the cookie dance (warm-up before the first API call), the
observed-shape parses (historicalOR rows, the three corporates lists), session
rotation on 401/403, the per-path circuit breaker, the throttle pacing, the
EOD-quote fallback for the blocked quote path, and the registry ranking
(nse_direct above jugaad above bse above yfinance for IN).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services import nse_provider, provider_registry, symbol_resolver
from services.errors import ProviderError

_FIXTURES = Path(__file__).parent / "fixtures" / "nse"

_HISTORICAL = json.loads((_FIXTURES / "historical_or_cm_equity.json").read_text())
_ANNOUNCEMENTS = json.loads((_FIXTURES / "corporate_announcements.json").read_text())
_EVENTS = json.loads((_FIXTURES / "event_calendar.json").read_text())
_SHAREHOLDING = json.loads((_FIXTURES / "corporate_share_holdings_master.json").read_text())
_ACCESS_DENIED = (_FIXTURES / "quote_equity_access_denied.html").read_text()


# ---------------------------------------------------------------------------
# Fake curl_cffi session seam.
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, status_code: int = 200, payload: object = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> object:
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class _FakeSession:
    """Records calls; delegates API responses to a per-test responder."""

    def __init__(self, responder) -> None:  # noqa: ANN001
        self._responder = responder
        self.calls: list[tuple[str, dict]] = []
        self.closed = False

    def get(self, url, params=None, headers=None, timeout=None):  # noqa: ANN001, ANN201
        self.calls.append((url, dict(params or {})))
        return self._responder(self, url, dict(params or {}))

    def close(self) -> None:
        self.closed = True


def _install(monkeypatch: pytest.MonkeyPatch, responder) -> list[_FakeSession]:  # noqa: ANN001
    """Route ``_new_session`` to fakes sharing one responder; return the fakes."""
    sessions: list[_FakeSession] = []

    def factory():  # noqa: ANN202
        session = _FakeSession(responder)
        sessions.append(session)
        return session

    monkeypatch.setattr(nse_provider, "_new_session", factory)
    return sessions


def _ok_responder(api_map: dict[str, object]):  # noqa: ANN202
    """Responder serving 200s: the warm-up homepage + a path→payload map."""

    def responder(session: _FakeSession, url: str, params: dict) -> _FakeResponse:
        if url == "https://www.nseindia.com/":
            return _FakeResponse(200, payload=None, text="<html>home</html>")
        for path, payload in api_map.items():
            if url.endswith(path):
                return _FakeResponse(200, payload=payload)
        raise AssertionError(f"unexpected URL in test: {url}")

    return responder


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch) -> None:
    symbol_resolver.reset_caches_for_tests()
    nse_provider.reset_for_tests()
    # No real sleeping in tests — pacing logic is tested directly on _Throttle.
    monkeypatch.setattr(nse_provider, "_throttle", nse_provider._Throttle(sleep=lambda _s: None))


# ---------------------------------------------------------------------------
# Cookie dance — warm-up precedes the first API call.
# ---------------------------------------------------------------------------


def test_warmup_hits_homepage_before_first_api_call(monkeypatch: pytest.MonkeyPatch) -> None:
    sessions = _install(monkeypatch, _ok_responder({"/api/historicalOR/cm/equity": _HISTORICAL}))
    series = nse_provider.get_history("RELIANCE", "1d", "1mo")
    assert series.bars
    assert len(sessions) == 1
    urls = [u for u, _ in sessions[0].calls]
    assert urls[0] == "https://www.nseindia.com/"  # the cookie warm-up
    assert urls[1].endswith("/api/historicalOR/cm/equity")
    # The API call carried the observed query contract.
    _, params = sessions[0].calls[1]
    assert params["symbol"] == "RELIANCE"
    assert params["series"] == '["EQ"]'
    assert "from" in params and "to" in params


# ---------------------------------------------------------------------------
# get_history — the OBSERVED historicalOR shape.
# ---------------------------------------------------------------------------


def test_get_history_parses_observed_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, _ok_responder({"/api/historicalOR/cm/equity": _HISTORICAL}))
    series = nse_provider.get_history("RELIANCE", "1d", "1mo")
    assert series.provider == "nse_direct"
    assert series.symbol == "RELIANCE"
    assert len(series.bars) == len(_HISTORICAL["data"])
    # Rows arrive newest-first; bars must be ascending, UTC-midnight dated.
    ts = [b.timestamp for b in series.bars]
    assert ts == sorted(ts)
    assert all(b.timestamp.tzinfo is not None and b.timestamp.hour == 0 for b in series.bars)
    # The newest fixture row's OHLCV survives the parse verbatim.
    newest = _HISTORICAL["data"][0]
    last = series.bars[-1]
    assert last.timestamp.date().isoformat() == newest["CH_TIMESTAMP"]
    assert last.open == newest["CH_OPENING_PRICE"]
    assert last.high == newest["CH_TRADE_HIGH_PRICE"]
    assert last.low == newest["CH_TRADE_LOW_PRICE"]
    assert last.close == newest["CH_CLOSING_PRICE"]
    assert last.volume == newest["CH_TOT_TRADED_QTY"]


def test_get_history_resamples_weekly(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, _ok_responder({"/api/historicalOR/cm/equity": _HISTORICAL}))
    series = nse_provider.get_history("RELIANCE", "1wk", "1mo")
    assert series.timeframe == "1wk"
    assert series.bars
    assert len(series.bars) <= len(_HISTORICAL["data"])


def test_intraday_timeframe_raises_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    sessions = _install(monkeypatch, _ok_responder({}))
    with pytest.raises(ProviderError, match="intraday"):
        nse_provider.get_history("RELIANCE", "5m", "1mo")
    assert sessions == []  # fast-fail, no warm-up


def test_non_nse_symbol_fast_fails_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    sessions = _install(monkeypatch, _ok_responder({}))
    with pytest.raises(ProviderError, match="not a known NSE instrument"):
        nse_provider.get_quote("AAPL")
    with pytest.raises(ProviderError, match="not a known NSE instrument"):
        nse_provider.get_history("AAPL", "1d", "1mo")
    assert sessions == []


def test_wide_range_exceeds_direct_lane_budget_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sessions = _install(monkeypatch, _ok_responder({}))
    with pytest.raises(ProviderError, match="budget"):
        nse_provider.get_history("RELIANCE", "1d", "5y")
    assert sessions == []  # the registry falls through to jugaad for wide ranges


def test_long_range_chunks_into_bounded_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    sessions = _install(monkeypatch, _ok_responder({"/api/historicalOR/cm/equity": _HISTORICAL}))
    series = nse_provider.get_history("RELIANCE", "1d", "2y")
    api_calls = [c for c in sessions[0].calls if c[0].endswith("/api/historicalOR/cm/equity")]
    assert len(api_calls) == 9  # 760d lookback / 90d windows
    # Identical fixture rows across windows dedupe by trading day.
    assert len(series.bars) == len(_HISTORICAL["data"])


def test_older_window_failure_truncates_instead_of_erroring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hits = {"n": 0}

    def responder(session: _FakeSession, url: str, params: dict) -> _FakeResponse:
        if url == "https://www.nseindia.com/":
            return _FakeResponse(200, text="home")
        hits["n"] += 1
        if hits["n"] == 1:
            return _FakeResponse(200, payload=_HISTORICAL)  # newest window serves
        return _FakeResponse(500, text="upstream sad")  # older window fails

    _install(monkeypatch, responder)
    series = nse_provider.get_history("RELIANCE", "1d", "2y")
    assert len(series.bars) == len(_HISTORICAL["data"])  # truncated, not errored
    assert hits["n"] == 2  # stopped extending older after the failure


def test_newest_window_failure_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def responder(session: _FakeSession, url: str, params: dict) -> _FakeResponse:
        if url == "https://www.nseindia.com/":
            return _FakeResponse(200, text="home")
        return _FakeResponse(500, text="upstream sad")

    _install(monkeypatch, responder)
    with pytest.raises(ProviderError, match="HTTP 500"):
        nse_provider.get_history("RELIANCE", "1d", "1mo")


# ---------------------------------------------------------------------------
# get_quote — priceInfo when served; OBSERVED-blocked path → EOD fallback.
# ---------------------------------------------------------------------------


def test_quote_parses_priceinfo_when_served(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "info": {"symbol": "RELIANCE"},
        "priceInfo": {
            "lastPrice": 1272.3,
            "previousClose": 1263.3,
            "change": 9.0,
            "pChange": 0.71,
        },
    }
    _install(monkeypatch, _ok_responder({"/api/quote-equity": payload}))
    q = nse_provider.get_quote("RELIANCE")
    assert q.provider == "nse_direct"
    assert q.symbol == "RELIANCE"
    assert q.price == 1272.3
    assert q.change == 9.0
    assert q.change_percent == 0.71
    assert q.currency == "INR"


def test_quote_blocked_falls_back_to_observed_eod(monkeypatch: pytest.MonkeyPatch) -> None:
    """The OBSERVED live behaviour: quote-equity 403s (Akamai path ACL) on every
    session while historicalOR serves on the same dance — the quote must come
    from the last historicalOR row + its official previous close."""

    def responder(session: _FakeSession, url: str, params: dict) -> _FakeResponse:
        if url == "https://www.nseindia.com/":
            return _FakeResponse(200, text="home")
        if url.endswith("/api/quote-equity"):
            return _FakeResponse(403, text=_ACCESS_DENIED)
        if url.endswith("/api/historicalOR/cm/equity"):
            return _FakeResponse(200, payload=_HISTORICAL)
        raise AssertionError(f"unexpected URL: {url}")

    _install(monkeypatch, responder)
    q = nse_provider.get_quote("RELIANCE")
    newest = _HISTORICAL["data"][0]
    assert q.provider == "nse_direct"
    assert q.price == newest["CH_CLOSING_PRICE"]
    expected_change = newest["CH_CLOSING_PRICE"] - newest["CH_PREVIOUS_CLS_PRICE"]
    assert q.change == pytest.approx(expected_change)
    assert q.change_percent == pytest.approx(
        expected_change / newest["CH_PREVIOUS_CLS_PRICE"] * 100.0
    )
    assert q.volume == newest["CH_TOT_TRADED_QTY"]
    assert q.currency == "INR"
    assert q.timestamp.date().isoformat() == newest["CH_TIMESTAMP"]


# ---------------------------------------------------------------------------
# Session rotation + per-path circuit breaker.
# ---------------------------------------------------------------------------


def test_rotation_on_403_then_success(monkeypatch: pytest.MonkeyPatch) -> None:
    state = {"sessions_seen": 0}

    def responder(session: _FakeSession, url: str, params: dict) -> _FakeResponse:
        if url == "https://www.nseindia.com/":
            return _FakeResponse(200, text="home")
        # First session is bot-flagged; the rotated session serves.
        if state["first"] is session:
            return _FakeResponse(403, text=_ACCESS_DENIED)
        return _FakeResponse(200, payload=_HISTORICAL)

    sessions = _install(monkeypatch, responder)

    original_factory = nse_provider._new_session

    def tracking_factory():  # noqa: ANN202
        s = original_factory()
        state.setdefault("first", s)
        state["sessions_seen"] += 1
        return s

    monkeypatch.setattr(nse_provider, "_new_session", tracking_factory)
    series = nse_provider.get_history("RELIANCE", "1d", "1mo")
    assert series.bars
    assert state["sessions_seen"] == 2  # rotated exactly once
    assert sessions[0].closed is True  # the burned session was discarded


def test_block_after_rotation_raises_and_opens_breaker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def responder(session: _FakeSession, url: str, params: dict) -> _FakeResponse:
        if url == "https://www.nseindia.com/":
            return _FakeResponse(200, text="home")
        return _FakeResponse(403, text=_ACCESS_DENIED)

    sessions = _install(monkeypatch, responder)
    # Each call burns two sessions (original + rotation) and records one block.
    for _ in range(nse_provider._BREAKER_THRESHOLD):
        with pytest.raises(ProviderError, match="blocked \\(HTTP 403\\)"):
            nse_provider.get_history("RELIANCE", "1d", "1mo")
    burned = len(sessions)
    assert burned == 2 * nse_provider._BREAKER_THRESHOLD
    # Breaker is now open: the next call fails fast with NO network traffic.
    with pytest.raises(ProviderError, match="circuit open"):
        nse_provider.get_history("RELIANCE", "1d", "1mo")
    assert len(sessions) == burned


def test_breaker_is_per_path_so_blocked_quote_cannot_poison_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def responder(session: _FakeSession, url: str, params: dict) -> _FakeResponse:
        if url == "https://www.nseindia.com/":
            return _FakeResponse(200, text="home")
        if url.endswith("/api/quote-equity"):
            return _FakeResponse(403, text=_ACCESS_DENIED)
        return _FakeResponse(200, payload=_HISTORICAL)

    _install(monkeypatch, responder)
    # Enough quote calls to open the quote path's breaker (each serves via the
    # EOD fallback — the user still gets a quote).
    for _ in range(nse_provider._BREAKER_THRESHOLD + 1):
        q = nse_provider.get_quote("RELIANCE")
        assert q.price > 0
    assert nse_provider._breaker_for("/api/quote-equity").seconds_remaining() > 0
    # The historical path stays healthy.
    series = nse_provider.get_history("RELIANCE", "1d", "1mo")
    assert series.bars


def test_circuit_breaker_cooldown_half_opens() -> None:
    clock = {"t": 0.0}
    breaker = nse_provider._CircuitBreaker(threshold=2, cooldown=100.0, clock=lambda: clock["t"])
    assert breaker.seconds_remaining() == 0.0
    breaker.record_block()
    assert breaker.seconds_remaining() == 0.0  # below threshold
    breaker.record_block()
    assert breaker.seconds_remaining() == pytest.approx(100.0)
    clock["t"] = 50.0
    assert breaker.seconds_remaining() == pytest.approx(50.0)
    clock["t"] = 101.0
    assert breaker.seconds_remaining() == 0.0  # half-open: one attempt allowed
    breaker.record_block()  # the attempt blocked again → re-open immediately
    assert breaker.seconds_remaining() == pytest.approx(100.0)
    breaker.record_ok()
    assert breaker.seconds_remaining() == 0.0


def test_throttle_spaces_calls_with_jitter() -> None:
    clock = {"t": 0.0}
    sleeps: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        clock["t"] += seconds

    throttle = nse_provider._Throttle(
        min_interval=1.0, jitter=0.4, sleep=fake_sleep, clock=lambda: clock["t"]
    )
    throttle.wait()  # first call never sleeps
    throttle.wait()
    throttle.wait()
    assert len(sleeps) == 2
    # Each gap is the base interval plus jitter in [0, 0.4].
    assert all(1.0 <= s <= 1.4 for s in sleeps)


# ---------------------------------------------------------------------------
# Corporate disclosures — the OBSERVED list shapes for Component 3.
# ---------------------------------------------------------------------------


def test_announcements_parse_observed_fixture_and_trim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sessions = _install(
        monkeypatch, _ok_responder({"/api/corporate-announcements": _ANNOUNCEMENTS})
    )
    items = nse_provider.get_corporate_announcements("RELIANCE", limit=2)
    assert len(items) == 2
    first = items[0]
    assert first["symbol"] == "RELIANCE"
    assert first["attchmntFile"].startswith("https://nsearchives.nseindia.com/")
    assert first["desc"] and first["sort_date"] and first["sm_isin"]
    _, params = sessions[0].calls[1]
    assert params == {"index": "equities", "symbol": "RELIANCE"}


def test_results_calendar_parses_observed_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, _ok_responder({"/api/event-calendar": _EVENTS}))
    rows = nse_provider.get_results_calendar("RELIANCE")
    assert rows == _EVENTS
    assert {"symbol", "company", "purpose", "bm_desc", "date"} <= set(rows[0])


def test_shareholding_master_parses_observed_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        _ok_responder({"/api/corporate-share-holdings-master": _SHAREHOLDING}),
    )
    rows = nse_provider.get_shareholding_master("RELIANCE")
    assert rows == _SHAREHOLDING
    first = rows[0]
    assert first["pr_and_prgrp"] is not None and first["public_val"] is not None
    assert first["date"]  # the quarter end, e.g. "31-MAR-2026"


def test_malformed_corporate_payload_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, _ok_responder({"/api/event-calendar": {"not": "a list"}}))
    with pytest.raises(ProviderError, match="malformed"):
        nse_provider.get_results_calendar("RELIANCE")


# ---------------------------------------------------------------------------
# Registry integration — nse_direct outranks jugaad outranks bse outranks yfinance.
# ---------------------------------------------------------------------------


def test_registry_ranks_nse_direct_first_for_in() -> None:
    for model_key in ("quote", "ohlcv"):
        ids = [p.id for p in provider_registry._candidates(model_key, "equity", "IN")]
        assert ids == ["nse_direct", "nse", "bse", "yfinance"]


def test_registry_skips_nse_direct_when_curl_cffi_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(nse_provider, "is_available", lambda: False)
    ids = [p.id for p in provider_registry._candidates("quote", "equity", "IN")]
    assert ids == ["nse", "bse", "yfinance"]
