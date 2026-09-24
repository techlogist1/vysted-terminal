"""Listed option chains with exchange-published open interest (R15-DATA-079, D-B11-6).

Research data only (D81): the chain is what the exchange published for a
session, never a trading surface.

IN — the NSE F&O UDiFF bhavcopy, the once-daily EOD dump of every F&O contract::

    https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_YYYYMMDD_F_0000.csv.zip

Same host, headers and ZIP wrapping as the CM bhavcopy in :mod:`services.nse_bhavcopy`
(this module shares its client, throttle and test transport). Only index and
stock option rows (``FinInstrmTp`` IDO/STO) are kept, keyed by the bare
underlying (``NIFTY``, ``RELIANCE``). The walk back from IST-today over
weekends and holidays mirrors ``nse_bhavcopy.fetch_latest``; parsed rows are
cached per trade date in :mod:`services.data_cache`.

US — yfinance ``Ticker.option_chain`` (OI, implied volatility). Its values are
delayed, so they are labelled by the newest contract trade date, never as live.
"""

from __future__ import annotations

import asyncio
import csv
import io
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import httpx

from models.market import OptionChain, OptionContract
from services import data_cache, nse_bhavcopy
from services.locale import (
    REGION_IN,
    REGION_US,
    _is_trading_day,
    freshness_for,
    region_currency,
    strip_exchange_suffix,
)
from services.symbol_resolver import region_hint

logger = logging.getLogger(__name__)

PROVIDER_NSE = "nse-fo-bhavcopy"
PROVIDER_US = "yfinance"

_FO_URL = "https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{ymd}_F_0000.csv.zip"
_OPTION_TYPES = frozenset({"IDO", "STO"})  # index options, stock options
_CACHE_KEY = "nse_fo_bhavcopy:{ymd}"
_CACHE_TTL_SECONDS = 7 * 24 * 3600.0
_EMPTY_MARKER = {"empty": True}

#: One packed option row: expiry ISO, strike, "call"/"put", OI, change in OI,
#: close, settle, volume, underlying price.
Packed = list[Any]


class OptionChainUnavailable(RuntimeError):
    """The source could not be reached, so absence cannot be told from a miss."""


@dataclass(frozen=True)
class FoBhavcopy:
    trade_date: date
    rows: dict[str, list[Packed]]


