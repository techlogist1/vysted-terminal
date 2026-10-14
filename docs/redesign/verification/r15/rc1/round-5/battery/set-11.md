# batch-4/W2-workflow-backtest-feeds (set-11)

Candidate: 9bc600ece2ce6343a6aa48f130d7620b1466bb98, own sidecar :52352

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-015 | in-process agent_invoke call with config `prompt_template` = palette key | typed prompt reaches the agent verbatim (`Summarize AAPL Q3 earnings beat in one line`), not the `{context}` fallback | holds |
| R15-AGENT-016 | in-process agent_invoke with `config.set_request_llm_creds` publishing provider/model/api_key, invoke_agent stubbed to emit `LLMErrorEvent` | api_key + provider threaded through to invoke_agent (`sk-test-123`, `anthropic`); node raises `RuntimeError`, no more `ok`-status sentinel | holds |
| R15-CODE-FRONTEND-006 | source read: NodeEditorPanel.tsx handleRun / store/workflow.ts runWorkflow / desktop-notification.ts bridge | NodeEditorPanel now calls `useWorkflowStore.getState().runWorkflow`, whose SSE loop calls `appendEvent` for every event, feeding `pendingNotifications`, which the bridge subscribes to | holds |
| R15-CODE-PLATFORM-002 | in-process calls to builtin.transform_json_path / flow_sleep / logic_compare('neq') / action_notify_desktop with the palette's own port/config names | json_path -> {'extracted':42}; sleep -> {'slept':0.01}; compare neq -> {'result':True}; notify -> real title/message, none of the prior None/0/''/unknown-op failures | holds |
| R15-CODE-PLATFORM-003 | same stub as AGENT-016 (LLMErrorEvent from invoke_agent) | agent_invoke raises RuntimeError with the real message instead of returning ok + `(no provider key configured)` | holds |
| R15-CODE-PLATFORM-016 | same source read as CODE-FRONTEND-006 | same fix: single SSE consumer through the store feeds the bridge | holds |
| R15-DATA-029 | curl /news?symbols=RELIANCE,TCS,KAYNES,BDL&region=IN; curl /earnings/INFY.NS/estimates and /earnings/INFY/estimates?region=IN | no "Flanigan" leakage, TCS item correctly sourced "Yahoo! Finance: TCS.NS News"; bare INFY and INFY.NS estimates are byte-identical (INR, eps 19.615) | holds |
| R15-DATA-040 | POST /backtest/run with symbols [AAPL, MSFT, ZZZZZNOTREAL] | result.warnings = ["No price history loaded for ZZZZZNOTREAL ...; metrics cover 2 of 3 symbols."], run completes ok | holds |

COVERAGE: 8/8 ids raw; no raw: none.
