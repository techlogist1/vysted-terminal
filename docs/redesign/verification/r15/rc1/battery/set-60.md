# batch-12/W5-w5 (set-60)

Candidate 4c6dfe8c. Own sidecar :52342, data dir rc1-data-battery-2. Raw output: `raw/set-60/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-AGENT-019 | In-process (candidate venv): `services.planner.classify_intent` on the cert's original + fresh prompts | All 5 portfolio-entry phrasings ("log 10 TCS at 3400", "record that I hold 20 ITC at 410", "enter 5 HDFCBANK at 1600", "noting down 15 WIPRO at 250", "add 3 NVDA at 180") classify `edit` (confidence 0.95); controls "what is P/E?" and "How is my portfolio doing?" stay `read`. Matches batch-12's cert exactly. | holds |
| R15-AGENT-092 | Code read: `services/run_manager.py:180-206,290-330` `undispatched` dict / `_on_tool_result` / `_output()` | An action is staged in `undispatched` keyed by `tool_call_id` and only promoted to `host_actions` inside `_on_tool_result` — i.e. once the tool actually got a result. A budget breach sets `halted`/`breach_reason` BEFORE that result arrives, so the action never leaves `undispatched` and `_output()`'s `host_actions` stays `[]` on the error path — reproducing the cert's live result ("host_actions: []" on a 1000-token breach) by source; the comment at line 182-183 names R15-AGENT-092 directly. | holds |
| R15-AGENT-093 | In-process: `_normalise_tool_args(LLMToolUseEvent(...))` on the cert's exact cases | `option_chain max_strikes:"10"` -> `10` (int); `"ten"` -> `INVALID_ARGS_SENTINEL` reason "'ten' is not of type 'integer'"; `screener_run limit:"25"` -> `25`; `news limit:"5"` -> `5`; `sec_insider_transactions limit:"5"` -> `5`, while `"5.0"` -> still rejected for an integer field. Byte-for-byte the cert's cases. | holds |

Summary: 3 holds, 0 regressions. AGENT-092 verified via direct source trace of the undispatched/host_actions gate rather than a live budget-breach agent run, avoiding an unnecessary Ollama-lock round for a mechanism fully visible in code.
