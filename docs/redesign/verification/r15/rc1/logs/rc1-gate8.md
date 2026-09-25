# rc1-gate8 working log

- 2026-09-25 05:06:15 IST start. Candidate 4097dac4 (rc1-cand worktree, read-only). Data dir scratchpad/rc1-data-rc1-gate8 (cp -R of rc1-seed-data).
- Own sidecar :52310 booted from rc1-cand/sidecar, env VYSTED_OPENBB_MCP_PORT=52153 VYSTED_SEC_EDGAR_MCP_PORT=52154. sleep pid 59904 (sh wrapper 59902, python 59905). Log scratchpad/rc1-gate8-sidecar.log.
- 05:10:15 (a) /openapi.json: 111 method+path rows (101 paths); app.routes 117 (diff = /docs,/redoc,/openapi.json,/mcp mount,/crypto/stream ws, :path converters). grep hits: GET /disclosures/shareholding, GET /portfolio/positions only.
- (b) catalog 56 / TOOL_SCHEMAS 56 / KNOWN_TOOL_IDS 56 / registered 33 / default grant 55 / MCP list_tools 40 (live :52310 /mcp also 40). Hits: portfolio_{add,update,delete}_position (tracked-portfolio host actions), shareholding_pattern; margins in fundamentals descriptions; backtest SIMULATED (historical backtest, kept).
- (c) pytest test_no_trading_surface.py: 8 passed.
- (d) rg over rc1-cand: src 111 / sidecar 244 / src-tauri 3 / plugins 0 / docs 5414 hits, all classified (grep-*.classified.tsv). Product surface: docs/PHASE_10_HANDOFF.md (11 hits) only.
- 05:16:47 (e) portfolio e2e phase A (scratch vitest, scratchpad/gate8-e2e, config root=rc1-cand read-only, cacheDir scratch; rc1-cand git status stays clean): 9/9 steps ok — add 3 (RELIANCE/AAPL/INFY+note), blob read-back + slice restore, P&L panel vs /quotes recompute exact, CSV via panel Export handler (3 rows, columns match), update AAPL + delete RELIANCE read-back, notes CRUD, watchlist CRUD, context captured.
- agent turn 1 (llama3.1:8b, ask): tool_use get_portfolio; context portfolio == blob ledger (ids/qty/cost). Narration listed AAPL 8 @ "₹190" (currency mislabel) and claimed "I've opened the Portfolio panel" with no open_panel call — small-model narration, noted.
- 05:19:28 agent turn 2 (ask): portfolio_add_position TCS 5 @ 3500 proposed + staged notice; blob byte-identical (cmp), legacy ledger []. Phase B: enqueue -> staged, blob unchanged; accept -> applied; read back 3 holdings incl TCS.
- Sidecar stopped (kill 59904; port free). rc1-cand git status clean.
- Verdict: FAIL on docs only (rc1-gate8:1 PHASE_10_HANDOFF.md); portfolio PASS 13/13. Also rc1-gate8:2 (low, get_portfolio lacks currency).
- Notes (residue, no path): src/lib/format.ts:278-280 provider short labels kite/upstox/dhan; ProvenanceBadge 'prefix' prop only exercised by DataBadges.test ('PAPER'); EmptyState.test 'Connect broker' fixture; watchlist slice restore ignores an empty list (deleting every symbol does not persist).
