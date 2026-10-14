# batch-5/W3-agent-runtime-chat (rc1-battery-7, set-17)

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98, own sidecar :52347 (source run). All entries
re-checked against candidate source + in-process where the fix is a runtime function, never
judged from the diff alone.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-AGENT-020 | Source read: catalog.py read_notes tool + context-provider.ts captureNotes() | `read_notes` capability present; `__notes__` context entry carries general + per-symbol note text to the agent | holds |
| R15-AGENT-025 | Source read: agent_runtime.py `_relay_provider`, `_PLANNER_TIMEOUT_SECONDS`, `IDLE_TIMEOUT_S`/`LOCAL_IDLE_TIMEOUT_S` | 20s planner timeout + heartbeat-every-10s/idle-timeout watchdog wired into the SSE relay | holds |
| R15-AGENT-026 | Source read: agent_runtime.py `_finish_turn` + `is_length_finish` | max_tokens/length finish now yields an explicit notice step (`_LENGTH_NOTICE`) before close | holds |
| R15-RESEARCH-014 | Source read: research/deep.py `_synthesis_llm` | `truncated` flag derived from `is_length_finish` propagates out of deep-research synthesis | holds |
| R15-AGENT-031 | Source read: message-notices.ts `isRuntimeNotice` + agent_runtime.py `NOTICE_STEP_KIND` | notices matched by `step_kind=="notice"`, not by a drifting prose regex | holds |
| R15-AGENT-033 | Source read: agent_runtime.py system instruction (awaiting_user_review) + staged notice text | "Staged for your review, not applied yet: ..." notice + explicit instruction present, matches cert | holds |
| R15-AGENT-040 | Source read: agent_runtime.py `_HISTORY_VERBATIM_MESSAGES`/`_HISTORY_SUMMARY_HEAD` fold logic + ChatSidebar.tsx marker | fold-to-summary (not FIFO truncation) + "older turns summarised" UI marker | holds |
| R15-AGENT-048 | Source read: llm/openai.py `_MAX_REPAIRS_PER_ROUND=2`, `_REPAIR_TIMEOUT_S=30.0` | repairs capped at 2/round, each timed + metered; rest sentineled with no call | holds |
| R15-UI-054 | Source read: same fix as R15-AGENT-031 (kind-based notice match) | "kept previous brief" notice now rendered as a transcript chip, not buried in trace | holds |

COVERAGE: 9/9 ids raw; no raw: none.
