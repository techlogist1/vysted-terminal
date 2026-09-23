"""``services.witness`` — the ONE copy of the India-witness predicates.

R15-CODE-DATA-005: "is this an Indian listing" and "is this a block error" were
copied across the witness modules, so a fix to one copy was not a fix.
R15-DATA-003: the copies decided by bare-ticker membership in the Indian
masters, so a US-bound AMAL fetched Amal Ltd's BSE filings.
"""

from __future__ import annotations

import pytest

from services import dividend_actions, market_cap_witness, ownership_check, witness
from services.research import range_check


def test_every_witness_uses_the_shared_predicates() -> None:
    for module in (ownership_check, market_cap_witness, range_check):
        assert module.is_applicable is witness.is_india_listing, module.__name__
    for module in (ownership_check, range_check, dividend_actions):
        assert module.is_block_error is witness.is_block_error, module.__name__
        assert not hasattr(module, "_is_blocked"), module.__name__
    assert dividend_actions.is_india_listing is witness.is_india_listing


@pytest.mark.parametrize("module", [market_cap_witness, range_check])
def test_bare_colliding_ticker_is_not_an_india_listing(module: object) -> None:
    """SMR is both NuScale (NYSE) and SMR Jewels (BSE). Only the resolved BSE
    listing is Indian; the bare ticker bound to the US company is not."""
    assert not module.is_applicable("SMR")  # type: ignore[attr-defined]
    assert module.is_applicable("SMR.BO")  # type: ignore[attr-defined]
