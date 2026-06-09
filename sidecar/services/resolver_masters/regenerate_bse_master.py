"""Regenerate ``bse_instruments.json`` — the bundled BSE scrip master.

NOT run at build/CI time (the bundled JSON is committed and read offline, exactly
like ``nse_instruments.json``). Run this by hand to refresh the snapshot from the
live BSE scrip list, mirroring how the NSE ``EQUITY_L`` master is produced.

Source of truth (idea-level; no GPL import — this only documents the URL shape):

  * BSE publishes the full active scrip list at the ``ListOfScripData`` endpoint:
    ``https://api.bseindia.com/BseIndiaAPI/api/ListOfScripData/w?Group=&Scripcode=&industry=&segment=Equity&status=Active``
    With ``Group=`` left empty the single call returns EVERY equity group —
    A/B/T/X/XT/Z **and the SME tiers M/MT** (observed live 2026-06-10: a JSON
    *list* of ~4.9k records; groups B 1621, X 1296, A 724, XT 399, M 327, T 205,
    MT 155, Z 67 + small P/MS/ZP/TS/IP/Y/R tails).
  * Each record carries ``SCRIP_CD`` (numeric scrip code), ``scrip_id`` (the
    ticker), ``Scrip_Name`` (display name), ``GROUP`` (liquidity tier),
    ``ISIN_NUMBER``, ``Status`` and ``Mktcap`` (crores; used only for the
    prominence ordering below).

Hardening: the fetch goes through ``curl_cffi`` with Chrome TLS impersonation
(BSE's WAF blocks plain-httpx clients intermittently) and retries with
exponential backoff + jitter; ``httpx`` with a desktop UA is the fallback when
``curl_cffi`` is unavailable. A sanity floor (:data:`_MIN_ROWS`) refuses to emit
a master from a tiny/blocked payload so a WAF refusal page can never overwrite
the good committed file.

Output row shape (matches what ``symbol_resolver._bse_master`` parses):

    [SCRIP_CODE, SYMBOL, NAME, GROUP, ISIN, STATUS]

Rows are ordered by market cap (descending, unknown-cap tail last) so the
prominence-ordered master breaks fuzzy-match ties toward the well-known
instrument, mirroring the SEC market-cap ordering of ``us_instruments.json``.
The emitted JSON carries a ``_generated`` (UTC date) + ``_source`` header and a
``_groups`` census so the snapshot's age and coverage are auditable in-repo.

Usage::

    python -m services.resolver_masters.regenerate_bse_master > bse_instruments.json

(Nothing here is imported at runtime — the resolver only reads the committed JSON.)
"""

from __future__ import annotations

import json
import random
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from typing import TextIO

LIST_URL = (
    "https://api.bseindia.com/BseIndiaAPI/api/ListOfScripData/w"
    "?Group=&Scripcode=&industry=&segment=Equity&status=Active"
)
_REFERER = "https://www.bseindia.com/"
_FALLBACK_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_TIMEOUT = 40.0
_ATTEMPTS = 4
_BACKOFF_BASE = 1.5  # seconds; grows ~1.5x per attempt, plus jitter
# Sanity floor: the live list is ~4.9k records. A payload far below this is a
# WAF block / error page, not the master — refuse rather than emit a stub.
_MIN_ROWS = 1000


def _fetch_once() -> list[dict]:
    """One impersonated GET of the scrip list → the decoded record list.

    ``curl_cffi`` (Chrome TLS impersonation) is the primary client; ``httpx``
    with a desktop UA is the fallback when curl_cffi is not installed. Raises on
    any transport / HTTP / decode failure (the caller retries).
    """
    try:
        from curl_cffi import requests as creq

        resp = creq.get(
            LIST_URL,
            impersonate="chrome",
            timeout=_TIMEOUT,
            headers={"Referer": _REFERER, "Accept": "application/json"},
        )
    except ImportError:
        import httpx

        resp = httpx.get(
            LIST_URL,
            timeout=_TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": _FALLBACK_UA,
                "Referer": _REFERER,
                "Accept": "application/json",
            },
        )
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} from ListOfScripData")
    payload = resp.json()
    # Observed live (2026-06-10): a bare JSON list. Older captures wrapped the
    # records in {"Table": [...]} — accept both.
    records = payload if isinstance(payload, list) else payload.get("Table", [])
    if not isinstance(records, list):
        raise RuntimeError(f"unexpected payload shape: {type(payload).__name__}")
    return records


