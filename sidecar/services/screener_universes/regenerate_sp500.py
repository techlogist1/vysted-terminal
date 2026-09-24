"""Regenerate the bundled S&P 500 universe pack (R15-LEAD-013).

Offline, hand-run maintenance script — NOT imported at runtime. ``sp500.json``
is a point-in-time membership snapshot (not a live feed); index membership
drifts ~20-25 names/year via M&A and rebalances, so the pack goes stale
silently until re-run. Fetches the current constituent table from Wikipedia's
"List of S&P 500 companies" (the public source already named in the pack's
own ``source`` field) and rewrites ``sp500.json`` in its existing shape
(``id``, ``label``, ``asset_class``, ``snapshot_date``, ``source``,
``symbols``) with a fresh ``snapshot_date``. The shape is unchanged, so
``services/screener.py`` needs no edit.

Usage::

    .venv/bin/python -m services.screener_universes.regenerate_sp500
"""

from __future__ import annotations

import io
import json
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
_OUT_PATH = Path(__file__).parent / "sp500.json"
# Wikipedia 403s the default urllib/pandas User-Agent (no UA at all) — send a
# real one, per Wikimedia's own user-agent policy.
_USER_AGENT = "vysted-terminal-sp500-regen/1.0 (https://github.com/techlogist1/vysted-terminal)"


def _to_yahoo_symbol(wikipedia_symbol: str) -> str:
    """Wikipedia's table dots class shares (``BRK.B``); Yahoo dashes them
    (``BRK-B``) — the format the rest of the pack (and the screener's quote
    lookups) already assumes."""
    return wikipedia_symbol.strip().replace(".", "-")


def fetch_symbols() -> list[str]:
    import pandas as pd

    request = urllib.request.Request(WIKIPEDIA_URL, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as resp:  # noqa: S310 (fixed https URL)
        html = resp.read().decode("utf-8")

    tables = pd.read_html(io.StringIO(html))
    constituents = tables[0]
    symbol_col = next(c for c in constituents.columns if str(c).strip().lower() == "symbol")
    symbols = sorted({_to_yahoo_symbol(s) for s in constituents[symbol_col].astype(str)})
    return symbols


def main() -> int:
    symbols = fetch_symbols()
    if len(symbols) < 490:
        # Sanity floor — a parse failure (wrong table, renamed column) would
        # silently produce a tiny or empty list; refuse to overwrite the pack.
        print(f"error: only found {len(symbols)} symbols, expected ~500-503", file=sys.stderr)
        return 1

    pack = json.loads(_OUT_PATH.read_text(encoding="utf-8"))
    pack["snapshot_date"] = datetime.now(UTC).date().isoformat()
    pack["symbols"] = symbols
    _OUT_PATH.write_text(json.dumps(pack, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(symbols)} symbols, snapshot_date={pack['snapshot_date']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
