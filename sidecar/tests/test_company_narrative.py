"""Tests for the company-overview AI narrative + numeric-verification pass.

The LLM is ALWAYS mocked — no test makes a live model call. The focus is the
numeric verifier, which is the load-bearing safety property: an injected
hallucinated number must be stripped/flagged; a correct number must pass
through untouched; the no-key path must degrade to a graceful null.
"""

from __future__ import annotations

import pytest

from models.fundamentals import Fundamentals
from models.market import Quote
from services import company_narrative
from services.company_narrative import (
    _close,
    _normalise_token,
    _source_values,
    _verify_text,
)

# --------------------------------------------------------------------------
# Source fixtures — a realistic, fully-populated company (Apple-shaped).
# --------------------------------------------------------------------------


def _apple_fundamentals() -> Fundamentals:
    return Fundamentals(
        symbol="AAPL",
        name="Apple Inc.",
        sector="Technology",
        industry="Consumer Electronics",
        currency="USD",
        market_cap=2_948_300_000_000.0,  # ~2.95T
        pe_ratio=31.5,
        forward_pe=28.2,
        peg_ratio=2.1,
        price_to_book=46.0,
        price_to_sales=8.3,
        ev_to_ebitda=23.4,
        book_value=4.18,
        dividend_yield=0.0044,  # 0.44%
        dividend_per_share=0.96,
        eps=6.13,
        beta=1.25,
        fifty_two_week_high=237.49,
        fifty_two_week_low=164.08,
        fifty_two_week_change=0.18,  # 18%
        roe=1.47,  # 147%
        roa=0.28,
        gross_margin=0.46,
        operating_margin=0.31,
        profit_margin=0.25,
        debt_to_equity=1.51,
        current_ratio=0.87,
        quick_ratio=0.83,
        revenue_ttm=391_000_000_000.0,  # 391B
        net_income_ttm=97_000_000_000.0,
        free_cash_flow=108_000_000_000.0,
        shares_outstanding=15_200_000_000.0,
        revenue_growth=0.02,
        earnings_growth=0.11,
        held_percent_insiders=0.0007,
        held_percent_institutions=0.61,
        provider="yfinance",
    )


def _apple_quote() -> Quote:
    return Quote(
        symbol="AAPL",
        price=192.50,
        change=2.30,
        change_percent=1.21,
        volume=51_000_000,
        currency="USD",
        market_state="REGULAR",
        timestamp="2026-06-05T20:00:00+00:00",
        provider="yfinance",
    )


# --------------------------------------------------------------------------
# Unit: tolerance + token normalisation primitives.
# --------------------------------------------------------------------------


def test_close_relative_band_accepts_rounded_large_figure() -> None:
    # "$2.95T" rounded against 2.9483T — within 2% relative.
    assert _close(2.95, 2.9483)


def test_close_rejects_far_ratio() -> None:
    # A P/E of 37 must NOT match a source 31.5 (outside both bands).
    assert not _close(37.0, 31.5)


def test_close_absolute_band_accepts_small_ratio_rounding() -> None:
    # P/E 31.5 stated as "31.5" — exact; and "31.50" rounding tolerated.
    assert _close(31.5, 31.5)
    assert _close(1.51, 1.5)  # debt/equity rounding


def test_normalise_token_suffix_and_money() -> None:
    import re

    from services.company_narrative import _NUMBER_RE

    def norm(s: str) -> float | None:
        m = _NUMBER_RE.search(s)
        assert m is not None
        return _normalise_token(m)

    assert norm("$2.95T") == pytest.approx(2.95e12)
    assert norm("391B") == pytest.approx(391e9)
    assert norm("21.3%") == pytest.approx(21.3)
    assert norm("1,234,567") == pytest.approx(1_234_567)
    assert norm("37x") == pytest.approx(37.0)
    assert norm("-4.2") == pytest.approx(-4.2)
    # ensure the regex object is what the module exports (guards a rename)
    assert isinstance(_NUMBER_RE, re.Pattern)


