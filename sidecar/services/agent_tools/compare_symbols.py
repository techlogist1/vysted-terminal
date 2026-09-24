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
from datetime import date, timedelta
from typing import Any

from services.agent_tools import register_tool

_VALID_TIMEFRAMES = ("1d", "1h", "1wk", "1mo")
_VALID_ASSET_CLASSES = ("equity", "crypto")
#: Window over which trailing relative performance is measured.
_RETURN_WINDOW = "6mo"
#: How far after the earliest window start a symbol's first bar may land and
#: still be ranked against it (about five trading days).
_WINDOW_START_SLACK = timedelta(days=7)


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


async def _quote_or_error(symbol: str, asset_class: str) -> tuple[Any, dict[str, Any] | None]:
    """One quote fetch: ``(quote, None)``, or ``(None, error entry)`` — never raised."""
    from services import provider_registry
    from services.errors import ProviderError

    try:
        return await asyncio.to_thread(provider_registry.get_quote, symbol, asset_class), None
    except ProviderError as exc:
        return None, {"symbol": symbol, "error": str(exc), "note": f"no quote for {symbol}: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return None, {
            "symbol": symbol,
            "error": str(exc),
            "note": f"unexpected error fetching {symbol}: {exc}",
        }


async def _resolve_after_miss(symbol: str) -> tuple[str | None, dict[str, Any] | None, str | None]:
    """An equity input that got no quote goes through the ONE resolution policy
    (``fundamentals._canonicalize``, the same wrapper the fundamentals tool uses).

    Returns ``(canonical, error_entry, note)``: a confident bind at a different
    listing (a company name, a typo'd ticker) → the canonical symbol to compare
    instead; a disambiguation → an error naming the candidates; an input that is
    no known listing at all → an "unresolved" error, so the model reads a wrong
    ticker as a wrong ticker, not as "no quote available". A known listing with
    no quote keeps the provider error (``None, None, None``).
    """
    from services import symbol_resolver
    from services.agent_tools.fundamentals import _canonicalize

    verdict = await _canonicalize(symbol)
    if verdict.canonical_symbol is not None:
        return verdict.canonical_symbol, None, verdict.note
    if verdict.honest_not_found is not None:
        error = verdict.honest_not_found["error"]
        return (
            None,
            {
                "symbol": symbol,
                "error": f"ambiguous name: {error}",
                "note": f"ambiguous name: {error}",
                "candidates": verdict.candidates,
            },
            None,
        )
    known = (
        symbol_resolver.is_us_symbol(symbol)
        or symbol_resolver.is_nse_symbol(symbol)
        or symbol_resolver.is_bse_symbol(symbol)
    )
    if known:
        return None, None, None
    error = (
        f"unresolved name: {symbol!r} is not a known ticker and matched no listing — "
        "retry with the company name or the exact exchange ticker"
    )
    return None, {"symbol": symbol, "error": error, "note": error}, None


async def _compare_one(symbol: str, timeframe: str, asset_class: str) -> dict[str, Any]:
    """Fetch quote + fundamentals + return window for a single symbol.

    Always returns a dict; a provider failure is reported as an ``error``
    field (with a human note) rather than raised, so the caller's
    ``asyncio.gather`` never aborts the batch on one bad ticker. An equity
    input with no quote is run through the resolution policy
    (:func:`_resolve_after_miss`) before the failure stands; a crypto pair
    passes through unchanged."""
    from services import provider_registry
    from services.errors import ProviderError

    requested = symbol
    resolved_note: str | None = None
    quote, failure = await _quote_or_error(symbol, asset_class)
    if failure is not None and asset_class != "crypto":
        canonical, unresolved, resolved_note = await _resolve_after_miss(symbol)
        if unresolved is not None:
            return unresolved
        if canonical is not None:
            symbol = canonical
            quote, failure = await _quote_or_error(symbol, asset_class)
    if failure is not None:
        return failure

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
    bars: list[Any] = []
    try:
        series = await asyncio.to_thread(
            provider_registry.get_history,
            symbol,
            timeframe,
            _RETURN_WINDOW,
            asset_class,
        )
        return_pct = _return_pct_window(series)
        bars = list(getattr(series, "bars", []) or [])
    except (ProviderError, Exception):  # noqa: BLE001
        return_pct = None

    return {
        "symbol": quote.symbol,
        # Set when the input was resolved to a different listing — never silent.
        **({"requested": requested, "note": resolved_note} if resolved_note else {}),
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
        # The window the return was measured over, so a short history (a new
        # listing, a provider gap) is visible rather than read as 6 months.
        "bars": len(bars),
        "window_start": bars[0].timestamp.date().isoformat() if bars else None,
        "window_end": bars[-1].timestamp.date().isoformat() if bars else None,
    }


