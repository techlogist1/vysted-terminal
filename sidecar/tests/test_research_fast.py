"""Tests for ``services.research.fast.gather_fast`` — the FAST structured bundle.

No network, no real LLM, no real tool registry: ``tool_call`` is a fake that
returns canned dicts shaped like the real agent tools. The tests assert the
bundle shape, that the four structured legs are pulled in PARALLEL, the
asset-class-driven ``suggested_indicators``, provenance carry-through, and — the
honesty contract — that a ``web_search`` returning ``ok: False`` yields
``web.available = False`` with the honest fallback note (never a fabricated
section).
"""

from __future__ import annotations

import asyncio
from typing import Any

from services.research.fast import gather_fast


def _instrument(symbol: str, name: str, asset_class: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "name": name,
        "exchange": "NASDAQ",
        "region": "US",
        "asset_class": asset_class,
        "yahoo_symbol": symbol,
        "confidence": 0.99,
    }


class _FakeToolCall:
    """A canned ``tool_call`` recording call order + concurrency.

    ``web_ok`` toggles whether ``web_search`` reports a configured backend.
    ``started``/``max_concurrent`` track that the four structured legs overlap
    (a serial implementation would never exceed concurrency 1).
    """

    def __init__(
        self,
        *,
        asset_class: str = "equity",
        web_ok: bool = True,
        resolve_ok: bool = True,
        web_reason: str | None = None,
    ) -> None:
        self.asset_class = asset_class
        self.web_ok = web_ok
        self.resolve_ok = resolve_ok
        # When set, a failed web_search reports this TYPED reason (e.g.
        # "rate_limited") so the bundle picks the transient note over "no backend".
        self.web_reason = web_reason
        self.calls: list[str] = []
        self._active = 0
        self.max_concurrent = 0

    async def __call__(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(name)
        self._active += 1
        self.max_concurrent = max(self.max_concurrent, self._active)
        try:
            # Yield so genuinely-parallel legs overlap on the event loop.
            await asyncio.sleep(0)
            return self._dispatch(name, args)
        finally:
            self._active -= 1

    def _dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "resolve_symbol":
            if not self.resolve_ok:
                return {"ok": False, "message": "could not resolve"}
            return {
                "ok": True,
                "query": args.get("query"),
                "region": "US",
                "resolved": _instrument("AAPL", "Apple Inc.", self.asset_class),
                "needs_disambiguation": False,
                "candidates": [],
            }
        if name == "price_data":
            return {
                "ok": True,
                "symbol": "AAPL",
                "timeframe": "1d",
                "provider": "yfinance",
                "quote": {"symbol": "AAPL", "price": 192.5},
                "bars": [{"close": 192.5}],
            }
        if name == "fundamentals":
            return {
                "ok": True,
                "fundamentals": {"symbol": "AAPL", "pe_ratio": 30.0, "provider": "openbb"},
            }
        if name == "news":
            return {
                "ok": True,
                "count": 1,
                "news": [{"headline": "Apple ships", "source": "reuters"}],
            }
        if name == "sec_filings_list":
            return {
                "ok": True,
                "filings": {"items": [{"form": "10-K", "provider": "sec-edgar"}]},
            }
        if name == "web_search":
            if not self.web_ok:
                failed: dict[str, Any] = {
                    "ok": False,
                    "query": args.get("query"),
                    "message": "No web-search backend is configured. Add an Exa key.",
                }
                if self.web_reason is not None:
                    failed["reason"] = self.web_reason
                return failed
            return {
                "ok": True,
                "backend": "exa",
                "query": args.get("query"),
                "results": [{"url": "https://x.com/a", "title": "A", "snippet": "s"}],
                "citations": [{"url": "https://x.com/a", "title": "A", "excerpt": "e"}],
            }
        return {"ok": False, "error": f"unexpected tool {name}"}


def test_fast_bundle_shape_and_provenance() -> None:
    fake = _FakeToolCall(asset_class="equity", web_ok=True)
    bundle = asyncio.run(gather_fast("Apple outlook", region="US", tool_call=fake))

    assert bundle["ok"] is True
    assert bundle["symbol"] == "AAPL"
    assert bundle["suggested_layout"] == "research-cockpit"

    structured = bundle["structured"]
    assert set(structured) == {"price", "fundamentals", "news", "filings"}
    for slot in structured.values():
        assert slot["ok"] is True

    # Provenance carried per leg (FR-041 badge).
    assert structured["price"]["provider"] == "yfinance"
    assert structured["fundamentals"]["provider"] == "openbb"
    assert structured["filings"]["provider"] == "sec-edgar"

    # Web section present + populated when a backend answered.
    assert bundle["web"]["available"] is True
    assert bundle["web"]["citations"]
    assert "note" not in bundle["web"]


def test_fast_pulls_four_legs_in_parallel() -> None:
    fake = _FakeToolCall(asset_class="equity", web_ok=True)
    asyncio.run(gather_fast("Apple", region="US", tool_call=fake))

    # resolve, then four structured legs, then one web round.
    assert fake.calls[0] == "resolve_symbol"
    assert set(fake.calls[1:5]) == {"price_data", "fundamentals", "news", "sec_filings_list"}
    assert fake.calls[-1] == "web_search"
    assert fake.calls.count("web_search") == 1
    # The four structured legs overlapped (a serial pull peaks at 1).
    assert fake.max_concurrent >= 2


def test_fast_indicators_per_asset_class() -> None:
    equity = asyncio.run(
        gather_fast("AAPL", region="US", tool_call=_FakeToolCall(asset_class="equity"))
    )
    etf = asyncio.run(gather_fast("SPY", region="US", tool_call=_FakeToolCall(asset_class="etf")))
    crypto = asyncio.run(
        gather_fast("BTC", region="US", tool_call=_FakeToolCall(asset_class="crypto"))
    )

    assert equity["suggested_indicators"] == ["ma", "volume", "rsi", "macd"]
    assert etf["suggested_indicators"] == ["ma", "volume", "rsi"]
    assert crypto["suggested_indicators"] == ["ema", "vwap", "rsi", "volume"]


def test_fast_web_unavailable_is_honest() -> None:
    fake = _FakeToolCall(asset_class="equity", web_ok=False)
    bundle = asyncio.run(gather_fast("Apple", region="US", tool_call=fake))

    assert bundle["ok"] is True  # structured data still pulled
    web = bundle["web"]
    assert web["available"] is False
    assert web["citations"] == []
    assert web["results"] == []
    # The honest fallback note — never an empty/fabricated web section. A genuine
    # no-backend miss (no typed reason) keeps the "no backend configured" copy.
    assert web["note"] == "No web-search backend configured — structured data only"
    assert "detail" in web  # the tool's "how to unlock it" message is surfaced


def test_fast_web_rate_limited_is_transient_not_no_backend() -> None:
    """WS3: a TRANSIENT throttle (typed reason "rate_limited") yields the honest
    "rate-limited, retry" note — NOT the false "no backend configured" claim. The
    backend exists; it was merely throttled this run."""
    fake = _FakeToolCall(asset_class="equity", web_ok=False, web_reason="rate_limited")
    bundle = asyncio.run(gather_fast("Apple", region="US", tool_call=fake))

    web = bundle["web"]
    assert web["available"] is False
    assert web["reason"] == "rate_limited"
    # The transient note, NOT the false global "no backend configured".
    assert web["note"] == "Web search was rate-limited — retry in a moment"
    assert "no backend" not in web["note"].lower()
    assert "no web-search backend" not in web["note"].lower()


def test_fast_resolution_failure_goes_web_only() -> None:
    """R8: an unresolvable query no longer dead-ends — the bundle proceeds
    WEB-ONLY with the honest one-line note, ``symbol == ""``, and ZERO
    structured calls (a free-text query never rides a ``symbol`` arg)."""
    fake = _FakeToolCall(resolve_ok=False)
    bundle = asyncio.run(gather_fast("zzzz nonsense", region="US", tool_call=fake))

    assert bundle["ok"] is True
    assert bundle["symbol"] == ""
    assert bundle["structured"] == {}
    assert bundle["note"] == "No listed instrument matched this query — web evidence only."
    assert bundle["resolved"]["ok"] is False
    # Exactly one resolve + one web round — no structured tool ever fired.
    assert fake.calls == ["resolve_symbol", "web_search"]
    assert bundle["web"]["available"] is True


def test_fast_low_confidence_resolution_goes_web_only() -> None:
    """A fuzzy match below the confidence floor is REJECTED (web-only run),
    never silently bound to the wrong instrument."""

    class _LowConfidence(_FakeToolCall):
        def _dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
            out = super()._dispatch(name, args)
            if name == "resolve_symbol":
                out["resolved"]["confidence"] = 0.2
            return out

    fake = _LowConfidence()
    bundle = asyncio.run(gather_fast("ambiguous name", region="US", tool_call=fake))
    assert bundle["ok"] is True
    assert bundle["symbol"] == ""
    assert fake.calls == ["resolve_symbol", "web_search"]


def test_fast_one_leg_failure_is_non_fatal() -> None:
    class _PartialFail(_FakeToolCall):
        def _dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
            if name == "fundamentals":
                raise RuntimeError("provider exploded")
            return super()._dispatch(name, args)

    fake = _PartialFail(asset_class="equity", web_ok=True)
    bundle = asyncio.run(gather_fast("Apple", region="US", tool_call=fake))

    assert bundle["ok"] is True
    assert bundle["structured"]["fundamentals"]["ok"] is False
    assert "error" in bundle["structured"]["fundamentals"]
    # The other legs still came through.
    assert bundle["structured"]["price"]["ok"] is True
    assert bundle["structured"]["news"]["ok"] is True
