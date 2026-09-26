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
from services.errors import humanize


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


class _PausingConversationProvider:
    """Records every request; a round either answers, calls a tool, or stalls
    (so the test can pause the run mid-round)."""

    def __init__(self, script: list[list[Any]]) -> None:
        self.script = script
        self.requests: list[list[tuple[str, str]]] = []

    async def stream_chat(
        self, messages: list[LLMMessage], model: str, api_key: str | None = None, **kwargs: Any
    ) -> AsyncIterator[Any]:
        self.requests.append([(m.role, m.content) for m in messages if m.role != "system"])
        for item in self.script[len(self.requests) - 1]:
            if item == "stall":
                await asyncio.sleep(30)
            yield item


def _ask(question: str) -> LLMToolUseEvent:
    return LLMToolUseEvent(tool_call_id="", name="ask_user", input={"question": question})


@pytest.mark.asyncio
async def test_ask_user_pauses_the_run_and_the_answer_resumes_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-CODE-AGENT-011: pause_run had no production caller, so paused, the
    question and the answer route could never fire. A delegate round that calls
    ask_user now parks the run with the question; none of that round's tools run."""
    done = LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))
    provider = _PausingConversationProvider(
        [
            [
                LLMDeltaEvent(text="Checking."),
                _ask("Which exchange, NSE or BSE?"),
                LLMToolUseEvent(tool_call_id="c1", name="price_data", input={}),
                done,
            ],
            [LLMDeltaEvent(text="Using NSE."), done],
        ]
    )
    _patch(monkeypatch, provider)
    dispatched: list[str] = []

    async def _tool(tool_call: Any, *_a: Any, **_k: Any) -> str:
        dispatched.append(tool_call.name)
        return "{}"

    monkeypatch.setattr(agent_runtime, "_dispatch_tool", _tool)
    run_id = run_manager.launch_run(agent_id="copilot", prompt="research RELIANCE", api_key="sk")
    paused = await _await_terminal(run_id)
    assert paused is not None
    assert (paused.status, paused.question) == ("paused", "Which exchange, NSE or BSE?")
    assert dispatched == []
    assert len(provider.requests) == 1

    run_manager.answer_run(run_id, "NSE", api_key="sk")
    row = await _await_terminal(run_id)
    assert row is not None
    assert (row.status, row.question) == ("done", None)
    assert provider.requests[1][-3:] == [
        ("assistant", "Checking."),
        ("assistant", "[ask_user → Which exchange, NSE or BSE?]"),
        ("user", "NSE"),
    ]


@pytest.mark.asyncio
async def test_answers_resume_the_conversation_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """R15-AGENT-036: the checkpoint is {prompt, turns}; each answer is the new
    prompt after the original prompt and every turn so far, tool steps included.
    Before, the prompt was replayed after the answer and a second answer became
    the prompt."""
    done = LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))
    provider = _PausingConversationProvider(
        [
            [
                LLMDeltaEvent(text="A1"),
                LLMToolUseEvent(tool_call_id="c1", name="price_data", input={}),
                done,
            ],
            [_ask("Q1?"), done],
            [LLMDeltaEvent(text="A2"), _ask("Q2?"), done],
            [LLMDeltaEvent(text="Final."), done],
        ]
    )
    _patch(monkeypatch, provider)

    async def _tool(*_a: Any, **_k: Any) -> str:
        return '{"ok": true, "close": 101}'

    monkeypatch.setattr(agent_runtime, "_dispatch_tool", _tool)

    run_id = run_manager.launch_run(agent_id="copilot", prompt="ORIGINAL", api_key="sk")
    await _await_terminal(run_id)
    run_manager.answer_run(run_id, "ANSWER ONE", api_key="sk")
    await _await_terminal(run_id)
    run_manager.answer_run(run_id, "ANSWER TWO", api_key="sk")
    row = await _await_terminal(run_id)
    assert row is not None and row.status == "done"

    tool_turn = ("assistant", '[price_data → {"ok": true, "close": 101}]')
    assert provider.requests[2] == [
        ("user", "ORIGINAL"),
        ("assistant", "A1"),
        tool_turn,
        ("assistant", "[ask_user → Q1?]"),
        ("user", "ANSWER ONE"),
    ]
    assert provider.requests[3] == [
        ("user", "ORIGINAL"),
        ("assistant", "A1"),
        tool_turn,
        ("assistant", "[ask_user → Q1?]"),
        ("user", "ANSWER ONE"),
        ("assistant", "A2"),
        ("assistant", "[ask_user → Q2?]"),
        ("user", "ANSWER TWO"),
    ]


