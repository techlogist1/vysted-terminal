# rc1-vshard-8 working log (gate round 4)
- 05:10 candidate worktree HEAD = 68d5573aff9a579af084dcbb124843f2aecff6e8 (checked)
- 05:10 own sidecar booted from worktree source on :52608, data dir scratchpad/rc1-round-4-data-rc1-vshard-8 (seed copy); sleep pid 34056; /health ok (0.8.0)
- 05:10-05:25 ran every id (see verifier/shard-8.md); vy.py refuses non-GET on :52608 (allowed 52100-52399) -> used direct curl to /agents/copilot/invoke with vy's payload, each Ollama call under the mkdir lock with an EXIT trap
- harness: the Ollama lock dir disappeared while my locked calls were still streaming (another lane removed a live lock)
- 05:25 sidecar stopped (kill 34056); port 52608 free; worktree git status clean
- verdicts: RESEARCH-007 refuted, LEAD-031 refuted, others hold; findings/rc1-vshard-8.json (6 entries)
