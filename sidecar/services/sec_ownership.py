"""Major holders of a US-listed foreign issuer, read from its latest 20-F.

An ADR such as SIFY or WIT has no Indian shareholding pattern, but its 20-F
(Item 7.A, "Major Shareholders") names every 5%-or-more holder. This lane
finds the newest 20-F through the sec-edgar-mcp filings index, fetches the
primary document from EDGAR (the index page names it) and parses the holders
table. It rides on top of a ``not_applicable`` shareholding answer and never
merges into the Indian ``patterns`` (R15-DATA-060).

sec-edgar-mcp cannot serve the text itself: it returns no sections for a 20-F
and truncates filing content at 50K characters, well before Item 7.
"""

from __future__ import annotations

import html
import logging
import re
from datetime import date, datetime

import httpx

from models.announcements import MajorShareholder, ShareholdingResponse
from services import data_cache, sec_filings_provider
from services.errors import ProviderError

logger = logging.getLogger(__name__)

#: SEC fair-access guidance wants a contact UA (same as the MCP subprocess).
_USER_AGENT = "Vysted Terminal (contact: support@vysted.com)"
_SEC_BASE = "https://www.sec.gov"
_TIMEOUT = 60.0
_TTL = 24 * 60 * 60

_CELL = re.compile(
    r"(?:\d{1,3}(?:,\d{2,3})+|\d{4,}|-)\s+(?:\(\w{1,3}\)\s+)?(\d{1,3}\.\d{1,2}|-)\s*%?"
)
_HEADER_END = re.compile(r"%|Percent(?:age)?|Outstanding|\b(?:19|20)\d{2}\b")
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_AS_OF = re.compile(r"as of\s+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})")
#: Text between two rows longer than this ends the table (a footnote/paragraph).
_MAX_ROW_GAP = 160
_WINDOW = 8000


def _text(document: str) -> str:
    text = re.sub(r"<[^>]+>", " ", document)
    return re.sub(r"\s+", " ", html.unescape(text))


def _clean_holder(raw: str) -> str:
    holder = re.sub(r"\(\w{1,3}\)|\*", " ", raw)
    holder = re.sub(r"^(?:\s*Equity\b)+|(?:\bEquity\s*)+$", " ", holder.strip())
    return re.sub(r"\s+", " ", holder).strip(" ,;:")


def parse_major_shareholders(document: str) -> tuple[list[MajorShareholder], date | None]:
    """The Item 7.A holders table of a 20-F (HTML or text) and its as-of date.

    Each row is ``holder shares pct`` repeated once per reported date. When
    the header's dates run newest-first the first column is served, else the
    last. Returns ``([], None)`` when no table is found."""
    text = _text(document)
    anchor = next(
        (
            m.start()
            for m in re.finditer(r"major shareholders", text, re.IGNORECASE)
            if re.search("beneficial", text[m.start() : m.start() + 400], re.IGNORECASE)
        ),
        None,
    )
    if anchor is None:
        return [], None
    section = text[anchor : anchor + _WINDOW]
    as_of_match = _AS_OF.search(section)
    as_of = None
    if as_of_match:
        try:
            as_of = datetime.strptime(as_of_match.group(1), "%B %d, %Y").date()
        except ValueError:
            as_of = None

    rows: list[tuple[str, list[str]]] = []
    header = ""
    cursor = 0
    for cell in _CELL.finditer(section):
        gap = section[cursor : cell.start()]
        if not rows:
            header = gap
            ends = list(_HEADER_END.finditer(gap))
            rows.append((gap[ends[-1].end() :] if ends else gap, [cell.group(1)]))
        elif not gap.strip():
            rows[-1][1].append(cell.group(1))
        elif len(gap) > _MAX_ROW_GAP:
            break
        else:
            rows.append((gap, [cell.group(1)]))
        cursor = cell.end()
    if not rows:
        return [], as_of

    columns = len(rows[0][1])
    years = [int(y) for y in _YEAR.findall(header)][-columns:]
    newest_first = columns > 1 and len(years) == columns and years == sorted(years, reverse=True)
    pick = 0 if newest_first else -1
    holders = []
    for raw, cells in rows:
        if len(cells) != columns:
            break
        name = _clean_holder(raw)
        if not name:
            continue
        value = cells[pick]
        holders.append(
            MajorShareholder(
                holder=name, percent=None if value == "-" else float(value), as_of=as_of
            )
        )
    return holders, as_of


