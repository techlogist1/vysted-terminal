"""Tests for ``services.yfinance_provider`` — focus on symbol normalisation.

yfinance returns 502 / "no data" for dot-tickers (``BRK.B``, ``BF.B``,
``RDS.A``) — its API expects the dash form (``BRK-B``). This module's
``_normalize_symbol`` helper translates dots to dashes at every public entry
point so callers can ask for the natural ``BRK.B`` and get a working response.
"""

from __future__ import annotations

import pytest

from services import yfinance_provider


class _RecordingTicker:
    """Capture the symbol every constructed Ticker was passed.

    The tests below patch ``yfinance_provider.yf.Ticker`` with this recorder, so
    the test can assert what the provider actually sent upstream — independent
    of whatever the call returned.
    """

    instances: list[str] = []

    def __init__(self, symbol: str) -> None:
        type(self).instances.append(symbol)
        self.symbol = symbol

    @property
    def fast_info(self) -> object:
        class _Info:
            last_price = 100.0
            previous_close = 99.0
            last_volume = 1_000.0
            currency = "USD"

        return _Info()

    def history(self, period: str, interval: str) -> object:  # noqa: ARG002
        import pandas as pd

        index = pd.to_datetime(["2026-05-14"])
        return pd.DataFrame(
            {
                "Open": [99.0],
                "High": [101.0],
                "Low": [98.0],
                "Close": [100.0],
                "Volume": [1_000.0],
            },
            index=index,
        )

    @property
    def info(self) -> dict:
        return {
            "longName": "Berkshire Hathaway Inc.",
            "sector": "Financial Services",
            "industry": "Insurance—Diversified",
            "marketCap": 1_000_000_000_000,
            "trailingPE": 12.0,
            "forwardPE": 11.0,
            "trailingPegRatio": 1.5,
            "priceToBook": 1.6,
            "dividendYield": 0.0,
            "trailingEps": 30.0,
            "beta": 0.85,
            "fiftyTwoWeekHigh": 500.0,
            "fiftyTwoWeekLow": 380.0,
            "regularMarketTime": 1_789_847_400,  # the last trade, epoch seconds
        }

    @property
    def income_stmt(self) -> object:
        import pandas as pd

        columns = pd.to_datetime(["2025-12-31"])
        return pd.DataFrame({columns[0]: [100.0]}, index=["Total Revenue"])

    balance_sheet = income_stmt
    cashflow = income_stmt

    @property
    def recommendations(self) -> object:
        import pandas as pd

        return pd.DataFrame([{"strongBuy": 1, "buy": 2, "hold": 3, "sell": 0, "strongSell": 0}])

    @property
    def analyst_price_targets(self) -> dict:
        return {"low": 380.0, "high": 600.0, "mean": 500.0}


@pytest.fixture
def recording_ticker(monkeypatch: pytest.MonkeyPatch) -> type[_RecordingTicker]:
    _RecordingTicker.instances = []
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _RecordingTicker)
    return _RecordingTicker


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("BRK.B", "BRK-B"),
        ("BF.B", "BF-B"),
        ("RDS.A", "RDS-A"),
        ("brk.b", "brk-b"),  # case preservation; yfinance is case-insensitive
        ("AAPL", "AAPL"),  # no-op for symbols without dots
        ("MSFT", "MSFT"),
    ],
)
def test_normalize_symbol(raw: str, expected: str) -> None:
    assert yfinance_provider._normalize_symbol(raw) == expected


def test_get_quote_normalises_dot_ticker(recording_ticker: type[_RecordingTicker]) -> None:
    quote = yfinance_provider.get_quote("BRK.B")
    assert recording_ticker.instances == ["BRK-B"], (
        "yfinance must receive the dash form, not the dot form"
    )
    assert quote.symbol == "BRK-B"
    assert quote.price == 100.0


def test_get_history_normalises_dot_ticker(recording_ticker: type[_RecordingTicker]) -> None:
    series = yfinance_provider.get_history("BRK.B", "1d")
    assert recording_ticker.instances == ["BRK-B"]
    assert series.symbol == "BRK-B"
    assert len(series.bars) == 1


def test_get_fundamentals_normalises_dot_ticker(
    recording_ticker: type[_RecordingTicker],
) -> None:
    fundamentals = yfinance_provider.get_fundamentals("BRK.B")
    assert recording_ticker.instances == ["BRK-B"]
    assert fundamentals.symbol == "BRK-B"


