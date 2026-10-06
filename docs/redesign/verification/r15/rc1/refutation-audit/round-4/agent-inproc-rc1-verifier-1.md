# rc1-verifier:1 (tie R15-AGENT-093) — arrange_layout pattern='custom' crashes the turn

Auditor: refutation audit round 4, group agent-inproc. HEAD `b06f4f70a96a94db6d5ba0fa507af59bbee1cfaa`;
`git diff --name-only 01015033 HEAD | grep -v '^docs/'` printed nothing (code tree = fix-round merge 01015033).
The fix round touched agent_runtime.py only at the research auto-brief block (_dispatch_round), not the coercion.
Own sidecar: `main.py --host 127.0.0.1 --port 52410 --data-dir <scratch>/refaudit4-agent-inproc/data` (pgid 77341), llama3.1:8b via Ollama under /tmp/vysted-r15-ollama.lock.

## Verdict: new_defect_confirmed (high) — introduced by the AGENT-093 round-2 fix 816f7cac, but NOT the AGENT-093 class

## 1. The tied entry's own class still holds at HEAD
AGENT-093 = strict-gate-rejects-coercible-args ("Coerce a numeric-looking string to its declared integer/number type at the schema gate").
```
cd sidecar && ./.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_b3_runtime_tool_args.py
8 passed in 0.06s
```
In-process (`/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/a093.py`, output below): option_chain max_strikes "5" -> 5, "5.0" -> 5 (int), "ten" -> sentinel. The coercion rule is intact.

## 2. The verifier's refutation, re-run at HEAD (in-process, the real _normalise_tool_args)
```
panels schema items: {'type': ['string', 'object']}
RAISED arrange_layout {"pattern": "custom", "panels": ["chart", "news"]} TypeError unhashable type: 'list'
RAISED arrange_layout {"pattern": "custom", "panels": [{"component": "chart"}]} TypeError unhashable type: 'list'
RAISED arrange_layout {"pattern": "custom", "panels": [{"panel": "news", "direction": "right", "reference": "chart"}]} TypeError unhashable type: 'list'
OK     arrange_layout {"pattern": "research-cockpit"} -> {"pattern": "research-cockpit"}
OK     arrange_layout {"pattern": "custom"} -> {"pattern": "custom"}
OK     arrange_layout {"pattern": "custom", "panels": []} -> {"pattern": "custom", "panels": []}
RAISED arrange_layout {"pattern": "custom", "panels": "[\"chart\",\"news\"]"} TypeError unhashable type: 'list'
OK     option_chain {"symbol": "AAPL", "max_strikes": "5"} -> {"symbol": "AAPL", "max_strikes": 5}
OK     option_chain {"symbol": "AAPL", "max_strikes": "5.0"} -> {"symbol": "AAPL", "max_strikes": 5}
OK     option_chain {"symbol": "AAPL", "max_strikes": "ten"} -> {"__vysted_invalid_args__": "invalid arguments for option_chain: 'ten' is not of type 'integer'; call again with valid args"}
LIST-TYPE arrange_layout/properties/panels/items ['string', 'object']
```
The only list-valued schema `type` in the whole catalog is arrange_layout/properties/panels/items = ["string","object"]
(sidecar/services/agent_tools/catalog.py:1447). `_coerce` (sidecar/services/agent_runtime.py:922-923):
```
    expected = schema.get("type")
    if expected in _JSON_STRING_TYPES and isinstance(value, str):
```
`expected in dict` hashes the list -> TypeError. It fires for every NON-EMPTY custom panels list (bare names, {panel,...}
objects, or a stringified array once parsed), i.e. every custom arrangement. pattern-only and panels=[] pass.
Pre-fix code (816f7cac^) iterated only top-level properties, where panels' type is "array" (hashable), so custom
layouts worked before the AGENT-093 round-2 fix: this is a regression introduced by that fix.

## 3. Live path at HEAD (llama3.1:8b, own sidecar :52410, two fresh phrasings)
Call: `sidecar/.venv/bin/python /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/inv.py '<prompt>' <out.jsonl> <autonomy>` (POST /agents/copilot/invoke, provider ollama, model llama3.1:8b, mode agent), under the lock.

