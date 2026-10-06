"""Batch 5 resolver pins: the bundled masters and their live rung (R15-DATA-017/057)."""

from __future__ import annotations

import os

import pytest

from services import symbol_resolver
from services.resolver_masters import regenerate_bse_master, regenerate_nse_master
from services.symbol_resolver import _refreshed_master as _real_refreshed_master


@pytest.fixture(autouse=True)
def _fresh_resolver(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(symbol_resolver, "_live_lookup", lambda query, region: [])
    symbol_resolver.reset_caches_for_tests()
    yield
    symbol_resolver.reset_caches_for_tests()


def _bundled_without(monkeypatch: pytest.MonkeyPatch, *symbols: str) -> None:
    """Serve the bundled masters as a June snapshot that predates ``symbols``."""
    real = symbol_resolver._load_master

    def older(filename: str, **kwargs: object) -> dict:
        master = real(filename, **kwargs)
        column = 1 if filename == "bse_instruments.json" else 0
        rows = [r for r in master.get("instruments", []) if r[column] not in symbols]
        return {**master, "instruments": rows}

    monkeypatch.setattr(symbol_resolver, "_load_master", older)


def _live_row(symbol: str, name: str) -> symbol_resolver.Instrument:
    return symbol_resolver.Instrument(
        symbol, name, "NSE", "IN", "equity", f"{symbol}.NS", symbol_resolver._DISAMBIGUATE_SCORE
    )


_EQUITY_L = (
    "SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, "
    "ISIN NUMBER, FACE VALUE\n"
    "JNPR,Juniper Green Energy Limited,EQ,06-AUG-2026,10,1,INE05C901015,10\n"
    "CENTEXT-RE,Centum Rights Entitlement,EQ,01-SEP-2026,1,1,INE000A20012,1\n"
)
_SME_EQUITY_L = (
    "SYMBOL,NAME_OF_COMPANY,SERIES,DATE_OF_LISTING,PAID_UP_VALUE,ISIN_NUMBER,FACE_VALUE,\n"
    "SUMAX,Sumax Engineering Limited,SM,02-Sep-26,10,INE11Z001019,10,\n"
)
_ETF_LIST = (
    "Symbol,Underlying Asset,SecurityName,DateofListing,MarketLot,ISINNumber,FaceValue\n"
    "GOLDBEES,Gold,NIPINDETFGOLDBEES,19-Mar-07,1,INF204KB17I5,1\n"
)


def _refreshed_nse() -> dict:
    return regenerate_nse_master.build_master(
        _EQUITY_L, _SME_EQUITY_L, _ETF_LIST, isin_rank={}, min_rows=1
    )


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


# --- R15-DATA-017 -------------------------------------------------------------


def test_nse_regeneration_types_emerge_rows_sm_and_drops_re_lines() -> None:
    rows = _refreshed_nse()["instruments"]
    assert rows == [
        ["JNPR", "Juniper Green Energy Limited", "EQ"],
        ["SUMAX", "Sumax Engineering Limited", "SM"],
        ["GOLDBEES", "NIPINDETFGOLDBEES", "ETF"],
    ]


def test_a_refreshed_list_makes_post_snapshot_listings_members(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """JNPR (main board) and SUMAX (Emerge) listed after the bundled snapshot;
    the refreshed list unions them in, and SUMAX maps to Yahoo's -SM.NS form."""
    import config
    from services import yfinance_provider

    _bundled_without(monkeypatch, "JNPR", "SUMAX")
    assert not symbol_resolver.is_nse_symbol("JNPR")
    symbol_resolver.reset_caches_for_tests()
    refreshed = _refreshed_nse()
    monkeypatch.setattr(
        symbol_resolver,
        "_refreshed_master",
        lambda filename: refreshed if filename == "nse_instruments.json" else None,
    )
    assert symbol_resolver.is_nse_symbol("JNPR")
    assert symbol_resolver.is_nse_symbol("SUMAX")
    assert symbol_resolver.is_nse_symbol("RELIANCE")  # the bundled rows stay
    token = config.set_request_region("IN")
    try:
        assert yfinance_provider._yahoo_symbol("SUMAX") == "SUMAX-SM.NS"
        assert yfinance_provider._yahoo_symbol("SUMAX.NS") == "SUMAX-SM.NS"
        assert yfinance_provider._yahoo_symbol("JNPR") == "JNPR.NS"
    finally:
        config.reset_request_region(token)
    assert symbol_resolver.resolve("SUMAX", "IN").best.yahoo_symbol == "SUMAX-SM.NS"


def test_the_disclosures_gate_admits_a_post_snapshot_listing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DHOOTTRANS (listed 2026-08-17) no longer fails the membership gate."""
    from services import corporate_disclosures

    monkeypatch.setattr(corporate_disclosures, "_nse_shareholding", lambda bare: [])
    monkeypatch.setattr(corporate_disclosures, "_bse_shareholding", lambda bare: [])
    response = corporate_disclosures.get_shareholding("DHOOTTRANS")
    assert response.symbol == "DHOOTTRANS"
    assert response.count == 0


@pytest.mark.parametrize(
    ("query", "absent", "live"),
    [
        ("Sumax Engineering Limited", "SUMAX", _live_row("SUMAX", "Sumax Engineering Limited")),
        ("Juniper Green Energy Limited", "JNPR", _live_row("JNPR", "Juniper Green Energy Ltd")),
    ],
)
def test_live_search_runs_when_the_fuzzy_best_shares_only_generic_words(
    monkeypatch: pytest.MonkeyPatch, query: str, absent: str, live: symbol_resolver.Instrument
) -> None:
    """A name missing from the masters fuzzes onto '... Engineering Ltd' /
    '... Green Energy Ltd' hits; the live rung still runs and its row joins the
    candidates (it used to run only when the masters found nothing)."""
    _bundled_without(monkeypatch, absent)
    asked: list[str] = []

    def lookup(q: str, region: str) -> list[symbol_resolver.Instrument]:  # noqa: ARG001
        asked.append(q)
        return [live]

    monkeypatch.setattr(symbol_resolver, "_live_lookup", lookup)
    resolution = symbol_resolver.resolve(query, "IN")
    assert asked == [query]
    assert live.symbol in [c.symbol for c in resolution.candidates]


def test_a_fuzzy_hit_on_a_distinctive_word_does_not_go_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def lookup(q: str, region: str) -> list:  # noqa: ARG001
        raise AssertionError("the live rung must not run")

    monkeypatch.setattr(symbol_resolver, "_live_lookup", lookup)
    assert symbol_resolver.resolve("Reliance Industries", "IN").best.symbol == "RELIANCE"


def test_refresh_writes_the_lists_to_the_data_dir_daily(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    """The runtime refresh lands in <data-dir>/resolver_masters/, the loaders
    union it, and a copy under a day old is not fetched again."""
    import config

    monkeypatch.setenv(config.DATA_DIR_ENV, str(tmp_path))
    monkeypatch.setattr(symbol_resolver, "_refreshed_master", _real_refreshed_master)
    monkeypatch.setattr(symbol_resolver, "_schedule_master_refresh", lambda: None)
    fetches: list[str] = []

    def fetch_nse() -> dict:
        fetches.append("nse")
        return _refreshed_nse()

    def fetch_bse() -> dict:
        fetches.append("bse")
        raise SystemExit("regenerate_bse_master: all 4 attempts failed: HTTP 403")

    monkeypatch.setattr(
        symbol_resolver,
        "_REFRESH_FETCHERS",
        {"nse_instruments.json": fetch_nse, "bse_instruments.json": fetch_bse},
    )
    _bundled_without(monkeypatch, "SUMAX")
    assert not symbol_resolver.is_nse_symbol("SUMAX")

    symbol_resolver.refresh_masters()
    assert fetches == ["nse", "bse"]
    assert symbol_resolver.is_nse_symbol("SUMAX")  # caches dropped, refreshed copy unioned
    assert symbol_resolver.is_bse_symbol("DHANBANK")  # a failed BSE fetch keeps the bundle

    symbol_resolver.refresh_masters()
    assert fetches == ["nse", "bse", "bse"]  # the NSE copy is fresh; BSE retries

    stale = tmp_path / "resolver_masters" / "nse_instruments.json"  # type: ignore[operator]
    old = stale.stat().st_mtime - symbol_resolver._REFRESH_INTERVAL_SECONDS - 1
    os.utime(stale, (old, old))
    symbol_resolver.refresh_masters()
    assert fetches == ["nse", "bse", "bse", "nse", "bse"]
