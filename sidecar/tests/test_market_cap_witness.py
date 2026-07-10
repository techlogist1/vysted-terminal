"""R13 (D72) — ``services.market_cap_witness``: the NON-provider share-count seam.

The existing market-cap check (price × shares) uses the provider's OWN share
count, so it is circular — a stale provider count hides (the RBA ₹5,233 Cr vs
₹4,236 Cr miss during live stake churn). This supplies a BSE-derived share count
from the bundled India master so the witness is independent. Never raises into
research, gated to Indian names that carry a BSE-derived count, and EXCLUDES the
NSE-only enrichment rows whose count was backfilled from yfinance.
"""

from __future__ import annotations

import asyncio

import pytest

from services import market_cap_witness, screener_universe_india, symbol_resolver
from services.market_cap_witness import MarketCapWitness, should_cross_check


@pytest.fixture(autouse=True)
def _reset() -> None:
    symbol_resolver.reset_caches_for_tests()


def _patch_seed(monkeypatch: pytest.MonkeyPatch, record: object) -> None:
    monkeypatch.setattr(
        screener_universe_india,
        "sector_seed_for",
        lambda symbol: record,  # noqa: ARG005
    )


# --- should_cross_check / is_applicable -----------------------------------------


def test_gate_requires_a_provider_market_cap() -> None:
    assert should_cross_check({"market_cap": 5.233e10}) is True
    assert should_cross_check({}) is False
    assert should_cross_check({"market_cap": None}) is False
    assert should_cross_check({"market_cap": True}) is False


def test_is_applicable_only_india() -> None:
    assert market_cap_witness.is_applicable("RBA")  # NSE+BSE
    assert not market_cap_witness.is_applicable("AAPL")
    assert not market_cap_witness.is_applicable("")


# --- get_market_cap_witness: the lookup wrapper ---------------------------------


def test_rba_shape_returns_bse_derived_share_count(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_seed(
        monkeypatch,
        {
            "isin": "INE07T201019",
            "scrip_code": "543248",
            "sector_source": "yfinance",  # sector origin only — shares are BSE-derived
            "shares_outstanding": 582876028,
        },
    )
    witness = asyncio.run(market_cap_witness.get_market_cap_witness("RBA"))
    assert isinstance(witness, MarketCapWitness)
    assert witness.shares_outstanding == 582876028.0
    assert witness.scrip_code == "543248"
    assert "BSE" in witness.source
    assert witness.as_wire()["shares_outstanding"] == 582876028.0


# --- R13 D-2: the as-of date propagated from the bundled master's _generated ----


def test_source_and_as_of_carry_the_bundled_masters_generated_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_seed(monkeypatch, {"scrip_code": "543248", "shares_outstanding": 582876028})
    monkeypatch.setattr(screener_universe_india, "sector_map_generated", lambda: "2026-06-11")
    witness = asyncio.run(market_cap_witness.get_market_cap_witness("RBA"))
    assert isinstance(witness, MarketCapWitness)
    assert witness.as_of == "2026-06-11"
    assert witness.source == "BSE ListOfScripData (bundled India master) (as of 2026-06-11)"
    assert witness.as_wire()["as_of"] == "2026-06-11"


def test_missing_generated_header_omits_the_as_of_suffix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_seed(monkeypatch, {"scrip_code": "543248", "shares_outstanding": 582876028})
    monkeypatch.setattr(screener_universe_india, "sector_map_generated", lambda: None)
    witness = asyncio.run(market_cap_witness.get_market_cap_witness("RBA"))
    assert isinstance(witness, MarketCapWitness)
    assert witness.as_of is None
    assert witness.source == "BSE ListOfScripData (bundled India master)"
    assert "as of" not in witness.source


def test_nse_only_enrichment_row_is_excluded(monkeypatch: pytest.MonkeyPatch) -> None:
    # No BSE scrip_code → the share count is a yfinance backfill; using it would
    # reintroduce the circularity, so the witness declines.
    _patch_seed(
        monkeypatch,
        {
            "isin": None,
            "scrip_code": None,
            "shares_outstanding": 101250000,
            "sector_source": "yfinance",
        },
    )
    assert asyncio.run(market_cap_witness.get_market_cap_witness("AAKASH")) is None


def test_null_share_count_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    # NHL shape: BSE-listed (has scrip_code) but no priced share count.
    _patch_seed(
        monkeypatch, {"isin": "INE0N4701016", "scrip_code": "544245", "shares_outstanding": None}
    )
    assert asyncio.run(market_cap_witness.get_market_cap_witness("NHL")) is None


def test_missing_record_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_seed(monkeypatch, None)
    assert asyncio.run(market_cap_witness.get_market_cap_witness("RBA")) is None


def test_zero_or_negative_shares_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_seed(monkeypatch, {"scrip_code": "543248", "shares_outstanding": 0})
    assert asyncio.run(market_cap_witness.get_market_cap_witness("RBA")) is None


def test_non_india_never_looks_up(monkeypatch: pytest.MonkeyPatch) -> None:
    def must_not_run(symbol: str) -> object:  # noqa: ARG001
        raise AssertionError("non-India symbol must not reach the master lookup")

    monkeypatch.setattr(screener_universe_india, "sector_seed_for", must_not_run)
    assert asyncio.run(market_cap_witness.get_market_cap_witness("AAPL")) is None


def test_lookup_failure_is_none_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(symbol: str) -> object:  # noqa: ARG001
        raise RuntimeError("master parse failed")

    monkeypatch.setattr(screener_universe_india, "sector_seed_for", explode)
    assert asyncio.run(market_cap_witness.get_market_cap_witness("RBA")) is None


def test_bundled_master_has_rba_bse_derived_count() -> None:
    # An INTEGRATION check against the real bundled master (no patch): RBA carries
    # a BSE-derived share count; NHL does not. Guards the applicability gate
    # against the actual data the witness ships with.
    rba = asyncio.run(market_cap_witness.get_market_cap_witness("RBA"))
    assert rba is not None
    assert rba.shares_outstanding > 0
    assert rba.scrip_code == "543248"
    assert asyncio.run(market_cap_witness.get_market_cap_witness("NHL")) is None
