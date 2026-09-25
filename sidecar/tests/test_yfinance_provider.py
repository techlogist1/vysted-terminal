"""Tests for ``services.yfinance_provider`` — focus on symbol normalisation.

yfinance returns 502 / "no data" for dot-tickers (``BRK.B``, ``BF.B``,
``RDS.A``) — its API expects the dash form (``BRK-B``). This module's
``_normalize_symbol`` helper translates dots to dashes at every public entry
point so callers can ask for the natural ``BRK.B`` and get a working response.
"""

from __future__ import annotations

import pytest

import config
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

    def get_history_metadata(self) -> dict:
        return {"regularMarketTime": 1_789_847_400}

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
        # BSE-only listing (BSE 542669; KSE, the old example, listed on NSE in
        # 2026-08, so the regenerated master makes it dual-listed) → .BO
        ("BMW", "BMW.BO"),
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
    """End-to-end: get_fundamentals('BMW') (BMW Industries, BSE-only) must
    construct a Yahoo Ticker for ``BMW.BO`` (the BSE listing), not ``BMW.NS`` —
    every fundamentals call routes through the same ``_yahoo_symbol`` mapper the
    pinning test above covers."""
    import config

    token = config.set_request_region("IN")
    try:
        fundamentals = yfinance_provider.get_fundamentals("BMW")
    finally:
        config.reset_request_region(token)
    assert recording_ticker.instances == ["BMW.BO"]
    assert fundamentals.symbol == "BMW.BO"


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


@pytest.mark.parametrize("index", ["^NSEI", "^BSESN"])
def test_yahoo_symbol_passes_caret_index_through_in_an_in_session(index: str) -> None:
    """R15-LEAD-011: Yahoo serves a caret index unsuffixed; ``^NSEI.NS`` is empty."""
    import config

    token = config.set_request_region("IN")
    try:
        assert yfinance_provider._yahoo_symbol(index) == index
    finally:
        config.reset_request_region(token)


# ---------------------------------------------------------------------------
# R15-LEAD-022: a non-Indian Yahoo exchange suffix is dot form, not dash form
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    ["BHP.AX", "0700.HK", "7203.T", "VOD.L", "SHOP.TO"],  # SHOP.TO is the class pin
)
def test_yahoo_symbol_passes_foreign_exchange_suffixes_through(raw: str) -> None:
    """A known non-Indian Yahoo exchange suffix is already Yahoo's own dot form —
    dash-rewriting it (the old universal rule) makes Yahoo report "possibly
    delisted" for every such listing."""
    assert yfinance_provider._yahoo_symbol(raw) == raw


def test_yahoo_symbol_still_dashes_the_us_share_class_quirk() -> None:
    """A genuine US share-class dot (not a recognised exchange suffix) still
    takes the dash rewrite yfinance's API expects."""
    assert yfinance_provider._yahoo_symbol("BRK.B") == "BRK-B"


def test_30m_history_asks_within_yahoos_60_day_intraday_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-DATA-064: a 3mo lookback at 30m is past Yahoo's cap and comes back empty."""
    import pandas as pd
    from yfinance.exceptions import YFPricesMissingError

    asked: list[tuple[str, str]] = []

    class _Ticker:
        def __init__(self, symbol: str) -> None:  # noqa: ARG002
            pass

        def history(self, period: str, interval: str, raise_errors: bool = False) -> object:
            asked.append((period, interval))
            if raise_errors:  # the empty-frame re-ask (R15-DATA-061) asks the same window
                raise YFPricesMissingError("SPY", "")
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _Ticker)
    yfinance_provider.get_history("SPY", "30m")
    assert asked == [("1mo", "30m"), ("1mo", "30m")]


