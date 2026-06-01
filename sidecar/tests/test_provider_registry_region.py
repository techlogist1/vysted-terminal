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
    assert in_ids == ["nse", "yfinance"]  # nse preferred, yfinance gated fallback
    assert us_ids == ["yfinance"]  # nse excluded from US
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
    from services import india_provider, yfinance_provider

    def nse_boom(symbol: str) -> Quote:
        raise ProviderError("nse down")

    monkeypatch.setattr(india_provider, "get_quote", nse_boom)
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
