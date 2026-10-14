"""The depositary ratio of an ADR, read off its newest 20-F cover page.

No bundled data source carries how many ordinary shares one ADS represents,
so the chat model stated one (R15-AGENT-090). The 20-F cover page does, under
"Securities registered pursuant to Section 12(b)": "American Depositary
Shares, each represented by Six Equity Shares" (SIFY), "each representing one
ordinary share" (INFY). This lane is keyless (EDGAR's submissions index + the
filing's primary document, as :mod:`services.sec_ownership` reads), exact —
the statement is quoted, the number parsed from it, never guessed — and cached
per symbol so the 5 MB filing is read once.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx

from services import data_cache, sec_filings_provider
from services.sec_ownership import _USER_AGENT, _text

_log = logging.getLogger(__name__)

_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
_ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"
#: Bounds the whole lookup (ticker map + two EDGAR reads), not one request:
#: fundamentals and financial_statements await it (R15-LEAD-032).
_TIMEOUT = 8.0
_TTL = 30 * 24 * 60 * 60  # a ratio changes by a ratio-change event, rarely
_MISS_TTL = 24 * 60 * 60

_NUMBER_WORDS = (
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
    "eighteen", "nineteen", "twenty",
)  # fmt: skip
#: The cover-page statement, in its two forms: "American Depositary Shares,
#: each representing / represented by N ordinary shares" and "Each American
#: Depositary Share / ADS represents N ordinary shares". ``N`` is an integer or
#: a number word; "one-half of one share" or "0.5" is no match — never a guess.
_STATEMENT = re.compile(
    r"(?:(?:American Depositary Shares?|ADSs?),?\s*(?:\(|\bof which\s+)?each\s+represent"
    r"(?:ing|s|ed by)|each\s+(?:American Depositary Share|ADS)\s+represent(?:ing|s|ed by))"
    r"\s+(?:the right to receive\s+)?"
    r"(?P<n>\d{1,3}|" + "|".join(_NUMBER_WORDS) + r")"
    r"(?:\s*\(\s*(?P<digits>\d{1,3})\s*\))?"
    r"(?:\s+(?:fully paid|paid[- ]up|new|deposited|underlying))*"
    r"\s+(?:ordinary|equity|common|class\s+[A-Z]\s+(?:ordinary|common)?)\s*shares?",
    re.IGNORECASE,
)
#: The cover page starts at the Section 12(b) registration table; the body
#: (a rights offering "each representing one equity share" of years ago) is
#: never read.
_COVER = re.compile(r"Section\s+12\s*\(\s*b\s*\)", re.IGNORECASE)
_COVER_WINDOW = 6000


def parse_cover_ratio(document: str) -> dict[str, Any] | None:
    """The ratio the 20-F cover page states, or ``None``.

    Returns ``{"ordinary_shares_per_ads": N, "statement": <the sentence>}``
    when the Section 12(b) table carries exactly one such statement (one
    distinct ratio), else ``None`` — a page without one, or one that names two
    different ratios, is not guessed at."""
    text = _text(document)
    anchor = _COVER.search(text)
    if anchor is None:
        return None
    window = text[anchor.start() : anchor.start() + _COVER_WINDOW]
    found: dict[int, str] = {}
    for match in _STATEMENT.finditer(window):
        word = match["n"].lower()
        n = int(word) if word.isdigit() else _NUMBER_WORDS.index(word) + 1
        if match["digits"] and int(match["digits"]) != n:
            return None
        found.setdefault(n, re.sub(r"\s+", " ", match.group()).strip())
    if len(found) != 1:
        return None
    n, statement = found.popitem()
    return {"ordinary_shares_per_ads": n, "statement": statement}


async def _get(url: str) -> httpx.Response:
    async with httpx.AsyncClient(
        headers={"User-Agent": _USER_AGENT}, timeout=_TIMEOUT, follow_redirects=True
    ) as client:
        resp = await client.get(url)
    resp.raise_for_status()
    return resp


async def _fetch(symbol: str) -> dict[str, Any] | None:
    tickers = await sec_filings_provider._load_company_tickers()
    cik = next(
        (
            str(row.get("cik_str") or "")
            for row in tickers.values()
            if isinstance(row, dict) and str(row.get("ticker") or "").upper() == symbol.upper()
        ),
        "",
    )
    if not cik.isdigit():
        return None
    recent = (await _get(_SUBMISSIONS_URL.format(cik=cik.zfill(10)))).json()["filings"]["recent"]
    filing = next(
        (
            (acc, doc, filed)
            for form, acc, doc, filed in zip(
                recent["form"],
                recent["accessionNumber"],
                recent["primaryDocument"],
                recent["filingDate"],
                strict=True,
            )
            if form == "20-F" and doc
        ),
        None,
    )
    if filing is None:
        return None
    acc, doc, filed = filing
    url = _ARCHIVE_URL.format(cik=cik, acc=acc.replace("-", ""), doc=doc)
    parsed = parse_cover_ratio((await _get(url)).text)
    if parsed is None:
        return None
    # Nested: the guard reads a result in segments, so the filing's own numbers
    # (20-F, a date) never count as sourced share counts.
    return {**parsed, "provenance": {"source": "SEC 20-F cover page", "filed": filed, "url": url}}


async def lookup(symbol: str) -> dict[str, Any] | None:
    """``symbol``'s depositary ratio from its newest 20-F cover page, cached;
    ``None`` when it files no 20-F, states no ratio, or EDGAR is unreachable.
    Never raises."""
    key = f"sec:ads-ratio:{symbol.upper()}"
    cached = await data_cache.get(key, _TTL)
    if isinstance(cached, dict):
        return cached or None
    if await data_cache.get(f"{key}:miss", _MISS_TTL) is not None:
        return None
    try:
        found = await asyncio.wait_for(_fetch(symbol), _TIMEOUT)
    except Exception as exc:  # noqa: BLE001 — an unreachable EDGAR is a miss, not a fault
        # ponytail: a cold fetch slower than _TIMEOUT caches a 24 h miss (an honest
        # absence; the ratio guard still defends); complete it in the background
        # if the live bar shows real ADRs missing.
        _log.warning("adr_ratio %s: %r", symbol, exc)
        await data_cache.set(f"{key}:miss", {})
        return None
    await data_cache.set(key if found else f"{key}:miss", found or {})
    return found