def _rank(resolved: list[dict[str, Any]]) -> dict[str, Any]:
    """Best/worst by trailing return, across comparable windows only.

    A symbol whose window starts well after the earliest one (a recent listing,
    a history gap) measured a shorter period, so it is left out of the ranking
    and named in ``note``; with fewer than two comparable windows there is no
    ranking at all.
    """
    ranked = [r for r in resolved if r.get("return_pct_window") is not None]
    if not ranked:
        return {"best": None, "worst": None}
    common_start = min(date.fromisoformat(r["window_start"]) for r in ranked)
    cutoff = (common_start + _WINDOW_START_SLACK).isoformat()
    comparable = [r for r in ranked if r["window_start"] <= cutoff]
    short = [r for r in ranked if r["window_start"] > cutoff]
    relative: dict[str, Any] = {"best": None, "worst": None}
    if len(comparable) >= 2:
        relative["best"] = max(comparable, key=lambda r: r["return_pct_window"])["symbol"]
        relative["worst"] = min(comparable, key=lambda r: r["return_pct_window"])["symbol"]
    if short:
        relative["note"] = "windows not comparable: " + "; ".join(
            f"{r['symbol']} has {r['bars']} bars since {r['window_start']}" for r in short
        )
    return relative


async def _compare_symbols(args: dict[str, Any]) -> dict[str, Any]:
    """Compare 2–4 symbols on quote, fundamentals, and trailing return.

    Args:
        symbols: A 2–4 element list of ticker strings. Required.
        timeframe: One of ``1d|1h|1wk|1mo`` (default ``1d``) — the bar size of
            the 6-month return window.
        asset_class: ``equity`` (default) or ``crypto``.

    Returns ``{"ok": True, "timeframe", "symbols": [...], "relative":
    {"best", "worst"[, "note"]}}`` where ``relative`` ranks the resolved symbols
    by ``return_pct_window`` across comparable windows only (see :func:`_rank`;
    ``None`` when fewer than two are comparable). Each symbol carries ``bars``,
    ``window_start`` and ``window_end``.
    Symbols that fail entirely are still listed with an ``error`` field. When
    fewer than two symbols resolve, returns ``{"ok": False, "symbols": [...],
    "message": ...}`` with each failed input's own reason in the message.
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
        # Each failed input keeps its own reason (unresolved name, ambiguous name
        # with its candidates, or no quote) so the model never reads a wrong
        # ticker as a data gap (R15-AGENT-045).
        reasons = "; ".join(f"{r['symbol']}: {r['error']}" for r in results if "error" in r)
        return {
            "ok": False,
            "symbols": results,
            "message": (
                "fewer than two symbols resolved — "
                f"{len(resolved)} of {len(symbols)} returned a quote. {reasons}"
            ),
        }

    return {
        "ok": True,
        "timeframe": timeframe,
        "symbols": results,
        "relative": _rank(resolved),
    }


def register() -> None:
    """Register the ``compare_symbols`` tool in the package registry."""
    register_tool("compare_symbols", _compare_symbols)


__all__ = ["_compare_symbols", "register"]
