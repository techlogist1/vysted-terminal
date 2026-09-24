"""yfinance data provider — the no-API-key default for equity data.

Covers quotes, OHLCV history, valuation ratios, the three financial statements,
and analyst ratings. yfinance does synchronous network I/O; FastAPI runs the
sync router functions that call into here on a worker thread, so this module
stays plain synchronous code.

Every public function raises :class:`ProviderError` on failure. yfinance's
upstream API drifts over time, so each function is defensive and tests mock the
``yf`` module rather than hitting the network.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Literal

import pandas as pd
import yfinance as yf

import config
from models.fundamentals import (
    AnalystRating,
    BalanceSheet,
    CashFlowStatement,
    FieldMeta,
    Fundamentals,
    IncomeStatement,
    StatementLine,
)
from models.market import OHLCVBar, OHLCVSeries, Quote
from services import provider_health, symbol_resolver
from services.errors import ProviderError

PROVIDER = "yfinance"


def _is_rate_limited(exc: BaseException) -> bool:
    """True when ``exc`` (or any exception in its cause/context chain) is a
    yfinance rate-limit — matched by type NAME so this module never imports
    ``yfinance.exceptions`` at call time (test mocks replace ``yf`` wholesale).
    """
    seen: set[int] = set()
    node: BaseException | None = exc
    while node is not None and id(node) not in seen:
        seen.add(id(node))
        if type(node).__name__ == "YFRateLimitError" or "Too Many Requests" in str(node):
            return True
        node = node.__cause__ or node.__context__
    return False


#: yfinance's "Yahoo answered, no such ticker / no bars" family (YFTzMissingError
#: and YFPricesMissingError subclass it), matched by type name like the rate limit.
_MISSING_TICKER_ERRORS = frozenset({"YFTickerMissingError"})

#: Transport failures across the HTTP stacks yfinance and its callers use
#: (curl_cffi, requests, httpx, the builtins), matched on any class in the MRO.
_NETWORK_ERROR_NAMES = frozenset(
    {
        "ConnectionError",
        "ConnectError",
        "ProxyError",
        "Timeout",
        "TimeoutError",
        "TimeoutException",
        "DNSError",
    }
)


def _chain(exc: BaseException) -> list[BaseException]:
    """``exc`` and its cause/context chain, cycle-safe."""
    seen: list[BaseException] = []
    node: BaseException | None = exc
    while node is not None and all(node is not s for s in seen):
        seen.append(node)
        node = node.__cause__ or node.__context__
    return seen


def _has_class_named(exc: BaseException, names: frozenset[str]) -> bool:
    return any(cls.__name__ in names for node in _chain(exc) for cls in type(node).__mro__)


def _provider_error(action: str, symbol: str, exc: BaseException) -> ProviderError:
    """Wrap a yfinance failure as a classified :class:`ProviderError` (R11/D53).

    A rate-limit is reported to the Yahoo-family circuit breaker and carries
    ``kind="rate_limited"`` so callers stop mislabelling throttles as
    ``no_data``/``correctness_gate``; a missing ticker is ``not_found`` and a
    transport failure ``network`` (D-B8-10)."""
    if _is_rate_limited(exc):
        provider_health.record_rate_limited(provider_health.YAHOO)
        return ProviderError(
            f"yfinance {action} rate-limited for {symbol!r}: {exc}",
            kind="rate_limited",
        )
    message = f"yfinance {action} failed for {symbol!r}: {exc}"
    if _has_class_named(exc, _MISSING_TICKER_ERRORS):
        return ProviderError(message, kind="not_found")
    if _has_class_named(exc, _NETWORK_ERROR_NAMES):
        return ProviderError(message, kind="network")
    return ProviderError(message)


def _surface_fetch_error(
    ticker: Any, period: str = "5d", interval: str = "1d"
) -> BaseException | None:
    """Re-fetch ``ticker``'s bars with yfinance's errors raised for this one call
    (not the process-wide ``hide_exceptions`` flag), returning what went wrong
    (``None`` when the fetch succeeds).

    yfinance hides fetch failures: ``history`` returns an empty frame and
    ``fast_info`` raises its internal ``'PriceHistory' object has no attribute
    '_dividends'`` for a missing ticker and a dead network alike, so a failed or
    empty fetch asks Yahoo once more to learn which."""
    try:
        ticker.history(period=period, interval=interval, raise_errors=True)
    except Exception as exc:  # noqa: BLE001 - the caller classifies it
        return exc
    return None


# Public timeframe -> (yfinance interval, default lookback period).
_TIMEFRAME_MAP: dict[str, tuple[str, str]] = {
    "1m": ("1m", "5d"),
    "5m": ("5m", "1mo"),
    "15m": ("15m", "1mo"),
    "30m": ("30m", "1mo"),  # Yahoo serves sub-hour bars for the last 60 days only
    "1h": ("1h", "6mo"),
    "1d": ("1d", "1y"),
    "1wk": ("1wk", "5y"),
    "1mo": ("1mo", "max"),
}


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _normalize_symbol(symbol: str) -> str:
    """Translate yfinance dot-ticker quirks (``BRK.B`` → ``BRK-B``).

    yfinance returns 502 / "no data" for symbols containing dots — its API
    expects the dash form (``BRK.B`` → ``BRK-B``, ``BF.B`` → ``BF-B``,
    ``RDS.A`` → ``RDS-A``). The mapping is yfinance-specific (other providers
    have their own conventions), so it lives in this provider rather than in
    the dispatch layer.
    """
    return symbol.replace(".", "-")


def _nse_listing(bare: str) -> str:
    """Yahoo's form of an NSE listing: Emerge (SME) names are ``-SM.NS``
    (SUMAX-SM.NS; ``SUMAX.NS`` is empty), the main board ``.NS``."""
    return f"{bare}-SM.NS" if symbol_resolver.is_nse_emerge(bare) else f"{bare}.NS"


#: Known Yahoo exchange suffixes carried unchanged (dot form) after the ``.NS``/
#: ``.BO``/``^`` cases above — R15-LEAD-022. None of these is a US share-class
#: letter, so a genuine US quirk ticker (``BRK.B``, ``BF.B``) still falls through
#: to the dash rewrite below.
_YAHOO_EXCHANGE_SUFFIXES = frozenset(
    {
        "AX",
        "HK",
        "T",
        "L",
        "TO",
        "V",
        "DE",
        "PA",
        "AS",
        "SW",
        "MI",
        "MC",
        "KS",
        "KQ",
        "SS",
        "SZ",
        "TW",
        "TWO",
        "SI",
        "JK",
        "BK",
        "KL",
        "NZ",
        "SA",
        "MX",
        "JO",
        "ST",
        "OL",
        "CO",
        "HE",
        "IR",
        "VI",
        "BR",
        "LS",
        "WA",
        "IS",
        "TA",
    }
)


def _yahoo_symbol(symbol: str) -> str:
    """Resolve the symbol to the form Yahoo actually serves data for.

    Four cases, in order:
      * a ``.NS``/``.BO`` suffix or a ``^`` index symbol is already Yahoo's form —
        pass it through UNCHANGED (the old ``_normalize_symbol`` wrongly turned
        ``ROUTE.NS`` into ``ROUTE-NS`` via its dot→dash rule, which Yahoo 502s on —
        the root cause of the all-dashes Indian Equity Overview); an NSE Emerge
        name given as ``.NS`` takes its ``-SM.NS`` form;
      * a bare ticker that is a known NSE instrument (and NOT also a US one) gets
        the ``.NS`` (or Emerge ``-SM.NS``) suffix so Yahoo returns NSE data
        instead of an empty US lookup;
      * a symbol ending in a known non-Indian Yahoo exchange suffix
        (``.AX``, ``.HK``, ``.T``, ``.L``, ...) is already Yahoo's dot form —
        pass it through UNCHANGED (R15-LEAD-022: dash-rewriting ``BHP.AX`` to
        ``BHP-AX`` makes Yahoo report it "possibly delisted");
      * everything else takes the US dot→dash quirk (``BRK.B`` → ``BRK-B``).
    """
    s = symbol.strip().upper()
    if s.startswith("^") or s.endswith(".BO"):
        return s  # a caret index (^NSEI, ^BSESN) is served unsuffixed (R15-LEAD-011)
    if s.endswith(".NS"):
        return _nse_listing(s[:-3]) if symbol_resolver.is_nse_emerge(s) else s
    # Region-aware India resolution. The symbol's intrinsic hint wins; else the
    # active session region. In an IN context a bare (dot-free) ticker picks the
    # exchange the instrument actually lists on — NSE by default, BUT a BSE-ONLY
    # listing must take ``.BO``:
    #   (a) an in-master NSE name (or a DUAL-listed name like INFY, where the IN
    #       user wants the INR NSE listing, not the US ADR) → ``.NS``;
    #   (b) a BSE-ONLY listing (KSE = BSE 519421, never on NSE) → ``.BO`` — Yahoo
    #       answers a bare-``.NS`` BSE-only ticker with a NAMELESS husk (KSE.NS is
    #       a 43-key shell, NOT a 404), while KSE.BO carries the full KSE Limited
    #       profile; forcing ``.NS`` here silently killed the fundamentals of
    #       every alphabetic BSE-only scrip (R13 root cause);
    #   (c) a name in NEITHER master → keep ``.NS`` so Yahoo 404s an unknown
    #       symbol, surfacing an honest "unavailable" rather than a wrong/empty
    #       US row.
    # A dotted US quirk ticker (BRK.B) is left to the dash path below.
    region = symbol_resolver.region_hint(s) or config.get_region()
    if region == "IN" and "." not in s:
        if symbol_resolver.is_nse_symbol(s):
            return _nse_listing(s)
        if symbol_resolver.is_bse_symbol(s):
            return f"{s}.BO"
        return f"{s}.NS"
    if symbol_resolver.is_nse_symbol(s) and not symbol_resolver.is_us_symbol(s):
        return _nse_listing(s)
    if "." in s and s.rsplit(".", 1)[-1] in _YAHOO_EXCHANGE_SUFFIXES:
        return s
    return s.replace(".", "-")


def _is_junk_fundamentals_name(name: str | None, yahoo_symbol: str) -> bool:
    """True when Yahoo returned a fund-ish JUNK record instead of a real company.

    A numeric ``.BO`` scrip code (``509470.BO``) makes Yahoo answer a garbled,
    comma-joined blob for the name — e.g. ``"509470.BO,0P0000BN3V,31"`` — carrying
    the queried symbol and/or an ``0P``-prefixed Morningstar/OTC fund id, never a
    real company name. The R11 honest-404 misses these because ``info`` is
    non-empty. Conservative by construction: a legitimate name (even one with a
    comma, ``"Reliance Industries, Inc."``) contains NONE of these signatures, so
    it is never wrongly rejected.
    """
    if not name or not name.strip():
        return True
    fragments = [f.strip().upper() for f in name.split(",")]
    if len(fragments) < 2:
        return False  # a real name may carry one comma (", Inc.") — that alone is fine
    query = yahoo_symbol.strip().upper()
    bare = query[:-3] if query.endswith((".BO", ".NS")) else query
    if query in fragments or bare in fragments:
        return True  # the queried symbol appears as its own comma-fragment
    return any(f.startswith("0P0") for f in fragments)  # a Morningstar/OTC fund id


# Fundamentals fields that are identity / metadata, not served data VALUES —
# excluded from the per-field provenance map (R13, deliverable 5).
_PROVENANCE_EXCLUDED_FIELDS = frozenset(
    {"symbol", "provider", "growth_basis", "field_meta", "financial_currency"}
)

# Fields ``get_fundamentals`` does NOT source from yfinance's ``info`` snapshot —
# they are computed downstream (trailing-12m dividends by the shared paid-TTM leg
# on /fundamentals and research; quarterly-statement growth by research). They
# are ``None`` here for a reason other than "provider did not publish", so they
# must not be pre-stamped "unavailable" (the
# derived leg stamps their real provenance — an affirmed-zero label, a computed
# value, or an insufficient-depth reason — when it runs).
_DERIVED_FIELDS = frozenset(
    {
        "dividend_per_share_ttm",
        "revenue_growth_computed",
        "earnings_growth_computed",
        "growth_computed_quarters",
    }
)

#: The reason stamped on a DATA field yfinance's ``info`` snapshot carried no
#: value for — so a null field reads as "the provider did not publish this",
#: never a bare dash the panel can't explain.
_NULL_FIELD_REASON = "provider did not publish this field"


def _served_field_meta(fund: Fundamentals, as_of: str) -> dict[str, FieldMeta]:
    """Per-field provenance for EVERY data field yfinance's snapshot speaks to.

    A ``status="ok"`` entry for each non-null data field (tagging the provider and
    the ``info`` fetch time ``as_of``), and a ``status="unavailable"`` entry — with
    an explicit ``reason`` — for each data field the snapshot carried NO value for,
    so a null field is never a bare, unexplained dash. Identity/metadata fields
    (symbol/provider/growth_basis/field_meta) and the downstream-DERIVED fields
    (dividend TTM, computed growth) are excluded — the latter get their real
    provenance from the derived leg, not a premature "unavailable". The correctness
    gate MERGES its withheld/flag entries onto this map downstream, so a field it
    nulls flips from ``ok`` to ``withheld`` while the rest keep their provenance.
    """
    skip = _PROVENANCE_EXCLUDED_FIELDS | _DERIVED_FIELDS
    meta: dict[str, FieldMeta] = {}
    for name in type(fund).model_fields:
        if name in skip:
            continue
        if getattr(fund, name, None) is not None:
            meta[name] = FieldMeta(status="ok", provider=PROVIDER, as_of=as_of)
        else:
            meta[name] = FieldMeta(
                status="unavailable",
                provider=PROVIDER,
                as_of=as_of,
                reason=_NULL_FIELD_REASON,
            )
    return meta


def _num(value: Any) -> float | None:
    """Coerce a possibly-missing/NaN value to ``float | None``."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


