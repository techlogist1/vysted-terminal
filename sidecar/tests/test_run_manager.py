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
    provider = _LoopingProvider(per_round=1)
    _patch(monkeypatch, provider)
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
    assert provider.calls == 2  # N steps = exactly N provider rounds


@pytest.mark.asyncio
async def test_breach_stops_before_the_rounds_tools_and_the_next_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-AGENT-037: the flag used to be only a flag — the round's tools ran and
    the next (unmetered) request went out after the breach."""
    provider = _LoopingProvider(per_round=100_000)
    _patch(monkeypatch, provider)
    dispatched: list[str] = []

    async def _no_dispatch(tool_call: Any, *_a: Any, **_k: Any) -> str:
        dispatched.append(tool_call.name)
        return "{}"

    monkeypatch.setattr(agent_runtime, "_dispatch_tool", _no_dispatch)
    run_id = run_manager.launch_run(
        agent_id="copilot", prompt="x", api_key="sk", budget=RunBudget(max_tokens=1000)
    )
    row = await _await_terminal(run_id)
    assert row is not None
    assert (row.status, row.detail) == ("error", "token ceiling 1000 reached (100000 used)")
    assert provider.calls == 1
    assert dispatched == []
    assert row.cost.tokens == 100_000


@pytest.mark.asyncio
async def test_a_final_answer_on_the_ceiling_round_is_done(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-AGENT-038: a one-shot answer under max_steps=1 finished; it is not an error."""
    _patch(monkeypatch, _OneShotProvider())
    run_id = run_manager.launch_run(
        agent_id="copilot", prompt="x", api_key="sk", budget=RunBudget(max_steps=1)
    )
    row = await _await_terminal(run_id)
    assert row is not None
    assert row.status == "done"
    assert row.detail == "completed (step ceiling 1 reached (1 taken) on the final round)"
    assert row.answer == "Analysis complete: NVDA looks rich."


@pytest.mark.asyncio
async def test_a_provider_less_run_is_priced_at_the_resolved_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-AGENT-074: buffett defaults to anthropic/opus; an omitted provider was
    priced at the $5/M fallback instead of the opus rate."""
    from services.budget_guard import estimate_spend_usd

    _patch(monkeypatch, _OneShotProvider())
    run_id = run_manager.launch_run(agent_id="buffett", prompt="x", api_key="sk")
    row = await _await_terminal(run_id)
    assert row is not None and row.status == "done"
    assert row.cost.spend_usd == round(estimate_spend_usd("anthropic", "claude-opus-4-8", 70), 6)


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


@pytest.mark.asyncio
async def test_omitted_ceilings_take_the_server_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    """R15-AGENT-034: an empty budget never means "no ceiling"."""
    from models.run import DEFAULT_RUN_BUDGET
    from services.budget_guard import BudgetGuard

    guards: list[BudgetGuard] = []

    class _CapturingGuard(BudgetGuard):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            guards.append(self)

    monkeypatch.setattr(run_manager, "BudgetGuard", _CapturingGuard)
    _patch(monkeypatch, _OneShotProvider())
    run_id = run_manager.launch_run(agent_id="copilot", prompt="x", budget=RunBudget())
    row = await _await_terminal(run_id)
    assert row is not None and row.budget == DEFAULT_RUN_BUDGET
    (guard,) = guards
    assert (guard.max_tokens, guard.max_spend_usd, guard.max_wall_seconds, guard.max_steps) == (
        120_000,
        1.0,
        600,
        12,
    )


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
    run_manager.cancel_run(run_id)
    row = await _await_terminal(run_id)
    assert row is not None
    assert row.status == "cancelled"


def test_cancel_unknown_raises_not_found() -> None:
    with pytest.raises(run_manager.RunNotFound):
        run_manager.cancel_run("nope")


def test_launch_unknown_agent_raises() -> None:
    with pytest.raises(run_manager.RunManagerError):
        run_manager.launch_run(agent_id="not-an-agent", prompt="x")


# ---------------------------------------------------------------------------
# HITL pause / answer / resume (FR-028)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pause_answer_resumes_run(monkeypatch: pytest.MonkeyPatch) -> None:
    class _SlowProvider:
        async def stream_chat(self, **_kwargs: Any) -> AsyncIterator[Any]:
            await asyncio.sleep(5)
            yield LLMDoneEvent()

    _patch(monkeypatch, _SlowProvider())
    run_id = run_manager.launch_run(agent_id="copilot", prompt="research NVDA", api_key="sk-test")
    await asyncio.sleep(0)  # the run is live, mid-round

    # The RUNNING run is paused with a question (a finished run cannot be).
    run_manager.pause_run(run_id, "Which exchange?")
    await _await_terminal(run_id)
    paused = runs_store.get_run(run_id)
    assert paused is not None
    assert paused.status == "paused"
    assert paused.question == "Which exchange?"

    # Human answers → run resumes from the checkpoint and completes.
    _patch(monkeypatch, _OneShotProvider())
    run_manager.answer_run(run_id, "NSE", api_key="sk-test")
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
    run_manager.resume_run(run_id, budget=RunBudget(max_tokens=1_000_000))
    resumed = await _await_terminal(run_id)
    assert resumed is not None
    assert resumed.status == "done"


def test_answer_unknown_run_raises() -> None:
    with pytest.raises(run_manager.RunNotFound):
        run_manager.answer_run("ghost", "hi")


def test_resume_unknown_run_raises() -> None:
    with pytest.raises(run_manager.RunNotFound):
        run_manager.resume_run("ghost")


# ---------------------------------------------------------------------------
# R10 — resume re-threads the persisted depth floor + region
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resume_rethreads_persisted_depth_and_region(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The E2 durable-run tail: a resumed run used to rebuild options BARE, so
    the research-depth ContextVar floor silently reset to NORMAL (and the
    region to the resume request's default). Launch under depth=deep/region=IN,
    resume, and assert the spawned driver sees both again."""
    import config

    # The launch breaches its ceiling so it ends resumable (a done run is final).
    _patch(monkeypatch, _LoopingProvider(per_round=100_000))
    region_token = config.set_request_region("IN")
    try:
        run_id = run_manager.launch_run(
            agent_id="copilot",
            prompt="research NVDA deeply",
            api_key="sk-test",
            budget=RunBudget(max_tokens=1000),
            options={"research_depth": "deep"},
        )
    finally:
        config.reset_request_region(region_token)
    await _await_terminal(run_id)
    # The allow-listed options persisted (depth from the caller, region from
    # the LAUNCH request) — and nothing else.
    assert runs_store.get_options(run_id) == {"research_depth": "deep", "region": "IN"}

    captured: dict[str, Any] = {}

    def _capture_invoke(**kwargs: Any) -> Any:
        async def _gen() -> Any:
            captured.update(kwargs)
            # The detached task re-threads the persisted region (the resume
            # request's middleware scope is the WRONG one).
            captured["region_at_invoke"] = config.get_region()
            from models.llm import LLMDoneEvent

            yield LLMDoneEvent()

        return _gen()

    monkeypatch.setattr(agent_runtime, "invoke_agent", _capture_invoke)
    run_manager.resume_run(run_id, api_key="sk-test")
    row = await _await_terminal(run_id)
    assert row is not None and row.status == "done"
    assert captured["options"]["research_depth"] == "deep"
    # region rides the ContextVar, never an adapter kwarg (popped in the task).
    assert "region" not in captured["options"]
    assert captured["region_at_invoke"] == "IN"


