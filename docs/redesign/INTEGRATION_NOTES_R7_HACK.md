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

---

## Pillar 2 — custom backtest strategies (`run_custom_backtest`)

### What shipped (no wiring needed)

The `custom` strategy lane EXECUTES end-to-end today: `services/backtest_dsl.py`
(restricted recursive-descent grammar — NO eval/exec; fields
open/high/low/close/volume; functions `sma|ema|rsi|highest|lowest|stdev|change`
with integer periods 1..500; arithmetic, comparisons, and/or/not; warm-up and
div-by-zero yield no-signal, never a crash), registered as strategy id
`custom` by `backtest_strategies.register_all()`, listed by
`GET /backtest/strategies`, validated by
`POST /backtest/strategies/custom/validate` (caret-positioned errors), and run
through the normal `POST /backtest/run` SSE lane with the definition riding
`BacktestRequest.params` (`{"entry": str, "exit": str, "position_size": number}`)
— zero model changes. The frontend picker's "Custom Strategy (DSL)" editor
validates inline against the validate route.

### Wiring request 3 — catalog Capability for `run_custom_backtest`

The handler ships in `sidecar/services/agent_tools/run_custom_backtest.py`
with a `register()` helper, deliberately NOT import-time-registered:
`test_capability_catalog.py::test_every_registered_handler_has_a_catalog_entry`
(SC-006) fails for any registered handler without a Capability, and
`catalog.py` is owned by another track. Land BOTH together:

1. Registration call — in `registry_v0_6_0.register_v0_6_0_tools()` (or a
   later aggregator slot), mirroring the other domains:

```python
    # R7 Track N — custom-DSL backtest authoring.
    from services.agent_tools import run_custom_backtest

    run_custom_backtest.register()
    registered.append("backtest-custom")
```

2. Catalog entry — paste into `CAPABILITY_CATALOG` next to `backtest_summary`
   (`# --- backtest ---` section):

```python
        _cap(
            "run_custom_backtest",
            description=(
                "Author and run a CUSTOM backtest strategy from declarative "
                "entry/exit rules over indicator comparisons (e.g. entry "
                "'sma(20) > sma(50)', exit 'rsi(14) > 70'). Fields: open, high, "
                "low, close, volume. Functions: sma(n), ema(n), rsi(n), "
                "highest(n), lowest(n), stdev(n), change(n). Operators: "
                "+ - * /, comparisons, and/or/not. Parsed server-side with a "
                "restricted grammar (never eval) and executed in the SIMULATED "
                "backtest engine — §6.5: no order path is reachable. Returns "
                "the digest (metrics, best/worst/recent trades) plus the runId; "
                "the full result renders in the backtest panel and resolves via "
                "backtest_summary."
            ),
            input_schema=_obj(
                {
                    "entry": {
                        "type": "string",
                        "description": "Entry rule, e.g. 'sma(20) > sma(50)'.",
                    },
                    "exit": {
                        "type": "string",
                        "description": "Exit rule, e.g. 'rsi(14) > 70'.",
                    },
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tickers to trade.",
                    },
                    "start_date": _DATE,
                    "end_date": _DATE,
                    "position_size": {
                        "type": "number",
                        "default": 100,
                        "description": "Fixed share quantity per trade.",
                    },
                    "initial_capital": {"type": "number", "default": 100000},
                    "walk_forward_slices": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 1,
                    },
                },
                ["entry", "exit", "symbols", "start_date", "end_date"],
            ),
            domain="workflows",
            read_only=True,
            kind="read_handler",
        ),
```

`read_only=True` rationale: the tool only SIMULATES (backtest engine has no
order path — §6.5) and caches the result in the in-memory `backtest_store`,
exactly like UI-started runs; it mutates no real state. If the lead prefers
the mutation gate anyway, flipping the flag needs no handler change.

Consider keeping it MCP-internal-only alongside `backtest_summary`
(`_MCP_INTERNAL_ONLY` at catalog.py ~L1071) for the same session-locality
reason (a run_id only resolves in this sidecar's memory) — or expose both;
the handler works either way.

Once wired, un-skip
`tests/test_backtest_custom.py::TestRunCustomBacktestTool::test_catalog_capability_exists`
(it asserts the exact entry above) and add `run_custom_backtest` to an agent's
`tools` allow-list (Strategy Critic is the natural fit) to make it reachable.