def fetch_records() -> list[dict]:
    """Fetch the live scrip list with retries (backoff + jitter between attempts)."""
    last_exc: Exception | None = None
    for attempt in range(1, _ATTEMPTS + 1):
        try:
            return _fetch_once()
        except Exception as exc:  # noqa: BLE001 - every failure mode retries the same way
            last_exc = exc
            if attempt < _ATTEMPTS:
                wait = _BACKOFF_BASE * (2 ** (attempt - 1)) + random.uniform(0.0, 0.5)
                print(
                    f"regenerate_bse_master: attempt {attempt}/{_ATTEMPTS} failed "
                    f"({exc}); retrying in {wait:.1f}s",
                    file=sys.stderr,
                )
                time.sleep(wait)
    raise SystemExit(f"regenerate_bse_master: all {_ATTEMPTS} attempts failed: {last_exc}")


def _mktcap(record: dict) -> float:
    """Market cap for the prominence sort; unknown caps sort to the tail."""
    try:
        return float(record.get("Mktcap") or "")
    except (TypeError, ValueError):
        return -1.0


def build_master(records: list[dict], *, min_rows: int = _MIN_ROWS) -> dict:
    """Normalise the live records into the bundled-master document.

    Rows are ``[SCRIP_CODE, SYMBOL, NAME, GROUP, ISIN, STATUS]``, market-cap
    ordered (prominence), one canonical row per ticker (the highest-cap record
    wins a duplicate). Raises :class:`ValueError` below ``min_rows`` so a
    blocked/truncated payload can never replace the good committed master.
    """
    rows: list[list[str]] = []
    seen: set[str] = set()
    for rec in sorted(records, key=_mktcap, reverse=True):
        code = str(rec.get("SCRIP_CD") or rec.get("Scripcode") or "").strip()
        symbol = str(rec.get("scrip_id") or "").strip().upper()
        name = str(rec.get("Scrip_Name") or rec.get("Issuer_Name") or "").strip()
        group = str(rec.get("GROUP") or rec.get("Group") or "").strip().upper()
        isin = str(rec.get("ISIN_NUMBER") or rec.get("ISIN") or "").strip()
        status = str(rec.get("Status") or "").strip()
        if not code or not symbol or symbol in seen:
            continue
        seen.add(symbol)
        rows.append([code, symbol, name, group, isin, status])
    if len(rows) < min_rows:
        raise ValueError(
            f"regenerate_bse_master: only {len(rows)} rows parsed "
            f"(floor {min_rows}) — refusing to emit a stub master"
        )
    groups = Counter(row[3] for row in rows)
    return {
        "exchange": "BSE",
        "_generated": datetime.now(tz=UTC).strftime("%Y-%m-%d"),
        "_source": LIST_URL,
        "_note": (
            "Full BSE scrip master regenerated via regenerate_bse_master.py from the "
            "ListOfScripData endpoint (all equity groups incl. the SME M/MT tiers). "
            "Rows are [SCRIP_CODE, SYMBOL, NAME, GROUP, ISIN, STATUS], market-cap "
            "ordered. Do not hand-edit; rerun the script to refresh."
        ),
        "_groups": dict(groups.most_common()),
        "instruments": rows,
    }


def dump_master(master: dict, fp: TextIO) -> None:
    """Emit the master with one instrument row per line (reviewable diffs)."""
    fp.write("{\n")
    for key in ("exchange", "_generated", "_source", "_note"):
        fp.write(f"  {json.dumps(key)}: {json.dumps(master[key], ensure_ascii=False)},\n")
    fp.write(f"  {json.dumps('_groups')}: {json.dumps(master['_groups'])},\n")
    fp.write('  "instruments": [\n')
    lines = [json.dumps(row, ensure_ascii=False) for row in master["instruments"]]
    fp.write(",\n".join(f"    {line}" for line in lines))
    fp.write("\n  ]\n}\n")


def main() -> None:
    records = fetch_records()
    try:
        master = build_master(records)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    dump_master(master, sys.stdout)
    print(
        f"regenerate_bse_master: wrote {len(master['instruments'])} rows; "
        f"groups {master['_groups']}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
