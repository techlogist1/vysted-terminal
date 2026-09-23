"""R12 (D66) — the resolver answers a renamed NSE symbol as its CURRENT identity.

The battery finding: eight days after NSE renamed Gujarat Gas Ltd to Gujarat
Energy Limited (GUJGASLTD → GUJENERGY, effective 2026-07-01), the app still
resolved both the name and the old ticker to the stale identity. With the
symbol-change lane's map injected (no live network), the resolver must answer
GUJENERGY with an explicit rename annotation — never a silent swap, and never
the stale symbol.
"""

from __future__ import annotations

from datetime import date

import pytest

from services import nse_symbol_change, symbol_resolver


def _raise_if_network(*_a: object, **_k: object) -> None:
    raise AssertionError("live lookup must not fire for a bundled-master symbol")


@pytest.fixture(autouse=True)
def _rename_map(monkeypatch: pytest.MonkeyPatch):
    """Inject the GUJGASLTD → GUJENERGY hop directly (offline) and pin the date.

    Resets both the live-lookup budget and the symbol-change map so nothing
    leaks into (or out of) the shared resolver test suite.
    """
    symbol_resolver._reset_live_lookup_for_tests()
    monkeypatch.setattr(symbol_resolver, "_live_lookup", _raise_if_network)
    monkeypatch.setattr(nse_symbol_change, "_ist_today", lambda: date(2026, 7, 10))
    nse_symbol_change.set_active_map_for_tests(
        {
            "GUJGASLTD": nse_symbol_change.SymbolChange(
                old_symbol="GUJGASLTD",
                new_symbol="GUJENERGY",
                effective_date=date(2026, 7, 1),
                new_name="GUJARAT ENERGY LIMITED",
            ),
        }
    )
    yield
    nse_symbol_change.reset_for_tests()
    symbol_resolver._reset_live_lookup_for_tests()


def _assert_renamed_to_gujenergy(best: symbol_resolver.Instrument) -> None:
    assert best.symbol == "GUJENERGY"
    assert best.exchange == "NSE"
    assert best.region == "IN"
    assert best.yahoo_symbol == "GUJENERGY.NS"
    assert best.name == "GUJARAT ENERGY LIMITED"
    assert best.rename is not None
    assert best.rename.renamed_from == "GUJGASLTD"
    assert best.rename.renamed_to == "GUJENERGY"
    assert best.rename.effective_date == "2026-07-01"


def test_old_ticker_resolves_to_current_symbol() -> None:
    r = symbol_resolver.resolve("GUJGASLTD", "IN")
    assert r.best is not None
    _assert_renamed_to_gujenergy(r.best)
    # The stale NSE ticker must not survive anywhere in the answer.
    assert all(not (c.symbol == "GUJGASLTD" and c.exchange == "NSE") for c in r.candidates)


def test_old_name_resolves_to_current_symbol() -> None:
    r = symbol_resolver.resolve("gujarat gas", "IN")
    assert r.best is not None
    _assert_renamed_to_gujenergy(r.best)


def test_dual_listed_old_ticker_collapses_the_stale_bse_candidate() -> None:
    """D67 gap: GUJGASLTD is dual-listed (NSE + BSE, same company/ISIN). The
    rename post-processing rewrote only the NSE row, stranding the BSE row as a
    stale "Gujarat Gas" candidate at confidence 1.0 with NO provenance — which
    also forced a spurious residual-tie disambiguation. Applying the rename to the
    candidate list too rewrites the BSE row to the current identity, dedupes it
    against the already-current NSE row, and lets the query bind cleanly."""
    r = symbol_resolver.resolve("GUJGASLTD", "IN")
    assert r.best is not None
    _assert_renamed_to_gujenergy(r.best)
    # No stale GUJGASLTD survives on ANY exchange (the pre-fix bug left the BSE row).
    assert all(c.symbol != "GUJGASLTD" for c in r.candidates)
    # Every surviving candidate is the current identity and carries provenance.
    assert r.candidates and all(
        c.symbol == "GUJENERGY" and c.rename is not None for c in r.candidates
    )
    # Collapsed to a single clean candidate → binds, never a disambiguation.
    assert len(r.candidates) == 1
    assert not r.needs_disambiguation


def _inject(old: str, new: str, effective: date, new_name: str) -> None:
    nse_symbol_change.set_active_map_for_tests(
        {old: nse_symbol_change.SymbolChange(old, new, effective, new_name)}
    )