#: Yahoo ratios whose numerator is in the TRADING currency while the denominator
#: is a statement figure in ``financialCurrency``. When the two currencies differ
#: (an ADR reporting in INR/TWD) the ratio is off by the exchange rate: SIFY's
#: ``priceToSalesTrailing12Months`` is USD market cap / INR revenue (~88x low) and
#: its ``enterpriseToEbitda`` (4.8) matches neither a USD nor an INR basis.
#: ``priceToBook`` is NOT here: Yahoo states ``bookValue`` per share in the trading
#: currency (SIFY 13.66 / 2.754 = 4.96 on a USD book value), so it stays served.
_MIXED_BASIS_RATIOS: dict[str, str] = {
    "price_to_sales": "price/sales (market cap over trailing revenue)",
    "ev_to_ebitda": "EV/EBITDA (enterprise value over EBITDA)",
}


#: Fields computed from the snapshot's price: their ``as_of`` is that price's
#: trade time, not the fetch time (R15-DATA-006).
_PRICE_DERIVED_FIELDS = (
    "ratio_price",
    "market_cap",
    "pe_ratio",
    "forward_pe",
    "peg_ratio",
    "price_to_book",
    "price_to_sales",
    "ev_to_ebitda",
    "dividend_yield",
    "fifty_two_week_change",
)


