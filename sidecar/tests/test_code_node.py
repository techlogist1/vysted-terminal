"""transform.code — the server evaluator is canonical (R15-CODE-PLATFORM-017).

Before this fix the node editor computed a code node's real run value with
mathjs (client) while an agent/MCP-triggered run of the SAME spec computed it
with this Python ``ast`` evaluator (server) — silently disagreeing on
``round(2.5)``, ``^`` and ternaries. The fix makes this module the ONE
evaluator for every run path; these are its parity-fixture pins (see
``code-node-run.test.ts`` for the frontend pin that the editor's run path
calls the server and never mathjs ``evaluate``).
"""

from __future__ import annotations

import asyncio

import pytest

from services.workflow_nodes.code_node import evaluate_code


def _run(expression: str, inputs: dict | None = None, bindings: list[str] | None = None):
    config = {"expression": expression, "inputs": bindings or list((inputs or {}).keys())}
    return asyncio.run(evaluate_code(inputs or {}, config))


class TestParityFixture:
    """The 3 named disagreements — canonical answers, pinned."""

    def test_round_half_away_from_zero_not_bankers_rounding(self) -> None:
        assert _run("round(2.5)")["value"] == 3
        assert _run("round(3.5)")["value"] == 4
        assert _run("round(-2.5)")["value"] == -3

    def test_round_with_decimals(self) -> None:
        assert _run("round(2.345, 2)")["value"] == pytest.approx(2.35)

    def test_caret_is_power_not_bitwise_xor(self) -> None:
        assert _run("2^3")["value"] == 8

    def test_caret_binds_tighter_than_addition_like_mathjs(self) -> None:
        # ast.BitXor precedence would have grouped this as (a + b)^2 == 25.
        assert _run("a + b^2", {"a": 2, "b": 3})["value"] == 11
        assert _run("2^3^2")["value"] == 512
        assert _run("-2^2")["value"] == -4

    def test_ternary(self) -> None:
        assert _run("a > b ? a : b", {"a": 5, "b": 2})["value"] == 5
        assert _run("a > b ? a : b", {"a": 1, "b": 2})["value"] == 2


class TestTernaryTranslation:
    def test_ternary_with_parenthesized_condition(self) -> None:
        assert _run("(a + 1 > b) ? a : b", {"a": 5, "b": 2})["value"] == 5

    def test_ternary_inside_a_call_is_not_split_early(self) -> None:
        # min(3, -1) = -1, so the condition is false and 'b' wins — a wrong
        # paren-depth tracker would instead split inside min(...)'s comma
        # args and raise a parse error.
        assert _run("min(a, b) > 0 ? a : b", {"a": 3, "b": -1})["value"] == -1

    def test_expression_with_no_ternary_is_unchanged(self) -> None:
        assert _run("a + b", {"a": 1, "b": 2})["value"] == 3


class TestExistingBehaviourUnchanged:
    """The pre-existing arithmetic/comparison/function subset stays intact."""

    def test_basic_arithmetic(self) -> None:
        assert _run("a + b * 2", {"a": 1, "b": 2})["value"] == 5

    def test_dict_member_access(self) -> None:
        assert _run("q.price", {"q": {"price": 192.5}})["value"] == 192.5

    def test_undefined_symbol_errors(self) -> None:
        with pytest.raises(ValueError, match="Undefined symbol"):
            _run("a + b", {"a": 1})

    def test_disallowed_syntax_errors(self) -> None:
        with pytest.raises(ValueError, match="disallowed syntax"):
            _run("__import__('os')")

    def test_missing_expression_errors(self) -> None:
        with pytest.raises(ValueError, match="missing 'expression'"):
            asyncio.run(evaluate_code({}, {"expression": "", "inputs": []}))
