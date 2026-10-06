# batch-8/W5-agent-runtime-research

Candidate `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`. Own sidecar `:52346`. Raw output: `raw/set-34/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-AGENT-085 | grep `src/modules/chat/ChatSidebar.tsx` for citation/unverified-claim machinery on plain chat turns | no citation-object or unverified-claims pass on a plain tool-grounded chat message outside the brief/Equity-Overview surfaces — matches register's documented `status: open` (still_reproduces, low) unchanged | holds |
| R15-AGENT-087 | grep `src/store/agent-mode.ts` docblock; `src/store/keybindings.ts` `SHELL_DEFAULTS` | `agent-mode.ts` docblock still describes "four-mode intent (FR-003)... Ask / Edit / Build / Delegate... ⌥1–⌥4"; `keybindings.ts` only binds `alt+1` (Agent) / `alt+2` (Delegate), with its own comment admitting "the legacy four-mode rows... described bindings the shipped handler no longer has" — matches register's documented `status: open` (prose drift only, low) unchanged | holds |
| R15-AGENT-089 | grep `sidecar/services/planner.py` `PLAN_ACTIONS`; `sidecar/services/agent_runtime.py` `_STAGEABLE_PLAN_ACTIONS` | neither tuple includes `close_panel`/`focus_panel` (`PLAN_ACTIONS` has 7 actions, none of the two; `_STAGEABLE_PLAN_ACTIONS` has 6, same gap) — matches register's documented `status: open` (still_reproduces, low; the host action remains callable in-loop, only pre-staging is affected) unchanged | holds |
| R15-RESEARCH-068 | grep repo-wide for `RESEARCH-068` | **not found anywhere** in `docs/redesign/verification/` or the register (`vysted-r15-register.json` has no such id; its `R15-RESEARCH-*` series stops at `-042`). This ID does not exist — not a product defect, a task-data/harness issue (the entry list this shard was given names an id that was never filed) | blocked_env |
| R15-RESEARCH-070 | grep repo-wide for `RESEARCH-070` | same as above — id does not exist anywhere in the verification tree or register | blocked_env |
| R15-RESEARCH-072 | grep repo-wide for `RESEARCH-072` | same as above — id does not exist anywhere in the verification tree or register | blocked_env |

Summary: 3 holds (all documented-open lows confirmed unchanged), 3 blocked_env (R15-RESEARCH-068/070/072 do not exist in the register or anywhere in the verification tree — a task-data issue, not a candidate defect; flagged in notes, no register entry to regress or certify).

COVERAGE: 6/6 ids raw (3 real repros + 3 non-existence confirmations).
