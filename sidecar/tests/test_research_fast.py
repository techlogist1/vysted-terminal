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

import pytest

from services import dividend_actions, ownership_check
from services.dividend_actions import DeclaredDividend
from services.ownership_check import ExchangeOwnership
from services.research.fast import gather_fast, snapshot_structured


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
    # R10 (E8): the derived metric-semantics leg rides every bundle.
    assert set(structured) == {"price", "fundamentals", "news", "filings", "derived"}
    for slot in structured.values():
        assert slot["ok"] is True

    # Provenance carried per leg (FR-041 badge).
    assert structured["price"]["provider"] == "yfinance"
    assert structured["fundamentals"]["provider"] == "openbb"
    assert structured["filings"]["provider"] == "sec-edgar"
    assert structured["derived"]["provider"] == "derived"
    # The execution-loop hint (R10, D38) names the lane that ran.
    assert bundle["execution_loop"] == "fast"

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
    # Resolve attempts (full query + the R10 prefix rungs) and ONE web round —
    # no structured tool ever fired.
    assert set(fake.calls) == {"resolve_symbol", "web_search"}
    assert fake.calls[-1] == "web_search"
    assert fake.calls.count("web_search") == 1
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
    # Resolve attempts only (full query + prefix rungs) + ONE web round.
    assert set(fake.calls) == {"resolve_symbol", "web_search"}
    assert fake.calls.count("web_search") == 1


def test_fast_disambiguation_returns_chooser_with_zero_web_spend() -> None:
    """R10 (D37): an ambiguous resolution returns the explicit "which did you
    mean?" payload — no markdown, no structured pulls, no web round."""

    class _Ambiguous(_FakeToolCall):
        def _dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
            if name == "resolve_symbol":
                return {
                    "ok": True,
                    "query": args.get("query"),
                    "status": "disambiguate",
                    "reason": "marquee family name",
                    "resolved": None,
                    "needs_disambiguation": True,
                    "candidates": [
                        {
                            "symbol": "TCS",
                            "name": "Tata Consultancy Services Limited",
                            "exchange": "NSE",
                            "confidence": 0.6,
                            "yahoo_symbol": "TCS.NS",
                        }
                    ],
                    "message": "which did you mean?",
                }
            return super()._dispatch(name, args)

    fake = _Ambiguous()
    bundle = asyncio.run(gather_fast("tata results", region="IN", tool_call=fake))
    assert bundle["ok"] is True
    assert bundle["needs_disambiguation"] is True
    assert bundle["query"] == "tata results"
    assert bundle["candidates"][0]["symbol"] == "TCS"
    assert bundle["candidates"][0]["yahoo_symbol"] == "TCS.NS"
    assert bundle["message"]
    assert bundle["execution_loop"] == "fast"
    assert "markdown" not in bundle and "structured" not in bundle
    # ZERO web/structured spend — only the resolver was consulted.
    assert set(fake.calls) == {"resolve_symbol"}


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
    # R13 JARVIS 2a: the failed leg names its CAUSE (provider_error) so the model
    # narrates OUR feed's gap, not a silent absence it can call a world-absence.
    assert bundle["structured"]["fundamentals"]["reason"] == "provider_error"
    # The other legs still came through.
    assert bundle["structured"]["price"]["ok"] is True
    assert bundle["structured"]["news"]["ok"] is True


def test_structured_value_classifies_failed_leg_reason() -> None:
    """R13 JARVIS 2a: the leg wrapper stamps a closed-vocabulary reason — an
    explicit token is honoured, else inferred from the error text; an ok leg
    carries no reason."""
    from services.research.fast import _structured_value

    provider_err = _structured_value(
        {"ok": False, "error": "unexpected error: boom"}, "fundamentals"
    )
    assert provider_err["ok"] is False
    assert provider_err["reason"] == "provider_error"

    explicit = _structured_value(
        {"ok": False, "reason": "rate_limited", "error": "429"}, "fundamentals"
    )
    assert explicit["reason"] == "rate_limited"

    not_found = _structured_value({"ok": False, "error": "SYM not found"}, "fundamentals")
    assert not_found["reason"] == "not_found"

    ok_leg = _structured_value(
        {"ok": True, "fundamentals": {"symbol": "X"}, "provider": "yfinance"}, "fundamentals"
    )
    assert "reason" not in ok_leg


# --- R13 entity-anchored NORMAL (fast-path) web query -----------------------


class _QueryCapturingToolCall(_FakeToolCall):
    """Records the web_search query so the anchored NORMAL query can be pinned."""

    def __init__(self, *, symbol: str, name: str) -> None:
        super().__init__()
        self._symbol = symbol
        self._name = name
        self.web_query: str | None = None

    def _dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "resolve_symbol":
            return {
                "ok": True,
                "query": args.get("query"),
                "region": "IN",
                "resolved": {
                    "symbol": self._symbol,
                    "name": self._name,
                    "exchange": "BSE",
                    "region": "IN",
                    "asset_class": "equity",
                    "yahoo_symbol": f"{self._symbol}.BO",
                    "confidence": 1.0,
                    "isin": "INE953E01022",
                    "bse_code": "519421",
                    "industry": None,
                },
                "needs_disambiguation": False,
                "candidates": [],
            }
        if name == "web_search":
            self.web_query = args.get("query")
            return {"ok": True, "citations": [], "results": []}
        return super()._dispatch(name, args)


