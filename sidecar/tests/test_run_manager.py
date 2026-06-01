"""run_manager tests — durable launch, budget abort (SC-008), cancel, resume.

The provider is mocked at the ``agent_runtime.get_provider`` boundary (the same
seam ``test_agent_runtime`` uses) so NO real LLM call is made. The tests drive
the detached task on the test's own event loop via ``asyncio`` and assert the
durable run row reflects each outcome.

SC-008 is the load-bearing assertion: a budget breach MUST abort the run 100% of
the time, with a stated reason persisted as the run's ``detail``.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest

from config import DATA_DIR_ENV
from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMMessage, LLMToolUseEvent, LLMUsage
from models.run import RunBudget
from services import agent_runtime, run_manager, runs_store


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    agent_runtime.reload()
    run_manager.reset_for_tests()
    yield
    run_manager.reset_for_tests()


class _LoopingProvider:
    """Always emits a tool_use + done(usage) so invoke_agent loops every round.

    Each round reports ``per_round`` tokens, so a token ceiling set below
    ``per_round`` breaches on the very first round.
    """

    def __init__(self, per_round: int = 100_000) -> None:
        self.per_round = per_round
        self.calls = 0

    async def stream_chat(
        self, messages: list[LLMMessage], model: str, api_key: str | None = None, **kwargs: Any
    ) -> AsyncIterator[Any]:
        self.calls += 1
        yield LLMToolUseEvent(tool_call_id=f"call-{self.calls}", name="price_data", input={})
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=self.per_round, output_tokens=0))


class _OneShotProvider:
    """Emits a single delta + terminal done — a natural completion, no tools."""

    async def stream_chat(
        self, messages: list[LLMMessage], model: str, api_key: str | None = None, **kwargs: Any
    ) -> AsyncIterator[Any]:
        yield LLMDeltaEvent(text="Analysis complete: NVDA looks rich.")
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=50, output_tokens=20))


def _patch(monkeypatch: pytest.MonkeyPatch, provider: Any) -> None:
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: provider)


async def _await_terminal(run_id: str, *, timeout: float = 5.0) -> Any:
    """Await the detached task for ``run_id`` then return the run row."""
    task = run_manager._TASKS.get(run_id)
    if task is not None:
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
        except (asyncio.CancelledError, Exception):  # noqa: BLE001 — terminal-state captured below
            pass
    return runs_store.get_run(run_id)


# ---------------------------------------------------------------------------
# Durable launch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_launch_creates_durable_row_immediately(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, _OneShotProvider())
    run_id = run_manager.launch_run(agent_id="copilot", prompt="research NVDA", api_key="sk-test")
    # The row exists the instant launch returns — before the task finishes.
    row = runs_store.get_run(run_id)
    assert row is not None
    assert row.agent_id == "copilot"
    assert row.status in ("running", "done")  # task may or may not have run yet
    await _await_terminal(run_id)


@pytest.mark.asyncio
async def test_natural_completion_marks_done(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, _OneShotProvider())
    run_id = run_manager.launch_run(agent_id="copilot", prompt="x", api_key="sk-test")
    row = await _await_terminal(run_id)
    assert row is not None
    assert row.status == "done"
    assert row.detail == "completed"
    assert row.cost.steps == 1
    assert row.cost.tokens == 70
    # The transcript carries the assistant's text for the foreground view.
    assert any("NVDA looks rich" in m["content"] for m in row.transcript)


# ---------------------------------------------------------------------------
# SC-008 — a budget breach aborts the run 100% of the time, with a reason.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_token_breach_aborts_with_reason_and_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch(monkeypatch, _LoopingProvider(per_round=100_000))
    run_id = run_manager.launch_run(
        agent_id="copilot",
        prompt="run forever",
        api_key="sk-test",
        budget=RunBudget(max_tokens=1000),  # one round (100k) blows it
    )
    row = await _await_terminal(run_id)
    assert row is not None
    assert row.status == "error"
    assert row.detail is not None
    assert "token ceiling 1000" in row.detail
    # A checkpoint was captured so the run is resumable.
    assert row.checkpoint_messages >= 1
    # The run did NOT spin to the _MAX_TOOL_ROUNDS cap — it aborted early.
    assert row.cost.steps <= 2


@pytest.mark.asyncio
async def test_wall_clock_breach_aborts_mid_round(monkeypatch: pytest.MonkeyPatch) -> None:
    """SC-008 wall-clock: a round that STALLS without ever emitting a terminator
    must still abort at the ceiling. breach() is only polled at a round terminator
    that never arrives here, so the asyncio.timeout backstop is what enforces the
    wall budget. (Regression guard for the self-validation finding: without the
    backstop this run would hang indefinitely.)"""

    class _HangingProvider:
        """Stalls mid-round forever — no terminator, so the round-boundary
        breach() check can never fire."""

        async def stream_chat(self, **_kwargs: Any) -> AsyncIterator[Any]:
            await asyncio.sleep(30)
            yield LLMDoneEvent()  # pragma: no cover — never reached

    _patch(monkeypatch, _HangingProvider())
    run_id = run_manager.launch_run(
        agent_id="copilot",
        prompt="hang",
        api_key="sk-test",
        budget=RunBudget(max_wall_seconds=0.3),
    )
    row = await _await_terminal(run_id, timeout=5.0)
    assert row is not None
    assert row.status == "error"
    assert "wall-clock ceiling" in (row.detail or "")
    # A checkpoint was still captured so the run is resumable.
    assert row.checkpoint_messages >= 1


@pytest.mark.asyncio
async def test_step_breach_aborts(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, _LoopingProvider(per_round=1))
    run_id = run_manager.launch_run(
        agent_id="copilot",
        prompt="loop",
        api_key="sk-test",
        budget=RunBudget(max_steps=2),
    )
    row = await _await_terminal(run_id)
    assert row is not None
    assert row.status == "error"
    assert "step ceiling 2" in (row.detail or "")


@pytest.mark.asyncio
async def test_spend_breach_aborts(monkeypatch: pytest.MonkeyPatch) -> None:
    # 100k tokens at the opus rate ($30/1M) = $3 per round; cap at $1.
    _patch(monkeypatch, _LoopingProvider(per_round=100_000))
    run_id = run_manager.launch_run(
        agent_id="copilot",
        prompt="spend",
        provider="anthropic",
        model="claude-opus-4-8",
        api_key="sk-test",
        budget=RunBudget(max_spend_usd=1.0),
    )
    row = await _await_terminal(run_id)
    assert row is not None
    assert row.status == "error"
    assert "spend ceiling" in (row.detail or "")
    assert row.cost.spend_usd > 0


# ---------------------------------------------------------------------------
# api_key is never persisted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_key_never_persisted(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "sk-super-secret-key-xyz"
    _patch(monkeypatch, _OneShotProvider())
    run_id = run_manager.launch_run(agent_id="copilot", prompt="x", api_key=secret)
    await _await_terminal(run_id)
    # The whole serialised run row must not contain the key anywhere.
    row = runs_store.get_run(run_id)
    assert row is not None
    assert secret not in row.model_dump_json()


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_marks_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    # A provider that yields control so the task is genuinely in-flight when we
    # cancel — an await point inside the stream.
    class _SlowProvider:
        async def stream_chat(self, **_kwargs: Any) -> AsyncIterator[Any]:
            await asyncio.sleep(5)
            yield LLMDoneEvent()

    _patch(monkeypatch, _SlowProvider())
    run_id = run_manager.launch_run(agent_id="copilot", prompt="x", api_key="sk-test")
    await asyncio.sleep(0)  # let the task start and hit the sleep
    assert run_manager.cancel_run(run_id) is True
    row = await _await_terminal(run_id)
    assert row is not None
    assert row.status == "cancelled"


def test_cancel_unknown_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    assert run_manager.cancel_run("nope") is False


def test_launch_unknown_agent_raises() -> None:
    with pytest.raises(run_manager.RunManagerError):
        run_manager.launch_run(agent_id="not-an-agent", prompt="x")


# ---------------------------------------------------------------------------
# HITL pause / answer / resume (FR-028)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pause_answer_resumes_run(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, _OneShotProvider())
    run_id = run_manager.launch_run(agent_id="copilot", prompt="research NVDA", api_key="sk-test")
    await _await_terminal(run_id)  # run completes once, leaving a checkpoint

    # Operator pauses the run with a question.
    assert run_manager.pause_run(run_id, "Approve buying NVDA?") is True
    paused = runs_store.get_run(run_id)
    assert paused is not None
    assert paused.status == "paused"
    assert paused.question == "Approve buying NVDA?"

    # Human answers → run resumes from the checkpoint and completes again.
    _patch(monkeypatch, _OneShotProvider())
    assert run_manager.answer_run(run_id, "Yes, proceed", api_key="sk-test") is True
    row = await _await_terminal(run_id)
    assert row is not None
    assert row.status == "done"
    assert row.question is None


@pytest.mark.asyncio
async def test_resume_after_budget_breach_with_fresh_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch(monkeypatch, _LoopingProvider(per_round=100_000))
    run_id = run_manager.launch_run(
        agent_id="copilot", prompt="big task", api_key="sk-test", budget=RunBudget(max_tokens=1000)
    )
    row = await _await_terminal(run_id)
    assert row is not None and row.status == "error"

    # Resume with a one-shot provider so it can complete under fresh ceilings.
    _patch(monkeypatch, _OneShotProvider())
    assert run_manager.resume_run(run_id, budget=RunBudget(max_tokens=1_000_000)) is True
    resumed = await _await_terminal(run_id)
    assert resumed is not None
    assert resumed.status == "done"


def test_answer_unknown_run_raises() -> None:
    with pytest.raises(run_manager.RunManagerError):
        run_manager.answer_run("ghost", "hi")


def test_resume_unknown_run_raises() -> None:
    with pytest.raises(run_manager.RunManagerError):
        run_manager.resume_run("ghost")
