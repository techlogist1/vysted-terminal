"""Corporate disclosures — merged BSE+NSE announcements, results, shareholding.

R7 Component 3. Models the RAW exchange feeds into the typed shapes in
:mod:`models.announcements` for the ``/disclosures`` router and the
``corporate_announcements`` / ``shareholding_pattern`` agent tools:

* **Announcements** — merged from BOTH exchange feeds, newest first. A
  within-feed re-dissemination collapses on ``(symbol, body-prefix-hash,
  date)``; an NSE item and a BSE item of one filing pair on the same day, a
  short dissemination gap and similar text or one unambiguous exchange
  category (:func:`_pair_cross_feed`):

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
    SLONGNAME, PDFFLAG, ...}], "Table1": [{"ROWCNT": n}]}`` — ``ROWCNT`` is the
    row total for the requested window, served ``pageno`` by ``pageno``.
    Attachments resolve under ``.../corpfiling/AttachLive/<ATTACHMENTNAME>``
    when ``PDFFLAG`` is 0 (verified live: 200 ``application/pdf``, while the
    ``AttachHis`` variant 404s) and under ``.../corpfiling/AttachHis/`` when it
    is 1 (filings live-probed 404 on ``AttachLive`` and 200 on ``AttachHis``).

  One exchange failing degrades honestly to a partial merge (the failure is
  recorded in ``errors``); BOTH failing raises so the caller never sees a
  silently-empty feed. Each served lane states the date range its items are
  complete for in ``windows`` (the BSE feed is date-bounded, NSE's is not).

* **Results calendar** — the NSE ``event-calendar`` feed and the BSE
  ``BoardMeeting`` feed (board meetings, results, dividends), merged, parsed
  dates, newest first.

A non-NSE/BSE instrument, or a venue with no such feed, is answered with an
empty list, ``coverage`` and a ``note`` (C3, D-B7-3) — never raised as an
upstream failure; a real transport failure still raises.

* **Deals** — bulk and block deals (NSE, or BSE for a BSE-only scrip) and SAST
  Reg 29 disclosures (NSE), newest first (:func:`get_deals`).

* **Corporate actions** — dividends, bonuses, splits, rights and buybacks from
  the NSE and BSE corporate-action feeds, a dual-listed action collapsed to one
  row (:func:`get_corporate_actions`).

* **Shareholding** — the NSE quarterly shareholding MASTER (promoter+group,
  public, employee-trust percentages + the XBRL filing URL). The FII/DII split
  lives only inside the XBRL, so on the NSE lane those fields are ``None`` — but
  for a DUAL-LISTED name the split is MERGED in from the BSE SEBI-XBRL lane
  (institutions/FII/DII + the non-institutional public float, as-of-labeled), so
  a name like SIL no longer loses its FII 38.86%/DII 4.04% to the NSE master. The
  ``public`` bucket is labeled ``incl. institutions`` on both lanes so it is never
  mistaken for the non-institutional float; nothing is ever fabricated.

All public functions are synchronous (matching every provider the registry
drives); async callers wrap them in ``asyncio.to_thread``. Network is reached
through two seams tests monkeypatch: the :mod:`services.nse_provider` raw
accessors and :func:`_bse_get_json`.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from collections import Counter
from datetime import UTC, date, datetime, timedelta

from models.announcements import (
    Announcement,
    AnnouncementsResponse,
    AnnouncementWindow,
    CorporateAction,
    CorporateActionsResponse,
    ExchangeDeal,
    ExchangeDealsResponse,
    ResultsCalendarResponse,
    ResultsEvent,
    ShareholdingPattern,
    ShareholdingResponse,
)
from services import data_cache, locale, nse_provider, symbol_resolver
from services.errors import ProviderError

logger = logging.getLogger(__name__)

EXCHANGE_NSE = "NSE"
EXCHANGE_BSE = "BSE"
EXCHANGES = (EXCHANGE_NSE, EXCHANGE_BSE)

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
#: The merged announcements feed is cached for 15 minutes for every caller (the
#: panel route, the agent tool and research's gather), which also keeps the NSE
#: throttle from re-walking the cookie dance per call (R15-DATA-074).
ANNOUNCEMENTS_TTL_SECONDS = 15 * 60

# The exchange "Public" category (NSE quarterly master ``public_val`` and the BSE
# SEBI ``PublicShareholdingMember``) FOLDS institutions in — it is the full public
# category, not the non-institutional float. Every ``public_percent`` we serve
# carries this basis label so a consumer never mistakes it for the true public
# float (which lives in ``public_non_institutional_percent`` when the XBRL splits
# it out).
PUBLIC_BASIS_INCL_INSTITUTIONS = "incl. institutions"

# BSE announcements API (observed live 2026-06-10 — module docstring).
_BSE_ANN_URL = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
_BSE_ATTACHMENT_LIVE = "https://www.bseindia.com/xml-data/corpfiling/AttachLive/"
_BSE_ATTACHMENT_HIS = "https://www.bseindia.com/xml-data/corpfiling/AttachHis/"
# The announcements window requested from BSE (the feed is date-bounded; NSE's
# returns full history trimmed client-side). Paged by count up to the limit, so
# an infrequent filer's quarter-old results filing is inside it (R15-DATA-019:
# a 30-day window showed JUMBO, last filed 50 days earlier, as empty). Live
# probes have served windows of about six months.
_BSE_ANN_WINDOW_DAYS = 180
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


def _today_ist() -> date:
    return datetime.now(tz=UTC).astimezone(_ist()).date()


def _covered_window(
    items: list[Announcement], limit: int, start: date | None, end: date, cut: bool
) -> AnnouncementWindow:
    """The range a lane's (limit-trimmed) items are complete for: from ``start``
    (``None`` = full history) unless older items were ``cut`` at ``limit``, in
    which case from the oldest kept item's day."""
    kept = [item.ts for item in items[:limit] if item.ts is not None]
    if cut and kept:
        start = min(kept).astimezone(_ist()).date()
    return AnnouncementWindow(window_start=start, window_end=end)


