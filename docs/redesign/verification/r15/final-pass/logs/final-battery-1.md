# final-battery-1 log

Lane battery:1 (Opus, effort high), candidate d38b5d1a (worktree final-cand, read-only; PYTHONDONTWRITEBYTECODE=1 for every in-process run).
Selection: the register at the sha, status == 'fixed', ids sorted as strings, p%4==1 -> 149 ids (battery/shard-1.ids).
Sidecar: one own sidecar on :52861 (sleep pid 1367 / worker 1368, data dir copied from final-seed-data), reused for every probe; stopped by killing pid 1367 at the end (worker gone, port down).
LIFECYCLE-005 used a second own sidecar on :52867 with VYSTED_OPENBB_MCP_PORT=52868 (closed port); stopped by its own sleep pid 14665.
Ollama lane: one lock hold (/tmp/vysted-r15-ollama.lock, 17:37:12 to about 17:38:46), llama3.1:8b. It ran two delegate runs (budget 1000 and a default-budget control) and one ASK-autonomy chart invoke. No OpenAI spend: LEAD-043 sent no key and a fake key only.
No vitest or pytest suites were run. ci_pinned ids name the test file:line and show the closure commit is an ancestor of d38b5d1a.

Results: holds 86, regressed 0, ci_pinned 63, needs_gui 0, blocked_env 0. findings/battery-1.json = [] (no regressions).

Notes:
- AGENT-033 run (llama3.1:8b, ASK): the staging notice fired and the model said "proposed". The same reply also printed BDL figures (price, market cap, P/E, 50-day MA) with no tool call behind them. This is an instance of the keyless local-model known limitation (DECISIONS 4.9-4.12), not a regression. Evidence: battery/raw/R15-AGENT-033.txt.
- AGENT-087: the named sections (FR-003/SC-029 and the agent-mode.ts docblock) are fixed. One residual "mode (Ask/Edit/Build/Delegate)" remains at specs/001-agent-native-redesign/spec.md:1112 (Key Entities). This is low doc drift outside the fix scope.
- CODE-DATA-003: a cold in-process call of the resolve_symbol tool has no rename map loaded, because the tool path does not call schedule_refresh. The app lifespan schedules it at boot (app.py:139). With the lane warm, the tool and /resolve are identical.
- CODE-PLATFORM-058: the three named copies now route through crate::app_data_dir. A later resolve_cache_dir (CROSS-PLATFORM-012) carries its own copy of the temp-dir fallback. This is adjacent and not this defect.
- Environment:
  - Yahoo was throttled this session: AAPL price_data and TCS.NS/AAPL earnings history were empty. Non-Yahoo symbols were used instead.
  - Keyless web_search reported every engine unavailable in-process, while curl to DuckDuckGo and Brave answered 200 and to Mojeek answered 403. RESEARCH-024 was verified through _dispatch with a SearXNG-shaped row.
  - The candidate worktree shows an uncommitted "M vitest.config.ts" that this lane did not make.
- Banned word/phrase scan of shard-1.md and raw/: 0 hits.

COVERAGE: 149/149 ids raw; no raw: none
