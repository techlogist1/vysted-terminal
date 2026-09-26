# batch-10/W1-runtime-backtest

Candidate `4c6dfe8c` (rc1-cand worktree). Own sidecar `127.0.0.1:52340`, data dir
`rc1-data-rc1-battery-0`. All 7 entries are design/code-level; re-verified by reading the
current source (function existence, derived-vs-mutable field structure, docstrings citing
the register id) — no pytest/vitest suite run, no live model call needed.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-050 | Read `sidecar/services/llm/anthropic.py` (`_split_system_and_messages`) and `sidecar/services/agent_runtime.py` (system-message construction). | `cache_control` breakpoint set on `system_blocks[0]` and on the last tool-result turn (incremental caching). `agent_runtime.py:708-712` sends the stable persona prompt as its OWN first system message, with the volatile session/turn preamble as separate LATER system messages — so the cached prefix (the expensive, stable persona+tools block) is no longer busted by the per-turn-changing preamble. | holds |
| R15-CODE-AGENT-009 | Read `sidecar/services/agent_runtime.py` around `invoke_agent`. | Delegates to `_prepare_run`, `_plan_prepass`, `_open_round`, `_relay_provider`, `_consume_round`, `_dispatch_round` — all present as independent functions; the former ~400-line monolith is decomposed. | holds |
| R15-CODE-AGENT-013 | In-process: `catalog.internal_tool_ids()` vs `agent_selectable_tool_ids()` vs `default_grant_tool_ids()`; grep for `.aliases` readers and `.mcp` field assignment. | `default_grant_tool_ids()` (55) now differs from `internal`/`agent_selectable` (56 each, which the docstring says are equal BY DESIGN, not a bug). `by_alias` in `catalog.py:1823` reads `cap.aliases` (no longer zero readers). `mcp` is now a derived `@property` on `Capability` computed from `kind` ("never set" per its docstring) — structurally impossible to overwrite, replacing the old mutable field that was blanket-assigned. | holds |
| R15-LIFECYCLE-015 | Read `sidecar/services/backtest_store.py`. | Docstring cites R15-LIFECYCLE-015 directly: results are persisted to `<data-dir>/backtests/<run_id>.json` in addition to the 32-slot in-memory LRU; `get()` falls back to disk on a cache miss, `list_runs()` merges disk+memory and sorts `reverse=True` by `started_at` (newest first). | holds |
| R15-AGENT-083 | Read `sidecar/services/agent_tools/catalog.py` (`mcp_capabilities`, `_MCP_INTERNAL_ONLY`). | Docstring cites R15-AGENT-083 directly and documents the external MCP surface as READ-ONLY in 0.9 by design ("no host action or mutating capability is projected; those stay in-app behind the proposed-changes gate") — the register's finding is resolved as an accepted, documented scope decision, not left as an undocumented gap. | holds |
| R15-AGENT-084 | grep `src/lib/host-actions.ts` for a drawing action; grep for an SC-022/SC-027 completeness audit. | `"add_chart_drawing"` host action exists (host-actions.ts:81,106,817,954). `sidecar/tests/test_capability_completeness.py` and `test_toolbelt_integrity.py` reference SC-022/SC-027 (completeness audit present). | holds |
| R15-RESEARCH-030 | grep `sidecar/services/agent_tools/catalog.py` for "transcript". | `earnings_call_transcript` capability exists (catalog.py:895-902), described as fetching the NSE/BSE concall transcript. | holds |

**Set result: 7/7 holds.**
