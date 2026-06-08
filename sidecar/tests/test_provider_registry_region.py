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
        currency="INR" if provider == "nse" else "USD",
        timestamp=datetime.now(tz=UTC),
        provider=provider,
    )


def test_candidate_region_routing() -> None:
    in_ids = [p.id for p in provider_registry._candidates("quote", "equity", "IN")]
    us_ids = [p.id for p in provider_registry._candidates("quote", "equity", "US")]
    crypto_ids = [p.id for p in provider_registry._candidates("quote", "crypto", "US")]
    # nse (20) → bse (25) → yfinance (50): the IN preference order. bse is the
    # micro-cap layer between the NSE default and the gated yfinance fallback.
    assert in_ids == ["nse", "bse", "yfinance"]
    assert us_ids == ["yfinance"]  # neither India provider serves US
    assert "bse" not in us_ids
    assert crypto_ids == ["ccxt"]


def test_effective_region_precedence() -> None:
    assert provider_registry._effective_region("GOLDBEES", None) == "IN"  # master hint
    assert provider_registry._effective_region("AAPL", None) == "US"
    assert provider_registry._effective_region("RELIANCE.NS", None) == "IN"  # suffix
    assert provider_registry._effective_region("AAPL", "IN") == "IN"  # explicit wins


def test_in_quote_prefers_nse(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import india_provider, yfinance_provider

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

    monkeypatch.setattr(india_provider, "get_quote", nse_boom)
    monkeypatch.setattr(bse_provider, "get_quote", bse_boom)
    monkeypatch.setattr(yfinance_provider, "get_quote", lambda s: _quote("yfinance", s))
    q = provider_registry.get_quote("RELIANCE.NS", region="IN")
    assert q.provider == "yfinance"  # gated last-resort served it


def test_correctness_gate_drives_fallthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import india_provider, yfinance_provider

    # nse returns a wrong-symbol quote → the gate rejects → fall through to yfinance.
    monkeypatch.setattr(india_provider, "get_quote", lambda s: _quote("nse", "WRONGSYM"))
    monkeypatch.setattr(yfinance_provider, "get_quote", lambda s: _quote("yfinance", s))
    q = provider_registry.get_quote("GOLDBEES", region="IN")
    assert q.provider == "yfinance"


def test_all_providers_fail_raises_honest_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import india_provider, yfinance_provider

    monkeypatch.setattr(india_provider, "get_quote", lambda s: _quote("nse", "WRONG"))
    monkeypatch.setattr(yfinance_provider, "get_quote", lambda s: _quote("yfinance", "ALSOWRONG"))
    with pytest.raises(ProviderError):
        provider_registry.get_quote("GOLDBEES", region="IN")


def test_us_request_never_routes_to_nse(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import india_provider, yfinance_provider

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
    # TIRUPATI is a seeded BSE-only micro-cap (not in the NSE/US masters).
    assert symbol_resolver.is_bse_symbol("TIRUPATI") is True
    assert symbol_resolver.region_hint("TIRUPATI") == "IN"
    # The registry routes it to the IN equity providers (bse included), not US.
    assert provider_registry._effective_region("TIRUPATI", None) == "IN"


def test_bo_suffix_resolves_to_in_and_includes_bse() -> None:
    # A `.BO` suffix is decisive for IN and the candidate set includes bse.
    assert provider_registry._effective_region("RELIANCE.BO", None) == "IN"
    in_ids = [p.id for p in provider_registry._candidates("ohlcv", "equity", "IN")]
    assert "bse" in in_ids


def test_bse_serves_micro_cap_when_nse_has_no_listing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A BSE-only micro-cap: NSE has no listing (raises), bse serves it, yfinance
    # is never reached.
    from services import bse_provider, india_provider, yfinance_provider

    def nse_no_listing(symbol: str) -> Quote:
        raise ProviderError("nse: not a known NSE instrument")

    monkeypatch.setattr(india_provider, "get_quote", nse_no_listing)
    monkeypatch.setattr(bse_provider, "get_quote", lambda s: _quote("bse", s))
    monkeypatch.setattr(
        yfinance_provider, "get_quote", lambda s: pytest.fail("yfinance must not be reached")
    )
    q = provider_registry.get_quote("TIRUPATI", region="IN")
    assert q.provider == "bse"


def test_nse_still_wins_over_bse_for_dual_listed(monkeypatch: pytest.MonkeyPatch) -> None:
    # RELIANCE is listed on both; nse (rank 20) outranks bse (rank 25).
    from services import bse_provider, india_provider

    monkeypatch.setattr(india_provider, "get_quote", lambda s: _quote("nse", s))
    monkeypatch.setattr(
        bse_provider, "get_quote", lambda s: pytest.fail("bse must not pre-empt nse")
    )
    q = provider_registry.get_quote("RELIANCE", region="IN")
    assert q.provider == "nse"


def test_in_quote_falls_through_nse_then_bse_then_yfinance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Full IN fallthrough: nse fails → bse fails → yfinance (gated last resort).
    from services import bse_provider, india_provider, yfinance_provider

    def boom(symbol: str) -> Quote:
        raise ProviderError("down")

    monkeypatch.setattr(india_provider, "get_quote", boom)
    monkeypatch.setattr(bse_provider, "get_quote", boom)
    monkeypatch.setattr(yfinance_provider, "get_quote", lambda s: _quote("yfinance", s))
    q = provider_registry.get_quote("RELIANCE.BO", region="IN")
    assert q.provider == "yfinance"