@pytest.mark.parametrize(
    "call",
    [
        lambda: yfinance_provider.get_history("AAPL", "1d"),
        lambda: yfinance_provider.get_income_statement("AAPL"),
    ],
    ids=["history", "income_statement"],
)
def test_a_successful_yahoo_call_closes_the_breaker(
    recording_ticker: type[_RecordingTicker], call
) -> None:  # noqa: ANN001
    """R15-DATA-072: three throttles open the Yahoo breaker; the next healthy
    round-trip on any data path closes it."""
    from services import provider_health

    provider_health.reset_for_tests()
    for _ in range(3):
        provider_health.record_rate_limited(provider_health.YAHOO)
    assert provider_health.is_open(provider_health.YAHOO)
    call()
    assert not provider_health.is_open(provider_health.YAHOO)
    provider_health.reset_for_tests()


# ---------------------------------------------------------------------------
# R15-DATA-061: a missing ticker is not_found, a dead network is network
# ---------------------------------------------------------------------------


def _failing_ticker(monkeypatch: pytest.MonkeyPatch, surfaced: Exception) -> None:
    """A ticker as yfinance behaves when its fetch fails: ``fast_info`` raises
    the library-internal AttributeError, ``history`` returns an empty frame, and
    only a ``raise_errors`` call surfaces the real cause."""
    import pandas as pd

    class _Ticker:
        def __init__(self, symbol: str) -> None:  # noqa: ARG002
            pass

        @property
        def fast_info(self) -> object:
            raise AttributeError("'PriceHistory' object has no attribute '_dividends'")

        def history(self, period: str, interval: str, raise_errors: bool = False) -> object:  # noqa: ARG002
            if raise_errors:
                raise surfaced
            return pd.DataFrame()

    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _Ticker)


def test_quote_of_a_missing_ticker_is_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    from yfinance.exceptions import YFPricesMissingError

    from services.errors import ProviderError

    _failing_ticker(monkeypatch, YFPricesMissingError("$ZZZZNOTREAL", ""))
    with pytest.raises(ProviderError) as info:
        yfinance_provider.get_quote("ZZZZNOTREAL")
    assert info.value.kind == "not_found"


def test_history_on_a_dead_network_is_network_not_an_empty_series(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from curl_cffi.requests.exceptions import ConnectionError as CurlConnectionError

    from services.errors import ProviderError

    _failing_ticker(monkeypatch, CurlConnectionError("curl: (7) Failed to connect"))
    with pytest.raises(ProviderError) as info:
        yfinance_provider.get_history("AAPL", "1d")
    assert info.value.kind == "network"


def test_quote_on_a_dead_network_is_network_not_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The class case: the internal AttributeError a missing ticker raises must
    not read as not_found when the network is what failed."""
    from curl_cffi.requests.exceptions import ConnectionError as CurlConnectionError

    from services.errors import ProviderError

    _failing_ticker(monkeypatch, CurlConnectionError("curl: (7) Could not connect to server"))
    with pytest.raises(ProviderError) as info:
        yfinance_provider.get_quote("AAPL")
    assert info.value.kind == "network"


# ---------------------------------------------------------------------------
# R15-LEAD-005: a quote is dated by its trade time, never the fetch time
# ---------------------------------------------------------------------------


def _closed_market_ticker(monkeypatch: pytest.MonkeyPatch, metadata: dict) -> None:
    import pandas as pd

    class _Ticker(_RecordingTicker):
        def get_history_metadata(self) -> dict:
            return metadata

        def history(self, period: str, interval: str) -> object:  # noqa: ARG002
            index = pd.to_datetime(["2026-09-21 20:00", "2026-09-22 20:00"]).tz_localize(
                "America/New_York"
            )
            return pd.DataFrame(
                {"Open": [1.0, 1.0], "High": [1.0, 1.0], "Low": [1.0, 1.0], "Close": [1.0, 1.0]},
                index=index,
            )

    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _Ticker)


def test_quote_is_dated_by_regular_market_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """A closed market: the last trade was two days before the fetch."""
    from datetime import UTC, datetime

    last_trade = datetime(2026, 9, 22, 20, 0, tzinfo=UTC)
    _closed_market_ticker(monkeypatch, {"regularMarketTime": int(last_trade.timestamp())})
    assert yfinance_provider.get_quote("AAPL").timestamp == last_trade


def test_quote_without_market_time_is_dated_by_its_last_bar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import UTC, datetime

    _closed_market_ticker(monkeypatch, {"currency": "USD"})
    stamp = yfinance_provider.get_quote("AAPL").timestamp
    assert stamp == datetime(2026, 9, 23, 0, 0, tzinfo=UTC)  # 20:00 New York


# ---------------------------------------------------------------------------
# R15-LEAD-023 / D-B9-2: no trade time anywhere is a ProviderError, never now()
# ---------------------------------------------------------------------------


def test_quote_with_no_market_time_and_empty_history_falls_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No ``regularMarketTime`` and an empty 5-day frame (a priced-but-untraded
    quote) must not crash on an empty-index lookup; it raises ``ProviderError``
    so the registry tries the next provider instead of dating the quote now()."""
    import pandas as pd

    from services.errors import ProviderError

    class _Ticker(_RecordingTicker):
        def get_history_metadata(self) -> dict:
            return {}

        def history(  # noqa: ARG002
            self, period: str, interval: str, raise_errors: bool = False
        ) -> object:
            return pd.DataFrame()

    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _Ticker)
    with pytest.raises(ProviderError) as info:
        yfinance_provider.get_quote("AAPL")
    assert info.value.kind is None
    assert "no trade time" in str(info.value)


