"""Tests for the /quotes router."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from models.market import Quote
from services.errors import ProviderError


@pytest.fixture
def yf_quote(mock_yfinance: type, monkeypatch: pytest.MonkeyPatch) -> type:
    """The shared yfinance fake plus the history metadata a real Ticker carries,
    which a yfinance quote reads its trade time from (R15-LEAD-005)."""
    monkeypatch.setattr(
        mock_yfinance,
        "get_history_metadata",
        lambda _self: {"regularMarketTime": int(time.time())},
        raising=False,
    )
    return mock_yfinance


def test_get_quote(client: TestClient, yf_quote: object) -> None:
    body = client.get("/quotes/AAPL").json()
    assert body["symbol"] == "AAPL"
    assert body["price"] == 192.5
    assert body["change"] == pytest.approx(2.5)
    assert body["change_percent"] == pytest.approx(2.5 / 190.0 * 100.0)
    assert body["provider"] == "yfinance"


def test_get_quote_carries_freshness(client: TestClient, yf_quote: object) -> None:
    """Every served quote carries a calendar-aware freshness label (SC-019).

    The recent mock-quote is never labelled ``stale`` — a legitimate close is
    ``live`` or ``eod``, never shown as a stale value (nor a stale value as live).
    """
    body = client.get("/quotes/AAPL").json()
    assert body["freshness"] in {"live", "eod"}


def test_get_quote_old_value_is_labeled_stale(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A quote dated well past the staleness tolerance is labelled ``stale`` — it
    is never presented as a live tick (SC-019, the 'no stale-as-live' invariant)."""
    from services import provider_registry

    def stale_quote(symbol: str, asset_class: str = "equity") -> Quote:  # noqa: ARG001
        return Quote(
            symbol=symbol,
            price=100.0,
            change=1.0,
            change_percent=1.0,
            timestamp=datetime.now(tz=UTC) - timedelta(days=45),
            provider="yfinance",
        )

    monkeypatch.setattr(provider_registry, "get_quote", stale_quote)
    body = client.get("/quotes/AAPL").json()
    assert body["freshness"] == "stale"