def _stamp_price_trade_time(meta: dict[str, FieldMeta], market_time: Any) -> None:
    """Date the price-derived fields by Yahoo's ``regularMarketTime`` (epoch
    seconds of the last trade). An illiquid scrip's last print can be months old
    (DAL: 2025-03-12), so the fetch time would present it as today's; when Yahoo
    names no trade time the as-of is left unknown (``None``), never now()."""
    trade_time = (
        datetime.fromtimestamp(market_time, tz=UTC).isoformat()
        if isinstance(market_time, (int, float))
        else None
    )
    for name in _PRICE_DERIVED_FIELDS:
        if name in meta:
            meta[name].as_of = trade_time


def _financial_currency(info: dict[str, Any]) -> str | None:
    """Yahoo's ``financialCurrency`` when it differs from the trading ``currency``.

    Yahoo states the statement sizes (``totalRevenue``, ``netIncomeToCommon``,
    ``freeCashflow``, ``ebitda``) in the reporting currency, which for a foreign
    reporter differs from the currency its listing trades in. ``None`` when the two
    agree or either is missing (nothing to disclose).
    """
    trading = info.get("currency")
    financial = info.get("financialCurrency")
    if not trading or not financial or str(financial).upper() == str(trading).upper():
        return None
    return str(financial)


def _withhold_mixed_basis_ratios(fund: Fundamentals) -> None:
    """Null every Yahoo ratio that divides a trading-currency figure by a
    statement-currency one and stamp its ``field_meta`` withheld with the reason
    (D-B2-3: no FX conversion, so a ratio on two bases is never served)."""
    meta = fund.field_meta if fund.field_meta is not None else {}
    for field_name, label in _MIXED_BASIS_RATIOS.items():
        if getattr(fund, field_name) is None:
            continue
        setattr(fund, field_name, None)
        prev = meta.get(field_name)
        meta[field_name] = FieldMeta(
            status="withheld",
            provider=PROVIDER,
            as_of=prev.as_of if prev else None,
            reason=(
                f"Yahoo's {label} mixes bases: the listing trades in {fund.currency} "
                f"but reports its statements in {fund.financial_currency}, so the "
                "ratio is off by the exchange rate; withheld"
            ),
        )
    fund.field_meta = meta


