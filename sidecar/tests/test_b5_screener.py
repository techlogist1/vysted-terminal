"""Batch-5 screener pins (R15 Stage C, W5)."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

import config
from models.fundamentals import Fundamentals
from models.market import Quote
from models.screener import NumericThresholdCriterion, ScreenerRequest, ScreenerUniverse
from services import data_cache, fundamentals_store, provider_health, screener
from services import yahoo_batch_provider as yb
from services.errors import ProviderError


@pytest.fixture(autouse=True)
def _isolated_stores(tmp_path: Path) -> None:
    data_cache.reset_for_tests(tmp_path / "cache.db")
    fundamentals_store.reset_for_tests(tmp_path / "fundamentals.db")
    yb.reset_for_tests()
    provider_health.reset_for_tests()
    yield
    data_cache.reset_for_tests(None)
    fundamentals_store.reset_for_tests(None)
    yb.reset_for_tests()
    provider_health.reset_for_tests()


def _v7_row(symbol: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "longName": f"{symbol} Inc.",
        "regularMarketPrice": 150.0,
        "regularMarketChangePercent": 1.0,
        "regularMarketVolume": 1_000_000,
        "regularMarketTime": 1_700_000_000,
        "currency": "USD",
        "marketCap": 500_000_000_000,
        "trailingPE": 20.0,
    }


def _install_v7(symbols: list[str]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="crumb")
        if request.url.path.endswith("/v7/finance/quote"):
            requested = (request.url.params.get("symbols") or "").split(",")
            rows = [_v7_row(s) for s in requested if s in symbols]
            return httpx.Response(200, json={"quoteResponse": {"result": rows}})
        return httpx.Response(200, text="ok")

    yb.reset_for_tests(httpx.MockTransport(handler))


def _fake_universe(symbols: list[str]):
    async def _resolve(universe_id, custom_symbols=None):  # noqa: ANN001, ARG001
        return ScreenerUniverse(id="sp500", label="S&P 500", symbols=symbols, asset_class="equity")

    return _resolve


@pytest.mark.asyncio
async def test_enrichment_code_bug_logs_warning_and_progress_completes(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """R15-LIFECYCLE-017: an adapter bug (AttributeError) during phase E is
    logged at WARNING with its type, and the enrich progress still reaches m/m."""
    symbols = ["AAA", "BBB", "CCC"]
    _install_v7(symbols)
    monkeypatch.setattr(screener, "resolve_universe", _fake_universe(symbols))

    async def broken_adapter(symbol: str) -> Fundamentals:
        raise AttributeError("'NoneType' object has no attribute 'get'")

    monkeypatch.setattr("services.provider_registry.get_fundamentals", broken_adapter)

    frames: list[tuple[str, int, int]] = []
    request = ScreenerRequest(
        universe="sp500",
        criteria=[NumericThresholdCriterion(field="roe", operator="gt", value=0.1)],
        limit=100,
    )
    with caplog.at_level(logging.WARNING, logger="services.screener"):
        await screener.run_screener(
            request, on_progress=lambda phase, done, total, _d: frames.append((phase, done, total))
        )

    warnings = [r for r in caplog.records if "unexpected enrichment error" in r.getMessage()]
    assert len(warnings) == 3
    assert all("AttributeError" in r.getMessage() for r in warnings)
    enrich = [(done, total) for phase, done, total in frames if phase == "enrich"]
    assert enrich and enrich[-1] == (3, 3)


@pytest.mark.asyncio
async def test_all_rate_limited_run_is_partial_with_nothing_evaluated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-UI-055: a run the upstream throttled end to end evaluated nothing,
    so it is partial — not a complete run where no stock passed."""
    symbols = ["AAA", "BBB", "CCC"]
    monkeypatch.setattr(screener, "resolve_universe", _fake_universe(symbols))

    def all_429(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="crumb")
        return httpx.Response(429, text="Too Many Requests")

    async def _no_sleep(_secs: float) -> None:
        return None

    async def throttled(symbol: str) -> Fundamentals:
        raise ProviderError(f"throttled {symbol}", kind="rate_limited")

    yb.reset_for_tests(httpx.MockTransport(all_429))
    monkeypatch.setattr(yb.asyncio, "sleep", _no_sleep)
    monkeypatch.setattr("services.provider_registry.get_fundamentals", throttled)

    result = await screener.run_screener(ScreenerRequest(universe="sp500", criteria=[]))

    assert result.evaluated_count == 0
    assert {d.reason for d in result.skip_details} == {"rate_limited"}
    assert result.partial is True
    assert result.throttled is True


def test_default_universe_route_follows_the_request_region(client) -> None:  # noqa: ANN001
    """R15-CODE-DATA-004: the region default comes from the sidecar's one map."""
    assert client.get("/screener/default-universe", headers={"X-Vysted-Region": "IN"}).json() == {
        "universe": "nifty50"
    }
    assert client.get("/screener/default-universe", headers={"X-Vysted-Region": "US"}).json() == {
        "universe": "sp500"
    }


@pytest.mark.asyncio
async def test_warm_loop_is_lazy_and_follows_the_request_region(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-LIFECYCLE-020: arming the warm loop at boot warms nothing; the first
    screener run under IN starts it on nifty50, not sp500."""
    warmed: list[list[str]] = []

    async def record_batch(symbols: list[str]):
        warmed.append(list(symbols))
        return {}, {}

    async def fund(symbol: str) -> Fundamentals:
        return Fundamentals(symbol=symbol, market_cap=1e9, provider="test")

    def quote(symbol: str, _asset_class: str = "equity") -> Quote:
        return Quote(
            symbol=symbol,
            price=1.0,
            change=0.0,
            change_percent=0.0,
            volume=1.0,
            currency="INR",
            timestamp=datetime.now(tz=UTC),
            provider="test",
        )

    monkeypatch.setattr(yb, "fetch_quotes_batch", record_batch)
    monkeypatch.setattr("services.provider_registry.get_fundamentals", fund)
    monkeypatch.setattr("services.provider_registry.get_quote", quote)

    screener.start_warm_precompute(interval=0.01)
    try:
        await asyncio.sleep(0.05)
        assert warmed == [] and screener._warm_task is None

        token = config.set_request_region("IN")
        try:
            await screener.run_screener(
                ScreenerRequest(universe="custom", custom_symbols=["RELIANCE"], criteria=[])
            )
        finally:
            config.reset_request_region(token)
        for _ in range(100):
            if warmed:
                break
            await asyncio.sleep(0.01)

        nifty = (await screener.resolve_universe("nifty50")).symbols
        assert warmed and warmed[0] == list(nifty)
    finally:
        await screener.stop_warm_precompute()
