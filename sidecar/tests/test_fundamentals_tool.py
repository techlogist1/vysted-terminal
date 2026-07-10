"""Tests for the ``fundamentals`` agent tool — the R8 retry behaviour + the
R12 symbol-typo cascade fix.

The R8 live failure: one transient provider exception became a brief
claiming P/E "not available" while the equity panel (same provider_registry)
rendered it. The tool retries ONCE (0.5s backoff) before the honest
``ok: False``.

The R12 battery finding: the copilot mistyped a symbol internally
(SIMPLEXREA.BO for SIMPLXREA.BO) calling this tool. The tool faithfully
404'd and the published brief claimed "P/E, P/B, market cap... unavailable"
— a false user-facing claim caused by the model's own typo, because this
tool did no symbol canonicalization before fetching. It now runs a
both-attempts-failed symbol through the ONE resolution policy
(:mod:`services.symbol_resolver` + :mod:`services.resolution_policy`,
the same seam ``resolve_symbol`` uses) before giving up.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from services import provider_registry, resolution_policy, symbol_resolver
from services.agent_tools import fundamentals as fundamentals_tool
from services.errors import ProviderError


class _FakeFundamentals:
    def model_dump(self, **_kw: Any) -> dict[str, Any]:
        return {"symbol": "AAPL", "pe_ratio": 31.2}


def _patch_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fundamentals_tool, "_RETRY_BACKOFF_SECS", 0.0)


def test_transient_failure_retries_once_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_backoff(monkeypatch)
    attempts = {"n": 0}

    async def flaky(symbol: str):  # noqa: ANN202
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise ProviderError("transient upstream hiccup")
        return _FakeFundamentals()

    monkeypatch.setattr(provider_registry, "get_fundamentals", flaky)
    out = asyncio.run(fundamentals_tool._fundamentals({"symbol": "AAPL"}))
    assert out["ok"] is True
    assert out["fundamentals"]["pe_ratio"] == 31.2
    assert attempts["n"] == 2


def test_double_failure_is_honest_after_exactly_two_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_backoff(monkeypatch)
    attempts = {"n": 0}

    async def dead(symbol: str):  # noqa: ANN202
        attempts["n"] += 1
        raise ProviderError("provider down")

    monkeypatch.setattr(provider_registry, "get_fundamentals", dead)
    out = asyncio.run(fundamentals_tool._fundamentals({"symbol": "AAPL"}))
    assert out["ok"] is False
    assert "provider down" in out["error"]
    assert attempts["n"] == 2  # one retry, never an unbounded loop


def test_provider_failure_carries_provider_error_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R13 JARVIS 2a: an app-side provider failure carries reason=provider_error
    so the model narrates OUR feed's gap, never 'the world doesn't publish it'."""
    _patch_backoff(monkeypatch)

    async def dead(symbol: str):  # noqa: ANN202
        raise ProviderError("provider down")

    monkeypatch.setattr(provider_registry, "get_fundamentals", dead)
    out = asyncio.run(fundamentals_tool._fundamentals({"symbol": "AAPL"}))
    assert out["ok"] is False
    assert out["reason"] == "provider_error"


def test_rate_limited_failure_is_classified(monkeypatch: pytest.MonkeyPatch) -> None:
    """R13 JARVIS 2a: a throttled fetch classifies as rate_limited (retry helps),
    distinct from a genuine provider_error."""
    _patch_backoff(monkeypatch)

    async def throttled(symbol: str):  # noqa: ANN202
        raise ProviderError("429 too many requests")

    monkeypatch.setattr(provider_registry, "get_fundamentals", throttled)
    out = asyncio.run(fundamentals_tool._fundamentals({"symbol": "AAPL"}))
    assert out["ok"] is False
    assert out["reason"] == "rate_limited"


def test_unexpected_exception_also_gets_the_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_backoff(monkeypatch)
    attempts = {"n": 0}

    async def crashy(symbol: str):  # noqa: ANN202
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("socket reset")
        return _FakeFundamentals()

    monkeypatch.setattr(provider_registry, "get_fundamentals", crashy)
    out = asyncio.run(fundamentals_tool._fundamentals({"symbol": "AAPL"}))
    assert out["ok"] is True
    assert attempts["n"] == 2


def test_first_try_success_does_not_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_backoff(monkeypatch)
    attempts = {"n": 0}

    async def fine(symbol: str):  # noqa: ANN202
        attempts["n"] += 1
        return _FakeFundamentals()

    monkeypatch.setattr(provider_registry, "get_fundamentals", fine)
    out = asyncio.run(fundamentals_tool._fundamentals({"symbol": "AAPL"}))
    assert out["ok"] is True
    assert attempts["n"] == 1


def test_missing_symbol_is_rejected_without_a_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def explode(symbol: str):  # noqa: ANN202
        raise AssertionError("provider must not be called")

    monkeypatch.setattr(provider_registry, "get_fundamentals", explode)
    out = asyncio.run(fundamentals_tool._fundamentals({}))
    assert out["ok"] is False