# ---------------------------------------------------------------------------
# R15-DATA-048 / R15-DATA-052 / R15-DATA-054 / R15-DATA-055: the fundamentals
# profile derives ratios Yahoo omits, resolves India sector via the bundled
# map, and carries basis / listing / 52-week-leg-date / forward-PE metadata.
# ---------------------------------------------------------------------------


def _fund_ticker(info: dict, **frames: object) -> type:
    """A yf.Ticker stand-in with ``.info`` plus the statement/history frames
    ``_derive_fundamentals`` reads. Any frame left out defaults to empty, which
    the derivation leg treats as "no data for this field" (never a crash)."""
    import pandas as pd

    class _T:
        def __init__(self, symbol: str) -> None:
            self.symbol = symbol

        @property
        def info(self) -> dict:
            return info

        @property
        def balance_sheet(self):  # noqa: ANN201
            return frames.get("balance_sheet", pd.DataFrame())

        @property
        def quarterly_balance_sheet(self):  # noqa: ANN201
            return frames.get("quarterly_balance_sheet", pd.DataFrame())

        @property
        def income_stmt(self):  # noqa: ANN201
            return frames.get("income_stmt", pd.DataFrame())

        @property
        def quarterly_income_stmt(self):  # noqa: ANN201
            return frames.get("quarterly_income_stmt", pd.DataFrame())

        def history(self, period: str = "1y", interval: str = "1d"):  # noqa: ANN201, ARG002
            return frames.get("history", pd.DataFrame())

    return _T


