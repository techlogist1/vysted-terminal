"""Regenerate ``india_sector_map.json`` — the bundled India sector/shares map (R10, D40).

NOT run at build/CI time (the bundled JSON is committed and read offline, exactly
like ``bse_instruments.json``). Run by hand to refresh the snapshot, mirroring
``regenerate_bse_master.py``.

Sources (all bseindia.com; ``curl_cffi`` Chrome impersonation, httpx fallback):

  1. ``ListOfScripData`` (one bulk call) — every Active equity scrip with
     SCRIP_CD / scrip_id / ISIN / GROUP / Mktcap (crores INR). The payload's
     ``INDUSTRY`` field is honoured when BSE populates it, but as observed live
     (2026-06-12) it is ``null`` on every record — the bulk industry source the
     original D40 design assumed is gone, so sector classification falls to (3).
  2. The equity bhavcopy CSV (one call, latest trading day, walks back up to
     7 days) — ``ClsPric`` per scrip code, so ``shares_outstanding`` derives as
     ``Mktcap(crores) × 1e7 / close`` at snapshot time.
  3. ``ComHeadernew`` (per-scrip, top ``--crawl`` records by Mktcap) — BSE's
     official harmonized classification: ``IndustryNew`` (the closed 22-value
     vocabulary from ``ddlIndustry``) + ``ISubGroup`` (kept as ``industry_raw``).
     ``IndustryNew`` maps to the Yahoo 11-sector vocabulary via the hand table
     below — every distinct live string is covered; unknown → ``null``, never a
     guess. Throttled with jitter; sustained hostility aborts the crawl and
     ships whatever was gathered (partial coverage is honest, see header).
  4. ``--fallback-yfinance N`` — when BSE refuses the per-scrip crawl entirely,
     sector comes from per-symbol yfinance ``.info`` for the top N records
     joined to NSE symbols (Yahoo vocabulary verbatim, ``sector_source:
     "yfinance"``). The runtime warm crawler backfills the rest.

Output shape (header + one record per line for reviewable diffs)::

    {
      "_generated": "...", "_source": "...", "_note": "...",
      "coverage": {"records": N, "with_sector": M, "with_shares": K,
                   "sector_sources": {"bse": M}},
      "records": [
        {"symbol": "RELIANCE", "isin": "INE002A01018", "scrip_code": "500325",
         "industry_raw": "Oil, Gas & Consumable Fuels / Refineries & Marketing",
         "sector": "Energy", "sector_source": "bse",
         "shares_outstanding": 1.13e10}, ...
      ]
    }

Usage::

    python -m services.resolver_masters.regenerate_india_sectors \
        [--crawl 800] [--fallback-yfinance 600] > india_sector_map.json

(Nothing here is imported at runtime — ``screener_universe_india`` only reads
the committed JSON.)
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import random
import sys
import time
from datetime import UTC, datetime, timedelta
from typing import Any, TextIO

LIST_URL = (
    "https://api.bseindia.com/BseIndiaAPI/api/ListOfScripData/w"
    "?Group=&Scripcode=&industry=&segment=Equity&status=Active"
)
HEADER_URL = (
    "https://api.bseindia.com/BseIndiaAPI/api/ComHeadernew/w"
    "?quotetype=EQ&scripcode={code}&seriesid="
)
BHAVCOPY_URL = (
    "https://www.bseindia.com/download/BhavCopy/Equity/"
    "BhavCopy_BSE_CM_0_0_0_{yyyymmdd}_F_0000.CSV"
)
_REFERER = "https://www.bseindia.com/"
_FALLBACK_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_TIMEOUT = 40.0
_BULK_ATTEMPTS = 4
_BACKOFF_BASE = 1.5
# Sanity floor mirroring regenerate_bse_master: a tiny payload is a WAF block.
_MIN_ROWS = 1000
# Per-scrip crawl discipline: jittered sleep between calls; this many
# CONSECUTIVE failures means BSE is hostile tonight — stop, keep the partial.
_CRAWL_SLEEP_RANGE = (0.35, 0.85)
_CRAWL_MAX_CONSECUTIVE_FAILURES = 12

# --- BSE IndustryNew (harmonized 22-value vocabulary, ddlIndustry 2026-06-12)
# → Yahoo 11-sector vocabulary. Every distinct live string is covered;
# "Diversified" is genuinely unclassifiable → None (never a guess).
_INDUSTRY_NEW_TO_YAHOO: dict[str, str | None] = {
    "automobile and auto components": "Consumer Cyclical",
    "capital goods": "Industrials",
    "chemicals": "Basic Materials",
    "construction": "Industrials",
    "construction materials": "Basic Materials",
    "consumer durables": "Consumer Cyclical",
    "consumer services": "Consumer Cyclical",
    "diversified": None,
    "fast moving consumer goods": "Consumer Defensive",
    "financial services": "Financial Services",
    "forest materials": "Basic Materials",
    "healthcare": "Healthcare",
    "information technology": "Technology",
    "media, entertainment & publication": "Communication Services",
    "metals & mining": "Basic Materials",
    "oil, gas & consumable fuels": "Energy",
    "power": "Utilities",
    "realty": "Real Estate",
    # Harmonized "Services" = commercial services / transport / logistics —
    # Yahoo classes these Industrials; the ISubGroup rides industry_raw.
    "services": "Industrials",
    "telecommunication": "Communication Services",
    "textiles": "Consumer Cyclical",
    "utilities": "Utilities",
}

# --- Legacy bulk-INDUSTRY strings (the pre-harmonization subgroup vocabulary
# the original D40 design expected on ListOfScripData). Kept so a restored
# bulk field maps without a re-crawl. Unknown → None.
_LEGACY_INDUSTRY_TO_YAHOO: dict[str, str | None] = {
    "it - software": "Technology",
    "it - services": "Technology",
    "it - hardware": "Technology",
    "computers - software": "Technology",
    "it consulting & software": "Technology",
    "banks": "Financial Services",
    "bank - private": "Financial Services",
    "bank - public": "Financial Services",
    "finance": "Financial Services",
    "finance (including nbfcs)": "Financial Services",
    "nbfc": "Financial Services",
    "non banking financial company (nbfc)": "Financial Services",
    "housing finance": "Financial Services",
    "asset management": "Financial Services",
    "insurance": "Financial Services",
    "stock/ commodity brokers": "Financial Services",
    "pharmaceuticals": "Healthcare",
    "pharmaceuticals & drugs": "Healthcare",
    "hospital": "Healthcare",
    "hospitals & healthcare services": "Healthcare",
    "healthcare services": "Healthcare",
    "refineries & marketing": "Energy",
    "refineries": "Energy",
    "oil exploration": "Energy",
    "oil marketing & distribution": "Energy",
    "gas distribution": "Energy",
    "coal": "Energy",
    "iron & steel": "Basic Materials",
    "steel": "Basic Materials",
    "cement": "Basic Materials",
    "cement & cement products": "Basic Materials",
    "aluminium": "Basic Materials",
    "mining": "Basic Materials",
    "fertilizers": "Basic Materials",
    "specialty chemicals": "Basic Materials",
    "commodity chemicals": "Basic Materials",
    "paints": "Basic Materials",
    "paper & paper products": "Basic Materials",
    "auto": "Consumer Cyclical",
    "automobiles": "Consumer Cyclical",
    "auto ancillaries": "Consumer Cyclical",
    "auto components & equipments": "Consumer Cyclical",
    "passenger cars & utility vehicles": "Consumer Cyclical",
    "2/3 wheelers": "Consumer Cyclical",
    "tyres & rubber products": "Consumer Cyclical",
    "textiles": "Consumer Cyclical",
    "retailing": "Consumer Cyclical",
    "hotels & restaurants": "Consumer Cyclical",
    "leisure": "Consumer Cyclical",
    "garments & apparels": "Consumer Cyclical",
    "media & entertainment": "Communication Services",
    "telecom - services": "Communication Services",
    "telecom services": "Communication Services",
    "power generation": "Utilities",
    "power - generation": "Utilities",
    "electric utilities": "Utilities",
    "realty": "Real Estate",
    "residential, commercial projects": "Real Estate",
    "fmcg": "Consumer Defensive",
    "personal products": "Consumer Defensive",
    "packaged foods": "Consumer Defensive",
    "sugar": "Consumer Defensive",
    "edible oil": "Consumer Defensive",
    "breweries & distilleries": "Consumer Defensive",
    "cigarettes & tobacco products": "Consumer Defensive",
}


def map_industry_to_sector(industry: str | None) -> str | None:
    """Map a BSE industry string (harmonized or legacy) to the Yahoo 11-sector
    vocabulary. Unknown → ``None`` — an unmapped sector is honest, a guessed
    one poisons every sector screen."""
    if not industry:
        return None
    key = industry.strip().casefold()
    if key in _INDUSTRY_NEW_TO_YAHOO:
        return _INDUSTRY_NEW_TO_YAHOO[key]
    return _LEGACY_INDUSTRY_TO_YAHOO.get(key)


# ---------------------------------------------------------------------------
# HTTP plumbing (curl_cffi primary, httpx fallback — same as the BSE master).
# ---------------------------------------------------------------------------


def _get(url: str, *, accept: str = "application/json") -> Any:
    try:
        from curl_cffi import requests as creq

        return creq.get(
            url,
            impersonate="chrome",
            timeout=_TIMEOUT,
            headers={"Referer": _REFERER, "Accept": accept},
        )
    except ImportError:
        import httpx

        return httpx.get(
            url,
            timeout=_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": _FALLBACK_UA, "Referer": _REFERER, "Accept": accept},
        )


def fetch_bulk_records() -> list[dict]:
    """The single bulk ``ListOfScripData`` call, retried with backoff+jitter."""
    last_exc: Exception | None = None
    for attempt in range(1, _BULK_ATTEMPTS + 1):
        try:
            resp = _get(LIST_URL)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code} from ListOfScripData")
            payload = resp.json()
            records = payload if isinstance(payload, list) else payload.get("Table", [])
            if not isinstance(records, list) or len(records) < _MIN_ROWS:
                shape = len(records) if isinstance(records, list) else type(records).__name__
                raise RuntimeError(f"suspicious payload ({shape} records)")
            return records
        except Exception as exc:  # noqa: BLE001 - every failure mode retries the same way
            last_exc = exc
            if attempt < _BULK_ATTEMPTS:
                wait = _BACKOFF_BASE * (2 ** (attempt - 1)) + random.uniform(0.0, 0.5)
                print(
                    f"regenerate_india_sectors: bulk attempt {attempt}/{_BULK_ATTEMPTS} "
                    f"failed ({exc}); retrying in {wait:.1f}s",
                    file=sys.stderr,
                )
                time.sleep(wait)
    raise SystemExit(f"regenerate_india_sectors: bulk fetch failed: {last_exc}")


def fetch_closes() -> dict[str, float]:
    """``{scrip_code: close}`` from the latest available equity bhavcopy.

    Walks back up to 7 days (weekends/holidays); best-effort — an empty dict
    just leaves ``shares_outstanding`` null on every record."""
    today = datetime.now(tz=UTC).date()
    for back in range(0, 7):
        day = today - timedelta(days=back)
        url = BHAVCOPY_URL.format(yyyymmdd=day.strftime("%Y%m%d"))
        try:
            resp = _get(url, accept="*/*")
        except Exception as exc:  # noqa: BLE001 - try the previous day
            print(f"regenerate_india_sectors: bhavcopy {day} failed: {exc}", file=sys.stderr)
            continue
        if resp.status_code != 200 or len(resp.content) < 10_000:
            continue
        closes: dict[str, float] = {}
        reader = csv.DictReader(io.StringIO(resp.text))
        for row in reader:
            code = (row.get("FinInstrmId") or "").strip()
            try:
                close = float(row.get("ClsPric") or "")
            except ValueError:
                continue
            if code and close > 0:
                closes[code] = close
        if closes:
            print(
                f"regenerate_india_sectors: bhavcopy {day} → {len(closes)} closes",
                file=sys.stderr,
            )
            return closes
    print("regenerate_india_sectors: no bhavcopy found in 7 days", file=sys.stderr)
    return {}


def crawl_bse_sectors(codes: list[str]) -> dict[str, dict[str, str | None]]:
    """Per-scrip ``ComHeadernew`` crawl → ``{code: {industry_raw, sector}}``.

    Throttled (jittered sleep per call); stops after
    ``_CRAWL_MAX_CONSECUTIVE_FAILURES`` consecutive failures (BSE hostile —
    keep the partial result rather than hammering the WAF)."""
    out: dict[str, dict[str, str | None]] = {}
    consecutive_failures = 0
    for idx, code in enumerate(codes):
        try:
            resp = _get(HEADER_URL.format(code=code))
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}")
            data = resp.json()
            industry_new = (data.get("IndustryNew") or "").strip()
            subgroup = (data.get("ISubGroup") or "").strip()
            legacy = (data.get("Industry") or "").strip()
            raw = " / ".join(p for p in (industry_new, subgroup) if p) or legacy or None
            sector = map_industry_to_sector(industry_new) or map_industry_to_sector(legacy)
            if raw or sector:
                out[code] = {"industry_raw": raw, "sector": sector}
            consecutive_failures = 0
        except Exception as exc:  # noqa: BLE001 - count and move on
            consecutive_failures += 1
            print(
                f"regenerate_india_sectors: header {code} failed ({exc}) "
                f"[{consecutive_failures} consecutive]",
                file=sys.stderr,
            )
            if consecutive_failures >= _CRAWL_MAX_CONSECUTIVE_FAILURES:
                print(
                    "regenerate_india_sectors: BSE hostile — aborting crawl, "
                    f"keeping {len(out)} classified",
                    file=sys.stderr,
                )
                break
        if idx and idx % 100 == 0:
            print(
                f"regenerate_india_sectors: crawled {idx}/{len(codes)} "
                f"({len(out)} classified)",
                file=sys.stderr,
            )
        time.sleep(random.uniform(*_CRAWL_SLEEP_RANGE))
    return out


def crawl_yfinance_sectors(symbols: list[str]) -> dict[str, dict[str, str | None]]:
    """Fallback: per-symbol yfinance ``.info`` → ``{base_symbol: {...}}``.

    Yahoo's sector vocabulary is the target vocabulary, so the value is used
    verbatim. Throttled like the BSE crawl."""
    import yfinance as yf

    out: dict[str, dict[str, str | None]] = {}
    consecutive_failures = 0
    for idx, sym in enumerate(symbols):
        try:
            info = yf.Ticker(f"{sym}.NS").info or {}
            sector = (info.get("sector") or "").strip() or None
            industry = (info.get("industry") or "").strip() or None
            if sector or industry:
                out[sym] = {"industry_raw": industry, "sector": sector}
            consecutive_failures = 0
        except Exception as exc:  # noqa: BLE001 - count and move on
            consecutive_failures += 1
            print(f"regenerate_india_sectors: yf {sym} failed ({exc})", file=sys.stderr)
            if consecutive_failures >= _CRAWL_MAX_CONSECUTIVE_FAILURES:
                break
        if idx and idx % 100 == 0:
            print(f"regenerate_india_sectors: yf crawled {idx}/{len(symbols)}", file=sys.stderr)
        time.sleep(random.uniform(*_CRAWL_SLEEP_RANGE))
    return out


def _mktcap_crores(record: dict) -> float:
    try:
        return float(record.get("Mktcap") or "")
    except (TypeError, ValueError):
        return -1.0


def build_map(
    records: list[dict],
    closes: dict[str, float],
    bse_sectors: dict[str, dict[str, str | None]],
    yf_sectors: dict[str, dict[str, str | None]],
) -> dict:
    """Assemble the bundled map document (header + per-record rows)."""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    sector_sources: dict[str, int] = {}
    with_sector = 0
    with_shares = 0
    for rec in sorted(records, key=_mktcap_crores, reverse=True):
        code = str(rec.get("SCRIP_CD") or "").strip()
        symbol = str(rec.get("scrip_id") or "").strip().upper()
        isin = str(rec.get("ISIN_NUMBER") or "").strip() or None
        if not code or not symbol or symbol in seen:
            continue
        seen.add(symbol)

        # Sector precedence: bulk INDUSTRY (when BSE populates it) → per-scrip
        # BSE crawl → yfinance fallback. Source is stamped per record.
        bulk_industry = (rec.get("INDUSTRY") or "").strip() or None
        industry_raw: str | None = None
        sector: str | None = None
        sector_source: str | None = None
        if bulk_industry:
            industry_raw = bulk_industry
            sector = map_industry_to_sector(bulk_industry)
            sector_source = "bse" if sector else None
        if sector is None and code in bse_sectors:
            industry_raw = bse_sectors[code]["industry_raw"] or industry_raw
            sector = bse_sectors[code]["sector"]
            sector_source = "bse" if sector else sector_source
        if sector is None and symbol in yf_sectors:
            industry_raw = yf_sectors[symbol]["industry_raw"] or industry_raw
            sector = yf_sectors[symbol]["sector"]
            sector_source = "yfinance" if sector else sector_source

        # shares_outstanding = Mktcap (crores INR → ×1e7) / close, at snapshot.
        shares: float | None = None
        mktcap = _mktcap_crores(rec)
        close = closes.get(code)
        if mktcap > 0 and close:
            shares = round(mktcap * 1e7 / close)

        if sector:
            with_sector += 1
            sector_sources[sector_source or "?"] = sector_sources.get(sector_source or "?", 0) + 1
        if shares:
            with_shares += 1
        rows.append(
            {
                "symbol": symbol,
                "isin": isin,
                "scrip_code": code,
                "industry_raw": industry_raw,
                "sector": sector,
                "sector_source": sector_source,
                "shares_outstanding": shares,
            }
        )
    return {
        "_generated": datetime.now(tz=UTC).strftime("%Y-%m-%d"),
        "_source": LIST_URL,
        "_note": (
            "India sector/shares map regenerated via regenerate_india_sectors.py. "
            "Identity+Mktcap from ListOfScripData; close from the equity bhavcopy "
            "(shares_outstanding = Mktcap*1e7/close at snapshot); sector from BSE's "
            "harmonized classification (ComHeadernew IndustryNew, hand-mapped to the "
            "Yahoo 11-sector vocabulary; unknown -> null) with a yfinance fallback. "
            "Partial sector coverage is expected — the runtime warm crawler backfills. "
            "Do not hand-edit; rerun the script to refresh."
        ),
        "coverage": {
            "records": len(rows),
            "with_sector": with_sector,
            "with_shares": with_shares,
            "sector_sources": sector_sources,
        },
        "records": rows,
    }


def dump_map(doc: dict, fp: TextIO) -> None:
    """Emit the map with one record per line (reviewable diffs)."""
    fp.write("{\n")
    for key in ("_generated", "_source", "_note"):
        fp.write(f"  {json.dumps(key)}: {json.dumps(doc[key], ensure_ascii=False)},\n")
    fp.write(f"  {json.dumps('coverage')}: {json.dumps(doc['coverage'])},\n")
    fp.write('  "records": [\n')
    lines = [json.dumps(row, ensure_ascii=False) for row in doc["records"]]
    fp.write(",\n".join(f"    {line}" for line in lines))
    fp.write("\n  ]\n}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--crawl",
        type=int,
        default=800,
        help="per-scrip BSE classification crawl depth (top-N by Mktcap; 0 disables)",
    )
    parser.add_argument(
        "--fallback-yfinance",
        type=int,
        default=0,
        help="when the BSE crawl yields nothing, crawl yfinance .info for the top N",
    )
    args = parser.parse_args()

    records = fetch_bulk_records()
    print(f"regenerate_india_sectors: {len(records)} bulk records", file=sys.stderr)
    closes = fetch_closes()

    bulk_has_industry = any((rec.get("INDUSTRY") or "").strip() for rec in records)
    bse_sectors: dict[str, dict[str, str | None]] = {}
    if not bulk_has_industry and args.crawl > 0:
        ordered = sorted(records, key=_mktcap_crores, reverse=True)
        codes = [str(r.get("SCRIP_CD") or "").strip() for r in ordered[: args.crawl]]
        codes = [c for c in codes if c]
        print(
            f"regenerate_india_sectors: bulk INDUSTRY empty — crawling top {len(codes)} "
            "via ComHeadernew",
            file=sys.stderr,
        )
        bse_sectors = crawl_bse_sectors(codes)

    yf_sectors: dict[str, dict[str, str | None]] = {}
    if not bulk_has_industry and not bse_sectors and args.fallback_yfinance > 0:
        ordered = sorted(records, key=_mktcap_crores, reverse=True)
        symbols = [str(r.get("scrip_id") or "").strip().upper() for r in ordered]
        symbols = [s for s in symbols if s][: args.fallback_yfinance]
        print(
            f"regenerate_india_sectors: BSE crawl empty — yfinance fallback for "
            f"{len(symbols)}",
            file=sys.stderr,
        )
        yf_sectors = crawl_yfinance_sectors(symbols)

    doc = build_map(records, closes, bse_sectors, yf_sectors)
    dump_map(doc, sys.stdout)
    print(
        f"regenerate_india_sectors: wrote {doc['coverage']['records']} records; "
        f"coverage {doc['coverage']}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
