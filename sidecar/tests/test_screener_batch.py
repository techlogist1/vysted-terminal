"""Screener × Yahoo v7 batch fast-path integration tests (FR-126 / SC-034).

Drives ``run_screener`` through the REAL batch path with a mocked v7 transport
(no network) to prove: the batch resolves the common screener fields, the skip
ledger itemizes every drop, per-symbol enrichment fills the fields v7 omits, and
the warm-precompute worker pre-fills the cache for a sub-second warm run.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from models.fundamentals import Fundamentals
from models.market import Quote
from models.screener import (
    NumericThresholdCriterion,
    ScreenerRequest,
    StringEqCriterion,
)
from services import data_cache, screener
from services import yahoo_batch_provider as yb


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path) -> None:
    data_cache.reset_for_tests(tmp_path / "screener_batch_cache.db")
    yield
    data_cache.reset_for_tests(None)
    yb.reset_for_tests(None)


def _row(symbol: str, **fields: object) -> dict[str, object]:
    row: dict[str, object] = {"symbol": symbol}
    row.update(fields)
    return row


def _install_v7(rows_by_symbol: dict[str, dict[str, object]]) -> None:
    """Install a MockTransport serving the given v7 rows; unknown symbols drop."""

    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="testcrumb")
        if "/v7/finance/quote" in request.url.path:
            syms = request.url.params.get("symbols", "").split(",")
            result = [rows_by_symbol[s] for s in syms if s in rows_by_symbol]
            return httpx.Response(200, json={"quoteResponse": {"result": result}})
        return httpx.Response(200, text="ok")

    yb.reset_for_tests(httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_batch_path_resolves_common_fields_end_to_end() -> None:
    _install_v7(
        {
            "AAA": _row("AAA", regularMarketPrice=100.0, marketCap=500e9, trailingPE=15.0),
            "BBB": _row("BBB", regularMarketPrice=50.0, marketCap=50e9, trailingPE=15.0),
            "DDD": _row("DDD", regularMarketPrice=20.0, marketCap=500e9, trailingPE=40.0),
        }
    )
    req = ScreenerRequest(
        universe="custom",
        custom_symbols=["AAA", "BBB", "DDD"],
        criteria=[
            NumericThresholdCriterion(field="market_cap", operator="gt", value=100e9),
            NumericThresholdCriterion(field="pe_ratio", operator="lt", value=20.0),
        ],
        limit=10,
    )
    result = await screener.run_screener(req)
    assert [r.symbol for r in result.rows] == ["AAA"]
    assert result.evaluated_count == 3
    assert result.skipped_count == 0
    assert result.skip_details == []
    # The serving provider is the batch path.
    assert result.rows[0].price == 100.0


@pytest.mark.asyncio
async def test_skip_ledger_itemizes_every_drop() -> None:
    # AAA returns; GONE is not in the v7 response; ZERO has a non-positive price.
    _install_v7(
        {
            "AAA": _row("AAA", regularMarketPrice=100.0, marketCap=500e9),
            "ZERO": _row("ZERO", regularMarketPrice=0.0, marketCap=10e9),
        }
    )

    # No per-symbol fallback success: stub the registry so GONE/ZERO can't be
    # rescued by the fallback (they must remain itemized).
    async def _fail_fundamentals(symbol: str) -> Fundamentals:
        raise screener.ProviderError("no data")

    def _fail_quote(symbol: str, _ac: str = "equity") -> Quote:
        raise screener.ProviderError("no data")

    import services.provider_registry as pr

    orig_f, orig_q = pr.get_fundamentals, pr.get_quote
    pr.get_fundamentals = _fail_fundamentals  # type: ignore[assignment]
    pr.get_quote = _fail_quote  # type: ignore[assignment]
    try:
        req = ScreenerRequest(
            universe="custom",
            custom_symbols=["AAA", "GONE", "ZERO"],
            criteria=[],
            limit=10,
        )
        result = await screener.run_screener(req)
    finally:
        pr.get_fundamentals = orig_f  # type: ignore[assignment]
        pr.get_quote = orig_q  # type: ignore[assignment]

    assert {r.symbol for r in result.rows} == {"AAA"}
    assert result.skipped_count == 2
    assert result.skipped_count == len(result.skip_details)
    ledger = {d.symbol: d.reason for d in result.skip_details}
    assert set(ledger) == {"GONE", "ZERO"}
    # GONE was absent from the v7 result; the fallback also failed → not_found
    # provisional reason survives (or correctness_gate from the fallback).
    assert ledger["GONE"] in {"not_found", "correctness_gate", "no_data", "timeout"}
    assert ledger["ZERO"] in {"no_data", "correctness_gate", "not_found"}


@pytest.mark.asyncio
async def test_enrichment_fills_field_v7_omits() -> None:
    # v7 carries price/market_cap but NOT sector — a sector criterion forces a
    # per-symbol enrichment, which the registry supplies.
    _install_v7(
        {
            "AAA": _row("AAA", regularMarketPrice=100.0, marketCap=500e9),
            "BBB": _row("BBB", regularMarketPrice=50.0, marketCap=200e9),
        }
    )

    async def _fundamentals(symbol: str) -> Fundamentals:
        sector = "Technology" if symbol == "AAA" else "Energy"
        return Fundamentals(symbol=symbol, sector=sector, provider="test")

    import services.provider_registry as pr

    orig = pr.get_fundamentals
    pr.get_fundamentals = _fundamentals  # type: ignore[assignment]
    try:
        req = ScreenerRequest(
            universe="custom",
            custom_symbols=["AAA", "BBB"],
            criteria=[StringEqCriterion(field="sector", operator="eq", value="Technology")],
            limit=10,
        )
        result = await screener.run_screener(req)
    finally:
        pr.get_fundamentals = orig  # type: ignore[assignment]

    assert [r.symbol for r in result.rows] == ["AAA"]
    # AAA enriched with sector + kept its batch market_cap.
    assert result.rows[0].sector == "Technology"
    assert result.rows[0].market_cap == 500e9
    assert result.skip_details == []


@pytest.mark.asyncio
async def test_warm_cache_makes_second_run_hit_cache() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="c")
        if "/v7/finance/quote" in request.url.path:
            calls["n"] += 1
            syms = request.url.params.get("symbols", "").split(",")
            return httpx.Response(
                200,
                json={
                    "quoteResponse": {
                        "result": [_row(s, regularMarketPrice=10.0, marketCap=1e12) for s in syms]
                    }
                },
            )
        return httpx.Response(200, text="ok")

    yb.reset_for_tests(httpx.MockTransport(handler))
    req = ScreenerRequest(universe="custom", custom_symbols=["AAA", "BBB"], criteria=[], limit=10)

    first = await screener.run_screener(req)
    assert {r.symbol for r in first.rows} == {"AAA", "BBB"}
    assert calls["n"] >= 1

    # Second run within the quote TTL resolves entirely from the cache.
    before = calls["n"]
    second = await screener.run_screener(req)
    assert {r.symbol for r in second.rows} == {"AAA", "BBB"}
    assert calls["n"] == before, "second run should hit the warm cache, not re-batch"


@pytest.mark.asyncio
async def test_batch_failure_degrades_to_per_symbol(monkeypatch: pytest.MonkeyPatch) -> None:
    # Batch endpoint is down → graceful degrade to the per-symbol path.
    async def _down(symbols: list[str]):
        return {}, {s: "no_data" for s in symbols}

    monkeypatch.setattr(yb, "fetch_quotes_batch", _down)

    async def _fundamentals(symbol: str) -> Fundamentals:
        return Fundamentals(symbol=symbol, sector="Technology", market_cap=300e9, provider="test")

    def _quote(symbol: str, _ac: str = "equity") -> Quote:
        from datetime import UTC, datetime

        return Quote(
            symbol=symbol,
            price=10.0,
            change=0.1,
            change_percent=1.0,
            volume=1000.0,
            currency="USD",
            timestamp=datetime.now(tz=UTC),
            provider="test",
        )

    import services.provider_registry as pr

    monkeypatch.setattr(pr, "get_fundamentals", _fundamentals)
    monkeypatch.setattr(pr, "get_quote", _quote)

    req = ScreenerRequest(universe="custom", custom_symbols=["AAA", "BBB"], criteria=[], limit=10)
    result = await screener.run_screener(req)
    assert {r.symbol for r in result.rows} == {"AAA", "BBB"}
    assert result.skip_details == []


# ---------------------------------------------------------------------------
# Warm-precompute worker — startup-safe + no leak
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_warm_precompute_starts_and_stops_cleanly() -> None:
    warmed = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="c")
        if "/v7/finance/quote" in request.url.path:
            warmed["n"] += 1
            syms = request.url.params.get("symbols", "").split(",")
            return httpx.Response(
                200,
                json={
                    "quoteResponse": {
                        "result": [_row(s, regularMarketPrice=5.0, marketCap=1e9) for s in syms]
                    }
                },
            )
        return httpx.Response(200, text="ok")

    yb.reset_for_tests(httpx.MockTransport(handler))

    # A tiny interval so the first warm runs immediately; the universe is the
    # bundled sp500 snapshot (real symbols, mocked transport).
    screener.start_warm_precompute(interval=0.05)
    # Let the first warm cycle run.
    import asyncio

    for _ in range(50):
        await asyncio.sleep(0.02)
        if warmed["n"] > 0:
            break
    assert warmed["n"] > 0, "warm worker never ran a cycle"

    # Clean shutdown — task is cancelled + awaited, no leak.
    await screener.stop_warm_precompute()
    assert screener._warm_task is None


@pytest.mark.asyncio
async def test_start_warm_precompute_is_idempotent() -> None:
    yb.reset_for_tests(httpx.MockTransport(lambda r: httpx.Response(200, text="c")))
    screener.start_warm_precompute(interval=999.0)
    first = screener._warm_task
    screener.start_warm_precompute(interval=999.0)
    assert screener._warm_task is first, "second start should be a no-op"
    await screener.stop_warm_precompute()
