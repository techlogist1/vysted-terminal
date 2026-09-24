"""Regenerate ``nse_instruments.json`` — the bundled NSE master (R15-DATA-017).

Built from NSE's three public listing files:

  * ``EQUITY_L.csv`` — the main board (series EQ/BE/BZ) → type ``EQ``;
  * ``SME_EQUITY_L.csv`` — NSE Emerge (series SM/ST/SZ) → type ``SM``, which Yahoo
    serves as ``<SYMBOL>-SM.NS`` (SUMAX-SM.NS, VINOD-SM.NS);
  * ``eq_etfseclist.csv`` — the ETF list → type ``ETF``.

Each list's face-value column lands in a ``face_values`` map (``{SYMBOL: face
value}``) beside the rows. Rights-entitlement lines (``-RE`` tickers, ISIN
security type ``20``) are dropped.
Rows are ``[SYMBOL, NAME, TYPE]``, ordered by the BSE master's market-cap rank of
the row's ISIN (prominence, so fuzzy ties break toward the well-known listing),
with unranked rows after in file order.

The same builder runs at runtime: :func:`services.symbol_resolver.refresh_masters`
fetches the lists daily into the data dir and unions them with the bundled file.

Usage::

    python -m services.resolver_masters.regenerate_nse_master > nse_instruments.json
"""

from __future__ import annotations

import csv
import io
import json
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from importlib import resources
from typing import TextIO

from services.resolver_masters.regenerate_bse_master import face_value, is_rights_entitlement

EQUITY_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
SME_URL = "https://nsearchives.nseindia.com/emerge/corporates/content/SME_EQUITY_L.csv"
ETF_URL = "https://nsearchives.nseindia.com/content/equities/eq_etfseclist.csv"
_REFERER = "https://www.nseindia.com/"
_TIMEOUT = 30.0
_ATTEMPTS = 3
# The main board alone lists ~2.5k names; far fewer rows is a block page, not the list.
_MIN_ROWS = 1000


def _get_once(url: str) -> str:
    """One impersonated GET (curl_cffi; httpx when it is not installed)."""
    try:
        from curl_cffi import requests as creq

        resp = creq.get(url, impersonate="chrome", timeout=_TIMEOUT, headers={"Referer": _REFERER})
    except ImportError:
        import httpx

        resp = httpx.get(url, timeout=_TIMEOUT, headers={"Referer": _REFERER})
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} from {url}")
    return resp.text


def _get(url: str) -> str:
    """:func:`_get_once` with retries: NSE's archive host resets connections."""
    for attempt in range(1, _ATTEMPTS):
        try:
            return _get_once(url)
        except Exception:  # noqa: BLE001 - every transport failure retries the same way
            time.sleep(2.0 * attempt)
    return _get_once(url)


def _rows(text: str) -> list[dict[str, str]]:
    """CSV records keyed by upper-cased, space-free header names."""
    reader = csv.reader(io.StringIO(text))
    header = [h.strip().upper().replace(" ", "_") for h in next(reader, [])]
    return [dict(zip(header, (c.strip() for c in row), strict=False)) for row in reader if row]


def _bse_isin_rank() -> dict[str, int]:
    """ISIN → market-cap rank from the bundled BSE master (prominence order)."""
    raw = json.loads(
        resources.files("services.resolver_masters")
        .joinpath("bse_instruments.json")
        .read_text("utf-8")
    )
    rank: dict[str, int] = {}
    for i, row in enumerate(raw.get("instruments", [])):
        if len(row) > 4 and row[4]:
            rank.setdefault(str(row[4]).strip().upper(), i)
    return rank


def build_master(
    equity_csv: str,
    sme_csv: str,
    etf_csv: str,
    *,
    isin_rank: dict[str, int] | None = None,
    min_rows: int = _MIN_ROWS,
) -> dict:
    """Normalise the three listing files into the bundled-master document."""
    rank = isin_rank if isin_rank is not None else _bse_isin_rank()
    found: list[tuple[str, str, str, str, float | None]] = []
    for text, typ, name_key in (
        (equity_csv, "EQ", "NAME_OF_COMPANY"),
        (sme_csv, "SM", "NAME_OF_COMPANY"),
        (etf_csv, "ETF", "SECURITYNAME"),
    ):
        for rec in _rows(text):
            symbol = rec.get("SYMBOL", "").upper()
            isin = (rec.get("ISIN_NUMBER") or rec.get("ISINNUMBER") or "").upper()
            par = face_value(rec.get("FACE_VALUE") or rec.get("FACEVALUE"))
            if symbol and not is_rights_entitlement(symbol, "", isin):
                found.append((symbol, rec.get(name_key, "") or symbol, typ, isin, par))
    ordered = sorted(enumerate(found), key=lambda item: (rank.get(item[1][3], len(rank)), item[0]))
    rows: list[list[str]] = []
    face_values: dict[str, float] = {}
    seen: set[str] = set()
    for _i, (symbol, name, typ, _isin, par) in ordered:
        if symbol not in seen:
            seen.add(symbol)
            rows.append([symbol, name, typ])
            if par is not None:
                face_values[symbol] = par
    if len(rows) < min_rows:
        raise ValueError(
            f"regenerate_nse_master: only {len(rows)} rows parsed "
            f"(floor {min_rows}) — refusing to emit a stub master"
        )
    return {
        "exchange": "NSE",
        "_generated": datetime.now(tz=UTC).strftime("%Y-%m-%d"),
        "_source": [EQUITY_URL, SME_URL, ETF_URL],
        "_note": (
            "NSE master regenerated via regenerate_nse_master.py from the main-board, "
            "Emerge (type SM, Yahoo -SM.NS) and ETF lists. Rows are [SYMBOL, NAME, TYPE], "
            "BSE market-cap ordered; face_values maps SYMBOL to the listed face value "
            "(INR). Do not hand-edit; rerun the script to refresh."
        ),
        "_types": dict(Counter(row[2] for row in rows).most_common()),
        "face_values": face_values,
        "instruments": rows,
    }


def fetch_master() -> dict:
    """Fetch the three live lists and build the master (raises on any failure)."""
    return build_master(_get(EQUITY_URL), _get(SME_URL), _get(ETF_URL))


def dump_master(master: dict, fp: TextIO) -> None:
    """Emit the master with one instrument row per line (reviewable diffs)."""
    fp.write("{\n")
    for key in ("exchange", "_generated", "_source", "_note", "_types", "face_values"):
        fp.write(f"  {json.dumps(key)}: {json.dumps(master[key], ensure_ascii=False)},\n")
    fp.write('  "instruments": [\n')
    lines = [json.dumps(row, ensure_ascii=False) for row in master["instruments"]]
    fp.write(",\n".join(f"    {line}" for line in lines))
    fp.write("\n  ]\n}\n")


def main() -> None:
    master = fetch_master()
    dump_master(master, sys.stdout)
    print(
        f"regenerate_nse_master: wrote {len(master['instruments'])} rows; types {master['_types']}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
