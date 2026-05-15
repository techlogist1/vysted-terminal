"""OpenBB ODP provider — Phase 2 wrap of the OpenBB Platform.

The provider talks to OpenBB through the *core* router-loader + command-runner
path, never through the ``openbb`` meta-package. The reason is the
PyInstaller ``--onefile`` constraint: the meta-package's first import generates
a static SDK by writing ``.py`` files into ``site-packages/openbb/package/``,
which is read-only inside a frozen one-file binary. Going through
``openbb_core.app.router.RouterLoader.from_extensions()`` and
``openbb_core.app.command_runner.CommandRunner.sync_run`` exercises the same
provider/router extensions but skips the codegen step.

OpenBB is bundled in this build (`openbb-core` + `openbb-equity` +
`openbb-economy` + `openbb-yfinance` + `openbb-fred` + `openbb-fmp` are pinned
in ``sidecar/requirements.txt``). When the import fails for any reason,
``is_available`` returns ``False`` and every accessor raises
:class:`ProviderError`, letting :mod:`services.provider_registry` fall back to
yfinance — the Tier-3 escape hatch the brief calls for.

The shapes returned here mirror the Vysted ``models.market`` and
``models.fundamentals`` Pydantic types, so the registry can drop OpenBB into a
yfinance-shaped slot without router or panel changes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
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
from services.errors import ProviderError

PROVIDER = "openbb"

# Map Vysted timeframe ids to OpenBB ``interval`` strings the equity router
# accepts (yfinance/fmp providers share this vocabulary).
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

# Default upstream provider per data class. The user-visible provider field on
# returned models is always ``"openbb"`` regardless — the upstream choice is an
# implementation detail.
_DEFAULT_PROVIDERS = {
    "quote": "yfinance",
    "history": "yfinance",
    "fundamentals": "yfinance",
    "income": "yfinance",
    "balance": "yfinance",
    "cashflow": "yfinance",
    "ratings": "yfinance",
    "macro": "fred",
}


# ---------------------------------------------------------------------------
# Import probe — done module-load so ``is_available`` is cheap and stable.
# ---------------------------------------------------------------------------

try:  # pragma: no cover - bundling-tier dependent
    from openbb_core.app.command_runner import CommandRunner as _CommandRunner
    from openbb_core.app.router import RouterLoader as _RouterLoader

    _OPENBB_AVAILABLE = True
except Exception:  # noqa: BLE001 - any import failure means OpenBB is not bundled
    _CommandRunner = None  # type: ignore[assignment]
    _RouterLoader = None  # type: ignore[assignment]
    _OPENBB_AVAILABLE = False


# ---------------------------------------------------------------------------
# Lazy runner initialisation. RouterLoader.from_extensions() is the expensive
# part (walks every installed openbb_core_extension entry point); cache it
# behind a lock so concurrent FastAPI workers don't race on first-use.
# ---------------------------------------------------------------------------

_runner: Any = None
_runner_lock = Lock()


def is_available() -> bool:
    """Return whether the OpenBB Platform is importable in this build."""
    return _OPENBB_AVAILABLE


def _normalize_symbol(symbol: str) -> str:
    """Mirror yfinance's dot-ticker fix at the OpenBB seam.

    OpenBB's yfinance/fmp providers inherit the same upstream quirk
    (``BRK.B`` returns nothing). Normalising here keeps callers symmetric with
    :mod:`services.yfinance_provider`.
    """
    return symbol.replace(".", "-").upper()


def _get_runner() -> Any:
    """Return a lazily-initialised, cached :class:`CommandRunner`."""
    global _runner
    if not _OPENBB_AVAILABLE:
        raise ProviderError("OpenBB is not available in this build — falling back to yfinance.")
    with _runner_lock:
        if _runner is None:
            # RouterLoader.from_extensions() registers every installed router
            # extension via the openbb_core_extension entry-point group; the
            # CommandRunner picks it up via the singleton SystemService.
            _RouterLoader.from_extensions()  # type: ignore[union-attr]
            _runner = _CommandRunner()  # type: ignore[union-attr]
        return _runner


def _run(
    route: str,
    *,
    provider: str,
    standard_params: dict[str, Any] | None = None,
    extra_params: dict[str, Any] | None = None,
) -> Any:
    """Execute an OpenBB route synchronously and unwrap the ``OBBject``."""
    runner = _get_runner()
    try:
        result = runner.sync_run(
            route,
            user="",
            provider_choices={"provider": provider},
            standard_params=standard_params or {},
            extra_params=extra_params or {},
        )
    except Exception as exc:  # noqa: BLE001 - any upstream failure becomes ProviderError
        raise ProviderError(f"OpenBB call {route!r} failed: {exc}") from exc
    return result


def _model_to_dict(item: Any) -> dict[str, Any]:
    """Convert an OpenBB result row to a plain dict regardless of shape."""
    if hasattr(item, "model_dump"):
        return dict(item.model_dump())
    if isinstance(item, dict):
        return dict(item)
    return {}


def _coerce_float(value: Any) -> float | None:
    """Convert a possibly-missing numeric field to ``float | None``."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _ensure_datetime(value: Any) -> datetime:
    """Coerce dates/datetimes/ISO strings to a UTC ``datetime``."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if hasattr(value, "isoformat"):  # date-like
        return datetime.fromisoformat(value.isoformat()).replace(tzinfo=UTC)
    if isinstance(value, str):
        # OpenBB returns ISO 8601; fromisoformat handles "YYYY-MM-DD" too.
        try:
            parsed = datetime.fromisoformat(value)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.now(tz=UTC)


# ---------------------------------------------------------------------------
# Public accessors — match yfinance_provider's surface for drop-in dispatch.
# ---------------------------------------------------------------------------


def get_quote(symbol: str) -> Quote:
    """Return the latest quote for ``symbol`` via OpenBB."""
    normalized = _normalize_symbol(symbol)
    result = _run(
        "/equity/price/quote",
        provider=_DEFAULT_PROVIDERS["quote"],
        standard_params={"symbol": normalized},
    )
    rows = getattr(result, "results", None) or []
    if not rows:
        raise ProviderError(f"OpenBB quote returned no rows for {symbol!r}")
    row = _model_to_dict(rows[0])

    price = _coerce_float(row.get("last_price") or row.get("close"))
    prev = _coerce_float(row.get("prev_close") or row.get("previous_close"))
    change = _coerce_float(row.get("change"))
    change_percent = _coerce_float(row.get("change_percent"))
    if price is None:
        raise ProviderError(f"OpenBB quote missing price for {symbol!r}")
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


def get_history(symbol: str, timeframe: str, range_: str | None = None) -> OHLCVSeries:
    """Return an OHLCV series for ``symbol`` at ``timeframe`` via OpenBB."""
    normalized = _normalize_symbol(symbol)
    interval = _TIMEFRAME_MAP.get(timeframe, "1d")
    extra: dict[str, Any] = {"interval": interval}
    # OpenBB accepts ``start_date`` / ``end_date`` (ISO strings); the existing
    # public surface accepts a yfinance-shaped ``range_`` string. We only honour
    # ``range_`` when it parses as an ISO date; otherwise rely on the provider
    # default (which is "max" for daily, sliding window for intraday).
    if range_ and len(range_) >= 8 and range_[4] == "-":
        extra["start_date"] = range_

    result = _run(
        "/equity/price/historical",
        provider=_DEFAULT_PROVIDERS["history"],
        standard_params={"symbol": normalized},
        extra_params=extra,
    )
    rows = getattr(result, "results", None) or []
    bars: list[OHLCVBar] = []
    for raw in rows:
        row = _model_to_dict(raw)
        try:
            bars.append(
                OHLCVBar(
                    timestamp=_ensure_datetime(row.get("date") or row.get("timestamp")),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume") or 0.0),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return OHLCVSeries(symbol=normalized, timeframe=timeframe, bars=bars, provider=PROVIDER)


def get_fundamentals(symbol: str) -> Fundamentals:
    """Return valuation ratios and a company profile for ``symbol`` via OpenBB."""
    normalized = _normalize_symbol(symbol)
    profile_rows: list[Any] = []
    try:
        profile = _run(
            "/equity/profile",
            provider=_DEFAULT_PROVIDERS["fundamentals"],
            standard_params={"symbol": normalized},
        )
        profile_rows = getattr(profile, "results", None) or []
    except ProviderError:
        # Profile is supplementary; fall back to the metric route below.
        profile_rows = []
    profile_row = _model_to_dict(profile_rows[0]) if profile_rows else {}

    metric_rows: list[Any] = []
    try:
        metric = _run(
            "/equity/fundamental/metrics",
            provider=_DEFAULT_PROVIDERS["fundamentals"],
            standard_params={"symbol": normalized},
        )
        metric_rows = getattr(metric, "results", None) or []
    except ProviderError:
        metric_rows = []
    metric_row = _model_to_dict(metric_rows[0]) if metric_rows else {}

    if not profile_row and not metric_row:
        raise ProviderError(f"OpenBB fundamentals returned no rows for {symbol!r}")

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
        # OpenBB providers return dividend_yield as a fraction already
        # (`0.0036` for AAPL), unlike yfinance 1.3.0 which returns a percentage
        # number. No /100 here.
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
    """Pivot a list-of-rows OpenBB statement payload into (periods, lines)."""
    periods: list[str] = []
    seen_periods: set[str] = set()
    for row in rows:
        period = str(row.get("period_ending") or row.get("date") or row.get("fiscal_year") or "")
        if period and period not in seen_periods:
            periods.append(period)
            seen_periods.add(period)

    # Collect (label -> {period -> value}) by walking every numeric field across
    # rows. OpenBB statement schemas vary by provider; this loop is shape-agnostic.
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


def _financial_statement(symbol: str, route: str) -> tuple[list[str], list[StatementLine]]:
    """Fetch a financial-statement route and pivot it to (periods, lines)."""
    normalized = _normalize_symbol(symbol)
    result = _run(
        route,
        provider=_DEFAULT_PROVIDERS["income"],
        standard_params={"symbol": normalized},
    )
    rows = [_model_to_dict(r) for r in (getattr(result, "results", None) or [])]
    if not rows:
        raise ProviderError(f"OpenBB {route} returned no rows for {symbol!r}")
    return _statement_lines(rows)


def get_income_statement(symbol: str) -> IncomeStatement:
    """Return the income-statement excerpt for ``symbol`` via OpenBB."""
    normalized = _normalize_symbol(symbol)
    periods, lines = _financial_statement(symbol, "/equity/fundamental/income")
    return IncomeStatement(symbol=normalized, periods=periods, lines=lines, provider=PROVIDER)


def get_balance_sheet(symbol: str) -> BalanceSheet:
    """Return the balance-sheet excerpt for ``symbol`` via OpenBB."""
    normalized = _normalize_symbol(symbol)
    periods, lines = _financial_statement(symbol, "/equity/fundamental/balance")
    return BalanceSheet(symbol=normalized, periods=periods, lines=lines, provider=PROVIDER)


def get_cash_flow(symbol: str) -> CashFlowStatement:
    """Return the cash-flow-statement excerpt for ``symbol`` via OpenBB."""
    normalized = _normalize_symbol(symbol)
    periods, lines = _financial_statement(symbol, "/equity/fundamental/cash")
    return CashFlowStatement(symbol=normalized, periods=periods, lines=lines, provider=PROVIDER)


def get_analyst_rating(symbol: str) -> AnalystRating:
    """Return aggregated analyst ratings for ``symbol`` via OpenBB."""
    normalized = _normalize_symbol(symbol)
    try:
        estimates = _run(
            "/equity/estimates/price_target",
            provider=_DEFAULT_PROVIDERS["ratings"],
            standard_params={"symbol": normalized},
        )
    except ProviderError as exc:
        raise ProviderError(f"OpenBB analyst rating failed for {symbol!r}: {exc}") from exc
    rows = [_model_to_dict(r) for r in (getattr(estimates, "results", None) or [])]
    if not rows:
        raise ProviderError(f"OpenBB analyst rating returned no rows for {symbol!r}")
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


# ---------------------------------------------------------------------------
# Macro — the Phase-1 hook returns 501; the real route lives here.
# ---------------------------------------------------------------------------


def get_macro_series(series_id: str, provider: str | None = None) -> MacroSeries:
    """Return a macro time-series by id (FRED-style) via OpenBB.

    ``provider`` defaults to ``"fred"``; pass any other OpenBB provider id
    (e.g. ``"econdb"``) to override.
    """
    upstream = provider or _DEFAULT_PROVIDERS["macro"]
    result = _run(
        "/economy/fred_series",
        provider=upstream,
        standard_params={"symbol": series_id},
    )
    rows = [_model_to_dict(r) for r in (getattr(result, "results", None) or [])]
    if not rows:
        raise ProviderError(f"OpenBB macro series returned no rows for {series_id!r}")

    title = ""
    metadata = getattr(result, "extra", None) or {}
    if isinstance(metadata, dict):
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