def test_fast_normal_query_quotes_the_display_name() -> None:
    """NORMAL fast path anchors on the QUOTED display name + bare symbol so a
    famous foreign namesake can't shadow a ≤3-char ticker (KSE ← Karachi)."""
    tool = _QueryCapturingToolCall(symbol="KSE", name="KSE Ltd")
    out = asyncio.run(gather_fast("KSE outlook", region="IN", tool_call=tool))
    assert out["symbol"] == "KSE"
    assert tool.web_query == '"KSE Ltd" KSE KSE outlook news outlook'


# --- R13 snapshot wiring: ownership_check + dividend_actions ----------------
#
# Mirrors the D56/D66 attach-next-to-provider pattern (see test_growth_check.py's
# "snapshot wiring" section): ``snapshot_structured`` only calls ``price_data`` +
# ``fundamentals``, so the fake tool only needs to answer those two.


def _fund_tool(fund: dict[str, Any]):
    async def tool(name: str, args: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG001
        if name == "price_data":
            return {"ok": True, "provider": "yfinance", "quote": {"symbol": "X", "price": 80.0}}
        if name == "fundamentals":
            return {"ok": True, "fundamentals": dict(fund)}
        raise AssertionError(f"unexpected tool {name}")

    return tool


def test_snapshot_attaches_ownership_and_declared_dividend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """(a) A fake IN listing with monkeypatched ownership_check/dividend_actions
    returning canned objects — fund_data carries ``ownership_exchange`` and
    ``dividend_declared`` under their documented wire shapes."""
    canned_ownership = ExchangeOwnership(
        promoter_percent=55.2,
        institutions_percent=0.06,
        public_percent=44.74,
        as_of_quarter="2026-03-31",
        source="BSE",
    )
    canned_declared = DeclaredDividend(
        amount=3.95, record_date="2026-07-31", subject="Dividend - Rs 3.95 Per Share"
    )

    async def fake_ownership(symbol: str) -> ExchangeOwnership:
        assert symbol == "GEE.BO"  # the RESOLVED listing, not the query
        return canned_ownership

    async def fake_declared(symbol: str) -> DeclaredDividend:
        assert symbol == "GEE.BO"
        return canned_declared

    monkeypatch.setattr(ownership_check, "get_exchange_ownership", fake_ownership)
    monkeypatch.setattr(dividend_actions, "get_declared_unpaid_dividend", fake_declared)

    snap = asyncio.run(
        snapshot_structured(
            _fund_tool(
                {
                    "symbol": "GEE.BO",
                    "provider": "yfinance",
                    "held_percent_insiders": 0.08455,
                }
            ),
            "GEE",
        )
    )
    fund = snap["fundamentals"]["data"]
    assert fund[ownership_check.OWNERSHIP_KEY] == canned_ownership.as_wire()
    assert fund[dividend_actions.DECLARED_KEY] == canned_declared.as_wire()


def test_snapshot_attaches_nothing_when_both_return_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """(b) Both cross-checks monkeypatched to return ``None`` — the keys are
    absent, and the snapshot never raises."""

    async def none_ownership(_symbol: str) -> None:
        return None

    async def none_declared(_symbol: str) -> None:
        return None

    monkeypatch.setattr(ownership_check, "get_exchange_ownership", none_ownership)
    monkeypatch.setattr(dividend_actions, "get_declared_unpaid_dividend", none_declared)

    snap = asyncio.run(
        snapshot_structured(
            _fund_tool(
                {
                    "symbol": "GEE.BO",
                    "provider": "yfinance",
                    "held_percent_insiders": 0.08455,
                }
            ),
            "GEE",
        )
    )
    fund = snap["fundamentals"]["data"]
    assert ownership_check.OWNERSHIP_KEY not in fund
    assert dividend_actions.DECLARED_KEY not in fund


def test_snapshot_skips_ownership_pull_when_not_applicable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """(c) A non-applicable target (``should_cross_check`` False — no ownership
    scalar in the fundamentals payload) — ``get_exchange_ownership`` is never
    called."""

    async def explode(_symbol: str) -> ExchangeOwnership:
        raise AssertionError("no ownership scalar to reconcile — must not pull the filing")

    async def none_declared(_symbol: str) -> None:
        return None

    monkeypatch.setattr(ownership_check, "get_exchange_ownership", explode)
    monkeypatch.setattr(dividend_actions, "get_declared_unpaid_dividend", none_declared)

    snap = asyncio.run(
        snapshot_structured(
            _fund_tool({"symbol": "GEE.BO", "provider": "yfinance"}),
            "GEE",
        )
    )
    fund = snap["fundamentals"]["data"]
    assert ownership_check.OWNERSHIP_KEY not in fund