def get_quote(symbol: str) -> Quote:
    """Return the latest quote for ``symbol``.

    Routes through :func:`_yahoo_symbol` (NOT the US-only ``_normalize_symbol``) so
    a ``.NS``/``.BO`` Indian symbol passes through unchanged and a bare NSE ticker
    in an IN context resolves to the ``.NS`` listing — the same region-aware mapper
    fundamentals/statements already use (the dot→dash US quirk still applies). The
    old path turned ``RELIANCE.NS`` into ``RELIANCE-NS``, which Yahoo 502s on.
    """
    normalized = _yahoo_symbol(symbol)
    ticker = yf.Ticker(normalized)
    try:
        fast = ticker.fast_info
        price = float(fast.last_price)
        prev = float(fast.previous_close)
        volume = getattr(fast, "last_volume", None)
        currency = getattr(fast, "currency", None) or "USD"
        timestamp = _quote_time(ticker)
    except Exception as exc:  # noqa: BLE001 - any yfinance failure is a provider error
        cause = _surface_fetch_error(ticker) or exc
        raise _provider_error("quote", symbol, cause) from exc

    provider_health.record_success(provider_health.YAHOO)
    change = price - prev
    change_percent = (change / prev * 100.0) if prev else 0.0
    return Quote(
        symbol=normalized.upper(),
        price=price,
        change=change,
        change_percent=change_percent,
        volume=_num(volume),
        currency=str(currency),
        timestamp=timestamp,
        provider=PROVIDER,
    )


def _quote_time(ticker: Any) -> datetime:
    """When the quoted price traded (R15-LEAD-005): Yahoo's ``regularMarketTime``
    from the history fetch ``fast_info`` priced from, else the last bar's time —
    never now(), which would date a closed market's last print as current.

    yfinance keeps ``regularMarketTime`` as epoch seconds until it formats the
    metadata into an exchange-local ``Timestamp``; both normalize to UTC.

    Terminal case (R15-LEAD-023, D-B9-2): when the metadata has no
    ``regularMarketTime`` AND the 5-day daily history comes back empty (no
    trade to date it by), this raises :class:`ProviderError` so the registry
    falls through to the next provider — never a synthesized ``now()``, which
    would misdate a closed/stale quote as fresh."""
    market_time = ticker.get_history_metadata().get("regularMarketTime")
    if market_time is None:
        bars = ticker.history(period="5d", interval="1d")
        if bars.empty:
            raise ProviderError("Yahoo returned a price with no trade time", kind=None)
        market_time = bars.index[-1]
    stamp = (
        pd.Timestamp(market_time, unit="s")
        if isinstance(market_time, (int, float))
        else pd.Timestamp(market_time)
    )
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize("UTC")
    return stamp.tz_convert("UTC").to_pydatetime()


