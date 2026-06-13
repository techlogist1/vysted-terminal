"""R10 (E1) — the ONE resolution acceptance policy + the Phase-0 repro table.

Three layers under test:

1. ``services.resolution_policy.decide`` — the single accept/disambiguate/
   unresolved verdict (band-aware: a whole-string fuzzy hit NEVER binds;
   a marquee family below ACCEPT always disambiguates).
2. A grep-style pin that no second threshold constant exists anywhere in
   ``services`` — the pre-R10 defect was three gates with two truths.
3. The Phase-0 repro table from the defect catalogue, pinned END-TO-END
   through the real resolver + the real ``resolve_symbol`` tool +
   ``resolve_target`` — the queries that live-bound REFR/FRLCY/LNKS must now
   bind RELIANCE or honestly disambiguate. Offline: the live lookup is stubbed.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

import pytest

from services import resolution_policy, symbol_resolver
from services.agent_tools.resolve_symbol import _resolve_symbol
from services.research.target import ResearchDisambiguation, ResearchTarget, resolve_target
from services.resolution_policy import (
    ACCEPT,
    BAND_EXACT_TICKER,
    BAND_FUZZY,
    BAND_MARQUEE,
    BAND_PREFIX,
    BAND_SUBSTRING,
    REJECT,
    decide,
)
from services.symbol_resolver import Instrument, Resolution


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(symbol_resolver, "_live_lookup", lambda query, region: [])


def _instrument(symbol: str, *, score: float, band: int, region: str = "IN") -> Instrument:
    return Instrument(
        symbol=symbol,
        name=f"{symbol} Ltd",
        exchange="NSE" if region == "IN" else "US",
        region=region,
        asset_class="equity",
        yahoo_symbol=f"{symbol}.NS" if region == "IN" else symbol,
        score=score,
        band=band,
    )


def _resolution(best: Instrument | None, candidates: list[Instrument] | None = None) -> Resolution:
    return Resolution(query="q", best=best, candidates=candidates or ([best] if best else []))


# --- 1. decide() — the one verdict -------------------------------------------


def test_decide_thresholds() -> None:
    assert ACCEPT == 0.72 and REJECT == 0.50
    exact = _instrument("RELIANCE", score=1.0, band=BAND_EXACT_TICKER)
    assert decide(_resolution(exact)).outcome == "bound"
    mid = _instrument("X", score=0.6, band=BAND_SUBSTRING)
    assert decide(_resolution(mid)).outcome == "disambiguate"
    low = _instrument("X", score=0.4, band=BAND_SUBSTRING)
    assert decide(_resolution(low)).outcome == "unresolved"
    assert decide(_resolution(None)).outcome == "unresolved"


def test_decide_boundary_values_pin_accept_and_reject() -> None:
    # The ACCEPT/REJECT numeric boundary is pinned with a STRONG (prefix) band —
    # the band that legitimately binds at the threshold.
    at_accept = _instrument("X", score=ACCEPT, band=BAND_PREFIX)
    assert decide(_resolution(at_accept)).outcome == "bound"
    just_under = _instrument("X", score=ACCEPT - 0.001, band=BAND_PREFIX)
    assert decide(_resolution(just_under)).outcome == "disambiguate"
    at_reject = _instrument("X", score=REJECT, band=BAND_PREFIX)
    assert decide(_resolution(at_reject)).outcome == "disambiguate"
    under_reject = _instrument("X", score=REJECT - 0.001, band=BAND_PREFIX)
    assert decide(_resolution(under_reject)).outcome == "unresolved"


def test_decide_substring_band_never_binds() -> None:
    # R10 review hardening: a bare-substring hit (band 1, always score 0.8 —
    # "Technologies" inside "Palantir Technologies") must DISAMBIGUATE, never
    # bind, even though 0.8 >= ACCEPT. Only band >= prefix binds outright.
    substr = _instrument("PLTR", score=0.8, band=BAND_SUBSTRING, region="US")
    verdict = decide(_resolution(substr))
    assert verdict.outcome == "disambiguate"
    assert verdict.instrument is None


def test_decide_fuzzy_band_never_binds() -> None:
    # The E1 class: SM("research reliance", "research frontiers inc") = 0.798
    # >= ACCEPT — a whole-string fuzzy hit must still NEVER bind silently.
    fuzzy_high = _instrument("REFR", score=0.798, band=BAND_FUZZY, region="US")
    verdict = decide(_resolution(fuzzy_high))
    assert verdict.outcome == "disambiguate"
    assert verdict.instrument is None


def test_decide_marquee_family_forces_disambiguation_with_candidates() -> None:
    family = [
        _instrument("TCS", score=0.6, band=BAND_MARQUEE),
        _instrument("TATASTEEL", score=0.6, band=BAND_MARQUEE),
    ]
    verdict = decide(_resolution(family[0], family))
    assert verdict.outcome == "disambiguate"
    assert "marquee" in verdict.reason
    assert [c.symbol for c in verdict.candidates] == ["TCS", "TATASTEEL"]


def test_decide_marquee_primary_binds() -> None:
    primary = _instrument("M&M", score=0.97, band=BAND_MARQUEE)
    assert decide(_resolution(primary)).outcome == "bound"


# --- 2. no second threshold constant anywhere --------------------------------


def test_no_second_threshold_constant_exists() -> None:
    services = Path(__file__).resolve().parents[1] / "services"
    numeric_assign = re.compile(
        r"^\s*(CONFIDENCE_FLOOR|DISAMBIGUATION_THRESHOLD|ACCEPT|REJECT)\s*=\s*[0-9.]",
        re.MULTILINE,
    )
    offenders: list[tuple[str, str]] = []
    for path in sorted(services.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        # resolution_policy.py's docstring documents the killed constant by
        # name — every OTHER mention (an import, a use, a redefinition) fails.
        if "CONFIDENCE_FLOOR" in text and path.name != "resolution_policy.py":
            offenders.append((path.name, "CONFIDENCE_FLOOR"))
        for match in numeric_assign.finditer(text):
            if path.name != "resolution_policy.py":
                offenders.append((path.name, match.group(1)))
    assert offenders == [], f"second acceptance threshold found: {offenders}"


# --- 3. the Phase-0 repro table, end-to-end ----------------------------------


async def _tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    assert name == "resolve_symbol"
    return await _resolve_symbol(args)


def _target(query: str) -> ResearchTarget | ResearchDisambiguation | None:
    return _run(resolve_target(_tool, query, region="IN"))


def test_repro_research_reliance_never_binds_refr() -> None:
    # Phase-0: "research Reliance" fuzzy-bound REFR (Research Frontiers, US)
    # at 0.798. Query cleaning strips the command verb; the bare name is the
    # exact NSE ticker.
    outcome = _target("research Reliance")
    assert isinstance(outcome, ResearchTarget)
    assert outcome.symbol == "RELIANCE"
    assert outcome.exchange == "NSE"


def test_repro_reliance_q4_results_never_binds_frlcy() -> None:
    # Phase-0: "Reliance Q4 results" bound FRLCY (Freelancer Ltd) at 0.686.
    # The fuzzy band never binds; the 1-word prefix reaches the exact ticker.
    outcome = _target("Reliance Q4 results")
    assert isinstance(outcome, ResearchTarget)
    assert outcome.symbol == "RELIANCE"


def test_repro_full_company_salad_binds_via_two_word_prefix() -> None:
    # Phase-0: "Reliance Industries Q4 FY26 results" bound LNKS (Linkers
    # Industries) at 0.712. >4 words disables whole-string fuzzy; the 2-word
    # prefix "Reliance Industries" is a suffix-stripped name-exact.
    outcome = _target("Reliance Industries Q4 FY26 results")
    assert isinstance(outcome, ResearchTarget)
    assert outcome.symbol == "RELIANCE"


def test_repro_lowercase_salad_binds_reliance_not_lnks() -> None:
    # Phase-0: "reliance industries quarterly results" scored LNKS (US) 0.690
    # over RELIANCE (NSE) 0.688 via the additive locale bonus. The band
    # tie-break + prefix loop now lands the real company.
    outcome = _target("reliance industries quarterly results")
    assert isinstance(outcome, ResearchTarget)
    assert outcome.symbol == "RELIANCE"


def test_repro_marquee_families_disambiguate_not_silently_bind() -> None:
    # Phase-0: "Tata" → TCS and "Bajaj" → BAJFINANCE bound silently at a
    # clamped 1.0. Marquee families now force the curated chooser.
    for query, expected_first in (("Tata", "TCS"), ("Bajaj", "BAJFINANCE")):
        outcome = _target(query)
        assert isinstance(outcome, ResearchDisambiguation), query
        assert outcome.curated is True
        assert outcome.candidates[0]["symbol"] == expected_first


def test_marquee_primary_aliases_bind_their_canonical_instrument() -> None:
    reliance = _target("reliance")
    assert isinstance(reliance, ResearchTarget) and reliance.symbol == "RELIANCE"
    mahindra = _target("mahindra")
    assert isinstance(mahindra, ResearchTarget) and mahindra.symbol == "M&M"


# --- marquee property: region IN => every marquee row is IN-listed -----------


def test_marquee_table_symbols_exist_in_the_nse_master() -> None:
    nse = symbol_resolver._nse_master()
    aliases = symbol_resolver._marquee_aliases()
    assert aliases, "marquee_aliases.json missing or empty"
    for key, entry in aliases.items():
        symbols = []
        if entry.get("primary"):
            symbols.append(entry["primary"])
        symbols.extend(entry.get("alternatives") or [])
        symbols.extend(entry.get("candidates") or [])
        assert symbols, f"marquee entry {key!r} names no symbols"
        for sym in symbols:
            assert sym in nse, f"marquee symbol {sym} ({key}) is not in the NSE master"


def test_marquee_property_region_in_every_bind_is_in_listed() -> None:
    for key in symbol_resolver._marquee_aliases():
        resolution = symbol_resolver.resolve(key, "IN")
        assert resolution.best is not None, key
        assert resolution.best.region == "IN", key
        assert all(c.region == "IN" for c in resolution.candidates), key
        verdict = resolution_policy.decide(resolution)
        if verdict.outcome == "bound":
            assert verdict.instrument is not None and verdict.instrument.region == "IN", key


def test_resolve_symbol_tool_reply_carries_the_status_verdict() -> None:
    bound = _run(_resolve_symbol({"query": "Tata Steel", "region": "IN"}))
    assert bound["status"] == "bound"
    assert bound["resolved"]["symbol"] == "TATASTEEL"
    ambiguous = _run(_resolve_symbol({"query": "tata", "region": "IN"}))
    assert ambiguous["ok"] is True
    assert ambiguous["status"] == "disambiguate"
    assert ambiguous["resolved"] is None  # resolved is null unless bound
    assert ambiguous["needs_disambiguation"] is True
    assert "which did you mean" in ambiguous["message"]
    missing = _run(_resolve_symbol({"query": "zzzqqqxnotathing", "region": "US"}))
    assert missing["ok"] is False
    assert missing["status"] == "unresolved"
    assert missing["resolved"] is None
