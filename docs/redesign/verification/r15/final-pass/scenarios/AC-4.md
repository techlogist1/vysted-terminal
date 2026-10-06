# AC-4 — durable runs: ceilings, cancel, resume (final-adv-maintainer, d38b5d1a)

Own source sidecar :52825, agent copilot, llama3.1:8b, prompt "Add INFY to my watchlist, open the chart for NVDA, and tell me NVDA's latest price." (AC-4/runs.log, per-run JSON).

| run | budget | result |
|---|---|---|
| A-tokens50 | max_tokens 50 | `error` — "token ceiling 50 reached (6566 used)", checkpoint_messages 1, host_actions [] , brief null |
| B-steps1 | max_steps 1 | `error` — "step ceiling 1 reached (1 taken)", checkpoint 1, host_actions [] |
| C-cancel | default | cancel at ~4 s → 200 `{cancelled:true}`, status `cancelled`, "cancelled by user", 0 tokens, host_actions [] |
| A resume | (no new budget) | 200 `{resumed:true}` → re-enters from checkpoint, breaches the same ceiling again on the first round: `error` "token ceiling 50 reached (6514 used)", cost accumulates (13080 tokens, 2 steps). Resume with fresh ceilings is the documented path (run_manager.resume_run docstring). |
| C resume | — | resume of a cancelled run is allowed by design (FR-028, `_resume(..., {"error","cancelled"})`); it completed `done`, and its host actions (add_to_watchlist INFY, set_chart_symbol NVDA) were DELIVERED as proposals with tool results `awaiting_user_review / staged_for_review` — never applied by the run (AC-4/final-437112b0….json). |

First breach ends in `error` with a stated reason and a resumable checkpoint every time; neither halted run delivered a host action. The halted-round-never-enqueued rule (R15-AGENT-092) is additionally pinned in-process: tests/test_run_manager.py + test_budget_guard.py + test_runs_router.py → 64 passed (AC-4/pytest-runs.txt).

Process note: the C resume ran outside the Ollama lock (my probe's mistake, logged in logs/final-adv-maintainer.md); no product impact.

VERDICT AC-4: pass
