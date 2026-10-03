"""R15 final pass, data-fundamentals round: money-relevant figure fixes."""

from __future__ import annotations

import asyncio
from datetime import date

import pytest

from models.fundamentals import Fundamentals
from services import correctness_gate
from services.exchange_financials import FiledPeriod, FiledPeriods


def _quarters(*eps: float, net: float = 305_000.0) -> FiledPeriods:
    ends = (date(2026, 6, 30), date(2026, 3, 31), date(2025, 12, 31), date(2025, 9, 30))
    starts = (date(2026, 4, 1), date(2026, 1, 1), date(2025, 10, 1), date(2025, 7, 1))
    return FiledPeriods(
        venue="bse",
        basis="standalone",
        periods=tuple(
            FiledPeriod(s, e, 10_000_000.0, net, q)
            for s, e, q in zip(starts, ends, eps, strict=True)
        ),
    )


# --- R15-FINAL-003: P/E follows the served (exchange-filed) EPS ---------------


def test_sunrajdi_pe_is_rederived_on_the_filed_eps() -> None:
    provider = Fundamentals(
        symbol="SUNRAJDI.BO",
        provider="yfinance",
        currency="INR",
        ratio_price=12.44,
        eps=0.08,
        pe_ratio=155.5,
        net_income_ttm=470_000.0,
        shares_outstanding=5_330_400.0,
    )
    gated = correctness_gate.validate_fundamentals(provider, "SUNRAJDI.BO", "IN")
    assert gated.field_meta["pe_ratio"].status == "flagged"  # the stale 141.1 reason

    served = correctness_gate.overlay_filed_periods(gated, _quarters(0.05, 0.06, 0.06, 0.06))

    assert served.eps == pytest.approx(0.23)
    assert served.pe_ratio == pytest.approx(12.44 / 0.23)
    assert round(served.pe_ratio, 1) == 54.1
    meta = served.field_meta["pe_ratio"]
    assert meta.status == "ok"
    assert meta.provider == "derived"
    assert "exchange-filed TTM EPS" in (meta.basis_note or "")
    assert meta.reason is None
    assert "141.1" not in str(served.field_meta)


def test_a_filed_eps_above_the_providers_lowers_the_pe() -> None:
    provider = Fundamentals(
        symbol="ICON.NS",
        provider="yfinance",
        currency="INR",
        ratio_price=80.0,
        eps=2.0,
        pe_ratio=40.0,
    )
    served = correctness_gate.overlay_filed_periods(provider, _quarters(1.0, 1.0, 1.0, 1.0))
    assert served.pe_ratio == pytest.approx(20.0)
    assert served.field_meta["pe_ratio"].provider == "derived"


def test_a_non_positive_filed_eps_withholds_the_providers_pe() -> None:
    provider = Fundamentals(
        symbol="ICON.NS",
        provider="yfinance",
        currency="INR",
        ratio_price=80.0,
        eps=2.0,
        pe_ratio=40.0,
    )
    served = correctness_gate.overlay_filed_periods(provider, _quarters(-1.0, 0.2, 0.2, 0.1))
    assert served.pe_ratio is None
    assert served.field_meta["pe_ratio"].status == "withheld"


# --- R15-FINAL-024: no ownership flag inside the 3pp band ---------------------


def _amal_exchange(institutions: float):  # noqa: ANN202
    from services.ownership_check import ExchangeOwnership

    return ExchangeOwnership(
        promoter_percent=63.4,
        institutions_percent=institutions,
        public_percent=36.6,
        as_of_quarter="2026-06-30",
        source="BSE",
    )


def test_zero_beside_a_small_filed_institutions_figure_is_not_flagged() -> None:
    f = Fundamentals(
        symbol="AMAL.NS",
        provider="yfinance",
        held_percent_insiders=0.634,
        held_percent_institutions=0.0,
    )
    out = correctness_gate.reconcile_ownership(f, _amal_exchange(0.03))
    assert (out.field_meta or {}).get("held_percent_institutions") is None


def test_zero_beside_a_large_filed_institutions_figure_is_flagged_truthfully() -> None:
    f = Fundamentals(
        symbol="AMAL.NS",
        provider="yfinance",
        held_percent_insiders=0.634,
        held_percent_institutions=0.0,
    )
    out = correctness_gate.reconcile_ownership(f, _amal_exchange(12.0))
    meta = out.field_meta["held_percent_institutions"]
    assert meta.status == "flagged"
    assert "0.00%" in meta.reason and "12.00%" in meta.reason and "beyond 3pp" in meta.reason


