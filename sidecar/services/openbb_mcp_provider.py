"""openbb-mcp provider — Phase 3 replacement for the Phase-2 OpenBB plugin.

The Phase-2 OpenBB integration shipped a bespoke FastAPI subprocess inside
``sidecar/openbb_subprocess/`` and launched it from Python via
``subprocess.Popen``. On Windows the launch deadlocked indefinitely (anyio
+ PyInstaller ``_MEIPASS`` + Windows handle-inheritance interaction; see
CLAUDE.md Gotchas and the v0.3.0 BLOCKERS doc).

Phase 3's architectural fix replaces both halves:

- the bespoke subprocess → the stock ``openbb-mcp-server`` package (1.4.0)
  packaged as its own PyInstaller ``--onefile`` binary in
  ``sidecar/openbb_mcp_subprocess/``;
- ``subprocess.Popen`` → Tauri Rust ``Command::new`` (see
  ``src-tauri/src/openbb_mcp.rs``). Different Windows handle semantics
  side-step the deadlock.

This module is the Python side of that fix. It learns the openbb-mcp port
from an env var the Tauri core writes during sidecar spawn
(``VYSTED_OPENBB_MCP_PORT``), instantiates an :class:`McpClient` over
Streamable-HTTP, and exposes the same public surface (``get_fundamentals``,
``get_income_statement``, ...) the retired ``openbb_provider`` exposed —
so :mod:`services.provider_registry` is a one-line swap.

OpenBB tool surface (1.4.0)
---------------------------

The openbb-mcp-server exposes a single discovery tool plus the per-route
"category_subcategory_action" tools generated from the OpenBB Platform
router tree. The tool names line up with OpenBB Python paths joined with
underscores:

    /equity/price/quote          → equity_price_quote
    /equity/price/historical     → equity_price_historical
    /equity/profile              → equity_profile
    /equity/fundamental/metrics  → equity_fundamental_metrics
    /equity/fundamental/income   → equity_fundamental_income
    /equity/fundamental/balance  → equity_fundamental_balance
    /equity/fundamental/cash     → equity_fundamental_cash
    /equity/estimates/price_target → equity_estimates_price_target
    /economy/fred_series         → economy_fred_series

The returned shape from each tool is JSON-encoded as a single text content
block; the provider parses that text block and maps it into the Vysted
Pydantic models, matching the field-mapping the retired ``openbb_provider``
did.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from models.fundamentals import (
    AnalystRating,
    BalanceSheet,
    CashFlowStatement,
    Fundamentals,
    IncomeStatement,
    StatementLine,
)
from models.market import (
    MacroObservation,
    MacroSeries,
    OHLCVBar,
    OHLCVSeries,
    Quote,
)
from services import mcp_client
from services.errors import ProviderError

PROVIDER = "openbb-mcp"

_log = logging.getLogger(__name__)

# Vysted timeframe → OpenBB interval string (mirrors openbb_provider).
_TIMEFRAME_MAP: dict[str, str] = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "1d": "1d",
    "1wk": "1W",
    "1mo": "1M",
}

# Env vars the Tauri core sets before spawning the main sidecar so the
# Python side learns where the openbb-mcp subprocess is listening.
_PORT_ENV = "VYSTED_OPENBB_MCP_PORT"
_HOST_ENV = "VYSTED_OPENBB_MCP_HOST"

# Default upstream provider per data class. The user-visible provider field
# on returned models is always "openbb-mcp"; this is an implementation detail.
_DEFAULT_PROVIDERS: dict[str, str] = {
    "quote": "yfinance",
    "history": "yfinance",
    "fundamentals": "yfinance",
    "income": "yfinance",
    "balance": "yfinance",
    "cashflow": "yfinance",
    "ratings": "yfinance",
    "macro": "fred",
}

# Cached availability flag. ``None`` = not yet probed.
_AVAILABLE: bool | None = None

# In-memory state mirroring the retired openbb_provider for test parity.
_last_tool_call_ok: bool | None = None
_last_error: str | None = None


# ---------------------------------------------------------------------------
# Port + availability discovery
# ---------------------------------------------------------------------------


def _resolve_endpoint() -> str | None:
    """Return the Streamable-HTTP endpoint for the openbb-mcp child, or ``None``.

    ``None`` means the Tauri core did not set the env var, which the
    registry treats as "openbb-mcp not bundled" and routes to yfinance.
    openbb-mcp-server 1.4.0 serves the transport at ``/mcp`` (no trailing
    slash — a trailing-slash GET gets a 307 to the canonical path); the
    MCP client follows redirects but pointing directly at the canonical
    path skips a needless hop.
    """
    port = os.environ.get(_PORT_ENV)
    if not port:
        return None
    host = os.environ.get(_HOST_ENV, "127.0.0.1")
    return f"http://{host}:{port}/mcp"


def is_available() -> bool:
    """Return whether the openbb-mcp subprocess is reachable in this build."""
    global _AVAILABLE
    if _AVAILABLE is None:
        _AVAILABLE = _resolve_endpoint() is not None
    return bool(_AVAILABLE)


async def status() -> dict[str, Any]:
    """Return a status payload for ``GET /openbb-mcp/status``.

    Reports the subprocess port, whether the MCP handshake has succeeded
    at least once, and the last tool-call outcome — what the plugin manager
    UI needs to colour the openbb-mcp plugin chip.
    """
    endpoint = _resolve_endpoint()
    available = endpoint is not None
    return {
        "available": available,
        "provider": PROVIDER,
        "endpoint": endpoint,
        "lastToolCallOk": _last_tool_call_ok,
        "lastError": _last_error,
    }


# ---------------------------------------------------------------------------
# Client + tool dispatch
# ---------------------------------------------------------------------------


async def _get_client() -> mcp_client.McpClient:
    """Return the cached :class:`McpClient` for the openbb-mcp subprocess."""
    endpoint = _resolve_endpoint()
    if endpoint is None:
        raise ProviderError(
            "openbb-mcp subprocess is not running — VYSTED_OPENBB_MCP_PORT not set."
        )
    return await mcp_client.get_client("openbb-mcp", transport="http", endpoint=endpoint)


def _decode_tool_result(result: dict[str, Any], tool_name: str) -> Any:
    """Pull the JSON body out of an MCP tool result.

    Tools return a list of content blocks; openbb-mcp emits one ``text``
    block whose body is JSON for a standard OBBject response. Parse it
    and return the decoded structure.
    """
    if result.get("isError"):
        raise ProviderError(
            f"openbb-mcp tool {tool_name!r} reported error: {result.get('content')!r}"
        )
    blocks = result.get("content") or []
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text", "")
            try:
                return json.loads(text)
            except (TypeError, ValueError) as exc:
                raise ProviderError(
                    f"openbb-mcp tool {tool_name!r} returned non-JSON text: {exc}"
                ) from exc
    raise ProviderError(f"openbb-mcp tool {tool_name!r} returned no text content")


def _result_rows(decoded: Any) -> list[dict[str, Any]]:
    """Return the OBBject ``results`` list as a list of dicts.

    openbb-mcp wraps its output as ``{"results": [...], "extra": {...}}``;
    older versions may also return the bare list. Handle both.
    """
    if isinstance(decoded, dict):
        results = decoded.get("results")
        if isinstance(results, list):
            return [_to_dict(row) for row in results]
        if results is None:
            return []
        return [_to_dict(results)]
    if isinstance(decoded, list):
        return [_to_dict(row) for row in decoded]
    return []


def _result_extra(decoded: Any) -> dict[str, Any]:
    """Return the OBBject ``extra`` block, or ``{}`` if not present."""
    if isinstance(decoded, dict):
        extra = decoded.get("extra")
        if isinstance(extra, dict):
            return extra
    return {}


def _to_dict(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return dict(item)
    if hasattr(item, "model_dump"):
        return dict(item.model_dump())
    return {}


async def _call_tool(name: str, arguments: dict[str, Any]) -> Any:
    """Invoke an openbb-mcp tool and return the decoded body."""
    global _last_tool_call_ok, _last_error
    client = await _get_client()
    try:
        raw = await client.call_tool(name, arguments)
    except Exception as exc:
        _last_tool_call_ok = False
        _last_error = f"{type(exc).__name__}: {exc}"
        raise ProviderError(f"openbb-mcp call {name!r} failed: {exc}") from exc
    decoded = _decode_tool_result(raw, name)
    _last_tool_call_ok = True
    _last_error = None
    return decoded


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_symbol(symbol: str) -> str:
    """Mirror yfinance's dot-ticker fix at the openbb-mcp seam."""
    return symbol.replace(".", "-").upper()


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _ensure_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if hasattr(value, "isoformat"):
        return datetime.fromisoformat(value.isoformat()).replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.now(tz=UTC)


