"""Batch 5 resolver pins: the bundled masters and their live rung (R15-DATA-017/057)."""

from __future__ import annotations

import pytest

from services import symbol_resolver
from services.resolver_masters import regenerate_bse_master


@pytest.fixture(autouse=True)
def _fresh_resolver():
    symbol_resolver.reset_caches_for_tests()
    yield
    symbol_resolver.reset_caches_for_tests()


def test_former_name_query_leads_with_the_bank_not_its_rights_entitlement() -> None:
    """R15-DATA-057: 'Dhanalakshmi Bank' ranked the expired DHAN-RE line first."""
    resolution = symbol_resolver.resolve("Dhanalakshmi Bank", "IN")
    symbols = [c.symbol for c in resolution.candidates]
    assert symbols[0] == "DHANBANK"
    assert "DHAN-RE" not in symbols


def test_an_old_master_with_an_re_line_is_clean_at_load(monkeypatch: pytest.MonkeyPatch) -> None:
    """The loader skips RE lines, so a master bundled before the regeneration
    fix does not make DHAN-RE a BSE equity."""
    real = symbol_resolver._load_master

    def with_re_line(filename: str, **kwargs: object) -> dict:
        master = real(filename, **kwargs)
        if filename == "bse_instruments.json":
            re_row = ["750942", "DHAN-RE", "Dhanlaxmi Bank Ltd", "R", "INE680A20011", "Active"]
            master = {**master, "instruments": [*master["instruments"], re_row]}
        return master

    monkeypatch.setattr(symbol_resolver, "_load_master", with_re_line)
    assert not symbol_resolver.is_bse_symbol("DHAN-RE")
    assert symbol_resolver.is_bse_symbol("DHANBANK")


def test_regeneration_drops_rights_entitlement_lines() -> None:
    def record(code: str, sym: str, group: str, isin: str) -> dict:
        return {
            "SCRIP_CD": code,
            "scrip_id": sym,
            "Scrip_Name": sym,
            "GROUP": group,
            "ISIN_NUMBER": isin,
            "Status": "Active",
            "Mktcap": "1.0",
        }

    master = regenerate_bse_master.build_master(
        [
            record("532180", "DHANBANK", "A", "INE680A01011"),
            record("750942", "DHAN-RE", "R", "INE680A20011"),
        ],
        min_rows=1,
    )
    assert [row[1] for row in master["instruments"]] == ["DHANBANK"]
