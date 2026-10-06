# Set: batch-8/W5-agent-runtime-research (set-34) — rc1-battery-10, candidate ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-AGENT-004 | real google.genai GenerateContentResponse (prompt 1000, tool-use 200, cand 800, thoughts 6000) through GeminiProvider.stream_chat -> BudgetGuard(max_tokens=7000) | usage in 1200 / out 6800; breach 'token ceiling 7000 reached (8000 used)' | holds |
| R15-LEAD-019 | BudgetGuard.record for openrouter :free slug vs paid vs unlisted paid (64,895 tok) | :free spend 0.0; deepseek-v4-flash 0.05841; unlisted paid 0.12979 | holds |
| R15-CODE-AGENT-007 | registry vs get_provider base url; then edit registry rows in-process | hosts equal registry; after edit dispatch follows https://edited.deepseek.example/v9 / edited.x.example/v2 | holds |
| R15-CODE-AGENT-016 | _discover_specs on a copy of agents/ + an openrouter agent JSON | roster 13 -> 14, degraded [] | holds |
| R15-LIFECYCLE-014 | bad-provider agent JSON, missing dir, live /health | degraded names zz-bad.json w/ reason; missing dir -> {'file':'nope','reason':'agents directory not found'} + ERROR log; live /health agents_degraded [] roster 13 | holds |
| R15-CODE-RESEARCH-003 | force run_iter_research/run_heavy_research to raise, call _run_loop for each depth | run_deep_research gone; ok:false, execution_loop iter/heavy, honest message; no second loop | holds |
