"""Custom-strategy DSL tests — parser, evaluator, engine lane, router, agent tool.

R7 hackability Pillar 2. Everything here EXECUTES: the DSL parses with a
restricted recursive-descent grammar (no eval/exec), the ``custom`` strategy
runs end-to-end through ``backtest_engine.run_backtest`` on fixture bars, the
validate route returns caret-positioned errors, and the ``run_custom_backtest``
agent tool authors + runs + caches a result ``backtest_summary`` can resolve.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from models.backtest import BacktestRequest
from services import backtest_engine, backtest_store, backtest_strategies
from services.agent_tools import run_custom_backtest as run_custom_backtest_mod
from services.backtest_dsl import (
    CustomDslStrategy,
    DslError,
    SymbolState,
    compile_rule,
    evaluate_rule,
    validate_definition,
)
from services.backtest_engine import Bar


@pytest.fixture(autouse=True)
def isolated_registries() -> None:
    backtest_engine.reset_registry_for_tests()
    backtest_store.reset_for_tests()
    yield
    backtest_engine.reset_registry_for_tests()
    backtest_store.reset_for_tests()


def _bar(close: float, ts: str = "2025-01-02", symbol: str = "AAPL") -> Bar:
    return Bar(
        timestamp=ts,
        symbol=symbol,
        open=close,
        high=close + 1,
        low=close - 1,
        close=close,
        volume=1000,
    )


def _bars(closes: list[float], symbol: str = "AAPL") -> list[Bar]:
    return [
        _bar(close, ts=f"2025-01-{day + 1:02d}", symbol=symbol) for day, close in enumerate(closes)
    ]


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class TestParser:
    def test_simple_comparison_compiles(self) -> None:
        rule = compile_rule("sma(20) > sma(50)")
        assert rule.indicators == frozenset({("sma", 20), ("sma", 50)})
        assert rule.required_bars == 50

    def test_boolean_composition_and_fields(self) -> None:
        rule = compile_rule("close > sma(10) and rsi(14) < 30 or not (volume > 1000)")
        assert ("rsi", 14) in rule.indicators
        # rsi warm-up needs period+1 bars.
        assert rule.required_bars == 15

    def test_arithmetic_inside_comparison(self) -> None:
        rule = compile_rule("(close - sma(5)) / sma(5) > 0.02")
        assert rule.indicators == frozenset({("sma", 5)})

    def test_unknown_identifier_reports_position(self) -> None:
        with pytest.raises(DslError) as exc_info:
            compile_rule("close > smaa(20)")
        assert exc_info.value.position == 8
        assert "smaa" in str(exc_info.value)

    def test_unexpected_character_reports_position(self) -> None:
        with pytest.raises(DslError) as exc_info:
            compile_rule("close > 100 $")
        assert exc_info.value.position == 12

    def test_non_integer_period_rejected(self) -> None:
        with pytest.raises(DslError, match="integer period"):
            compile_rule("sma(20.5) > 1")

    def test_period_bounds_enforced(self) -> None:
        with pytest.raises(DslError, match="1..500"):
            compile_rule("sma(501) > 1")
        with pytest.raises(DslError, match="1..500"):
            compile_rule("sma(0) > 1")

    def test_unbalanced_parens(self) -> None:
        with pytest.raises(DslError, match="expected"):
            compile_rule("(close > 100")

    def test_non_boolean_rule_rejected(self) -> None:
        with pytest.raises(DslError, match="comparison or boolean"):
            compile_rule("sma(20) + 5")

    def test_chained_comparison_rejected(self) -> None:
        with pytest.raises(DslError, match="chained comparisons"):
            compile_rule("10 < close < 20")

    def test_empty_rule_rejected(self) -> None:
        with pytest.raises(DslError, match="empty rule"):
            compile_rule("   ")

    def test_trailing_garbage_rejected(self) -> None:
        with pytest.raises(DslError, match="unexpected"):
            compile_rule("close > 100 close")

    def test_no_python_escape_hatches(self) -> None:
        # Attribute access, imports, subscripts, calls on fields: all parse errors.
        for hostile in (
            "__import__('os').system('true') > 0",
            "close.__class__ > 0",
            "open('/etc/passwd') > 0",  # 'open' is a FIELD, not callable
            "exec(1) > 0",
            "close[0] > 1",
        ):
            with pytest.raises(DslError):
                compile_rule(hostile)

    def test_paren_recursion_bomb_is_a_dsl_error(self) -> None:
        # The reviewer's exact adversarial input: 5000 nested parens must be a
        # positioned DslError (the token cap fires first at this size), never
        # a RecursionError escaping compile_rule or validate_definition
        # ("Never raises" is a contract, not a hope).
        bomb = "(" * 5000 + "close > 1" + ")" * 5000
        with pytest.raises(DslError, match="too long"):
            compile_rule(bomb)
        report = validate_definition({"entry": bomb, "exit": "rsi(14) > 70"})
        assert report["ok"] is False
        assert report["errors"][0]["rule"] == "entry"
        assert report["errors"][0]["position"] is not None

    def test_nesting_depth_cap_fires_under_the_token_cap(self) -> None:
        # 50 nested parens is only ~109 tokens — small enough to pass the
        # token cap, deep enough that ONLY the depth budget stops it.
        with pytest.raises(DslError, match="too deeply nested"):
            compile_rule("(" * 50 + "close > 1" + ")" * 50)

    def test_not_and_unary_minus_chains_are_depth_capped(self) -> None:
        # `not` and unary-minus recurse in the parser too — same budget.
        with pytest.raises(DslError, match="too deeply nested"):
            compile_rule("not " * 50 + "close > 1")
        with pytest.raises(DslError, match="too deeply nested"):
            compile_rule("-" * 50 + "close > 1")

    def test_token_flood_is_a_dsl_error(self) -> None:
        # A flat `+ 1` spine parses iteratively but builds a deep left-leaning
        # BinOp chain that would recurse in _collect_indicators/_eval — the
        # token cap rejects it before any AST exists.
        with pytest.raises(DslError, match="too long"):
            compile_rule("close " + "+ 1 " * 5000 + "> 1")

    def test_legal_nesting_and_width_still_parse(self) -> None:
        # Depth under the cap parses fine...
        deep = "(" * 10 + "close > 1" + ")" * 10
        assert compile_rule(deep).required_bars == 1
        # ...and sibling groups don't accumulate depth (budget is released).
        wide = " and ".join("(close > sma(2))" for _ in range(25))
        assert compile_rule(wide).indicators == frozenset({("sma", 2)})


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


class TestEvaluator:
    def test_warmup_yields_no_signal(self) -> None:
        rule = compile_rule("sma(3) > 100")
        state = SymbolState(rule.indicators)
        for close in (101.0, 102.0):
            bar = _bar(close)
            state.update(bar)
            assert evaluate_rule(rule, bar, state) is False  # still warming up

    def test_sma_fires_after_window(self) -> None:
        rule = compile_rule("sma(3) > 100")
        state = SymbolState(rule.indicators)
        result = False
        for close in (101.0, 102.0, 103.0):
            bar = _bar(close)
            state.update(bar)
            result = evaluate_rule(rule, bar, state)
        assert result is True  # mean(101,102,103) = 102 > 100

    def test_field_reference_reads_current_bar(self) -> None:
        rule = compile_rule("close > 104")
        state = SymbolState(rule.indicators)
        bar = _bar(105.0)
        state.update(bar)
        assert evaluate_rule(rule, bar, state) is True

    def test_division_by_zero_suppresses_signal(self) -> None:
        rule = compile_rule("close / change(1) > 0")
        state = SymbolState(rule.indicators)
        first = _bar(100.0)
        state.update(first)
        flat = _bar(100.0, ts="2025-01-03")
        state.update(flat)
        # change(1) == 0 → division yields None → no signal, no crash.
        assert evaluate_rule(rule, flat, state) is False

    def test_rsi_extremes(self) -> None:
        # Monotonic rally → RSI 100 (avg loss 0).
        rule = compile_rule("rsi(3) > 90")
        state = SymbolState(rule.indicators)
        fired = False
        for i, close in enumerate((100.0, 101.0, 102.0, 103.0, 104.0)):
            bar = _bar(close, ts=f"2025-01-{i + 2:02d}")
            state.update(bar)
            fired = evaluate_rule(rule, bar, state)
        assert fired is True

    def test_highest_lowest_change(self) -> None:
        rule = compile_rule("close >= highest(3) - 1 and change(2) > 0 and close > lowest(2)")
        state = SymbolState(rule.indicators)
        fired = False
        for i, close in enumerate((100.0, 101.0, 103.0)):
            bar = _bar(close, ts=f"2025-01-{i + 2:02d}")
            state.update(bar)
            fired = evaluate_rule(rule, bar, state)
        # close=103, highs=(101,102,104): highest=104, 103 >= 103 ✓;
        # change(2)=103-100=3 ✓; lowest(2)=min(100,102)... lows are close-1.
        assert fired is True


# ---------------------------------------------------------------------------
# validate_definition
# ---------------------------------------------------------------------------


class TestValidateDefinition:
    def test_ok_reports_indicators_and_warmup(self) -> None:
        report = validate_definition({"entry": "sma(20) > sma(50)", "exit": "rsi(14) > 70"})
        assert report["ok"] is True
        assert report["indicators"] == ["rsi(14)", "sma(20)", "sma(50)"]
        assert report["requiredBars"] == 50

    def test_missing_rules_and_bad_size(self) -> None:
        report = validate_definition({"entry": "", "position_size": -5})
        assert report["ok"] is False
        rules = {err["rule"] for err in report["errors"]}
        assert rules == {"entry", "exit", "position_size"}

    def test_parse_error_carries_rule_and_position(self) -> None:
        report = validate_definition({"entry": "sma(20) >", "exit": "bogus > 1"})
        assert report["ok"] is False
        by_rule = {err["rule"]: err for err in report["errors"]}
        assert by_rule["entry"]["position"] == 9  # end-of-expression
        assert by_rule["exit"]["position"] == 0
        assert "bogus" in by_rule["exit"]["message"]


# ---------------------------------------------------------------------------
# CustomDslStrategy through the real engine
# ---------------------------------------------------------------------------


class TestCustomStrategyEndToEnd:
    @pytest.mark.asyncio
    async def test_round_trip_trade_executes(self) -> None:
        backtest_strategies.register_all()
        # Rise above the 3-bar SMA, then collapse below it: one full round trip.
        closes = [100.0, 100.0, 100.0, 110.0, 112.0, 90.0, 85.0]

        async def loader(_s: list[str], _a: str, _b: str) -> list[Bar]:
            return _bars(closes)

        request = BacktestRequest(
            strategyId="custom",
            params={"entry": "close > sma(3)", "exit": "close < sma(3)", "position_size": 10},
            symbols=["AAPL"],
            startDate="2025-01-01",
            endDate="2025-01-08",
            initialCapital=10_000.0,
        )
        result = await backtest_engine.run_backtest(request, bar_loader=loader)
        assert result.strategy_id == "custom"
        assert len(result.trades) >= 1
        closed = [t for t in result.trades if t.pnl is not None]
        assert closed, "expected at least one closed round-trip trade"
        assert closed[0].close_reason == "exit: close < sma(3)"
        assert result.metrics.trade_count == len(closed)

    @pytest.mark.asyncio
    async def test_bad_definition_raises_with_message(self) -> None:
        with pytest.raises(DslError, match="entry rule"):
            CustomDslStrategy({"entry": "sma(", "exit": "rsi(14) > 70"})

    @pytest.mark.asyncio
    async def test_per_symbol_state_is_isolated(self) -> None:
        strategy = CustomDslStrategy(
            {"entry": "close > sma(2)", "exit": "close < sma(2)", "position_size": 1}
        )
        from services.backtest_engine import SimPortfolio

        portfolio = SimPortfolio(cash=1_000.0)
        # Feed AAPL two bars (warm), MSFT only one (cold) — MSFT must not signal.
        for bar in _bars([100.0, 110.0], symbol="AAPL"):
            intents = await strategy.on_bar(bar, portfolio)
        assert intents and intents[0].symbol == "AAPL"
        cold = _bar(500.0, symbol="MSFT")
        assert await strategy.on_bar(cold, portfolio) == []


# ---------------------------------------------------------------------------
# Router — validate endpoint + the custom lane on /backtest/run
# ---------------------------------------------------------------------------


class TestRouter:
    def test_validate_ok(self, client: TestClient) -> None:
        response = client.post(
            "/backtest/strategies/custom/validate",
            json={"entry": "sma(20) > sma(50)", "exit": "rsi(14) > 70", "positionSize": 100},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["errors"] == []
        assert body["indicators"] == ["rsi(14)", "sma(20)", "sma(50)"]
        assert body["requiredBars"] == 50

    def test_validate_surfaces_caret_position(self, client: TestClient) -> None:
        response = client.post(
            "/backtest/strategies/custom/validate",
            json={"entry": "close > smaa(20)", "exit": "rsi(14) > 70"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is False
        assert body["errors"][0]["rule"] == "entry"
        assert body["errors"][0]["position"] == 8

    def test_validate_survives_paren_recursion_bomb(self, client: TestClient) -> None:
        # Reviewer's live repro: this exact body used to 500 (RecursionError
        # escaping validate_definition). Contract: 200 + ok:false, always.
        bomb = "(" * 5000 + "close > 1" + ")" * 5000
        response = client.post(
            "/backtest/strategies/custom/validate",
            json={"entry": bomb, "exit": "rsi(14) > 70"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is False
        assert body["errors"][0]["rule"] == "entry"
        assert body["errors"][0]["position"] is not None

    def test_custom_spec_listed_once_registered(self, client: TestClient) -> None:
        backtest_strategies.register_all()
        response = client.get("/backtest/strategies")
        assert response.status_code == 200
        specs = {spec["id"]: spec for spec in response.json()["strategies"]}
        assert "custom" in specs
        assert "entry" in specs["custom"]["paramsSchema"]["properties"]

    def test_run_route_executes_custom_lane(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        backtest_strategies.register_all()
        closes = [100.0, 100.0, 100.0, 110.0, 112.0, 90.0, 85.0]

        async def fake_loader(_s: list[str], _a: str, _b: str) -> list[Bar]:
            return _bars(closes)

        import routers.backtest as backtest_router

        monkeypatch.setattr(backtest_router, "load_bars", fake_loader)
        response = client.post(
            "/backtest/run",
            json={
                "strategyId": "custom",
                "params": {"entry": "close > sma(3)", "exit": "close < sma(3)"},
                "symbols": ["AAPL"],
                "startDate": "2025-01-01",
                "endDate": "2025-01-08",
                "initialCapital": 100000,
            },
        )
        assert response.status_code == 200
        frames = [
            json.loads(line[len("data: ") :])
            for line in response.text.splitlines()
            if line.startswith("data: ")
        ]
        kinds = [frame["kind"] for frame in frames]
        assert kinds[0] == "run-start"
        assert kinds[-1] == "run-complete"
        result = frames[-1]["result"]
        assert result["strategyId"] == "custom"
        assert result["metrics"]["tradeCount"] >= 1

    def test_run_route_surfaces_dsl_error_as_run_error(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        backtest_strategies.register_all()

        async def fake_loader(_s: list[str], _a: str, _b: str) -> list[Bar]:
            return _bars([100.0, 101.0])

        import routers.backtest as backtest_router

        monkeypatch.setattr(backtest_router, "load_bars", fake_loader)
        response = client.post(
            "/backtest/run",
            json={
                "strategyId": "custom",
                "params": {"entry": "close > smaa(3)", "exit": "close < sma(3)"},
                "symbols": ["AAPL"],
                "startDate": "2025-01-01",
                "endDate": "2025-01-08",
            },
        )
        assert response.status_code == 200
        frames = [
            json.loads(line[len("data: ") :])
            for line in response.text.splitlines()
            if line.startswith("data: ")
        ]
        assert frames[-1]["kind"] == "run-error"
        assert "smaa" in frames[-1]["message"]


# ---------------------------------------------------------------------------
# run_custom_backtest agent tool
# ---------------------------------------------------------------------------


class TestRunCustomBacktestTool:
    @pytest.mark.asyncio
    async def test_authors_runs_and_caches(self, monkeypatch: pytest.MonkeyPatch) -> None:
        backtest_strategies.register_all()
        closes = [100.0, 100.0, 100.0, 110.0, 112.0, 90.0, 85.0]

        async def fake_loader(_s: list[str], _a: str, _b: str) -> list[Bar]:
            return _bars(closes)

        monkeypatch.setattr(run_custom_backtest_mod, "load_bars", fake_loader)
        out = await run_custom_backtest_mod._run_custom_backtest(
            {
                "entry": "close > sma(3)",
                "exit": "close < sma(3)",
                "symbols": ["aapl"],
                "start_date": "2025-01-01",
                "end_date": "2025-01-08",
                "position_size": 10,
            }
        )
        assert out["ok"] is True
        assert out["strategyId"] == "custom"
        assert out["symbols"] == ["AAPL"]
        assert out["indicators"] == ["sma(3)"]
        assert out["metrics"]["tradeCount"] >= 1
        # The run landed in the shared store — backtest_summary + the
        # frontend's GET /backtest/runs/{id} both resolve it.
        cached = backtest_store.get(out["runId"])
        assert cached is not None
        assert cached.request.params["entry"] == "close > sma(3)"

    @pytest.mark.asyncio
    async def test_invalid_definition_returns_errors_not_exception(self) -> None:
        out = await run_custom_backtest_mod._run_custom_backtest(
            {
                "entry": "close > smaa(3)",
                "exit": "rsi(14) > 70",
                "symbols": ["AAPL"],
                "start_date": "2025-01-01",
                "end_date": "2025-01-08",
            }
        )
        assert out["ok"] is False
        assert out["errors"][0]["rule"] == "entry"
        assert out["errors"][0]["position"] == 8

    @pytest.mark.asyncio
    async def test_missing_symbols_rejected(self) -> None:
        out = await run_custom_backtest_mod._run_custom_backtest(
            {"entry": "close > sma(3)", "exit": "close < sma(3)", "symbols": []}
        )
        assert out["ok"] is False
        assert "symbols" in out["error"]

    def test_register_binds_handler(self) -> None:
        from services import agent_tools

        agent_tools.reset_for_tests()
        run_custom_backtest_mod.register()
        assert agent_tools.is_registered("run_custom_backtest")
        agent_tools.reset_for_tests()

    @pytest.mark.skip(reason="lead wires catalog entry")
    def test_catalog_capability_exists(self) -> None:
        """Passes once the lead lands the Capability from INTEGRATION_NOTES."""
        from services.agent_tools.catalog import CAPABILITY_CATALOG

        cap = CAPABILITY_CATALOG["run_custom_backtest"]
        assert cap.kind == "read_handler"
        assert cap.read_only is True
        required = set(cap.input_schema.get("required", []))
        assert {"entry", "exit", "symbols", "start_date", "end_date"} <= required
