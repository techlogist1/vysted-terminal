"""Tests for ``services.research.target`` — the ONE instrument binding (R8/R10).

The live defects this contract kills: a heavy explorer re-resolving its
focus-augmented task string published the whole sentence as ``brief.symbol``
("Saksoft Limited — focus: Analyze revenue growth…"), a fuzzy fallback
"success" on contaminated text bound a WRONG instrument (Reliance → CMTL), and
— R10 (E1) — the binding accepted at 0.5 what the agent path disambiguated at
0.72. The verdict now arrives on the wire (``status``, from the ONE policy in
``services.resolution_policy``); this layer never re-judges it with a second
threshold.
"""

from __future__ import annotations

import asyncio
from typing import Any

from services.research.target import (
    NO_INSTRUMENT_NOTE,
    ResearchDisambiguation,
    ResearchTarget,
    resolve_target,
    resolved_payload,
    target_from_payload,
)
from services.resolution_policy import ACCEPT


def _run(coro):
    return asyncio.run(coro)


def _payload(
    symbol: str,
    *,
    confidence: float = 0.95,
    name: str = "Acme Corp",
    status: str | None = "bound",
) -> dict[str, Any]:
    out: dict[str, Any] = {
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
    if status is not None:
        out["status"] = status
    return out


def _disambiguation_payload(query: str, *, reason: str = "") -> dict[str, Any]:
    return {
        "ok": True,
        "query": query,
        "status": "disambiguate",
        "reason": reason,
        "resolved": None,
        "needs_disambiguation": True,
        "candidates": [
            {
                "symbol": "TCS",
                "name": "Tata Consultancy Services Limited",
                "exchange": "NSE",
                "confidence": 0.6,
                "yahoo_symbol": "TCS.NS",
            },
            {
                "symbol": "TATASTEEL",
                "name": "Tata Steel Limited",
                "exchange": "NSE",
                "confidence": 0.6,
                "yahoo_symbol": "TATASTEEL.NS",
            },
        ],
        "message": "which did you mean?",
    }


def test_binds_clean_symbol_with_metadata() -> None:
    target = target_from_payload(_payload("SAKSOFT", name="Saksoft Limited"))
    assert isinstance(target, ResearchTarget)
    assert target.symbol == "SAKSOFT"
    assert target.name == "Saksoft Limited"
    assert target.exchange == "NSE"
    assert target.region == "IN"
    assert target.confidence == 0.95


def test_symbol_is_uppercased_and_shape_gated() -> None:
    target = target_from_payload(_payload("brk.b"))
    assert isinstance(target, ResearchTarget) and target.symbol == "BRK.B"
    # The live ULTRA bug shape: a whole focus sentence can NEVER bind — even
    # when the wire status claims "bound".
    sentence = (
        "Saksoft Limited — focus: Analyze revenue growth trajectory, margin "
        "trends, and valuation multiples"
    )
    assert target_from_payload(_payload(sentence)) is None
    # Too long / illegal characters / empty all rejected.
    assert target_from_payload(_payload("A" * 21)) is None
    assert target_from_payload(_payload("RELIANCE INDUSTRIES")) is None  # embedded space
    assert target_from_payload(_payload("")) is None


def test_status_is_the_one_verdict_no_second_floor() -> None:
    # R10: a wire "bound" binds at any score the policy accepted — this layer
    # holds NO second threshold (the pre-R10 0.5 floor is gone).
    bound = target_from_payload(_payload("CMTL", confidence=0.8, status="bound"))
    assert isinstance(bound, ResearchTarget)
    # An unresolved verdict never binds, whatever the embedded score says.
    unresolved = _payload("CMTL", confidence=0.99, status="unresolved")
    unresolved["ok"] = False
    assert target_from_payload(unresolved) is None


def test_legacy_payload_without_status_binds_only_at_accept() -> None:
    # A pre-R10 reply (no status) gets the policy's ACCEPT bar — never the old
    # 0.5 floor that silently bound research to the wrong company.
    assert target_from_payload(_payload("CMTL", confidence=0.5, status=None)) is None
    assert target_from_payload(_payload("CMTL", confidence=ACCEPT - 0.01, status=None)) is None
    assert isinstance(target_from_payload(_payload("CMTL", confidence=ACCEPT, status=None)), ResearchTarget)


def test_disambiguate_status_builds_the_explicit_chooser() -> None:
    outcome = target_from_payload(_disambiguation_payload("tata"))
    assert isinstance(outcome, ResearchDisambiguation)
    assert outcome.query == "tata"
    assert [c["symbol"] for c in outcome.candidates] == ["TCS", "TATASTEEL"]
    # The wire candidates carry the brief-contract shape (types/brief.ts).
    assert set(outcome.candidates[0]) == {"symbol", "name", "exchange", "score", "yahoo_symbol"}
    payload = outcome.payload()
    assert payload["ok"] is True
    assert payload["needs_disambiguation"] is True
    assert payload["message"] == "which did you mean?"
    # No markdown, no structured — a chooser is never a half-brief.
    assert "markdown" not in payload and "structured" not in payload
    # The loop can stamp ITS run query over the attempt that disambiguated.
    assert outcome.payload(query="tata results today")["query"] == "tata results today"


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
    assert isinstance(target, ResearchTarget) and target.symbol == "ROUTE"
    assert calls == [("resolve_symbol", {"query": "Route Mobile results", "region": "IN"})]

    async def crash(name: str, args: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("resolver exploded")

    assert _run(resolve_target(crash, "anything")) is None


def test_resolved_payload_round_trips_raw_and_is_honest_for_none() -> None:
    raw = _payload("NVDA", name="NVIDIA Corporation")
    raw["candidates"] = [{"symbol": "NVDA"}]
    target = target_from_payload(raw)
    assert isinstance(target, ResearchTarget)
    # The full resolver reply (candidates and all) rides structured["resolved"].
    assert resolved_payload(target) is raw
    none_payload = resolved_payload(None)
    assert none_payload["ok"] is False
    assert none_payload["message"] == NO_INSTRUMENT_NOTE


def test_equity_like_classification() -> None:
    equity = target_from_payload(_payload("ROUTE"))
    assert isinstance(equity, ResearchTarget) and equity.is_equity_like() is True
    crypto_payload = _payload("BTC-USD")
    crypto_payload["resolved"]["asset_class"] = "crypto"
    crypto = target_from_payload(crypto_payload)
    assert isinstance(crypto, ResearchTarget) and crypto.is_equity_like() is False


def test_target_is_frozen() -> None:
    target = target_from_payload(_payload("NVDA"))
    assert isinstance(target, ResearchTarget)
    try:
        target.symbol = "HACK"  # type: ignore[misc]
    except AttributeError:
        return
    raise AssertionError("ResearchTarget must be immutable")


def test_keyword_salad_query_binds_via_leading_prefix() -> None:
    # The live R8 gate-1 rerun: the model passed "Route Mobile Q4 FY26 quarterly
    # results revenue profit dividend exchange filings" — the full string does
    # not resolve, but the leading words name the company. The prefix fallback
    # must bind it instead of degrading to an unbound, empty run.
    async def tool_call(name: str, args: dict[str, Any]) -> dict[str, Any]:
        assert name == "resolve_symbol"
        if args["query"] == "Route Mobile":
            return _payload("ROUTE", name="Route Mobile Limited", confidence=0.98)
        return {"ok": False, "status": "unresolved", "resolved": None}

    bound = _run(
        resolve_target(
            tool_call,
            "Route Mobile Q4 FY26 quarterly results revenue profit dividend exchange filings",
            region="IN",
        )
    )
    assert isinstance(bound, ResearchTarget) and bound.symbol == "ROUTE"


def test_one_word_prefix_binds_only_at_first_word_band_or_above() -> None:
    # R10: the 1-word prefix rung exists ("RELIANCE.NS results" must reach the
    # bare ticker) but weak one-word evidence (prefix 0.92 / substring 0.8)
    # never binds a run — a stray leading word is not a company.
    async def weak(name: str, args: dict[str, Any]) -> dict[str, Any]:
        if args["query"] == "Frontiers":
            return _payload("REFR", name="Research Frontiers Inc", confidence=0.8)
        return {"ok": False, "status": "unresolved", "resolved": None}

    assert _run(resolve_target(weak, "Frontiers something quarterly outlook today")) is None

    async def strong(name: str, args: dict[str, Any]) -> dict[str, Any]:
        if args["query"] == "RELIANCE.NS":
            return _payload("RELIANCE", name="Reliance Industries Limited", confidence=1.0)
        return {"ok": False, "status": "unresolved", "resolved": None}

    bound = _run(resolve_target(strong, "RELIANCE.NS quarterly results dividend history filings"))
    assert isinstance(bound, ResearchTarget) and bound.symbol == "RELIANCE"


def test_curated_disambiguation_beats_an_incidental_fuzzy_one() -> None:
    # "Tata stock price today": the full query fuzzy-disambiguates against junk;
    # the marquee prefix produces the CURATED family chooser — the curated one
    # must win (and stop the scan), never the junk candidates.
    async def tool_call(name: str, args: dict[str, Any]) -> dict[str, Any]:
        q = args["query"]
        if q == "Tata stock price today":
            junk = _disambiguation_payload(q, reason="score 0.64 in the disambiguation band")
            junk["candidates"] = [
                {"symbol": "FRLCY", "name": "Freelancer Ltd", "confidence": 0.64}
            ]
            return junk
        if q == "Tata stock":
            return _disambiguation_payload(q, reason="marquee family name")
        return {"ok": False, "status": "unresolved", "resolved": None}

    outcome = _run(resolve_target(tool_call, "Tata stock price today", region="IN"))
    assert isinstance(outcome, ResearchDisambiguation)
    assert outcome.curated is True
    assert [c["symbol"] for c in outcome.candidates] == ["TCS", "TATASTEEL"]


def test_fuzzy_disambiguation_survives_when_nothing_binds() -> None:
    async def tool_call(name: str, args: dict[str, Any]) -> dict[str, Any]:
        if args["query"] == "relianse industries":
            return _disambiguation_payload(args["query"], reason="score 0.69")
        return {"ok": False, "status": "unresolved", "resolved": None}

    outcome = _run(resolve_target(tool_call, "relianse industries"))
    assert isinstance(outcome, ResearchDisambiguation)
    assert outcome.curated is False


def test_prefix_fallback_never_binds_when_nothing_resolves() -> None:
    async def tool_call(name: str, args: dict[str, Any]) -> dict[str, Any]:
        return {"ok": False, "status": "unresolved", "resolved": None}

    bound = _run(resolve_target(tool_call, "completely unresolvable keyword salad here"))
    assert bound is None
