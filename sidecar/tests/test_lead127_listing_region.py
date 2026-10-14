"""R15-LEAD-127: price and fundamentals are fetched in the RESOLVED listing's
region, not the session's.

Under session IN, research bound 'Halliburton' to HAL/US and then filled the
brief with Hindustan Aeronautics' INR price and fundamentals: the legs got the
bare ticker and re-resolved it through ``config.get_region()``. The copilot's
``price_data``/``fundamentals`` tools had no region channel at all.

(a) research: the real ``resolve_symbol`` plus a recording stub for every other
tool; (b) the tool handlers, recording the region ``provider_registry``'s own
precedence (``_effective_region``) routes to; (c) fresh collision tickers.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import pytest

import config
from models.market import OHLCVBar, OHLCVSeries, Quote
from services import correctness_gate, provider_registry
from services.agent_tools import fundamentals as fundamentals_tool
from services.agent_tools import price_data as price_data_tool
from services.agent_tools.resolve_symbol import _resolve_symbol
from services.research.fast import gather_fast, snapshot_structured

_LEGS = ("price_data", "fundamentals")


def _research_legs(query: str) -> tuple[dict[str, Any], dict[str, str]]:
    """Run ``gather_fast(query)`` under session IN; return the resolved payload
    and the ambient region each price/fundamentals leg ran under."""
    seen: dict[str, str] = {}

    async def tool_call(name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "resolve_symbol":
            return await _resolve_symbol(args)
        if name in _LEGS:
            seen[name] = args.get("region") or config.get_region()
        return {"ok": False, "error": "stub"}

    async def main() -> dict[str, Any]:
        config.set_request_region("IN")
        out = await gather_fast(query, region="IN", tool_call=tool_call)
        assert config.get_region() == "IN"  # the scope never leaks to the caller
        return out

    out = asyncio.run(main())
    return (out.get("resolved") or {}).get("resolved") or {}, seen


@pytest.mark.parametrize(
    ("query", "symbol"),
    [("Halliburton", "HAL"), ("Ferrari", "RACE"), ("Carnival", "CCL")],
)
def test_research_fetches_a_us_namesake_in_us_under_session_in(query: str, symbol: str) -> None:
    resolved, seen = _research_legs(query)
    assert resolved.get("symbol") == symbol
    assert resolved.get("region") == "US"
    assert seen == {"price_data": "US", "fundamentals": "US"}


def test_research_control_in_listing_stays_in() -> None:
    resolved, seen = _research_legs("Hindustan Aeronautics")
    assert resolved.get("region") == "IN"
    assert seen == {"price_data": "IN", "fundamentals": "IN"}


def test_snapshot_without_listing_region_keeps_the_ambient_region() -> None:
    seen: dict[str, str] = {}

    async def tool_call(name: str, args: dict[str, Any]) -> dict[str, Any]:
        seen[name] = config.get_region()
        return {"ok": False, "error": "stub"}

    async def main() -> None:
        config.set_request_region("IN")
        await snapshot_structured(tool_call, "HAL", region="IN")
        assert seen == {"price_data": "IN", "fundamentals": "IN"}
        await snapshot_structured(tool_call, "HAL", region="IN", listing_region="US")
        assert seen == {"price_data": "US", "fundamentals": "US"}
        assert config.get_region() == "IN"

    asyncio.run(main())


class _FakeFundamentals:
    symbol = "HAL"

    def model_dump(self, **_kw: Any) -> dict[str, Any]:
        return {"symbol": "HAL"}


def _record_fundamentals_route(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    routed: list[str] = []

    async def fake_resolve(_key: str, _asset: str, eff: str, *_a: Any, **_k: Any) -> Any:
        routed.append(eff)
        return _FakeFundamentals()

    async def identity(fundamentals: Any) -> Any:
        return fundamentals

    monkeypatch.setattr(provider_registry, "_resolve_async", fake_resolve)
    monkeypatch.setattr(correctness_gate, "apply_exchange_financials", identity)
    return routed


def _record_price_route(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    routed: list[str] = []
    ts = datetime(2026, 1, 2, tzinfo=UTC)

    def fake_resolve(
        key: str, _asset: str, eff: str, _validate: Any, symbol: str, *_a: Any, **_k: Any
    ) -> Any:
        routed.append(eff)
        if key == "quote":
            return Quote.model_validate(
                {
                    "symbol": symbol,
                    "price": 1.0,
                    "change": 0.0,
                    "change_percent": 0.0,
                    "timestamp": ts.isoformat(),
                    "provider": "stub",
                }
            )
        bar = OHLCVBar(timestamp=ts, open=1.0, high=1.0, low=1.0, close=1.0, volume=1.0)
        return OHLCVSeries(symbol=symbol, timeframe="1d", bars=[bar], provider="stub")

    monkeypatch.setattr(provider_registry, "_resolve_sync", fake_resolve)
    return routed


def _under_in(coro_fn: Any, args: dict[str, Any]) -> dict[str, Any]:
    async def main() -> dict[str, Any]:
        config.set_request_region("IN")
        out = await coro_fn(args)
        assert config.get_region() == "IN"
        return out

    return asyncio.run(main())


@pytest.mark.parametrize("symbol", ["HAL", "RACE", "PTC"])
def test_fundamentals_region_arg_routes_the_us_listing(
    monkeypatch: pytest.MonkeyPatch, symbol: str
) -> None:
    routed = _record_fundamentals_route(monkeypatch)
    out = _under_in(fundamentals_tool._fundamentals, {"symbol": symbol, "region": "US"})
    assert out["ok"] is True
    assert routed == ["US"]


def test_fundamentals_without_region_keeps_the_session_listing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    routed = _record_fundamentals_route(monkeypatch)
    _under_in(fundamentals_tool._fundamentals, {"symbol": "HAL"})
    assert routed == ["IN"]


@pytest.mark.parametrize("symbol", ["HAL", "RACE", "PTC"])
def test_price_data_region_arg_routes_the_us_listing(
    monkeypatch: pytest.MonkeyPatch, symbol: str
) -> None:
    routed = _record_price_route(monkeypatch)
    out = _under_in(price_data_tool._price_data, {"symbol": symbol, "region": "us"})
    assert out["ok"] is True
    assert routed == ["US", "US"]


def test_price_data_without_or_with_unknown_region_keeps_the_session_listing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    routed = _record_price_route(monkeypatch)
    _under_in(price_data_tool._price_data, {"symbol": "HAL"})
    _under_in(price_data_tool._price_data, {"symbol": "HAL", "region": "NSE"})
    assert routed == ["IN"] * 4


def test_catalog_exposes_the_region_arg_on_both_tools() -> None:
    from services.agent_tools.catalog import CAPABILITY_CATALOG

    for name in _LEGS:
        props = CAPABILITY_CATALOG[name].input_schema["properties"]
        assert props["region"]["enum"] == ["US", "IN", "GLOBAL"]
        assert CAPABILITY_CATALOG[name].input_schema["required"] == ["symbol"]
