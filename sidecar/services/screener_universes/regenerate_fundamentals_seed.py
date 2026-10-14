"""Regenerate a bundled fundamentals seed pack (R11 D52; US pack R15-DATA-110).

Offline, hand-run maintenance script — NOT imported at runtime. Exports a
warm ``fundamentals_cache.db`` (a store the app's own crawler filled) into
``india_fundamentals_seed.json.gz`` (``--market india``) or
``us_fundamentals_seed.json.gz`` (``--market us``), the snapshot a fresh
install seeds its store from so the screener works instantly on an honest,
labeled basis.

Usage::

    .venv/bin/python -m services.screener_universes.regenerate_fundamentals_seed \
        --market us --db "~/Library/Application Support/com.vysted.terminal/fundamentals_cache.db"

Selection: every row of the market (``.NS``/``.BO`` for india; the bundled
``sp500.json`` symbols for us) carrying at least one data tier
(``v7_updated_at`` or ``info_updated_at``). A US pack is written only WHOLE —
covering at least 95% of sp500 (SC-034's <5% skip bar) — never a partial one.
Exported fields: the full numeric vocabulary +
name/currency/sector/industry/sector_source. Per-row
``seed_as_of`` = the OLDEST exported tier stamp (conservative honesty — a row
mixing a June-13 info tier with a June-16 v7 tier is dated June 13).
Quote-tier prices are deliberately NOT exported — same-day prices are the
bhavcopy lane's job (D54); the pack is fundamentals.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

# R15-DATA-095: was a hand-duplicated copy of fundamentals_store._NUMERIC_FIELDS
# that had already drifted from it once. The store derives that tuple from
# ScreenerNumericField (models/screener.py) — the one declaration of the
# vocabulary — so this now reads the store's own tuple instead of re-declaring
# it a third time.
from services.fundamentals_store import _NUMERIC_FIELDS

_IDENTITY_FIELDS = ("name", "currency", "sector", "industry", "sector_source")


def _sp500_symbols() -> set[str]:
    return set(json.loads((Path(__file__).parent / "sp500.json").read_text())["symbols"])


def build_pack(db_path: str, market: str = "india") -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    sp500 = _sp500_symbols() if market == "us" else set()
    rows = []
    for row in conn.execute(
        "SELECT * FROM fundamentals WHERE v7_updated_at IS NOT NULL OR info_updated_at IS NOT NULL"
    ):
        symbol = row["symbol"]
        if not (symbol in sp500 if market == "us" else symbol.endswith((".NS", ".BO"))):
            continue
        stamps = [s for s in (row["v7_updated_at"], row["info_updated_at"]) if s is not None]
        record: dict = {"symbol": row["symbol"], "seed_as_of": min(stamps)}
        for field in _IDENTITY_FIELDS:
            if row[field] is not None:
                record[field] = row[field]
        exported = 0
        for field in _NUMERIC_FIELDS:
            if row[field] is not None:
                record[field] = row[field]
                exported += 1
        if exported:
            rows.append(record)
    conn.close()
    rows.sort(key=lambda r: r["symbol"])
    stamps = [r["seed_as_of"] for r in rows]
    return {
        "_generated": datetime.now(tz=UTC).date().isoformat(),
        "_source": f"warm fundamentals_cache.db export ({Path(db_path).name})",
        "_rows": len(rows),
        "_oldest_as_of": datetime.fromtimestamp(min(stamps), tz=UTC).isoformat()
        if stamps
        else None,
        "_newest_as_of": datetime.fromtimestamp(max(stamps), tz=UTC).isoformat()
        if stamps
        else None,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="path to a warm fundamentals_cache.db")
    parser.add_argument("--market", choices=("india", "us"), default="india")
    parser.add_argument("--out", help="output pack path (default: the market's bundled pack)")
    args = parser.parse_args()
    db_path = str(Path(args.db).expanduser())
    out = args.out or str(Path(__file__).parent / f"{args.market}_fundamentals_seed.json.gz")
    pack = build_pack(db_path, args.market)
    # Sanity floor (regenerate_bse_master precedent): never overwrite a good
    # committed pack with a near-empty export — and never ship a partial US one.
    floor = 1000 if args.market == "india" else math.ceil(0.95 * len(_sp500_symbols()))
    if pack["_rows"] < floor:
        print(f"REFUSING to write: only {pack['_rows']} rows exported (<{floor})", file=sys.stderr)
        return 1
    payload = gzip.compress(json.dumps(pack, separators=(",", ":")).encode("utf-8"), mtime=0)
    Path(out).write_bytes(payload)
    print(
        f"wrote {out}: {pack['_rows']} rows, {len(payload):,} bytes gz, "
        f"as-of {pack['_oldest_as_of']} … {pack['_newest_as_of']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