# ---------------------------------------------------------------------------
# R15-AGENT-013 — a run's answer, brief and host actions are collectable
# ---------------------------------------------------------------------------


class _ScriptedRoundsProvider:
    """Three rounds of prose; round 1 publishes a brief, round 2 writes a note."""

    def __init__(self) -> None:
        self.calls = 0

    async def stream_chat(
        self, messages: list[LLMMessage], model: str, api_key: str | None = None, **kwargs: Any
    ) -> AsyncIterator[Any]:
        self.calls += 1
        yield LLMDeltaEvent(text=f"Round {self.calls}: " + "valuation detail " * 20)
        if self.calls == 1:
            brief = {"symbol": "NVDA", "title": "NVDA", "markdown": "## Thesis"}
            yield LLMToolUseEvent(tool_call_id="c-brief", name="publish_brief", input=brief)
        elif self.calls == 2:
            note = {"scope": "NVDA", "text": "Watch the margin"}
            yield LLMToolUseEvent(tool_call_id="c-note", name="write_note", input=note)
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=10, output_tokens=10))


@pytest.mark.asyncio
async def test_run_output_is_returned_untruncated_by_get_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from routers import runs as runs_router

    _patch(monkeypatch, _ScriptedRoundsProvider())
    run_id = run_manager.launch_run(agent_id="copilot", prompt="research NVDA", api_key="sk")
    row = await _await_terminal(run_id)
    assert row is not None and row.status == "done"

    wire = runs_router.get_run(run_id)
    answer = wire["answer"]
    assert len(answer) > 500
    assert "Round 1:" in answer and "Round 3:" in answer
    assert "\n\nRound 2:" in answer  # each round is its own paragraph
    assert wire["brief"] == {"symbol": "NVDA", "title": "NVDA", "markdown": "## Thesis"}
    assert wire["hostActions"] == [
        {
            "tool_call_id": "c-note",
            "name": "write_note",
            "input": {"scope": "NVDA", "text": "Watch the margin"},
        }
    ]


class _TextThenOverBudgetProvider:
    """Writes prose, then a round whose usage breaches the token ceiling."""

    async def stream_chat(
        self, messages: list[LLMMessage], model: str, api_key: str | None = None, **kwargs: Any
    ) -> AsyncIterator[Any]:
        yield LLMDeltaEvent(text="Partial analysis before the ceiling.")
        yield LLMToolUseEvent(tool_call_id="c-1", name="price_data", input={})
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=100_000, output_tokens=0))


@pytest.mark.asyncio
async def test_errored_run_still_carries_its_partial_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Case the fix was not written against: an error exit keeps the text."""
    _patch(monkeypatch, _TextThenOverBudgetProvider())
    run_id = run_manager.launch_run(
        agent_id="copilot", prompt="x", api_key="sk", budget=RunBudget(max_tokens=1000)
    )
    row = await _await_terminal(run_id)
    assert row is not None and row.status == "error"
    assert row.answer == "Partial analysis before the ceiling."