def _fetch_bse_announcements(
    bare: str, limit: int
) -> tuple[list[Announcement], AnnouncementWindow]:
    """The BSE lane — ``AnnSubCategoryGetData`` rows over the last
    :data:`_BSE_ANN_WINDOW_DAYS`, paged until ``limit`` items are collected or
    the window's ``ROWCNT`` rows run out, with the window the items cover."""
    code = symbol_resolver.bse_scrip_code(bare)
    if not code:
        raise ProviderError(f"bse announcements: no scrip code for {bare!r} in the master")
    today = _today_ist()
    start = today - timedelta(days=_BSE_ANN_WINDOW_DAYS)
    params = {
        "strCat": "-1",
        "strPrevDate": start.strftime("%Y%m%d"),
        "strScrip": str(code),
        "strSearch": "P",
        "strToDate": today.strftime("%Y%m%d"),
        "strType": "C",
        "subcategory": "-1",
    }
    items: list[Announcement] = []
    rows_seen = 0
    page = 1
    while True:
        payload = _bse_get_json(_BSE_ANN_URL, {"pageno": str(page), **params})
        table = payload.get("Table") if isinstance(payload, dict) else None
        if not isinstance(table, list):
            raise ProviderError(f"bse announcements: malformed payload for {bare!r}")
        for row in table:
            if not isinstance(row, dict):
                continue
            item = _bse_row_to_announcement(bare, row)
            if item is not None:
                items.append(item)
        rows_seen += len(table)
        total = _bse_row_count(payload)
        exhausted = not table or (total is not None and rows_seen >= total)
        if exhausted or len(items) >= limit:
            break
        page += 1
    cut = len(items) > limit or not exhausted
    return items[:limit], _covered_window(items, limit, start, today, cut)


def _bse_row_count(payload: dict) -> int | None:
    """``Table1[0].ROWCNT`` — the window's row total across every page."""
    meta = payload.get("Table1")
    if isinstance(meta, list) and meta and isinstance(meta[0], dict):
        count = meta[0].get("ROWCNT")
        if isinstance(count, int):
            return count
    return None


def _bse_row_to_announcement(bare: str, row: dict) -> Announcement | None:
    """Observed BSE row → :class:`Announcement` (None for a headline-less row)."""
    headline = _clean(row.get("NEWSSUB")) or _clean(row.get("HEADLINE"))
    if not headline:
        return None
    category = _clean(row.get("CATEGORYNAME")) or _clean(row.get("SUBCATNAME"))
    attachment = _clean(row.get("ATTACHMENTNAME"))
    # PDFFLAG 1 files the attachment under the history path, 0 under the live one.
    base = _BSE_ATTACHMENT_HIS if row.get("PDFFLAG") == 1 else _BSE_ATTACHMENT_LIVE
    item = Announcement(
        # The BSE payload carries only the numeric SCRIP_CD + the long company
        # name — stamp the requested bare ticker (mirrors bse_provider quotes).
        symbol=bare,
        exchange=EXCHANGE_BSE,
        headline=headline,
        category=category,
        attachment_url=(base + attachment) if attachment else None,
        ts=_parse_bse_ts(row),
    )
    # HEADLINE is the body text NSE's attchmntText carries; NEWSSUB is a subject.
    item._body = _clean(row.get("HEADLINE"))
    item._kind = _canonical_kind(row.get("SUBCATNAME")) or _canonical_kind(row.get("CATEGORYNAME"))
    return item


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


def _fetch_nse_announcements(
    bare: str, limit: int
) -> tuple[list[Announcement], AnnouncementWindow]:
    """The NSE lane — the full history trimmed to ``limit``, so its items cover
    all of history unless the trim cut older ones."""
    rows = nse_provider.get_corporate_announcements(bare, limit=limit)
    items: list[Announcement] = []
    for row in rows:
        item = _nse_row_to_announcement(bare, row)
        if item is not None:
            items.append(item)
    return items, _covered_window(items, limit, None, _today_ist(), len(rows) >= limit)


def _nse_row_to_announcement(bare: str, row: dict) -> Announcement | None:
    """Observed NSE row → :class:`Announcement` (None for a headline-less row).

    ``attchmntText`` is the disclosure text (the substantive headline);
    ``desc`` is the category label ("Updates") and the fallback headline for a
    text-less row.
    """
    headline = _clean(row.get("attchmntText")) or _clean(row.get("desc"))
    if not headline:
        return None
    item = Announcement(
        symbol=_clean(row.get("symbol")) or bare,
        exchange=EXCHANGE_NSE,
        headline=headline,
        category=_clean(row.get("desc")),
        attachment_url=_clean(row.get("attchmntFile")) or None,
        ts=_parse_nse_ts(row),
    )
    item._kind = _canonical_kind(row.get("desc"))
    return item


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


#: How much of the normalised body the dedup compares: BSE truncates HEADLINE
#: near 200 characters ("... ICICI ...."), so a prefix well inside that matches
#: the full NSE text of the same filing (D-B3-10).
_DEDUP_PREFIX_CHARS = 120
#: NSE's wrapper around a filing's own title ("Reliance Industries Limited has
#: informed the Exchange regarding 'Presentation on ...'", "... about Credit
#: Rating"); BSE carries the bare title, so the wrapper is dropped before comparing.
_NSE_WRAPPER_RE = re.compile(r"^.*? has informed (?:the exchange )?(?:regarding|about|that) ")
#: The two feeds disseminate one filing a few minutes apart (0-10 min observed
#: live, 2026-09-23); two filings further apart are never paired.
_PAIR_WINDOW = timedelta(minutes=10)
#: Share of the shorter text's words the other text must carry for two items to
#: be one filing. Live pairs score 0.67-1.0; two different same-day filings of
#: one company minutes apart score up to 0.53 (shared "Company executives ...
#: Institutional Investors' Meeting" boilerplate).
_PAIR_MIN_OVERLAP = 0.6
#: Exchange category labels (NSE ``desc``; BSE ``SUBCATNAME``, else
#: ``CATEGORYNAME``) mapped to one canonical kind, from the labels on the live
#: HDFCBANK/TCS/RELIANCE/INFY feeds (2026-09). NSE's templated text ("... has
#: informed the Exchange about Schedule of meet") shares few words with BSE's
#: subject ("Announcement under Regulation 30 (LODR)-Analyst / Investor Meet -
#: Intimation"), but both feeds file it under the same category. Catch-all
#: labels (NSE "Updates", "Disclosure of material issue") are left out.
_CANONICAL_KIND = {
    "analysts/institutional investor meet/con. call updates": "analyst_meet",
    "investor presentation": "analyst_meet",
    "analyst / investor meet": "analyst_meet",
    "earnings call transcript": "analyst_meet",
    "credit rating": "credit_rating",
    "press release": "press_release",
    "press release / media release": "press_release",
    "copy of newspaper publication": "newspaper",
    "newspaper publication": "newspaper",
    "board meeting intimation": "board_meeting",
    "board meeting": "board_meeting",
    "outcome of board meeting": "board_outcome",
    "shareholders meeting": "shareholder_meeting",
    "agm": "shareholder_meeting",
    "egm": "shareholder_meeting",
    "general updates": "general",
    "general": "general",
    "acquisition": "acquisition",
    "bagging/receiving of orders/contracts": "order",
    "award of order / receipt of order": "order",
    "esop/esos/esps": "esop",
    "allotment of esop / esps": "esop",
    "change in management": "management_change",
    "dividend": "dividend",
    "certificate under sebi (depositories and participants) regulations, 2018": "dp_certificate",
    "certificate under reg. 74 (5) of sebi (dp) regulations, 2018": "dp_certificate",
    "news verification": "clarification",
    "clarification": "clarification",
}
_STOPWORDS = frozenset(
    "the a an of to in on for and is has have that this with by as at be we you our its it "
    "are from under about regarding please note inform wish will been was were or".split()
)


