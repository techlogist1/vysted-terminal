"""Tests for ``services.research.target`` — the ONE instrument binding (R8).

The live defects this contract kills: a heavy explorer re-resolving its
focus-augmented task string published the whole sentence as ``brief.symbol``
("Saksoft Limited — focus: Analyze revenue growth…"), and a fuzzy fallback
"success" on contaminated text bound a WRONG instrument (Reliance → CMTL).
"""

from __future__ import annotations

import asyncio
from typing import Any

from services.research.target import (
    CONFIDENCE_FLOOR,
    NO_INSTRUMENT_NOTE,
    ResearchTarget,
    resolve_target,
    resolved_payload,
    target_from_payload,
)


def _run(coro):
    return asyncio.run(coro)


def _payload(symbol: str, *, confidence: float = 0.95, name: str = "Acme Corp") -> dict[str, Any]:
    return {
        "ok": True,
        "resolved": {
            "symbol": symbol,
            "name": name,
            "exchange": "NSE",
            "region": "IN",
            "asset_class": "equity",
            "confidence": confidence,
        },
    }


def test_binds_clean_symbol_with_metadata() -> None:
    target = target_from_payload(_payload("SAKSOFT", name="Saksoft Limited"))
    assert target is not None
    assert target.symbol == "SAKSOFT"
    assert target.name == "Saksoft Limited"
    assert target.exchange == "NSE"
    assert target.region == "IN"
    assert target.confidence == 0.95


def test_symbol_is_uppercased_and_shape_gated() -> None:
    target = target_from_payload(_payload("brk.b"))
    assert target is not None and target.symbol == "BRK.B"
    # The live ULTRA bug shape: a whole focus sentence can NEVER bind.
    sentence = (
        "Saksoft Limited — focus: Analyze revenue growth trajectory, margin "
        "trends, and valuation multiples"
    )
    assert target_from_payload(_payload(sentence)) is None
    # Too long / illegal characters / empty all rejected.
    assert target_from_payload(_payload("A" * 21)) is None
    assert target_from_payload(_payload("RELIANCE INDUSTRIES")) is None  # embedded space
    assert target_from_payload(_payload("")) is None


def test_confidence_floor_rejects_fuzzy_binds() -> None:
    assert target_from_payload(_payload("CMTL", confidence=0.31)) is None
    assert target_from_payload(_payload("CMTL", confidence=CONFIDENCE_FLOOR)) is not None
    # A payload with NO confidence field is an untrusted bind — rejected.
    payload = _payload("CMTL")
    del payload["resolved"]["confidence"]
    assert target_from_payload(payload) is None


def test_failed_or_malformed_resolution_returns_none() -> None:
    assert target_from_payload({"ok": False, "message": "no match"}) is None
    assert target_from_payload({"ok": True, "resolved": None}) is None
    assert target_from_payload({}) is None


def test_resolve_target_calls_resolver_once_and_survives_a_crash() -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    async def tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
        calls.append((name, args))
        return _payload("ROUTE", name="Route Mobile Limited")

    target = _run(resolve_target(tool, "Route Mobile results", region="IN"))
    assert target is not None and target.symbol == "ROUTE"
    assert calls == [("resolve_symbol", {"query": "Route Mobile results", "region": "IN"})]

    async def crash(name: str, args: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("resolver exploded")

    assert _run(resolve_target(crash, "anything")) is None


def test_resolved_payload_round_trips_raw_and_is_honest_for_none() -> None:
    raw = _payload("NVDA", name="NVIDIA Corporation")
    raw["candidates"] = [{"symbol": "NVDA"}]
    target = target_from_payload(raw)
    assert target is not None
    # The full resolver reply (candidates and all) rides structured["resolved"].
    assert resolved_payload(target) is raw
    none_payload = resolved_payload(None)
    assert none_payload["ok"] is False
    assert none_payload["message"] == NO_INSTRUMENT_NOTE


def test_equity_like_classification() -> None:
    equity = target_from_payload(_payload("ROUTE"))
    assert equity is not None and equity.is_equity_like() is True
    crypto_payload = _payload("BTC-USD")
    crypto_payload["resolved"]["asset_class"] = "crypto"
    crypto = target_from_payload(crypto_payload)
    assert crypto is not None and crypto.is_equity_like() is False


def test_target_is_frozen() -> None:
    target = target_from_payload(_payload("NVDA"))
    assert isinstance(target, ResearchTarget)
    try:
        target.symbol = "HACK"  # type: ignore[misc]
    except AttributeError:
        return
    raise AssertionError("ResearchTarget must be immutable")