# ---------------------------------------------------------------------------
# Public accessors — identical surface to the retired openbb_provider.
# ---------------------------------------------------------------------------


async def get_quote(symbol: str) -> Quote:
    """Return the latest quote for ``symbol`` via openbb-mcp."""
    normalized = _normalize_symbol(symbol)
    decoded = await _call_tool(
        "equity_price_quote",
        {"symbol": normalized, "provider": _DEFAULT_PROVIDERS["quote"]},
    )
    rows = _result_rows(decoded)
    if not rows:
        raise ProviderError(f"openbb-mcp quote returned no rows for {symbol!r}")
    row = rows[0]

    price = _coerce_float(row.get("last_price") or row.get("close"))
    prev = _coerce_float(row.get("prev_close") or row.get("previous_close"))
    change = _coerce_float(row.get("change"))
    change_percent = _coerce_float(row.get("change_percent"))
    if price is None:
        raise ProviderError(f"openbb-mcp quote missing price for {symbol!r}")
    if change is None and prev is not None:
        change = price - prev
    if change_percent is None and prev:
        change_percent = ((price - prev) / prev) * 100.0

    return Quote(
        symbol=normalized,
        price=price,
        change=change or 0.0,
        change_percent=change_percent or 0.0,
        volume=_coerce_float(row.get("volume") or row.get("exchange_volume")),
        currency=str(row.get("currency") or "USD"),
        timestamp=_ensure_datetime(row.get("last_timestamp") or row.get("date")),
        provider=PROVIDER,
    )


