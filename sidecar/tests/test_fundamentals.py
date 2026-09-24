"""Tests for the /fundamentals router."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _no_network_filed_basis(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the route's filed-basis read (R15-DATA-054) off the network; its
    own cases live in ``test_fundamentals_basis.py``."""
    from services import exchange_financials

    async def _stub(_listing: str) -> None:
        return None

    monkeypatch.setattr(exchange_financials, "filed_basis", _stub)


@pytest.fixture(autouse=True)
def _isolated_data_cache(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: ANN001
    """The statement and rating routes are cached (R15-DATA-096): each test gets
    its own cache file, so one test's fake never serves the next."""
    from config import DATA_DIR_ENV
    from services import data_cache

    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    data_cache.reset_for_tests()
    yield
    data_cache.reset_for_tests()


def test_get_fundamentals(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/fundamentals/AAPL").json()
    assert body["symbol"] == "AAPL"
    assert body["name"] == "Apple Inc."
    assert body["sector"] == "Technology"
    assert body["pe_ratio"] == 31.2
    assert body["beta"] == 1.25
    # yfinance 1.3.0 returns ``dividendYield`` as a percentage number
    # (the fake supplies ``0.44``); the provider divides by 100 so the
    # ``dividend_yield`` field carries a true fraction.
    assert body["dividend_yield"] == pytest.approx(0.0044)
    assert body["provider"] == "yfinance"
    # D55: the growth-basis truth rides the raw REST response (the panel/agent
    # bypass semantics.py, so the contract itself must carry it).
    assert body["growth_basis"] == "mrq_yoy"
    # R13 ledger #8: AAPL's provider name ("Apple Inc.") agrees with the
    # bundled master's canonical name — no identity_note.
    assert body["identity_note"] is None


def test_get_fundamentals_provider_error_is_502(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A provider failure is an honest 502, never an unhandled 500."""
    from services import provider_registry
    from services.errors import ProviderError

    async def boom(symbol: str):  # noqa: ANN202
        raise ProviderError("yfinance fundamentals failed for 'AAPL': upstream 500")

    monkeypatch.setattr(provider_registry, "get_fundamentals", boom)
    resp = client.get("/fundamentals/AAPL")
    assert resp.status_code == 502
    assert "upstream 500" in resp.json()["detail"]


def test_get_fundamentals_rate_limited_is_429(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A throttle (ProviderError.kind == 'rate_limited') is a 429 with a human
    'try again shortly' detail — not a 502 or a no-data masquerade."""
    from services import provider_registry
    from services.errors import ProviderError

    async def throttled(symbol: str):  # noqa: ANN202
        raise ProviderError("429 Too Many Requests", kind="rate_limited")

    monkeypatch.setattr(provider_registry, "get_fundamentals", throttled)
    resp = client.get("/fundamentals/AAPL")
    assert resp.status_code == 429
    assert "throttled" in resp.json()["detail"].lower()


def test_get_fundamentals_dividend_yield_missing(
    client: TestClient,
    mock_yfinance: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing ``dividendYield`` stays ``None`` — no divide-by-100 crash."""
    from services import yfinance_provider

    class _NoYieldTicker(mock_yfinance):  # type: ignore[misc, valid-type]
        @property
        def info(self) -> dict:
            data = super().info.copy()
            data.pop("dividendYield", None)
            return data

    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _NoYieldTicker)
    body = client.get("/fundamentals/AAPL").json()
    assert body["dividend_yield"] is None


def test_get_income_statement(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/fundamentals/AAPL/income").json()
    assert body["symbol"] == "AAPL"
    assert body["periods"] == ["2025-09-30", "2024-09-30"]  # ISO period ends (R15-LEAD-015)
    labels = {line["label"] for line in body["lines"]}
    assert "Total Revenue" in labels
    assert "Net Income" in labels


def test_get_balance_sheet(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/fundamentals/AAPL/balance").json()
    assert body["periods"] == ["2025-09-30", "2024-09-30"]  # ISO period ends (R15-LEAD-015)
    assert len(body["lines"]) == 2


def test_get_cash_flow(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/fundamentals/AAPL/cashflow").json()
    assert len(body["lines"]) == 2


def test_a_second_statement_call_is_served_from_the_cache(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R15-DATA-096: /income (and its siblings) went to the provider on every
    call; a repeat within the TTL is now a cache hit."""
    from models.fundamentals import IncomeStatement, StatementLine
    from services import provider_registry

    calls: list[tuple[str, str]] = []

    async def income(symbol: str, period: str = "annual") -> IncomeStatement:
        calls.append((symbol, period))
        return IncomeStatement(
            symbol="AAPL",
            periods=["2025-09-30"],
            lines=[StatementLine(label="Total Revenue", values={"2025-09-30": 1.0})],
            provider="yfinance",
        )

    monkeypatch.setattr(provider_registry, "get_income_statement", income)
    first = client.get("/fundamentals/AAPL/income").json()
    assert client.get("/fundamentals/AAPL/income").json() == first
    assert calls == [("AAPL", "annual")]
    # The period is part of the key: quarters are their own fetch.
    client.get("/fundamentals/AAPL/income?period=quarterly")
    assert calls == [("AAPL", "annual"), ("AAPL", "quarterly")]


def test_a_second_ratings_call_is_served_from_the_cache(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from models.fundamentals import AnalystRating
    from services import provider_registry

    calls: list[str] = []

    async def rating(symbol: str) -> AnalystRating:
        calls.append(symbol)
        return AnalystRating(symbol="MSFT", provider="yfinance")

    monkeypatch.setattr(provider_registry, "get_analyst_rating", rating)
    client.get("/fundamentals/MSFT/ratings")
    client.get("/fundamentals/MSFT/ratings")
    assert calls == ["MSFT"]


def _dhanbank_ticker() -> type:
    """DHANBANK.NS-shaped frames: four quarters to Q1 FY27 and four fiscal years."""
    import pandas as pd

    def frame(ends: list[str]) -> pd.DataFrame:
        columns = pd.to_datetime(ends)
        return pd.DataFrame(
            {col: [1_000.0 + i, 100.0 + i] for i, col in enumerate(columns)},
            index=["Total Revenue", "Net Income"],
        )

    quarters = frame(["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30"])
    years = frame(["2026-03-31", "2025-03-31", "2024-03-31", "2023-03-31"])

    class _Ticker:
        def __init__(self, symbol: str) -> None:  # noqa: ARG002
            pass

        income_stmt = balance_sheet = cashflow = years
        quarterly_income_stmt = quarterly_balance_sheet = quarterly_cashflow = quarters

    return _Ticker


@pytest.mark.parametrize("route", ["income", "balance", "cashflow"])
def test_statement_routes_serve_quarters_by_iso_period_end(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, route: str
) -> None:
    """R15-DATA-026: ?period=quarterly returns four ISO period-end labels (not
    four quarters collapsed into one year label). R15-LEAD-015 moved the annual
    route from bare fiscal years to the same ISO period ends."""
    from services import yfinance_provider

    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _dhanbank_ticker())
    quarterly = client.get(f"/fundamentals/DHANBANK.NS/{route}?period=quarterly").json()
    assert quarterly["periods"] == ["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30"]
    revenue = next(line for line in quarterly["lines"] if line["label"] == "Total Revenue")
    assert revenue["values"]["2026-06-30"] == 1_000.0
    annual = client.get(f"/fundamentals/DHANBANK.NS/{route}").json()
    assert annual["periods"] == ["2026-03-31", "2025-03-31", "2024-03-31", "2023-03-31"]
    assert quarterly["gaps"] == annual["gaps"] == []


def _gapped_ticker(quarter_ends: list[str], year_ends: list[str]) -> type:
    import pandas as pd

    def frame(ends: list[str]) -> pd.DataFrame:
        return pd.DataFrame(
            {col: [1_000.0 + i] for i, col in enumerate(pd.to_datetime(ends))},
            index=["Total Revenue"],
        )

    class _Ticker:
        def __init__(self, symbol: str) -> None:  # noqa: ARG002
            pass

        income_stmt = balance_sheet = cashflow = frame(year_ends)
        quarterly_income_stmt = quarterly_balance_sheet = quarterly_cashflow = frame(quarter_ends)

    return _Ticker


@pytest.mark.parametrize("route", ["income", "balance", "cashflow"])
def test_a_missing_quarter_is_an_explicit_gap_period(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, route: str
) -> None:
    """R15-LEAD-015: Yahoo's DHANBANK.NS quarterly frame skips 2025-09-30; the
    statement lists it as a gap period with null values, never silently."""
    from services import yfinance_provider

    monkeypatch.setattr(
        yfinance_provider.yf,
        "Ticker",
        _gapped_ticker(
            ["2026-06-30", "2026-03-31", "2025-12-31", "2025-06-30", "2025-03-31"],
            ["2026-03-31", "2025-03-31", "2024-03-31", "2022-03-31"],
        ),
    )
    quarterly = client.get(f"/fundamentals/DHANBANK.NS/{route}?period=quarterly").json()
    assert quarterly["gaps"] == ["2025-09-30"]
    assert quarterly["periods"][3:5] == ["2025-09-30", "2025-06-30"]
    assert quarterly["lines"][0]["values"]["2025-09-30"] is None
    assert quarterly["lines"][0]["values"]["2025-06-30"] == 1_003.0
    # The same rule on an annual frame the fix was not written against.
    annual = client.get(f"/fundamentals/DHANBANK.NS/{route}").json()
    assert annual["gaps"] == ["2023-03-31"]


def test_a_half_yearly_filers_quarters_are_not_gaps(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from services import yfinance_provider

    monkeypatch.setattr(
        yfinance_provider.yf,
        "Ticker",
        _gapped_ticker(["2026-03-31", "2025-09-30", "2025-03-31", "2024-09-30"], ["2026-03-31"]),
    )
    quarterly = client.get("/fundamentals/JONJUA.BO/income?period=quarterly").json()
    assert quarterly["gaps"] == []
    assert len(quarterly["periods"]) == 4


def test_both_statement_providers_label_an_annual_period_alike() -> None:
    """R15-LEAD-015: openbb-mcp labels annual rows by ISO period_ending; yfinance
    now labels the same fiscal year the same way (it used the bare year)."""
    import pandas as pd

    from services import openbb_mcp_provider, yfinance_provider

    frame = pd.DataFrame(
        {pd.Timestamp("2026-03-31"): [5.0], pd.Timestamp("2025-03-31"): [4.0]},
        index=["Total Revenue"],
    )
    rows = [
        {"period_ending": "2026-03-31", "fiscal_year": 2026, "total_revenue": 5.0},
        {"period_ending": "2025-03-31", "fiscal_year": 2025, "total_revenue": 4.0},
    ]
    yahoo_periods, _ = yfinance_provider._statement_lines(frame)
    openbb_periods, _ = openbb_mcp_provider._statement_lines(rows)
    assert yahoo_periods == openbb_periods == ["2026-03-31", "2025-03-31"]


def test_get_analyst_rating(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/fundamentals/AAPL/ratings").json()
    assert body["symbol"] == "AAPL"
    assert body["strong_buy"] == 12
    assert body["buy"] == 20
    assert body["hold"] == 8
    assert body["consensus"] == "buy"
    assert body["target_mean"] == 225.0


def test_get_fundamentals_unknown_symbol_is_honest_404(client, monkeypatch) -> None:
    """R11 gate-7 catch: a garbage symbol used to serve an all-null 200 (a
    dishonest 'instrument exists, no data' shape). yfinance returns an EMPTY
    info dict for unknown symbols — the provider now raises kind="not_found"
    and the route answers an honest 404 with a human message."""
    from services import yfinance_provider

    class _EmptyTicker:
        def __init__(self, symbol: str) -> None:
            self.info = {}

    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _EmptyTicker)
    resp = client.get("/fundamentals/NOTAREALSYMBOL123")
    assert resp.status_code == 404
    assert "check the symbol" in resp.json()["detail"]


def test_get_fundamentals_all_null_shell_degrades_to_404(client, monkeypatch) -> None:  # noqa: ANN001
    """R13 D3 end-to-end: an all-null openbb shell + a failing yfinance must reach
    the router as a 404, never a dishonest all-null 200 payload."""
    from models.fundamentals import Fundamentals
    from services import openbb_mcp_provider, yfinance_provider
    from services.errors import ProviderError

    monkeypatch.setattr(openbb_mcp_provider, "is_available", lambda: True)

    async def openbb_null(symbol: str) -> Fundamentals:
        return Fundamentals(symbol="AAPL", provider="openbb-mcp")  # all data fields None

    def yfinance_boom(symbol: str) -> Fundamentals:
        raise ProviderError("Yahoo has no company record for 'AAPL.NS'", kind="not_found")

    monkeypatch.setattr(openbb_mcp_provider, "get_fundamentals", openbb_null)
    monkeypatch.setattr(yfinance_provider, "get_fundamentals", yfinance_boom)

    resp = client.get("/fundamentals/AAPL")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# R13 — the additive field_meta contract (per-field provenance / coverage)
# ---------------------------------------------------------------------------


def test_field_meta_is_additive_and_absent_by_default() -> None:
    """A Fundamentals built without field_meta carries ``None`` and a legacy
    consumer that never reads the key is unaffected — the wire stays additive."""
    from models.fundamentals import Fundamentals

    fund = Fundamentals(symbol="AAPL", provider="yfinance", pe_ratio=31.2)
    assert fund.field_meta is None
    # An OLD payload (no field_meta key at all) still validates.
    legacy = Fundamentals.model_validate({"symbol": "AAPL", "provider": "yfinance"})
    assert legacy.field_meta is None


def test_field_meta_roundtrips_all_three_statuses() -> None:
    """FieldMeta serialises + revalidates for ok / withheld / unavailable."""
    from models.fundamentals import FieldMeta, Fundamentals

    fund = Fundamentals(
        symbol="KSE.BO",
        provider="yfinance",
        pe_ratio=6.93,
        field_meta={
            "pe_ratio": FieldMeta(
                status="ok", provider="yfinance", as_of="2026-07-10T00:00:00+00:00"
            ),
            "dividend_yield": FieldMeta(status="withheld", reason="ambiguous unit"),
            "beta": FieldMeta(status="unavailable"),
        },
    )
    wire = fund.model_dump(mode="json")
    back = Fundamentals.model_validate(wire)
    assert back.field_meta is not None
    assert back.field_meta["pe_ratio"].status == "ok"
    assert back.field_meta["pe_ratio"].as_of == "2026-07-10T00:00:00+00:00"
    assert back.field_meta["dividend_yield"].status == "withheld"
    assert back.field_meta["dividend_yield"].reason == "ambiguous unit"
    assert back.field_meta["beta"].status == "unavailable"


# ---------------------------------------------------------------------------
# R13 ledger #8 (bounded) — the additive identity_note cross-check
# ---------------------------------------------------------------------------


def test_get_fundamentals_identity_note_flags_a_rename(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CDG-shaped fixture (R13 battery, ledger #8): ``/resolve`` says "CDG
    Petchem Ltd" (the bundled master's canonical name) while ``/fundamentals``
    says "Jujhar Logistics Limited" (the provider's, post-rename) — the
    disagreement now rides an additive ``identity_note``, never a silent swap
    of either name."""
    from models.fundamentals import Fundamentals
    from services import provider_registry, symbol_resolver
    from services.resolution_policy import BAND_EXACT_TICKER
    from services.symbol_resolver import Instrument, Resolution

    async def fake_fundamentals(symbol: str) -> Fundamentals:  # noqa: ARG001
        return Fundamentals(
            symbol="CDG.BO", name="Jujhar Logistics Limited", provider="yfinance", pe_ratio=34.7
        )

    def fake_resolve(query: str, region: str) -> Resolution:  # noqa: ARG001
        instrument = Instrument(
            symbol="CDG",
            name="CDG Petchem Ltd",
            exchange="BSE",
            region="IN",
            asset_class="equity",
            yahoo_symbol="CDG.BO",
            score=1.0,
            band=BAND_EXACT_TICKER,
        )
        return Resolution(query=query, best=instrument, candidates=[instrument])

    monkeypatch.setattr(provider_registry, "get_fundamentals", fake_fundamentals)
    monkeypatch.setattr(symbol_resolver, "resolve", fake_resolve)

    body = client.get("/fundamentals/CDG").json()
    assert body["name"] == "Jujhar Logistics Limited"  # the provider's name is NEVER swapped
    assert body["identity_note"] is not None
    assert "Jujhar Logistics Limited" in body["identity_note"]
    assert "CDG Petchem Ltd" in body["identity_note"]


def test_get_fundamentals_identity_note_absent_when_names_agree(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The resolver and the provider naming the SAME company (mere suffix
    wording aside — "Ltd" vs "Limited") never trips the note."""
    from models.fundamentals import Fundamentals
    from services import provider_registry, symbol_resolver
    from services.resolution_policy import BAND_EXACT_TICKER
    from services.symbol_resolver import Instrument, Resolution

    async def fake_fundamentals(symbol: str) -> Fundamentals:  # noqa: ARG001
        return Fundamentals(
            symbol="TCS.NS", name="Tata Consultancy Services Ltd", provider="yfinance"
        )

    def fake_resolve(query: str, region: str) -> Resolution:  # noqa: ARG001
        instrument = Instrument(
            symbol="TCS",
            name="Tata Consultancy Services Limited",
            exchange="NSE",
            region="IN",
            asset_class="equity",
            yahoo_symbol="TCS.NS",
            score=1.0,
            band=BAND_EXACT_TICKER,
        )
        return Resolution(query=query, best=instrument, candidates=[instrument])

    monkeypatch.setattr(provider_registry, "get_fundamentals", fake_fundamentals)
    monkeypatch.setattr(symbol_resolver, "resolve", fake_resolve)

    body = client.get("/fundamentals/TCS").json()
    assert body["identity_note"] is None


def test_get_fundamentals_identity_note_absent_when_resolver_cannot_bind(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An identity cross-check must never break the endpoint it rides — an
    unresolvable symbol simply leaves the note absent (never a 500)."""
    from models.fundamentals import Fundamentals
    from services import provider_registry, symbol_resolver
    from services.symbol_resolver import Resolution

    async def fake_fundamentals(symbol: str) -> Fundamentals:  # noqa: ARG001
        return Fundamentals(symbol="XXXX", name="Some Provider Name", provider="yfinance")

    def fake_resolve(query: str, region: str) -> Resolution:  # noqa: ARG001
        return Resolution(query=query, best=None, candidates=[])

    monkeypatch.setattr(provider_registry, "get_fundamentals", fake_fundamentals)
    monkeypatch.setattr(symbol_resolver, "resolve", fake_resolve)

    resp = client.get("/fundamentals/XXXX")
    assert resp.status_code == 200
    assert resp.json()["identity_note"] is None


# ---------------------------------------------------------------------------
# R15-DATA-004: Yahoo ownership reconciled against the exchange filing
# ---------------------------------------------------------------------------


def _ownership_route(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    symbol: str,
    exchange: object,
    **held: float,
) -> dict:
    """GET /fundamentals for a stubbed Indian listing with a stubbed exchange
    shareholding pattern (``exchange`` is an ExchangeOwnership or None)."""
    from models.fundamentals import FieldMeta, Fundamentals
    from services import ownership_check, provider_registry, symbol_resolver
    from services.symbol_resolver import Resolution

    async def fake_fundamentals(requested: str) -> Fundamentals:  # noqa: ARG001
        meta = {k: FieldMeta(status="ok", provider="yfinance") for k in held}
        return Fundamentals(
            symbol=symbol,
            name="X Ltd",
            provider="yfinance",
            field_meta=meta,
            **held,  # type: ignore[arg-type]
        )

    async def fake_exchange(listing: str) -> object:
        assert listing == symbol  # the resolved Yahoo listing form (C4)
        return exchange

    def fake_resolve(query: str, region: str) -> Resolution:  # noqa: ARG001
        return Resolution(query=query, best=None, candidates=[])

    monkeypatch.setattr(provider_registry, "get_fundamentals", fake_fundamentals)
    monkeypatch.setattr(ownership_check, "get_exchange_ownership", fake_exchange)
    monkeypatch.setattr(symbol_resolver, "resolve", fake_resolve)
    return client.get(f"/fundamentals/{symbol}").json()


def _filing(promoter: float | None, institutions: float | None, public: float | None) -> object:
    from services.ownership_check import ExchangeOwnership

    return ExchangeOwnership(
        promoter_percent=promoter,
        institutions_percent=institutions,
        public_percent=public,
        as_of_quarter="2026-06-30",
        source="BSE",
    )


@pytest.mark.parametrize(
    ("symbol", "field", "value", "filing", "status"),
    [
        # DHANBANK: a promoter-less bank; the filing carries no promoter group.
        ("DHANBANK.NS", "held_percent_insiders", 0.51176, (None, 14.26, 85.74), "flagged"),
        # JONJUA: 46.6% insiders against a filed 29.67% promoter group.
        ("JONJUA.BO", "held_percent_insiders", 0.46623, (29.67, 0.0, 70.33), "flagged"),
        # SAFE: 73.84% against a filed 73.58% sits inside the 3pp band.
        ("SAFE.BO", "held_percent_insiders", 0.7384, (73.58, 0.1, 26.32), "ok"),
        # NAPEROL institutions leg: 0 against a filed 1.77% (zero vs non-zero).
        ("NAPEROL.BO", "held_percent_institutions", 0.0, (60.0, 1.77, 38.23), "flagged"),
    ],
)
def test_ownership_is_flagged_when_the_exchange_filing_disagrees(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    symbol: str,
    field: str,
    value: float,
    filing: tuple,
    status: str,
) -> None:
    body = _ownership_route(client, monkeypatch, symbol, _filing(*filing), **{field: value})
    assert body[field] == value  # kept, never substituted
    meta = body["field_meta"][field]
    assert meta["status"] == status
    if status == "flagged":
        assert "BSE" in meta["reason"] and "2026-06-30" in meta["reason"]


def test_ownership_is_unreconciled_when_the_exchange_filing_is_unavailable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = _ownership_route(client, monkeypatch, "JONJUA.BO", None, held_percent_insiders=0.46623)
    meta = body["field_meta"]["held_percent_insiders"]
    assert meta["status"] == "flagged"
    assert meta["reason"].startswith("unreconciled: exchange shareholding unavailable")


# ---------------------------------------------------------------------------
# R15-DATA-014: revenue_ttm reconciled against the provider's own statements
# ---------------------------------------------------------------------------

_QUARTERLY = ["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30"]


def _revenue_route(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    symbol: str,
    fields: dict,
    annual_revenue: float | None,
    quarter_ends: list[str],
) -> dict:
    """GET /fundamentals for a stubbed yfinance payload whose own annual income
    statement carries ``annual_revenue`` (``None`` → the statement fetch fails)."""
    from datetime import date

    from models.fundamentals import Fundamentals, IncomeStatement, StatementLine
    from services import provider_registry, symbol_resolver, yfinance_provider
    from services.errors import ProviderError
    from services.symbol_resolver import Resolution

    async def fake_fundamentals(requested: str) -> Fundamentals:  # noqa: ARG001
        return Fundamentals(symbol=symbol, name="X Ltd", provider="yfinance", **fields)

    def fake_income(listing: str) -> IncomeStatement:
        assert listing == symbol  # the same listing the payload was served for
        if annual_revenue is None:
            raise ProviderError("yfinance income statement failed: upstream 500")
        line = StatementLine(label="Total Revenue", values={"2026": annual_revenue})
        return IncomeStatement(symbol=symbol, periods=["2026"], lines=[line], provider="yfinance")

    def fake_quarters(listing: str) -> list[date]:  # noqa: ARG001
        if annual_revenue is None:
            raise ProviderError("yfinance quarterly income statement failed: upstream 500")
        return [date.fromisoformat(d) for d in quarter_ends]

    def fake_resolve(query: str, region: str) -> Resolution:  # noqa: ARG001
        return Resolution(query=query, best=None, candidates=[])

    monkeypatch.setattr(provider_registry, "get_fundamentals", fake_fundamentals)
    monkeypatch.setattr(yfinance_provider, "get_income_statement", fake_income)
    monkeypatch.setattr(yfinance_provider, "get_quarterly_period_ends", fake_quarters)
    monkeypatch.setattr(symbol_resolver, "resolve", fake_resolve)
    return client.get(f"/fundamentals/{symbol}").json()


def test_revenue_diverging_from_the_annual_statement_is_flagged(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FUSION: a 858cr "TTM" against the provider's own 1,513cr fiscal year."""
    fields = {"revenue_ttm": 8_582_000_128, "net_income_ttm": 1_685_100_032}
    fields["profit_margin"] = 0.19635
    body = _revenue_route(client, monkeypatch, "FUSION.NS", fields, 15_131_300_000, _QUARTERLY)
    assert body["revenue_ttm"] == 8_582_000_128  # kept, never substituted
    meta = body["field_meta"]["revenue_ttm"]
    assert meta["status"] == "flagged"
    assert "15,131,300,000" in meta["reason"]


def test_revenue_the_provider_statements_agree_with_is_served_from_the_filings(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DAL: Yahoo's 2.76cr TTM sits beside its own FY 2.07cr annual (within the
    band) and a matching margin, so no Yahoo witness can see it; the BSE-filed
    quarters (9.97cr, screener 9.97cr) are served instead (R15-DATA-014)."""
    from datetime import date

    from services import exchange_financials
    from services.exchange_financials import FiledPeriod, FiledPeriods

    quarters = [
        (date(2026, 4, 1), date(2026, 6, 30), 72_600_000.0),
        (date(2026, 1, 1), date(2026, 3, 31), 100_000.0),
        (date(2025, 10, 1), date(2025, 12, 31), 25_800_000.0),
        (date(2025, 7, 1), date(2025, 9, 30), 1_200_000.0),
    ]
    filed = FiledPeriods(
        "bse", "standalone", tuple(FiledPeriod(s, e, rev, None, None) for s, e, rev in quarters)
    )

    async def filed_periods(listing: str) -> FiledPeriods:
        assert listing == "DAL.BO"
        return filed

    monkeypatch.setattr(exchange_financials, "get_filed_periods", filed_periods)
    fields = {"revenue_ttm": 27_600_000, "net_income_ttm": 10_200_000, "profit_margin": 0.36957}
    body = _revenue_route(client, monkeypatch, "DAL.BO", fields, 20_668_000, _QUARTERLY)
    assert body["revenue_ttm"] == pytest.approx(99_700_000)
    assert body["field_meta"]["revenue_ttm"]["provider"] == "bse"


def test_half_yearly_filer_ttm_is_labelled_annual(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """JONJUA files half-yearly: two period ends in the trailing year, so its
    trailing sizes are labelled "annual, not trailing-4Q"."""
    fields = {"revenue_ttm": 239_033_504, "net_income_ttm": 87_482_000, "profit_margin": 0.36598}
    half_yearly = ["2026-03-31", "2025-09-30", "2025-03-31"]
    body = _revenue_route(client, monkeypatch, "JONJUA.BO", fields, 212_051_000, half_yearly)
    for field_name in ("revenue_ttm", "net_income_ttm"):
        meta = body["field_meta"][field_name]
        assert meta["status"] == "flagged"
        assert "annual, not trailing-4Q" in meta["reason"]


def test_statement_fetch_failure_leaves_revenue_ok(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fields = {"revenue_ttm": 8_582_000_128, "net_income_ttm": 1_685_100_032}
    fields["profit_margin"] = 0.19635
    resp_body = _revenue_route(client, monkeypatch, "FUSION.NS", fields, None, _QUARTERLY)
    assert resp_body["revenue_ttm"] == 8_582_000_128
    assert (resp_body["field_meta"] or {}).get("revenue_ttm") is None


# ---------------------------------------------------------------------------
# R15-DATA-005: BVPS and P/B reconciled against the newest filed equity
# ---------------------------------------------------------------------------


def _book_route(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    symbol: str,
    fields: dict,
    annual: dict[str, float],
    quarterly: dict[str, float] | None = None,
) -> dict:
    """GET /fundamentals for a stubbed yfinance payload whose own balance sheets
    (Yahoo's frames: rows by label, one column per period end) carry the given
    Stockholders Equity."""
    import pandas as pd

    from models.fundamentals import Fundamentals
    from services import provider_registry, symbol_resolver, yfinance_provider
    from services.symbol_resolver import Resolution

    def frame(values: dict[str, float] | None) -> pd.DataFrame:
        if not values:
            return pd.DataFrame()
        columns = pd.to_datetime(list(values))
        return pd.DataFrame([list(values.values())], index=["Stockholders Equity"], columns=columns)

    class _Ticker:
        def __init__(self, listing: str) -> None:  # noqa: ARG002
            self.quarterly_balance_sheet = frame(quarterly)
            self.balance_sheet = frame(annual)

    async def fake_fundamentals(requested: str) -> Fundamentals:  # noqa: ARG001
        return Fundamentals(symbol=symbol, name="X Ltd", provider="yfinance", **fields)

    def fake_resolve(query: str, region: str) -> Resolution:  # noqa: ARG001
        return Resolution(query=query, best=None, candidates=[])

    monkeypatch.setattr(provider_registry, "get_fundamentals", fake_fundamentals)
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _Ticker)
    monkeypatch.setattr(symbol_resolver, "resolve", fake_resolve)
    return client.get(f"/fundamentals/{symbol}").json()


#: JNPR (R15 battery): BVPS 70.02 = equity / the pre-IPO 488,989,292 shares,
#: while shares outstanding (568,998,442) agrees with market cap / price.
_JNPR = {
    "book_value": 70.02,
    "price_to_book": 3.7867754,
    "shares_outstanding": 568_998_442,
    "ratio_price": 265.15,
    "market_cap": 150_869_936_896,
}
#: JUMBO (R15 battery): BVPS 54.361 against its own 477,377,000 / 8,373,700 = 57.01.
_JUMBO = {
    "book_value": 54.361,
    "price_to_book": 2.7593,
    "shares_outstanding": 8_373_700,
    "ratio_price": 150.0,
    "market_cap": 1_256_055_000,
}


@pytest.mark.parametrize(
    ("symbol", "fields", "equity"),
    [("JNPR", _JNPR, 34_238_000_000), ("JUMBO.BO", _JUMBO, 477_377_000)],
)
def test_book_value_on_a_stale_share_count_is_flagged(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    symbol: str,
    fields: dict,
    equity: float,
) -> None:
    body = _book_route(client, monkeypatch, symbol, fields, {"2026-03-31": equity})
    assert body["book_value"] == fields["book_value"]  # kept, never substituted
    assert body["price_to_book"] == fields["price_to_book"]
    for field_name in ("book_value", "price_to_book"):
        meta = body["field_meta"][field_name]
        assert meta["status"] == "flagged"
        assert f"{equity:,.0f} as of 2026-03-31" in meta["reason"]
    # The share count itself agrees with market cap, so it stays unflagged.
    assert (body["field_meta"] or {}).get("shares_outstanding") is None


def test_book_value_within_the_band_is_untouched(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """About 1% off the balance-sheet figure (JUMBO at 56.44 vs 57.01) is rounding."""
    fields = dict(_JUMBO, book_value=56.44, price_to_book=2.6577)
    body = _book_route(client, monkeypatch, "JUMBO.BO", fields, {"2026-03-31": 477_377_000})
    meta = body["field_meta"] or {}
    assert meta.get("book_value") is None and meta.get("price_to_book") is None


def test_book_value_is_witnessed_by_the_newest_quarter_over_an_older_annual(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A case the fix was not written against: the June quarter's equity (500M)
    is newer than the March fiscal year's (477.4M). BVPS 59.71 matches the
    quarter, so nothing is flagged; the annual figure alone would flag it by 4.6%."""
    fields = dict(_JUMBO, book_value=59.71, price_to_book=2.5121)
    body = _book_route(
        client,
        monkeypatch,
        "JUMBO.BO",
        fields,
        annual={"2026-03-31": 477_377_000, "2025-03-31": 431_000_000},
        quarterly={"2026-06-30": 500_000_000, "2026-03-31": 477_377_000},
    )
    meta = body["field_meta"] or {}
    assert meta.get("book_value") is None and meta.get("price_to_book") is None


# ---------------------------------------------------------------------------
# R15-DATA-047/049: the paid-TTM dividend leg runs on /fundamentals too.
# ---------------------------------------------------------------------------


def _dividend_route(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, ttm: object, **fields: float | None
) -> dict:
    from models.fundamentals import FieldMeta, Fundamentals
    from services import dividend_history, provider_registry, symbol_resolver
    from services.symbol_resolver import Resolution

    async def fake_fundamentals(requested: str) -> Fundamentals:  # noqa: ARG001
        meta = {k: FieldMeta(status="ok", provider="yfinance") for k, v in fields.items() if v}
        return Fundamentals(
            symbol="X.NS", name="X Ltd", provider="yfinance", field_meta=meta, **fields
        )

    async def fake_ttm(symbol: str) -> object:
        assert symbol == "X.NS"
        return ttm

    def fake_resolve(query: str, region: str) -> Resolution:  # noqa: ARG001
        return Resolution(query=query, best=None, candidates=[])

    monkeypatch.setattr(provider_registry, "get_fundamentals", fake_fundamentals)
    monkeypatch.setattr(dividend_history, "get_dividend_ttm", fake_ttm)
    monkeypatch.setattr(symbol_resolver, "resolve", fake_resolve)
    return client.get("/fundamentals/X.NS").json()


def test_special_dividend_year_flags_dividend_per_share(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from services.dividend_history import DividendTTM

    body = _dividend_route(
        client,
        monkeypatch,
        DividendTTM(656.0, "paid"),
        dividend_per_share=525.0,
        dividend_yield=0.0193,
        ratio_price=26935.0,
    )
    assert body["dividend_per_share"] == 525.0
    assert body["dividend_per_share_ttm"] == 656.0
    assert body["field_meta"]["dividend_per_share"]["status"] == "flagged"


def test_never_payer_reads_an_affirmed_zero_yield(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from services.dividend_history import AFFIRMED_ZERO_LABEL, DividendTTM

    body = _dividend_route(
        client,
        monkeypatch,
        DividendTTM(0.0, "affirmed_zero", AFFIRMED_ZERO_LABEL),
        ratio_price=49.88,
    )
    assert body["dividend_per_share_ttm"] == 0.0
    assert body["dividend_yield"] == 0.0
    assert body["field_meta"]["dividend_yield"]["label"] == AFFIRMED_ZERO_LABEL


def test_ratings_cache_is_keyed_on_the_resolved_listing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    """R15-LEAD-009: a region switch inside the TTL refetches for the other
    listing instead of serving the first region's cached ratings."""
    from config import DATA_DIR_ENV
    from models.analyst_extended import RatingsHistoryResponse
    from services import analyst_ratings_extended, data_cache, yfinance_provider

    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    data_cache.reset_for_tests()
    listings: list[str] = []

    async def _history(symbol: str) -> RatingsHistoryResponse:
        listings.append(yfinance_provider._yahoo_symbol(symbol))
        return RatingsHistoryResponse(symbol=symbol, history=[])

    monkeypatch.setattr(analyst_ratings_extended, "get_ratings_history", _history)
    try:
        for region in ("IN", "US", "IN"):
            client.get("/fundamentals/INFY/ratings/history", headers={"X-Vysted-Region": region})
    finally:
        data_cache.reset_for_tests()
    assert listings == ["INFY.NS", "INFY"]
