"""R12 (D67) — identity cross-check: provider name vs resolver canonical name.

The D56 pattern applied to identity: when the fundamentals provider's company
name materially disagrees with the resolver's canonical name for the same
instrument, a machine-readable ``identity_conflict`` is emitted (both names,
never a swap). The GUJGASLTD-shaped case (the resolver's stale "Gujarat Gas"
vs yfinance's already-updated "Gujarat Energy") is the disagree anchor.
"""

from __future__ import annotations

from services import identity_crosscheck as ic


def test_similarity_agree_and_disagree() -> None:
    # Suffix/wording variants are the same identity (1.0).
    assert ic.token_set_similarity("Reliance Industries Limited", "Reliance Industries Ltd") == 1.0
    # The finding: one shared token out of three → 0.33, well below the floor.
    sim = ic.token_set_similarity("Gujarat Gas Limited", "Gujarat Energy Limited")
    assert sim < ic.CONFLICT_THRESHOLD
    assert round(sim, 2) == 0.33


def test_agree_case_emits_no_conflict() -> None:
    assert (
        ic.identity_conflict(
            "Reliance Industries Limited", "Reliance Industries Ltd", symbol="RELIANCE"
        )
        is None
    )
    # Exact match, differing only by corporate suffix + case.
    assert ic.identity_conflict("Infosys Limited", "INFOSYS LTD") is None


def test_gujgasltd_shaped_disagreement_emits_conflict() -> None:
    conflict = ic.identity_conflict(
        "Gujarat Gas Limited",
        "Gujarat Energy Limited",
        provider="yfinance",
        symbol="GUJGASLTD",
    )
    assert conflict is not None
    assert conflict["field"] == "identity"
    assert conflict["kind"] == "identity_conflict"
    assert conflict["symbol"] == "GUJGASLTD"
    assert conflict["similarity"] < ic.CONFLICT_THRESHOLD
    # Both names ride the conflict, in the D56 sources shape — never a swap.
    values = {s["value"] for s in conflict["sources"]}
    assert values == {"Gujarat Gas Limited", "Gujarat Energy Limited"}
    providers = {s["provider"] for s in conflict["sources"]}
    assert "yfinance" in providers
    assert any("resolver" in p for p in providers)


def test_missing_or_blank_names_are_noop() -> None:
    assert ic.identity_conflict(None, "Gujarat Energy Limited") is None
    assert ic.identity_conflict("Gujarat Gas Limited", None) is None
    assert ic.identity_conflict("   ", "Gujarat Energy Limited") is None
    assert ic.identity_conflict("Gujarat Gas Limited", "") is None


def test_completely_different_companies_conflict() -> None:
    # Bajaj Finance vs Bajaj Finserv are distinct entities — a mis-resolution
    # of one onto the other must surface, not be absorbed.
    conflict = ic.identity_conflict("Bajaj Finance Limited", "Bajaj Finserv Limited")
    assert conflict is not None
    assert conflict["similarity"] < ic.CONFLICT_THRESHOLD
