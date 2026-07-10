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
    # A real yfinance fundamentals is never an all-null shell — give it a real
    # field so the fall-through serves data (R13 D3 rejects only empty shells).
    monkeypatch.setattr(
        yfinance_provider,
        "get_fundamentals",
        lambda symbol: _fundamentals("yfinance", pe_ratio=25.0),
    )

    result = asyncio.run(provider_registry.get_fundamentals("AAPL"))
    # Fell through; the result names the provider that actually served it.
    assert result.provider == "yfinance"


def test_fundamentals_serves_openbb_when_it_is_screener_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services import openbb_mcp_provider

    monkeypatch.setattr(openbb_mcp_provider, "is_available", lambda: True)

    async def openbb_ok(symbol: str) -> Fundamentals:
        # Screener-COMPLETE (carries roe) → openbb wins; no fall-through.
        return _fundamentals("openbb-mcp", roe=0.2)

    monkeypatch.setattr(openbb_mcp_provider, "get_fundamentals", openbb_ok)
    result = asyncio.run(provider_registry.get_fundamentals("AAPL"))
    assert result.provider == "openbb-mcp"  # preferred provider served it
    assert result.roe == 0.2


def test_fundamentals_incomplete_openbb_falls_through_to_yfinance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An openbb result with NO screener-grade fields (its real behaviour) is
    incomplete → the registry enriches from yfinance, which populates them."""
    from services import openbb_mcp_provider, yfinance_provider

    monkeypatch.setattr(openbb_mcp_provider, "is_available", lambda: True)

    async def openbb_sparse(symbol: str) -> Fundamentals:
        # Valid (has pe) but missing every screener-grade field — the openbb case.
        return _fundamentals("openbb-mcp", pe_ratio=30.0)

    monkeypatch.setattr(openbb_mcp_provider, "get_fundamentals", openbb_sparse)
    monkeypatch.setattr(
        yfinance_provider,
        "get_fundamentals",
        lambda symbol: _fundamentals("yfinance", roe=0.18, profit_margin=0.25),
    )

    result = asyncio.run(provider_registry.get_fundamentals("AAPL"))
    assert result.provider == "yfinance"  # enriched from the richer path
    assert result.roe == 0.18
    assert result.profit_margin == 0.25


def test_fundamentals_returns_partial_when_every_provider_is_sparse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If NO provider has screener-grade fields, the highest-ranked partial is
    still returned — incompleteness is never a hard failure."""
    from services import openbb_mcp_provider, yfinance_provider

    monkeypatch.setattr(openbb_mcp_provider, "is_available", lambda: True)

    async def openbb_sparse(symbol: str) -> Fundamentals:
        return _fundamentals("openbb-mcp", pe_ratio=30.0)

    monkeypatch.setattr(openbb_mcp_provider, "get_fundamentals", openbb_sparse)
    monkeypatch.setattr(
        yfinance_provider, "get_fundamentals", lambda symbol: _fundamentals("yfinance")
    )

    result = asyncio.run(provider_registry.get_fundamentals("AAPL"))
    # openbb is rank-10 (higher than yfinance); its partial is the one kept.
    assert result.provider == "openbb-mcp"
    assert result.pe_ratio == 30.0


def test_fundamentals_all_null_shell_plus_failing_yfinance_raises_not_a_shell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R13 D3: an all-null openbb shell (every data field None) + a failing
    yfinance must NOT be served as a 200 null payload — the registry raises the
    last provider error (here a not_found) instead of the shell."""
    from services import openbb_mcp_provider, yfinance_provider

    monkeypatch.setattr(openbb_mcp_provider, "is_available", lambda: True)

    async def openbb_null_shell(symbol: str) -> Fundamentals:
        return _fundamentals("openbb-mcp")  # symbol=AAPL, every data field None

    def yfinance_boom(symbol: str) -> Fundamentals:
        raise ProviderError("Yahoo has no company record for 'AAPL.NS'", kind="not_found")

    monkeypatch.setattr(openbb_mcp_provider, "get_fundamentals", openbb_null_shell)
    monkeypatch.setattr(yfinance_provider, "get_fundamentals", yfinance_boom)

    with pytest.raises(ProviderError) as excinfo:
        asyncio.run(provider_registry.get_fundamentals("AAPL"))
    assert excinfo.value.kind == "not_found"


def test_fundamentals_all_null_everywhere_raises_synthetic_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R13 D3: when EVERY provider returns an all-null shell (no error raised), the
    registry still refuses to serve a shell — it raises a synthetic not_found."""
    from services import openbb_mcp_provider, yfinance_provider

    monkeypatch.setattr(openbb_mcp_provider, "is_available", lambda: True)

    async def openbb_null(symbol: str) -> Fundamentals:
        return _fundamentals("openbb-mcp")

    monkeypatch.setattr(openbb_mcp_provider, "get_fundamentals", openbb_null)
    monkeypatch.setattr(
        yfinance_provider, "get_fundamentals", lambda symbol: _fundamentals("yfinance")
    )

    with pytest.raises(ProviderError) as excinfo:
        asyncio.run(provider_registry.get_fundamentals("AAPL"))
    assert excinfo.value.kind == "not_found"


def test_fundamentals_partial_but_real_is_still_served(monkeypatch: pytest.MonkeyPatch) -> None:
    """R13 D3 guard is data-aware, not completeness-aware: a partial result with
    even ONE real field (openbb pe_ratio) is still served, never dropped."""
    from services import openbb_mcp_provider, yfinance_provider

    monkeypatch.setattr(openbb_mcp_provider, "is_available", lambda: True)

    async def openbb_partial(symbol: str) -> Fundamentals:
        return _fundamentals("openbb-mcp", pe_ratio=30.0)  # one real field

    monkeypatch.setattr(openbb_mcp_provider, "get_fundamentals", openbb_partial)
    monkeypatch.setattr(
        yfinance_provider, "get_fundamentals", lambda symbol: _fundamentals("yfinance")
    )

    result = asyncio.run(provider_registry.get_fundamentals("AAPL"))
    assert result.provider == "openbb-mcp"
    assert result.pe_ratio == 30.0


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


def _quote(provider: str, symbol: str = "AAPL"):  # noqa: ANN202
    from datetime import UTC, datetime

    from models.market import Quote

    # The correctness gate (FR-063) rejects a quote whose symbol does not match
    # the request, or one dated far behind the session calendar — so a realistic
    # fake echoes the requested symbol and a current timestamp.
    return Quote(
        symbol=symbol,
        price=1.0,
        change=0.0,
        change_percent=0.0,
        timestamp=datetime.now(tz=UTC),
        provider=provider,
    )


def _fundamentals(provider: str, **fields: float) -> Fundamentals:
    return Fundamentals(symbol="AAPL", provider=provider, **fields)
