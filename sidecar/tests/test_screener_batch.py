"""Tests for the R4 batch fast path wired into ``run_screener`` (FR-126 / SC-034).

The curated equity universes (``sp500`` / ``nifty50``) route through the Yahoo
v7 batch provider; ``custom`` / ``crypto-top50`` stay on the per-symbol path
(covered by ``test_screener.py``). These tests:

  - drive a small ``sp500`` universe through the batch path with a mocked v7
    transport and assert the rows + the itemized skip ledger;
  - prove the skip ledger invariant ``skipped_count == len(skip_details)`` with
    a mix of resolved + not_found symbols;
  - prove a criterion on a v7-omitted field (e.g. ``roe``) triggers per-symbol
    enrichment, and that an enrichment miss itemizes ``missing_field:<f>``;
  - prove a TOTAL batch wipeout degrades gracefully to the per-symbol fallback.

The v7 endpoint is mocked at the transport level (no live Yahoo call); the
per-symbol fallback / enrichment provider is monkeypatched.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from models.fundamentals import Fundamentals
from models.market import Quote
from models.screener import (
    CriterionGroup,
    NumericThresholdCriterion,
    ScreenerRequest,
    ScreenerUniverse,
    StringEqCriterion,
)
from services import data_cache, fundamentals_store, screener
from services import yahoo_batch_provider as yb


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path) -> None:
    """Point the data cache at a tmp file + reset the batch session per test."""
    data_cache.reset_for_tests(tmp_path / "screener_batch_cache.db")
    fundamentals_store.reset_for_tests(tmp_path / "fundamentals_test.db")
    yb.reset_for_tests()
    yield
    data_cache.reset_for_tests(None)
    fundamentals_store.reset_for_tests(None)
    yb.reset_for_tests()


def _v7_row(symbol: str, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "symbol": symbol,
        "longName": f"{symbol} Inc.",
        "regularMarketPrice": 150.0,
        "regularMarketChange": 1.5,
        "regularMarketChangePercent": 1.0,
        "regularMarketVolume": 1_000_000,
        "regularMarketTime": 1_700_000_000,
        "currency": "USD",
        "marketCap": 500_000_000_000,
        "trailingPE": 20.0,
        "forwardPE": 18.0,
        "priceToBook": 10.0,
        "epsTrailingTwelveMonths": 6.0,
        "fiftyTwoWeekHigh": 199.0,
        "fiftyTwoWeekLow": 124.0,
        "fiftyTwoWeekChangePercent": 21.4,
        "trailingAnnualDividendYield": 0.01,
    }
    row.update(overrides)
    return row


def _install_v7(rows_by_symbol: dict[str, dict[str, object]]) -> None:
    """Install a MockTransport that serves a crumb + the given v7 rows."""

    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="crumb")
        if request.url.path.endswith("/v7/finance/quote"):
            requested = (request.url.params.get("symbols") or "").split(",")
            result = [rows_by_symbol[s] for s in requested if s in rows_by_symbol]
            return httpx.Response(200, json={"quoteResponse": {"result": result}})
        return httpx.Response(200, text="ok")

    yb.reset_for_tests(httpx.MockTransport(handler))


def _fake_sp500(symbols: list[str]):
    async def _resolve(universe_id, custom_symbols=None):  # noqa: ANN001, ARG001
        return ScreenerUniverse(id="sp500", label="S&P 500", symbols=symbols, asset_class="equity")

    return _resolve


@pytest.mark.asyncio
async def test_batch_path_resolves_curated_universe(monkeypatch: pytest.MonkeyPatch) -> None:
    symbols = ["AAA", "BBB", "CCC"]
    _install_v7({s: _v7_row(s, marketCap=(900 - i) * 1e9) for i, s in enumerate(symbols)})
    monkeypatch.setattr(screener, "resolve_universe", _fake_sp500(symbols))

    request = ScreenerRequest(
        universe="sp500",
        criteria=[NumericThresholdCriterion(field="pe_ratio", operator="lt", value=25.0)],
        limit=100,
    )
    result = await screener.run_screener(request)
    assert {r.symbol for r in result.rows} == {"AAA", "BBB", "CCC"}
    assert result.evaluated_count == 3
    assert result.skipped_count == 0
    assert result.skip_details == []
    # Field mapping landed on the rows (v7-covered fields populated).
    aaa = next(r for r in result.rows if r.symbol == "AAA")
    assert aaa.pe_ratio == 20.0
    assert aaa.forward_pe == 18.0
    assert aaa.price == 150.0


@pytest.mark.asyncio
async def test_skip_ledger_itemizes_unresolved(monkeypatch: pytest.MonkeyPatch) -> None:
    """A symbol Yahoo never returns AND the fallback cannot resolve is itemized."""
    symbols = ["AAA", "GHOST"]
    _install_v7({"AAA": _v7_row("AAA")})  # GHOST absent from v7
    monkeypatch.setattr(screener, "resolve_universe", _fake_sp500(symbols))

    # The per-symbol fallback also fails for GHOST (raises ProviderError).
    from services.errors import ProviderError

    async def fake_fund(symbol: str) -> Fundamentals:
        raise ProviderError("no such symbol")

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_fund)

    request = ScreenerRequest(universe="sp500", criteria=[], limit=100)
    result = await screener.run_screener(request)
    assert {r.symbol for r in result.rows} == {"AAA"}
    assert result.evaluated_count == 1
    # SC-034 invariant: every skip is itemized, count matches the list length.
    assert result.skipped_count == len(result.skip_details) == 1
    skip = result.skip_details[0]
    assert skip.symbol == "GHOST"
    # The fallback's correctness_gate reason supersedes the batch's provisional one.
    assert skip.reason == "correctness_gate"


@pytest.mark.asyncio
async def test_batch_provisional_skip_recovered_by_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A symbol the batch missed but the per-symbol fallback resolves is NOT skipped."""
    symbols = ["AAA", "LATE"]
    _install_v7({"AAA": _v7_row("AAA")})  # LATE absent from v7 → provisional not_found
    monkeypatch.setattr(screener, "resolve_universe", _fake_sp500(symbols))

    async def fake_fund(symbol: str) -> Fundamentals:
        return Fundamentals(symbol=symbol, market_cap=100e9, pe_ratio=12.0, provider="test")

    def fake_quote(symbol: str, _asset_class: str = "equity") -> Quote:
        return Quote(
            symbol=symbol,
            price=42.0,
            change=0.0,
            change_percent=0.0,
            volume=1.0,
            currency="USD",
            timestamp=datetime.now(tz=UTC),
            provider="test",
        )

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_fund)
    monkeypatch.setattr("services.provider_registry.get_quote", fake_quote)

    request = ScreenerRequest(universe="sp500", criteria=[], limit=100)
    result = await screener.run_screener(request)
    assert {r.symbol for r in result.rows} == {"AAA", "LATE"}
    assert result.skipped_count == 0
    assert result.skip_details == []


