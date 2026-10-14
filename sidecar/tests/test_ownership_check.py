"""R13 / D68 — ``services.ownership_check``: the yfinance-vs-exchange-SHP seam.

No live network: the ``corporate_disclosures.get_shareholding`` fetch is
monkeypatched (mirroring the ``growth_check`` test discipline), so these pin the
applicability gate, the never-raise contract, and the exchange circuit wiring.
"""

from __future__ import annotations

import asyncio
from datetime import date

import pytest

from models.announcements import ShareholdingPattern, ShareholdingResponse
from services import corporate_disclosures, ownership_check, provider_health, symbol_resolver
from services.errors import ProviderError


@pytest.fixture(autouse=True)
def _reset() -> None:
    provider_health.reset_for_tests()
    symbol_resolver.reset_caches_for_tests()


def _response(**pattern_fields: object) -> ShareholdingResponse:
    pattern = ShareholdingPattern(symbol="X", quarter_end=date(2026, 6, 30), **pattern_fields)
    return ShareholdingResponse(symbol="X", count=1, patterns=[pattern])


def test_should_cross_check_requires_a_provider_scalar() -> None:
    assert ownership_check.should_cross_check({"held_percent_insiders": 0.4})
    assert ownership_check.should_cross_check({"held_percent_institutions": 0.1})
    assert not ownership_check.should_cross_check({})
    assert not ownership_check.should_cross_check({"held_percent_insiders": True})


def test_is_applicable_only_india() -> None:
    assert ownership_check.is_applicable("BOMOXY-B1.BO")  # BSE-only micro-cap listing
    assert not ownership_check.is_applicable("AAPL")
    assert not ownership_check.is_applicable("")


def test_get_exchange_ownership_returns_latest_pattern(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        corporate_disclosures,
        "get_shareholding",
        lambda symbol: _response(
            promoter_percent=73.29,
            institutions_percent=0.06,
            public_percent=26.71,
            source="BSE",
        ),
    )
    result = asyncio.run(ownership_check.get_exchange_ownership("BOMOXY-B1.BO"))
    assert result is not None
    assert result.promoter_percent == 73.29
    assert result.institutions_percent == 0.06
    assert result.as_of_quarter == "2026-06-30"
    assert result.source == "BSE"
    assert result.as_wire()["promoter_percent"] == 73.29


def test_get_exchange_ownership_non_india_never_fetches(monkeypatch: pytest.MonkeyPatch) -> None:
    def must_not_run(symbol: str) -> ShareholdingResponse:
        raise AssertionError("non-India symbol must not reach the exchange lane")

    monkeypatch.setattr(corporate_disclosures, "get_shareholding", must_not_run)
    assert asyncio.run(ownership_check.get_exchange_ownership("AAPL")) is None


def test_us_bound_colliding_ticker_gets_no_exchange_ownership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-DATA-003: research bound to NASDAQ:AMAL (Amalgamated Financial) passes
    the fundamentals leg's listing, the bare ``AMAL``. Amal Ltd (BSE 506597)
    shares the ticker string; its BSE shareholding must never be fetched and
    presented as the US company's promoter holding."""

    def must_not_run(symbol: str) -> ShareholdingResponse:
        raise AssertionError("a US-bound listing must not reach the exchange lane")

    monkeypatch.setattr(corporate_disclosures, "get_shareholding", must_not_run)
    assert asyncio.run(ownership_check.get_exchange_ownership("AMAL")) is None


def test_get_exchange_ownership_failure_is_none_never_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        corporate_disclosures,
        "get_shareholding",
        lambda symbol: (_ for _ in ()).throw(ProviderError("bse shareholding: index HTTP 503")),
    )
    assert asyncio.run(ownership_check.get_exchange_ownership("BOMOXY-B1.BO")) is None
    # a plain miss does NOT open the circuit
    assert not provider_health.is_open(ownership_check.EXCHANGE)


def test_get_exchange_ownership_block_opens_the_circuit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        corporate_disclosures,
        "get_shareholding",
        lambda symbol: (_ for _ in ()).throw(ProviderError("nse_direct: blocked (HTTP 401)")),
    )
    for _ in range(3):
        assert asyncio.run(ownership_check.get_exchange_ownership("BOMOXY-B1.BO")) is None
    assert provider_health.is_open(ownership_check.EXCHANGE)


def test_open_circuit_skips_the_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    provider_health.record_rate_limited(ownership_check.EXCHANGE, weight=3)
    assert provider_health.is_open(ownership_check.EXCHANGE)
    calls = {"n": 0}

    def counting(symbol: str) -> ShareholdingResponse:
        calls["n"] += 1
        return _response(promoter_percent=1.0)

    monkeypatch.setattr(corporate_disclosures, "get_shareholding", counting)
    assert asyncio.run(ownership_check.get_exchange_ownership("BOMOXY-B1.BO")) is None
    assert calls["n"] == 0


def test_get_exchange_ownership_empty_patterns_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        corporate_disclosures,
        "get_shareholding",
        lambda symbol: ShareholdingResponse(symbol="X", count=0, patterns=[]),
    )
    assert asyncio.run(ownership_check.get_exchange_ownership("BOMOXY-B1.BO")) is None


def test_merged_bse_split_keeps_its_own_provenance_in_the_brief(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-RESEARCH-011: the NSE June master row carries an institutions figure
    merged from the BSE XBRL of the March quarter. The brief's institutions basis
    names BSE and March, while the promoter basis stays NSE and June."""
    from services.research.semantics import derive_semantics

    monkeypatch.setattr(
        corporate_disclosures,
        "get_shareholding",
        lambda symbol: _response(
            promoter_percent=20.31,
            institutions_percent=42.9,
            public_percent=79.69,
            source="NSE",
            split_source="BSE",
            split_as_of=date(2026, 3, 31),
        ),
    )
    exchange = asyncio.run(ownership_check.get_exchange_ownership("SIL.NS"))
    assert exchange is not None
    structured = {
        "fundamentals": {
            "ok": True,
            "provider": "yfinance",
            "data": {ownership_check.OWNERSHIP_KEY: exchange.as_wire()},
        }
    }
    data = derive_semantics(structured, "IN")["data"]
    assert data["institutions_percent_exchange"]["basis"] == "BSE shareholding filing, 2026-03-31"
    assert data["promoter_percent_exchange"]["basis"] == "NSE shareholding filing, 2026-06-30"
