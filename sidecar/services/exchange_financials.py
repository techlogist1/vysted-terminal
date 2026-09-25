"""Exchange-filed results — the independent India witness (R15-DATA-014/027/076, D-B7-1).

Yahoo's ``totalRevenue``/``netIncomeToCommon``/``trailingEps`` and its growth
scalars were only ever checked against Yahoo's own statements, so a Yahoo-wide
error (DAL: 2.76 Cr served, 9.97 Cr filed) passed every check. This module
reads the results the company FILED with its exchange:

  * an NSE listing (``.NS``): the SEBI Integrated Filing (Financials) index
    (:func:`services.nse_provider.get_financial_filings`) and each filing's
    XBRL (:func:`services.nse_provider.get_archive_text`). Observed live
    (2026-09-24, FUSION / DHANBANK): the figures are raw INR on the
    ``in-capmkt`` taxonomy; a dimensionless duration context per reported
    period (``OneD`` the quarter, ``FourD`` the year on a Q4 filing) carries
    ``RevenueFromOperations`` (banks: ``Income``), ``ProfitLossForPeriod``
    (banks: ``ProfitLossForThePeriod``) and the basic EPS.
  * a BSE listing (``.BO``): the BSE result pages' JSON
    (:func:`services.bse_provider.get_results_summary` names the latest
    quarter's id and page format; ``results.aspx`` ids step 1.00 per quarter,
    ``NBFC.aspx`` ids step 4), figures in INR million.

Only quarters and half-years are kept (a fiscal-year row is not a trailing
period). :func:`get_filed_periods` never raises: any fetch or parse failure,
a partial walk included, is ``None`` so a caller never reads a gap the lane
itself made as a filing gap. Results are cached per listing for a day.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from xml.etree import ElementTree as ET

from services import bse_provider, locale, nse_provider, symbol_resolver
from services.witness import is_india_listing

logger = logging.getLogger(__name__)

VENUE_NSE = "nse"
VENUE_BSE = "bse"

#: Filed results change quarterly; a day keeps the 1 req/s NSE lane off the
#: hot path while a new filing is picked up the next day.
_TTL_SECONDS = 24 * 60 * 60
#: Periods fetched per listing: four for the trailing year plus the one a year
#: before the newest (MRQ-YoY).
_PERIODS_WANTED = 5
#: A period boundary is contiguous with the next period's start within this slack.
_CONTIGUITY_DAYS = 5
#: The year-ago period is the same-length one ending 365 days (± this) earlier.
_YEAR_AGO_WINDOW_DAYS = 45

_NSE_REVENUE = ("RevenueFromOperations", "Income")
_NSE_PROFIT = (
    "ProfitOrLossAttributableToOwnersOfParent",
    "ProfitLossForPeriod",
    "ProfitLossForThePeriod",
)
_NSE_EPS = (
    "BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations",
    "BasicEarningsPerShareAfterExtraordinaryItems",
    "BasicEarningsLossPerShareFromContinuingOperations",
)
_BSE_MILLION = 1_000_000.0
_BSE_QTR_RE = re.compile(r"/corporates/(results|NBFC)\.aspx\?.*?qtr=([0-9.]+)", re.IGNORECASE)


@dataclass(frozen=True)
class FiledPeriod:
    """One filed quarter or half-year. Sizes in INR, EPS in INR per share."""

    start: date
    end: date
    revenue: float | None
    net_profit: float | None
    eps: float | None
    filed: date | None = None
    url: str | None = None

    @property
    def months(self) -> int:
        return round((self.end - self.start).days / 30.44)


@dataclass(frozen=True)
class FiledPeriods:
    """A listing's filed periods on one basis, newest first."""

    venue: str
    basis: str
    periods: tuple[FiledPeriod, ...]

    def trailing(self) -> tuple[FiledPeriod, ...] | None:
        """The contiguous filed periods covering the 12 months to the newest
        period end (four quarters, two halves), or ``None`` when the filings
        leave a hole in that year (a half-yearly filer's missing quarter)."""
        chain: list[FiledPeriod] = []
        months = 0
        for period in self.periods:
            if months >= 12:
                break
            if chain and abs((chain[-1].start - period.end).days - 1) > _CONTIGUITY_DAYS:
                if period.end >= chain[-1].start:
                    continue  # an overlapping longer period ending on the same date
                return None
            chain.append(period)
            months += period.months
        return tuple(chain) if months == 12 else None

    def cadence(self) -> str:
        """``quarterly`` when four filed quarters cover the trailing year, else
        ``half-yearly`` (a half-year period, or a quarter the exchange holds no
        filing for)."""
        trail = self.trailing()
        if trail is not None and all(p.months == 3 for p in trail):
            return "quarterly"
        return "half-yearly"

    def year_ago(self, period: FiledPeriod) -> FiledPeriod | None:
        """The same-length period ending about a year before ``period``."""
        for other in self.periods:
            off = abs((period.end - other.end).days - 365)
            if other.months == period.months and off <= _YEAR_AGO_WINDOW_DAYS:
                return other
        return None