def test_source_values_includes_scaled_and_percent_forms() -> None:
    values = _source_values(_apple_fundamentals(), _apple_quote())
    # market cap scaled mantissa is reachable for the "$2.95T" form
    assert any(_close(v, 2.9483) for v in values)
    # a fraction field (dividend yield 0.0044) reachable as 0.44%
    assert any(_close(v, 0.44) for v in values)
    # P/E reachable
    assert any(_close(v, 31.5) for v in values)


# --------------------------------------------------------------------------
# Unit: the verification pass — the core safety property.
# --------------------------------------------------------------------------


def test_verify_passes_correct_numbers_untouched() -> None:
    source = _source_values(_apple_fundamentals(), _apple_quote())
    text = "Apple trades at a P/E of 31.5 with a market cap near $2.95T."
    cleaned, unverified = _verify_text(text, source)
    assert unverified == []
    assert "31.5" in cleaned
    assert "2.95T" in cleaned
    assert "[unverified]" not in cleaned


def test_verify_strips_hallucinated_number() -> None:
    source = _source_values(_apple_fundamentals(), _apple_quote())
    # 64.2% gross margin is INVENTED (source is 46%); P/E 31.5 is real.
    text = "With a P/E of 31.5 and a gross margin of 64.2%, the firm looks rich."
    cleaned, unverified = _verify_text(text, source)
    assert len(unverified) == 1
    assert unverified[0].text == "64.2%"
    assert "64.2%" not in cleaned
    assert "[unverified]" in cleaned
    # the legitimate number survived
    assert "31.5" in cleaned


def test_verify_strips_fabricated_market_cap() -> None:
    source = _source_values(_apple_fundamentals(), _apple_quote())
    text = "Apple is a $4.2T behemoth."  # real cap is ~2.95T
    cleaned, unverified = _verify_text(text, source)
    assert any(c.text == "$4.2T" for c in unverified)
    assert "4.2T" not in cleaned


def test_verify_leaves_years_alone() -> None:
    source = _source_values(_apple_fundamentals(), _apple_quote())
    text = "Since 2020 the company has compounded steadily."
    cleaned, unverified = _verify_text(text, source)
    assert unverified == []
    assert "2020" in cleaned


# --------------------------------------------------------------------------
# Integration: generate_narrative with a MOCKED LLM.
# --------------------------------------------------------------------------


