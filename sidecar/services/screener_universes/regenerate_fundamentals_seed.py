"""Regenerate the bundled India fundamentals seed pack (R11, D52).

Offline, hand-run maintenance script — NOT imported at runtime. Exports a
warm ``fundamentals_cache.db`` (a store the app's own crawler filled) into
``india_fundamentals_seed.json.gz``, the snapshot a fresh install seeds its
store from so the full-universe screener works instantly on an honest,
labeled basis.

Usage::

    .venv/bin/python -m services.screener_universes.regenerate_fundamentals_seed \
        --db "~/Library/Application Support/com.vysted.terminal/fundamentals_cache.db"

Selection: every ``.NS``/``.BO`` row carrying at least one data tier
(``v7_updated_at`` or ``info_updated_at``). Exported fields: the full numeric
vocabulary + name/currency/sector/industry/sector_source. Per-row
``seed_as_of`` = the OLDEST exported tier stamp (conservative honesty — a row
mixing a June-13 info tier with a June-16 v7 tier is dated June 13).
Quote-tier prices are deliberately NOT exported — same-day prices are the
bhavcopy lane's job (D54); the pack is fundamentals.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

_NUMERIC_FIELDS = (
    "market_cap",
    "pe_ratio",
    "forward_pe",
    "peg_ratio",
    "price_to_book",
    "price_to_sales",
    "ev_to_ebitda",
    "book_value",
    "dividend_yield",
    "eps",
    "beta",
    "roe",
    "roa",
    "gross_margin",
    "operating_margin",
    "profit_margin",
    "debt_to_equity",
    "current_ratio",
    "quick_ratio",
    "revenue_growth",
    "earnings_growth",
    "fifty_two_week_high",
    "fifty_two_week_low",
    "fifty_two_week_change",
    "held_percent_insiders",
    "held_percent_institutions",
    "shares_outstanding",
)
_IDENTITY_FIELDS = ("name", "currency", "sector", "industry", "sector_source")


def build_pack(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = []
    for row in conn.execute(
        "SELECT * FROM fundamentals WHERE (symbol LIKE '%.NS' OR symbol LIKE '%.BO') "
        "AND (v7_updated_at IS NOT NULL OR info_updated_at IS NOT NULL)"
    ):
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
    parser.add_argument(
        "--out",
        default=str(Path(__file__).parent / "india_fundamentals_seed.json.gz"),
        help="output pack path",
    )
    args = parser.parse_args()
    db_path = str(Path(args.db).expanduser())
    pack = build_pack(db_path)
    if pack["_rows"] < 1000:
        # Sanity floor (regenerate_bse_master precedent): never overwrite a
        # good committed pack with a near-empty export.
        print(f"REFUSING to write: only {pack['_rows']} rows exported (<1000)", file=sys.stderr)
        return 1
    payload = gzip.compress(json.dumps(pack, separators=(",", ":")).encode("utf-8"), mtime=0)
    Path(args.out).write_bytes(payload)
    print(
        f"wrote {args.out}: {pack['_rows']} rows, {len(payload):,} bytes gz, "
        f"as-of {pack['_oldest_as_of']} … {pack['_newest_as_of']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
