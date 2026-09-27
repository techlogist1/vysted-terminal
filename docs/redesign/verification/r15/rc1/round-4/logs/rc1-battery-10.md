# rc1-battery-10 working log

Candidate: 1006c6da694ede5776c3dabbd27b305aeb56b5ad
Sidecar: booted from candidate source on 127.0.0.1:52350, data dir
scratchpad/rc1-round-4-data-battery-10 (copy of rc1-round-4-seed-data), MCP env
vars pointed at the shared read-only stack (:52153 openbb, :52154 sec-edgar).
sleep pid 86012 (wrapper sh pid 86010), stopped cleanly at end of run.

Sets covered: batch-6/set-24 (9 ids, host-actions/portfolio), batch-9/set-35
(5 ids, agent runtime), batch-26/set-77 (2 ids, resolver + earnings estimates).
All 16 ids: holds. No regressions, no new defects, no chain failures, no gate8
scope in this shard.

set-24: all 9 entries were certified in batch-6 solely via vitest
(host-actions.test.ts / portfolios.test.ts). Per the no-vitest rule for this
role, each fix was independently re-derived by reading the current candidate
source (portfolios.ts, host-actions.ts, proposed-changes.ts, PortfolioPanel.tsx,
sidecar routers/portfolio.py) rather than executing the suites; every code path
the original defect named is confirmed present and correct.

set-35 + set-77: certified in batch-9/batch-26 via live sidecar/agent repros;
re-run live against this shard's own sidecar (curl for LLM-chat/earnings/
custom-agents/resolve, vy.py+Ollama under the shared lock for the two agent
runs). Ollama lock note: the lock dir vanished mid-hold on the first
vy.py call (AGENT-046) despite the trap's own rmdir not yet having fired
(process was still running) — likely another lane's cleanup logic mis-firing
on a fresh (non-stale) lock; the run itself completed correctly and cleanly
(no output corruption), so it is noted here as an environment observation,
not filed as a product defect.

COVERAGE: 16/16 ids raw; no raw: none.