async def _fetch_text(url: str) -> str:
    """GET one EDGAR page. Raises :class:`ProviderError` on any failure."""
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": _USER_AGENT}, timeout=_TIMEOUT, follow_redirects=True
        ) as client:
            resp = await client.get(url)
    except httpx.HTTPError as exc:
        raise ProviderError(f"sec 20-F: transport failure: {exc}") from exc
    if resp.status_code != 200:
        raise ProviderError(f"sec 20-F: HTTP {resp.status_code} for {url}")
    return resp.text


def _primary_document(index_page: str) -> str | None:
    """The first document link of an EDGAR filing index page (inline-XBRL
    links carry an ``/ix?doc=`` prefix)."""
    match = re.search(r'href="(?:/ix\?doc=)?(/Archives/edgar/data/[^"]+\.htm)"', index_page)
    return f"{_SEC_BASE}{match.group(1)}" if match else None


async def latest_20f_holders(symbol: str) -> tuple[list[MajorShareholder], str, date] | None:
    """The holders of ``symbol``'s newest 20-F with its URL and filing date, or
    ``None`` when it files no 20-F (or sec-edgar-mcp is not bundled). Raises
    :class:`ProviderError` when a 20-F exists but cannot be read."""
    if not sec_filings_provider.is_available():
        return None
    listing = await sec_filings_provider.list_filings(symbol, form_type="20-F", limit=5)  # type: ignore[arg-type]
    filing = next((f for f in listing.filings if f.form_type == "20-F"), None)
    if filing is None:
        return None
    cache_key = f"sec:20f-holders:{filing.accession}"
    cached = await data_cache.get(cache_key, _TTL)
    if isinstance(cached, dict):
        holders = [MajorShareholder.model_validate(row) for row in cached["holders"]]
        return holders, cached["url"], filing.filed_date
    index = await _fetch_text(f"{filing.edgar_url}{filing.accession}-index.htm")
    url = _primary_document(index)
    if url is None:
        raise ProviderError(f"sec 20-F: no primary document on {filing.accession}'s index")
    holders, _ = parse_major_shareholders(await _fetch_text(url))
    await data_cache.set(
        cache_key, {"url": url, "holders": [h.model_dump(mode="json") for h in holders]}
    )
    return holders, url, filing.filed_date


async def attach_major_shareholders(response: ShareholdingResponse) -> ShareholdingResponse:
    """Serve a not-applicable shareholding answer's 20-F holders, if any.

    A covered (NSE/BSE) answer is returned untouched. A 20-F that exists but
    cannot be read keeps the answer ``not_applicable`` and says why."""
    if response.coverage != "not_applicable":
        return response
    try:
        found = await latest_20f_holders(response.symbol)
    except ProviderError as exc:
        logger.warning("sec_ownership: %s: %s", response.symbol, exc)
        return response.model_copy(
            update={"note": f"{response.note}; its 20-F holders could not be read ({exc})"}
        )
    if found is None or not found[0]:
        return response
    holders, url, filed = found
    note = (
        f"{response.symbol} is not an NSE/BSE instrument; its major (5%+) holders are read "
        f"from its 20-F filed {filed.isoformat()} (Item 7.A), not an Indian shareholding pattern"
    )
    return response.model_copy(
        update={
            "coverage": "covered",
            "note": note,
            "provider": "sec-20f",
            "major_shareholders": holders,
            "source_url": url,
        }
    )


__all__ = ["attach_major_shareholders", "latest_20f_holders", "parse_major_shareholders"]
