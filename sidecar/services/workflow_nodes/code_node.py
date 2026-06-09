"""transform.code — restricted expression evaluator (mathjs-frontend parity).

The R7 hackability track ships the code node with CLIENT-side mathjs execution
(the node editor partitions the spec); this Python lane gives AGENT/MCP-run
workflows the same node server-side. Safe by construction: stdlib ``ast`` parse
+ a node whitelist; NO eval/exec, no attribute access beyond dict-member reads.
Keep agent-authored expressions to arithmetic / comparison / boolean /
``abs|min|max|round|sum|sqrt|floor|ceil`` for cross-lane parity (mathjs-only
sugar — ``^`` as power, matrices, units — is not in this subset).
"""

from __future__ import annotations

import ast
import operator
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
_FUNCS: dict[str, Any] = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "sum": sum,
    "sqrt": lambda x: float(x) ** 0.5,
    "floor": lambda x: float(int(x // 1)),
    "ceil": lambda x: float(-int(-x // 1)),
}


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
    raise ValueError(f"disallowed syntax: {type(node).__name__}")


async def evaluate_code(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    expression = config.get("expression")
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("transform.code: missing 'expression'")
    bindings = config.get("inputs") or []
    scope = {name: inputs.get(name) for name in bindings if isinstance(name, str)}
    scope = {k: v for k, v in scope.items() if v is not None}
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"transform.code: parse error: {exc.msg}") from exc
    return {"value": _eval(tree, scope)}


def register() -> None:
    workflow_engine.register_node_type("transform.code", evaluate_code)