@pytest.mark.parametrize(
    ("old", "new", "effective", "new_name"),
    [
        # BSE-only companies whose ticker string equals a retired NSE symbol.
        ("NSDL", "GUJENERGY", date(2026, 7, 1), "GUJARAT ENERGY LIMITED"),
        ("SHREE", "AJMERA", date(2009, 6, 23), "Ajmera Realty & Infra India Limited"),
        ("HSIL", "AGI", date(2019, 8, 12), "AGI Greenpac Limited"),
        ("WORTH", "WORTHPERI", date(2014, 5, 2), "Worth Peripherals Limited"),
        # A retired NSE ticker reused by a different, currently listed company.
        ("DTIL", "DVL", date(2010, 2, 1), "Dhunseri Ventures Limited"),
    ],
)
def test_rename_never_rewrites_a_different_company(
    old: str, new: str, effective: date, new_name: str
) -> None:
    """R15-DATA-012: the rename row is keyed by the ticker STRING. A BSE-only
    company sharing that string, or a current NSE listing that reused a retired
    ticker, is a different company (a different ISIN) and keeps its own identity:
    no rewrite, no rename note, no borrowed .NS listing."""
    _inject(old, new, effective, new_name)
    r = symbol_resolver.resolve(old, "IN")
    assert r.best is not None
    assert r.best.symbol == old and r.best.rename is None
    assert all(c.symbol != new and c.rename is None for c in r.candidates)


def test_genuine_dual_listed_rename_still_collapses_to_the_current_symbol() -> None:
    """The case the gate was not written against: ITC (NSE + BSE, one ISIN)
    renamed on NSE. Both exchange rows are the same instrument, so both rewrite
    to the one current NSE row, which carries the company's ISIN and binds."""
    _inject("ITC", "ITCNEW", date(2026, 7, 1), "ITC NEW LIMITED")
    r = symbol_resolver.resolve("ITC", "IN")
    assert r.best is not None
    assert r.best.symbol == "ITCNEW" and r.best.exchange == "NSE"
    assert r.best.isin == "INE154A01025"
    assert r.best.rename is not None and r.best.rename.renamed_from == "ITC"
    assert [c.symbol for c in r.candidates] == ["ITCNEW"]
    assert not r.needs_disambiguation


@pytest.mark.parametrize("query", ["zomato", "ZOMATO"])
def test_retired_ticker_missing_from_the_master_resolves_to_current(query: str) -> None:
    """R15-DATA-018: the refreshed master carries ETERNAL but no longer ZOMATO,
    so the old ticker used to answer "No instrument matched". The symbol-change
    master still knows ZOMATO -> ETERNAL: the current instrument binds, with its
    rename provenance and former symbol, before any guess or network lookup."""
    _inject("ZOMATO", "ETERNAL", date(2025, 4, 9), "ETERNAL LIMITED")
    r = symbol_resolver.resolve(query, "IN")
    assert r.best is not None
    assert r.best.symbol == "ETERNAL" and r.best.yahoo_symbol == "ETERNAL.NS"
    assert r.best.rename is not None and r.best.rename.renamed_from == "ZOMATO"
    assert r.best.former_name == "ZOMATO"
    assert not r.needs_disambiguation


def test_autocomplete_lists_the_current_symbol_for_a_retired_ticker() -> None:
    _inject("ZOMATO", "ETERNAL", date(2025, 4, 9), "ETERNAL LIMITED")
    first = symbol_resolver.autocomplete("ZOMATO", "IN")[0]
    assert first.symbol == "ETERNAL"
    assert first.rename is not None and first.rename.renamed_from == "ZOMATO"


def test_current_symbol_exposes_its_former_symbol() -> None:
    """The case the lane was not written against: SEQUENT -> VIYASH (NSE,
    effective 2026-01-23). The old ticker finds VIYASH, and resolving VIYASH
    itself says it was formerly SEQUENT."""
    _inject("SEQUENT", "VIYASH", date(2026, 1, 23), "Viyash Scientific Limited")
    old = symbol_resolver.resolve("SEQUENT", "IN").best
    assert old is not None and old.symbol == "VIYASH"
    current = symbol_resolver.resolve("VIYASH", "IN").best
    assert current is not None and current.symbol == "VIYASH"
    assert current.rename is None
    assert current.former_name == "SEQUENT"


def test_no_rename_when_map_empty() -> None:
    """A cold app with no symbol-change data answers exactly as before (stale but
    honest — never a fabricated rename)."""
    nse_symbol_change.reset_for_tests()  # empty the injected map
    r = symbol_resolver.resolve("GUJGASLTD", "IN")
    assert r.best is not None
    assert r.best.symbol == "GUJGASLTD"
    assert r.best.rename is None
