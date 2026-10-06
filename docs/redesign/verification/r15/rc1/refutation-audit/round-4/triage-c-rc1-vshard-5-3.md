# triage-c — rc1-vshard-5:3 (tie R15-CODE-PLATFORM-017)

Auditor: triage-c, rc1 gate round 4. Written 07:23 IST. HEAD 7c450c8e. The code tree is the same as 01015033: `git diff --name-only 01015033 HEAD | grep -v '^docs/'` prints only CHANGELOG.md.

**Verdict: partial on R15-CODE-PLATFORM-017. Severity: medium (kept).**

## Shard claim

rc1-vshard-5:3 says the code-node inspector's mathjs value preview still disagrees with the server's `evaluate_code`:
- round(1.005,2): preview 1.01, server 1.0
- log(100,10): preview 2, server disallowed Call
- nested ternary: preview 2, server parse error
- 1/0: preview Infinity, server error

## Tied entry

R15-CODE-PLATFORM-017 (fixed, batch 10, f407107; class `duplicate-client-drift`). Its title says "transform.code has two evaluators with different semantics: the editor (mathjs) and the agent/MCP path (Python ast) disagree". The repro ends: "A workflow authored and tested in the editor then run by the agent via MCP run_workflow yields a different value or fails." The fix_shape reads: "Run transform.code only on the server (keep mathjs for inline syntax preview at most) ... if both stay, a shared parity fixture both suites evaluate."

The fix (341bac93 + 6c5b49d3) makes the server evaluator canonical for every run. It also brings the server into line on the entry's three named cases: round half away from zero, `^` as power, and one top-level ternary. It keeps mathjs for the syntax check (`compileCodeExpression`) and for a live VALUE preview (`evaluateCodeExpression`, code-node-inspector.tsx:44-57 and :133-142).

`test_code_node.py` pins only the server. No fixture is evaluated by both suites: `grep -rn parity src/modules/node-editor/code-node.test.ts` returns nothing.

## Duplicate search

A register grep for mathjs, transform.code, code-node, code node and evaluate_code returns three entries:
- R15-CODE-PLATFORM-017: this entry.
- R15-CODE-PLATFORM-065: an SSE validation error is swallowed. That is a different defect.
- R15-CODE-PLATFORM-066: unbounded `**`. Also a different defect.

None of them covers the preview drift.

## Re-run at HEAD

### Client

This runs the real sandbox and the rendered inspector. It uses a scratch vitest over a `git archive HEAD` copy of src at `$S/fe` with node_modules symlinked (the test is saved as `$S/TRIAGEC_P017.test.tsx.txt`).

```
cd $S/fe && ./node_modules/.bin/vitest run src/modules/node-editor/TRIAGEC_P017.test.tsx   -> 2 passed, EXIT=0
CLIENT ["round(2.5)",{},true,{"value":3}]
CLIENT ["2^3",{},true,{"value":8}]
CLIENT ["a > 1 ? 1 : 0",{"a":3},true,{"value":1}]
CLIENT ["round(1.005, 2)",{},true,{"value":1.01}]
CLIENT ["round(2.675, 2)",{},true,{"value":2.68}]
CLIENT ["1/0",{},true,{"value":"Infinity"}]
CLIENT ["a > 1 ? 1 : a > 0 ? 2 : 3",{"a":0.5},true,{"value":2}]
CLIENT ["sqrt(-4)",{},true,{"value":{"mathjs":"Complex","re":0,"im":2}}]
CLIENT ["log(100, 10)",{},true,{"value":2}]
CLIENT ["exp(0)",{},true,{"value":1}]
CLIENT ["7 % -3",{},true,{"value":-2}]
CLIENT ["a == 1 ? 10 : 20",{"a":1},true,{"value":10}]
CLIENT ["pi * 2",{},true,{"value":6.283185307179586}]
INSPECTOR log(x,10) x=100 -> "= 2" syntax error shown: false
INSPECTOR round(x,2) x=1.005 -> "= 1.01"
INSPECTOR nested ternary x=0.5 -> "= 2" syntax error shown: false
```
(The fields are: expression, scope, compileCodeExpression ok, evaluateCodeExpression result.)

### Server

This calls `evaluate_code` in-process (sidecar/.venv):

```
SERVER ["round(2.5)", {}, {"value": 3.0}]
SERVER ["2^3", {}, {"value": 8}]
SERVER ["a > 1 ? 1 : 0", {"a": 3}, {"value": 1}]
SERVER ["round(1.005, 2)", {}, {"value": 1.0}]
SERVER ["round(2.675, 2)", {}, {"value": 2.68}]
SERVER ["1/0", {}, {"error": "ZeroDivisionError: division by zero"}]
SERVER ["a > 1 ? 1 : a > 0 ? 2 : 3", {"a": 0.5}, {"error": "ValueError: transform.code: parse error: invalid syntax"}]
SERVER ["sqrt(-4)", {}, {"value": "(1.2246467991473532e-16+2j)"}]
SERVER ["log(100, 10)", {}, {"error": "ValueError: disallowed syntax: Call"}]
SERVER ["exp(0)", {}, {"error": "ValueError: disallowed syntax: Call"}]
SERVER ["7 % -3", {}, {"value": -2}]
SERVER ["a == 1 ? 10 : 20", {"a": 1}, {"value": 10}]
SERVER ["pi * 2", {}, {"error": "ValueError: Undefined symbol pi"}]
```

