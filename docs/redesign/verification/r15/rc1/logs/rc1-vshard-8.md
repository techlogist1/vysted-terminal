# rc1-vshard-8 working log
- 2026-09-26 09:30:27 IST start. Candidate 81fbfe910d472ecd154fa62e42d86bce213a697e (worktree rc1-4c6dfe8-fix-int, HEAD verified).
- Own sidecar :52608, data dir scratchpad/rc1-data-rc1-vshard-8, sleep pid 89378 (python 89379).
- 09:36:10 vy.py refuses non-GET on :52608 (range 52100-52399); agent runs go to shared :52152 (4c6dfe8c; agent_runtime/agent_tools/agents/llm/correctness_gate/yfinance_provider byte-identical to 81fbfe91 per git diff --quiet).
- 09:46:14 done; sidecar stopped (kill 89378, :52608 free). shard-8.md + findings written.