def parse_fo_bhavcopy(text: str) -> dict[str, list[Packed]]:
    """Option rows of an NSE F&O UDiFF bhavcopy, keyed by bare underlying symbol."""
    num = nse_bhavcopy._num
    rows: dict[str, list[Packed]] = {}
    for raw in csv.DictReader(io.StringIO(text)):
        row = {(k or "").strip(): (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}
        side = {"CE": "call", "PE": "put"}.get((row.get("OptnTp") or "").upper())
        strike = num(row.get("StrkPric"))
        symbol = (row.get("TckrSymb") or "").upper()
        if row.get("FinInstrmTp") not in _OPTION_TYPES or not side or strike is None or not symbol:
            continue
        try:
            expiry = date.fromisoformat(row.get("XpryDt") or "").isoformat()
        except ValueError:
            continue
        rows.setdefault(symbol, []).append(
            [
                expiry,
                strike,
                side,
                num(row.get("OpnIntrst")),
                num(row.get("ChngInOpnIntrst")),
                num(row.get("ClsPric")),
                num(row.get("SttlmPric")),
                num(row.get("TtlTradgVol")),
                num(row.get("UndrlygPric")),
            ]
        )
    return rows


def _cache_key(day: date) -> str:
    return _CACHE_KEY.format(ymd=day.strftime("%Y%m%d"))


async def _fetch_fo_day(day: date) -> tuple[str, dict[str, list[Packed]] | None]:
    """``("ok", rows)``, ``("missing", None)`` on a 404, else ``("failed", None)``."""
    try:
        resp = await nse_bhavcopy._throttled_get(_FO_URL.format(ymd=day.strftime("%Y%m%d")))
    except httpx.HTTPError as exc:
        logger.warning("option_chain: F&O bhavcopy request failed for %s (%s)", day, exc)
        return "failed", None
    if resp.status_code == 404:
        return "missing", None
    if resp.status_code != 200:
        logger.warning("option_chain: HTTP %s for the %s F&O bhavcopy", resp.status_code, day)
        return "failed", None
    rows = parse_fo_bhavcopy(nse_bhavcopy._decode_body(resp.content))
    if not rows:
        logger.warning("option_chain: %s F&O bhavcopy parsed to zero option rows", day)
        return "failed", None
    return "ok", rows


async def fetch_latest_fo(max_lookback_days: int = 7) -> FoBhavcopy | None:
    """The newest published NSE F&O bhavcopy, or ``None`` when it cannot be fetched.

    Weekends are skipped without a request; a 404 walks back a day (cached as a
    holiday only for a past non-trading day, never today, whose file lands
    after the close); a blocked or failed day stops the walk.
    """
    today = nse_bhavcopy._ist_today()
    for offset in range(max_lookback_days + 1):
        day = today - timedelta(days=offset)
        if day.weekday() >= 5:
            continue
        cached = await data_cache.get(_cache_key(day), _CACHE_TTL_SECONDS)
        if isinstance(cached, dict) and cached.get("rows"):
            return FoBhavcopy(trade_date=day, rows=cached["rows"])
        if cached is not None:
            continue  # a cached holiday marker
        status, rows = await _fetch_fo_day(day)
        if status == "ok" and rows:
            await data_cache.set(_cache_key(day), {"rows": rows})
            return FoBhavcopy(trade_date=day, rows=rows)
        if status == "failed":
            return None
        if day < today and not _is_trading_day(day, REGION_IN):
            await data_cache.set(_cache_key(day), _EMPTY_MARKER)
    logger.warning("option_chain: no F&O bhavcopy within %d days of %s", max_lookback_days, today)
    return None


def _pick_expiry(expiries: list[date], expiry: date | None, symbol: str) -> date:
    if expiry is None:
        return expiries[0]
    if expiry not in expiries:
        listed = ", ".join(d.isoformat() for d in expiries)
        raise ValueError(f"{symbol} has no {expiry.isoformat()} expiry; listed: {listed}")
    return expiry


def _chain(
    symbol: str,
    region: str,
    provider: str,
    as_of: date,
    expiries: list[date],
    expiry: date,
    underlying: float | None,
    contracts: list[OptionContract],
) -> OptionChain:
    return OptionChain(
        symbol=symbol,
        expiry=expiry,
        expiries=expiries,
        underlying_price=underlying,
        contracts=sorted(contracts, key=lambda c: (c.strike, c.option_type)),
        as_of=as_of,
        provider=provider,
        currency=region_currency(region),
        freshness=freshness_for(region, as_of, intraday=False).state,
    )


def _nse_chain(symbol: str, fo: FoBhavcopy, expiry: date | None) -> OptionChain:
    packed = fo.rows[symbol]
    expiries = sorted({date.fromisoformat(p[0]) for p in packed})
    chosen = _pick_expiry(expiries, expiry, symbol)
    contracts = [
        OptionContract(
            expiry=chosen,
            strike=p[1],
            option_type=p[2],
            open_interest=p[3],
            change_in_oi=p[4],
            last_price=p[5],
            settle_price=p[6],
            volume=p[7],
        )
        for p in packed
        if p[0] == chosen.isoformat()
    ]
    underlying = next((p[8] for p in packed if p[8] is not None), None)
    return _chain(
        symbol, REGION_IN, PROVIDER_NSE, fo.trade_date, expiries, chosen, underlying, contracts
    )


def _float(value: Any) -> float | None:
    """A finite float from a pandas cell, else ``None`` (NaN is not a value)."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out else None


def _yf_option_chain(symbol: str, expiry: date | None) -> dict[str, Any] | None:
    """yfinance's chain for one expiry (BLOCKING; the test seam for the US leg)."""
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    listed = [date.fromisoformat(d) for d in ticker.options]
    if not listed:
        return None
    chosen = _pick_expiry(listed, expiry, symbol)
    chain = ticker.option_chain(chosen.isoformat())
    return {
        "expiries": listed,
        "expiry": chosen,
        "calls": chain.calls.to_dict("records"),
        "puts": chain.puts.to_dict("records"),
        "underlying": (chain.underlying or {}).get("regularMarketPrice"),
    }


async def _us_chain(symbol: str, expiry: date | None) -> OptionChain | None:
    try:
        raw = await asyncio.to_thread(_yf_option_chain, symbol, expiry)
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001 - yfinance raises anything on a throttle
        raise OptionChainUnavailable(f"yfinance option chain failed for {symbol}: {exc}") from exc
    if raw is None:
        return None
    contracts: list[OptionContract] = []
    trade_dates: list[date] = []
    for side, records in (("call", raw["calls"]), ("put", raw["puts"])):
        for rec in records:
            strike = _float(rec.get("strike"))
            if strike is None:
                continue
            last_trade = rec.get("lastTradeDate")
            if hasattr(last_trade, "date"):
                trade_dates.append(last_trade.date())
            contracts.append(
                OptionContract(
                    expiry=raw["expiry"],
                    strike=strike,
                    option_type=side,
                    open_interest=_float(rec.get("openInterest")),
                    last_price=_float(rec.get("lastPrice")),
                    volume=_float(rec.get("volume")),
                    implied_volatility=_float(rec.get("impliedVolatility")),
                )
            )
    if not contracts:
        return None
    as_of = max(trade_dates) if trade_dates else date.today()
    return _chain(
        symbol,
        REGION_US,
        PROVIDER_US,
        as_of,
        raw["expiries"],
        raw["expiry"],
        _float(raw["underlying"]),
        contracts,
    )


async def get_option_chain(symbol: str, expiry: date | None = None) -> OptionChain | None:
    """One expiry of ``symbol``'s option chain (the nearest when ``expiry`` is omitted).

    ``None`` when the symbol has no listed options (not an F&O underlying, no
    US options). Raises ``ValueError`` for an expiry the source does not list
    and :class:`OptionChainUnavailable` when the source could not be read.
    An IN-pinned symbol never falls through to the US leg; an ambiguous bare
    ticker (NIFTY, INFY) tries the NSE F&O file first.
    """
    region = region_hint(symbol)
    bare = strip_exchange_suffix(symbol)
    nse_failed = False
    if region != REGION_US:
        fo = await fetch_latest_fo()
        if fo is None:
            nse_failed = True
        elif bare in fo.rows:
            return _nse_chain(bare, fo, expiry)
        if region == REGION_IN:
            if nse_failed:
                raise OptionChainUnavailable("the NSE F&O bhavcopy could not be fetched")
            return None
    chain = await _us_chain(bare, expiry)
    if chain is None and nse_failed:
        raise OptionChainUnavailable("the NSE F&O bhavcopy could not be fetched")
    return chain


__all__ = [
    "PROVIDER_NSE",
    "PROVIDER_US",
    "OptionChainUnavailable",
    "fetch_latest_fo",
    "get_option_chain",
    "parse_fo_bhavcopy",
]
