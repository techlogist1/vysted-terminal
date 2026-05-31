"""FR-035 / FR-053 — the provider-declaration-driven resolver.

The registry no longer hardcodes ``if asset_class``; it resolves by a STANDARD
MODEL KEY against a declaration table, walking providers in PREFERENCE ORDER and
falling through on :class:`ProviderError`. These tests assert: a request resolves
to the preferred provider, falls through to the next on a ProviderError, the
result names the SERVING provider (provenance not overwritten), and
``active_providers`` is derived from the same table.
"""

from __future__ import annotations

import asyncio

import pytest

from models.fundamentals import Fundamentals
from services import provider_registry
from services.errors import ProviderError

# ---------------------------------------------------------------------------
# Resolution by model-key + preference order
# ---------------------------------------------------------------------------


def test_quote_resolves_to_yfinance_for_equity(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import yfinance_provider

    calls: list[str] = []

    def fake_quote(symbol: str):  # noqa: ANN202
        calls.append(symbol)
        return _quote("yfinance")

    monkeypatch.setattr(yfinance_provider, "get_quote", fake_quote)
    quote = provider_registry.get_quote("AAPL", "equity")
    assert quote.provider == "yfinance"  # serving provider lands in provenance
    assert calls == ["AAPL"]


def test_quote_resolves_to_ccxt_for_crypto(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import ccxt_provider

    def fake_ticker(exchange: str, symbol: str):  # noqa: ANN202
        return _quote("ccxt")

    monkeypatch.setattr(ccxt_provider, "get_ticker", fake_ticker)
    quote = provider_registry.get_quote("BTC/USDT", "crypto")
    assert quote.provider == "ccxt"


def test_fundamentals_prefers_openbb_then_falls_through_to_yfinance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services import openbb_mcp_provider, yfinance_provider

    # openbb-mcp is the rank-10 preferred provider but errors → fall through.
    monkeypatch.setattr(openbb_mcp_provider, "is_available", lambda: True)

    async def openbb_boom(symbol: str) -> Fundamentals:
        raise ProviderError("openbb-mcp down")

    monkeypatch.setattr(openbb_mcp_provider, "get_fundamentals", openbb_boom)
    monkeypatch.setattr(
        yfinance_provider, "get_fundamentals", lambda symbol: _fundamentals("yfinance")
    )

    result = asyncio.run(provider_registry.get_fundamentals("AAPL"))
    # Fell through; the result names the provider that actually served it.
    assert result.provider == "yfinance"


def test_fundamentals_serves_openbb_when_it_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import openbb_mcp_provider

    monkeypatch.setattr(openbb_mcp_provider, "is_available", lambda: True)

    async def openbb_ok(symbol: str) -> Fundamentals:
        return _fundamentals("openbb-mcp")

    monkeypatch.setattr(openbb_mcp_provider, "get_fundamentals", openbb_ok)
    result = asyncio.run(provider_registry.get_fundamentals("AAPL"))
    assert result.provider == "openbb-mcp"  # preferred provider served it


def test_macro_with_no_provider_raises_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import openbb_mcp_provider

    # openbb-mcp is the ONLY macro provider; absent → clean ProviderError (→ 501/502).
    monkeypatch.setattr(openbb_mcp_provider, "is_available", lambda: False)
    with pytest.raises(ProviderError, match="no provider available"):
        asyncio.run(provider_registry.get_macro_series("DGS10"))


# ---------------------------------------------------------------------------
# active_providers — derived from the declaration table (FR-053)
# ---------------------------------------------------------------------------


def test_active_providers_is_derived_and_keyed_by_model_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services import openbb_mcp_provider

    monkeypatch.setattr(openbb_mcp_provider, "is_available", lambda: True)
    report = provider_registry.active_providers()

    # Keyed by STANDARD MODEL KEY, not by asset class.
    assert "quote" in report and "ohlcv" in report
    assert "fundamentals" in report and "macro_series" in report
    # ccxt (rank 10) is preferred for quote/ohlcv.
    assert report["quote"].startswith("ccxt")
    # openbb-mcp (rank 10) preferred for fundamentals with yfinance as fallback.
    assert report["fundamentals"].startswith("openbb-mcp")
    assert "yfinance" in report["fundamentals"]
    assert report["openbb-mcp"] == "available"


def test_active_providers_marks_macro_unavailable_without_openbb(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services import openbb_mcp_provider

    monkeypatch.setattr(openbb_mcp_provider, "is_available", lambda: False)
    report = provider_registry.active_providers()
    # macro_series is openbb-only; absent → unavailable.
    assert report["macro_series"] == "unavailable"
    # fundamentals still served by yfinance (no openbb prefix when openbb absent).
    assert report["fundamentals"] == "yfinance"


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


def _quote(provider: str):  # noqa: ANN202
    from datetime import UTC, datetime

    from models.market import Quote

    return Quote(
        symbol="X",
        price=1.0,
        change=0.0,
        change_percent=0.0,
        timestamp=datetime(2026, 5, 31, tzinfo=UTC),
        provider=provider,
    )


def _fundamentals(provider: str) -> Fundamentals:
    return Fundamentals(symbol="AAPL", provider=provider)
