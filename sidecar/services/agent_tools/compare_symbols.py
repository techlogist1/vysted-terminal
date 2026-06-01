"""v0.6.0 agent tool — ``compare_symbols``.

Fetches a quote + fundamentals + a 6-month relative-performance window for
2–4 symbols concurrently and ranks them by trailing return, so an agent can
answer "how do AAPL, MSFT and NVDA compare?" in one call instead of fanning
out to ``price_data``/``fundamentals`` per ticker. Registered via
:func:`register` from :func:`services.agent_tools.registry_v0_6_0`.

Failure isolation: each symbol is fetched in its own task wrapped so one
provider failure surfaces as a per-symbol ``error`` field rather than tanking
the whole batch. The tool returns ``ok=False`` only when fewer than two
symbols resolve (a comparison of one is meaningless) or the input is malformed.
"""

from __future__ import annotations

import asyncio
from typing import Any

from services.agent_tools import register_tool

_VALID_TIMEFRAMES = ("1d", "1h", "1wk", "1mo")
_VALID_ASSET_CLASSES = ("equity", "crypto")
#: Window over which trailing relative performance is measured.
_RETURN_WINDOW = "6mo"


def _return_pct_window(series: Any) -> float | None:
    """Trailing return across the fetched window as ``(last/first - 1) * 100``.

    Returns ``None`` when the series is empty, single-bar, or anchored on a
    non-positive first close (which would make the ratio meaningless)."""
    bars = list(getattr(series, "bars", []) or [])
    if len(bars) < 2:
        return None
    first_close = bars[0].close
    last_close = bars[-1].close
    if first_close is None or last_close is None or first_close <= 0:
        return None
    return (last_close / first_close - 1.0) * 100.0


async def _compare_one(symbol: str, timeframe: str, asset_class: str) -> dict[str, Any]:
    """Fetch quote + fundamentals + return window for a single symbol.

    Always returns a dict; a provider failure is reported as an ``error``
    field (with a human note) rather than raised, so the caller's
    ``asyncio.gather`` never aborts the batch on one bad ticker."""
    from services import provider_registry
    from services.errors import ProviderError

    try:
        quote = await asyncio.to_thread(provider_registry.get_quote, symbol, asset_class)
    except ProviderError as exc:
        return {"symbol": symbol, "error": str(exc), "note": f"no quote for {symbol}: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {
            "symbol": symbol,
            "error": str(exc),
            "note": f"unexpected error fetching {symbol}: {exc}",
        }

    # Fundamentals are routinely sparse (and absent for crypto) — a failure here
    # degrades to None rather than failing the symbol.
    fundamentals: Any = None
    if asset_class != "crypto":
        try:
            fundamentals = await provider_registry.get_fundamentals(symbol)
        except (ProviderError, Exception):  # noqa: BLE001
            fundamentals = None

    # History backs the relative-performance ranking — a failure degrades the
    # window to None but keeps the (more important) quote in the comparison.
    return_pct: float | None = None
    try:
        series = await asyncio.to_thread(
            provider_registry.get_history,
            symbol,
            timeframe,
            _RETURN_WINDOW,
            asset_class,
        )
        return_pct = _return_pct_window(series)
    except (ProviderError, Exception):  # noqa: BLE001
        return_pct = None

    return {
        "symbol": quote.symbol,
        "provider": quote.provider,
        "quote": {
            "price": quote.price,
            "change_percent": quote.change_percent,
            "currency": quote.currency,
        },
        "fundamentals": (
            {
                "market_cap": fundamentals.market_cap,
                "pe_ratio": fundamentals.pe_ratio,
                "forward_pe": fundamentals.forward_pe,
                "peg_ratio": fundamentals.peg_ratio,
                "price_to_book": fundamentals.price_to_book,
                "dividend_yield": fundamentals.dividend_yield,
                "eps": fundamentals.eps,
                "beta": fundamentals.beta,
            }
            if fundamentals is not None
            else None
        ),
        "return_pct_window": return_pct,
    }


async def _compare_symbols(args: dict[str, Any]) -> dict[str, Any]:
    """Compare 2–4 symbols on quote, fundamentals, and trailing return.

    Args:
        symbols: A 2–4 element list of ticker strings. Required.
        timeframe: One of ``1d|1h|1wk|1mo`` (default ``1d``) — the bar size of
            the 6-month return window.
        asset_class: ``equity`` (default) or ``crypto``.

    Returns ``{"ok": True, "timeframe", "symbols": [...], "relative":
    {"best", "worst"}}`` where ``relative`` ranks the resolved symbols by
    ``return_pct_window`` (``None`` when no symbol has a measurable window).
    Symbols that fail entirely are still listed with an ``error`` field. When
    fewer than two symbols resolve, returns ``{"ok": False, "message": ...}``.
    """
    symbols = args.get("symbols")
    if not isinstance(symbols, list) or not all(isinstance(s, str) and s for s in symbols):
        return {"ok": False, "error": "symbols must be a list of non-empty strings"}
    if not (2 <= len(symbols) <= 4):
        return {"ok": False, "error": "symbols must contain between 2 and 4 tickers"}

    timeframe = str(args.get("timeframe") or "1d")
    if timeframe not in _VALID_TIMEFRAMES:
        return {"ok": False, "error": f"timeframe must be one of {list(_VALID_TIMEFRAMES)}"}

    asset_class = str(args.get("asset_class") or "equity")
    if asset_class not in _VALID_ASSET_CLASSES:
        return {"ok": False, "error": f"asset_class must be one of {list(_VALID_ASSET_CLASSES)}"}

    results = await asyncio.gather(
        *(_compare_one(symbol, timeframe, asset_class) for symbol in symbols)
    )

    resolved = [r for r in results if "error" not in r]
    if len(resolved) < 2:
        return {
            "ok": False,
            "message": (
                "fewer than two symbols resolved — "
                f"{len(resolved)} of {len(symbols)} returned a quote"
            ),
        }

    ranked = [r for r in resolved if r.get("return_pct_window") is not None]
    if ranked:
        best = max(ranked, key=lambda r: r["return_pct_window"])["symbol"]
        worst = min(ranked, key=lambda r: r["return_pct_window"])["symbol"]
        relative = {"best": best, "worst": worst}
    else:
        relative = {"best": None, "worst": None}

    return {
        "ok": True,
        "timeframe": timeframe,
        "symbols": results,
        "relative": relative,
    }


def register() -> None:
    """Register the ``compare_symbols`` tool in the package registry."""
    register_tool("compare_symbols", _compare_symbols)


__all__ = ["_compare_symbols", "register"]
