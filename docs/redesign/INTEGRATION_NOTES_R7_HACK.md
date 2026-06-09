# Integration notes — R7 Track N (hackability), worktree `r7-hack`

Cross-boundary wiring this track needs from the lead. Each entry is exact and
paste-ready; files named here are owned by other tracks per the brief.

---

## Pillar 1 — code node (`transform.code`)

### What shipped (no wiring needed)

The node-editor run path executes `transform.code` CLIENT-side tonight:
`NodeEditorPanel.handleRun` partitions the spec (`code-node-run.ts
partitionWorkflow`), POSTs only the server-executable sub-spec to
`/workflow/run`, then evaluates code nodes in the sandboxed mathjs instance
(`code-node.ts`) from the streamed `node-output` frames, in topological order,
with engine-parity `upstream node failed` propagation. Code→server edges are
rejected pre-run with an honest message. Serializable spec:

```json
{
  "id": "c1",
  "type": "transform.code",
  "position": { "x": 0, "y": 0 },
  "config": { "expression": "quote.price * qty", "inputs": ["quote", "qty"] }
}
```

Each `inputs[i]` is BOTH an input port id and an expression variable. Output:
one port `value`.

### Wiring request 1 — server-side parity handler (unblocks agent/MCP runs)

`services/mcp_server.py run_workflow(spec_json)` calls
`workflow_engine.run_workflow` directly, and `_validate_spec` rejects any
unregistered type — so an AGENT-authored spec containing `transform.code`
fails server-side until a Python handler registers. Paste-ready module
(suggested `sidecar/services/workflow_nodes/code_node.py` — owned by the
workflow-nodes track, NOT r7-hack):

```python
"""transform.code — restricted expression evaluator (mathjs-frontend parity).

Safe: stdlib ast parse + node whitelist; NO eval/exec/attribute access on
arbitrary objects. Dict inputs support dotted access via Subscript-free
`a.b` rewriting handled below (Attribute on dict values only).
"""

from __future__ import annotations

import ast
import operator
from typing import Any

from services import workflow_engine

_BIN_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_CMP_OPS = {
    ast.Gt: operator.gt, ast.GtE: operator.ge, ast.Lt: operator.lt,
    ast.LtE: operator.le, ast.Eq: operator.eq, ast.NotEq: operator.ne,
}
_FUNCS: dict[str, Any] = {
    "abs": abs, "min": min, "max": max, "round": round, "sum": sum,
    "sqrt": lambda x: float(x) ** 0.5, "floor": lambda x: float(int(x // 1)),
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
        return -value if isinstance(node.op, ast.USub) else +value if isinstance(node.op, ast.UAdd) else not value
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
```

Registration line (in `workflow_nodes/__init__.py` next to the v0.5.0 calls,
or a `register()` call from `registry_v0_6_0.py`):

```python
workflow_engine.register_node_type("transform.code", code_node.evaluate_code)
```

Grammar caveat: the Python lane accepts `and/or/not` like mathjs; mathjs-only
sugar (`^` as power, matrices, units) is NOT in the Python subset — keep
agent-authored expressions to arithmetic/comparison/boolean/`abs|min|max|
round|sum|sqrt|floor|ceil` for cross-lane parity. Once this lands, the
client-side seam retires by deleting the partition in ONE place:
`src/modules/node-editor/code-node-run.ts partitionWorkflow` (return
`{server: spec, codeOrder: []}`); everything else is untouched.

### Wiring request 2 — agent surface for authoring workflows

There is NO tool today for the agent to CREATE or UPDATE a saved workflow:
MCP has `run_workflow(spec_json)` + `list_workflows` (`services/mcp_server.py`
~L259/L289) and the catalog has no workflow-authoring capability. Per CLAUDE.md
the workflow tools are **hand-written + MCP-only** (NOT catalog `read_handler`s)
— so this is an mcp_server.py entry, not a `catalog.py` Capability. Paste-ready,
mirroring `list_workflows`' dict-wrap + error shape:

```python
@mcp.tool
async def save_workflow(spec_json: str) -> dict[str, Any]:
    """Create or update a saved workflow. Maps to POST /workflow/save.

    ``spec_json`` is a JSON-encoded WorkflowSpec — the same shape
    ``run_workflow`` accepts, including ``transform.code`` nodes
    (``config = {"expression": str, "inputs": [str, ...]}``).
    """
    from models.workflow import WorkflowSpec

    try:
        spec = WorkflowSpec.model_validate_json(spec_json)
    except Exception as exc:  # noqa: BLE001 — surface parse errors cleanly
        return {"ok": False, "error": f"invalid workflow spec: {exc}"}
    async with _internal_client() as client:
        response = await client.post(
            "/workflow/save", json=spec.model_dump(mode="json", by_alias=True)
        )
        response.raise_for_status()
        return {"ok": True, "workflow": response.json()}
```

Note: `POST /workflow/save` (`routers/workflow.py`) does not validate node
types, so saving code-node specs already works today; only RUNNING them
server-side needs wiring request 1.
