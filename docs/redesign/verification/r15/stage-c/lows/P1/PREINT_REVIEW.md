# Lows P1 pre-integration review

- Reviewer: Opus (claude-opus-5-5[1m]), read-only, fresh context
- Candidate: `worktree-agent-lows-P1-int-4c6dfe8` @ 70fe85c9af801387dc503e4a4bc97552f7a532d8
- Base: 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2 (writers cut from ebc5ed41)
- Diff: 91 files, +3156 / -764
- Stamp: 07:07 IST
- Status: untested pending integration (no pytest / vitest / cargo / tsc run, per the off-lane rule)

## Verdict: needs_fix

## Blocking

1. **W8 R15-UI-076: region defaults ripple into existing vitest suites (vitest red).**
   `src/store/symbols.ts` `DEFAULT_SYMBOLS` and `src/store/chart-drawings.ts` `DEFAULT_CHART_SYMBOL` now resolve to the IN defaults (`^NSEI`, RELIANCE.NS, TCS.NS, HDFCBANK.NS; chart `^NSEI`). The following unchanged tests still pin the old US defaults:
   - `src/modules/watchlist/WatchlistPanel.test.tsx`: expects SPY / AAPL / BTC/USDT from `DEFAULT_SYMBOLS`.
   - `src/modules/news/NewsFeedPanel.test.tsx:107`: expects `["SPY","QQQ","BTC","ETH","NVDA","AAPL"]`.
   - `src/modules/panel-context-publishers.test.tsx`: `findByText("SPY")` / `findByText("AAPL")`.
   - `src/store/settings.test.ts:159`: chart defaults symbol `"SPY"`.
   - `src/lib/workspace.test.ts:710`: restored default drawing symbol `"SPY"`.
   - Check also `src/modules/notes/NotesPanel.test.tsx` (it seeds `[...DEFAULT_SYMBOLS]` at line 43).

   Fix: in each test, seed the US list explicitly (`defaultSymbolsForRegion("US")` / `defaultChartSymbolForRegion("US")`), or move the expectations to the IN defaults. Keep every assertion; do not delete, skip or loosen any of them. Then run vitest at integration.

## Checks

- **(a) Safety surface.** The per-path diff is empty for `sidecar/models/audit_log.py`, `sidecar/services/kill_switch.py`, `src-tauri/src/kill_switch.rs` and `types/proposed-change.ts`.
  - `sidecar/services/agent_runtime.py` changed, but none of the hunks touch the proposed-changes gate. The changes are:
    - `_STAGEABLE_PLAN_ACTIONS` is now `frozenset(PLAN_ACTIONS) ∩ HOST_ACTION_TOOLS`. It only drives the advisory `staged` badge.
    - The preamble tool list is now derived from the catalog.
    - `_resolve_model` now raises when there is no default.
    - The tool timeout is read from `cap.timeout_from_args`.
  - safety_surface_touched = false.
- **(b) Claimed tests.** Every claimed pytest, vitest and cargo test exists as source and asserts its entry's behaviour.
  - Modified tests were updated, not weakened. Examples: onboarding tests moved to app-meta mocks; `backtest.test` now asserts `barsProcessed`; the PortfolioPanel test uses the field-specific message; the store idempotency tests were converted when `_ensure_schema` was removed.
- **(c) Conflict resolution.** There were no textual conflicts and no file overlaps between writers.
  - Candidate blobs equal the writer blobs, with two exceptions:
    - The 5 files in style commit 70fe85c9 (ruff I001 import order and prettier table whitespace only).
    - 3 W2 files that moved with the base, whose +/- hunks are identical to W2's own diff.
- **(d) Contracts.**
  - `types/backtest.ts` mirrors `sidecar/models/backtest.py`: both drop the "trade" event and the progress equity.
  - The MCP projection equals the 31 ids pinned in `test_mcp_catalog_parity._MCP_EXPOSED`, with `run_custom_backtest` now internal-only.
  - Every agent JSON is ≤ 4608 bytes (copilot is 4382).
  - Only prompt text changed, so the roster count is unchanged.
  - `run_backtest(bar_loader=...)` is now a required keyword, and every caller passes it (AST scan).
  - `update_run` now returns None, and no caller uses its return value.
  - `TerminalHolding.currency` is now required, and there are no other TS consumers.
  - `publishAckStatus` was removed, and it had no other callers.
- **(e) ci-local risk.**
  - Passed:
    - `ruff check` and `ruff format --check` on the whole sidecar (445 files).
    - `py_compile`.
    - `prettier --check` on all changed files.
    - Static emulation of audit-design-tokens check 4 found 0 violations.
  - Not run: vitest (red per Blocking 1), tsc, eslint, clippy, cargo test and pytest.

## Advisories

1. `_resolve_model` now raises ValueError instead of falling back to "gpt-4.1-mini". All 8 registry providers have a default today, but a provider added later without one will fail loudly at invoke.
2. The copilot prompt no longer has explicit tool routing or its own "no brokerage" line. The shared preamble still carries "no brokerage connection". Watch agent behaviour in the battery.
3. The MCP exposed set is pinned at 31. Any new `read_handler` capability must be added to `_MCP_EXPOSED` or `_MCP_INTERNAL_ONLY` explicitly.
4. `web_available` semantics changed: `is_web_search_source` excludes `vysted://` sources and those with source_type filing/news. This misfires if the search layer ever stamps `source_type="news"` on web hits. The TS mirror `isWebSearchSource` must stay in lockstep.
5. The FAST `structured` gains a `source_floor` leg. `brief-blocks` `deriveMetrics` reads named keys, so the leg does not render; nothing breaks.
6. The CSV formula-injection prefix also prefixes text cells that start with "-" (for example a note like "-short"). Numeric cells are unaffected.
7. `MAX_HOLDING_QUANTITY = 1e12` silently drops restored holdings above the cap, such as very large token lots. Consider surfacing a notice.
8. `runs_store` has `LIST_LIMIT = 100` and 30-day retention. An old paused run can fall off the list or be pruned at the first connect.
9. The Rust changes are not verified by cargo or clippy. Watch three points: `no_wait` closure type inference in `migrate_collecting`, `value.into()` into `serde_json::Value`, and the new tests that read source files (`no_env_mutation_in_src` scans only the flat `src/*.rs`).
10. The `sidecar_healthy` readiness check now needs HTTP/1.1 200 plus a compact `"service":"vysted-sidecar"`. This holds for Starlette's JSONResponse today, but a response-class change would break readiness.
11. mentions adds a module-level 140 ms debounce per resolve. That is fine for the UI, but tests using fake timers must advance it.
12. The `proposed-changes.ts` ack plumbing (`ok = status !== "failed"`) sits next to the gate. It is behaviour-preserving for done/kept, but the lead should eyeball it.
13. PREINT says W6 restamped fixtures in `test_runs_router`. The actual restamps are in `test_runs_store` and `test_schema_version`. This is a doc slip.
14. Carried items:
    - Could-not: R15-CODE-RESEARCH-005, R15-CODE-AGENT-031.
    - Handed to the lead: R15-DOCS-009, R15-CODE-PLATFORM-049, and the stale four-mode mentions in spec.md.
