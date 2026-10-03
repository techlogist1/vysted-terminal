# set-17 batch-5/W3-agent-runtime-chat (rc1-battery-20, candidate ace7dd76)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-040 | in-process _coerce_history + invoke_agent on 12-msg history (raw: raw/set-17/R15-AGENT-040.txt) | folded=4, summary message sent to provider keeps turn-1 'FY26 guidance' constraint and FAILED tool trailer; 'Older turns summarised' notice emitted | holds |
| R15-AGENT-026 | invoke_agent with fake provider: length, max_tokens, no-finish-with-text, empty round (raw: raw/set-17/R15-AGENT-026.txt) | length/max_tokens -> notice step 'hit the model's output limit'; no-finish -> error code truncated; empty -> error empty_response | holds |
| R15-RESEARCH-014 | deep.synthesis_llm through real oneshot seam, finish max_tokens/length/stop (raw: raw/set-17/R15-RESEARCH-014.txt) | truncated True for max_tokens/length, False for stop/end_turn; Anthropic ceiling 128000 not 4096 | holds |
| R15-AGENT-025 | hanging provider with fast clock (raw: raw/set-17/R15-AGENT-025.txt) | 4 heartbeats then error code provider_idle; planner call carries _PLANNER_TIMEOUT_SECONDS=20 | holds |
| R15-AGENT-048 | OpenAIProvider._resolve_tool_events, 5 invalid calls, oneshot stubbed (raw: raw/set-17/R15-AGENT-048.txt) | 2 repair calls (cap), each timeout=30s and usage ledgered; other 3 get invalid-args sentinel | holds |
| R15-AGENT-033 | invoke_agent set_chart_symbol BDL, autonomy ask vs auto (raw: raw/set-17/R15-AGENT-033.txt) | ask -> notice 'Staged for your review, not applied yet: set_chart_symbol BDL' and tool result awaiting_user_review; auto -> no notice, dispatched_unconfirmed | holds |
| R15-AGENT-031 | invoke_agent publish_brief with ack none/kept_previous/failed; old regex vs notice kind (raw: raw/set-17/R15-AGENT-031.txt) | all three divergences are step_kind notice; old regex misses 2 of them but isRuntimeNotice('notice') true | holds |
| R15-UI-054 | same probe, kept_previous ack (raw: raw/set-17/R15-UI-054.txt) | kept_previous emitted as notice kind; frontend matches by kind (isRuntimeNotice), ChatSidebar onResearchStep routes to addNotice | holds |