def test_get_fundamentals_derives_ratios_from_statements(monkeypatch: pytest.MonkeyPatch) -> None:
    """ELCIDIN (R15-DATA-048): Yahoo's ``info`` carries no ROE/ROCE/D-E/EPS/PE/
    market cap — this NBFC-shell's Yahoo record is bare — so every one is
    derived from the statements the provider already fetches and labelled
    'derived', never silently left null."""
    import pandas as pd

    info = {
        "longName": "Elcid Investments Ltd",
        "currency": "INR",
        "currentPrice": 45.0,
        "sharesOutstanding": 200_000,
        "netIncomeToCommon": 5_000_000.0,
    }
    columns = pd.to_datetime(["2025-03-31"])
    balance_sheet = pd.DataFrame(
        {columns[0]: [40_000_000.0, 10_000_000.0, 25_000_000.0, 0.0]},
        index=["Total Assets", "Current Liabilities", "Stockholders Equity", "Total Debt"],
    )
    income_stmt = pd.DataFrame({columns[0]: [4_500_000.0]}, index=["EBIT"])
    monkeypatch.setattr(
        yfinance_provider.yf,
        "Ticker",
        _fund_ticker(info, balance_sheet=balance_sheet, income_stmt=income_stmt),
    )
    fund = yfinance_provider.get_fundamentals("ELCIDIN.BO")
    meta = fund.field_meta
    assert meta is not None

    assert fund.roce == pytest.approx(4_500_000.0 / (40_000_000.0 - 10_000_000.0))
    assert meta["roce"].provider == "derived"
    assert fund.roe == pytest.approx(5_000_000.0 / 25_000_000.0)
    assert meta["roe"].provider == "derived"
    assert fund.debt_to_equity == 0.0
    assert meta["debt_to_equity"].provider == "derived"
    assert fund.eps == pytest.approx(5_000_000.0 / 200_000)
    assert meta["eps"].provider == "derived"
    assert fund.pe_ratio == pytest.approx(45.0 / fund.eps)
    assert meta["pe_ratio"].provider == "derived"
    assert fund.market_cap == pytest.approx(45.0 * 200_000)
    assert meta["market_cap"].provider == "derived"


def test_get_fundamentals_derived_pe_suppressed_for_negative_eps_sify(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """rc1-datapack:1 (SIFY): Yahoo carries no ``trailingPE`` and a negative
    ``trailingEps`` (-0.13) — the price/EPS fallback must not serve a negative
    ratio as a real value. ``pe_ratio`` stays ``None`` with an explicit reason,
    never ``-103.15`` at ``status: ok``."""
    info = {
        "longName": "Sify Technologies Ltd",
        "currency": "INR",
        "currentPrice": 13.41,
        "trailingEps": -0.13,
    }
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _info_ticker(info))
    fund = yfinance_provider.get_fundamentals("SIFY.NS")
    assert fund.pe_ratio is None
    meta = fund.field_meta["pe_ratio"]
    assert meta.status == "unavailable"
    assert meta.reason == "P/E not meaningful for a loss-making company (negative EPS)"


def test_get_fundamentals_derived_pe_suppressed_for_negative_eps_vertex(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Class pin (a second, independently-shaped case the fix was not written
    against): VERTEX, eps -0.25, gets the same suppression — not a one-off
    guard against the SIFY fixture's exact numbers."""
    info = {
        "longName": "Vertex Ltd",
        "currency": "INR",
        "currentPrice": 3.05,
        "trailingEps": -0.25,
    }
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _info_ticker(info))
    fund = yfinance_provider.get_fundamentals("VERTEX.BO")
    assert fund.pe_ratio is None
    meta = fund.field_meta["pe_ratio"]
    assert meta.status == "unavailable"
    assert meta.reason == "P/E not meaningful for a loss-making company (negative EPS)"


def test_get_fundamentals_roce_unavailable_without_statement_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No EBIT/assets/current-liabilities row anywhere: ROCE has no Yahoo
    equivalent at all, so it is stamped explicitly 'unavailable' (never a bare
    missing key)."""
    monkeypatch.setattr(config, "get_region", lambda: "US")
    info = {"longName": "Sparse Statement Co", "currency": "USD"}
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _info_ticker(info))
    fund = yfinance_provider.get_fundamentals("SPARSE")
    assert fund.roce is None
    assert fund.field_meta["roce"].status == "unavailable"
    assert fund.field_meta["roce"].reason == "insufficient statement data to derive ROCE"


def test_get_fundamentals_derives_roce_for_a_us_name_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Class pin (the fix was not written against this case): the derived-ratio
    leg is not India-specific — a US name gets the same EBIT/(assets - current
    liabilities) derivation, while ``basis`` stays unstamped (a US listing has
    no Yahoo consolidation guarantee)."""
    import pandas as pd

    monkeypatch.setattr(config, "get_region", lambda: "US")
    info = {"longName": "Charter Communications Inc", "currency": "USD"}
    columns = pd.to_datetime(["2025-12-31"])
    balance_sheet = pd.DataFrame(
        {columns[0]: [145_000_000_000.0, 12_000_000_000.0]},
        index=["Total Assets", "Current Liabilities"],
    )
    income_stmt = pd.DataFrame({columns[0]: [9_500_000_000.0]}, index=["EBIT"])
    monkeypatch.setattr(
        yfinance_provider.yf,
        "Ticker",
        _fund_ticker(info, balance_sheet=balance_sheet, income_stmt=income_stmt),
    )
    fund = yfinance_provider.get_fundamentals("CHTR")
    assert fund.roce == pytest.approx(9_500_000_000.0 / (145_000_000_000.0 - 12_000_000_000.0))
    assert fund.field_meta["roce"].provider == "derived"
    assert fund.basis is None