def _dedup_key(item: Announcement) -> tuple[str, str, str]:
    """The exact dedup key: ``(symbol, body-prefix-hash, date)``.

    Collapses a re-disseminated item (and an exact cross-feed copy); an NSE and
    a BSE item whose texts differ are paired by :func:`_pair_cross_feed`. The
    compared text is the disclosure body (NSE ``attchmntText``, BSE
    ``HEADLINE``), never BSE's short ``NEWSSUB`` subject. It is casefolded,
    punctuation and whitespace runs collapse to one space (BSE doubles quotes and
    spaces), NSE's "has informed the Exchange" wrapper is dropped, and the first
    :data:`_DEDUP_PREFIX_CHARS` characters are hashed. The date component is the
    announcement's IST calendar day (timestamp-less items use an empty day and
    only collapse on identical text). The display headline is unchanged.
    """
    text = re.sub(r"[\W_]+", " ", (item._body or item.headline).casefold()).strip()
    normalized = _NSE_WRAPPER_RE.sub("", text)[:_DEDUP_PREFIX_CHARS]
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]
    day = item.ts.astimezone(_ist()).date().isoformat() if item.ts else ""
    return (item.symbol.upper(), digest, day)


def _words(text: str | None) -> frozenset[str]:
    """The content words of one announcement text: casefolded, apostrophes
    dropped (BSE doubles them), NSE's "has informed the Exchange" wrapper removed,
    stopwords and one-letter tokens skipped."""
    folded = re.sub(r"['\u2019]", "", (text or "").casefold())
    normalized = _NSE_WRAPPER_RE.sub("", re.sub(r"[\W_]+", " ", folded).strip())
    return frozenset(w for w in normalized.split() if len(w) > 1 and w not in _STOPWORDS)


def _overlap(a: frozenset[str], b: frozenset[str]) -> float:
    """Share of the shorter word set found in the other; 0 when either side has
    fewer than two words (a boilerplate "Enclosed" body says nothing)."""
    if len(a) < 2 or len(b) < 2:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _canonical_kind(label: object) -> str | None:
    """An exchange category label's canonical kind (:data:`_CANONICAL_KIND`)."""
    text = _clean(label)
    return _CANONICAL_KIND.get(text.casefold()) if text else None


def _pair_cross_feed(items: list[Announcement]) -> list[Announcement]:
    """Drop each BSE item that pairs with an NSE item of the same filing
    (R15-DATA-020); NSE wins a pair.

    Candidates share the symbol and IST day and were disseminated within
    :data:`_PAIR_WINDOW`. A candidate pairs when the word overlap of the NSE text
    against the BSE body or its subject, whichever is higher, reaches
    :data:`_PAIR_MIN_OVERLAP` (BSE's body is often boilerplate — "Enclosed" —
    while its subject names the filing), or when both items carry the same
    canonical category (:data:`_CANONICAL_KIND`) and each is the other's only
    same-category candidate in the window (NSE's templated text rarely shares
    words with BSE's subject). Pairs are taken best-first (highest overlap, then
    the shortest gap) and each item pairs at most once, so two filings minutes
    apart each keep their own match.
    """
    nse = [i for i in items if i.exchange == EXCHANGE_NSE and i.ts is not None]
    bse = [i for i in items if i.exchange == EXCHANGE_BSE and i.ts is not None]
    in_window: list[tuple[int, int, float]] = []
    for n_idx, n_item in enumerate(nse):
        n_day = n_item.ts.astimezone(_ist()).date()
        for b_idx, b_item in enumerate(bse):
            gap = abs(n_item.ts - b_item.ts)
            if (
                n_item.symbol.upper() == b_item.symbol.upper()
                and gap <= _PAIR_WINDOW
                and b_item.ts.astimezone(_ist()).date() == n_day
            ):
                in_window.append((n_idx, b_idx, gap.total_seconds()))
    same_kind = [
        (n_idx, b_idx)
        for n_idx, b_idx, _gap in in_window
        if nse[n_idx]._kind is not None and nse[n_idx]._kind == bse[b_idx]._kind
    ]
    kind_matches_nse = Counter(n_idx for n_idx, _b in same_kind)
    kind_matches_bse = Counter(b_idx for _n, b_idx in same_kind)
    candidates: list[tuple[float, float, int, int]] = []
    for n_idx, b_idx, gap_seconds in in_window:
        n_words = _words(nse[n_idx].headline)
        b_item = bse[b_idx]
        score = max(
            _overlap(n_words, _words(b_item._body)), _overlap(n_words, _words(b_item.headline))
        )
        unique_kind = (
            (n_idx, b_idx) in same_kind
            and kind_matches_nse[n_idx] == 1
            and kind_matches_bse[b_idx] == 1
        )
        if score >= _PAIR_MIN_OVERLAP or unique_kind:
            candidates.append((-score, gap_seconds, n_idx, b_idx))
    paired_nse: set[int] = set()
    paired_bse: set[int] = set()
    for _score, _gap, n_idx, b_idx in sorted(candidates):
        if n_idx not in paired_nse and b_idx not in paired_bse:
            paired_nse.add(n_idx)
            paired_bse.add(b_idx)
    dropped = {id(bse[b_idx]) for b_idx in paired_bse}
    return [item for item in items if id(item) not in dropped]


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
        if any(listed for _, listed in lanes):
            note = f"{bare} is not listed on {exchange}, so its {exchange} feed does not cover it"
            return AnnouncementsResponse(
                symbol=bare, exchange=exchange, count=0, coverage="venue_not_covered", note=note
            )
        return AnnouncementsResponse(
            symbol=bare, exchange=exchange, count=0, **_not_applicable(bare)
        )

    merged: list[Announcement] = []
    sources: list[str] = []
    errors: dict[str, str] = {}
    windows: dict[str, AnnouncementWindow] = {}
    for name in applicable:  # NSE first — it wins an exact-text collision
        fetch = _fetch_nse_announcements if name == EXCHANGE_NSE else _fetch_bse_announcements
        try:
            items, windows[name] = fetch(bare, limit)
            merged.extend(items)
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
    deduped = _pair_cross_feed(deduped)
    floor = datetime.min.replace(tzinfo=UTC)
    deduped.sort(key=lambda a: a.ts or floor, reverse=True)
    trimmed = deduped[:limit]
    if len(deduped) > limit and trimmed[-1].ts is not None:
        # The merged trim cut older items from the lanes: none is complete
        # before the oldest item kept.
        cut = trimmed[-1].ts.astimezone(_ist()).date()
        windows = {
            name: window.model_copy(update={"window_start": max(window.window_start or cut, cut)})
            for name, window in windows.items()
        }
    return AnnouncementsResponse(
        symbol=bare,
        exchange=exchange,
        count=len(trimmed),
        announcements=trimmed,
        sources=sources,
        errors=errors,
        windows=windows,
    )