@pytest.mark.asyncio
async def test_enrichment_triggered_for_v7_omitted_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A criterion on ``roe`` (not on the v7 row) triggers per-symbol enrichment."""
    symbols = ["AAA", "BBB"]
    _install_v7({s: _v7_row(s) for s in symbols})
    monkeypatch.setattr(screener, "resolve_universe", _fake_sp500(symbols))

    async def fake_fund(symbol: str) -> Fundamentals:
        # Enrichment supplies roe; AAA passes the filter, BBB fails it.
        return Fundamentals(
            symbol=symbol,
            roe=0.30 if symbol == "AAA" else 0.05,
            provider="test-enrich",
        )

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_fund)

    request = ScreenerRequest(
        universe="sp500",
        criteria=[NumericThresholdCriterion(field="roe", operator="gt", value=0.20)],
        limit=100,
    )
    result = await screener.run_screener(request)
    assert {r.symbol for r in result.rows} == {"AAA"}
    # Both symbols were evaluable (enriched); only one matched the filter.
    assert result.evaluated_count == 2
    assert result.skipped_count == 0
    aaa = next(r for r in result.rows if r.symbol == "AAA")
    assert aaa.roe == 0.30
    # The batch-covered fields survive the enrichment merge.
    assert aaa.pe_ratio == 20.0


@pytest.mark.asyncio
async def test_enrichment_miss_itemizes_missing_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When enrichment cannot supply a needed field, the symbol is itemized."""
    symbols = ["AAA"]
    _install_v7({"AAA": _v7_row("AAA")})
    monkeypatch.setattr(screener, "resolve_universe", _fake_sp500(symbols))

    async def fake_fund(symbol: str) -> Fundamentals:
        # roe stays None → the needed field is still missing post-enrichment.
        return Fundamentals(symbol=symbol, provider="test")

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_fund)

    request = ScreenerRequest(
        universe="sp500",
        criteria=[NumericThresholdCriterion(field="roe", operator="gt", value=0.20)],
        limit=100,
    )
    result = await screener.run_screener(request)
    assert result.rows == []
    assert result.skipped_count == len(result.skip_details) == 1
    assert result.skip_details[0].symbol == "AAA"
    assert result.skip_details[0].reason == "missing_field:roe"


