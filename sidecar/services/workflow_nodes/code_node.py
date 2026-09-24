"""transform.code — restricted expression evaluator (THE canonical evaluator,
R15-CODE-PLATFORM-017).

Runs every ``transform.code`` node server-side, agent/MCP-triggered or edited
in the node editor alike — the node editor's mathjs sandbox
(``code-node.ts``) is kept ONLY for the inline syntax check as you type
(``compileCodeExpression``) and the inspector's live preview; the value a
run actually produces always comes from here, so there is exactly one
evaluator, never two disagreeing on the same expression. Safe by
construction: stdlib ``ast`` parse + a node whitelist; NO eval/exec, no
attribute access beyond dict-member reads. Expressions are written in the
editor's math notation (mathjs-flavoured, e.g. ``a + b^2``, ``a > b ? a :
b``) — this module accepts that surface directly rather than Python's own
spelling of power/ternary:

- ``^`` is rewritten to Python's ``**`` (:data:`_CARET_RE`, string
  literals left alone) BEFORE ``ast.parse``, so power keeps mathjs's tight,
  right-associative binding: ``a + b^2`` is ``a + (b**2)`` and ``2^3^2`` is
  ``512``. Remapping ``ast.BitXor`` after the parse would inherit Python's
  XOR precedence (below ``+``/``*``) and silently regroup ``a + b^2``.
- ``cond ? a : b`` is rewritten (:func:`_translate_ternary`, paren-depth
  aware) into Python's own ``(a) if (cond) else (b)`` before ``ast.parse``,
  which lets :func:`_eval` handle it as a plain ``IfExp``. ``ponytail:``
  handles exactly ONE top-level ternary (the documented, tested shape) —
  a nested ternary in the false-branch is out of scope.
- ``round(x[, n])`` rounds HALF AWAY FROM ZERO (mathjs's convention, and the
  expected-since-school convention) rather than Python's builtin
  round-half-to-even (``round(2.5)`` is ``3``, never the banker's-rounding
  ``2``) — the two evaluators disagreeing here was exactly what this
  residual fixed; canonical now means canonical, not "whichever ran last".
"""

from __future__ import annotations

import ast
import math
import operator
import re
from typing import Any

from services import workflow_engine

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_CMP_OPS = {
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
}


def _round(x: Any, ndigits: Any = 0) -> float:
    """Round-half-AWAY-from-zero to ``ndigits`` decimals — see module docstring."""
    shift = 10 ** int(ndigits)
    shifted = float(x) * shift
    rounded = math.floor(shifted + 0.5) if shifted >= 0 else math.ceil(shifted - 0.5)
    return rounded / shift


_FUNCS: dict[str, Any] = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": _round,
    "sum": sum,
    "sqrt": lambda x: float(x) ** 0.5,
    "floor": lambda x: float(int(x // 1)),
    "ceil": lambda x: float(-int(-x // 1)),
}


#: A string literal (kept verbatim) or a bare ``^`` (rewritten to ``**``).
_CARET_RE = re.compile(r"""("[^"]*"|'[^']*')|\^""")


def _caret_to_pow(expr: str) -> str:
    """Rewrite mathjs's ``^`` power operator to Python's ``**``, skipping
    string literals, so the parse inherits ``**``'s precedence (see module
    docstring)."""
    return _CARET_RE.sub(lambda m: m.group(1) if m.group(1) is not None else "**", expr)


def _translate_ternary(expr: str) -> str:
    """Rewrite ONE top-level mathjs ternary (``cond ? a : b``) into Python's
    ``(a) if (cond) else (b)`` so :func:`ast.parse` can read it — Python has
    no ``?:`` token. Paren/bracket-depth aware so a ``?``/``:`` inside a
    nested call or a nested ternary is left alone; a bare expression with no
    top-level ``?`` is returned unchanged."""
    depth = 0
    q_pos = -1
    for i, ch in enumerate(expr):
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == "?" and depth == 0:
            q_pos = i
            break
    if q_pos == -1:
        return expr
    depth = 0
    c_pos = -1
    for i in range(q_pos + 1, len(expr)):
        ch = expr[i]
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == ":" and depth == 0:
            c_pos = i
            break
    if c_pos == -1:
        return expr
    cond = expr[:q_pos].strip()
    true_expr = expr[q_pos + 1 : c_pos].strip()
    false_expr = expr[c_pos + 1 :].strip()
    return f"({true_expr}) if ({cond}) else ({false_expr})"


def _eval(node: ast.AST, scope: dict[str, Any]) -> Any:
    if isinstance(node, ast.Expression):
        return _eval(node.body, scope)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, bool, str)):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in scope:
            raise ValueError(f"Undefined symbol {node.id}")
        return scope[node.id]
    if isinstance(node, ast.Attribute):  # dict member access: quote.price
        base = _eval(node.value, scope)
        if isinstance(base, dict) and node.attr in base:
            return base[node.attr]
        raise ValueError(f"Undefined symbol {node.attr}")
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval(node.left, scope), _eval(node.right, scope))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd, ast.Not)):
        value = _eval(node.operand, scope)
        if isinstance(node.op, ast.USub):
            return -value
        if isinstance(node.op, ast.UAdd):
            return +value
        return not value
    if isinstance(node, ast.Compare) and all(type(op) in _CMP_OPS for op in node.ops):
        left = _eval(node.left, scope)
        for op, comparator in zip(node.ops, node.comparators, strict=True):
            right = _eval(comparator, scope)
            if not _CMP_OPS[type(op)](left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.BoolOp):
        values = [_eval(v, scope) for v in node.values]
        return all(values) if isinstance(node.op, ast.And) else any(values)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS:
        return _FUNCS[node.func.id](*[_eval(a, scope) for a in node.args])
    if isinstance(node, ast.List):
        return [_eval(e, scope) for e in node.elts]
    if isinstance(node, ast.IfExp):  # the translated ``cond ? a : b`` ternary
        return _eval(node.body, scope) if _eval(node.test, scope) else _eval(node.orelse, scope)
    raise ValueError(f"disallowed syntax: {type(node).__name__}")


async def evaluate_code(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    expression = config.get("expression")
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("transform.code: missing 'expression'")
    bindings = config.get("inputs") or []
    scope = {name: inputs.get(name) for name in bindings if isinstance(name, str)}
    scope = {k: v for k, v in scope.items() if v is not None}
    try:
        tree = ast.parse(_translate_ternary(_caret_to_pow(expression.strip())), mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"transform.code: parse error: {exc.msg}") from exc
    return {"value": _eval(tree, scope)}


def register() -> None:
    workflow_engine.register_node_type("transform.code", evaluate_code)
