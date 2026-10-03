# Set 56 — lows-P1/agent-runtime (rc1-battery-22, candidate ace7dd768c3b809b0e72b20b20cfc94eea2368bd)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-071 | in-process: preamble vs catalog default grant (raw/set-56/R15-AGENT-071.txt) | preamble tool list is generated from `catalog.default_grant_tool_ids()` host_action kind; all 19 host_action ids present; loaded copilot prompt carries preamble (copilot.json still names some tools in persona prose, adjacent note) | holds |
| R15-AGENT-073 | in-process `_resolve_model(copilot,'anthropic',None)` | -> claude-opus-4-8 (registry default), not qwen2.5:7b; unknown provider -> ValueError, no 'gpt-4.1-mini' literal | holds |
| R15-AGENT-089 | in-process `planner.PLAN_ACTIONS`, `_coerce_steps`, `_STAGEABLE_PLAN_ACTIONS` | close_panel/focus_panel in PLAN_ACTIONS, kept by _coerce_steps (bogus dropped), in stageable set | holds |
| R15-CODE-AGENT-018 | `_STAGEABLE_PLAN_ACTIONS == _READ_SAFE_PANEL_ACTIONS` | False (stageable derived from PLAN_ACTIONS ∩ HOST_ACTION_TOOLS; read-safe keeps open_company_overview) with comment on the relation | holds |
| R15-CODE-PLATFORM-076 | per-agent systemPrompt byte length | copilot 4382 B (was 8751); others 2581-3900 | holds |
| R15-CODE-AGENT-017 | live :52362, bad tools_json row inserted into own data dir, GET /custom-agents | HTTP 200, list returns the good custom agent, bad row skipped | holds |
| R15-CODE-AGENT-029 | `grep -rn _ensure_schema sidecar --include=*.py` | 0 hits | holds |
| R15-DOCS-009 | grep LangGraph docs/BLUEPRINT.md, requirements | 0 LangGraph hits; BLUEPRINT :90,:126 now say 'hand-rolled loop' | holds |

COVERAGE: 8/8 ids raw; no raw: none
