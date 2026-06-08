"""Regenerate ``bse_instruments.json`` — the bundled BSE scrip master.

NOT run at build/CI time (the bundled JSON is committed and read offline, exactly
like ``nse_instruments.json``). Run this by hand to refresh the snapshot from the
live BSE scrip list, mirroring how the NSE ``EQUITY_L`` master is produced.

Source of truth (idea-level; no GPL import — this only documents the URL shape):

  * BSE publishes the full active scrip list at the ``ListOfScrips`` endpoint:
    ``https://api.bseindia.com/BseIndiaAPI/api/ListOfScripData/w?Group=&Scripcode=&industry=&segment=Equity&status=Active``
    (the same host the quote header endpoint uses; needs the desktop UA +
    ``Referer: https://www.bseindia.com/`` headers the provider already sends).
  * Each row carries ``SCRIP_CD`` (numeric scrip code), ``Scrip_Name`` /
    ``scrip_id`` (the ticker), ``SCRIP_NAME`` (long name), ``GROUP`` (the A/B/T/Z/
    X/XT liquidity tier — the micro-cap tail lives in B/X/XT/T/Z), and ``ISIN_NUMBER``.

Output row shape (matches what ``symbol_resolver._bse_master`` parses):

    [SCRIP_CODE, SYMBOL, NAME, GROUP, ISIN]

The committed file is a small *representative seed* (large-caps + a sampling of
the micro-cap groups) sufficient for ``is_bse_symbol`` / ``region_hint`` and the
tests. Running this against the live endpoint produces the full ~5–6k-row master.

Usage::

    python -m services.resolver_masters.regenerate_bse_master > bse_instruments.json

(Kept dependency-light: ``httpx`` is already shipped; nothing here is imported at
runtime — the resolver only reads the committed JSON.)
"""

from __future__ import annotations

import json
import sys

_LIST_URL = (
    "https://api.bseindia.com/BseIndiaAPI/api/ListOfScripData/w"
    "?Group=&Scripcode=&industry=&segment=Equity&status=Active"
)
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bseindia.com/",
    "Accept": "application/json",
}


def _fetch_rows() -> list[list[str]]:
    import httpx  # local import — never loaded by the runtime resolver path

    resp = httpx.get(_LIST_URL, headers=_HEADERS, timeout=30.0, follow_redirects=True)
    resp.raise_for_status()
    payload = resp.json()
    records = payload if isinstance(payload, list) else payload.get("Table", [])
    rows: list[list[str]] = []
    for rec in records:
        code = str(rec.get("SCRIP_CD") or rec.get("Scripcode") or "").strip()
        symbol = str(rec.get("scrip_id") or rec.get("Scrip_Name") or "").strip().upper()
        name = str(rec.get("SCRIP_NAME") or rec.get("Scrip_Name") or "").strip()
        group = str(rec.get("GROUP") or rec.get("Group") or "").strip().upper()
        isin = str(rec.get("ISIN_NUMBER") or rec.get("ISIN") or "").strip()
        if code and symbol:
            rows.append([code, symbol, name, group, isin])
    return rows


def main() -> None:
    rows = _fetch_rows()
    out = {
        "exchange": "BSE",
        "_note": (
            "Regenerated via regenerate_bse_master.py from the BSE ListOfScripData "
            "endpoint. Rows are [SCRIP_CODE, SYMBOL, NAME, GROUP, ISIN]."
        ),
        "instruments": rows,
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