@pytest.fixture
def _patch_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch the data layer so the service grounds against deterministic data."""

    async def _fake_fundamentals(symbol: str) -> Fundamentals:
        return _apple_fundamentals()

    def _fake_quote(symbol: str, region: str | None = None) -> Quote:
        return _apple_quote()

    monkeypatch.setattr(company_narrative.provider_registry, "get_fundamentals", _fake_fundamentals)
    monkeypatch.setattr(company_narrative.provider_registry, "get_quote", _fake_quote)


def _patch_llm(monkeypatch: pytest.MonkeyPatch, output: str) -> None:
    async def _fake_complete(*args: object, **kwargs: object) -> str:
        return output

    monkeypatch.setattr(company_narrative, "complete", _fake_complete)


@pytest.mark.asyncio
async def test_generate_redacts_hallucinated_figure(
    monkeypatch: pytest.MonkeyPatch, _patch_data: None
) -> None:
    # The model invents a 64.2% gross margin and a $4.2T market cap; P/E 31.5 is real.
    _patch_llm(
        monkeypatch,
        "SUMMARY: Apple trades at a P/E of 31.5 and is a $4.2T company "
        "with a gross margin of 64.2%.\n"
        "INSIGHTS:\n"
        "- Strong P/E of 31.5\n"
        "- Margins around 64.2%",
    )
    result = await company_narrative.generate_narrative(
        "AAPL", provider="anthropic", model="claude-opus-4-7", api_key="sk-test"
    )
    # The hallucinated figures are flagged and redacted; the real one survives.
    flagged = {c.text for c in result.unverified_claims}
    assert "$4.2T" in flagged
    assert "64.2%" in flagged
    assert result.verified is False
    assert result.summary is not None
    assert "4.2T" not in result.summary
    assert "64.2%" not in result.summary
    assert "31.5" in result.summary
    # insights also vetted
    joined = " ".join(result.insights)
    assert "64.2%" not in joined
    assert "31.5" in joined
    assert result.source_provider == "yfinance"
    assert result.generated_at is not None


@pytest.mark.asyncio
async def test_generate_passes_all_correct_numbers(
    monkeypatch: pytest.MonkeyPatch, _patch_data: None
) -> None:
    _patch_llm(
        monkeypatch,
        "SUMMARY: Apple Inc. trades at a P/E of 31.5 with a market cap of $2.95T "
        "and last printed at 192.50.\n"
        "INSIGHTS:\n"
        "- EPS of 6.13\n"
        "- Beta of 1.25",
    )
    result = await company_narrative.generate_narrative(
        "AAPL", provider="anthropic", model="claude-opus-4-7", api_key="sk-test"
    )
    assert result.unverified_claims == []
    assert result.verified is True
    assert result.summary is not None
    assert "31.5" in result.summary
    assert "2.95T" in result.summary
    assert "[unverified]" not in result.summary
    assert len(result.insights) == 2


@pytest.mark.asyncio
async def test_generate_no_key_returns_graceful_null(
    monkeypatch: pytest.MonkeyPatch, _patch_data: None
) -> None:
    # No api_key for a key-requiring provider → graceful null, never an error,
    # and the model is NEVER called.
    called = {"complete": False}

    async def _should_not_run(*args: object, **kwargs: object) -> str:
        called["complete"] = True
        return "should not happen"

    monkeypatch.setattr(company_narrative, "complete", _should_not_run)

    result = await company_narrative.generate_narrative(
        "AAPL", provider="anthropic", model="claude-opus-4-7", api_key=None
    )
    assert result.summary is None
    assert result.insights == []
    assert result.verified is False
    assert result.reason is not None
    assert "key" in result.reason.lower()
    # Data still resolved, so we can name the grounding source.
    assert result.source_provider == "yfinance"
    assert called["complete"] is False


@pytest.mark.asyncio
async def test_generate_empty_model_output_returns_reason(
    monkeypatch: pytest.MonkeyPatch, _patch_data: None
) -> None:
    _patch_llm(monkeypatch, "   ")
    result = await company_narrative.generate_narrative(
        "AAPL", provider="anthropic", model="claude-opus-4-7", api_key="sk-test"
    )
    assert result.summary is None
    assert result.reason is not None


@pytest.mark.asyncio
async def test_generate_no_data_returns_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _no_fundamentals(symbol: str) -> Fundamentals:
        raise RuntimeError("provider down")

    def _no_quote(symbol: str, region: str | None = None) -> Quote:
        raise RuntimeError("provider down")

    monkeypatch.setattr(company_narrative.provider_registry, "get_fundamentals", _no_fundamentals)
    monkeypatch.setattr(company_narrative.provider_registry, "get_quote", _no_quote)

    result = await company_narrative.generate_narrative(
        "ZZZZ", provider="anthropic", model="claude-opus-4-7", api_key="sk-test"
    )
    assert result.summary is None
    assert result.reason is not None
    assert result.source_provider is None


# --------------------------------------------------------------------------
# Route: the endpoint always answers 200 (graceful degradation).
# --------------------------------------------------------------------------


def test_narrative_route_no_headers_is_graceful(client: object, mock_yfinance: object) -> None:
    # No BYOK headers → 200 with summary null + a reason (mock_yfinance provides
    # the grounding data so source_provider is named).
    response = client.get("/fundamentals/AAPL/narrative")  # type: ignore[attr-defined]
    assert response.status_code == 200
    body = response.json()
    assert body["summary"] is None
    assert body["reason"] is not None
    assert body["verified"] is False