async def get_history(symbol: str, timeframe: str, range_: str | None = None) -> OHLCVSeries:
    """Return an OHLCV series for ``symbol`` at ``timeframe`` via openbb-mcp."""
    normalized = _normalize_symbol(symbol)
    interval = _TIMEFRAME_MAP.get(timeframe, "1d")
    arguments: dict[str, Any] = {
        "symbol": normalized,
        "interval": interval,
        "provider": _DEFAULT_PROVIDERS["history"],
    }
    if range_ and len(range_) >= 8 and range_[4] == "-":
        arguments["start_date"] = range_

    decoded = await _call_tool("equity_price_historical", arguments)
    bars: list[OHLCVBar] = []
    for raw in _result_rows(decoded):
        try:
            bars.append(
                OHLCVBar(
                    timestamp=_ensure_datetime(raw.get("date") or raw.get("timestamp")),
                    open=float(raw["open"]),
                    high=float(raw["high"]),
                    low=float(raw["low"]),
                    close=float(raw["close"]),
                    volume=float(raw.get("volume") or 0.0),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return OHLCVSeries(symbol=normalized, timeframe=timeframe, bars=bars, provider=PROVIDER)


async def get_fundamentals(symbol: str) -> Fundamentals:
    """Return valuation ratios + company profile for ``symbol`` via openbb-mcp."""
    normalized = _normalize_symbol(symbol)
    profile_rows: list[dict[str, Any]] = []
    try:
        profile = await _call_tool(
            "equity_profile",
            {"symbol": normalized, "provider": _DEFAULT_PROVIDERS["fundamentals"]},
        )
        profile_rows = _result_rows(profile)
    except ProviderError:
        profile_rows = []
    profile_row = profile_rows[0] if profile_rows else {}

    metric_rows: list[dict[str, Any]] = []
    try:
        metric = await _call_tool(
            "equity_fundamental_metrics",
            {"symbol": normalized, "provider": _DEFAULT_PROVIDERS["fundamentals"]},
        )
        metric_rows = _result_rows(metric)
    except ProviderError:
        metric_rows = []
    metric_row = metric_rows[0] if metric_rows else {}

    if not profile_row and not metric_row:
        raise ProviderError(f"openbb-mcp fundamentals returned no rows for {symbol!r}")

    raw_yield = _coerce_float(metric_row.get("dividend_yield"))
    return Fundamentals(
        symbol=normalized,
        name=profile_row.get("name") or profile_row.get("long_name"),
        sector=profile_row.get("sector"),
        industry=profile_row.get("industry_category") or profile_row.get("industry"),
        market_cap=_coerce_float(profile_row.get("market_cap") or metric_row.get("market_cap")),
        pe_ratio=_coerce_float(metric_row.get("pe_ratio") or metric_row.get("trailing_pe")),
        forward_pe=_coerce_float(metric_row.get("forward_pe")),
        peg_ratio=_coerce_float(metric_row.get("peg_ratio")),
        price_to_book=_coerce_float(metric_row.get("price_to_book")),
        # OpenBB returns dividend_yield as a fraction already.
        dividend_yield=raw_yield,
        eps=_coerce_float(metric_row.get("eps") or metric_row.get("trailing_eps")),
        beta=_coerce_float(profile_row.get("beta") or metric_row.get("beta")),
        fifty_two_week_high=_coerce_float(
            profile_row.get("year_high") or metric_row.get("fifty_two_week_high")
        ),
        fifty_two_week_low=_coerce_float(
            profile_row.get("year_low") or metric_row.get("fifty_two_week_low")
        ),
        provider=PROVIDER,
    )


def _statement_lines(rows: list[dict[str, Any]]) -> tuple[list[str], list[StatementLine]]:
    """Pivot a list-of-rows openbb-mcp statement payload into (periods, lines)."""
    periods: list[str] = []
    seen_periods: set[str] = set()
    for row in rows:
        period = str(row.get("period_ending") or row.get("date") or row.get("fiscal_year") or "")
        if period and period not in seen_periods:
            periods.append(period)
            seen_periods.add(period)

    lines_by_label: dict[str, dict[str, float | None]] = {}
    for row in rows:
        period = str(row.get("period_ending") or row.get("date") or row.get("fiscal_year") or "")
        if not period:
            continue
        for key, value in row.items():
            if key in {"symbol", "period_ending", "date", "fiscal_year", "period", "cik"}:
                continue
            coerced = _coerce_float(value)
            if coerced is None and value is not None and not isinstance(value, (int, float)):
                continue
            slot = lines_by_label.setdefault(key, {})
            slot[period] = coerced

    lines = [StatementLine(label=label, values=values) for label, values in lines_by_label.items()]
    return periods, lines


async def _financial_statement(
    symbol: str, tool_name: str
) -> tuple[list[str], list[StatementLine]]:
    """Fetch a financial-statement tool and pivot to (periods, lines)."""
    normalized = _normalize_symbol(symbol)
    decoded = await _call_tool(
        tool_name,
        {"symbol": normalized, "provider": _DEFAULT_PROVIDERS["income"]},
    )
    rows = _result_rows(decoded)
    if not rows:
        raise ProviderError(f"openbb-mcp {tool_name!r} returned no rows for {symbol!r}")
    return _statement_lines(rows)


async def get_income_statement(symbol: str) -> IncomeStatement:
    """Return the income-statement excerpt for ``symbol`` via openbb-mcp."""
    normalized = _normalize_symbol(symbol)
    periods, lines = await _financial_statement(symbol, "equity_fundamental_income")
    return IncomeStatement(symbol=normalized, periods=periods, lines=lines, provider=PROVIDER)


async def get_balance_sheet(symbol: str) -> BalanceSheet:
    """Return the balance-sheet excerpt for ``symbol`` via openbb-mcp."""
    normalized = _normalize_symbol(symbol)
    periods, lines = await _financial_statement(symbol, "equity_fundamental_balance")
    return BalanceSheet(symbol=normalized, periods=periods, lines=lines, provider=PROVIDER)


async def get_cash_flow(symbol: str) -> CashFlowStatement:
    """Return the cash-flow excerpt for ``symbol`` via openbb-mcp."""
    normalized = _normalize_symbol(symbol)
    periods, lines = await _financial_statement(symbol, "equity_fundamental_cash")
    return CashFlowStatement(symbol=normalized, periods=periods, lines=lines, provider=PROVIDER)


async def get_analyst_rating(symbol: str) -> AnalystRating:
    """Return aggregated analyst ratings for ``symbol`` via openbb-mcp."""
    normalized = _normalize_symbol(symbol)
    decoded = await _call_tool(
        "equity_estimates_price_target",
        {"symbol": normalized, "provider": _DEFAULT_PROVIDERS["ratings"]},
    )
    rows = _result_rows(decoded)
    if not rows:
        raise ProviderError(f"openbb-mcp analyst rating returned no rows for {symbol!r}")
    row = rows[0]
    return AnalystRating(
        symbol=normalized,
        consensus=str(row.get("consensus") or row.get("rating") or "") or None,
        target_mean=_coerce_float(row.get("target_mean") or row.get("price_target_mean")),
        target_high=_coerce_float(row.get("target_high") or row.get("price_target_high")),
        target_low=_coerce_float(row.get("target_low") or row.get("price_target_low")),
        strong_buy=int(_coerce_float(row.get("strong_buy")) or 0),
        buy=int(_coerce_float(row.get("buy")) or 0),
        hold=int(_coerce_float(row.get("hold")) or 0),
        sell=int(_coerce_float(row.get("sell")) or 0),
        strong_sell=int(_coerce_float(row.get("strong_sell")) or 0),
        provider=PROVIDER,
    )


async def get_macro_series(series_id: str, provider: str | None = None) -> MacroSeries:
    """Return a macro time-series by id via openbb-mcp."""
    upstream = provider or _DEFAULT_PROVIDERS["macro"]
    decoded = await _call_tool(
        "economy_fred_series",
        {"symbol": series_id, "provider": upstream},
    )
    rows = _result_rows(decoded)
    if not rows:
        raise ProviderError(f"openbb-mcp macro series returned no rows for {series_id!r}")

    title = ""
    metadata = _result_extra(decoded)
    info = metadata.get("results_metadata") or {}
    if isinstance(info, dict):
        entry = info.get(series_id) or next(iter(info.values()), {})
        if isinstance(entry, dict):
            title = str(entry.get("title") or "")

    observations: list[MacroObservation] = []
    for row in rows:
        date = row.get("date")
        value = _coerce_float(row.get("value") or row.get(series_id))
        if date is None:
            continue
        observations.append(MacroObservation(date=_ensure_datetime(date), value=value))

    return MacroSeries(
        series_id=series_id,
        title=title or series_id,
        units=None,
        observations=observations,
        provider=PROVIDER,
    )


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _reset_for_tests() -> None:
    """Clear cached availability state — used only from the test suite."""
    global _AVAILABLE, _last_tool_call_ok, _last_error
    _AVAILABLE = None
    _last_tool_call_ok = None
    _last_error = None