def test_get_income_statement_normalises_dot_ticker(
    recording_ticker: type[_RecordingTicker],
) -> None:
    statement = yfinance_provider.get_income_statement("BRK.B")
    assert recording_ticker.instances == ["BRK-B"]
    assert statement.symbol == "BRK-B"


def test_get_balance_sheet_normalises_dot_ticker(
    recording_ticker: type[_RecordingTicker],
) -> None:
    sheet = yfinance_provider.get_balance_sheet("BRK.B")
    assert recording_ticker.instances == ["BRK-B"]
    assert sheet.symbol == "BRK-B"


def test_get_cash_flow_normalises_dot_ticker(
    recording_ticker: type[_RecordingTicker],
) -> None:
    flow = yfinance_provider.get_cash_flow("BRK.B")
    assert recording_ticker.instances == ["BRK-B"]
    assert flow.symbol == "BRK-B"


def test_get_analyst_rating_normalises_dot_ticker(
    recording_ticker: type[_RecordingTicker],
) -> None:
    rating = yfinance_provider.get_analyst_rating("BRK.B")
    assert recording_ticker.instances == ["BRK-B"]
    assert rating.symbol == "BRK-B"


def test_aapl_unchanged(recording_ticker: type[_RecordingTicker]) -> None:
    """Sanity: dotless symbols are not transformed."""
    yfinance_provider.get_quote("AAPL")
    assert recording_ticker.instances == ["AAPL"]


def test_get_quote_passes_nse_suffix_through(recording_ticker: type[_RecordingTicker]) -> None:
    """An ``.NS`` suffix is already a Yahoo India symbol — get_quote must pass it
    through, NOT mangle it to ``RELIANCE-NS`` (the all-dashes form Yahoo 502s on).
    This is the WS6 fix: quote/history now use the region-aware ``_yahoo_symbol``."""
    quote = yfinance_provider.get_quote("RELIANCE.NS")
    assert recording_ticker.instances == ["RELIANCE.NS"]
    assert quote.symbol == "RELIANCE.NS"


def test_get_quote_passes_bse_suffix_through(recording_ticker: type[_RecordingTicker]) -> None:
    """A ``.BO`` (BSE) suffix — including a numeric scrip code — passes through."""
    quote = yfinance_provider.get_quote("532837.BO")
    assert recording_ticker.instances == ["532837.BO"]
    assert quote.symbol == "532837.BO"


def test_get_history_passes_bse_suffix_through(recording_ticker: type[_RecordingTicker]) -> None:
    """get_history routes through ``_yahoo_symbol`` too, so ``.BO`` is unchanged."""
    series = yfinance_provider.get_history("532837.BO", "1d")
    assert recording_ticker.instances == ["532837.BO"]
    assert series.symbol == "532837.BO"


# --- junk fund-id records for numeric .BO codes (honest 404, R12) -------------


def _info_ticker(info: dict) -> type:
    """A yf.Ticker stand-in whose ``.info`` returns a fixed dict."""

    class _T:
        def __init__(self, symbol: str) -> None:
            self.symbol = symbol

        @property
        def info(self) -> dict:
            return info

    return _T


def test_get_fundamentals_rejects_yahoo_junk_symbol_fragment(monkeypatch) -> None:  # noqa: ANN001
    """A numeric ``.BO`` scrip code makes Yahoo return a garbled fund-ish record
    whose name carries the queried symbol as a comma-fragment
    ("509470.BO,0P0000BN3V,31"). It passes the empty-info gate (info is
    non-empty), so it must be caught by the junk-name signature → honest 404,
    never fabricated PE/mcap served against a nonsense name."""
    from services.errors import ProviderError

    junk = {
        "shortName": "509470.BO,0P0000BN3V,31",
        "marketCap": 31,
        "trailingPE": 12.0,
    }
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _info_ticker(junk))
    with pytest.raises(ProviderError) as excinfo:
        yfinance_provider.get_fundamentals("509470.BO")
    assert excinfo.value.kind == "not_found"


def test_get_fundamentals_rejects_yahoo_fund_id_name(monkeypatch) -> None:  # noqa: ANN001
    """The other junk shape: the name carries an ``0P``-prefixed Morningstar fund
    id even when the queried symbol itself is absent — also a non-company record
    → honest 404."""
    from services.errors import ProviderError

    junk = {"longName": "SOMEFUND,0P0000C9ZK", "marketCap": 31}
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _info_ticker(junk))
    with pytest.raises(ProviderError) as excinfo:
        yfinance_provider.get_fundamentals("503229.BO")
    assert excinfo.value.kind == "not_found"