@pytest.mark.asyncio
async def test_a_run_killed_mid_round_resumes_from_its_last_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-LIFECYCLE-012: the checkpoint was written only at exit, so a killed
    process left a running row with no checkpoint that could not be resumed."""
    done = LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))
    provider = _PausingConversationProvider(
        [
            [
                LLMDeltaEvent(text="A1"),
                LLMToolUseEvent(tool_call_id="c1", name="price_data", input={}),
                done,
            ],
            ["stall"],
            [LLMDeltaEvent(text="Final."), done],
        ]
    )
    _patch(monkeypatch, provider)

    async def _tool(*_a: Any, **_k: Any) -> str:
        return '{"ok": true, "close": 101}'

    monkeypatch.setattr(agent_runtime, "_dispatch_tool", _tool)
    run_id = run_manager.launch_run(agent_id="copilot", prompt="ORIGINAL", api_key="sk")
    while len(provider.requests) < 2:
        await asyncio.sleep(0.01)

    tool_turn = {"role": "assistant", "content": '[price_data → {"ok": true, "close": 101}]'}
    expected = {"prompt": "ORIGINAL", "turns": [{"role": "assistant", "content": "A1"}, tool_turn]}
    assert runs_store.get_checkpoint(run_id) == expected  # persisted mid-run

    # The process dies: its task is gone, the row still says running.
    task = run_manager._TASKS[run_id]
    task.cancel()
    await _await_terminal(run_id)
    runs_store._RECONCILED.clear()
    row = runs_store.get_run(run_id)
    assert row is not None
    assert (row.status, row.detail) == ("error", "interrupted by sidecar restart")

    run_manager.resume_run(run_id, api_key="sk")
    row = await _await_terminal(run_id)
    assert row is not None and row.status == "done"
    assert provider.requests[2] == [
        ("user", "ORIGINAL"),
        ("assistant", "A1"),
        (tool_turn["role"], tool_turn["content"]),
        ("user", "Continue the task from where you stopped."),
    ]


@pytest.mark.asyncio
async def test_a_compound_launch_waits_for_start_with_its_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-AGENT-039: the planner was gated to foreground turns, so an unattended
    run started a compound task with no plan to approve."""
    from services.planner import Plan, PlanStep

    async def _decompose(_prompt: str, **_k: Any) -> Plan:
        return Plan(
            goal="Set up the cockpit and research NVDA",
            steps=[
                PlanStep(action="open_panel", rationale="Open the chart"),
                PlanStep(action="research", rationale="Research NVDA"),
            ],
        )

    monkeypatch.setattr(agent_runtime, "decompose", _decompose)
    provider = _PausingConversationProvider([[LLMDeltaEvent(text="Done."), LLMDoneEvent()]])
    _patch(monkeypatch, provider)
    prompt = "open the chart, the watchlist and news, then research NVDA"
    run_id = run_manager.launch_run(
        agent_id="copilot", prompt=prompt, provider="openai", model="gpt-4.1-mini", api_key="sk"
    )
    planned = await _await_terminal(run_id)
    assert planned is not None and planned.status == "planned"
    assert planned.plan is not None
    assert planned.plan.goal == "Set up the cockpit and research NVDA"
    assert [s["rationale"] for s in planned.plan.steps] == ["Open the chart", "Research NVDA"]
    assert provider.requests == []  # nothing ran before the user's Start

    run_manager.start_run(run_id, api_key="sk")
    row = await _await_terminal(run_id)
    assert row is not None and (row.status, row.answer) == ("done", "Done.")
    assert provider.requests[0][-1] == ("user", prompt)


@pytest.mark.asyncio
async def test_get_run_lists_the_runs_tool_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    """R15-AGENT-039: the driver flattened every tool step to "[tool_use name]"
    and the run wire carried no activity."""
    from routers import runs as runs_router

    done = LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))
    provider = _PausingConversationProvider(
        [
            [LLMToolUseEvent(tool_call_id="c1", name="price_data", input={}), done],
            [LLMToolUseEvent(tool_call_id="c2", name="web_search", input={}), done],
            [LLMDeltaEvent(text="Summary."), done],
        ]
    )
    _patch(monkeypatch, provider)
    results = {
        "price_data": '{"ok": true, "close": 101}',
        "web_search": '{"ok": false, "error": "search rate-limited"}',
    }

    async def _tool(tool_call: Any, *_a: Any, **_k: Any) -> str:
        return results[tool_call.name]

    monkeypatch.setattr(agent_runtime, "_dispatch_tool", _tool)
    run_id = run_manager.launch_run(agent_id="copilot", prompt="x", api_key="sk")
    await _await_terminal(run_id)

    assert runs_router.get_run(run_id)["activity"] == [
        {"tool": "price_data", "status": "ok", "summary": '{"ok": true, "close": 101}'},
        {"tool": "web_search", "status": "error", "summary": "search rate-limited"},
    ]


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


