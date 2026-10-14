# set-11: batch-4/W2-workflow-backtest-feeds

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-PLATFORM-002 | POST /workflow/run, palette-shaped graph (json_path value, compare neq, branch value, sleep seconds=1, notify) | json_path extracted 333.69, branch true_path carries value, compare neq result false (no 'unknown op'), sleep slept 1.0, notify message 'AAPL 333.69', run-complete | holds |
| R15-AGENT-015 | in-process agent_invoke with config prompt_template (form key) in candidate venv, invoke_agent stubbed to capture prompt | prompt received 'Typed prompt about CTX' (not '{context}'); registry form key is prompt_template | holds |
| R15-AGENT-016 | POST /workflow/run ai.agent_invoke no creds / unknown agent / api_key in node config | node-error 'No Anthropic API key is set', run-error (not ok + sentinel); unknown agent run-error; api_key config 422 | holds |
| R15-CODE-PLATFORM-003 | same runs as AGENT-016 | failures surface as node-error + run-error, no '(no provider key configured)' sentinel | holds |
| R15-CODE-FRONTEND-006 | frontend-only repro (store/UI); backend notify output leg run live | NodeEditorPanel.tsx:413 calls useWorkflowStore.runWorkflow, no consumeSse; NodeEditorPanel.test.tsx:341 pins pendingNotifications; backend notify intent live | ci_pinned (NodeEditorPanel.test.tsx pendingNotifications toMatchObject; workflow.test.ts runWorkflow SSE) |
| R15-CODE-PLATFORM-016 | same as FRONTEND-006 | same | ci_pinned (same tests) |
| R15-DATA-040 | POST /backtest/run AAPL,MSFT,ZZZZNOTREAL | warnings ['No price history loaded for ZZZZNOTREAL ... metrics cover 2 of 3 symbols.'] | holds |
| R15-DATA-029 | _yahoo_symbol in-process; GET /earnings/{RELIANCE.NS,INFY}/estimates (with/without IN region); GET /news BDL and IN watchlist | RELIANCE.NS stays RELIANCE.NS; /earnings/RELIANCE.NS/estimates INR real data; INFY -> INFY.NS INR EPS 19.67; BDL news has no Flanigan's (0 hits in 17-item IN watchlist feed) | holds |

Adjacent note (not a regression): _yahoo_symbol('532540.BO') now returns 'TCS.BO' (BSE scrip code resolved to its symbol), where the batch-4 verifier recorded pass-through unchanged. The entry's own repro (.NS/.BO not mangled to -NS/-BO) holds.

COVERAGE: 8/8 ids raw (set-11); no raw: none