async def get_announcements_cached(
    symbol: str, exchange: str | None = None, limit: int = DEFAULT_LIMIT
) -> AnnouncementsResponse:
    """:func:`get_announcements` through :mod:`services.data_cache` — the one
    cached entry point the router, the agent tool and research share. Raises
    :class:`ProviderError` like the uncached call; a failure is never cached."""
    normalized = symbol.strip().upper()
    cache_key = f"disclosures:announcements:{normalized}:{exchange or 'ALL'}:{limit}"
    cached = await data_cache.get(cache_key, ANNOUNCEMENTS_TTL_SECONDS)
    if isinstance(cached, dict):
        try:
            return AnnouncementsResponse.model_validate(cached)
        except Exception:  # noqa: BLE001
            logger.warning("disclosures: cache deserialise failed for %s; refetching", cache_key)
    response = await asyncio.to_thread(get_announcements, normalized, exchange, limit)
    await data_cache.set(cache_key, response.model_dump(mode="json"))
    return response


def _not_applicable(bare: str) -> dict[str, str]:
    """The out-of-coverage answer for a non-NSE/BSE instrument (C3, D-B7-3)."""
    return {
        "coverage": "not_applicable",
        "note": f"{bare} is not an NSE/BSE instrument; Indian exchange disclosures do not apply",
    }


# ---------------------------------------------------------------------------
# Results calendar (NSE event-calendar feed + BSE board-meeting feed).
# ---------------------------------------------------------------------------


def _nse_results(bare: str) -> list[ResultsEvent]:
    events = []
    for row in nse_provider.get_results_calendar(bare):
        purpose = _clean(row.get("purpose"))
        if purpose:
            events.append(
                ResultsEvent(
                    symbol=_clean(row.get("symbol")) or bare,
                    company=_clean(row.get("company")),
                    purpose=purpose,
                    description=_clean(row.get("bm_desc")),
                    date=_parse_day(row.get("date")),
                    exchange=EXCHANGE_NSE,
                )
            )
    return events


#: BSE's per-scrip board-meeting feed. Observed live 2026-09-24 (scrip 539681
#: DAL; fixture under ``tests/fixtures/bse/``): ``{"Table": [{scrip_code,
#: Short_name, LONG_NAME, Purpose_name ("Results", "General", ...), meeting_date
#: "12 Aug 2026", tm "2026-08-12T00:00:00"}, ...]}``.
_BSE_BOARD_MEETING_URL = "https://api.bseindia.com/BseIndiaAPI/api/BoardMeeting/w"


def _bse_results(bare: str, code: str) -> list[ResultsEvent]:
    payload = _bse_get_json(_BSE_BOARD_MEETING_URL, {"scripcode": code})
    table = payload.get("Table") if isinstance(payload, dict) else None
    if not isinstance(table, list):
        raise ProviderError(f"bse board meetings: malformed payload for {bare!r}")
    events = []
    for row in table:
        purpose = _clean(row.get("Purpose_name")) if isinstance(row, dict) else None
        if purpose:
            events.append(
                ResultsEvent(
                    symbol=bare,
                    company=_clean(row.get("LONG_NAME")),
                    purpose=purpose,
                    date=_parse_day(str(row.get("tm") or "")[:10]),
                    exchange=EXCHANGE_BSE,
                )
            )
    return events


def _meeting_key(event: ResultsEvent) -> tuple[date | None, str]:
    """One board meeting across both feeds: its date and purpose kind (NSE
    "Financial Results" and BSE "Results" are one kind)."""
    purpose = event.purpose.lower()
    return event.date, "results" if "result" in purpose else purpose


