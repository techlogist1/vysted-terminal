from tests.conftest import *  # noqa
from tests.test_run_manager import _isolated, _patch, _await_terminal  # noqa
from typing import Any
import pytest
from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMToolUseEvent, LLMUsage
from models.run import RunBudget
from services import agent_runtime, run_manager

class TwoRounds:
    """Round 1: a valid write_note, small usage (dispatched). Round 2: save_layout + over budget."""
    def __init__(self, second_tokens): self.n=0; self.second=second_tokens
    async def stream_chat(self, messages, model, api_key=None, **kw):
        self.n+=1
        if self.n==1:
            yield LLMToolUseEvent(tool_call_id="c1", name="write_note", input={"scope":"NVDA","text":"a"})
            yield LLMDoneEvent(usage=LLMUsage(input_tokens=10, output_tokens=0))
        elif self.n==2 and self.second is not None:
            yield LLMToolUseEvent(tool_call_id="c2", name="write_note", input={"scope":"TCS","text":"b"})
            yield LLMDoneEvent(usage=LLMUsage(input_tokens=self.second, output_tokens=0))
        else:
            yield LLMDeltaEvent(text="done")
            yield LLMDoneEvent(usage=LLMUsage(input_tokens=5, output_tokens=5))

async def _run(monkeypatch, prov, budget):
    _patch(monkeypatch, prov)
    rid = run_manager.launch_run(agent_id="copilot", prompt="x", api_key="sk", budget=budget)
    return await _await_terminal(rid)

@pytest.mark.asyncio
async def test_success_path_keeps_dispatched_host_action(monkeypatch):
    row = await _run(monkeypatch, TwoRounds(None), RunBudget(max_tokens=100000))
    print("SUCCESS", row.status, row.host_actions)
    assert row.status in ("done","completed","ok","succeeded")
    assert [a["name"] for a in row.host_actions] == ["write_note"]

@pytest.mark.asyncio
async def test_second_round_halt_keeps_only_first(monkeypatch):
    row = await _run(monkeypatch, TwoRounds(100_000), RunBudget(max_tokens=1000))
    print("HALT2", row.status, row.detail, row.host_actions)
    assert row.status == "error"
    assert [a["input"]["scope"] for a in row.host_actions] == ["NVDA"]