def test_get_fundamentals_accepts_a_legitimate_bse_name(monkeypatch) -> None:  # noqa: ANN001
    """Conservative: a real company name (even one carrying a comma, ", Ltd.")
    passes the junk gate untouched — the guard never rejects a legitimate name."""
    legit = {
        "longName": "Reliance Industries, Ltd.",
        "currency": "INR",
        "marketCap": 1_800_000_000_000,
        "trailingPE": 24.0,
    }
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _info_ticker(legit))
    fundamentals = yfinance_provider.get_fundamentals("RELIANCE.BO")
    assert fundamentals.name == "Reliance Industries, Ltd."
    assert fundamentals.pe_ratio == 24.0


# --- R13 deliverable 1: BSE-only bare tickers must map to .BO (not .NS) --------


@pytest.mark.parametrize(
    ("bare", "expected"),
    [
        ("KSE", "KSE.BO"),  # BSE-only listing (BSE 519421, never on NSE) → .BO
        ("GOLDBEES", "GOLDBEES.NS"),  # NSE-only → .NS
        ("RELIANCE", "RELIANCE.NS"),  # dual NSE+BSE — the INR NSE listing wins
        ("TCS", "TCS.NS"),  # dual NSE+BSE → .NS
        ("INFY", "INFY.NS"),  # dual + US ADR — an IN session still takes NSE
        ("ZZUNKNOWNXQ", "ZZUNKNOWNXQ.NS"),  # in no master → honest .NS (Yahoo 404s)
    ],
)
def test_yahoo_symbol_routes_bse_only_to_bo(bare: str, expected: str) -> None:
    """A bare IN ticker resolves to the exchange it actually lists on: NSE for an
    NSE/dual name, ``.BO`` for a BSE-ONLY scrip (the KSE root cause — Yahoo serves
    a nameless husk on KSE.NS but the full profile on KSE.BO), and an honest
    ``.NS`` for a name in neither master (Yahoo 404s an unknown symbol)."""
    import config

    token = config.set_request_region("IN")
    try:
        assert yfinance_provider._yahoo_symbol(bare) == expected
    finally:
        config.reset_request_region(token)


def test_get_fundamentals_bse_only_ticker_fetches_bo(
    recording_ticker: type[_RecordingTicker],
) -> None:
    """End-to-end: get_fundamentals('KSE') must construct a Yahoo Ticker for
    ``KSE.BO`` (the BSE listing), not ``KSE.NS`` — every fundamentals call routes
    through the same ``_yahoo_symbol`` mapper the pinning test above covers."""
    import config

    token = config.set_request_region("IN")
    try:
        fundamentals = yfinance_provider.get_fundamentals("KSE")
    finally:
        config.reset_request_region(token)
    assert recording_ticker.instances == ["KSE.BO"]
    assert fundamentals.symbol == "KSE.BO"


# --- R13 deliverable 2: honest husk vs fund-id-blob messages ------------------


def test_get_fundamentals_nameless_husk_says_no_company_record(monkeypatch) -> None:  # noqa: ANN001
    """A NAMELESS husk (Yahoo answers keys but NO company name — the ``KSE.NS``
    43-key shell a bare BSE-only ticker used to hit) reports 'Yahoo has no company
    record', NOT the misleading 'non-company (fund-id) record' the old code gave
    for every empty-named husk."""
    from services.errors import ProviderError

    husk = {"currency": "INR", "exchange": "NSI", "quoteType": "EQUITY"}  # no name
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _info_ticker(husk))
    with pytest.raises(ProviderError) as excinfo:
        yfinance_provider.get_fundamentals("KSE.NS")
    assert excinfo.value.kind == "not_found"
    message = str(excinfo.value)
    assert "no company record" in message
    assert "KSE.NS" in message
    assert "fund-id" not in message