@pytest.mark.asyncio
async def test_resume_reuses_the_launch_provider_model_and_adds_to_the_cost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-AGENT-035 / R15-LIFECYCLE-013: a resume ran on the agent default with
    no key (live: Ollama swapped llama3.1:8b for Qwen) and zeroed the cost."""
    _patch(monkeypatch, _LoopingProvider(per_round=100_000))
    run_id = run_manager.launch_run(
        agent_id="copilot",
        prompt="big task",
        provider="ollama",
        model="llama3.1:8b",
        api_key="sk-launch-secret",
        budget=RunBudget(max_tokens=1000),
    )
    before = await _await_terminal(run_id)
    assert before is not None and before.status == "error"

    captured: dict[str, Any] = {}

    def _capture_invoke(**kwargs: Any) -> Any:
        async def _gen() -> Any:
            captured.update(kwargs)
            kwargs["on_round_usage"](LLMUsage(input_tokens=10, output_tokens=0), "m", "ollama")
            yield LLMDeltaEvent(text="done now")
            yield LLMDoneEvent()

        return _gen()

    monkeypatch.setattr(agent_runtime, "invoke_agent", _capture_invoke)
    run_manager.resume_run(run_id, api_key="sk-resume-secret")
    after = await _await_terminal(run_id)
    assert after is not None and after.status == "done"
    assert (captured["provider"], captured["model"]) == ("ollama", "llama3.1:8b")
    assert captured["api_key"] == "sk-resume-secret"
    assert (after.cost.tokens, after.cost.steps) == (100_010, before.cost.steps + 1)
    from config import get_data_dir

    stored = (get_data_dir() / runs_store.DB_FILENAME).read_bytes()
    assert b"sk-launch-secret" not in stored and b"sk-resume-secret" not in stored


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
    # The runtime mints every tool-call id (R15-AGENT-046), never "c-note".
    [action] = wire["hostActions"]
    assert action["tool_call_id"].startswith("call_")
    assert wire["hostActions"] == [
        {
            "tool_call_id": action["tool_call_id"],
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


class _NoteThenOverBudgetProvider:
    """A valid write_note in a round whose usage breaches the token ceiling."""

    async def stream_chat(
        self, messages: list[LLMMessage], model: str, api_key: str | None = None, **kwargs: Any
    ) -> AsyncIterator[Any]:
        note = {"scope": "NVDA", "text": "Watch the margin"}
        yield LLMToolUseEvent(tool_call_id="c-note", name="write_note", input=note)
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=100_000, output_tokens=0))


@pytest.mark.asyncio
async def test_a_halted_rounds_host_actions_are_not_proposed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-AGENT-092: the halt stops before dispatch, so the round's write_note
    must not reach delegate-runs.ts as a proposed change."""
    _patch(monkeypatch, _NoteThenOverBudgetProvider())
    dispatched: list[str] = []

    async def _record_dispatch(tool_call: Any, *_a: Any, **_k: Any) -> str:
        dispatched.append(tool_call.name)
        return "{}"

    monkeypatch.setattr(agent_runtime, "_dispatch_tool", _record_dispatch)
    run_id = run_manager.launch_run(
        agent_id="copilot", prompt="x", api_key="sk", budget=RunBudget(max_tokens=1000)
    )
    row = await _await_terminal(run_id)
    assert row is not None and row.status == "error"
    assert dispatched == []
    assert row.host_actions == []


@pytest.mark.asyncio
async def test_crashed_run_detail_is_humanized(monkeypatch: pytest.MonkeyPatch) -> None:
    """R15-CODE-PLATFORM-038: a run that crashes records the humanizer's plain
    sentence as its detail, never the raw exception text."""
    crash = RuntimeError("Error code: 402 - {'error': {'message': 'Insufficient Balance'}}")

    async def _crashing_invoke(**_: Any) -> AsyncIterator[Any]:
        raise crash
        yield  # pragma: no cover — makes this an async generator

    monkeypatch.setattr(agent_runtime, "invoke_agent", _crashing_invoke)
    run_id = run_manager.launch_run(
        agent_id="copilot", prompt="x", api_key="sk", provider="deepseek", model="deepseek-chat"
    )
    row = await _await_terminal(run_id)
    assert row is not None and row.status == "error"
    assert row.detail == humanize("deepseek", crash).message
    assert "Insufficient Balance" not in row.detail