@pytest.mark.asyncio
async def test_total_batch_wipeout_degrades_to_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 500 from every chunk → batch yields nothing → per-symbol fallback runs."""
    symbols = ["AAA", "BBB"]

    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="crumb")
        if request.url.path.endswith("/v7/finance/quote"):
            return httpx.Response(500, text="down")
        return httpx.Response(200, text="ok")

    yb.reset_for_tests(httpx.MockTransport(handler))
    monkeypatch.setattr(screener, "resolve_universe", _fake_sp500(symbols))

    async def fake_fund(symbol: str) -> Fundamentals:
        return Fundamentals(symbol=symbol, sector="Technology", market_cap=100e9, provider="fb")

    def fake_quote(symbol: str, _asset_class: str = "equity") -> Quote:
        return Quote(
            symbol=symbol,
            price=10.0,
            change=0.0,
            change_percent=0.0,
            volume=1.0,
            currency="USD",
            timestamp=datetime.now(tz=UTC),
            provider="fb",
        )

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_fund)
    monkeypatch.setattr("services.provider_registry.get_quote", fake_quote)

    request = ScreenerRequest(
        universe="sp500",
        criteria=[StringEqCriterion(field="sector", operator="eq", value="Technology")],
        limit=100,
    )
    result = await screener.run_screener(request)
    assert {r.symbol for r in result.rows} == {"AAA", "BBB"}
    assert result.skipped_count == 0


@pytest.mark.asyncio
async def test_warm_cache_makes_second_run_skip_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A second batch run inside the quote TTL resolves from cache (no v7 call)."""
    symbols = ["AAA", "BBB"]
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="crumb")
        if request.url.path.endswith("/v7/finance/quote"):
            calls["n"] += 1
            requested = (request.url.params.get("symbols") or "").split(",")
            result = [_v7_row(s) for s in requested]
            return httpx.Response(200, json={"quoteResponse": {"result": result}})
        return httpx.Response(200, text="ok")

    yb.reset_for_tests(httpx.MockTransport(handler))
    monkeypatch.setattr(screener, "resolve_universe", _fake_sp500(symbols))

    request = ScreenerRequest(universe="sp500", criteria=[], limit=100)
    first = await screener.run_screener(request)
    assert {r.symbol for r in first.rows} == {"AAA", "BBB"}
    calls_after_first = calls["n"]
    assert calls_after_first >= 1

    second = await screener.run_screener(request)
    assert {r.symbol for r in second.rows} == {"AAA", "BBB"}
    # The warm cache short-circuits the batch endpoint entirely.
    assert calls["n"] == calls_after_first, "expected warm-cache hit, v7 re-called"


@pytest.mark.asyncio
async def test_group_field_drives_enrichment(monkeypatch: pytest.MonkeyPatch) -> None:
    """A v7-omitted field referenced ONLY inside an AND/OR group still enriches."""
    symbols = ["AAA"]
    _install_v7({"AAA": _v7_row("AAA")})
    monkeypatch.setattr(screener, "resolve_universe", _fake_sp500(symbols))

    async def fake_fund(symbol: str) -> Fundamentals:
        return Fundamentals(symbol=symbol, roe=0.25, provider="enrich")

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_fund)

    request = ScreenerRequest(
        universe="sp500",
        criteria=[],
        group=CriterionGroup(
            combinator="or",
            criteria=[NumericThresholdCriterion(field="roe", operator="gt", value=0.20)],
        ),
        limit=100,
    )
    result = await screener.run_screener(request)
    assert {r.symbol for r in result.rows} == {"AAA"}
    assert result.skipped_count == 0


# ---------------------------------------------------------------------------
# Warm-loop exponential backoff (self-inflicted-429 fix)
# ---------------------------------------------------------------------------


def test_warm_sleep_seconds_grows_geometrically_and_caps() -> None:
    """Consecutive throttled cycles grow the warm sleep, capped at the ceiling."""
    base = screener._WARM_INTERVAL_SECONDS
    factor = screener._WARM_BACKOFF_FACTOR
    cap = screener._WARM_BACKOFF_CAP_SECONDS
    jit = screener._WARM_BACKOFF_JITTER_FRACTION

    # The (pre-jitter) target per consecutive-throttle count.
    def target(n: int) -> float:
        return min(cap, base * (factor**n))

    # n == 0 → base; each step strictly larger until the cap is hit. Sample many
    # draws so the jittered value always stays inside ±jit of the target.
    prev_target = -1.0
    for n in range(0, 20):
        t = target(n)
        for _ in range(40):
            s = screener._warm_sleep_seconds(base, n)
            assert (t * (1 - jit)) - 1e-9 <= s <= (t * (1 + jit)) + 1e-9
        if t > prev_target:
            # Still climbing — strictly larger target than the last step.
            assert t > prev_target
        prev_target = t

    # A large streak is pinned at the cap (±jitter), never unbounded.
    big = target(50)
    assert big == cap
    for _ in range(40):
        s = screener._warm_sleep_seconds(base, 50)
        assert (cap * (1 - jit)) - 1e-9 <= s <= (cap * (1 + jit)) + 1e-9


