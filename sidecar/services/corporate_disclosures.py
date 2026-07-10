"""Corporate disclosures — merged BSE+NSE announcements, results, shareholding.

R7 Component 3. Models the RAW exchange feeds into the typed shapes in
:mod:`models.announcements` for the ``/disclosures`` router and the
``corporate_announcements`` / ``shareholding_pattern`` agent tools:

* **Announcements** — merged from BOTH exchange feeds and deduplicated by
  ``(symbol, headline-hash, date)``, newest first:

  - NSE: :func:`services.nse_provider.get_corporate_announcements` (the
    curl_cffi cookie-danced lane; observed item keys ``an_dt``,
    ``attchmntFile``, ``attchmntText``, ``desc``, ``sort_date``, ``symbol`` —
    fixtures under ``tests/fixtures/nse/``).
  - BSE: the public ``AnnSubCategoryGetData`` JSON API, keyed by the numeric
    scrip code from the bundled master. Shape OBSERVED LIVE (scratch curl_cffi
    probe, 2026-06-10 IST, scrip 500325 RELIANCE; trimmed verbatim fixture at
    ``tests/fixtures/bse/ann_sub_category_get_data.json``): ``{"Table": [
    {NEWSID, SCRIP_CD, NEWSSUB, HEADLINE, MORE, CATEGORYNAME, SUBCATNAME,
    NEWS_DT/DT_TM "2026-06-09T19:44:02.21" (IST naive), ATTACHMENTNAME,
    SLONGNAME, ...}], "Table1": [{"ROWCNT": n}]}``. Attachments resolve under
    ``https://www.bseindia.com/xml-data/corpfiling/AttachLive/<ATTACHMENTNAME>``
    (verified live: 200 ``application/pdf``; the ``AttachHis`` variant 404s for
    a current filing).

  One exchange failing degrades honestly to a partial merge (the failure is
  recorded in ``errors``); BOTH failing raises so the caller never sees a
  silently-empty feed.

* **Results calendar** — the NSE ``event-calendar`` feed (board meetings,
  results, dividends), parsed dates, newest first.

* **Shareholding** — the NSE quarterly shareholding MASTER (promoter+group,
  public, employee-trust percentages + the XBRL filing URL). The FII/DII split
  lives only inside the XBRL, so those fields are honest ``None`` — never
  fabricated; the ``xbrl_url`` is returned so deeper analysis can pull it.

All public functions are synchronous (matching every provider the registry
drives); async callers wrap them in ``asyncio.to_thread``. Network is reached
through two seams tests monkeypatch: the :mod:`services.nse_provider` raw
accessors and :func:`_bse_get_json`.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import UTC, date, datetime, timedelta

from models.announcements import (
    Announcement,
    AnnouncementsResponse,
    ResultsCalendarResponse,
    ResultsEvent,
    ShareholdingPattern,
    ShareholdingResponse,
)
from services import locale, nse_provider, symbol_resolver
from services.errors import ProviderError

logger = logging.getLogger(__name__)

EXCHANGE_NSE = "NSE"
EXCHANGE_BSE = "BSE"
EXCHANGES = (EXCHANGE_NSE, EXCHANGE_BSE)

DEFAULT_LIMIT = 50
MAX_LIMIT = 200

# BSE announcements API (observed live 2026-06-10 — module docstring).
_BSE_ANN_URL = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
_BSE_ATTACHMENT_BASE = "https://www.bseindia.com/xml-data/corpfiling/AttachLive/"
# The announcements window requested from BSE (the feed is date-bounded; NSE's
# returns full history trimmed client-side, so a month keeps the lanes roughly
# comparable while staying one cheap request).
_BSE_ANN_WINDOW_DAYS = 30
# Browser headers for the BSE API (it serves an empty/blocked payload to an
# obvious bot — same posture as bse_provider; TLS/UA via impersonate="chrome").
_BSE_HEADERS = {
    "Referer": "https://www.bseindia.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}
_BSE_TIMEOUT = 20.0


def _ist():  # noqa: ANN202 - ZoneInfo
    return locale.market_timezone(locale.REGION_IN)


# ---------------------------------------------------------------------------
# BSE announcements lane (the network seam tests monkeypatch).
# ---------------------------------------------------------------------------


def _bse_get_json(url: str, params: dict[str, str]) -> object:
    """One Chrome-impersonated GET returning parsed JSON (the test seam)."""
    from curl_cffi import requests as curl_requests

    session = curl_requests.Session(impersonate="chrome")
    try:
        try:
            resp = session.get(url, params=params, headers=_BSE_HEADERS, timeout=_BSE_TIMEOUT)
        except Exception as exc:
            raise ProviderError(f"bse announcements: transport failure: {exc}") from exc
        if resp.status_code != 200:
            raise ProviderError(f"bse announcements: HTTP {resp.status_code}")
        try:
            return resp.json()
        except Exception as exc:
            raise ProviderError(f"bse announcements: non-JSON body: {exc}") from exc
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001 - best-effort close
            pass


def _fetch_bse_announcements(bare: str, limit: int) -> list[Announcement]:
    """The BSE lane — ``AnnSubCategoryGetData`` rows for the last month."""
    code = symbol_resolver.bse_scrip_code(bare)
    if not code:
        raise ProviderError(f"bse announcements: no scrip code for {bare!r} in the master")
    today = datetime.now(tz=UTC).astimezone(_ist()).date()
    params = {
        "pageno": "1",
        "strCat": "-1",
        "strPrevDate": (today - timedelta(days=_BSE_ANN_WINDOW_DAYS)).strftime("%Y%m%d"),
        "strScrip": str(code),
        "strSearch": "P",
        "strToDate": today.strftime("%Y%m%d"),
        "strType": "C",
        "subcategory": "-1",
    }
    payload = _bse_get_json(_BSE_ANN_URL, params)
    table = payload.get("Table") if isinstance(payload, dict) else None
    if not isinstance(table, list):
        raise ProviderError(f"bse announcements: malformed payload for {bare!r}")
    items: list[Announcement] = []
    for row in table:
        if not isinstance(row, dict):
            continue
        item = _bse_row_to_announcement(bare, row)
        if item is not None:
            items.append(item)
    return items[: max(limit, 0)]


def _bse_row_to_announcement(bare: str, row: dict) -> Announcement | None:
    """Observed BSE row → :class:`Announcement` (None for a headline-less row)."""
    headline = _clean(row.get("NEWSSUB")) or _clean(row.get("HEADLINE"))
    if not headline:
        return None
    category = _clean(row.get("CATEGORYNAME")) or _clean(row.get("SUBCATNAME"))
    attachment = _clean(row.get("ATTACHMENTNAME"))
    return Announcement(
        # The BSE payload carries only the numeric SCRIP_CD + the long company
        # name — stamp the requested bare ticker (mirrors bse_provider quotes).
        symbol=bare,
        exchange=EXCHANGE_BSE,
        headline=headline,
        category=category,
        attachment_url=(_BSE_ATTACHMENT_BASE + attachment) if attachment else None,
        ts=_parse_bse_ts(row),
    )


def _parse_bse_ts(row: dict) -> datetime | None:
    """``NEWS_DT``/``DT_TM`` are IST-naive ISO strings ("2026-06-09T19:44:02.21")."""
    for key in ("NEWS_DT", "DT_TM", "News_submission_dt", "DissemDT"):
        raw = _clean(row.get(key))
        if not raw:
            continue
        try:
            return datetime.fromisoformat(raw).replace(tzinfo=_ist())
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# NSE announcements lane (rides the nse_provider raw accessor).
# ---------------------------------------------------------------------------


def _fetch_nse_announcements(bare: str, limit: int) -> list[Announcement]:
    rows = nse_provider.get_corporate_announcements(bare, limit=limit)
    items: list[Announcement] = []
    for row in rows:
        item = _nse_row_to_announcement(bare, row)
        if item is not None:
            items.append(item)
    return items


def _nse_row_to_announcement(bare: str, row: dict) -> Announcement | None:
    """Observed NSE row → :class:`Announcement` (None for a headline-less row).

    ``attchmntText`` is the disclosure text (the substantive headline);
    ``desc`` is the category label ("Updates") and the fallback headline for a
    text-less row.
    """
    headline = _clean(row.get("attchmntText")) or _clean(row.get("desc"))
    if not headline:
        return None
    return Announcement(
        symbol=_clean(row.get("symbol")) or bare,
        exchange=EXCHANGE_NSE,
        headline=headline,
        category=_clean(row.get("desc")),
        attachment_url=_clean(row.get("attchmntFile")) or None,
        ts=_parse_nse_ts(row),
    )


def _parse_nse_ts(row: dict) -> datetime | None:
    """``sort_date`` ("2026-06-09 19:45:31") primary; ``an_dt`` ("09-Jun-2026
    19:45:31") fallback. Both are IST wall-clock."""
    raw = _clean(row.get("sort_date"))
    if raw:
        try:
            return datetime.fromisoformat(raw).replace(tzinfo=_ist())
        except ValueError:
            pass
    raw = _clean(row.get("an_dt"))
    if raw:
        try:
            return datetime.strptime(raw, "%d-%b-%Y %H:%M:%S").replace(tzinfo=_ist())
        except ValueError:
            pass
    return None


# ---------------------------------------------------------------------------
# The merged feed.
# ---------------------------------------------------------------------------


def _dedup_key(item: Announcement) -> tuple[str, str, str]:
    """The brief's dedup key: ``(symbol, headline-hash, date)``.

    The headline is whitespace-collapsed + casefolded before hashing so a
    re-dissemination with cosmetic spacing differences still collapses; the
    date component is the announcement's IST calendar day (timestamp-less
    items use an empty day and only collapse on identical text).
    """
    normalized = re.sub(r"\s+", " ", item.headline).strip().casefold()
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]
    day = item.ts.astimezone(_ist()).date().isoformat() if item.ts else ""
    return (item.symbol.upper(), digest, day)