def test_get_fundamentals_fund_id_blob_says_non_company_record(monkeypatch) -> None:  # noqa: ANN001
    """The OTHER junk shape — a garbled comma-blob name carrying the queried
    symbol / an 0P Morningstar id — still reports the 'non-company (fund-id)
    record' message (kept for real fund-id blobs)."""
    from services.errors import ProviderError

    blob = {"shortName": "509470.BO,0P0000BN3V,31", "marketCap": 31, "trailingPE": 12.0}
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _info_ticker(blob))
    with pytest.raises(ProviderError) as excinfo:
        yfinance_provider.get_fundamentals("509470.BO")
    assert excinfo.value.kind == "not_found"
    assert "non-company (fund-id) record" in str(excinfo.value)


# --- R13 deliverable 5: per-field provenance population -----------------------


def test_get_fundamentals_populates_field_meta_provenance(
    recording_ticker: type[_RecordingTicker],
) -> None:
    """Every non-null DATA field yfinance serves carries an 'ok' FieldMeta with
    provider='yfinance' + an as_of (the info fetch time); identity/metadata fields
    (symbol/provider/growth_basis) do NOT get an entry; and — R13 fix — a null DATA
    field carries an explicit 'unavailable' entry so the panel never renders a
    bare, unexplained dash."""
    fundamentals = yfinance_provider.get_fundamentals("BRK.B")
    meta = fundamentals.field_meta
    assert meta is not None
    for field_name in ("pe_ratio", "market_cap", "name", "beta"):
        assert meta[field_name].status == "ok"
        assert meta[field_name].provider == "yfinance"
        assert meta[field_name].as_of  # a non-empty ISO timestamp
    # Identity / metadata fields never get a provenance entry.
    assert "symbol" not in meta
    assert "provider" not in meta
    assert "growth_basis" not in meta
    # A field the source did not carry now carries an explicit 'unavailable' entry
    # with the reason (was: no entry at all — the bare-dash bug).
    assert meta["revenue_ttm"].status == "unavailable"
    assert meta["revenue_ttm"].provider == "yfinance"
    assert meta["revenue_ttm"].reason == "provider did not publish this field"
    assert meta["revenue_ttm"].as_of  # stamped with the same info fetch time
    # A downstream-DERIVED field (computed by the research leg, not this snapshot)
    # is NOT pre-stamped 'unavailable' — the derived leg owns its provenance.
    assert "dividend_per_share_ttm" not in meta
    assert "revenue_growth_computed" not in meta


# --- R15-DATA-008: statement sizes carry their own reporting currency ----------


def _adr_info(**overrides: object) -> dict:
    """SIFY's Yahoo ``info`` shape (collected 2026-09-19): trades in USD, reports in
    INR, so ``totalRevenue``/``netIncomeToCommon`` are INR amounts."""
    info: dict = {
        "longName": "Sify Technologies Limited",
        "currency": "USD",
        "financialCurrency": "INR",
        "marketCap": 989_456_832,
        "currentPrice": 13.66,
        "totalRevenue": 46_506_049_536,
        "netIncomeToCommon": -912_369_984,
        "priceToSalesTrailing12Months": 0.021275874,
        "enterpriseToEbitda": 4.813,
        "priceToBook": 4.959653,
        "bookValue": 2.754225,
        "sharesOutstanding": 72_434_615,
    }
    info.update(overrides)
    return info


def test_adr_statement_sizes_carry_financial_currency_and_mixed_ratios_withheld(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SIFY: revenue is kept (never FX-converted) but labelled INR, while the Yahoo
    ratios dividing a USD figure by an INR statement figure are withheld with a
    reason. P/B stays: Yahoo's book value is per share in the trading currency."""
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _info_ticker(_adr_info()))
    f = yfinance_provider.get_fundamentals("SIFY")
    assert f.currency == "USD"
    assert f.financial_currency == "INR"
    assert f.revenue_ttm == 46_506_049_536
    assert f.price_to_sales is None
    assert f.ev_to_ebitda is None
    assert f.field_meta is not None
    for field_name in ("price_to_sales", "ev_to_ebitda"):
        meta = f.field_meta[field_name]
        assert meta.status == "withheld"
        assert "USD" in meta.reason and "INR" in meta.reason
    assert f.price_to_book == 4.959653
    assert f.field_meta["price_to_book"].status == "ok"


