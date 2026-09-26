"""Pass B (B1) — region routing + correctness-gated fallthrough in the registry."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from models.market import Quote
from services import provider_registry
from services.errors import ProviderError


def _quote(provider: str, symbol: str) -> Quote:
    return Quote(
        symbol=symbol,
        price=100.0,
        change=0.0,
        change_percent=0.0,
        currency="INR" if provider.startswith("nse") else "USD",
        timestamp=datetime.now(tz=UTC),
        provider=provider,
    )


def _direct_down(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub the exchange-direct lane to fail (no network) so the tests below
    exercise the jugaad-and-down portion of the IN chain unchanged."""
    from services import nse_provider

    def boom(symbol: str) -> Quote:
        raise ProviderError("nse_direct down")

    monkeypatch.setattr(nse_provider, "get_quote", boom)


def test_candidate_region_routing() -> None:
    in_ids = [p.id for p in provider_registry._candidates("quote", "equity", "IN")]
    us_ids = [p.id for p in provider_registry._candidates("quote", "equity", "US")]
    crypto_ids = [p.id for p in provider_registry._candidates("quote", "crypto", "US")]
    # nse_direct (15) → nse/jugaad (20) → bse (25) → yfinance (50): the IN
    # preference order (R7 Component 2). The exchange-direct lane fronts jugaad;
    # bse is the micro-cap layer between them and the gated yfinance fallback.
    assert in_ids == ["nse_direct", "nse", "bse", "yfinance"]
    assert us_ids == ["yfinance"]  # no India provider serves US
    assert "bse" not in us_ids
    assert "nse_direct" not in us_ids
    assert crypto_ids == ["ccxt"]