def test_get_fundamentals_roce_uses_annual_ebit_not_the_newest_quarter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-DATA-048 review pin: a quarterly income statement with a NEWER, smaller
    EBIT must not replace the annual EBIT in ROCE (that understates it ~4x)."""
    import pandas as pd

    monkeypatch.setattr(config, "get_region", lambda: "US")
    info = {"longName": "Quarterly Filer Inc", "currency": "USD"}
    annual = pd.to_datetime(["2025-12-31"])
    quarter = pd.to_datetime(["2026-06-30"])
    balance_sheet = pd.DataFrame(
        {annual[0]: [100_000_000.0, 20_000_000.0]},
        index=["Total Assets", "Current Liabilities"],
    )
    income_stmt = pd.DataFrame({annual[0]: [16_000_000.0]}, index=["EBIT"])
    quarterly_income_stmt = pd.DataFrame({quarter[0]: [4_000_000.0]}, index=["EBIT"])
    monkeypatch.setattr(
        yfinance_provider.yf,
        "Ticker",
        _fund_ticker(
            info,
            balance_sheet=balance_sheet,
            income_stmt=income_stmt,
            quarterly_income_stmt=quarterly_income_stmt,
        ),
    )
    fund = yfinance_provider.get_fundamentals("QTRLY")
    assert fund.roce == pytest.approx(16_000_000.0 / (100_000_000.0 - 20_000_000.0))


def test_get_fundamentals_naperol_reads_financial_services_from_the_map(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NAPEROL (R15-DATA-052): Yahoo misclassifies this name as 'Basic
    Materials' — the bundled BSE-sourced India sector map overrides it with the
    correct 'Financial Services', even though Yahoo's own value was non-empty
    (the map wins for an Indian listing whenever it carries a sector, not only
    when Yahoo served a blank one)."""
    info = {
        "longName": "Naprol Chemical Industries Ltd",
        "currency": "INR",
        "sector": "Basic Materials",
        "industry": "Chemicals",
    }
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _info_ticker(info))
    fund = yfinance_provider.get_fundamentals("NAPEROL.BO")
    assert fund.sector == "Financial Services"
    assert fund.industry == "Investment Company"
    assert fund.sector_source == "resolver"


def test_get_fundamentals_empty_yahoo_sector_is_not_served(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bare Yahoo ``sector: ""`` (ok status, empty string) never counts as a
    served value for a non-Indian listing with no map to fall back on —
    ``sector`` stays ``None``, not a fabricated blank string."""
    monkeypatch.setattr(config, "get_region", lambda: "US")
    info = {"longName": "Blank Sector Co", "currency": "USD", "sector": "", "industry": ""}
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _info_ticker(info))
    fund = yfinance_provider.get_fundamentals("BLANK")
    assert fund.sector is None
    assert fund.sector_source is None


def test_get_fundamentals_never_defaults_a_basis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-DATA-054: ``info`` does not say which accounting basis Yahoo used, so
    the provider stamps none for any listing (a hard-coded "consolidated" was
    false for standalone filers like SMR); the route derives it from the
    exchange filings (``test_fundamentals_basis.py``)."""
    info = {"longName": "Crest Ventures Ltd", "currency": "INR", "marketCap": 5_000_000_000}
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _info_ticker(info))
    fund = yfinance_provider.get_fundamentals("CREST.BO")
    assert fund.basis is None

    monkeypatch.setattr(config, "get_region", lambda: "US")
    us_info = {"longName": "Example Corp", "currency": "USD", "marketCap": 1_000_000}
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _info_ticker(us_info))
    us_fund = yfinance_provider.get_fundamentals("EXMPL")
    assert us_fund.basis is None