def get_announcements(
    symbol: str, exchange: str | None = None, limit: int = DEFAULT_LIMIT
) -> AnnouncementsResponse:
    """Merged BSE+NSE corporate announcements for ``symbol``, newest first.

    ``exchange`` filters to one feed ("NSE"/"BSE"); ``None`` merges both.
    Lanes the symbol is not listed on are skipped without error; a lane that
    IS applicable but fails is recorded in ``errors`` and the partial merge is
    served. Every applicable lane failing (or no lane applying) raises
    :class:`ProviderError` — the feed is never silently empty-on-failure.
    """
    bare = locale.strip_exchange_suffix(symbol.strip().upper())
    if not bare:
        raise ProviderError("disclosures: empty symbol")
    if exchange is not None and exchange not in EXCHANGES:
        raise ProviderError(f"disclosures: unknown exchange {exchange!r} (use NSE or BSE)")
    limit = max(1, min(int(limit), MAX_LIMIT))

    lanes: list[tuple[str, bool]] = [
        (EXCHANGE_NSE, symbol_resolver.is_nse_symbol(bare)),
        (EXCHANGE_BSE, symbol_resolver.is_bse_symbol(bare)),
    ]
    applicable = [name for name, listed in lanes if listed and exchange in (None, name)]
    if not applicable:
        wanted = exchange or "NSE/BSE"
        raise ProviderError(f"disclosures: {bare!r} is not a known {wanted} instrument")

    merged: list[Announcement] = []
    sources: list[str] = []
    errors: dict[str, str] = {}
    for name in applicable:  # NSE first — it wins a cross-feed dedup collision
        fetch = _fetch_nse_announcements if name == EXCHANGE_NSE else _fetch_bse_announcements
        try:
            merged.extend(fetch(bare, limit))
            sources.append(name)
        except ProviderError as exc:
            logger.debug("disclosures: %s announcements failed for %s: %s", name, bare, exc)
            errors[name] = str(exc)
    if not sources:
        detail = "; ".join(f"{name}: {msg}" for name, msg in errors.items())
        raise ProviderError(
            f"disclosures: every announcement source failed for {bare!r} ({detail})"
        )

    seen: set[tuple[str, str, str]] = set()
    deduped: list[Announcement] = []
    for item in merged:
        key = _dedup_key(item)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    floor = datetime.min.replace(tzinfo=UTC)
    deduped.sort(key=lambda a: a.ts or floor, reverse=True)
    trimmed = deduped[:limit]
    return AnnouncementsResponse(
        symbol=bare,
        exchange=exchange,
        count=len(trimmed),
        announcements=trimmed,
        sources=sources,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Results calendar (NSE event-calendar feed).
# ---------------------------------------------------------------------------


def get_results_calendar(symbol: str) -> ResultsCalendarResponse:
    """Results/board-meeting events for ``symbol``, newest first."""
    bare = locale.strip_exchange_suffix(symbol.strip().upper())
    if not bare:
        raise ProviderError("disclosures: empty symbol")
    rows = nse_provider.get_results_calendar(bare)
    events: list[ResultsEvent] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        purpose = _clean(row.get("purpose"))
        if not purpose:
            continue
        events.append(
            ResultsEvent(
                symbol=_clean(row.get("symbol")) or bare,
                company=_clean(row.get("company")),
                purpose=purpose,
                description=_clean(row.get("bm_desc")),
                date=_parse_day(row.get("date")),
            )
        )
    events.sort(key=lambda e: e.date or date.min, reverse=True)
    return ResultsCalendarResponse(symbol=bare, count=len(events), events=events)


# ---------------------------------------------------------------------------
# Shareholding pattern (NSE quarterly master).
# ---------------------------------------------------------------------------


def get_shareholding(symbol: str) -> ShareholdingResponse:
    """Quarterly shareholding patterns for ``symbol``, newest quarter first.

    NSE-first, BSE-fallback: a dual-listed name is served from the NSE quarterly
    master (promoter/public/employee-trust percentages; FII/DII stay ``None`` —
    that split lives only in the linked NSE XBRL); a BSE-only name — or one the
    NSE lane cannot serve — falls back to the BSE lane, which parses the SEBI
    XBRL and additionally carries the institutions total + FII/DII split. Every
    pattern carries a ``source`` label ("NSE"/"BSE") and its as-of quarter; a
    lane that is applicable but fails is recorded and the next lane is tried,
    and no figure is ever fabricated.
    """
    bare = locale.strip_exchange_suffix(symbol.strip().upper())
    if not bare:
        raise ProviderError("disclosures: empty symbol")
    lanes: list[tuple[str, bool, object]] = [
        (EXCHANGE_NSE, symbol_resolver.is_nse_symbol(bare), _nse_shareholding),
        (EXCHANGE_BSE, symbol_resolver.is_bse_symbol(bare), _bse_shareholding),
    ]
    applicable = [(name, fetch) for name, listed, fetch in lanes if listed]
    if not applicable:
        raise ProviderError(f"disclosures: {bare!r} is not a known NSE/BSE instrument")

    errors: dict[str, str] = {}
    for name, fetch in applicable:  # NSE first — it wins for a dual-listed name
        try:
            patterns = fetch(bare)
        except ProviderError as exc:
            logger.debug("disclosures: %s shareholding failed for %s: %s", name, bare, exc)
            errors[name] = str(exc)
            continue
        if patterns:
            patterns.sort(key=lambda p: p.quarter_end, reverse=True)
            return ShareholdingResponse(symbol=bare, count=len(patterns), patterns=patterns)
    if errors:
        detail = "; ".join(f"{name}: {msg}" for name, msg in errors.items())
        raise ProviderError(
            f"disclosures: every shareholding source failed for {bare!r} ({detail})"
        )
    # Every applicable lane was reachable but carried no pattern — honest empty.
    return ShareholdingResponse(symbol=bare, count=0, patterns=[])


def _nse_shareholding(bare: str) -> list[ShareholdingPattern]:
    """The NSE quarterly-master lane → typed patterns (source ``"NSE"``)."""
    patterns: list[ShareholdingPattern] = []
    for row in nse_provider.get_shareholding_master(bare):
        if not isinstance(row, dict):
            continue
        quarter_end = _parse_day(row.get("date"))
        if quarter_end is None:
            continue  # a quarter-less row is unplottable — skip, never guess
        patterns.append(
            ShareholdingPattern(
                symbol=_clean(row.get("symbol")) or bare,
                quarter_end=quarter_end,
                promoter_percent=_pct(row.get("pr_and_prgrp")),
                fii_percent=None,
                dii_percent=None,
                institutions_percent=None,
                public_percent=_pct(row.get("public_val")),
                employee_trusts_percent=_pct(row.get("employeeTrusts")),
                submission_date=_parse_day(row.get("submissionDate")),
                xbrl_url=_clean(row.get("xbrl")) or None,
                source=EXCHANGE_NSE,
            )
        )
    return patterns


def _bse_shareholding(bare: str) -> list[ShareholdingPattern]:
    """The BSE SEBI-XBRL lane → typed patterns (source ``"BSE"``)."""
    from services import bse_provider

    patterns: list[ShareholdingPattern] = []
    for row in bse_provider.get_shareholding(bare):
        if not isinstance(row, dict):
            continue
        quarter_end = row.get("quarter_end")
        if not isinstance(quarter_end, date):
            continue
        submission = row.get("submission_date")
        patterns.append(
            ShareholdingPattern(
                symbol=bare,
                quarter_end=quarter_end,
                promoter_percent=_as_float(row.get("promoter_percent")),
                fii_percent=_as_float(row.get("fii_percent")),
                dii_percent=_as_float(row.get("dii_percent")),
                institutions_percent=_as_float(row.get("institutions_percent")),
                public_percent=_as_float(row.get("public_percent")),
                employee_trusts_percent=None,
                submission_date=submission if isinstance(submission, date) else None,
                xbrl_url=_clean(row.get("xbrl_url")) or None,
                source=EXCHANGE_BSE,
            )
        )
    return patterns


# ---------------------------------------------------------------------------
# Small parse helpers.
# ---------------------------------------------------------------------------


def _clean(value: object) -> str | None:
    """A stripped non-empty string, else ``None``."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _parse_day(value: object) -> date | None:
    """Parse the exchanges' day spellings: ``31-MAR-2026`` / ``05-Aug-2005`` /
    ISO ``2026-03-31``. ``None`` when absent/unparseable."""
    raw = _clean(value)
    if not raw:
        return None
    for parser in (
        lambda s: datetime.strptime(s, "%d-%b-%Y").date(),  # %b matching is case-insensitive
        date.fromisoformat,
    ):
        try:
            return parser(raw)
        except ValueError:
            continue
    return None


def _pct(value: object) -> float | None:
    """Coerce a percentage cell ("50.01") to ``float | None``."""
    if value is None or value == "" or value == "-":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: object) -> float | None:
    """A numeric (non-bool) value as float, else ``None`` — for the BSE lane's
    already-typed rows (never coerces a bool or a string into a percentage)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


__all__ = [
    "DEFAULT_LIMIT",
    "EXCHANGES",
    "EXCHANGE_BSE",
    "EXCHANGE_NSE",
    "MAX_LIMIT",
    "get_announcements",
    "get_results_calendar",
    "get_shareholding",
]