def test_crypto_quote_is_live(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Crypto trades 24/7, so a fresh crypto fetch is always labelled ``live``."""
    from services import provider_registry

    def crypto_quote(symbol: str, asset_class: str = "equity") -> Quote:  # noqa: ARG001
        return Quote(
            symbol=symbol,
            price=65000.0,
            change=500.0,
            change_percent=0.7,
            currency="USD",
            timestamp=datetime.now(tz=UTC) - timedelta(days=10),
            provider="ccxt",
        )

    monkeypatch.setattr(provider_registry, "get_quote", crypto_quote)
    # Batch endpoint avoids the encoded-slash path-routing issue of crypto pairs.
    body = client.get("/quotes", params={"symbols": "BTC/USDT", "asset_class": "crypto"}).json()
    assert len(body) == 1
    assert body[0]["freshness"] == "live"


def test_get_quotes_batch(client: TestClient, yf_quote: object) -> None:
    body = client.get("/quotes", params={"symbols": "AAPL,MSFT"}).json()
    assert len(body) == 2
    assert {q["symbol"] for q in body} == {"AAPL", "MSFT"}


def test_get_quotes_batch_skips_failures(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from services import provider_registry

    def fake_get_quote(symbol: str, asset_class: str = "equity") -> Quote:
        if symbol == "BAD":
            raise ProviderError("symbol not found")
        return Quote(
            symbol=symbol,
            price=100.0,
            change=1.0,
            change_percent=1.0,
            timestamp=datetime.now(tz=UTC),
            provider="yfinance",
        )

    monkeypatch.setattr(provider_registry, "get_quote", fake_get_quote)
    body = client.get("/quotes", params={"symbols": "AAPL,BAD,MSFT"}).json()
    assert [q["symbol"] for q in body] == ["AAPL", "MSFT"]


def test_get_quotes_batch_fans_out_concurrently(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each blocking provider call sleeps; concurrent fan-out keeps wall time ≈ one call.

    Sequential execution of N sleepy calls would take ~N * delay; the
    ``asyncio.to_thread`` + ``asyncio.gather`` fan-out runs them in parallel on
    worker threads so the batch finishes in roughly one call's time.
    """
    from services import provider_registry

    delay = 0.2
    n_symbols = 10

    def slow_get_quote(symbol: str, asset_class: str = "equity") -> Quote:  # noqa: ARG001
        time.sleep(delay)
        return Quote(
            symbol=symbol,
            price=100.0,
            change=1.0,
            change_percent=1.0,
            timestamp=datetime.now(tz=UTC),
            provider="yfinance",
        )

    monkeypatch.setattr(provider_registry, "get_quote", slow_get_quote)
    symbols = ",".join(f"SYM{i}" for i in range(n_symbols))

    start = time.perf_counter()
    body = client.get("/quotes", params={"symbols": symbols}).json()
    elapsed = time.perf_counter() - start

    assert len(body) == n_symbols
    # Sequential would be ~n_symbols * delay (= 2.0s). Concurrent must be well
    # under half that even allowing for thread-pool + scheduling overhead.
    assert elapsed < (n_symbols * delay) / 2, f"batch was not concurrent: {elapsed:.3f}s"


def test_get_quote_provider_error(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from services import provider_registry

    def boom(*_args: object, **_kwargs: object) -> Quote:
        raise ProviderError("upstream down")

    monkeypatch.setattr(provider_registry, "get_quote", boom)
    response = client.get("/quotes/AAPL")
    assert response.status_code == 502
    assert response.json()["detail"] == "The data provider returned an unexpected response."


#: 2026-09-23 10:30 IST: NSE is open, the US session is closed (01:00 ET).
_NSE_HOURS = datetime(2026, 9, 23, 5, 0, tzinfo=UTC)


def _freeze_locale_clock(monkeypatch: pytest.MonkeyPatch, now: datetime) -> None:
    from services import locale

    class _Frozen(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001, ANN206
            return now.astimezone(tz) if tz else now

    monkeypatch.setattr(locale, "datetime", _Frozen)


def test_us_quote_in_an_in_session_reads_the_us_calendar(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # R15-UI-090: region IN during NSE hours; AAPL's own session is closed, so
    # its quote is not live. An NSE listing at the same moment still is.
    from services import provider_registry

    _freeze_locale_clock(monkeypatch, _NSE_HOURS)

    def quote(symbol: str, asset_class: str = "equity") -> Quote:  # noqa: ARG001
        provider = "nse_direct" if symbol == "RELIANCE" else "yfinance"
        return Quote(
            symbol=symbol,
            price=100.0,
            change=0.0,
            change_percent=0.0,
            timestamp=_NSE_HOURS,
            provider=provider,
        )

    monkeypatch.setattr(provider_registry, "get_quote", quote)
    headers = {"X-Vysted-Region": "IN"}
    assert client.get("/quotes/AAPL", headers=headers).json()["freshness"] != "live"
    assert client.get("/quotes/RELIANCE", headers=headers).json()["freshness"] == "live"


@pytest.mark.parametrize("index_symbol", ["%5ENSEI", "%5EBSESN"])
@pytest.mark.parametrize("region_header", ["IN", "US"])
def test_indian_index_reads_the_nse_calendar_regardless_of_session_region(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    index_symbol: str,
    region_header: str,
) -> None:
    """R15-UI-090: an Indian caret index (served by yfinance) is dated against
    the NSE calendar, not the session region — live during NSE hours whether
    the active session region is IN or US."""
    from services import provider_registry

    _freeze_locale_clock(monkeypatch, _NSE_HOURS)

    def quote(symbol: str, asset_class: str = "equity") -> Quote:  # noqa: ARG001
        return Quote(
            symbol=symbol,
            price=100.0,
            change=0.0,
            change_percent=0.0,
            timestamp=_NSE_HOURS,
            provider="yfinance",
        )

    monkeypatch.setattr(provider_registry, "get_quote", quote)
    headers = {"X-Vysted-Region": region_header}
    body = client.get(f"/quotes/{index_symbol}", headers=headers).json()
    assert body["freshness"] == "live"


def test_a_crypto_pair_routes_through_the_quote_path(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R15-DATA-081: ``BTC/USDT`` arrives as ``BTC%2FUSDT``; Starlette decodes it
    before matching, so the route takes a path parameter."""
    from services import provider_registry

    asked: list[tuple[str, str]] = []

    def quote(symbol: str, asset_class: str = "equity") -> Quote:
        asked.append((symbol, asset_class))
        return Quote(
            symbol=symbol,
            price=67_000.0,
            change=0.0,
            change_percent=0.0,
            currency="USDT",
            timestamp=datetime.now(tz=UTC),
            provider="ccxt:binance",
        )

    monkeypatch.setattr(provider_registry, "get_quote", quote)
    resp = client.get("/quotes/BTC%2FUSDT", params={"asset_class": "crypto"})
    assert resp.status_code == 200
    assert asked == [("BTC/USDT", "crypto")]