def test_get_fundamentals_listing_date_and_52week_leg_dates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-DATA-055: ``listing_date`` is the NSE master's DATE OF LISTING and
    Yahoo's ``firstTradeDateMilliseconds`` rides ``first_trade_date``, the
    52-week high/low dates come from the 1y history's argmax/argmin, and
    ``forward_pe_fiscal_year`` is set only when Yahoo names a forward-PE
    horizon."""
    from datetime import UTC, datetime

    import pandas as pd

    listing_ms = int(datetime(2026, 1, 5, tzinfo=UTC).timestamp() * 1000)
    next_fy_end = int(datetime(2027, 3, 31, tzinfo=UTC).timestamp())
    info = {
        "longName": "Freshly Listed Ltd",
        "currency": "INR",
        "fiftyTwoWeekHigh": 120.0,
        "fiftyTwoWeekLow": 80.0,
        "firstTradeDateMilliseconds": listing_ms,
        "forwardPE": 18.0,
        "nextFiscalYearEnd": next_fy_end,
    }
    index = pd.to_datetime(["2026-01-06", "2026-06-15", "2026-09-01"])
    history = pd.DataFrame({"High": [100.0, 120.0, 110.0], "Low": [95.0, 100.0, 80.0]}, index=index)
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _fund_ticker(info, history=history))
    fund = yfinance_provider.get_fundamentals("DHOOTTRANS.NS")
    assert fund.listing_date == "2026-08-17"  # NSE EQUITY_L DATE OF LISTING
    assert fund.first_trade_date == "2026-01-05"
    assert fund.fifty_two_week_high_date == "2026-06-15"
    assert fund.fifty_two_week_low_date == "2026-09-01"
    assert fund.forward_pe_fiscal_year == "2027-03-31"


def test_a_bse_only_listing_has_no_listing_date_only_a_first_trade_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-DATA-055: NAPEROL (BSE-only) — Yahoo's 2002-07-01 is where its data
    starts, not the listing; the NSE master does not list it, so no listing date."""
    from datetime import UTC, datetime

    first_ms = int(datetime(2002, 7, 1, tzinfo=UTC).timestamp() * 1000)
    info = {"longName": "Naperol Investments Ltd", "currency": "INR"}
    info["firstTradeDateMilliseconds"] = first_ms
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _info_ticker(info))
    fund = yfinance_provider.get_fundamentals("NAPEROL.BO")
    assert fund.listing_date is None
    assert fund.first_trade_date == "2002-07-01"


def test_get_fundamentals_no_forward_pe_leaves_fiscal_year_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Case not written against: Yahoo names a ``nextFiscalYearEnd`` but omits
    ``forwardPE`` entirely — the horizon is not stamped (it would describe an
    estimate that does not exist)."""
    from datetime import UTC, datetime

    monkeypatch.setattr(config, "get_region", lambda: "US")
    next_fy_end = int(datetime(2027, 3, 31, tzinfo=UTC).timestamp())
    info = {"longName": "No Estimate Co", "currency": "USD", "nextFiscalYearEnd": next_fy_end}
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _info_ticker(info))
    fund = yfinance_provider.get_fundamentals("NOEST")
    assert fund.forward_pe_fiscal_year is None
