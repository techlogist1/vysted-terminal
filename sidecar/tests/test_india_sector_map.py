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

from collections import Counter

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
