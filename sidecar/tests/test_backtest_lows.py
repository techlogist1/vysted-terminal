"""Pinning tests for the P1/W1 backtest lows batch.

R15-AGENT-079, R15-CODE-PLATFORM-034, R15-CODE-PLATFORM-035,
R15-CODE-PLATFORM-036 — see docs/redesign/verification/vysted-r15-register.json.
"""

from __future__ import annotations

from services.backtest_dsl import compile_rule

# ---------------------------------------------------------------------------
# R15-AGENT-079 — keyword case-folding
# ---------------------------------------------------------------------------


def test_uppercase_and_or_parse_like_lowercase() -> None:
    lower = compile_rule("sma(20) > 50 and close > 1")
    upper = compile_rule("SMA(20) > 50 AND close > 1")
    assert upper.indicators == lower.indicators
    assert upper.required_bars == lower.required_bars