### Live

The sidecar here is my own, on :52430, booted through main.py so that `register_all` registers transform.code. (A bare `uvicorn app:app` boot leaves transform.code unregistered.) One-node spec, POST /workflow/run:

```
== POST /workflow/run  expression: round(2.5)
data: {"kind":"node-output","nodeId":"c1","outputs":{"value":3.0}}
== POST /workflow/run  expression: log(100, 10)
data: {"kind":"node-error","nodeId":"c1","message":"disallowed syntax: Call"}
== POST /workflow/run  expression: round(1.005, 2)
data: {"kind":"node-output","nodeId":"c1","outputs":{"value":1.0}}
== POST /workflow/run  expression: 0.5 > 1 ? 1 : 0.5 > 0 ? 2 : 3
data: {"kind":"node-error","nodeId":"c1","message":"transform.code: parse error: invalid syntax"}
== POST /workflow/run  expression: 1/0
data: {"kind":"node-error","nodeId":"c1","message":"division by zero"}
== POST /workflow/run expression log(x, 10) inputs {x:100} (the inspector case)
data: {"kind":"node-error","nodeId":"c1","message":"disallowed syntax: Call"}
```

## Classification

The entry's own named cases no longer reproduce. round(2.5), 2^3 and a single ternary agree on both sides, and every run goes through the server. What remains is a second evaluator still inside the editor. For the expressions below it tells the author, as they type, a value the run will not produce:
- `log(x, 10)` with x=100: the preview shows "= 2" and no syntax error, but the run fails with "disallowed syntax: Call".
- `round(x, 2)` with x=1.005: the preview shows "= 1.01", but the run gives 1.0.
- A nested ternary: the preview shows "= 2" and no syntax error, but the run gives "parse error: invalid syntax".
- exp, pi, sqrt of a negative and 1/0 drift the same way.

This is exactly the entry's class (two evaluators, client drift). It also matches the entry's own failure narrative: "authored and tested in the editor ... yields a different value or fails". The fix went past the fix_shape's allowance of "syntax preview at most", and it did not add the "shared parity fixture both suites evaluate" the fix_shape requires when both evaluators stay. So the stated repro holds, but a stated part of the class does not, and the verdict is **partial** on the tie. It is not a new defect, and not a duplicate.

Severity stays **medium**. The outcome of a real run is correct and honest (node-error with the reason). The harm is an authoring-time preview that shows a value, or a clean syntax check, which the run then contradicts. That degrades a stated feature, and running the workflow is a workaround.

## Root cause

src/modules/node-editor/code-node-inspector.tsx:44-57 computes the Preview with `evaluateCodeExpression` (mathjs, src/modules/node-editor/code-node.ts:171-198). The inline check at :38 uses `compileCodeExpression` (mathjs parse, code-node.ts:153-165). The canonical evaluator is sidecar/services/workflow_nodes/code_node.py:66-75 (`_FUNCS` is eight functions), :88-122 (only one top-level ternary) and :59-63 (`_round` on raw floats). Neither the preview nor the check consults it, and no shared fixture ties the two together.

## Fix shape

Make the inspector's Preview come from the canonical evaluator instead of mathjs. The existing route already supports this: debounce a POST /workflow/run with a one-node spec `{type:'transform.code', config:{expression, inputs}}` and `inputs` set to the sample values. A source node receives the run-level inputs (workflow_engine.py:301-305). Render the node-output `value` or the node-error `message`. Drop `evaluateCodeExpression` from the inspector.

Keep mathjs parse only as a cheap "does not parse" hint. Never let it be the sole signal that an expression is valid. The server's parse error or disallowed-syntax message shown by the preview is the validity signal.

If any client-side evaluation stays, add one JSON parity fixture of [expression, scope, value|error] that both `sidecar/tests/test_code_node.py` and `src/modules/node-editor/code-node.test.ts` evaluate.

## Acceptance test

`src/modules/node-editor/code-node-inspector.test.tsx`: render CodeNodeInspector with expression `log(x, 10)`, inputs ['x'], sample x=100, and the run transport mocked to return the server's node-error. Assert that `code-node-preview` shows "disallowed syntax: Call" and never "= 2". Assert the same for `round(x, 2)` with x=1.005 (preview "= 1"), and for the nested ternary (preview shows the parse error).

`sidecar/tests/test_code_node.py` (or a shared fixture read by both suites): pin the same three expressions to their server results.

Live re-proof: the scratch vitest above must no longer report "= 2" / "= 1.01" for the log and round cases, and the POST /workflow/run commands above must agree with whatever the preview shows.

## Certification-failure count

- The R15-CODE-PLATFORM-017 note has no 'certification failures so far' clause.
- The batch VERDICTS list it as certified in batch-10, and it appears in no not_certified list.
- No REFUTATION_AUDIT file has a regression_confirmed or partial verdict for it.

Baseline 0. This partial adds 1, so the count is **1**.