# --- NSE lane ------------------------------------------------------------------


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _float(text: object) -> float | None:
    try:
        return float(str(text).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def parse_nse_xbrl(text: str) -> list[FiledPeriod]:
    """Every dimensionless 3- or 6-month period an Integrated Filing XBRL reports."""
    root = ET.fromstring(text.encode())
    spans: dict[str, tuple[date, date]] = {}
    for ctx in root.iter():
        if _local(ctx.tag) != "context" or any(_local(e.tag) == "scenario" for e in ctx.iter()):
            continue
        dates = {_local(e.tag): (e.text or "").strip() for e in ctx.iter()}
        if "startDate" in dates and "endDate" in dates:
            spans[ctx.get("id", "")] = (
                date.fromisoformat(dates["startDate"]),
                date.fromisoformat(dates["endDate"]),
            )
    facts: dict[str, dict[str, float]] = {}
    for el in root:
        ref = el.get("contextRef")
        value = _float(el.text)
        if ref in spans and value is not None:
            facts.setdefault(ref, {})[_local(el.tag)] = value

    def first(values: dict[str, float], names: tuple[str, ...]) -> float | None:
        return next((values[n] for n in names if n in values), None)

    periods = []
    for ref, (start, end) in spans.items():
        values = facts.get(ref, {})
        revenue = first(values, _NSE_REVENUE)
        period = FiledPeriod(
            start, end, revenue, first(values, _NSE_PROFIT), first(values, _NSE_EPS)
        )
        if revenue is not None and period.months in (3, 6):
            periods.append(period)
    return periods


def _nse_day(value: object) -> date | None:
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y"):
        try:
            return datetime.strptime(str(value).strip().title(), fmt).date()
        except ValueError:
            continue
    return None


def _nse_rows(bare: str) -> list[dict]:
    return [
        r
        for r in nse_provider.get_financial_filings(bare)
        if r.get("consolidated") in ("Standalone", "Consolidated")
        and str(r.get("xbrl") or "").endswith(".xml")
        and _nse_day(r.get("qe_Date"))
    ]


def _nse_basis(rows: list[dict]) -> str:
    """``Consolidated`` when the newest filed quarter has a consolidated filing."""
    newest = max(_nse_day(r["qe_Date"]) for r in rows)
    has_consolidated = any(
        r["consolidated"] == "Consolidated" and _nse_day(r["qe_Date"]) == newest for r in rows
    )
    return "Consolidated" if has_consolidated else "Standalone"


def _nse_periods(bare: str) -> FiledPeriods | None:
    rows = _nse_rows(bare)
    if not rows:
        return None
    basis = _nse_basis(rows)
    # A revision supersedes the original filing for the same quarter.
    latest: dict[date, dict] = {}
    for row in sorted(rows, key=lambda r: _nse_day(r.get("creation_Date")) or date.min):
        if row["consolidated"] == basis:
            latest[_nse_day(row["qe_Date"])] = row
    periods: dict[tuple[date, date], FiledPeriod] = {}
    for quarter_end in sorted(latest, reverse=True)[:_PERIODS_WANTED]:
        row = latest[quarter_end]
        for p in parse_nse_xbrl(nse_provider.get_archive_text(row["xbrl"])):
            filed = _nse_day(row.get("broadcast_Date") or row.get("creation_Date"))
            periods.setdefault(
                (p.start, p.end),
                FiledPeriod(p.start, p.end, p.revenue, p.net_profit, p.eps, filed, row["xbrl"]),
            )
    return _assemble(VENUE_NSE, basis.lower(), periods.values())


# --- BSE lane ------------------------------------------------------------------


def _bse_day(value: object) -> date | None:
    try:
        return datetime.strptime(str(value).strip(), "%d-%b-%y").date()
    except ValueError:
        return None


def _month_end(label: object) -> date | None:
    """``"Jun-26"`` → 2026-06-30."""
    try:
        first = datetime.strptime(str(label).strip(), "%b-%y").date()
    except ValueError:
        return None
    return (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


def _row(rows: list[dict], key: str, *names: str) -> dict | None:
    return next((r for r in rows if str(r.get(key) or "").strip() in names), None)


def _million(value: object) -> float | None:
    number = _float(value)
    return number * _BSE_MILLION if number is not None else None


def _bse_detail_period(code: str, qtr: str, url: str) -> FiledPeriod | None:
    rows = bse_provider.get_result_detail(code, qtr)

    def value(*names: str) -> object:
        row = _row(rows, "fld_desc", *names)
        return row.get("Value") if row else None

    start, end = _bse_day(value("Date Begin")), _bse_day(value("Date End"))
    if start is None or end is None:
        return None  # the exchange holds no filing under this id
    eps = _float(value("Basic EPS for continuing operation", "Basic EPS"))
    return FiledPeriod(
        start,
        end,
        _million(value("Net Sales/Revenue From Operations", "Revenue from Operations")),
        _million(value("Net Profit")),
        eps,
        url=url,
    )


def _bse_nbfc_periods(code: str, qtr_id: int, url: str) -> list[FiledPeriod]:
    rows = bse_provider.get_nbfc_profit_loss(code, qtr_id)
    revenue = _row(rows, "HeaderName", "Total Revenue from operations")
    profit = next(
        (
            r
            for r in rows
            if str(r.get("HeaderName", "")).startswith("Profit / (loss) for the period")
        ),
        None,
    )
    eps = next(
        (r for r in rows if str(r.get("HeaderName", "")).strip().lower().startswith("basic")),
        None,
    )
    periods = []
    for label_key, value_key in (("CurYear", "CurrentValue"), ("PrevYear", "PrevValue")):
        end = _month_end((revenue or {}).get(label_key))
        if end is None or revenue is None:
            continue
        start = date(end.year - (end.month <= 2), (end.month - 3) % 12 + 1, 1)
        periods.append(
            FiledPeriod(
                start,
                end,
                _million(revenue.get(value_key)),
                _million((profit or {}).get(value_key)),
                _float((eps or {}).get(value_key)),
                url=url,
            )
        )
    return periods


def _bse_periods(bare: str) -> FiledPeriods | None:
    code = symbol_resolver.bse_scrip_code(bare)
    if not code:
        return None
    links = (bse_provider.get_results_summary(code).get("resultinS") or [{}])[0]
    match = _BSE_QTR_RE.search(str(links.get("LLQ") or ""))
    if match is None:
        return None  # a result format this lane does not read (bank, insurer)
    page, latest = match.group(1).lower(), match.group(2)
    url = str(links["LLQ"])
    found: list[FiledPeriod] = []
    if page == "nbfc":
        qtr_id = int(float(latest))
        for step in range(0, 3):  # each id answers its quarter and the one before
            found.extend(_bse_nbfc_periods(code, qtr_id - 8 * step, url))
    else:
        for step in range(_PERIODS_WANTED):
            period = _bse_detail_period(code, f"{float(latest) - step:.2f}", url)
            if period is not None:
                found.append(period)
    return _assemble(VENUE_BSE, "standalone", {(p.start, p.end): p for p in found}.values())


def _assemble(venue: str, basis: str, periods: Iterable[FiledPeriod]) -> FiledPeriods | None:
    # Newest first; of two periods ending together, the quarter before the half.
    ordered = sorted(periods, key=lambda p: (p.end, -p.months), reverse=True)
    return FiledPeriods(venue, basis, tuple(ordered)) if ordered else None


# --- entry point ---------------------------------------------------------------

_cache: dict[str, tuple[float, FiledPeriods]] = {}
_basis_cache: dict[str, tuple[float, str | None]] = {}


def reset_for_tests() -> None:
    _cache.clear()
    _basis_cache.clear()


def _fetch(listing: str) -> FiledPeriods | None:
    bare = locale.strip_exchange_suffix(listing).removesuffix("-SM")
    if listing.upper().endswith(".NS"):
        return _nse_periods(bare)
    return _bse_periods(bare)


def _fetch_and_cache(key: str) -> FiledPeriods | None:
    """Runs inside the ``to_thread`` worker: the cache write lives here, not
    after the ``await``, so a caller cancelled mid-fetch (FAST's budget box)
    still lands the result the worker thread finishes computing — otherwise
    every later call repeats the same paced NSE walk (rc1-battery-4:1)."""
    filed = _fetch(key)
    if filed is not None:
        _cache[key] = (time.monotonic(), filed)
    return filed


async def get_filed_periods(listing: str) -> FiledPeriods | None:
    """The exchange-filed periods for an NSE/BSE ``listing`` (``FUSION.NS``,
    ``DAL.BO``), or ``None`` — any other listing, no filings, or any failure.
    Never raises; a success is cached for a day."""
    if not is_india_listing(listing):
        return None
    key = listing.strip().upper()
    hit = _cache.get(key)
    if hit is not None and time.monotonic() - hit[0] < _TTL_SECONDS:
        return hit[1]
    try:
        return await asyncio.to_thread(_fetch_and_cache, key)
    except Exception as exc:  # noqa: BLE001 — a witness must never break the payload
        logger.debug("exchange-filed results unavailable for %s: %s", listing, exc)
        return None


def _fetch_basis(listing: str) -> str | None:
    bare = locale.strip_exchange_suffix(listing).removesuffix("-SM")
    if listing.endswith(".NS") or symbol_resolver.dual_listed_bse_code(bare):
        rows = _nse_rows(bare)
        return _nse_basis(rows).lower() if rows else None
    code = symbol_resolver.bse_scrip_code(bare)
    if not code:
        return None
    links = (bse_provider.get_results_summary(code).get("resultinS") or [{}])[0]
    # BSE's result pages publish the standalone result only.
    return "standalone" if any(links.get(k) for k in ("LLQ", "LSQ", "LFY")) else None


async def filed_basis(listing: str) -> str | None:
    """The accounting basis an NSE/BSE ``listing`` files its results on
    (R15-DATA-054), which is the basis a provider serving the company's
    primary statements (Yahoo) uses: ``"consolidated"`` when the newest
    NSE-filed quarter carries a consolidated filing, else ``"standalone"``. A
    listing the company also has on NSE (a dual-listed ``.BO``) reads the NSE
    index; a BSE-only listing is ``"standalone"`` when BSE holds a result for
    it. ``None`` for any other listing, no filing, or any failure — never a
    default. Never raises; cached for a day."""
    if not is_india_listing(listing):
        return None
    key = listing.strip().upper()
    hit = _basis_cache.get(key)
    if hit is not None and time.monotonic() - hit[0] < _TTL_SECONDS:
        return hit[1]
    filed = _cache.get(key)
    fresh = filed is not None and time.monotonic() - filed[0] < _TTL_SECONDS
    if fresh and filed[1].venue == VENUE_NSE:
        return filed[1].basis  # the NSE lane already read the same index today
    try:
        basis = await asyncio.to_thread(_fetch_basis, key)
    except Exception as exc:  # noqa: BLE001 — a label must never break the payload
        logger.debug("filed basis unavailable for %s: %s", listing, exc)
        return None
    _basis_cache[key] = (time.monotonic(), basis)
    return basis


__all__ = [
    "FiledPeriod",
    "FiledPeriods",
    "filed_basis",
    "get_filed_periods",
    "parse_nse_xbrl",
    "reset_for_tests",
]