def get_history(symbol: str, timeframe: str, range_: str | None = None) -> OHLCVSeries:
    """Return an OHLCV series for ``symbol`` at ``timeframe``.

    Routes through :func:`_yahoo_symbol` so ``RELIANCE.NS`` / ``532837.BO`` pass
    through unchanged instead of being mangled to the all-dashes form Yahoo 502s on.

    Yahoo forward-fills an untraded scrip with bars at the prior close and zero
    volume (DAL.BO: 1,238 bars, 33 traded). Those bars are not trades, so they
    are dropped (R15-DATA-016); a zero-volume bar whose prices move (an index)
    is kept.

    yfinance hides fetch exceptions, returning an empty frame for a dead network
    too, so an empty frame is re-asked with errors raised: an outage is a
    ``network`` error, never an empty series; Yahoo answering with no bars
    (``YFTickerMissingError``) stays the empty series the history route
    downgrades to "no price data".
    """
    normalized = _yahoo_symbol(symbol)
    interval, default_period = _TIMEFRAME_MAP.get(timeframe, ("1d", "1y"))
    period = range_ or default_period
    ticker = yf.Ticker(normalized)
    try:
        frame = ticker.history(period=period, interval=interval)
    except Exception as exc:  # noqa: BLE001
        raise _provider_error("history", symbol, exc) from exc
    if frame.empty:
        hidden = _surface_fetch_error(ticker, period, interval)
        if hidden is not None and not _has_class_named(hidden, _MISSING_TICKER_ERRORS):
            raise _provider_error("history", symbol, hidden) from hidden
    provider_health.record_success(provider_health.YAHOO)

    bars: list[OHLCVBar] = []
    prior_close: float | None = None
    for index, row in frame.iterrows():
        timestamp = index.to_pydatetime() if hasattr(index, "to_pydatetime") else index
        ohlc = [_num(row[column]) for column in ("Open", "High", "Low", "Close")]
        if any(value is None for value in ohlc):
            continue  # a bar with a NaN/missing price cell is dropped, never served
        open_, high, low, close = ohlc
        volume = _num(row["Volume"]) or 0.0
        forward_filled = (
            volume == 0
            and open_ == high == low == close
            and prior_close in (None, close)  # the first bar has no prior to differ from
        )
        prior_close = close
        if forward_filled:
            continue
        bars.append(
            OHLCVBar(
                timestamp=timestamp,
                open=open_,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )
    return OHLCVSeries(symbol=normalized.upper(), timeframe=timeframe, bars=bars, provider=PROVIDER)


#: Balance-sheet / income-statement rows read for the derived-ratio leg
#: (R15-DATA-048), each in preference order.
_TOTAL_ASSETS_LABELS = ("Total Assets",)
_CURRENT_LIABILITIES_LABELS = ("Current Liabilities", "Total Current Liabilities")
_TOTAL_DEBT_LABELS = ("Total Debt",)
_EBIT_LABELS = ("EBIT", "Operating Income")
_REVENUE_LABELS = ("Total Revenue",)


def _newest_statement_value(
    frames: tuple[pd.DataFrame, ...], labels: tuple[str, ...]
) -> tuple[date, float] | None:
    """The newest ``(period_end, value)`` across ``frames`` for the first row any
    frame carries from ``labels`` — the shared reader behind
    :func:`get_newest_equity` and the derived-ratio leg."""
    newest: tuple[date, float] | None = None
    for frame in frames:
        if frame is None or frame.empty:
            continue
        label = next((name for name in labels if name in frame.index), None)
        if label is None:
            continue
        for column, raw in frame.loc[label].items():
            value = _num(raw)
            if value is None:
                continue
            period_end = pd.Timestamp(column).date()
            if newest is None or period_end > newest[0]:
                newest = (period_end, value)
    return newest


def _annual_series(frame: pd.DataFrame | None, labels: tuple[str, ...]) -> list[tuple[date, float]]:
    """Every ``(period_end, value)`` pair for the first matching row, oldest
    first — the revenue-growth fallback's consecutive-annual-period reader."""
    if frame is None or frame.empty:
        return []
    label = next((name for name in labels if name in frame.index), None)
    if label is None:
        return []
    pairs: list[tuple[date, float]] = []
    for column, raw in frame.loc[label].items():
        value = _num(raw)
        if value is None:
            continue
        pairs.append((pd.Timestamp(column).date(), value))
    pairs.sort(key=lambda pair: pair[0])
    return pairs


def _derive_fundamentals(fund: Fundamentals, ticker: Any, fetched_at: str) -> None:
    """Fill valuation/health/profile fields Yahoo omitted, from the statements
    the provider already fetches (R15-DATA-048/054/055, D-B9-6).

    A derived ratio is used ONLY where Yahoo's own field is ``None`` — it never
    overrides a value Yahoo actually served — and is stamped
    ``field_meta[name].provider = "derived"`` with the formula in
    ``basis_note``. ``roce`` has no Yahoo equivalent at all, so it is always
    either derived or left explicitly ``unavailable`` (it is excluded from the
    generic per-field provenance pass — see ``_DERIVED_FIELDS`` — so it must be
    stamped here either way). A fetch failure on this best-effort leg never
    fails the fundamentals call: the ratios simply stay whatever Yahoo served.
    """
    meta = fund.field_meta if fund.field_meta is not None else {}

    try:
        bs_frames: tuple[pd.DataFrame, ...] = (ticker.quarterly_balance_sheet, ticker.balance_sheet)
    except Exception:  # noqa: BLE001 - a derived leg's own fetch failure is not fatal
        bs_frames = ()
    try:
        is_frames: tuple[pd.DataFrame, ...] = (ticker.quarterly_income_stmt, ticker.income_stmt)
    except Exception:  # noqa: BLE001
        is_frames = ()

    equity = _newest_statement_value(bs_frames, _EQUITY_LABELS)
    total_assets = _newest_statement_value(bs_frames, _TOTAL_ASSETS_LABELS)
    current_liabilities = _newest_statement_value(bs_frames, _CURRENT_LIABILITIES_LABELS)
    total_debt = _newest_statement_value(bs_frames, _TOTAL_DEBT_LABELS)
    # Annual EBIT only: a newest-quarter EBIT over a period-end balance sheet
    # understates ROCE ~4x.
    ebit = _newest_statement_value(is_frames[-1:], _EBIT_LABELS)

    def _derive(field_name: str, value: float, note: str) -> None:
        setattr(fund, field_name, value)
        prev = meta.get(field_name)
        meta[field_name] = FieldMeta(
            status="ok",
            provider="derived",
            as_of=prev.as_of if prev and prev.as_of else fetched_at,
            basis_note=note,
        )

    # ROCE — always derived (or explicitly unavailable); Yahoo has no such field.
    roce_value: float | None = None
    if ebit is not None and total_assets is not None and current_liabilities is not None:
        denom = total_assets[1] - current_liabilities[1]
        if denom != 0:
            roce_value = ebit[1] / denom
    if roce_value is not None:
        _derive("roce", roce_value, "annual EBIT / (total assets - current liabilities)")
    else:
        meta["roce"] = FieldMeta(
            status="unavailable",
            provider=PROVIDER,
            as_of=fetched_at,
            reason="insufficient statement data to derive ROCE",
        )

    if (
        fund.roe is None
        and fund.net_income_ttm is not None
        and equity is not None
        and equity[1] != 0
    ):
        _derive("roe", fund.net_income_ttm / equity[1], "net income (TTM) / stockholders equity")

    # A derived D/E of 0 for a genuinely debt-free name is a served VALUE
    # (R15-DATA-048) — never withheld or skipped as missing.
    if fund.debt_to_equity is None and total_debt is not None:
        if total_debt[1] == 0:
            _derive("debt_to_equity", 0.0, "total debt / stockholders equity")
        elif equity is not None and equity[1] != 0:
            _derive("debt_to_equity", total_debt[1] / equity[1], "total debt / stockholders equity")

    if fund.eps is None and fund.net_income_ttm is not None and fund.shares_outstanding:
        _derive(
            "eps",
            fund.net_income_ttm / fund.shares_outstanding,
            "net income (TTM) / shares outstanding",
        )

    if fund.pe_ratio is None and fund.ratio_price is not None and fund.eps:
        _derive("pe_ratio", fund.ratio_price / fund.eps, "price / EPS")

    if fund.market_cap is None and fund.ratio_price is not None and fund.shares_outstanding:
        _derive(
            "market_cap", fund.ratio_price * fund.shares_outstanding, "price x shares outstanding"
        )

    # Revenue growth fallback — only when Yahoo gave NEITHER growth figure, so
    # the single shared ``growth_basis`` never mixes an annual-derived figure
    # with a Yahoo-served MRQ-YoY one.
    if fund.revenue_growth is None and fund.earnings_growth is None:
        annual_revenue = is_frames[-1] if is_frames else None
        series = _annual_series(annual_revenue, _REVENUE_LABELS)
        if len(series) >= 2:
            previous, latest = series[-2][1], series[-1][1]
            if previous:
                _derive(
                    "revenue_growth",
                    (latest - previous) / abs(previous),
                    "annual YoY revenue growth",
                )
                fund.growth_basis = "annual_yoy"

    # 52-week leg dates (R15-DATA-055): the 1y daily history's argmax(High) /
    # argmin(Low). Best-effort — a fetch failure leaves the dates unset.
    if fund.fifty_two_week_high is not None or fund.fifty_two_week_low is not None:
        try:
            hist = ticker.history(period="1y", interval="1d")
        except Exception:  # noqa: BLE001
            hist = None
        if hist is not None and not hist.empty:
            if "High" in hist.columns and fund.fifty_two_week_high is not None:
                idx = hist["High"].idxmax()
                fund.fifty_two_week_high_date = pd.Timestamp(idx).date().isoformat()
                meta["fifty_two_week_high_date"] = FieldMeta(
                    status="ok", provider=PROVIDER, as_of=fetched_at
                )
            if "Low" in hist.columns and fund.fifty_two_week_low is not None:
                idx = hist["Low"].idxmin()
                fund.fifty_two_week_low_date = pd.Timestamp(idx).date().isoformat()
                meta["fifty_two_week_low_date"] = FieldMeta(
                    status="ok", provider=PROVIDER, as_of=fetched_at
                )

    fund.field_meta = meta


def _resolve_sector(yahoo: str, info: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    """``(sector, industry, sector_source)`` for a fundamentals payload
    (R15-DATA-052).

    Yahoo's ``sector``/``industry`` are used as served, EXCEPT a bare empty
    string ``""`` never counts as served (Yahoo returns ``ok`` with an empty
    string for names it has no classification for, e.g. ELCIDIN — that must
    read as unavailable, not a real blank sector). For an Indian listing
    (a resolved ``.NS``/``.BO`` symbol), the bundled India sector map is
    consulted and its record — when it carries a non-empty sector — WINS over
    Yahoo, because Yahoo's classification for small/micro-cap Indian names is
    frequently wrong (NAPEROL: Yahoo 'Basic Materials', BSE-sourced map and
    screener.in both 'Financial Services')."""
    raw_sector = info.get("sector")
    raw_industry = info.get("industry")
    sector = raw_sector if raw_sector and str(raw_sector).strip() else None
    industry = raw_industry if raw_industry and str(raw_industry).strip() else None
    sector_source = "yfinance" if sector is not None else None

    if yahoo.endswith((".NS", ".BO")):
        bare = yahoo.rsplit(".", 1)[0]
        if bare.endswith("-SM"):
            bare = bare[: -len("-SM")]
        record = symbol_resolver._india_sector_map().get(bare)  # noqa: SLF001
        if record:
            map_sector = record.get("sector")
            map_industry = record.get("industry_raw") or record.get("sector")
            if map_sector and str(map_sector).strip():
                sector = str(map_sector)
                sector_source = "resolver"
            if map_industry and str(map_industry).strip():
                industry = str(map_industry)
    return sector, industry, sector_source


def get_fundamentals(symbol: str) -> Fundamentals:
    """Return valuation ratios, profitability, health, and a company profile.

    Uses :func:`_yahoo_symbol` so a bare NSE ticker (``ROUTE``) or a ``.NS`` form
    (``ROUTE.NS``) actually hits Yahoo's India data instead of an empty US lookup
    — the fix for the all-dashes Indian Equity Overview.
    """
    yahoo = _yahoo_symbol(symbol)
    ticker = yf.Ticker(yahoo)
    try:
        info = ticker.info
    except Exception as exc:  # noqa: BLE001
        raise _provider_error("fundamentals", symbol, exc) from exc

    provider_health.record_success(provider_health.YAHOO)
    fetched_at = _utcnow().isoformat()  # the info snapshot's as_of for field_meta
    # An unknown/garbage symbol comes back as an EMPTY info dict, not an
    # exception — serving it as an all-null 200 reads as "instrument exists,
    # no data" (a dishonest shape; R11 gate-7 catch) and lets the deep
    # crawler stamp uncovered scrips as freshly enriched. Say the truth.
    if not isinstance(info, dict) or not any(
        info.get(key) is not None
        for key in ("longName", "shortName", "regularMarketPrice", "marketCap", "currency")
    ):
        raise ProviderError(f"yfinance has no instrument data for {symbol!r}", kind="not_found")
    # Two DISTINCT junk shapes reach here (both pass the empty-info gate because
    # SOME identity key is set), and the error must say which actually happened:
    #   * a NAMELESS husk — Yahoo answered with keys but NO company name (the
    #     ``KSE.NS`` 43-key shell a bare BSE-only ticker used to hit): there is no
    #     company record for this symbol, full stop;
    #   * a garbled fund-id BLOB — a non-empty but nonsense name carrying the
    #     queried symbol / an ``0P``-Morningstar id ("509470.BO,0P0000BN3V,31"),
    #     which a numeric ``.BO`` scrip code provokes.
    # Both are an honest 404, but the OLD code reported the nameless husk as a
    # "non-company (fund-id) record" — a misleading message that pointed at the
    # wrong failure mode.
    name = info.get("longName") or info.get("shortName")
    if not name or not str(name).strip():
        raise ProviderError(
            f"Yahoo has no company record for {yahoo!r}",
            kind="not_found",
        )
    if _is_junk_fundamentals_name(name, yahoo):
        raise ProviderError(
            f"yfinance returned a non-company (fund-id) record for {symbol!r}",
            kind="not_found",
        )
    # yfinance 1.3.0 returns ``dividendYield`` as a percentage number (e.g.
    # ``0.36`` for AAPL, ``6.01`` for VZ) — not a fraction. The contract is a
    # fraction (the panel ×100s it). A negative or implausible value is withheld
    # by the correctness gate, the only yield bound (R15-DATA-034).
    raw_yield = _num(info.get("dividendYield"))
    div_yield = raw_yield / 100.0 if raw_yield is not None else None

    # yfinance reports debtToEquity in percent form (150.0 = 1.5x); normalise to a
    # ratio so the screener/overview read the conventional D/E.
    raw_de = _num(info.get("debtToEquity"))
    debt_to_equity = (raw_de / 100.0) if raw_de is not None else None

    sector, industry, sector_source = _resolve_sector(yahoo, info)

    # R15-DATA-054: Yahoo serves the CONSOLIDATED statement set for an Indian
    # listing; every other listing's basis is not independently knowable here.
    basis: Literal["consolidated", "standalone"] | None = (
        "consolidated" if yahoo.endswith((".NS", ".BO")) else None
    )
    # R15-DATA-055: the listing's first-trade date, for the "since listing"
    # 52w-range relabel on a listing younger than a year.
    listing_ms = info.get("firstTradeDateMilliseconds")
    listing_date = (
        datetime.fromtimestamp(listing_ms / 1000.0, tz=UTC).date().isoformat()
        if isinstance(listing_ms, (int, float))
        else None
    )
    # The fiscal year end the forward-PE estimate targets, when Yahoo names one.
    next_fy_end = info.get("nextFiscalYearEnd")
    forward_pe_fiscal_year = (
        datetime.fromtimestamp(next_fy_end, tz=UTC).date().isoformat()
        if info.get("forwardPE") is not None and isinstance(next_fy_end, (int, float))
        else None
    )

    fund = Fundamentals(
        symbol=yahoo,
        name=name,
        sector=sector,
        industry=industry,
        sector_source=sector_source,
        basis=basis,
        listing_date=listing_date,
        forward_pe_fiscal_year=forward_pe_fiscal_year,
        currency=info.get("currency") or info.get("financialCurrency"),
        financial_currency=_financial_currency(info),
        ratio_price=_num(info.get("currentPrice") or info.get("regularMarketPrice")),
        # Valuation
        market_cap=_num(info.get("marketCap")),
        pe_ratio=_num(info.get("trailingPE")),
        forward_pe=_num(info.get("forwardPE")),
        peg_ratio=_num(info.get("trailingPegRatio") or info.get("pegRatio")),
        price_to_book=_num(info.get("priceToBook")),
        price_to_sales=_num(info.get("priceToSalesTrailing12Months")),
        ev_to_ebitda=_num(info.get("enterpriseToEbitda")),
        book_value=_num(info.get("bookValue")),
        dividend_yield=div_yield,
        dividend_per_share=_num(info.get("dividendRate")),
        eps=_num(info.get("trailingEps")),
        beta=_num(info.get("beta")),
        fifty_two_week_high=_num(info.get("fiftyTwoWeekHigh")),
        fifty_two_week_low=_num(info.get("fiftyTwoWeekLow")),
        fifty_two_week_change=_num(info.get("52WeekChange")),
        # Profitability (fractions)
        roe=_num(info.get("returnOnEquity")),
        roa=_num(info.get("returnOnAssets")),
        gross_margin=_num(info.get("grossMargins")),
        operating_margin=_num(info.get("operatingMargins")),
        profit_margin=_num(info.get("profitMargins")),
        # Financial health
        debt_to_equity=debt_to_equity,
        current_ratio=_num(info.get("currentRatio")),
        quick_ratio=_num(info.get("quickRatio")),
        # Size & growth
        revenue_ttm=_num(info.get("totalRevenue")),
        net_income_ttm=_num(info.get("netIncomeToCommon")),
        free_cash_flow=_num(info.get("freeCashflow")),
        shares_outstanding=_num(info.get("sharesOutstanding")),
        revenue_growth=_num(info.get("revenueGrowth")),
        earnings_growth=_num(info.get("earningsGrowth")),
        # Ownership (fractions)
        held_percent_insiders=_num(info.get("heldPercentInsiders")),
        held_percent_institutions=_num(info.get("heldPercentInstitutions")),
        provider=PROVIDER,
    )
    # R13: stamp per-field provenance for every value actually served (the gate
    # then merges its withheld/flag entries on top).
    fund.field_meta = _served_field_meta(fund, fetched_at)
    _stamp_price_trade_time(fund.field_meta, info.get("regularMarketTime"))
    if fund.financial_currency is not None:
        _withhold_mixed_basis_ratios(fund)
    _derive_fundamentals(fund, ticker, fetched_at)
    return fund


def _statement_lines(frame: pd.DataFrame) -> tuple[list[str], list[StatementLine]]:
    """Convert a yfinance statement DataFrame to (periods, lines).

    Every period is labelled by its ISO period-end date, annual and quarterly
    alike (R15-DATA-026), the label openbb-mcp serves too (R15-LEAD-015)."""
    periods = [pd.Timestamp(col).date().isoformat() for col in frame.columns]
    lines: list[StatementLine] = []
    for label, row in frame.iterrows():
        values = {period: _num(row.iloc[idx]) for idx, period in enumerate(periods)}
        lines.append(StatementLine(label=str(label), values=values))
    return periods, lines


def get_income_statement(symbol: str, period: str = "annual") -> IncomeStatement:
    """Return the income statement excerpt for ``symbol``; ``period`` is
    ``"annual"`` or ``"quarterly"``."""
    normalized = _yahoo_symbol(symbol)
    try:
        ticker = yf.Ticker(normalized)
        frame = ticker.quarterly_income_stmt if period == "quarterly" else ticker.income_stmt
    except Exception as exc:  # noqa: BLE001
        raise _provider_error("income statement", symbol, exc) from exc
    provider_health.record_success(provider_health.YAHOO)
    periods, lines = _statement_lines(frame)
    return IncomeStatement(
        symbol=normalized.upper(), periods=periods, lines=lines, provider=PROVIDER
    )


def get_quarterly_period_ends(symbol: str) -> list[date]:
    """The period-end dates of Yahoo's quarterly income statement for ``symbol``.

    The witness for how many filed periods back Yahoo's trailing-12-month sizes:
    a half-yearly filer shows two period ends in a year, not four.
    """
    normalized = _yahoo_symbol(symbol)
    try:
        frame = yf.Ticker(normalized).quarterly_income_stmt
        ends = [pd.Timestamp(column).date() for column in frame.columns]
    except Exception as exc:  # noqa: BLE001
        raise _provider_error("quarterly income statement", symbol, exc) from exc
    provider_health.record_success(provider_health.YAHOO)
    return ends


def get_balance_sheet(symbol: str, period: str = "annual") -> BalanceSheet:
    """Return the balance sheet excerpt for ``symbol``."""
    normalized = _yahoo_symbol(symbol)
    try:
        ticker = yf.Ticker(normalized)
        frame = ticker.quarterly_balance_sheet if period == "quarterly" else ticker.balance_sheet
    except Exception as exc:  # noqa: BLE001
        raise _provider_error("balance sheet", symbol, exc) from exc
    provider_health.record_success(provider_health.YAHOO)
    periods, lines = _statement_lines(frame)
    return BalanceSheet(symbol=normalized.upper(), periods=periods, lines=lines, provider=PROVIDER)


#: Balance-sheet rows read as total stockholders' equity, in preference order.
_EQUITY_LABELS = ("Stockholders Equity", "Common Stock Equity")


def get_newest_equity(symbol: str) -> tuple[date, float] | None:
    """The newest filed stockholders' equity for ``symbol`` and its period end,
    across Yahoo's quarterly and annual balance sheets (a quarter filed after the
    last fiscal year wins). ``None`` when neither frame carries an equity row.

    The witness for the per-share book fields: ``bookValue`` and ``priceToBook``
    are Yahoo scalars that can sit on a stale share count (R15-DATA-005).
    """
    normalized = _yahoo_symbol(symbol)
    try:
        ticker = yf.Ticker(normalized)
        frames = (ticker.quarterly_balance_sheet, ticker.balance_sheet)
    except Exception as exc:  # noqa: BLE001
        raise _provider_error("balance sheet", symbol, exc) from exc
    provider_health.record_success(provider_health.YAHOO)
    newest: tuple[date, float] | None = None
    for frame in frames:
        label = next((name for name in _EQUITY_LABELS if name in frame.index), None)
        if label is None:
            continue
        for column, raw in frame.loc[label].items():
            value = _num(raw)
            period_end = pd.Timestamp(column).date()
            if value is not None and (newest is None or period_end > newest[0]):
                newest = (period_end, value)
    return newest


def get_cash_flow(symbol: str, period: str = "annual") -> CashFlowStatement:
    """Return the cash-flow statement excerpt for ``symbol``."""
    normalized = _yahoo_symbol(symbol)
    try:
        ticker = yf.Ticker(normalized)
        frame = ticker.quarterly_cashflow if period == "quarterly" else ticker.cashflow
    except Exception as exc:  # noqa: BLE001
        raise _provider_error("cash flow", symbol, exc) from exc
    provider_health.record_success(provider_health.YAHOO)
    periods, lines = _statement_lines(frame)
    return CashFlowStatement(
        symbol=normalized.upper(), periods=periods, lines=lines, provider=PROVIDER
    )


def get_analyst_rating(symbol: str) -> AnalystRating:
    """Return aggregated analyst ratings and price targets for ``symbol``."""
    normalized = _yahoo_symbol(symbol)
    try:
        ticker = yf.Ticker(normalized)
        recommendations = ticker.recommendations
        targets = ticker.analyst_price_targets
    except Exception as exc:  # noqa: BLE001
        raise _provider_error("analyst rating", symbol, exc) from exc
    provider_health.record_success(provider_health.YAHOO)

    counts = {"strongBuy": 0, "buy": 0, "hold": 0, "sell": 0, "strongSell": 0}
    if recommendations is not None and not recommendations.empty:
        latest = recommendations.iloc[0]
        for key in counts:
            value = _num(latest.get(key))
            counts[key] = int(value) if value is not None else 0

    targets = targets or {}
    return AnalystRating(
        symbol=normalized.upper(),
        consensus=_consensus(counts),
        target_mean=_num(targets.get("mean")),
        target_high=_num(targets.get("high")),
        target_low=_num(targets.get("low")),
        strong_buy=counts["strongBuy"],
        buy=counts["buy"],
        hold=counts["hold"],
        sell=counts["sell"],
        strong_sell=counts["strongSell"],
        provider=PROVIDER,
    )


def _consensus(counts: dict[str, int]) -> str | None:
    """Derive a coarse consensus label from the rating counts."""
    total = sum(counts.values())
    if total == 0:
        return None
    bullish = counts["strongBuy"] + counts["buy"]
    bearish = counts["sell"] + counts["strongSell"]
    if bullish > bearish and bullish >= counts["hold"]:
        return "buy"
    if bearish > bullish and bearish >= counts["hold"]:
        return "sell"
    return "hold"
