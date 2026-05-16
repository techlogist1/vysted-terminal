"""Strategy Critic end-to-end demo test (BLUEPRINT Use Case 2).

Proves the full chain Phase-4 / v0.5.0 ships:

    register strategy → run backtest → cache result →
    construct Strategy Critic invocation → mock LLM emits tool_use →
    runtime dispatches backtest_summary → tool result flows into the
    conversation → mock LLM emits final critique text → caller sees the
    full event sequence (delta-or-tool_use → tool result round-trip →
    final delta → done).

The LLM provider is mocked at the ``get_provider`` factory boundary
(same pattern as ``test_agent_runtime.py``). The mock returns two
streams in sequence: the first emits a ``tool_use`` for
``backtest_summary`` plus a ``done`` terminator; the second emits the
final critique delta + ``done``. Between the two streams the agent
runtime is expected to invoke the registered ``backtest_summary``
tool against the cached :class:`BacktestResult` and append the result
as a ``role="tool"`` message before re-calling the provider.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from models.agent import AgentContextSnapshot
from models.backtest import BacktestRequest
from models.llm import (
    LLMDeltaEvent,
    LLMDoneEvent,
    LLMMessage,
    LLMToolUseEvent,
    LLMUsage,
)
from services import agent_runtime, agent_tools, backtest_engine, backtest_store
from services.backtest_engine import (
    BacktestOrderIntent,
    BacktestStrategy,
    Bar,
    SimPortfolio,
)

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_registries() -> None:
    backtest_engine.reset_registry_for_tests()
    backtest_store.reset_for_tests()
    yield
    backtest_engine.reset_registry_for_tests()
    backtest_store.reset_for_tests()


class _BuySellStrategy(BacktestStrategy):
    """Buy on bar 1, sell on the last bar — guarantees one closed trade."""

    NAME = "e2e_buy_sell"

    def __init__(self, params: dict) -> None:
        super().__init__(params)
        self._n = 0
        self._total = int(params.get("total_bars", 5))

    async def on_bar(self, bar: Bar, portfolio: SimPortfolio) -> list[BacktestOrderIntent]:
        self._n += 1
        if self._n == 1 and not portfolio.has_position(bar.symbol):
            return [BacktestOrderIntent(symbol=bar.symbol, quantity=10, reason="entry")]
        if self._n == self._total and portfolio.has_position(bar.symbol):
            qty = portfolio.positions[bar.symbol].quantity
            return [BacktestOrderIntent(symbol=bar.symbol, quantity=-qty, reason="exit")]
        return []


def _bars() -> list[Bar]:
    closes = [100.0, 102.0, 105.0, 103.0, 108.0]
    return [
        Bar(
            timestamp=f"2025-01-{i + 1:02d}",
            symbol="AAPL",
            open=c,
            high=c + 1,
            low=c - 1,
            close=c,
            volume=1_000.0,
        )
        for i, c in enumerate(closes)
    ]


async def _bar_loader(_symbols: list[str], _start: str, _end: str) -> list[Bar]:
    return _bars()


# ---------------------------------------------------------------------------
# Mock Strategy Critic LLM provider — two-stream tool round-trip
# ---------------------------------------------------------------------------


class _MockCriticProvider:
    """Stand-in adapter that emits a tool_use then a final critique."""

    def __init__(self) -> None:
        self.calls: list[list[LLMMessage]] = []
        self.run_id: str = ""

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        model: str,  # noqa: ARG002
        api_key: str | None = None,  # noqa: ARG002
        **_kwargs: Any,
    ) -> AsyncIterator[Any]:
        # Snapshot the messages list at the time of the call — the
        # runtime mutates it between rounds.
        self.calls.append([m.model_copy() for m in messages])
        round_index = len(self.calls)
        if round_index == 1:
            # First round — emit a tool_use for backtest_summary.
            yield LLMToolUseEvent(
                tool_call_id="tu_001",
                name="backtest_summary",
                input={"run_id": self.run_id},
            )
            yield LLMDoneEvent(usage=LLMUsage(input_tokens=80, output_tokens=15))
            return
        # Second round — emit the final critique synthesis.
        yield LLMDeltaEvent(
            text=(
                "## Section 2 — Sample size and statistical power\n"
                "Backtest shows 1 closed trade with a positive P&L. "
                "One observation is not evidence; this is anecdote. "
                "Concern."
            )
        )
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=200, output_tokens=45))


# ---------------------------------------------------------------------------
# The Use Case 2 end-to-end test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_strategy_critic_use_case_2_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    """One backtest run + one mocked LLM critique = a full Use Case 2 round.

    Steps under test:

    1. Register an in-test ``e2e_buy_sell`` strategy and run a backtest
       through ``backtest_engine.run_backtest``.
    2. Cache the result in ``backtest_store`` so the foundation's
       ``backtest_summary`` tool can resolve the run id.
    3. Reload the agent runtime so the shipping ``strategy_critic``
       JSON config is registered.
    4. Patch the LLM provider factory with a two-round mock that emits
       a ``tool_use`` for ``backtest_summary`` then a critique delta.
    5. Stream the agent through ``agent_runtime.invoke_agent`` with a
       focused-panel context snapshot that includes the run id.
    6. Assert that the runtime emitted the tool_use, that it dispatched
       it correctly (the second-round mock saw a ``role="tool"``
       message with the summary payload), and that the final critique
       delta + a single terminator landed in the caller's event list.
    """
    agent_runtime.reload()

    # Step 1 — register + run a backtest.
    backtest_engine.register_strategy("e2e_buy_sell", _BuySellStrategy)
    request = BacktestRequest(
        strategyId="e2e_buy_sell",
        params={"total_bars": 5},
        symbols=["AAPL"],
        startDate="2025-01-01",
        endDate="2025-12-31",
        initialCapital=100_000.0,
    )
    result = await backtest_engine.run_backtest(request, bar_loader=_bar_loader)

    # Step 2 — cache so backtest_summary can resolve it.
    backtest_store.put(result)
    assert backtest_store.get(result.run_id) is not None

    # The foundation registered backtest_summary at import time; confirm
    # it survived the fixture reset (the reset only clears the
    # *backtest-engine* registry, not the tool registry).
    assert agent_tools.is_registered("backtest_summary")

    # Step 3 — agent runtime sees the strategy_critic JSON config.
    critic = agent_runtime.get_agent("strategy_critic")
    assert critic is not None, "strategy_critic agent must be registered"
    assert "backtest_summary" in critic.tools

    # Step 4 — patch the provider factory.
    provider = _MockCriticProvider()
    provider.run_id = result.run_id

    def factory(_pid: str, **_kw: Any) -> _MockCriticProvider:
        return provider

    monkeypatch.setattr(agent_runtime, "get_provider", factory)

    # Step 5 — invoke the agent with a context snapshot that mentions
    # the run id (so the model knows what to ask about).
    snapshot = AgentContextSnapshot(
        focused_source="backtest-panel",
        by_source={"backtest-panel": {"runId": result.run_id, "strategyId": "e2e_buy_sell"}},
        captured_at=12345,
    )

    events: list[Any] = []
    async for event in agent_runtime.invoke_agent(
        agent_id="strategy_critic",
        prompt=(
            "Please critique the strategy run identified by the focused panel. "
            "Use backtest_summary to load the run."
        ),
        context_snapshot=snapshot,
        api_key="sk-test",
    ):
        events.append(event)

    # Step 6 — assert the event sequence.
    kinds = [e.kind for e in events]
    assert kinds.count("tool_use") == 1, f"expected exactly one tool_use, got: {kinds}"
    assert kinds.count("done") == 1, f"expected exactly one terminal 'done', got: {kinds}"
    assert kinds.index("tool_use") < kinds.index("done")

    # The first event must be the tool_use; the last must be the done.
    assert events[0].kind == "tool_use"
    assert events[0].name == "backtest_summary"
    assert events[-1].kind == "done"

    # There must be at least one delta after the tool round (the critique).
    deltas = [e for e in events if e.kind == "delta"]
    assert deltas, "expected at least one critique delta after the tool round"
    assert "Sample size" in deltas[0].text  # the mock's canned critique header

    # The runtime must have made exactly two provider calls (one per round).
    assert len(provider.calls) == 2

    # The second provider call must include a tool-role message carrying
    # the dispatched backtest_summary result.
    second_call_messages = provider.calls[1]
    tool_messages = [m for m in second_call_messages if m.role == "tool"]
    assert len(tool_messages) == 1
    tool_message = tool_messages[0]
    assert tool_message.tool_call_id == "tu_001"
    # The summary payload must mention the strategy and run id.
    assert result.run_id in tool_message.content
    assert "e2e_buy_sell" in tool_message.content


@pytest.mark.asyncio
async def test_strategy_critic_handles_missing_run_id_gracefully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the tool is called with a bogus run_id the runtime keeps streaming.

    The model receives a structured ``{ok: False, error: ...}`` payload
    on the second round and is free to emit a coherent failure
    explanation. The runtime itself must not crash.
    """
    agent_runtime.reload()

    class _BogusRunProvider(_MockCriticProvider):
        async def stream_chat(
            self,
            messages: list[LLMMessage],
            model: str,
            api_key: str | None = None,
            **_kwargs: Any,
        ) -> AsyncIterator[Any]:
            self.calls.append([m.model_copy() for m in messages])
            if len(self.calls) == 1:
                yield LLMToolUseEvent(
                    tool_call_id="tu_bogus",
                    name="backtest_summary",
                    input={"run_id": "does-not-exist"},
                )
                yield LLMDoneEvent()
                return
            yield LLMDeltaEvent(text="No backtest available; cannot critique.")
            yield LLMDoneEvent()

    provider = _BogusRunProvider()
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: provider)

    events: list[Any] = []
    async for event in agent_runtime.invoke_agent(
        agent_id="strategy_critic",
        prompt="critique the latest run",
        api_key="sk-test",
    ):
        events.append(event)

    kinds = [e.kind for e in events]
    assert "tool_use" in kinds
    assert kinds[-1] == "done"
    # Tool result must surface the error to the model.
    tool_msg = next(m for m in provider.calls[1] if m.role == "tool")
    assert "no cached backtest" in tool_msg.content


@pytest.mark.asyncio
async def test_strategy_critic_unknown_tool_does_not_crash_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Provider emits an unknown tool name → runtime substitutes an error payload."""
    agent_runtime.reload()

    class _UnknownToolProvider(_MockCriticProvider):
        async def stream_chat(
            self,
            messages: list[LLMMessage],
            model: str,
            api_key: str | None = None,
            **_kwargs: Any,
        ) -> AsyncIterator[Any]:
            self.calls.append([m.model_copy() for m in messages])
            if len(self.calls) == 1:
                yield LLMToolUseEvent(
                    tool_call_id="tu_unknown",
                    name="nonexistent_tool",
                    input={},
                )
                yield LLMDoneEvent()
                return
            yield LLMDeltaEvent(text="OK, no tool available.")
            yield LLMDoneEvent()

    provider = _UnknownToolProvider()
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: provider)

    events: list[Any] = []
    async for event in agent_runtime.invoke_agent(
        agent_id="strategy_critic",
        prompt="x",
        api_key="sk-test",
    ):
        events.append(event)
    kinds = [e.kind for e in events]
    assert kinds[-1] == "done"
    tool_msg = next(m for m in provider.calls[1] if m.role == "tool")
    assert "not available" in tool_msg.content