def test_in_quote_prefers_nse_direct(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import india_provider, nse_provider

    monkeypatch.setattr(nse_provider, "get_quote", lambda s: _quote("nse_direct", s))
    monkeypatch.setattr(
        india_provider, "get_quote", lambda s: pytest.fail("jugaad must not pre-empt nse_direct")
    )
    q = provider_registry.get_quote("GOLDBEES", region="IN")
    assert q.provider == "nse_direct"


def test_effective_region_precedence() -> None:
    assert provider_registry._effective_region("GOLDBEES", None) == "IN"  # master hint
    assert provider_registry._effective_region("AAPL", None) == "US"
    assert provider_registry._effective_region("RELIANCE.NS", None) == "IN"  # suffix
    assert provider_registry._effective_region("AAPL", "IN") == "IN"  # explicit wins


def test_in_quote_prefers_nse(monkeypatch: pytest.MonkeyPatch) -> None:
    # With the direct lane down, jugaad (nse) is the next preference and
    # yfinance is never reached.
    from services import india_provider, yfinance_provider

    _direct_down(monkeypatch)
    monkeypatch.setattr(india_provider, "get_quote", lambda s: _quote("nse", s))
    monkeypatch.setattr(
        yfinance_provider, "get_quote", lambda s: pytest.fail("yfinance must not be reached")
    )
    q = provider_registry.get_quote("GOLDBEES", region="IN")
    assert q.provider == "nse"


def test_in_quote_falls_through_to_yfinance_when_nse_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # RELIANCE is dual-listed (NSE + BSE), so the IN chain is nse → bse →
    # yfinance. Both India providers are stubbed to fail (no network) so the
    # gated last-resort yfinance serves it.
    from services import bse_provider, india_provider, yfinance_provider

    def nse_boom(symbol: str) -> Quote:
        raise ProviderError("nse down")

    def bse_boom(symbol: str) -> Quote:
        raise ProviderError("bse down")

    _direct_down(monkeypatch)
    monkeypatch.setattr(india_provider, "get_quote", nse_boom)
    monkeypatch.setattr(bse_provider, "get_quote", bse_boom)
    monkeypatch.setattr(yfinance_provider, "get_quote", lambda s: _quote("yfinance", s))
    q = provider_registry.get_quote("RELIANCE.NS", region="IN")
    assert q.provider == "yfinance"  # gated last-resort served it


def test_correctness_gate_drives_fallthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import india_provider, nse_provider, yfinance_provider

    # Both NSE lanes return wrong-symbol quotes → the gate rejects each → fall
    # through to yfinance.
    monkeypatch.setattr(nse_provider, "get_quote", lambda s: _quote("nse_direct", "WRONGSYM"))
    monkeypatch.setattr(india_provider, "get_quote", lambda s: _quote("nse", "WRONGSYM"))
    monkeypatch.setattr(yfinance_provider, "get_quote", lambda s: _quote("yfinance", s))
    q = provider_registry.get_quote("GOLDBEES", region="IN")
    assert q.provider == "yfinance"


def test_all_providers_fail_raises_honest_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import india_provider, yfinance_provider

    _direct_down(monkeypatch)
    monkeypatch.setattr(india_provider, "get_quote", lambda s: _quote("nse", "WRONG"))
    monkeypatch.setattr(yfinance_provider, "get_quote", lambda s: _quote("yfinance", "ALSOWRONG"))
    with pytest.raises(ProviderError):
        provider_registry.get_quote("GOLDBEES", region="IN")


def test_us_request_never_routes_to_nse(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import india_provider, nse_provider, yfinance_provider

    monkeypatch.setattr(
        nse_provider,
        "get_quote",
        lambda s: pytest.fail("nse_direct must not serve a US request"),
    )
    monkeypatch.setattr(
        india_provider, "get_quote", lambda s: pytest.fail("nse must not serve a US request")
    )
    monkeypatch.setattr(yfinance_provider, "get_quote", lambda s: _quote("yfinance", s))
    q = provider_registry.get_quote("AAPL")  # default region US via hint
    assert q.provider == "yfinance"


# ---------------------------------------------------------------------------
# WS6 — BSE micro-cap provider region routing.
# ---------------------------------------------------------------------------


def test_bare_bse_only_ticker_resolves_to_in() -> None:
    from services import symbol_resolver

    symbol_resolver.reset_caches_for_tests()
    # ICONIKSPEV is a real BSE-only group-X micro-cap in the regenerated full
    # master (scrip 511260), absent from the NSE/US masters.
    assert symbol_resolver.is_bse_symbol("ICONIKSPEV") is True
    assert symbol_resolver.region_hint("ICONIKSPEV") == "IN"
    # The registry routes it to the IN equity providers (bse included), not US.
    assert provider_registry._effective_region("ICONIKSPEV", None) == "IN"


def test_bo_suffix_resolves_to_in_and_includes_bse() -> None:
    # A `.BO` suffix is decisive for IN and the candidate set includes bse.
    assert provider_registry._effective_region("RELIANCE.BO", None) == "IN"
    in_ids = [p.id for p in provider_registry._candidates("ohlcv", "equity", "IN")]
    assert "bse" in in_ids


def test_bse_serves_micro_cap_when_nse_has_no_listing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A BSE-only micro-cap: neither NSE lane has a listing (both raise), bse
    # serves it, yfinance is never reached.
    from services import bse_provider, india_provider, nse_provider, yfinance_provider

    def nse_no_listing(symbol: str) -> Quote:
        raise ProviderError("nse: not a known NSE instrument")

    monkeypatch.setattr(nse_provider, "get_quote", nse_no_listing)
    monkeypatch.setattr(india_provider, "get_quote", nse_no_listing)
    monkeypatch.setattr(bse_provider, "get_quote", lambda s: _quote("bse", s))
    monkeypatch.setattr(
        yfinance_provider, "get_quote", lambda s: pytest.fail("yfinance must not be reached")
    )
    q = provider_registry.get_quote("ICONIKSPEV", region="IN")
    assert q.provider == "bse"


def test_nse_still_wins_over_bse_for_dual_listed(monkeypatch: pytest.MonkeyPatch) -> None:
    # RELIANCE is listed on both; with the direct lane down, jugaad (rank 20)
    # still outranks bse (rank 25).
    from services import bse_provider, india_provider

    _direct_down(monkeypatch)
    monkeypatch.setattr(india_provider, "get_quote", lambda s: _quote("nse", s))
    monkeypatch.setattr(
        bse_provider, "get_quote", lambda s: pytest.fail("bse must not pre-empt nse")
    )
    q = provider_registry.get_quote("RELIANCE", region="IN")
    assert q.provider == "nse"


def test_statement_for_another_listing_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """R15-DATA-001: a statement provider that answers the bare US ticker (DAL,
    Delta Air Lines) for an IN request whose listing is DAL.BO (Dynamic
    Archistructures) is rejected by the identity gate, and the registry falls
    through to the provider that fetched the requested listing."""
    import asyncio

    import config
    from models.fundamentals import IncomeStatement
    from services import openbb_mcp_provider, yfinance_provider

    async def us_listing(symbol: str, period: str = "annual") -> IncomeStatement:  # noqa: ARG001
        return IncomeStatement(symbol="DAL", periods=[], lines=[], provider="openbb-mcp")

    monkeypatch.setattr(openbb_mcp_provider, "is_available", lambda: True)
    monkeypatch.setattr(openbb_mcp_provider, "get_income_statement", us_listing)
    monkeypatch.setattr(
        yfinance_provider,
        "get_income_statement",
        lambda s, period="annual": IncomeStatement(
            symbol="DAL.BO", periods=[], lines=[], provider="yfinance"
        ),
    )
    token = config.set_request_region("IN")
    try:
        statement = asyncio.run(provider_registry.get_income_statement("DAL"))
    finally:
        config.reset_request_region(token)
    assert statement.provider == "yfinance" and statement.symbol == "DAL.BO"


def test_name_only_fundamentals_shell_is_not_served(monkeypatch: pytest.MonkeyPatch) -> None:
    """R15-DATA-001 (SUMAX): a result carrying only a name is an identity shell,
    not data. With no provider serving real fields it degrades to an error
    rather than a 200 showing a different entity's name over blanks."""
    import asyncio

    from models.fundamentals import Fundamentals
    from services import openbb_mcp_provider, yfinance_provider

    async def name_only(symbol: str) -> Fundamentals:
        return Fundamentals(symbol=symbol, name="Some US Muni Fund", provider="openbb-mcp")

    def yf_down(symbol: str) -> Fundamentals:
        raise ProviderError("yfinance: no data")

    monkeypatch.setattr(openbb_mcp_provider, "is_available", lambda: True)
    monkeypatch.setattr(openbb_mcp_provider, "get_fundamentals", name_only)
    monkeypatch.setattr(yfinance_provider, "get_fundamentals", yf_down)
    with pytest.raises(ProviderError):
        asyncio.run(provider_registry.get_fundamentals("SUMAX.NS"))


def test_in_quote_falls_through_nse_then_bse_then_yfinance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Full IN fallthrough: nse_direct fails → nse fails → bse fails → yfinance
    # (gated last resort).
    from services import bse_provider, india_provider, yfinance_provider

    def boom(symbol: str) -> Quote:
        raise ProviderError("down")

    _direct_down(monkeypatch)
    monkeypatch.setattr(india_provider, "get_quote", boom)
    monkeypatch.setattr(bse_provider, "get_quote", boom)
    monkeypatch.setattr(yfinance_provider, "get_quote", lambda s: _quote("yfinance", s))
    q = provider_registry.get_quote("RELIANCE.BO", region="IN")
    assert q.provider == "yfinance"


# --- R15-DATA-071: a partial series does not end the ohlcv walk --------------


def _series(provider: str, symbol: str, *, partial: bool = False):  # noqa: ANN202
    from datetime import date

    from models.market import OHLCVBar, OHLCVSeries

    bar = OHLCVBar(
        timestamp=datetime.now(tz=UTC), open=10.0, high=11.0, low=9.0, close=10.5, volume=1000
    )
    return OHLCVSeries(
        symbol=symbol,
        timeframe="1d",
        bars=[bar],
        provider=provider,
        partial=partial,
        coverage_start=date(2026, 9, 1) if partial else None,
    )


def _in_history_lanes(monkeypatch: pytest.MonkeyPatch, bse, yfinance) -> None:  # noqa: ANN001
    """Both NSE lanes have no listing; bse and yfinance answer as given."""
    from services import bse_provider, india_provider, nse_provider, yfinance_provider

    def no_listing(symbol: str, timeframe: str, range_: str | None = None):  # noqa: ANN202, ARG001
        raise ProviderError("nse: not a known NSE instrument", kind="not_found")

    monkeypatch.setattr(nse_provider, "get_history", no_listing)
    monkeypatch.setattr(india_provider, "get_history", no_listing)
    monkeypatch.setattr(bse_provider, "get_history", bse)
    monkeypatch.setattr(yfinance_provider, "get_history", yfinance)


def test_partial_bse_range_falls_through_to_complete_lane(monkeypatch: pytest.MonkeyPatch) -> None:
    _in_history_lanes(
        monkeypatch,
        bse=lambda s, tf, r=None: _series("bse", s, partial=True),
        yfinance=lambda s, tf, r=None: _series("yfinance", s),
    )
    series = provider_registry.get_history("ICONIKSPEV", "1d", "1y", region="IN")
    assert series.provider == "yfinance"
    assert series.partial is False


def test_partial_bse_range_is_served_flagged_when_the_next_lane_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def yfinance_down(symbol: str, timeframe: str, range_: str | None = None):  # noqa: ANN202, ARG001
        raise ProviderError("yfinance: rate limited", kind="rate_limited")

    _in_history_lanes(
        monkeypatch,
        bse=lambda s, tf, r=None: _series("bse", s, partial=True),
        yfinance=yfinance_down,
    )
    series = provider_registry.get_history("ICONIKSPEV", "1d", "1y", region="IN")
    assert series.provider == "bse"
    assert series.partial is True
    assert series.coverage_start is not None


def test_two_partial_lanes_serve_the_higher_ranked(monkeypatch: pytest.MonkeyPatch) -> None:
    # The class case (quotes carry no completeness gate and keep first-valid-wins,
    # pinned by the quote fall-through tests above).
    _in_history_lanes(
        monkeypatch,
        bse=lambda s, tf, r=None: _series("bse", s, partial=True),
        yfinance=lambda s, tf, r=None: _series("yfinance", s, partial=True),
    )
    series = provider_registry.get_history("ICONIKSPEV", "1d", "1y", region="IN")
    assert series.provider == "bse"
    assert series.partial is True


def test_bse_scrip_code_request_accepts_the_codes_canonical_ticker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-LEAD-028: the bse lane answers a code-addressed request (506597.BO)
    under the code's canonical ticker (AMAL); the correctness gate used to
    reject that as a symbol mismatch and fall through to yfinance (no data). A
    code whose canonical ticker is not the returned symbol (544774 is SMR) is
    still a mismatch and falls through."""
    from services import bse_provider, india_provider, nse_provider, yfinance_provider

    def nse_no_listing(symbol: str) -> Quote:
        raise ProviderError("nse: not a known NSE instrument", kind="not_found")

    monkeypatch.setattr(nse_provider, "get_quote", nse_no_listing)
    monkeypatch.setattr(india_provider, "get_quote", nse_no_listing)
    monkeypatch.setattr(bse_provider, "get_quote", lambda s: _quote("bse", "AMAL"))
    monkeypatch.setattr(yfinance_provider, "get_quote", lambda s: _quote("yfinance", s))
    assert provider_registry.get_quote("506597.BO", region="IN").provider == "bse"
    assert provider_registry.get_quote("544774.BO", region="IN").provider == "yfinance"

    _in_history_lanes(
        monkeypatch,
        bse=lambda s, tf, r=None: _series("bse", "AMAL"),
        yfinance=lambda s, tf, r=None: pytest.fail("yfinance must not be reached"),
    )
    assert provider_registry.get_history("506597.BO", "1d", "1y", region="IN").provider == "bse"


def test_bo_history_for_a_dual_listed_name_is_never_served_by_an_nse_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-DATA-115 class pin (RELIANCE, a case the fix was not written against):
    with both NSE lanes up, an explicit ``.BO`` history request goes to bse. The
    real NSE gates run; their fetches fail the test if reached."""
    from services import bse_provider, india_provider, nse_provider

    monkeypatch.setattr(nse_provider, "is_available", lambda: True)
    monkeypatch.setattr(india_provider, "is_available", lambda: True)
    monkeypatch.setattr(nse_provider, "_new_session", lambda: pytest.fail("nse_direct fetched"))
    monkeypatch.setattr(india_provider, "_stock_df", lambda *a: pytest.fail("nse fetched"))
    monkeypatch.setattr(bse_provider, "get_history", lambda s, tf, r=None: _series("bse", s))
    series = provider_registry.get_history("RELIANCE.BO", "1d", "1y", region="IN")
    assert series.provider == "bse"


def test_bse_scrip_code_fundamentals_reach_amal_via_yfinance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-LEAD-028: the fundamentals/statements/ratings/earnings routes never
    reach the bse lane (only quote/history do), so a code-addressed fundamentals
    request must resolve through yfinance's own ``_yahoo_symbol`` mapping. With
    no fix, Yahoo is asked for the bare code (``506597.BO``, which does not
    exist) instead of the canonical ticker (``AMAL.BO``)."""
    import asyncio

    from services import yfinance_provider

    class _Ticker:
        def __init__(self, symbol: str) -> None:
            self.symbol = symbol

        @property
        def info(self) -> dict:
            if self.symbol != "AMAL.BO":
                return {}
            return {"longName": "Amal Ltd", "currency": "INR", "marketCap": 500_000_000.0}

    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _Ticker)
    fundamentals = asyncio.run(provider_registry.get_fundamentals("506597.BO", region="IN"))
    assert fundamentals.name == "Amal Ltd"
    assert fundamentals.symbol == "AMAL.BO"
