"""The BSE scrip-master regeneration tooling + the SHIPPED regenerated master.

Offline only: the fixture records mirror the REAL ``ListOfScripData`` record
shape observed live 2026-06-10 (a JSON list; keys ``SCRIP_CD``, ``Scrip_Name``,
``Status``, ``GROUP``, ``ISIN_NUMBER``, ``scrip_id``, ``Issuer_Name``,
``Mktcap``...). The live download happened once, by hand, to produce the
committed ``bse_instruments.json`` — these tests pin the script's parsing/
ordering/safety behaviour and the committed master's integrity (full-universe
row count, SME groups present, the ICONIKSPEV acceptance row).
"""

from __future__ import annotations

import io
import json

import pytest

from services import symbol_resolver
from services.resolver_masters import regenerate_bse_master as regen

# The observed live record shape (one real row + synthetic siblings).
_ICONIK_RECORD = {
    "SCRIP_CD": "511260",
    "Scrip_Name": "Iconik Sports And Events Ltd",
    "Status": "Active",
    "GROUP": "X",
    "FACE_VALUE": "10.00",
    "ISIN_NUMBER": "INE088P01015",
    "INDUSTRY": None,
    "scrip_id": "ICONIKSPEV",
    "Segment": "Equity",
    "NSURL": "https://www.bseindia.com/stock-share-price/iconik-sports-and-events-ltd/iconikspev/511260/",
    "Issuer_Name": "ICONIK SPORTS AND EVENTS LIMITED",
    "Mktcap": "145.83",
}


def _record(code: str, sym: str, name: str, group: str, isin: str, mktcap: str | None) -> dict:
    return {
        "SCRIP_CD": code,
        "Scrip_Name": name,
        "Status": "Active",
        "GROUP": group,
        "ISIN_NUMBER": isin,
        "scrip_id": sym,
        "Segment": "Equity",
        "Issuer_Name": name.upper(),
        "Mktcap": mktcap,
    }


_RECORDS = [
    _ICONIK_RECORD,
    _record("500325", "RELIANCE", "Reliance Industries Ltd", "A", "INE002A01018", "2000000.00"),
    _record("999001", "SMENAME", "Some SME Ltd", "M", "INE000M01010", None),  # no Mktcap
    _record("999002", "SMETNAME", "Some SME-T Ltd", "MT", "INE000M01028", "12.50"),
]


def test_build_master_rows_shape_and_ordering() -> None:
    master = regen.build_master(_RECORDS, min_rows=1)
    rows = master["instruments"]
    # [SCRIP_CODE, SYMBOL, NAME, GROUP, ISIN, STATUS] — 6 columns.
    assert all(len(r) == 6 for r in rows)
    # Market-cap ordering: RELIANCE first, the Mktcap-less SME row last.
    assert rows[0][1] == "RELIANCE"
    assert rows[-1][1] == "SMENAME"
    iconik = next(r for r in rows if r[1] == "ICONIKSPEV")
    assert iconik == [
        "511260",
        "ICONIKSPEV",
        "Iconik Sports And Events Ltd",
        "X",
        "INE088P01015",
        "Active",
    ]
    # SME tiers survive into the group census.
    assert master["_groups"]["M"] == 1
    assert master["_groups"]["MT"] == 1


def test_build_master_dedupes_ticker_keeping_highest_cap() -> None:
    dup = [
        _record("100001", "DUPLI", "Dupli Big Ltd", "B", "INE000D01018", "500.00"),
        _record("100002", "DUPLI", "Dupli Small Ltd", "X", "INE000D01026", "5.00"),
    ]
    master = regen.build_master(dup, min_rows=1)
    rows = [r for r in master["instruments"] if r[1] == "DUPLI"]
    assert len(rows) == 1  # one canonical row per ticker
    assert rows[0][0] == "100001"  # the higher-cap record won


def test_build_master_skips_codeless_or_symbolless_records() -> None:
    bad = [
        _record("", "NOCODE", "No Code Ltd", "X", "INE000N01016", "1.0"),
        _record("100003", "", "No Symbol Ltd", "X", "INE000N01024", "1.0"),
        _ICONIK_RECORD,
    ]
    master = regen.build_master(bad, min_rows=1)
    assert [r[1] for r in master["instruments"]] == ["ICONIKSPEV"]


def test_build_master_refuses_stub_payload() -> None:
    # A WAF block / error page parses to a handful of rows at most — the sanity
    # floor must refuse to emit, protecting the good committed master.
    with pytest.raises(ValueError, match="refusing to emit"):
        regen.build_master(_RECORDS)  # default floor is ~1000


def test_build_master_header_is_dated_and_sourced() -> None:
    master = regen.build_master(_RECORDS, min_rows=1)
    assert master["exchange"] == "BSE"
    assert len(master["_generated"]) == 10  # YYYY-MM-DD
    assert master["_source"] == regen.LIST_URL
    assert "regenerate_bse_master.py" in master["_note"]


def test_dump_master_round_trips_as_json() -> None:
    master = regen.build_master(_RECORDS, min_rows=1)
    buf = io.StringIO()
    regen.dump_master(master, buf)
    parsed = json.loads(buf.getvalue())
    assert parsed["instruments"] == master["instruments"]
    assert parsed["_generated"] == master["_generated"]


def test_fetch_records_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def flaky_fetch() -> list[dict]:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("HTTP 403 from ListOfScripData")
        return list(_RECORDS)

    monkeypatch.setattr(regen, "_fetch_once", flaky_fetch)
    monkeypatch.setattr(regen.time, "sleep", lambda s: None)  # no real backoff in tests
    assert regen.fetch_records() == _RECORDS
    assert calls["n"] == 3


def test_fetch_records_exhausted_raises_systemexit(monkeypatch: pytest.MonkeyPatch) -> None:
    def always_blocked() -> list[dict]:
        raise RuntimeError("HTTP 403 from ListOfScripData")

    monkeypatch.setattr(regen, "_fetch_once", always_blocked)
    monkeypatch.setattr(regen.time, "sleep", lambda s: None)
    with pytest.raises(SystemExit, match="all 4 attempts failed"):
        regen.fetch_records()


# --- the SHIPPED regenerated master (committed file integrity) ---------------


def test_shipped_master_is_the_full_universe() -> None:
    symbol_resolver.reset_caches_for_tests()
    master = symbol_resolver._load_master("bse_instruments.json")
    rows = master["instruments"]
    # The live list is ~4.9k active equity scrips — a full regeneration, not a seed.
    assert len(rows) > 4000
    assert master["_generated"]  # dated header survives in-repo
    groups = {r[3] for r in rows}
    # Every equity tier incl. the SME M/MT groups.
    assert {"A", "B", "T", "X", "XT", "Z", "M", "MT"} <= groups


def test_shipped_master_resolves_iconikspev_deterministically() -> None:
    symbol_resolver.reset_caches_for_tests()
    assert symbol_resolver.is_bse_symbol("ICONIKSPEV")
    assert symbol_resolver.bse_scrip_code("ICONIKSPEV") == "511260"
    # BSE-only (absent from the NSE/US masters) → the bare ticker hints IN, which
    # is what routes /history/ICONIKSPEV into the IN provider chain (bse included).
    assert symbol_resolver.region_hint("ICONIKSPEV") == "IN"
