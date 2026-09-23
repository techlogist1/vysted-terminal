# APOSD critique — workflow-engine

Worker model: `claude-opus-5-5[1m]`. Skill `aposd-critique` loaded and followed (two personas,
18 principles, specificity gate). Assessment independence: **degraded (sequential)** — no
sub-agent tool in this worker, so Assessment A (Strategic Thinker) was completed before
Assessment B (Tactical Tornado) was run. Snapshot persistence to `.aposd/critique/` skipped
(would write an unrequested file into the repo). Scope: all 26 owning files read (engine, store,
router, models, all 8 node modules, types, store, every node-editor file; tests not graded) plus
the callers that decide whether promises hold (`mcp_server.run_workflow`, `app.py`/`main.py`
registration, `desktop-notification.ts`, `macro_router`, `routers/quant.py`, `models/quant.py`,
`agent_runtime.invoke_agent`). Raw findings: `../raw/code-workflow-engine.json` (13, prefix
`COD-workflow-engine-`).

Proofs (scratch script `scratchpad/wf/proof.py`, run against the sidecar venv, no sidecar
started; mathjs checked with the repo's node_modules):

- A graph wired exactly as the palette wires it: `json_path` → `{extracted: None}`, `branch` →
  `{true_path: None, false_path: None}`, `sleep {duration_ms: 1000}` → `slept 0.0`, `compare`
  with the palette's `ne` → `unknown op 'ne'`, `notify_desktop` → `message ''`. All but compare
  report `ok`.
- `logic_branch({"value": "false"})` → `true_path: "false"` (also `"no"`, `"0"`, `"off"`).
- Spec with an unregistered type: `_validate_spec` raises, **0 events emitted**.
- `transform.code`: `round(2.5)` server 2 / mathjs 3; `2^3` server error / mathjs 8; ternary
  server parse error / mathjs 1; `7**(10**7)` blocked the loop **8.2 s**.

## Tactical Tornado verdict — HIGH risk

The engine core (`workflow_engine.py`) is small and readable; everything around it was built
teammate-by-teammate and release-by-release with no shared contract. The most damning pattern
is **the node contract exists in two hand-copied places that already disagree**: the TS palette
(`node-registry.ts:102-165,438-509`) and the Python handlers (`builtin.py`) name different ports
and config keys for 9 of the 10 built-ins, so the editor's own default graphs silently yield
`None` as success. Around it: two SSE clients for one wire (the one with the notification side
effect is dead), two `transform.code` evaluators with different arithmetic, a router that
swallows the one error the UI most needs, and a handler that turns every LLM failure into a
fake answer "so CI passes". 17 red flags: information leakage x5 (node ports/config, macro
providers x3 copies, code-node semantics, SSE parsing), comments that lie x6 (router :57,
code-node.ts:26, code-node-run.ts:12, builtin.py:42 and :158, engine docstring :3-5,
types/workflow.ts:65), special-general mixture x2 (agent sentinel, branch truthiness), dead
surface x3 (`useWorkflowStore.runWorkflow`, `resume-from`, `_encode_event_dict`), temporal
decomposition x1 (`registry_v0_6_0`).

## Design principles score — 3 pass / 7 at-risk / 8 violate (3/18)

| #   | Principle                       | Grade   | Evidence (file:line : pattern)                                                                                                                                                                                  | Consequence                                                                                                  |
| --- | ------------------------------- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| 1   | Strategic over tactical         | violate | `builtin.py:20-23,201-206` "workflows must run end-to-end in CI … degrades to a sentinel"; `NodeEditorPanel.tsx:374-379` documents a router bug instead of fixing it                                            | Test convenience shipped as product behaviour; defects fossilise as comments                                 |
| 2   | Deep modules                    | pass    | `workflow_engine.py:177-315` `run_workflow(spec, inputs, on_event)` hides wiring, concurrency, failure propagation, timing                                                                                      | Callers (router, MCP) are ~10 lines each                                                                     |
| 3   | Information hiding              | violate | node ports/config known in `node-registry.ts:102-165,438-509` AND `builtin.py:109,167,235,281,335,391,406`; nothing enforces agreement                                                                          | 9/10 built-ins mis-wired (proof)                                                                             |
| 4   | Information leakage             | violate | `macro_nodes.py:22` `_VALID_PROVIDERS` = `macro_router.py:47-52` = `node-registry.ts:364`; code-node semantics in `code_node.py:20-45` and `code-node.ts` (mathjs)                                                | Adding a provider or operator needs 3 edits; UI and agent disagree on arithmetic                             |
| 5   | General-purpose modules deeper  | at-risk | engine `NodeHandler = Callable[[dict, dict], Awaitable[dict]]` (`workflow_engine.py:47`) is general, but no port/config spec rides the registration (`:63-66`)                                                  | The general registry cannot describe its nodes, so every client re-describes them                           |
| 6   | Different layer, different abs. | at-risk | `routers/workflow.py:50-60` adds nothing but a queue + a swallow; siblings `llm.py:144`, `agents.py:109` emit an error frame                                                                                     | The router layer loses the engine's error                                                                    |
| 7   | Pull complexity downward        | violate | client re-implements cycle detection (`code-node-run.ts:76-90`) and "no terminal frame" inference (`NodeEditorPanel.tsx:435-441`) because the server does not report `WorkflowEngineError`                      | Complexity pushed up to every client; MCP path already does it right (`mcp_server.py:282-285`)               |
| 8   | Better together / apart         | violate | `src/store/workflow.ts:240-337` SSE client + intent capture vs `NodeEditorPanel.tsx:386-431,937-976` second SSE client; only the dead one feeds `desktop-notification.ts`                                        | Notify Desktop node never notifies                                                                           |
| 9   | Define errors out of existence  | violate | `builtin.py:197-206` every agent failure → `"(no provider key configured)"` status ok; `_render_template` `:136-148` blanks missing keys; `_walk_path` `:352-377` None on any miss                               | Failures become plausible data downstream                                                                    |
| 10  | Design it twice                 | violate | `transform.code` shipped twice (`code_node.py`, `code-node.ts`) without a parity check; `logic.branch` shipped without an engine "skipped" state (`workflow_engine.py:210-282`)                                  | Divergent results (round/`^`/ternary); branches cannot gate                                                  |
| 11  | Comments describe non-obvious   | violate | `routers/workflow.py:57` "engine emits run-error on validation failures" (false); `code-node.ts:26-27` + `code-node-run.ts:12-15` "no server handler" (false since `code_node.py:103`); `builtin.py:158` env key | Readers are steered away from the real behaviour                                                             |
| 12  | Comments first                  | at-risk | `workflow_engine.py:3-5` "runs downstream nodes when their inputs are available" vs gather-barrier `:260-282`; `types/workflow.ts:65` "engine refuses unknown majors" never implemented                           | Interface comments were written, then not honoured                                                           |
| 13  | Choosing names                  | at-risk | `registry_v0_6_0.register_v0_6_0_nodes` (release number, not concept); palette port `response` vs handler `content`; `flow.sleep` "milliseconds" (`node-registry.ts:162`) vs `seconds`                          | Names encode history and mislead on units                                                                    |
| 14  | Modifying existing code         | at-risk | v0.6.0 sidecar specs were added correctly (`node-registry.ts:221-349`) while the drifted v0.5.0 built-ins right above were left untouched                                                                        | Each increment fixed only its own slice                                                                      |
| 15  | Consistency                     | violate | blocking work: `builtin.py:64,87,121` `to_thread` vs `quant_nodes.py:51,62,73,84` inline; precedence idioms: `quant_nodes.py:31-36`, `research_nodes.py:47,57`, `screener_nodes.py:54-56`, `sec_nodes.py:35-42` | CPU-bound quant freezes the sidecar; 0/''/[] inputs silently replaced by config                              |
| 16  | Code should be obvious          | at-risk | `builtin.py:215-219` `in _TRUTHY_STRINGS or bool(value.strip())` — the set is dead; `workflow_engine.py:345-352` source nodes get global inputs, wired nodes do not                                               | `"false"` routes true (proof)                                                                                |
| 17  | Design for the future           | at-risk | `workflow_store.py:53-63` + `models/workflow.py:23,32,55` `extra="forbid"`, `version` unchecked; `WorkflowRunRequest.mode/resume_from` (`models/workflow.py:73-74`) accepted and ignored                       | One schema change 500s the whole saved list; dead promise of partial replay                                  |
| 18  | Performance as design           | pass    | engine keeps wiring O(N·E) on tiny graphs; I/O adapters use `to_thread`; SSE router cancels the task on disconnect (`routers/workflow.py:69-71`)                                                                  | Fine at desktop scale — the real performance defects are the at-loop CPU nodes (#15), not the engine         |

**Summary: 3 pass, 7 at risk, 8 violate (3/18 pass).**

## Overall impression

The engine itself is a decent deep module: one call, a callback, concurrency and failure
propagation hidden. The subsystem fails at its edges, where the contract between the palette,
the handlers and the clients was never made a single thing. The single biggest opportunity:
**make a node registration carry its spec** (ports, config schema, execution lane) and derive
the palette, the parity checks and the "is this runnable" answer from the sidecar. That one
change removes findings 1, 6 (partly), 11 and 13 and makes the next drift a test failure.

## What's working

- `workflow_engine.run_workflow` (`workflow_engine.py:177-315`): deep interface, failure
  propagation "upstream node failed" is explicit, callback errors cannot abort a run
  (`:162-169`). The MCP proxy (`mcp_server.py:258-285`) wraps it in 25 lines.
- The v0.6.0 sidecar node specs (`node-registry.ts:221-349`) are an honest mirror (their ports
  equal the handlers' keys) and the free-form JSON editor for nested request models
  (`node-registry.ts:351-356`) is a good "don't fake a form" call.
- The server code node is a real whitelist evaluator (`code_node.py:48-86`) — no `eval`, no
  attribute access beyond dict members; only resource bounds are missing.

## Priority issues

- **[P0] Node contract duplicated and drifted (COD-workflow-engine-1, high).** Principle:
  Information hiding. Symptom: unknown unknowns — the canvas looks wired, the run is green,
  every value is `None`. Fix: `register_node_type(type_id, handler, spec)` +
  `GET /workflow/node-types`; interim, correct the 10 TS specs and add a parity test.
- **[P1] Agent node fakes success (COD-workflow-engine-2, high).** Principle: Define errors out
  of existence (misapplied). Symptom: unknown unknowns — downstream consumes
  `"(no provider key configured)"` as an answer; no key path; `api_key` in config persists to
  `workflows.db`; no BudgetGuard. Fix: raise on `LLMErrorEvent`, thread foreground BYOK creds,
  pass `on_round_usage`, move the CI stub into test fixtures.
- **[P1] Branch cannot gate (COD-workflow-engine-3, high).** Principle: Design it twice.
  Symptom: change amplification — every side-effecting node must defend against `None`. Fix:
  engine `skipped` status + SKIP sentinel on the un-taken port; fix `_is_truthy`.
- **[P2] Router swallows validation errors (COD-workflow-engine-4, medium).** Principle: Pull
  complexity downward. Fix: emit `run-error` with the `WorkflowEngineError` text; delete the
  client's cycle re-check and guess message.
- **[P2] Dead notification path + two SSE clients (COD-workflow-engine-5, medium).** Principle:
  Better together. Fix: route panel events through `useWorkflowStore.appendEvent`, delete the
  unused `runWorkflow` client.

Also filed: two code-node evaluators diverge (6), code node CPU/memory exhaustion on the loop
(7), quant nodes block the loop (8), no timeouts + wave barrier (9), saved-list brittleness /
no versioning (10), domain-knowledge leakage in adapters (11), release-numbered registration +
dead `resume-from` (12), plugin nodes unrunnable (13).

## Persona walkthrough

**Tactical Tornado:** would keep adding nodes the way `registry_v0_6_0.py:35-63` does — a new
`*_nodes.py`, a new `register()` line, another hand-typed `NodeSpec` in `node-registry.ts`, a
fresh `inputs.get(x) or config.get(x)` chain — and patch each UI symptom client-side the way
`NodeEditorPanel.tsx:435-441` guesses at the swallowed error. Next it would add a
`"(no data)"` sentinel to a fetch node so an offline demo stays green, exactly like
`builtin.py:205-206`.

**Strategic Thinker:** would put the node's spec next to its handler (one registration call,
ports + config schema + lane), serve it, and let the palette, the parity test and the
"runnable?" check read it. The engine would grow one concept — `skipped` — so branches mean
something, and one policy — per-node timeout + `to_thread` for sync work — so no adapter has
to remember. One SSE client in the store; one `transform.code` lane on the server.

## Minor observations

- `workflow_nodes/__init__.py:60` logs a hardcoded count `11`.
- `routers/workflow.py:120-121` `_encode_event_dict` is dead ("kept for parity").
- `compute.indicator` `params`/`period` accepted by the UI (`node-registry.ts:446`) but
  "not consumed today" (`builtin.py:103-104`).
- `_render_template` (`builtin.py:130-148`) is full `str.format` — `{value.__class__}` style
  attribute walks on inputs are allowed; harmless locally, worth restricting to `format_map`
  with plain keys.

## Questions to consider

- Should a workflow node's config schema be a Pydantic model registered with the handler, so the
  quant/screener "free-form JSON" nodes get validation at save time instead of run time?
- Does the product need client-side node execution at all now that the server has a
  `transform.code` handler?
- Is the plugin `contributesNodes` capability worth keeping without a TS→sidecar execution
  bridge (Tier-4 question for the operator)?

## Run notes

Target slug: not computed (persistence skipped, see header). Ignore list: none
(`.aposd/critique/ignore.md` absent). Assessment independence: degraded (sequential).
Temp files: proof script left in the session scratchpad only.
