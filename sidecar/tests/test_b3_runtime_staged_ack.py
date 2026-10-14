"""C1 / D-B3-2: the non-terminal ``staged`` host-action ack.

Under AUTO, a change kind that still needs review is acked ``staged``. The
ledger must let a later terminal ack replace it, and the model must hear
"awaiting review", never the "did NOT apply" failure copy.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from models.llm import LLMToolUseEvent
from services import action_ledger, agent_runtime


@pytest.fixture(autouse=True)
def _clean_ledger() -> Iterator[None]:
    action_ledger.reset_for_tests()
    yield
    action_ledger.reset_for_tests()


def _ack(client: TestClient, call_id: str, status: str) -> None:
    resp = client.post("/agents/actions/ack", json={"toolCallId": call_id, "status": status})
    assert resp.status_code == 200


def test_staged_then_applied_resolves_to_applied(client: TestClient) -> None:
    _ack(client, "w-1", "staged")
    _ack(client, "w-1", "applied")
    entry = action_ledger.get("w-1")
    assert entry is not None and entry["status"] == "applied"


def test_late_staged_ack_never_replaces_a_terminal_one(client: TestClient) -> None:
    _ack(client, "w-2", "applied")
    _ack(client, "w-2", "staged")
    entry = action_ledger.get("w-2")
    assert entry is not None and entry["status"] == "applied"


def test_staged_ack_narrates_awaiting_review_not_failure() -> None:
    action_ledger.record("w-3", "staged")
    call = LLMToolUseEvent(tool_call_id="w-3", name="write_note", input={"scope": "TCS"})
    payload = json.loads(agent_runtime._grounded_host_action_result(call, action_ledger.get("w-3")))
    assert payload["ok"] is True
    assert payload["status"] == "staged"
    assert "awaiting their review" in payload["note"]
    assert "did NOT apply" not in payload["note"]