def test_warm_sleep_seconds_zero_streak_is_base() -> None:
    """A clean cycle (streak 0) sleeps around base, never backed off."""
    base = screener._WARM_INTERVAL_SECONDS
    jit = screener._WARM_BACKOFF_JITTER_FRACTION
    for _ in range(100):
        s = screener._warm_sleep_seconds(base, 0)
        assert (base * (1 - jit)) - 1e-9 <= s <= (base * (1 + jit)) + 1e-9


@pytest.mark.asyncio
async def test_warm_once_flags_rate_limited_cycle(monkeypatch: pytest.MonkeyPatch) -> None:
    """_warm_once returns True iff the cycle came back near-totally rate_limited."""
    symbols = ["AAA", "BBB", "CCC", "DDD"]
    monkeypatch.setattr(screener, "resolve_universe", _fake_sp500(symbols))

    # All four symbols 429 → throttled cycle. asyncio.sleep stubbed so the
    # in-fetch retry adds no latency.
    async def _no_sleep(_secs: float) -> None:
        return None

    monkeypatch.setattr(yb.asyncio, "sleep", _no_sleep)

    def all_429(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="crumb")
        if request.url.path.endswith("/v7/finance/quote"):
            return httpx.Response(429, text="Too Many Requests")
        return httpx.Response(200, text="ok")

    yb.reset_for_tests(httpx.MockTransport(all_429))
    assert await screener._warm_once() is True

    # All four resolve cleanly → not a throttle.
    _install_v7({s: _v7_row(s) for s in symbols})
    assert await screener._warm_once() is False


@pytest.mark.asyncio
async def test_warm_loop_backs_off_then_resets(monkeypatch: pytest.MonkeyPatch) -> None:
    """A throttled streak grows the loop's sleep; the first clean cycle resets it.

    Drives ``_warm_loop`` with a scripted ``_warm_once`` (throttled ×3, then a
    clean cycle) and a stubbed ``asyncio.sleep`` that records each requested
    duration and cancels the loop once the script is exhausted — so no real time
    passes and cancellation still stops the loop cleanly."""
    # Throttle, throttle, throttle, clean — then stop.
    script = iter([True, True, True, False])
    sleeps: list[float] = []
    cycle = {"n": 0}

    async def fake_warm_once() -> bool:
        cycle["n"] += 1
        return next(script)

    async def fake_sleep(secs: float) -> None:
        sleeps.append(secs)
        if cycle["n"] >= 4:
            # Script exhausted (the clean cycle ran) — stop the loop the way a
            # real shutdown would, proving CancelledError still propagates.
            raise asyncio.CancelledError

    monkeypatch.setattr(screener, "_warm_once", fake_warm_once)
    monkeypatch.setattr(screener.asyncio, "sleep", fake_sleep)

    base = 10.0
    jit = screener._WARM_BACKOFF_JITTER_FRACTION
    factor = screener._WARM_BACKOFF_FACTOR

    with pytest.raises(asyncio.CancelledError):
        await screener._warm_loop(base)

    # Four cycles ran, four sleeps recorded.
    assert cycle["n"] == 4
    assert len(sleeps) == 4

    # Sleep n corresponds to a streak of (1, 2, 3, 0) consecutive throttles.
    def within(value: float, streak: int) -> bool:
        target = min(screener._WARM_BACKOFF_CAP_SECONDS, base * (factor**streak))
        return (target * (1 - jit)) - 1e-9 <= value <= (target * (1 + jit)) + 1e-9

    assert within(sleeps[0], 1)
    assert within(sleeps[1], 2)
    assert within(sleeps[2], 3)
    # The clean cycle reset the streak to 0 → back to base.
    assert within(sleeps[3], 0)
    # Monotonic growth across the throttled run (jitter can't reorder these gaps).
    assert sleeps[0] < sleeps[1] < sleeps[2]
    # And the reset genuinely dropped below the backed-off sleeps.
    assert sleeps[3] < sleeps[2]
    # Backoff state is observable and was reset to 0 on the clean cycle.
    assert screener._warm_consecutive_throttles == 0


@pytest.mark.asyncio
async def test_warm_loop_cancellation_stops_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    """A CancelledError raised inside the warm cycle propagates and stops the loop."""

    async def fake_warm_once() -> bool:
        raise asyncio.CancelledError

    monkeypatch.setattr(screener, "_warm_once", fake_warm_once)

    with pytest.raises(asyncio.CancelledError):
        await screener._warm_loop(screener._WARM_INTERVAL_SECONDS)
