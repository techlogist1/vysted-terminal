# final-battery-2 working log (lane battery:2, claude-opus-5-5, effort high)

Candidate d38b5d1a2487bd52fe8a7e741a3a5266e3206611 (read-only scratch worktree final-cand). Register: docs/redesign/verification/vysted-r15-register.json at that sha, status=='fixed', sorted, p%4==2 -> 149 ids (battery/shard-2.ids).

- Sidecar: one own sidecar on :52862 from final-cand source, scratch data dir final-data-final-battery-2 (seed copy), MCP ports 52801/52802 read-only; pids in battery/shard-2.pids.json; log logs/final-battery-2-sidecar.log; /health 0.9.0. Stopped at 2026-10-03 17:52:35 IST with kill 8074 (own sleep pid); :52862 then refused (curl exit 7); pids 8072/8074/8075 gone.
- Runner: scratch fb2/run.py runs one probe script per id and writes battery/raw/<id>.txt (command, output, EXIT). Batches: static (54), curl c1-c3, in-process i1/i2, LLM (4 ids under the ollama mkdir lock, one call per hold; lock absent at close), fix rounds 1-4.
- Probe fixes (scratch-side only, no product change): AGENT-007 PYTHONPATH; AGENT-011 real _run_custom_backtest after backtest_strategies.register_all(); AGENT-063 probe scripts copied into fb2/sc; RESEARCH-029/037 re-enabled in b15_s2.py; CODE-DATA-012 grep -c exit masked; DATA-072 rewritten to record_rate_limited x3 (first probe called a non-existent record_throttle and never tripped); LEAD-050 full GE/IT/ON/ALL probe; UI-089 grep path corrected to src/store/marketplace.ts.
- CODE-FRONTEND-019 chmod'd only my scratch data dir's workspaces/ (555 then 755). CODE-PLATFORM-013 ran a scratch vitest harness (scratchpad fb2-fe, symlinks to final-cand, jsdom url http://localhost:5173, one probe file; not the repo suite, not committed).
- RESEARCH-008: blocked_env as at rc2. Live keyless web_search answers in 11-18 s (< 25 s cap, no timeout) with "DuckDuckGo unreachable; Brave/Mojeek rate-limiting"; the rotation replica at the production 6 s deadline returns keyless:brave in 6.0 s. Side observation filed medium (new_defect, 0.9.1): the product Brave engine gets 429 while plain-UA curl gets 20 results in the same minute.
- UI-083: no rc2 row; GUI-round certified -> needs_gui.

Counts: holds 110, regressed 0, ci_pinned 37, needs_gui 1, blocked_env 1. Regressions: none. findings/battery-2.json holds the one medium side finding.

COVERAGE: 149/149 ids raw; no raw: none