def get_results_calendar(symbol: str) -> ResultsCalendarResponse:
    """Results/board-meeting events for ``symbol`` from BOTH exchanges, newest
    first (R15-DATA-050).

    A BSE-only (or SME) name is served from BSE's board-meeting feed; a dual
    listing's meeting on both feeds collapses to one ``NSE+BSE`` event. A
    non-NSE/BSE instrument is answered ``not_applicable``; a failing lane is
    recorded in ``errors`` and every applicable lane failing raises.
    """
    bare = locale.strip_exchange_suffix(symbol.strip().upper())
    if not bare:
        raise ProviderError("disclosures: empty symbol")
    on_nse = symbol_resolver.is_nse_symbol(bare)
    bse_code = (
        symbol_resolver.dual_listed_bse_code(bare)
        if on_nse
        else symbol_resolver.bse_scrip_code(bare)
    )
    if not on_nse and not bse_code:
        return ResultsCalendarResponse(symbol=bare, count=0, **_not_applicable(bare))

    by_lane: dict[str, list[ResultsEvent]] = {}
    errors: dict[str, str] = {}
    lanes = [
        (EXCHANGE_NSE, on_nse, lambda: _nse_results(bare)),
        (EXCHANGE_BSE, bool(bse_code), lambda: _bse_results(bare, bse_code)),
    ]
    for name, applicable, fetch in lanes:
        if not applicable:
            continue
        try:
            by_lane[name] = fetch()
        except ProviderError as exc:
            logger.debug("disclosures: %s results calendar failed for %s: %s", name, bare, exc)
            errors[name] = str(exc)
    if not by_lane:
        detail = "; ".join(f"{name}: {msg}" for name, msg in errors.items())
        raise ProviderError(f"disclosures: every results source failed for {bare!r} ({detail})")
    events = list(by_lane.get(EXCHANGE_NSE, []))
    seen = {_meeting_key(e): i for i, e in enumerate(events)}
    for event in by_lane.get(EXCHANGE_BSE, []):
        index = seen.get(_meeting_key(event))
        if index is None:
            seen[_meeting_key(event)] = len(events)
            events.append(event)
        elif events[index].exchange == EXCHANGE_NSE:
            events[index] = events[index].model_copy(update={"exchange": "NSE+BSE"})
    events.sort(key=lambda e: e.date or date.min, reverse=True)
    return ResultsCalendarResponse(
        symbol=bare, count=len(events), events=events, sources=list(by_lane), errors=errors
    )


# ---------------------------------------------------------------------------
# Corporate actions (NSE corporates-corporateActions + BSE CorporateAction).
# ---------------------------------------------------------------------------

