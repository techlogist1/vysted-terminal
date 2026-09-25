"""Pinning tests for the P1/W1 backtest lows batch.

R15-AGENT-079, R15-CODE-PLATFORM-034, R15-CODE-PLATFORM-035,
R15-CODE-PLATFORM-036 — see docs/redesign/verification/vysted-r15-register.json.
"""

from __future__ import annotations

import pytest
from services import backtest_dsl
from services.backtest_dsl import CustomDslStrategy, compile_rule

# ---------------------------------------------------------------------------
# R15-AGENT-079 — keyword case-folding
# ---------------------------------------------------------------------------


def test_uppercase_and_or_parse_like_lowercase() -> None:
    lower = compile_rule("sma(20) > 50 and close > 1")
    upper = compile_rule("SMA(20) > 50 AND close > 1")
    assert upper.indicators == lower.indicators
    assert upper.required_bars == lower.required_bars


# ---------------------------------------------------------------------------
# R15-CODE-PLATFORM-036 — CustomDslStrategy compiles each rule once
# ---------------------------------------------------------------------------


def test_each_rule_compiled_once(monkeypatch: pytest.MonkeyPatch) -> None:
    real_compile_rule = backtest_dsl.compile_rule
    calls = {"n": 0}

    def counting_compile_rule(source: str):
        calls["n"] += 1
        return real_compile_rule(source)

    monkeypatch.setattr(backtest_dsl, "compile_rule", counting_compile_rule)
    strategy = CustomDslStrategy({"entry": "sma(20) > sma(50)", "exit": "rsi(14) > 70"})

    assert calls["n"] == 2
    assert strategy.entry.source == "sma(20) > sma(50)"
    assert strategy.exit.source == "rsi(14) > 70"
