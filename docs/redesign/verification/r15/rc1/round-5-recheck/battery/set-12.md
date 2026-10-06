# batch-4/W2-workflow-backtest-feeds — rc1-battery-11 (shard 11)

Candidate sha `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. Method: live
`POST /workflow/run` / `POST /backtest/run` / market-data GETs against
rc1-battery-11's own sidecar (`:52351`, sourced from the candidate worktree,
own data dir seeded from the round's keyless snapshot), building graphs
directly from the palette's own specs (`node-registry.ts`
`BUILT_IN_NODE_SPECS`/`BUILT_IN_NODE_CONFIG_FIELDS`), plus a source read of
`NodeEditorPanel.tsx`/`store/workflow.ts` for the two frontend-wiring
entries. One live agent call (`ai.agent_invoke` on the keyless `copilot`
agent, local Ollama) ran under the shared local-model lock. Raw output:
`battery/raw/set-12/<id>.txt`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-PLATFORM-002 | palette-shaped graph: fetch_quote→json_path→compare("neq")+branch→sleep→notify_desktop; also fetch_history→compute.indicator(rsi) | json_path.extracted=real price (not None); compare "neq" returns bool (not "unknown op"); branch.true_path carries value; sleep slept 1.0s (not 0.0); notify message=rendered value (not ""); RSI(14) series populated | holds |
| R15-AGENT-015 | same graph's `ai.agent_invoke` node, `prompt_template`="Reply with exactly: BATTERY ELEVEN", agent `copilot` (keyless ollama) | reply = exactly "BATTERY ELEVEN" — typed prompt reached the agent, not `{context}` | holds |
| R15-AGENT-016 | `ai.agent_invoke` with a nonexistent agent_id, no creds | `node-error` + `run-error` with the real message ("unknown agent: ..."); no `(no provider key configured)` sentinel, no fake `ok` | holds |
| R15-CODE-PLATFORM-003 | same as R15-AGENT-016 (same handler/defect class) | same node-error/run-error, real message surfaced | holds |
| R15-CODE-FRONTEND-006 | source read: NodeEditorPanel.tsx now calls `useWorkflowStore.runWorkflow` (line 413), no private `consumeSse`; live notify_desktop output carries `intent:"desktop-notification"` | store's single SSE client (`appendEvent`) is the only consumer; notification intent shape matches what the bridge drains | holds |
| R15-CODE-PLATFORM-016 | same as R15-CODE-FRONTEND-006 (same fix) | same | holds |
| R15-DATA-040 | `POST /backtest/run` [AAPL, MSFT, ZZZZNOTREAL] | `warnings` populated: "No price history loaded for ZZZZNOTREAL ...; metrics cover 2 of 3 symbols." (was null) | holds |
| R15-DATA-029 | `/earnings/RELIANCE.NS/estimates`, `/earnings/BDL/estimates`, `/news?symbols=BDL`, `/earnings/INFY/estimates` | RELIANCE.NS and bare BDL both resolve with real INR estimates; BDL news returns `[]` (no Flanigan's mismatch); INFY resolves to INFY.NS INR EPS ~19.6 (not the ADR's USD 0.205) | holds |

COVERAGE: 8/8 ids raw; no raw: none.
