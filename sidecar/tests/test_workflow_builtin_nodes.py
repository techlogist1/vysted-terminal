"""Tests for the v0.5.0 built-in workflow node handlers.

Each handler is exercised in isolation (direct ``await handler(inputs, config)``)
plus once end-to-end through the engine to verify registration. The
``isolated_registry`` fixture wipes the engine's handler table between
tests; the ``register_builtins`` fixture re-installs the ten built-ins
so each test starts from a known state.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import pytest

from config import DATA_DIR_ENV
from models.market import OHLCVBar, OHLCVSeries, Quote
from services import workflow_engine, workflow_nodes
from services.workflow_nodes import builtin


@pytest.fixture(autouse=True)
def isolated_registry() -> None:
    workflow_engine.reset_registry_for_tests()
    yield
    workflow_engine.reset_registry_for_tests()


@pytest.fixture
def register_builtins() -> None:
    workflow_nodes.register_all()


@pytest.fixture
def temp_data_dir(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> object:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------------------
# Helper fixtures returning realistic shapes
# ---------------------------------------------------------------------------


def _sample_quote(symbol: str = "AAPL") -> Quote:
    return Quote(
        symbol=symbol,
        price=192.5,
        change=2.5,
        change_percent=1.32,
        volume=51_000_000,
        currency="USD",
        market_state="REGULAR",
        timestamp=datetime(2026, 5, 14, tzinfo=UTC),
        provider="yfinance",
    )


def _sample_series(symbol: str = "AAPL", n: int = 30) -> OHLCVSeries:
    bars = [
        OHLCVBar(
            timestamp=datetime(2026, 4, 1 + i, tzinfo=UTC),
            open=100.0 + i,
            high=101.0 + i,
            low=99.0 + i,
            close=100.5 + i,
            volume=1_000_000 + i * 1_000,
        )
        for i in range(n)
    ]
    return OHLCVSeries(symbol=symbol, timeframe="1d", bars=bars, provider="yfinance")


# ---------------------------------------------------------------------------
# register_all + idempotency
# ---------------------------------------------------------------------------


def test_register_all_installs_ten_node_types(register_builtins: None) -> None:
    """``register_all`` registers exactly the ten built-in node ids."""
    expected = {
        "data.fetch_quote",
        "data.fetch_history",
        "compute.indicator",
        "ai.agent_invoke",
        "logic.branch",
        "logic.compare",
        "action.log",
        "action.notify_desktop",
        "transform.json_path",
        "flow.sleep",
    }
    assert expected.issubset(set(workflow_engine.registered_node_types()))


def test_register_all_is_idempotent() -> None:
    """Repeated registration does not raise and the count stays stable."""
    workflow_nodes.register_all()
    workflow_nodes.register_all()
    count = len(
        [
            t
            for t in workflow_engine.registered_node_types()
            if t in {f"{prefix}.{suffix}" for prefix, suffix in _BUILTIN_PAIRS}
        ]
    )
    assert count == 10


_BUILTIN_PAIRS = [
    ("data", "fetch_quote"),
    ("data", "fetch_history"),
    ("compute", "indicator"),
    ("ai", "agent_invoke"),
    ("logic", "branch"),
    ("logic", "compare"),
    ("action", "log"),
    ("action", "notify_desktop"),
    ("transform", "json_path"),
    ("flow", "sleep"),
]


# ---------------------------------------------------------------------------
# data.fetch_quote
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_quote_uses_config_symbol(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []

    def _fake_get_quote(symbol: str, asset_class: str = "equity") -> Quote:
        calls.append((symbol, asset_class))
        return _sample_quote(symbol)

    monkeypatch.setattr("services.provider_registry.get_quote", _fake_get_quote)
    result = await builtin.fetch_quote({}, {"symbol": "AAPL"})
    assert result["quote"]["symbol"] == "AAPL"
    assert calls == [("AAPL", "equity")]


@pytest.mark.asyncio
async def test_fetch_quote_prefers_input_symbol(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_get_quote(symbol: str, asset_class: str = "equity") -> Quote:
        return _sample_quote(symbol)

    monkeypatch.setattr("services.provider_registry.get_quote", _fake_get_quote)
    result = await builtin.fetch_quote({"symbol": "MSFT"}, {"symbol": "AAPL"})
    assert result["quote"]["symbol"] == "MSFT"


@pytest.mark.asyncio
async def test_fetch_quote_missing_symbol_raises() -> None:
    with pytest.raises(ValueError, match="missing 'symbol'"):
        await builtin.fetch_quote({}, {})


# ---------------------------------------------------------------------------
# data.fetch_history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_history_calls_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, str | None, str]] = []

    def _fake(symbol: str, timeframe: str, range_: str | None, asset_class: str) -> OHLCVSeries:
        calls.append((symbol, timeframe, range_, asset_class))
        return _sample_series(symbol)

    monkeypatch.setattr("services.provider_registry.get_history", _fake)
    result = await builtin.fetch_history({}, {"symbol": "AAPL", "period": "1y", "interval": "1d"})
    assert calls == [("AAPL", "1d", "1y", "equity")]
    assert result["series"]["symbol"] == "AAPL"
    assert len(result["series"]["bars"]) == 30


@pytest.mark.asyncio
async def test_fetch_history_missing_symbol_raises() -> None:
    with pytest.raises(ValueError, match="missing 'symbol'"):
        await builtin.fetch_history({}, {})


# ---------------------------------------------------------------------------
# compute.indicator
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_indicator_runs_rsi() -> None:
    series = _sample_series(n=30)
    # series is a live Pydantic model — the handler accepts both shapes.
    result = await builtin.compute_indicator({"series": series}, {"indicator_id": "rsi"})
    assert "indicators" in result["result"]
    assert any(s["name"] == "rsi" for s in result["result"]["indicators"])


@pytest.mark.asyncio
async def test_compute_indicator_rehydrates_from_dump() -> None:
    series = _sample_series(n=30).model_dump(mode="json")
    result = await builtin.compute_indicator({"series": series}, {"indicator_id": "sma"})
    assert any(s["name"] == "sma" for s in result["result"]["indicators"])


@pytest.mark.asyncio
async def test_compute_indicator_missing_inputs_raises() -> None:
    with pytest.raises(ValueError, match="'series'"):
        await builtin.compute_indicator({}, {"indicator_id": "rsi"})
    with pytest.raises(ValueError, match="'indicator_id'"):
        await builtin.compute_indicator({"series": _sample_series()}, {})


# ---------------------------------------------------------------------------
# ai.agent_invoke
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_invoke_aggregates_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    from models.llm import LLMDeltaEvent, LLMDoneEvent

    async def _fake_invoke(
        agent_id: str,
        prompt: str,
        **_: Any,
    ):
        yield LLMDeltaEvent(text="Hello ")
        yield LLMDeltaEvent(text="world.")
        yield LLMDoneEvent()

    monkeypatch.setattr("services.agent_runtime.invoke_agent", _fake_invoke)
    result = await builtin.agent_invoke(
        {"context": "AAPL is up"},
        {"agent_id": "buffett", "prompt_template": "Analyze: {context}"},
    )
    assert result["content"] == "Hello world."
    assert result["agent_id"] == "buffett"
    assert result["error"] is None


@pytest.mark.asyncio
async def test_agent_invoke_degrades_on_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from models.llm import LLMDoneEvent, LLMErrorEvent

    async def _fake_invoke(agent_id: str, prompt: str, **_: Any):
        yield LLMErrorEvent(message="no API key")
        yield LLMDoneEvent()

    monkeypatch.setattr("services.agent_runtime.invoke_agent", _fake_invoke)
    result = await builtin.agent_invoke({}, {"agent_id": "buffett"})
    assert result["content"] == "(no provider key configured)"
    assert result["error"] == "no API key"


@pytest.mark.asyncio
async def test_agent_invoke_requires_agent_id() -> None:
    with pytest.raises(ValueError, match="'agent_id'"):
        await builtin.agent_invoke({}, {})


# ---------------------------------------------------------------------------
# logic.branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_logic_branch_truthy_routes_value() -> None:
    result = await builtin.logic_branch({"value": "non-empty"}, {})
    assert result == {"true_path": "non-empty", "false_path": None}


@pytest.mark.asyncio
async def test_logic_branch_falsy_routes_false_path() -> None:
    result = await builtin.logic_branch({"value": ""}, {})
    assert result == {"true_path": None, "false_path": ""}


@pytest.mark.asyncio
async def test_logic_branch_gt_mode() -> None:
    result = await builtin.logic_branch({"value": 5.5, "threshold": 3.0}, {"mode": "gt"})
    assert result["true_path"] == 5.5
    assert result["false_path"] is None


@pytest.mark.asyncio
async def test_logic_branch_gt_mode_below() -> None:
    result = await builtin.logic_branch({"value": 1.0, "threshold": 3.0}, {"mode": "gt"})
    assert result["true_path"] is None
    assert result["false_path"] == 1.0


@pytest.mark.asyncio
async def test_logic_branch_gt_mode_invalid() -> None:
    with pytest.raises(ValueError, match="numeric"):
        await builtin.logic_branch({"value": "nope"}, {"mode": "gt", "threshold": 3.0})


# ---------------------------------------------------------------------------
# logic.compare
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("op", "a", "b", "expected"),
    [
        ("lt", 1, 2, True),
        ("lte", 2, 2, True),
        ("gt", 5, 2, True),
        ("gte", 2, 2, True),
        ("eq", "a", "a", True),
        ("neq", "a", "b", True),
        ("lt", 5, 2, False),
        ("eq", 1, 2, False),
    ],
)
async def test_logic_compare_ops(op: str, a: Any, b: Any, expected: bool) -> None:
    result = await builtin.logic_compare({"a": a, "b": b}, {"op": op})
    assert result == {"result": expected}


@pytest.mark.asyncio
async def test_logic_compare_unknown_op_raises() -> None:
    with pytest.raises(ValueError, match="unknown op"):
        await builtin.logic_compare({"a": 1, "b": 2}, {"op": "weird"})


@pytest.mark.asyncio
async def test_logic_compare_non_numeric_inequality_raises() -> None:
    with pytest.raises(ValueError, match="numeric"):
        await builtin.logic_compare({"a": "x", "b": "y"}, {"op": "lt"})


# ---------------------------------------------------------------------------
# action.log
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_action_log_renders_template_and_returns_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="services.workflow_nodes.builtin")
    result = await builtin.action_log(
        {"symbol": "AAPL", "price": 192.5},
        {"level": "info", "message_template": "{symbol} at {price}"},
    )
    assert result == {"logged": True, "level": "info", "message": "AAPL at 192.5"}
    assert any("AAPL at 192.5" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_action_log_handles_missing_template_keys() -> None:
    result = await builtin.action_log(
        {"symbol": "AAPL"}, {"message_template": "{symbol}/{missing}"}
    )
    # ``missing`` is rendered as the empty string by _Defaulting
    assert result["message"] == "AAPL/"


# ---------------------------------------------------------------------------
# action.notify_desktop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_action_notify_desktop_returns_intent_payload() -> None:
    result = await builtin.action_notify_desktop(
        {"symbol": "AAPL"},
        {"title": "Alert {symbol}", "message_template": "Price reached {symbol}"},
    )
    assert result["notified"] is True
    assert result["intent"] == "desktop-notification"
    assert result["title"] == "Alert AAPL"
    assert result["message"] == "Price reached AAPL"


# ---------------------------------------------------------------------------
# transform.json_path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transform_json_path_walks_dotted_path() -> None:
    payload = {"data": {"symbol": "AAPL", "price": 192.5}}
    result = await builtin.transform_json_path({"value": payload}, {"path": "data.symbol"})
    assert result == {"extracted": "AAPL"}


@pytest.mark.asyncio
async def test_transform_json_path_indexes_list() -> None:
    payload = {"items": [{"name": "first"}, {"name": "second"}]}
    result = await builtin.transform_json_path({"value": payload}, {"path": "items.1.name"})
    assert result == {"extracted": "second"}


@pytest.mark.asyncio
async def test_transform_json_path_missing_returns_none() -> None:
    result = await builtin.transform_json_path({"value": {"a": 1}}, {"path": "a.b.c"})
    assert result == {"extracted": None}


@pytest.mark.asyncio
async def test_transform_json_path_missing_path_raises() -> None:
    with pytest.raises(ValueError, match="'path'"):
        await builtin.transform_json_path({"value": {}}, {})


# ---------------------------------------------------------------------------
# flow.sleep
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flow_sleep_clamps_negative_to_zero() -> None:
    result = await builtin.flow_sleep({"value": "x"}, {"seconds": -10})
    assert result == {"value": "x", "slept": 0.0}


@pytest.mark.asyncio
async def test_flow_sleep_clamps_to_max() -> None:
    # We don't actually want to wait 300s; verify the clamp returns the cap
    # without measuring wall time. Patching asyncio.sleep keeps the test fast.
    async def _fake_sleep(seconds: float) -> None:
        # The handler must request the clamped cap, not the raw 999.
        assert seconds == 300.0

    import services.workflow_nodes.builtin as mod

    original = mod.asyncio.sleep
    mod.asyncio.sleep = _fake_sleep  # type: ignore[assignment]
    try:
        result = await builtin.flow_sleep({"value": "x"}, {"seconds": 999})
    finally:
        mod.asyncio.sleep = original  # type: ignore[assignment]
    assert result["slept"] == 300.0


@pytest.mark.asyncio
async def test_flow_sleep_runs_short_real() -> None:
    start = asyncio.get_event_loop().time()
    result = await builtin.flow_sleep({"value": 42}, {"seconds": 0.01})
    elapsed = asyncio.get_event_loop().time() - start
    assert result == {"value": 42, "slept": 0.01}
    assert elapsed >= 0.005


@pytest.mark.asyncio
async def test_flow_sleep_invalid_seconds_raises() -> None:
    with pytest.raises(ValueError, match="numeric"):
        await builtin.flow_sleep({}, {"seconds": "fast"})


# ---------------------------------------------------------------------------
# Engine integration — populated research workflow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_research_workflow_runs_end_to_end(
    register_builtins: None,
    temp_data_dir: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Phase-4 brief's research workflow shape: quote → history → indicator → agent → log."""
    from models.llm import LLMDeltaEvent, LLMDoneEvent
    from models.workflow import WorkflowEdge, WorkflowNode, WorkflowSpec

    monkeypatch.setattr(
        "services.provider_registry.get_quote", lambda symbol, ac="equity": _sample_quote(symbol)
    )
    monkeypatch.setattr(
        "services.provider_registry.get_history",
        lambda symbol, tf, range_, ac="equity": _sample_series(symbol),
    )

    async def _fake_invoke(agent_id: str, prompt: str, **_: Any):
        yield LLMDeltaEvent(text=f"Analysis for {agent_id}.")
        yield LLMDoneEvent()

    monkeypatch.setattr("services.agent_runtime.invoke_agent", _fake_invoke)

    def _n(node_id: str, type_id: str, cfg: dict[str, Any] | None = None) -> WorkflowNode:
        return WorkflowNode(
            id=node_id, type=type_id, position={"x": 0.0, "y": 0.0}, config=cfg or {}
        )

    def _e(eid: str, src: str, tgt: str, sport: str, tport: str) -> WorkflowEdge:
        return WorkflowEdge(
            id=eid,
            sourceNode=src,
            sourcePort=sport,
            targetNode=tgt,
            targetPort=tport,
        )

    spec = WorkflowSpec(
        id="wf-research",
        name="AAPL research",
        version=1,
        nodes=[
            _n("q", "data.fetch_quote", {"symbol": "AAPL"}),
            _n("h", "data.fetch_history", {"symbol": "AAPL", "interval": "1d"}),
            _n("i", "compute.indicator", {"indicator_id": "rsi"}),
            _n(
                "a",
                "ai.agent_invoke",
                {"agent_id": "buffett", "prompt_template": "{context}"},
            ),
            _n("l", "action.log", {"message_template": "done"}),
        ],
        edges=[
            _e("eh", "h", "i", "series", "series"),
            _e("ea", "i", "a", "result", "context"),
            _e("el", "a", "l", "content", "value"),
        ],
        updatedAt=0,
    )

    result = await workflow_engine.run_workflow(spec)
    assert result.status == "ok"
    by_id = {n.node_id: n for n in result.nodes}
    assert by_id["q"].outputs["quote"]["symbol"] == "AAPL"
    assert by_id["h"].outputs["series"]["symbol"] == "AAPL"
    assert by_id["i"].status == "ok"
    assert by_id["a"].outputs["content"] == "Analysis for buffett."
    assert by_id["l"].status == "ok"