# --- R15-FINAL-009: missing market cap derived from the BSE master count -------


def _no_filings(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import exchange_financials

    async def none(_listing: str) -> None:
        return None

    monkeypatch.setattr(exchange_financials, "get_filed_periods", none)
    correctness_gate.reset_witness_cache_for_tests()


def _served(symbol: str, **fields: float) -> Fundamentals:
    return Fundamentals(symbol=symbol, provider="nse", currency="INR", ratio_price=703.0, **fields)


def test_amal_ns_market_cap_is_derived_from_the_master_share_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services import market_cap_witness

    _no_filings(monkeypatch)
    master = market_cap_witness._lookup("AMAL.NS")
    assert master is not None and master.scrip_code == "506597"

    out = asyncio.run(correctness_gate.apply_witnesses(_served("AMAL.NS")))

    assert out.shares_outstanding == master.shares_outstanding
    assert out.market_cap == pytest.approx(703.0 * master.shares_outstanding)
    meta = out.field_meta["market_cap"]
    assert meta.status == "ok" and meta.provider == "derived"
    assert "master share count" in meta.basis_note and "BSE ListOfScripData" in meta.basis_note
    assert out.field_meta["shares_outstanding"].provider == "derived"


def test_a_served_market_cap_is_never_overridden(monkeypatch: pytest.MonkeyPatch) -> None:
    _no_filings(monkeypatch)
    out = asyncio.run(
        correctness_gate.apply_witnesses(
            _served("AMAL.NS", market_cap=8_690_951_168.0, shares_outstanding=12_362_662.0)
        )
    )
    assert out.market_cap == 8_690_951_168.0
    assert out.shares_outstanding == 12_362_662.0
    assert out.field_meta is None


def test_another_companys_bse_row_under_the_same_ticker_is_not_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NSE ZEAL (Zeal Global) vs BSE ZEAL (Zeal Aqua): the master row keyed by
    the ticker is the other company's share count."""
    _no_filings(monkeypatch)
    out = asyncio.run(correctness_gate.apply_witnesses(_served("ZEAL.NS")))
    assert out.market_cap is None
    assert out.shares_outstanding is None


# --- R15-FINAL-005: NSE Emerge (SME) fundamentals from the exchange filings ----

#: YASHOPTICS as NSE served it (live probe 2026-10-03, evidence
#: fix-r1/data-fundamentals/final-005-yashoptics-filed-periods.txt).
_YASH_FILED = FiledPeriods(
    venue="nse",
    basis="standalone",
    periods=(
        FiledPeriod(date(2025, 10, 1), date(2026, 3, 31), 306_140_000.0, 59_271_000.0, 2.39),
        FiledPeriod(date(2025, 4, 1), date(2025, 9, 30), 233_758_000.0, 31_210_000.0, 1.26),
        FiledPeriod(date(2024, 10, 1), date(2025, 3, 31), 237_077_000.0, 50_384_000.0, 2.03),
    ),
)


def _sme_lanes(monkeypatch: pytest.MonkeyPatch, filed: dict[str, FiledPeriods]) -> None:
    """Every fundamentals provider not_found, empty statements, a live quote,
    and the exchange lane answering ``filed`` per listing."""
    from datetime import UTC, datetime

    from models.fundamentals import IncomeStatement
    from models.market import Quote
    from services import exchange_financials, provider_registry, yfinance_provider
    from services.errors import ProviderError
    from services.provider_registry import ProviderDeclaration

    def not_found(symbol: str) -> None:
        raise ProviderError(f"yfinance has no instrument data for {symbol!r}", kind="not_found")

    def quote(symbol: str) -> Quote:
        return Quote(
            symbol=yfinance_provider._yahoo_symbol(symbol),
            price=135.0,
            change=None,
            change_percent=None,
            currency="INR",
            timestamp=datetime.now(UTC),
            provider="nse_direct",
        )

    def income(symbol: str, _period: str) -> IncomeStatement:
        return IncomeStatement(
            symbol=yfinance_provider._yahoo_symbol(symbol), periods=[], lines=[], provider="yf"
        )

    async def filed_periods(listing: str) -> FiledPeriods | None:
        return filed.get(listing)

    monkeypatch.setattr(
        provider_registry,
        "_PROVIDERS",
        (
            ProviderDeclaration(
                id="yf",
                rank=10,
                serves={"fundamentals": not_found, "quote": quote, "income_statement": income},
            ),
        ),
    )
    monkeypatch.setattr(exchange_financials, "get_filed_periods", filed_periods)


def _route(monkeypatch: pytest.MonkeyPatch, symbol: str):  # noqa: ANN202
    """GET /fundamentals/<symbol> (IN) with the route's other network reads stubbed."""
    from fastapi.testclient import TestClient

    from app import create_app
    from routers import fundamentals as route
    from services import exchange_financials

    async def none(*_args: object) -> None:
        return None

    async def same(f: Fundamentals) -> Fundamentals:
        return f

    monkeypatch.setattr(exchange_financials, "filed_basis", none)
    monkeypatch.setattr(route, "_identity_note", none)
    monkeypatch.setattr(correctness_gate, "apply_witnesses", same)
    return TestClient(create_app()).get(
        f"/fundamentals/{symbol}", headers={"X-Vysted-Region": "IN"}
    )


def test_yashoptics_fundamentals_come_from_the_nse_filings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _sme_lanes(monkeypatch, {"YASHOPTICS-SM.NS": _YASH_FILED})
    resp = _route(monkeypatch, "YASHOPTICS")

    assert resp.status_code == 200, resp.text
    f = resp.json()
    assert f["symbol"] == "YASHOPTICS-SM.NS"
    assert f["revenue_ttm"] == pytest.approx(539_898_000.0)  # 53.99 Cr, screener FY26
    assert f["net_income_ttm"] == pytest.approx(90_481_000.0)
    assert f["eps"] == pytest.approx(3.65)
    assert f["pe_ratio"] == pytest.approx(135.0 / 3.65)
    meta = f["field_meta"]
    assert meta["revenue_ttm"]["provider"] == "nse"
    assert "sum of 2 filed half-years" in meta["revenue_ttm"]["label"]
    assert meta["pe_ratio"]["provider"] == "derived"


def test_an_sme_listing_with_no_filings_says_it_is_not_covered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _sme_lanes(monkeypatch, {})
    resp = _route(monkeypatch, "SUMAX")
    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert "No data provider covers fundamentals for this NSE Emerge (SME) listing" in detail
    assert "no results filing" in detail
    assert "check the symbol" not in detail


def test_the_registry_crawler_path_never_walks_the_filings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The screener/warm crawlers read ``get_fundamentals``: it states the
    coverage gap but never hits the exchange lane (one NSE walk per symbol)."""
    from services import exchange_financials, provider_registry
    from services.errors import ProviderError, provider_error_response

    _sme_lanes(monkeypatch, {"YASHOPTICS-SM.NS": _YASH_FILED})

    async def boom(_listing: str) -> None:
        raise AssertionError("the exchange lane rode the crawler path")

    monkeypatch.setattr(exchange_financials, "get_filed_periods", boom)
    with pytest.raises(ProviderError) as caught:
        asyncio.run(provider_registry.get_fundamentals("YASHOPTICS.NS", region="IN"))
    status, body = provider_error_response(caught.value)
    assert status == 404
    assert "NSE Emerge (SME) listing" in body["detail"]
    assert "check the symbol" not in body["detail"]


def test_an_unknown_symbol_still_reads_check_the_symbol(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import provider_registry
    from services.errors import ProviderError, provider_error_response

    _sme_lanes(monkeypatch, {})
    with pytest.raises(ProviderError) as caught:
        asyncio.run(provider_registry.get_fundamentals("ZZQXNOTREAL.NS", region="IN"))
    assert "check the symbol" in provider_error_response(caught.value)[1]["detail"]


def test_an_empty_sme_statement_carries_the_not_covered_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services import provider_registry

    _sme_lanes(monkeypatch, {})
    statement = asyncio.run(provider_registry.get_income_statement("SUMAX.NS", region="IN"))
    assert statement.periods == []
    assert "NSE Emerge (SME)" in (statement.reason or "")


# --- R15-FINAL-005 round 2: SME filers whose Sep/Mar filing is half-year only ---

#: VOLERCAR as NSE served it (live probe 2026-10-03, round 2): quarterly results
#: in Jun/Dec, but the Sep-25 and Mar-26 Integrated Filings carry only the
#: 6-month context, so no four filed quarters or two filed halves end on
#: 2026-06-30 and round 1's trailing chain came back empty.
_VOLERCAR_FILED = FiledPeriods(
    venue="nse",
    basis="standalone",
    periods=(
        FiledPeriod(date(2026, 4, 1), date(2026, 6, 30), 142_105_000.0, 10_954_000.0, 0.98),
        FiledPeriod(date(2025, 10, 1), date(2026, 3, 31), 266_055_000.0, 13_384_000.0, 1.2),
        FiledPeriod(date(2025, 10, 1), date(2025, 12, 31), 126_540_000.0, 6_417_000.0, 0.58),
        FiledPeriod(date(2025, 4, 1), date(2025, 9, 30), 262_386_000.0, 21_322_000.0, 1.91),
        FiledPeriod(date(2025, 4, 1), date(2025, 6, 30), 123_519_000.0, 12_704_000.0, 1.14),
    ),
)
#: GANESHIN consolidated (live probe 2026-10-03): consolidated filings start at
#: Sep-25, so Apr-Jun 2025 has no consolidated quarter and no chain reaches
#: 2026-06-30; the two FY26 halves are the newest complete year.
_GANESHIN_FILED = FiledPeriods(
    venue="nse",
    basis="consolidated",
    periods=(
        FiledPeriod(date(2026, 4, 1), date(2026, 6, 30), 3_787_661_000.0, 297_144_000.0, 6.96),
        FiledPeriod(date(2025, 10, 1), date(2026, 3, 31), 4_449_132_000.0, 434_998_000.0, 10.18),
        FiledPeriod(date(2025, 10, 1), date(2025, 12, 31), 2_153_286_000.0, 190_413_000.0, 4.46),
        FiledPeriod(date(2025, 4, 1), date(2025, 9, 30), 3_906_324_000.0, 326_729_000.0, 7.65),
    ),
)
_VOLERCAR_TTM_REVENUE = 142_105_000.0 + 266_055_000.0 + (262_386_000.0 - 123_519_000.0)
_VOLERCAR_TTM_INCOME = 10_954_000.0 + 13_384_000.0 + (21_322_000.0 - 12_704_000.0)
_VOLERCAR_TTM_EPS = 0.98 + 1.2 + (21_322_000.0 - 12_704_000.0) * 1.91 / 21_322_000.0
_HEADLINE = ("revenue_ttm", "net_income_ttm", "eps", "pe_ratio", "market_cap")


def test_volercar_ttm_is_built_from_its_half_year_less_the_filed_quarter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _sme_lanes(monkeypatch, {"VOLERCAR-SM.NS": _VOLERCAR_FILED})
    resp = _route(monkeypatch, "VOLERCAR")

    assert resp.status_code == 200, resp.text
    f = resp.json()
    assert f["revenue_ttm"] == pytest.approx(_VOLERCAR_TTM_REVENUE)  # 54.70 Cr
    assert f["net_income_ttm"] == pytest.approx(_VOLERCAR_TTM_INCOME)
    assert f["eps"] == pytest.approx(_VOLERCAR_TTM_EPS)
    assert f["pe_ratio"] == pytest.approx(135.0 / _VOLERCAR_TTM_EPS)
    shares = _VOLERCAR_TTM_INCOME / _VOLERCAR_TTM_EPS
    assert f["market_cap"] == pytest.approx(135.0 * shares)
    meta = f["field_meta"]
    revenue = meta["revenue_ttm"]
    assert (revenue["provider"], revenue["as_of"]) == ("nse", "2026-06-30")
    assert (
        "2025-07-01..2025-09-30 derived as the filed half-year 2025-04-01..2025-09-30"
        in (revenue["label"])
    )
    assert meta["pe_ratio"]["provider"] == "derived"
    assert meta["market_cap"]["provider"] == "derived"
    assert "imply" in meta["market_cap"]["basis_note"]


def test_the_derived_fill_never_replaces_a_provider_size() -> None:
    """The witness path (Yahoo answered a name+price shell, stamping every null
    'provider did not publish this field') fills VOLERCAR from the filings;
    a main-board listing whose provider sized it keeps the provider's figure
    and its quarterly-gap cadence label (R15-LEAD-004 unchanged)."""
    from models.fundamentals import FieldMeta

    generic = FieldMeta(
        status="unavailable", provider="yfinance", reason="provider did not publish this field"
    )
    shell = Fundamentals(
        symbol="VOLERCAR-SM.NS",
        currency="INR",
        ratio_price=216.3,
        provider="yfinance",
        field_meta={name: generic for name in _HEADLINE},
    )
    served = correctness_gate.overlay_filed_periods(shell, _VOLERCAR_FILED)
    assert served.revenue_ttm == pytest.approx(_VOLERCAR_TTM_REVENUE)
    assert served.pe_ratio == pytest.approx(216.3 / _VOLERCAR_TTM_EPS)
    assert served.field_meta is not None
    assert all(served.field_meta[name].status == "ok" for name in _HEADLINE)

    sized = Fundamentals(symbol="NDTV.NS", currency="INR", revenue_ttm=4.0e9, provider="yfinance")
    kept = correctness_gate.overlay_filed_periods(sized, _VOLERCAR_FILED)
    assert kept.revenue_ttm == 4.0e9
    assert _VOLERCAR_FILED.cadence() == "quarterly-gap"


def test_ganeshin_serves_the_newest_complete_filed_year_stating_its_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _sme_lanes(monkeypatch, {"GANESHIN-SM.NS": _GANESHIN_FILED})
    resp = _route(monkeypatch, "GANESHIN")

    assert resp.status_code == 200, resp.text
    f = resp.json()
    assert f["revenue_ttm"] == pytest.approx(8_355_456_000.0)  # FY26 consolidated
    assert f["net_income_ttm"] == pytest.approx(761_727_000.0)
    assert f["eps"] == pytest.approx(17.83)
    revenue = f["field_meta"]["revenue_ttm"]
    assert revenue["as_of"] == "2026-03-31"
    assert "sum of 2 filed half-years to 2026-03-31" in revenue["label"]


def test_too_few_filed_periods_state_a_typed_reason_on_every_headline_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fresh SME listing with one filed quarter: 200 with the price and a
    typed reason on every null headline field, never a silent null or a 404."""
    one = FiledPeriods(
        venue="nse",
        basis="standalone",
        periods=(FiledPeriod(date(2026, 4, 1), date(2026, 6, 30), 50_000_000.0, 4_000_000.0, 0.5),),
    )
    _sme_lanes(monkeypatch, {"FRESHSME-SM.NS": one})
    from services import provider_registry

    monkeypatch.setattr(provider_registry, "_is_known_india_listing", lambda _listing: True)
    resp = _route(monkeypatch, "FRESHSME-SM.NS")

    assert resp.status_code == 200, resp.text
    f = resp.json()
    for name in _HEADLINE:
        assert f[name] is None
        meta = f["field_meta"][name]
        assert meta["status"] == "unavailable"
        assert "not published by the data provider" in meta["reason"]
        assert "check the symbol" not in meta["reason"]
    assert "insufficient filed periods" in f["field_meta"]["revenue_ttm"]["reason"]
    assert "no trailing EPS" in f["field_meta"]["pe_ratio"]["reason"]


def test_an_unread_filing_states_why_each_headline_field_is_null(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The witness path with no filing read (SUMAX, QUALIANCE): every null
    headline field names that, over the provider's generic stamp."""
    from models.fundamentals import FieldMeta
    from services import exchange_financials, market_cap_witness

    async def none(*_args: object) -> None:
        return None

    monkeypatch.setattr(exchange_financials, "get_filed_periods", none)
    monkeypatch.setattr(market_cap_witness, "get_market_cap_witness", none)
    generic = FieldMeta(
        status="unavailable", provider="nse_direct", reason="provider did not publish this field"
    )
    shell = Fundamentals(
        symbol="SUMAX-SM.NS",
        currency="INR",
        ratio_price=50.0,
        provider="nse_direct",
        field_meta={"revenue_ttm": generic},
    )
    served = asyncio.run(correctness_gate.apply_witnesses(shell))
    assert served.field_meta is not None
    for name in _HEADLINE:
        reason = served.field_meta[name].reason or ""
        assert "no exchange-filed results could be read" in reason, name
