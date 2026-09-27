# rc1-gate8 — gate round 4 working log

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad (worktree rc1-round-4-cand, rev-parse verified at start).
Fresh start: no prior round-4 gate8 files existed.

- 01:26 own sidecar :52310 from candidate source, data = cp -R of rc1-round-4-seed-data -> rc1-round-4-data-rc1-gate8; sleep pid 49056 / worker 49057; /health ok, openbb-mcp available.
- (a) /openapi.json -> 111 method+path rows (app.routes: 117 incl. docs/openapi/redoc, /mcp mounts, /crypto/stream ws). Hits: GET /portfolio/positions, GET /disclosures/shareholding. No order/broker/kill/audit route.
- (b) tool surfaces dumped from the worktree venv (scratch script); catalog/TOOL_SCHEMAS/KNOWN_TOOL_IDS 56, registered 33, MCP 40 (in-process == live :52310 /mcp, byte-identical). Hits: portfolio_* host actions, shareholding_pattern.
- (c) pytest tests/test_no_trading_surface.py: 8 passed.
- (d) rg over src/sidecar/src-tauri/plugins/docs of the candidate worktree; every hit classified (scratch classifier + manual overrides): product 0 in every root.
- (e) headless scratch vitest (config + tests in scratchpad, never committed; worktree untouched) against :52310: 3 holdings via the panel form, CSV via the panel Export button (downloadCsv captured), update/delete via row controls, notes + watchlist CRUD, autosave-path persist + launch-restore round trip; P&L recomputed in Python from fresh /quotes: exact match.
- Agent (llama3.1:8b, Ollama lock held per call): get_portfolio call matches the ledger.
- Gated add under ask: staged, store and blob unchanged until accept, then accept → applied, ack 200, and blob read-back has INFY.NS 5@1500.
- Order-attempt probe: declined correctly, but the model staged portfolio_add_position with an invented cost_basis 145 (still pending). Filed as rc1-gate8:1, low, a local-model known-limitation instance (DECISIONS 4.9-4.12), no fix round.
- Host fail-closed scratch check: order/broker/kill names are not host mutations, and applyHostAction returns null for them. An add without cost re-pends.
- 01:39 sidecar stopped (kill sleep pid 49056; worker 49057 exited). Ollama lock released by each call's trap.
- Wrote GATE8.md, gate8.json and findings/rc1-gate8.json. Verdict PASS.
