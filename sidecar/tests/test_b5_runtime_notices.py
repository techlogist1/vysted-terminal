"""Batch 5 (W3): every runtime notice is a typed ``notice`` step (C9).

The chat used to recognise a notice by matching its English copy, and the copy
drifted (R15-AGENT-031 / R15-UI-054). Each notice now carries
``step_kind="notice"``, so the frontend branches on the kind alone.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from services import action_ledger, agent_runtime


@pytest.fixture(autouse=True)
def _clean_ledger(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    action_ledger.reset_for_tests()
    monkeypatch.setattr(agent_runtime, "_ACK_GRACE_SECONDS", 0.0)
    yield
    action_ledger.reset_for_tests()


@pytest.mark.asyncio
async def test_all_three_divergence_branches_emit_notice_kind() -> None:
    # No ack, kept_previous and failed: the three divergence branches.
    action_ledger.record("kept", "kept_previous", {"symbol": "AAPL"})
    action_ledger.record("failed", "failed", {"symbol": "MSFT"})
    notices = await agent_runtime._publish_divergence_notices(["unacked", "kept", "failed"])
    assert len(notices) == 3
    assert {n.step_kind for n in notices} == {"notice"}