(a) ask, "Arrange my workspace with a custom layout: the chart on the left and the news panel on the right." (frames, deltas omitted)
```
{"kind": "tool_result", "tool_call_id": "call_b77a943050904f07aab21c9190db5612", "name": "arrange_layout", "ok": false, "error": "invalid arguments for arrange_layout: \"[{'panel': 'chart', 'direction': 'left'}, {'panel': 'news', 'direction': 'right'}]\" is not of type 'array'; call again with valid args"}
{"kind": "error", "message": "The terminal hit an internal error.", "action": "Try again; if it keeps happening, restart Vysted.", "detail": "TypeError: unhashable type: 'list'", "code": "internal"}
{"kind": "done"}
```
(b) auto, "Lay out my panels myself-style: put the watchlist first, then the screener beside it, then the macro panel below. Use a custom arrangement, not a preset."
```
{"kind": "error", "message": "The terminal hit an internal error.", "action": "Try again; if it keeps happening, restart Vysted.", "detail": "TypeError: unhashable type: 'list'", "code": "internal"}
{"kind": "done"}
```
Sidecar log traceback (own sidecar):
```
Traceback (most recent call last):
  File "/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar/routers/agents.py", line 94, in _generator
    async for event in agent_runtime.invoke_agent(
    ...<10 lines>...
        yield _encode_event(event)
  File "/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar/services/agent_runtime.py", line 3326, in invoke_agent
    async for event in events:
        yield event
  File "/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar/services/agent_runtime.py", line 2895, in _consume_round
    _normalise_tool_args(event)
    ~~~~~~~~~~~~~~~~~~~~^^^^^^^
  File "/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar/services/agent_runtime.py", line 978, in _normalise_tool_args
    _coerce(args, cap.input_schema)
    ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar/services/agent_runtime.py", line 938, in _coerce
    value[key] = _coerce(value[key], sub_schema)
                 ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar/services/agent_runtime.py", line 942, in _coerce
    value[:] = [_coerce(item, items_schema) for item in value]
                ~~~~~~~^^^^^^^^^^^^^^^^^^^^
  File "/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar/services/agent_runtime.py", line 923, in _coerce
    if expected in _JSON_STRING_TYPES and isinstance(value, str):
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: unhashable type: 'list'
```
The router's last-resort guard (sidecar/routers/agents.py:106-111) turns it into "The terminal hit an internal error." + done:
the turn is aborted, no arrange_layout tool_use reaches the host, nothing is placed, the model's answer is cut off.

## 4. Classification
- Not 'partial' of AGENT-093: its class is a coercible argument being REJECTED by the gate. Here the arguments are already
  valid (["chart","news"]) and nothing needs coercing; the gate crashes on a union-typed schema. The numeric-string coercion
  the entry's fix_shape names holds at every depth (section 1).
- Not a duplicate: no register entry covers it (register grep for unhashable / pattern custom / arrange_layout custom: none).
- New defect, severity high (kept): a core agent flow (custom arrangement, a documented arrange_layout pattern) is broken for
  every input of the class and the whole turn dies with an internal error.

Root cause: sidecar/services/agent_runtime.py:923 (`expected in _JSON_STRING_TYPES` with a list-valued JSON-schema `type`).
Fix shape: in `_coerce`, treat a non-string `type` (a JSON-schema union) as "leave the value to the validator": return
`value` unchanged when `not isinstance(expected, str)` (a string is valid for ["string","object"]; coercing it would be wrong).
No catalog change.
Acceptance: sidecar/tests/test_b3_runtime_tool_args.py new test_union_typed_items_do_not_crash:
`_normalise_tool_args(LLMToolUseEvent(name="arrange_layout", input={"pattern":"custom","panels":["chart","news"]}))` leaves
input unchanged with no INVALID_ARGS_SENTINEL; same for `[{"panel":"news","direction":"right","reference":"chart"}]`; plus a
catalog walk asserting `_coerce` does not raise for every capability schema that has a list-valued `type`. Live re-proof:
`cd sidecar && ./.venv/bin/python /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/a093.py` prints OK for all arrange_layout custom rows, and the (a) prompt above on
llama3.1:8b yields an arrange_layout tool_use with no {"code":"internal"} error frame.

Certification-failure count: verdict does not land on a register entry -> 0 (n/a). AGENT-093 stays at 1 (round-2 rc1-verifier:5).

## 5. Fix shape checked in memory (no repo file edited)
Scratch plugin /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/plug/coercefix_plugin.py wraps _coerce to return the value unchanged for a non-string schema type.
`cd sidecar && PYTHONPATH=/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/plug ./.venv/bin/python -c 'import coercefix_plugin; exec(open("/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/a093.py").read())'`:
every arrange_layout custom row prints OK (the stringified array is still parsed to a list at the top-level "array" step),
and option_chain "5"/"5.0"/"ten" are unchanged (5, 5, sentinel).
`PYTHONPATH=/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/plug ./.venv/bin/python -m pytest -q -p no:cacheprovider -p coercefix_plugin tests/test_b3_runtime_tool_args.py tests/test_agent_runtime.py` -> 276 passed.
