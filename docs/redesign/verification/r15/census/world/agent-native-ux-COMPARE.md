# R15 Census — WORLD-COMPARE: agent-native UX vs the in-app agent

Worker model id: `claude-fable-5-1`
Date: 2026-09-19
Input research: `census/world/agent-native-ux.md` (W-1 .. W-12; the file ends at W-12 with no
closing checklist — the patterns themselves are the comparison rows).
Status: IN PROGRESS (written as-you-go; a later section supersedes this line when complete).

## Working notes (code read so far)

- `sidecar/services/agent_runtime.py` (full), `run_manager.py`, `runs_store.py`,
  `budget_guard.py`, `routers/runs.py`, `src/lib/delegate-runs.ts`,
  `src/modules/chat/AgentsRail.tsx`, `src/store/agent-runs.ts`, `ChatSidebar.tsx:690-1240`.
- Confirmed so far (W-7/W-8): a Delegate run's RESULT is never delivered — rail shows only
  active runs (`AgentsRail.tsx:29-32`), nothing fetches `GET /runs/{id}`, `onForeground` prints
  status only (`ChatSidebar.tsx:1178-1187`), the driver drops every `tool_use` to a
  `[tool_use name]` string (`run_manager.py:167-173`), `resumeDelegateRun` has no caller,
  `pause_run` has no caller, resume re-spawns with `provider=None, model=None, api_key=None`
  (`run_manager.py:401-412`, `routers/runs.py:126-135`), no boot reconcile of orphaned
  `running` rows (`app.py:153` only shuts down).
