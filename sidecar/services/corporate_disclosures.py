"""Corporate disclosures — merged BSE+NSE announcements, results, shareholding.

R7 Component 3. Models the RAW exchange feeds into the typed shapes in
:mod:`models.announcements` for the ``/disclosures`` router and the
``corporate_announcements`` / ``shareholding_pattern`` agent tools:

* **Announcements** — merged from BOTH exchange feeds, newest first. A
  within-feed re-dissemination collapses on ``(symbol, body-prefix-hash,
  date)``; an NSE item and a BSE item of one filing pair on the same day, a
  short dissemination gap and similar text (:func:`_pair_cross_feed`):

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

* **Results calendar** — the NSE ``event-calendar`` feed (board meetings,
  results, dividends), parsed dates, newest first.

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
from datetime import UTC, date, datetime, timedelta

from models.announcements import (
    Announcement,
    AnnouncementsResponse,
    AnnouncementWindow,
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


def _pair_cross_feed(items: list[Announcement]) -> list[Announcement]:
    """Drop each BSE item that pairs with an NSE item of the same filing
    (R15-DATA-020); NSE wins a pair.

    Candidates share the symbol and IST day and were disseminated within
    :data:`_PAIR_WINDOW`. Their similarity is the word overlap of the NSE text
    against the BSE body or its subject, whichever is higher (BSE's body is
    often boilerplate — "Enclosed" — while its subject names the filing). Pairs
    are taken best-first (highest overlap, then the shortest gap) and each item
    pairs at most once, so two filings minutes apart each keep their own match.
    """
    nse = [i for i in items if i.exchange == EXCHANGE_NSE and i.ts is not None]
    bse = [i for i in items if i.exchange == EXCHANGE_BSE and i.ts is not None]
    candidates: list[tuple[float, float, int, int]] = []
    for n_idx, n_item in enumerate(nse):
        n_words = _words(n_item.headline)
        n_day = n_item.ts.astimezone(_ist()).date()
        for b_idx, b_item in enumerate(bse):
            gap = abs(n_item.ts - b_item.ts)
            if (
                n_item.symbol.upper() != b_item.symbol.upper()
                or gap > _PAIR_WINDOW
                or b_item.ts.astimezone(_ist()).date() != n_day
            ):
                continue
            score = max(
                _overlap(n_words, _words(b_item._body)), _overlap(n_words, _words(b_item.headline))
            )
            if score >= _PAIR_MIN_OVERLAP:
                candidates.append((-score, gap.total_seconds(), n_idx, b_idx))
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
        wanted = exchange or "NSE/BSE"
        raise ProviderError(f"disclosures: {bare!r} is not a known {wanted} instrument")

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
    "DEFAULT_LIMIT",
    "EXCHANGES",
    "EXCHANGE_BSE",
    "EXCHANGE_NSE",
    "MAX_LIMIT",
    "get_announcements",
    "get_announcements_cached",
    "get_results_calendar",
    "get_shareholding",
]
