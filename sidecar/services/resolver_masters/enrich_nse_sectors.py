"""One-time gap-filler: complete the NSE universe's sector coverage in
``india_sector_map.json`` via yfinance ``.info`` (R10 gate-4 data fix).

The bundled map was built from BSE ``ListOfScripData`` whose ``INDUSTRY`` field
went null live (2026-06), so only ~793/4,875 records carry a sector and the
small-cap NSE IT names the operator's screen needs (SAKSOFT, DATAMATICS, …) had
``sector=None`` — the ``sector eq Technology`` prefilter excluded them. This
fills every NSE-master symbol that lacks a sector with yfinance's Yahoo-vocab
sector, so the prefilter narrows the universe instantly and the screen returns
correct rows fast. Throttle-tolerant + resumable (writes progress in place).

Run:  PATH=.venv/bin python -m services.resolver_masters.enrich_nse_sectors
"""

from __future__ import annotations

import json
import sys
import time
from importlib import resources
from pathlib import Path


def _map_path() -> Path:
    return Path(str(resources.files("services.resolver_masters") / "india_sector_map.json"))


def _nse_symbols() -> list[str]:
    raw = json.loads(
        (resources.files("services.resolver_masters") / "nse_instruments.json").read_text()
    )
    return [str(row[0]).strip().upper() for row in raw if row and row[0]]


def main() -> int:
    import yfinance as yf

    path = _map_path()
    doc = json.loads(path.read_text())
    records = doc["records"] if isinstance(doc, dict) and "records" in doc else doc
    by_symbol = {str(r.get("symbol", "")).upper(): r for r in records}

    nse = _nse_symbols()
    todo = [s for s in nse if not (by_symbol.get(s) or {}).get("sector")]
    print(
        f"NSE symbols={len(nse)} | already sectored={len(nse) - len(todo)} | to fetch={len(todo)}"
    )

    filled = 0
    for i, sym in enumerate(todo):
        try:
            info = yf.Ticker(f"{sym}.NS").info
            sector = (info.get("sector") or "").strip()
            industry = (info.get("industry") or "").strip()
        except Exception:  # noqa: BLE001 — one bad symbol never stops the crawl
            sector, industry = "", ""
        if sector:
            rec = by_symbol.get(sym)
            if rec is None:
                rec = {"symbol": sym}
                records.append(rec)
                by_symbol[sym] = rec
            rec["sector"] = sector
            rec["industry"] = industry or rec.get("industry")
            rec["sector_source"] = "yfinance"
            filled += 1
        # Persist every 50 so a throttle-kill keeps progress (resumable).
        if (i + 1) % 50 == 0:
            path.write_text(json.dumps(doc, indent=1, ensure_ascii=False))
            print(f"  {i + 1}/{len(todo)} processed, {filled} filled", flush=True)
        time.sleep(0.4)  # gentle pacing for yfinance

    # Refresh the coverage header if present.
    if isinstance(doc, dict) and "coverage" in doc:
        with_sector = sum(1 for r in records if r.get("sector"))
        doc["coverage"]["with_sector"] = with_sector
        doc["coverage"].setdefault("sector_sources", {})["yfinance"] = filled
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    print(
        f"DONE — filled {filled} sectors; total with_sector now "
        f"{sum(1 for r in records if r.get('sector'))}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