def test_tool_result_carries_growth_basis(monkeypatch: pytest.MonkeyPatch) -> None:
    """D55: the agent tool returns the raw Fundamentals dump, which now carries
    ``growth_basis`` — so a copilot consuming growth via the tool sees the MRQ
    truth, not a bare 'yoy'."""
    from models.fundamentals import Fundamentals

    async def real(symbol: str):  # noqa: ANN202
        return Fundamentals(
            symbol="AAPL", provider="yfinance", revenue_growth=0.18, earnings_growth=-0.05
        )

    monkeypatch.setattr(provider_registry, "get_fundamentals", real)
    out = asyncio.run(fundamentals_tool._fundamentals({"symbol": "AAPL"}))
    assert out["ok"] is True
    assert out["fundamentals"]["growth_basis"] == "mrq_yoy"


# --- R12: symbol-typo cascade — canonicalize before giving up -----------------


def test_exact_symbol_first_try_success_never_touches_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The unchanged fast path: a symbol that succeeds on the first provider
    call never reaches the resolution policy at all — not just a no-op call,
    the resolver is never even consulted."""
    _patch_backoff(monkeypatch)

    def explode_resolve(query: str, region: str):  # noqa: ANN202
        raise AssertionError("resolver must not be consulted on a first-try success")

    monkeypatch.setattr(symbol_resolver, "resolve", explode_resolve)

    async def fine(symbol: str):  # noqa: ANN202
        return _FakeFundamentals()

    monkeypatch.setattr(provider_registry, "get_fundamentals", fine)
    out = asyncio.run(fundamentals_tool._fundamentals({"symbol": "AAPL"}))
    assert out["ok"] is True
    assert "note" not in out


def test_typo_confidently_bound_gets_corrective_refetch_and_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R12 battery finding: the copilot mistyped SIMPLEXREA.BO for
    SIMPLXREA.BO calling this tool; the tool faithfully 404'd and the
    published brief claimed fundamentals "unavailable" — a false claim
    caused by the model's own typo. When the resolution policy confidently
    BINDS a different canonical symbol (the same ``decide()`` verdict
    ``resolve_symbol`` rides — never a reimplemented match), the tool
    re-fetches under that symbol and surfaces the correction via a ``note``,
    never silently."""
    _patch_backoff(monkeypatch)

    canonical = symbol_resolver.Instrument(
        symbol="SIMPLXREA",
        name="Simplex Realty Ltd",
        exchange="BSE",
        region="IN",
        asset_class="equity",
        yahoo_symbol="SIMPLXREA.BO",
        score=1.0,
        band=resolution_policy.BAND_EXACT_TICKER,
    )

    def fake_resolve(query: str, region: str):  # noqa: ANN202
        return symbol_resolver.Resolution(query=query, best=canonical, candidates=[canonical])

    monkeypatch.setattr(symbol_resolver, "resolve", fake_resolve)

    calls: list[str] = []

    async def flaky_typo(symbol: str):  # noqa: ANN202
        calls.append(symbol)
        if symbol == "SIMPLEXREA.BO":
            raise ProviderError("404 not found")
        return _FakeFundamentals()

    monkeypatch.setattr(provider_registry, "get_fundamentals", flaky_typo)
    out = asyncio.run(fundamentals_tool._fundamentals({"symbol": "SIMPLEXREA.BO"}))
    assert out["ok"] is True
    assert out["note"] == "resolved 'SIMPLEXREA.BO' → 'SIMPLXREA.BO'"
    # both attempts ride the typo (the R8 retry), then ONE corrective fetch
    # on the canonical symbol — never an unbounded loop.
    assert calls == ["SIMPLEXREA.BO", "SIMPLEXREA.BO", "SIMPLXREA.BO"]


def test_typo_that_scores_fuzzy_gets_disambiguation_candidates_not_bare_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The exact R12 battery scenario against the REAL bundled BSE master:
    SIMPLEXREA.BO (typo) vs the real SIMPLXREA.BO scores in the FUZZY band
    (~0.65) — below ACCEPT, so the D46 substring/fuzzy-never-binds hardening
    forbids an auto-bind (see ``test_decide_substring_band_never_binds``).
    The tool must not echo a bare provider 404; it surfaces the
    disambiguation candidate instead."""
    _patch_backoff(monkeypatch)
    symbol_resolver.reset_caches_for_tests()
    monkeypatch.setattr(symbol_resolver, "_live_lookup", lambda query, region: [])

    async def dead(symbol: str):  # noqa: ANN202
        raise ProviderError("404 not found")

    monkeypatch.setattr(provider_registry, "get_fundamentals", dead)
    out = asyncio.run(fundamentals_tool._fundamentals({"symbol": "SIMPLEXREA.BO"}))
    assert out["ok"] is False
    assert "did you mean" in out["error"]
    assert any(c["symbol"] == "SIMPLXREA.BO" for c in out["candidates"])


def test_garbage_symbol_gets_honest_not_found_no_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A symbol the resolution policy has NO opinion on (``unresolved``,
    zero candidates) keeps failing honestly — the original provider error
    stands, never a fabricated match, never a crash. The resolver's silence
    is not manufactured into disambiguation candidates that don't exist."""
    _patch_backoff(monkeypatch)
    symbol_resolver.reset_caches_for_tests()
    monkeypatch.setattr(symbol_resolver, "_live_lookup", lambda query, region: [])

    async def dead(symbol: str):  # noqa: ANN202
        raise ProviderError("404 not found")

    monkeypatch.setattr(provider_registry, "get_fundamentals", dead)
    out = asyncio.run(fundamentals_tool._fundamentals({"symbol": "ZZZQQQNOTREAL123"}))
    assert out["ok"] is False
    assert "candidates" not in out
    assert "provider error" in out["error"]
