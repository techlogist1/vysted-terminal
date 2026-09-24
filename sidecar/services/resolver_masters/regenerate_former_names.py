"""Regenerate ``former_names.json`` — the bundled former-company-name master.

NOT run at build/CI time (the bundled JSON is committed and read offline, exactly
like ``bse_instruments.json``/``nse_instruments.json``). Run this by hand to
refresh the snapshot.

R15-DATA-059: a query by a company's RETIRED legal name ("BeiGene" for the
listing now named ONC/BeOne Medicines) resolved to nothing (or a wrong fuzzy
match), because the name scan only ever compared against each instrument's
CURRENT name. This master supplies the missing former-name index the resolver
scan joins against (:func:`services.symbol_resolver._former_names`).

Sources
~~~~~~~

* **US** — SEC EDGAR ``submissions`` API's ``formerNames`` array, one call per
  CIK: ``https://data.sec.gov/submissions/CIK{cik:010d}.json``. The
  ticker→CIK map comes from SEC's bulk ``company_tickers.json`` (one request,
  no per-row cost). Every ticker in the bundled ``us_instruments.json`` that
  SEC's bulk file also knows is crawled. SEC's fair-access policy caps
  automated access at 10 req/s with an identifying UA — this crawl batches
  requests 10-wide and paces each batch to take >= 1s wall-clock.
* **IN** — NSE's own company name-change file (the sibling of the
  ``symbolchange.csv`` :mod:`services.nse_symbol_change` already reads),
  keyed by the CURRENT NSE symbol with the previous + new legal name:
  ``https://nsearchives.nseindia.com/content/equities/namechange.csv``. One
  request, no pacing needed (already a single cumulative file, like
  ``symbolchange.csv``).
* **Manual seed** (:data:`_MANUAL_SEED`) — a small, individually-cited table
  for verified renames neither automated source carries (a BSE-only SME
  listing has no NSE symbol to key the NSE file on), mirroring how
  ``marquee_aliases.json`` is hand-curated rather than crawled.

Output shape (matches what ``symbol_resolver._former_names`` parses)::

    {"_generated": "<UTC date>",
     "_source": "SEC EDGAR submissions formerNames (US) + NSE namechange.csv (IN) + manual seed",
     "former_names": {"us": {SYMBOL: [name, ...]}, "in": {SYMBOL: [name, ...]}}}

A duplicate former name for the same symbol is deduped (order-preserving); the
manual seed is merged in last so a hand-verified name always survives a
crawl-shape change.

Usage::

    python -m services.resolver_masters.regenerate_former_names [--limit N]
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_HERE = Path(__file__).parent
_OUTPUT = _HERE / "former_names.json"
_US_MASTER = _HERE / "us_instruments.json"

_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
_NAMECHANGE_URL = "https://nsearchives.nseindia.com/content/equities/namechange.csv"

# SEC asks for an identifying UA (fair-access policy); NSE just wants a normal
# browser UA (no BSE-style WAF on this archive host).
_SEC_UA = "vysted-terminal-r15-data059/1.0 (research; data059@vysted.local)"
_NSE_UA = "Mozilla/5.0 (compatible; VystedTerminal/1.0)"

_SEC_BATCH = 10  # SEC fair-access ceiling is 10 req/s; one batch per second.

# BSE-only / SME renames a listed-exchange name-change file does not carry
# (verified from the company's own filing, not crawled) — R15-DATA-059
# register evidence (docs/redesign/verification/r15/battery/packs/S4_TTC.json).
_MANUAL_SEED: dict[str, dict[str, list[str]]] = {
    "in": {
        # Toss The Coin Ltd (BSE SME, scrip 544303) — FY2025-26 annual report's
        # covering letter to BSE, dated 2026-08-14: "Toss The Coin Limited
        # (Formerly known as Toss the Coin Pvt Ltd)". BSE-only (no NSE symbol),
        # so nsearchives' NSE-only namechange.csv never carries this row.
        "TTC": ["Toss the Coin Private Limited"],
    },
}


def _us_symbols() -> list[str]:
    raw = json.loads(_US_MASTER.read_text(encoding="utf-8"))
    return [str(row[0]).strip().upper() for row in raw.get("instruments", []) if row]


async def _fetch_ticker_cik_map(client: httpx.AsyncClient) -> dict[str, int]:
    resp = await client.get(_TICKERS_URL)
    resp.raise_for_status()
    out: dict[str, int] = {}
    for row in resp.json().values():
        ticker = str(row.get("ticker") or "").strip().upper()
        cik = row.get("cik_str")
        if ticker and isinstance(cik, int):
            out[ticker] = cik
    return out


async def _fetch_former_names_one(client: httpx.AsyncClient, cik: int) -> list[str]:
    """Former legal names for one CIK, oldest→newest, or ``[]`` on any miss."""
    try:
        resp = await client.get(_SUBMISSIONS_URL.format(cik=cik))
    except httpx.HTTPError as exc:
        logger.debug("former_names: CIK %s request failed: %s", cik, exc)
        return []
    if resp.status_code != 200:
        return []
    try:
        data = resp.json()
    except ValueError:
        return []
    names = [str(row["name"]).strip() for row in data.get("formerNames", []) if row.get("name")]
    return names


async def crawl_us(symbols: list[str], *, limit: int | None = None) -> dict[str, list[str]]:
    """``{TICKER: [former_name, ...]}`` for every crawlable US ticker.

    Paced 10-wide/second (SEC fair-access). A ticker SEC's bulk map does not
    know, or whose submissions call errors, is silently absent (best-effort —
    a partial crawl never blocks the release; the resolver degrades to no
    former-name match for that ticker exactly as it does today)."""
    out: dict[str, list[str]] = {}
    async with httpx.AsyncClient(headers={"User-Agent": _SEC_UA}, timeout=15.0) as client:
        tick2cik = await _fetch_ticker_cik_map(client)
        known = [(sym, tick2cik[sym]) for sym in symbols if sym in tick2cik]
        if limit is not None:
            known = known[:limit]
        logger.info("former_names(us): crawling %d/%d tickers", len(known), len(symbols))
        for start in range(0, len(known), _SEC_BATCH):
            batch = known[start : start + _SEC_BATCH]
            t0 = time.monotonic()
            results = await asyncio.gather(
                *(_fetch_former_names_one(client, cik) for _sym, cik in batch)
            )
            for (sym, _cik), names in zip(batch, results, strict=True):
                if names:
                    out[sym] = names
            elapsed = time.monotonic() - t0
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)
            done = start + len(batch)
            if done % 500 == 0 or done == len(known):
                logger.info(
                    "former_names(us): %d/%d done, %d with a former name",
                    done,
                    len(known),
                    len(out),
                )
    return out


def _parse_namechange(text: str) -> dict[str, list[str]]:
    """``{SYMBOL: [former_name, ...]}`` from NSE's namechange.csv body.

    One header row (``NCH_SYMBOL, NCH_PREV_NAME, NCH_NEW_NAME, NCH_DT``),
    sorted oldest-first in the source; a symbol with several renames over the
    decades keeps every distinct prior name, order-preserving, deduped."""
    out: dict[str, list[str]] = {}
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if len(row) < 3:
            continue
        symbol = row[0].strip().upper()
        prev_name = row[1].strip()
        if symbol in ("", "NCH_SYMBOL") or not prev_name or prev_name == "NCH_PREV_NAME":
            continue
        names = out.setdefault(symbol, [])
        if prev_name not in names:
            names.append(prev_name)
    return out


async def crawl_in() -> dict[str, list[str]]:
    async with httpx.AsyncClient(headers={"User-Agent": _NSE_UA}, timeout=20.0) as client:
        resp = await client.get(_NAMECHANGE_URL)
        resp.raise_for_status()
    parsed = _parse_namechange(resp.text)
    logger.info("former_names(in): %d NSE symbols with a prior name", len(parsed))
    return parsed


def _merge_seed(
    crawled: dict[str, list[str]], seeded: dict[str, list[str]]
) -> dict[str, list[str]]:
    out = {sym: list(names) for sym, names in crawled.items()}
    for sym, names in seeded.items():
        existing = out.setdefault(sym, [])
        for name in names:
            if name not in existing:
                existing.append(name)
    return out


async def regenerate(*, limit: int | None = None, us: bool = True, in_: bool = True) -> dict:
    former_names: dict[str, dict[str, list[str]]] = {"us": {}, "in": {}}
    if us:
        former_names["us"] = crawl_result_us = await crawl_us(_us_symbols(), limit=limit)
        former_names["us"] = _merge_seed(crawl_result_us, _MANUAL_SEED.get("us", {}))
    if in_:
        crawl_result_in = await crawl_in()
        former_names["in"] = _merge_seed(crawl_result_in, _MANUAL_SEED.get("in", {}))
    elif "in" in _MANUAL_SEED:
        former_names["in"] = _merge_seed({}, _MANUAL_SEED["in"])
    payload = {
        "_generated": datetime.now(UTC).date().isoformat(),
        "_source": "SEC EDGAR submissions formerNames (US) + NSE namechange.csv (IN) + manual seed",
        "former_names": former_names,
    }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="cap the US crawl (debug/dev only)")
    parser.add_argument("--us-only", action="store_true")
    parser.add_argument("--in-only", action="store_true")
    parser.add_argument("--out", type=Path, default=_OUTPUT)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    payload = asyncio.run(
        regenerate(
            limit=args.limit,
            us=not args.in_only,
            in_=not args.us_only,
        )
    )
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    us_count = len(payload["former_names"]["us"])
    in_count = len(payload["former_names"]["in"])
    logger.info("former_names: wrote %s (us=%d, in=%d)", args.out, us_count, in_count)


if __name__ == "__main__":
    main()
