# R15-LEAD-036 lows writer result (06:54 IST)

- Outcome: fixed_untested (untested pending integration; no test was run, off-lane rule).
- Not the signed-off local-model class: this is guard replacement formatting (defect_class guard-replacement-formatting), not a figure stated with no ok tool call.
- Base 4c6dfe8c; branch worktree-agent-lows-LEAD-036-4c6dfe8; fix commit 500cd050.
- Open shape fixed: batch-22/23 cross-round fence (b22v_crossround.py): a fence opened in round 1 before a tool call stayed open when round 2's note streamed.
- Root cause: _consume_round judged each release with no knowledge of a fence an earlier release (often an earlier round) left open.
- Fix (sidecar/services/agent_runtime.py): _TurnState.fence carries (prefix, closer) of the fence released prose left open; _release judges the next release with the opener line prefixed (the hold point too); new _carry_fence strips the already-streamed prefix from kept output, prepends the closer before a replacing note, and holds back an opener whose body is still blank so a replaced block leaves no fence at all.
- Tests as source (sidecar/tests/test_agent_runtime.py, end of file): test_a_fence_opened_before_a_tool_call_leaves_no_marker_when_replaced (``` and ~~~, the b22v_crossround shape), test_a_streamed_fence_is_closed_before_the_next_rounds_note (``` and ~~~), control test_a_fence_continued_on_an_ok_result_streams_as_written.
- Checks run: python3 -m py_compile, ruff format, ruff check on the two touched files.
- Risk for the verifier: the held empty opener now makes round 2's rows a fenced block judged by the fence path (_judge_clause on the body) instead of row by row; an empty unclosed fence at turn end is now dropped instead of streamed.