#: BSE's per-scrip corporate-action feed. Observed live 2026-09-24 (scrip 542446
#: JONJUA; fixtures under ``tests/fixtures/bse/``): ``{"Table": [dividend
#: history], "Table1": [bonus history], "Table2": [{purpose "Bonus issue 7:24",
#: purpose_code, Ex_date "04 Sep 2026", BCRD "RD 04/09/2026" (or "BC <from>-<to>"
#: for a book closure), Details "25.00" (a dividend's amount), PAYMENT_DATE
#: "2026-08-30T00:00:00" | null}, ...]}``; Table2 is the combined recent list.
_BSE_CA_URL = "https://api.bseindia.com/BseIndiaAPI/api/CorporateAction/w"
#: The purpose line's kind, checked in order (an AGM line that names a dividend
#: is a dividend; "Right Issue of Equity Shares" is a rights issue).
_ACTION_KINDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("bonus", re.compile(r"\bbonus\b", re.IGNORECASE)),
    ("split", re.compile(r"split|sub-?division", re.IGNORECASE)),
    ("rights", re.compile(r"\brights?\b", re.IGNORECASE)),
    ("buyback", re.compile(r"buy\s*-?\s*back", re.IGNORECASE)),
    ("dividend", re.compile(r"dividend", re.IGNORECASE)),
)
_RATIO_RE = re.compile(r"(\d+)\s*:\s*(\d+)")
_AMOUNT_RE = re.compile(r"(?:rs\.?|₹|inr)\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)


def _action_kind(purpose: str) -> str:
    return next((kind for kind, pattern in _ACTION_KINDS if pattern.search(purpose)), "other")


def _action_ratio(kind: str, purpose: str) -> str | None:
    """A bonus/rights/split ratio ("7:24") in the purpose line, else ``None``."""
    match = _RATIO_RE.search(purpose) if kind in ("bonus", "rights", "split") else None
    return f"{match.group(1)}:{match.group(2)}" if match else None


def _dividend_amount(kind: str, purpose: str) -> float | None:
    """A dividend's per-share amount in the purpose line ("Rs 25 Per Share")."""
    match = _AMOUNT_RE.search(purpose) if kind == "dividend" else None
    return float(match.group(1)) if match else None


def _parse_bse_day(value: object) -> date | None:
    """BSE's action dates: "04 Sep 2026", "RD 04/09/2026", "2026-08-30T00:00:00"."""
    raw = _clean(value)
    if not raw:
        return None
    for fmt in ("%d %b %Y", "RD %d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _nse_corporate_actions(bare: str) -> list[CorporateAction]:
    """The NSE lane: ``subject`` + ``exDate``/``recDate`` rows (no payment date)."""
    actions: list[CorporateAction] = []
    for row in nse_provider.get_corporate_actions(bare):
        purpose = _clean(row.get("subject"))
        if not purpose:
            continue
        kind = _action_kind(purpose)
        actions.append(
            CorporateAction(
                symbol=bare,
                kind=kind,
                purpose=purpose,
                ratio=_action_ratio(kind, purpose),
                amount_per_share=_dividend_amount(kind, purpose),
                ex_date=_parse_day(row.get("exDate")),
                record_date=_parse_day(row.get("recDate")),
                exchange=EXCHANGE_NSE,
            )
        )
    return actions


def _bse_corporate_actions(bare: str, code: str) -> list[CorporateAction]:
    """The BSE lane: the ``Table2`` rows of the scrip's CorporateAction feed."""
    payload = _bse_get_json(_BSE_CA_URL, {"scripcode": code})
    table = payload.get("Table2") if isinstance(payload, dict) else None
    if not isinstance(table, list):
        raise ProviderError(f"bse corporate actions: malformed payload for {bare!r}")
    actions: list[CorporateAction] = []
    for row in table:
        purpose = _clean(row.get("purpose")) if isinstance(row, dict) else None
        if not purpose:
            continue
        kind = _action_kind(purpose)
        amount = _pct(row.get("Details")) if kind == "dividend" else None
        actions.append(
            CorporateAction(
                symbol=bare,
                kind=kind,
                purpose=purpose,
                ratio=_action_ratio(kind, purpose),
                amount_per_share=amount if amount is not None else _dividend_amount(kind, purpose),
                ex_date=_parse_bse_day(row.get("Ex_date")),
                record_date=_parse_bse_day(row.get("BCRD")),
                payment_date=_parse_bse_day(row.get("PAYMENT_DATE")),
                exchange=EXCHANGE_BSE,
            )
        )
    return actions


def _merge_actions(nse: list[CorporateAction], bse: list[CorporateAction]) -> list[CorporateAction]:
    """NSE rows plus each BSE row that is not the same action: a dual-listed
    action (same kind and ex-date) collapses onto the NSE row, which takes the
    fields only BSE carries (the payment date) and is labelled ``NSE+BSE``."""
    merged = list(nse)
    open_by_key: dict[tuple[str, date], list[int]] = {}
    for idx, action in enumerate(nse):
        if action.ex_date is not None:
            open_by_key.setdefault((action.kind, action.ex_date), []).append(idx)
    for action in bse:
        slots = open_by_key.get((action.kind, action.ex_date)) if action.ex_date else None
        if not slots:
            merged.append(action)
            continue
        idx = slots.pop(0)
        filled = {
            name: getattr(action, name)
            for name in ("ratio", "amount_per_share", "record_date", "payment_date")
            if getattr(merged[idx], name) is None
        }
        merged[idx] = merged[idx].model_copy(update={**filled, "exchange": "NSE+BSE"})
    return merged


def get_corporate_actions(symbol: str) -> CorporateActionsResponse:
    """Dividends, bonuses, splits, rights and buybacks for ``symbol`` from BOTH
    exchanges, newest ex-date first (R15-DATA-025).

    A BSE-only name is served from BSE; a dual-listed name's action on both
    feeds collapses to one row. Lanes the symbol is not listed on are skipped; a
    failing applicable lane is recorded in ``errors`` and the rest is served;
    every applicable lane failing raises :class:`ProviderError`.
    """
    bare = locale.strip_exchange_suffix(symbol.strip().upper())
    if not bare:
        raise ProviderError("disclosures: empty symbol")
    on_nse = symbol_resolver.is_nse_symbol(bare)
    # A dual-listed name's own BSE scrip only: a same-ticker BSE scrip of another
    # company would merge that company's actions into this one.
    bse_code = (
        symbol_resolver.dual_listed_bse_code(bare)
        if on_nse
        else symbol_resolver.bse_scrip_code(bare)
    )
    if not on_nse and not bse_code:
        return CorporateActionsResponse(symbol=bare, count=0, **_not_applicable(bare))

    by_lane: dict[str, list[CorporateAction]] = {}
    errors: dict[str, str] = {}
    lanes = [
        (EXCHANGE_NSE, on_nse, lambda: _nse_corporate_actions(bare)),
        (EXCHANGE_BSE, bool(bse_code), lambda: _bse_corporate_actions(bare, bse_code)),
    ]
    for name, applicable, fetch in lanes:
        if not applicable:
            continue
        try:
            by_lane[name] = fetch()
        except ProviderError as exc:
            logger.debug("disclosures: %s corporate actions failed for %s: %s", name, bare, exc)
            errors[name] = str(exc)
    if not by_lane:
        detail = "; ".join(f"{name}: {msg}" for name, msg in errors.items())
        raise ProviderError(
            f"disclosures: every corporate-action source failed for {bare!r} ({detail})"
        )
    actions = _merge_actions(by_lane.get(EXCHANGE_NSE, []), by_lane.get(EXCHANGE_BSE, []))
    actions.sort(key=lambda a: a.ex_date or date.min, reverse=True)
    return CorporateActionsResponse(
        symbol=bare, count=len(actions), actions=actions, sources=list(by_lane), errors=errors
    )


# ---------------------------------------------------------------------------
# Bulk / block deals and SAST disclosures (R15-DATA-024).
# ---------------------------------------------------------------------------

DEAL_KINDS = ("bulk", "block", "sast")
#: How far back the NSE bulk/block lanes are asked for (the feed is dated).
_DEALS_LOOKBACK_DAYS = 365
#: BSE's per-scrip bulk/block feed (the stock page's "Bulk / Block Deals" tab;
#: ``type`` 1 = bulk, 2 = block). Observed live 2026-09-24 (scrip 539091 CCDL):
#: ``{"Table": [{DEAL_DATE "23 Sep 2026", SCRIP_CODE, scripname, CLIENT_NAME,
#: TRANSACTION_TYPE "B"|"S", QUANTITY, PRICE}], "Table1": [scrip meta]}``.
_BSE_DEALS_URL = "https://api.bseindia.com/BseIndiaAPI/api/BulkblockDeal/w"
_BSE_DEAL_TYPE = {"bulk": "1", "block": "2"}
_SIDES = {"BUY": "buy", "B": "buy", "SELL": "sell", "S": "sell"}


def _nse_deals(bare: str, kind: str) -> list[ExchangeDeal]:
    """One NSE lane: bulk or block deals over the lookback, or SAST disclosures."""
    if kind == "sast":
        return [_nse_sast_deal(bare, row) for row in nse_provider.get_sast_disclosures(bare)]
    today = _today_ist()
    rows = nse_provider.get_bulk_block_deals(
        bare, f"{kind}_deals", today - timedelta(days=_DEALS_LOOKBACK_DAYS), today
    )
    return [
        _trade_deal(
            bare,
            kind,
            EXCHANGE_NSE,
            _parse_day(row.get("BD_DT_DATE")),
            row.get("BD_CLIENT_NAME"),
            row.get("BD_BUY_SELL"),
            row.get("BD_QTY_TRD"),
            row.get("BD_TP_WATP"),
        )
        for row in rows
    ]


def _bse_deals(bare: str, code: str, kind: str) -> list[ExchangeDeal]:
    """One BSE lane (bulk or block) for a BSE-only scrip."""
    payload = _bse_get_json(
        _BSE_DEALS_URL, {"fromdt": "", "todt": "", "type": _BSE_DEAL_TYPE[kind], "scripcode": code}
    )
    table = payload.get("Table") if isinstance(payload, dict) else None
    if not isinstance(table, list):
        raise ProviderError(f"bse {kind} deals: malformed payload for {bare!r}")
    return [
        _trade_deal(
            bare,
            kind,
            EXCHANGE_BSE,
            _parse_bse_day(row.get("DEAL_DATE")),
            row.get("CLIENT_NAME"),
            row.get("TRANSACTION_TYPE"),
            row.get("QUANTITY"),
            row.get("PRICE"),
        )
        for row in table
        if isinstance(row, dict)
    ]


def _trade_deal(
    bare: str,
    kind: str,
    exchange: str,
    day: date | None,
    party: object,
    side: object,
    quantity: object,
    price: object,
) -> ExchangeDeal:
    qty, px = _pct(quantity), _pct(price)
    return ExchangeDeal(
        symbol=bare,
        kind=kind,
        date=day,
        party=_clean(party),
        side=_SIDES.get((_clean(side) or "").upper()),
        quantity=qty,
        price=px,
        value=round(qty * px, 2) if qty is not None and px is not None else None,
        exchange=exchange,
    )


def _nse_sast_deal(bare: str, row: dict) -> ExchangeDeal:
    """A Reg 29 row: dated by the transaction's last day ("... to 07-SEP-2026")."""
    sale = (_clean(row.get("acqSaleType")) or "").lower() == "sale"
    period = _clean(row.get("acquirerDate")) or ""
    return ExchangeDeal(
        symbol=bare,
        kind="sast",
        date=_parse_day(period.rsplit(" to ", 1)[-1]),
        party=_clean(row.get("acquirerName")),
        side="sell" if sale else "buy",
        quantity=_pct(row.get("noOfShareSale" if sale else "noOfShareAcq")),
        percent_after=_pct(row.get("totAftShare")),
        exchange=EXCHANGE_NSE,
        source_url=_clean(row.get("attachement")),
    )


def get_deals(symbol: str, kind: str | None = None) -> ExchangeDealsResponse:
    """Bulk deals, block deals and SAST (Reg 29) disclosures for ``symbol``,
    newest first (R15-DATA-024).

    An NSE listing is served from NSE's bulk, block and SAST feeds; a BSE-only
    scrip from BSE's bulk and block feeds (BSE carries no SAST lane here).
    ``kind`` filters to one of :data:`DEAL_KINDS`. A failing lane is recorded in
    ``errors`` and the rest is served; every applicable lane failing (or none
    applying) raises :class:`ProviderError`.
    """
    bare = locale.strip_exchange_suffix(symbol.strip().upper())
    if not bare:
        raise ProviderError("disclosures: empty symbol")
    if kind is not None and kind not in DEAL_KINDS:
        raise ProviderError(f"disclosures: unknown deal kind {kind!r} (use bulk, block or sast)")
    kinds = [kind] if kind else list(DEAL_KINDS)
    if symbol_resolver.is_nse_symbol(bare):
        lanes = [(f"{EXCHANGE_NSE} {k}", lambda k=k: _nse_deals(bare, k)) for k in kinds]
    elif code := symbol_resolver.bse_scrip_code(bare):
        lanes = [
            (f"{EXCHANGE_BSE} {k}", lambda k=k: _bse_deals(bare, code, k))
            for k in kinds
            if k in _BSE_DEAL_TYPE
        ]
        if not lanes:
            note = f"SAST disclosures come from NSE; {bare} is BSE-only"
            return ExchangeDealsResponse(
                symbol=bare, kind=kind, count=0, coverage="venue_not_covered", note=note
            )
    else:
        return ExchangeDealsResponse(symbol=bare, kind=kind, count=0, **_not_applicable(bare))

    deals: list[ExchangeDeal] = []
    sources: list[str] = []
    errors: dict[str, str] = {}
    for name, fetch in lanes:
        try:
            deals.extend(fetch())
            sources.append(name)
        except ProviderError as exc:
            logger.debug("disclosures: %s deals failed for %s: %s", name, bare, exc)
            errors[name] = str(exc)
    if not sources:
        detail = "; ".join(f"{name}: {msg}" for name, msg in errors.items())
        raise ProviderError(f"disclosures: every deal source failed for {bare!r} ({detail})")
    deals.sort(key=lambda d: d.date or date.min, reverse=True)
    return ExchangeDealsResponse(
        symbol=bare, kind=kind, count=len(deals), deals=deals, sources=sources, errors=errors
    )


# ---------------------------------------------------------------------------
# Shareholding pattern (NSE quarterly master).
# ---------------------------------------------------------------------------


def get_shareholding(symbol: str) -> ShareholdingResponse:
    """Quarterly shareholding patterns for ``symbol``, newest quarter first.

    NSE-first, BSE-fallback with a MERGE for dual-listed names. The NSE quarterly
    master carries promoter/public/employee-trust percentages but NO FII/DII split
    (that lives only in the SEBI XBRL), and its "public" bucket FOLDS institutions
    in — so a dual-listed name with a large FII position (SIL: FII 38.86%, public
    36.79% true vs 79.69% institution-inclusive) loses its institutional picture on
    the NSE lane alone. When a name is ALSO BSE-listed, each NSE pattern is enriched
    with the BSE SEBI-XBRL split (institutions/FII/DII + the non-institutional
    public float) for the matching quarter — or the nearest BSE quarter carrying a
    split, honestly stamped via ``split_source``/``split_as_of``. A BSE-only name
    (or one the NSE lane cannot serve) is served from the BSE lane directly. Every
    pattern carries a ``source`` label ("NSE"/"BSE"), a ``public_basis`` label
    ("incl. institutions"), and its as-of quarter; a lane that is applicable but
    fails is recorded and the next lane is tried, and no figure is ever fabricated.
    """
    bare = locale.strip_exchange_suffix(symbol.strip().upper())
    if not bare:
        raise ProviderError("disclosures: empty symbol")
    is_bse = symbol_resolver.is_bse_symbol(bare)
    lanes: list[tuple[str, bool, object]] = [
        (EXCHANGE_NSE, symbol_resolver.is_nse_symbol(bare), _nse_shareholding),
        (EXCHANGE_BSE, is_bse, _bse_shareholding),
    ]
    applicable = [(name, fetch) for name, listed, fetch in lanes if listed]
    if not applicable:
        # A US-listed ADR's 20-F holders ride on top: sec_ownership.attach_major_shareholders.
        return ShareholdingResponse(symbol=bare, count=0, **_not_applicable(bare))

    errors: dict[str, str] = {}
    for name, fetch in applicable:  # NSE first — it wins for a dual-listed name
        try:
            patterns = fetch(bare)
        except ProviderError as exc:
            logger.debug("disclosures: %s shareholding failed for %s: %s", name, bare, exc)
            errors[name] = str(exc)
            continue
        if patterns:
            # A dual-listed NSE result recovers its FII/DII split from the BSE
            # SEBI XBRL (the NSE master carries none) — the highest-leverage fix.
            # Only when the BSE scrip under this ticker IS the NSE company: a
            # same-ticker BSE scrip of another company (NSE FOCUS = Focus
            # Lighting, BSE FOCUS = Focus Business Solution) would stamp that
            # company's split onto this one, so the split stays None instead.
            if name == EXCHANGE_NSE and symbol_resolver.dual_listed_bse_code(bare):
                patterns = _merge_bse_split(bare, patterns)
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
                # The NSE master's ``public_val`` is the exchange "Public"
                # category — it FOLDS institutions in. Label it so no consumer
                # reads it as the non-institutional float (the BSE merge fills
                # in ``public_non_institutional_percent`` for a dual-listed name).
                public_percent=_pct(row.get("public_val")),
                public_basis=PUBLIC_BASIS_INCL_INSTITUTIONS,
                public_non_institutional_percent=None,
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
        submission = row.get("submission_date")
        xbrl_url = _clean(row.get("xbrl_url"))
        quarter_basis = None
        if not isinstance(quarter_end, date):
            # A filed pattern is never dropped over a period label the parser
            # does not know (R15-DATA-022): it is dated by its filing, and says so.
            if not (xbrl_url and isinstance(submission, date)):
                continue
            quarter_end = submission
            quarter_basis = f"filing date; the BSE period {row.get('period')!r} was not parsed"
        patterns.append(
            ShareholdingPattern(
                symbol=bare,
                quarter_end=quarter_end,
                quarter_basis=quarter_basis,
                promoter_percent=_as_float(row.get("promoter_percent")),
                fii_percent=_as_float(row.get("fii_percent")),
                dii_percent=_as_float(row.get("dii_percent")),
                institutions_percent=_as_float(row.get("institutions_percent")),
                # The BSE "Public" category (``PublicShareholdingMember``) also
                # includes institutions; the non-institutional slice rides its
                # own field. Both labeled for an unambiguous read.
                public_percent=_as_float(row.get("public_percent")),
                public_basis=PUBLIC_BASIS_INCL_INSTITUTIONS,
                public_non_institutional_percent=_as_float(
                    row.get("public_non_institutional_percent")
                ),
                employee_trusts_percent=None,
                split_basis=row.get("split_basis"),
                promoter_pledged_percent=_as_float(row.get("promoter_pledged_percent")),
                promoter_pledge_basis=row.get("promoter_pledge_basis"),
                submission_date=submission if isinstance(submission, date) else None,
                xbrl_url=xbrl_url,
                source=EXCHANGE_BSE,
            )
        )
    return patterns


def _pattern_has_split(pattern: ShareholdingPattern) -> bool:
    """True when a BSE pattern carries any of the institution split fields —
    the parts the NSE master lacks and the merge exists to recover."""
    return (
        pattern.institutions_percent is not None
        or pattern.fii_percent is not None
        or pattern.dii_percent is not None
    )


#: The farthest a BSE quarter may sit from an NSE pattern and still lend it its
#: split: one quarter plus the filing lag (D-B3-11). The BSE lane parses only a
#: few recent XBRLs, so without a bound years of NSE quarters carried one split
#: (SIL 2021-09..2024-09 all showed 2024-12's, up to 1,188 days away).
_SPLIT_MERGE_MAX_DAYS = 100


def _merge_bse_split(
    bare: str, nse_patterns: list[ShareholdingPattern]
) -> list[ShareholdingPattern]:
    """Enrich NSE-master patterns with the BSE SEBI-XBRL institution split.

    For each NSE quarter, the split (institutions/FII/DII + the non-institutional
    public float) is taken from the BSE pattern of the SAME quarter-end, or — when
    that quarter has not filed on BSE yet — the NEAREST BSE quarter that carries a
    split, if it is within :data:`_SPLIT_MERGE_MAX_DAYS`, stamped
    ``split_source="BSE"`` + ``split_as_of=<that quarter>`` so a
    consumer sees the as-of honestly (never silently aligned). The BSE lane failing
    or carrying no split is a no-op: the labeled NSE patterns stand unchanged (the
    split stays ``None``, never fabricated).
    """
    try:
        bse_patterns = _bse_shareholding(bare)
    except Exception as exc:  # noqa: BLE001 — best-effort enrichment over an
        # already-successful NSE lane must never break it (same doctrine as the
        # dividend cross-check, services.dividend_history) — a bug/timeout deep
        # in the BSE lane (e.g. an unexpected KeyError from bse_provider) must
        # degrade to "no split enrichment", never surface as a 500.
        logger.debug("disclosures: BSE split enrich unavailable for %s: %s", bare, exc)
        return nse_patterns
    with_split = [p for p in bse_patterns if _pattern_has_split(p)]
    if not with_split:
        return nse_patterns
    with_split.sort(key=lambda p: p.quarter_end, reverse=True)
    by_quarter = {p.quarter_end: p for p in with_split}
    enriched: list[ShareholdingPattern] = []
    for pattern in nse_patterns:
        match = by_quarter.get(pattern.quarter_end)
        if match is None:
            nearest = min(with_split, key=lambda p: abs((p.quarter_end - pattern.quarter_end).days))
            if abs((nearest.quarter_end - pattern.quarter_end).days) <= _SPLIT_MERGE_MAX_DAYS:
                match = nearest
        if match is None:
            enriched.append(pattern)  # no BSE quarter close enough: the split stays None
            continue
        enriched.append(
            pattern.model_copy(
                update={
                    "fii_percent": match.fii_percent,
                    "dii_percent": match.dii_percent,
                    "institutions_percent": match.institutions_percent,
                    "public_non_institutional_percent": match.public_non_institutional_percent,
                    "split_source": EXCHANGE_BSE,
                    "split_as_of": match.quarter_end,
                    "split_basis": match.split_basis,
                    # The pledge rides the same filing as the split (R15-DATA-023).
                    "promoter_pledged_percent": match.promoter_pledged_percent,
                    "promoter_pledge_basis": match.promoter_pledge_basis,
                }
            )
        )
    return enriched


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
    "DEAL_KINDS",
    "DEFAULT_LIMIT",
    "EXCHANGES",
    "EXCHANGE_BSE",
    "EXCHANGE_NSE",
    "MAX_LIMIT",
    "get_announcements",
    "get_announcements_cached",
    "get_corporate_actions",
    "get_deals",
    "get_results_calendar",
    "get_shareholding",
]
