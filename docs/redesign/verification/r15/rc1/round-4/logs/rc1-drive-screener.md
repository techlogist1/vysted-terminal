# rc1-drive-screener — working log (gate round 4)

- Verified candidate worktree HEAD == `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. OK.
- Copied `rc1-round-4-seed-data` → `rc1-round-4-data-screener`. Booted own sidecar from
  candidate `sidecar/` source on `127.0.0.1:52322` against that data dir, MCP env pointed at
  the shared `:52153`/`:52154`. `/health` 200 in ~8s. Yahoo circuit open the whole drive
  (`consecutive_opens:1`, `throttles_total:42` at boot) — expected per census.
- Read `src/store/screener.ts`, `ScreenerPanel.tsx`, `ScreenerPresets.tsx`,
  `ScreenerResultsTable.tsx`, `src/lib/host-actions.ts`, `sidecar/routers/screener.py`,
  `sidecar/services/agent_runtime.py` before driving.
- Re-drove census findings 1/2/4/5-6/7 plus region-default-universe and workspace-persistence
  fixes; all confirmed fixed (see `drives/screener.md`, `surface/screener/rc1/round-4/`).
- Ollama lock: acquired cleanly twice (`mkdir` succeeded first try both times); released via
  the `trap ... EXIT` wrapper. Noticed the lock was picked up by another concurrent
  agent (research-briefs / scenario lanes) between my two holds — expected, shared single
  lane working as designed.
- New finding: AUTO-autonomy narration mismatch on `write_screener_filters` (llama3.1:8b says
  "waiting for your confirmation" on an action the runtime already dispatched) —
  `rc1-drive-screener:1`, medium, not covered by DECISIONS 4.9-4.12's fabricated-figure class.
- Did NOT re-run the existing screener vitest suite, the 39-formula grammar-parity matrix, or
  the agent-context/panel-publish rows — unchanged surface, no register signal pointing at a
  regression, out of scope for owner-drive per the task's continue-not-re-derive instruction.
- Stopped own sidecar: the `sleep 86400 | python3` pipe's sleep pid died but the python
  worker (pid 57754, port 52322) stayed up — killed it directly (my own process, my own
  isolated port, not a shared/other-owner port) and confirmed `/health` now unreachable.
- No shared port (`:52152-54`) or other owner's sidecar touched at any point.