def test_twd_reporting_adr_behaves_the_same(monkeypatch: pytest.MonkeyPatch) -> None:
    """A case the fix was not written against: a TWD-reporting ADR (TSM shape)
    labels its statement sizes TWD and withholds the mixed P/S the same way."""
    info = _adr_info(
        longName="Taiwan Semiconductor Manufacturing Company Limited",
        financialCurrency="TWD",
        marketCap=1_200_000_000_000,
        totalRevenue=3_600_000_000_000,
        priceToSalesTrailing12Months=0.333,
    )
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _info_ticker(info))
    f = yfinance_provider.get_fundamentals("TSM")
    assert f.financial_currency == "TWD"
    assert f.revenue_ttm == 3_600_000_000_000
    assert f.price_to_sales is None
    assert f.field_meta["price_to_sales"].status == "withheld"


def test_same_currency_reporter_has_no_financial_currency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A domestic reporter (financialCurrency == currency) is untouched: no
    financial_currency, P/S served as-is."""
    info = _adr_info(financialCurrency="USD")
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _info_ticker(info))
    f = yfinance_provider.get_fundamentals("SIFY")
    assert f.financial_currency is None
    assert f.price_to_sales == 0.021275874
    assert f.field_meta["price_to_sales"].status == "ok"


# --- R15-DATA-006: price-derived fields are dated by the price's trade time ---


def test_price_derived_as_of_is_the_last_trade_not_the_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DAL last traded on 2025-03-12: its market cap / P/E / P/B rest on that
    print, so their as_of says so instead of the fetch time; a non-price field
    keeps the fetch time. With no trade time Yahoo named, the as_of is unknown."""
    from datetime import UTC, datetime

    last_trade = datetime(2025, 3, 12, 10, 30, tzinfo=UTC)
    info = {
        "longName": "Dynamic Archistructures Ltd",
        "currency": "INR",
        "currentPrice": 49.88,
        "marketCap": 249_900_000,
        "trailingPE": 5.6044946,
        "priceToBook": 0.6,
        "beta": 0.2,
        "regularMarketTime": int(last_trade.timestamp()),
    }
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _info_ticker(info))
    meta = yfinance_provider.get_fundamentals("DAL.BO").field_meta
    for field_name in ("ratio_price", "market_cap", "pe_ratio", "price_to_book"):
        assert meta[field_name].as_of == last_trade.isoformat()
    assert not meta["beta"].as_of.startswith("2025-03-12")

    info.pop("regularMarketTime")
    meta = yfinance_provider.get_fundamentals("DAL.BO").field_meta
    assert meta["market_cap"].as_of is None


# ---------------------------------------------------------------------------
# R15-DATA-016: Yahoo's forward-filled untraded bars are not served
# ---------------------------------------------------------------------------


def _history_ticker(monkeypatch: pytest.MonkeyPatch, frame: object) -> None:
    class _Ticker:
        def __init__(self, symbol: str) -> None:  # noqa: ARG002
            pass

        def history(self, period: str, interval: str) -> object:  # noqa: ARG002
            return frame

    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _Ticker)


def test_history_drops_forward_filled_untraded_bars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Live DAL.BO capture: 1,238 daily bars, 33 of them traded; the rest repeat
    the prior close at zero volume through to today."""
    from pathlib import Path

    import pandas as pd

    fixture = Path(__file__).parent / "fixtures" / "bse" / "dal_bo_yahoo_history_20260923.csv"
    frame = pd.read_csv(fixture, index_col="Date")
    frame.index = pd.to_datetime(frame.index, utc=True)
    _history_ticker(monkeypatch, frame)

    series = yfinance_provider.get_history("DAL.BO", "1d", "5y")
    assert len(series.bars) == 33
    assert all(bar.volume > 0 for bar in series.bars)
    assert series.bars[-1].timestamp.date().isoformat() == "2023-12-06"  # 00:00 IST
    assert series.bars[-1].close == pytest.approx(46.58)


def test_history_keeps_zero_volume_bars_whose_prices_move(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An index carries no volume; its bars are real and all kept."""
    import pandas as pd

    frame = pd.DataFrame(
        {
            "Open": [25000.0, 25100.0, 25050.0],
            "High": [25200.0, 25150.0, 25300.0],
            "Low": [24900.0, 25000.0, 25000.0],
            "Close": [25100.0, 25050.0, 25250.0],
            "Volume": [0, 0, 0],
        },
        index=pd.to_datetime(["2026-09-18", "2026-09-21", "2026-09-22"]),
    )
    _history_ticker(monkeypatch, frame)
    assert len(yfinance_provider.get_history("^NSEI", "1d", "1mo").bars) == 3
