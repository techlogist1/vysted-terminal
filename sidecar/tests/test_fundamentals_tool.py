"""Tests for the ``fundamentals`` agent tool — the R8 retry behaviour.

The live failure: one transient provider exception became a brief claiming
P/E "not available" while the equity panel (same provider_registry) rendered
it. The tool now retries ONCE (0.5s backoff) before the honest ``ok: False``.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from services import provider_registry
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
