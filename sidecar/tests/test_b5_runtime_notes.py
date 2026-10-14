"""Batch 5 (W3): the agent can read the user's notes (C2).

R15-AGENT-020: ``write_note`` wrote into the Notes store, but nothing read it
back: no capability, snapshot field or preamble line carried a note, so the
agent could overwrite a thesis it could not see.
"""

from __future__ import annotations

import pytest

from models.agent import AgentContextSnapshot
from services.agent_runtime import _build_context_preamble, _build_local_tools

_PLEDGE = "exit if promoter pledge > 20%"


def _snapshot() -> AgentContextSnapshot:
    return AgentContextSnapshot(
        focused_source="chart",
        by_source={
            "__terminal__": {"focusedPanel": "chart", "focusedSymbol": "BDL", "charts": []},
            "__notes__": {
                "general": "Rotate out of defence names before the Q3 results.",
                "bySymbol": {"BDL": _PLEDGE},
            },
        },
    )


@pytest.mark.asyncio
async def test_a_symbol_note_is_readable_and_named_in_the_preamble() -> None:
    result = await _build_local_tools(_snapshot())["read_notes"]({"scope": "BDL"})
    assert result == {"ok": True, "scope": "BDL", "note": _PLEDGE, "empty": False}
    preamble = _build_context_preamble(_snapshot()) or ""
    assert "User notes exist for: global, BDL (read them with read_notes)." in preamble
    assert f'Their note on BDL: "{_PLEDGE}"' in preamble


@pytest.mark.asyncio
async def test_the_global_scope_reads_the_general_note_and_a_missing_one_says_so() -> None:
    tools = _build_local_tools(_snapshot())
    general = await tools["read_notes"]({"scope": "global"})
    assert general["note"] == "Rotate out of defence names before the Q3 results."
    missing = await tools["read_notes"]({"scope": "hal"})
    assert missing["empty"] is True and missing["note"] == ""
    assert missing["message"] == "The user has no HAL note."
