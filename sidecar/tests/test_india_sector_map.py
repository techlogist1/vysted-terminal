"""The SHIPPED india_sector_map.json — integrity of the committed data file.

Pattern: the shipped-master checks in ``test_regenerate_bse_master.py``, applied
to the sector/shares seed. R11 (D59) fixed three defects the census caught in
the committed map — these tests pin the file so they can never silently return:

  - the coverage header said ``records: 4875`` while the file held 5,010
    records (never updated when enrich_nse_sectors.py appended 135 NSE-only
    rows) — the header IS the product's honesty surface
    (``sector_map_coverage()`` serves it verbatim);
  - 1,340 records carried a Yahoo industry string under an orphaned
    ``industry`` key while every reader consumes ``industry_raw`` only —
    silently unread enrichment data;
  - the 135 NSE-only rows had no ``shares_outstanding`` at all, so market-cap
    screens nulled out on exactly those symbols with no coverage caveat.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from types import SimpleNamespace

import pytest

from services import symbol_resolver

#: The ONE record shape every row carries after the D59 hygiene pass.
_CANONICAL_KEYS = {
    "symbol",
    "isin",
    "scrip_code",
    "industry_raw",
    "sector",
    "sector_source",
    "shares_outstanding",
}


def _shipped_map() -> dict:
    return symbol_resolver._load_master("india_sector_map.json")


def test_shipped_map_coverage_header_matches_the_actual_records() -> None:
    """The honest-coverage contract: every count in the header must equal a
    census computed over the records themselves — a stale header misreports
    the screener's own coverage surface."""
    doc = _shipped_map()
    records = doc["records"]
    coverage = doc["coverage"]
    assert coverage["records"] == len(records), (
        f"coverage.records says {coverage['records']} but the file holds {len(records)}"
    )
    assert coverage["with_sector"] == sum(1 for r in records if r.get("sector"))
    assert coverage["with_shares"] == sum(1 for r in records if r.get("shares_outstanding"))
    actual_sources = Counter(r["sector_source"] for r in records if r.get("sector"))
    assert coverage["sector_sources"] == dict(actual_sources)


def test_shipped_map_no_record_carries_industry_without_industry_raw() -> None:
    """The D59 defect class: enrichment data written under a key nothing reads.
    After the hygiene pass the orphan ``industry`` key must not exist at all —
    every industry string lives in ``industry_raw`` (the one key readers
    consume)."""
    for rec in _shipped_map()["records"]:
        assert "industry" not in rec, (
            f"{rec['symbol']}: orphaned 'industry' key — readers only consume industry_raw"
        )
        assert "industry_raw" in rec, f"{rec['symbol']}: missing the industry_raw key"


def test_shipped_map_records_have_one_canonical_shape() -> None:
    """Every record carries the same 7-key shape with sane value types — no
    partial-shape rows (the pre-D59 file had three coexisting shapes)."""
    records = _shipped_map()["records"]
    assert len(records) > 4000  # a full regeneration, not a seed
    seen: set[str] = set()
    for rec in records:
        assert set(rec) == _CANONICAL_KEYS, (rec.get("symbol"), sorted(rec))
        sym = rec["symbol"]
        assert isinstance(sym, str) and sym and sym == sym.upper(), sym
        assert sym not in seen, f"duplicate record for {sym}"
        seen.add(sym)
        for key in ("isin", "scrip_code", "industry_raw", "sector", "sector_source"):
            assert rec[key] is None or isinstance(rec[key], str), (sym, key, rec[key])
        shares = rec["shares_outstanding"]
        assert shares is None or (isinstance(shares, int) and shares > 0), (sym, shares)
        # A record claiming a sector must say where it came from, and vice
        # versa — sector/sector_source travel together or not at all.
        assert bool(rec["sector"]) == bool(rec["sector_source"]), (sym, rec)


def test_shipped_map_nse_only_rows_carry_shares_outstanding() -> None:
    """The 135 enrichment-added NSE-only rows (recognizable by their null BSE
    identity) must carry shares_outstanding — pre-D59 they had none, so
    market-cap-gated screens silently excluded exactly those symbols."""
    records = _shipped_map()["records"]
    nse_only = [r for r in records if r["isin"] is None and r["scrip_code"] is None]
    assert nse_only, "the NSE-only enrichment rows must exist"
    unshared = [r["symbol"] for r in nse_only if not r["shares_outstanding"]]
    assert unshared == [], f"NSE-only rows still lack shares_outstanding: {unshared}"


def test_enrichment_writes_canonical_seven_keys(
    tmp_path: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R15-DATA-106: the producer must not resurrect the orphaned 'industry'
    key or append partial records — a re-run would red the shipped-map tests
    above. Runs the real enrichment loop against a stubbed yf.Ticker and a
    2-record fixture doc (one sectorless existing row to update, one new
    NSE-only symbol to append)."""
    from services.resolver_masters import enrich_nse_sectors

    doc = {
        "records": [
            {
                "symbol": "EXISTING",
                "isin": "INE000A00000",
                "scrip_code": "500000",
                "industry_raw": None,
                "sector": None,
                "sector_source": None,
                "shares_outstanding": 1000,
            }
        ],
        "coverage": {"records": 1, "with_sector": 0, "sector_sources": {}},
    }
    map_path = tmp_path / "india_sector_map.json"
    map_path.write_text(json.dumps(doc))

    monkeypatch.setattr(enrich_nse_sectors, "_map_path", lambda: map_path)
    monkeypatch.setattr(enrich_nse_sectors, "_nse_symbols", lambda: ["EXISTING", "NEWSYM"])
    monkeypatch.setattr(enrich_nse_sectors.time, "sleep", lambda _seconds: None)

    class _FakeTicker:
        def __init__(self, ticker: str) -> None:
            self.ticker = ticker

        @property
        def info(self) -> dict:
            return {"sector": "Technology", "industry": "Software - Application"}

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=_FakeTicker))

    assert enrich_nse_sectors.main() == 0

    written = json.loads(map_path.read_text())
    records = written["records"]
    assert len(records) == 2
    for rec in records:
        assert "industry" not in rec, f"{rec['symbol']}: orphaned 'industry' key reappeared"
        assert set(rec) == _CANONICAL_KEYS, (rec["symbol"], sorted(rec))
        assert rec["sector"] == "Technology"
        assert rec["industry_raw"] == "Software - Application"
        assert rec["sector_source"] == "yfinance"
