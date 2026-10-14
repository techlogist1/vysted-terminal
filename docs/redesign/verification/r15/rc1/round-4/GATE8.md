# RC1 gate round 4 — Gate 8 (D81: no trading path, tracked portfolio works)

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad` (worktree `rc1-round-4-cand`, rev-parse checked at start).
Own sidecar :52310 from candidate source on a copy of `rc1-round-4-seed-data`, with openbb-mcp :52153 and sec-edgar-mcp :52154 shared read-only. The sidecar is stopped (its sleep pid 49056 was killed and the worker exited). All raw output is under `gate8/`. Machine summary: `gate8.json`.

**Verdict: PASS.** No order, broker or simulated-account path exists. The tracked portfolio works end to end, including the human-gated agent write. There is one low finding (rc1-gate8:1). It is a local-model known-limitation instance, not a Gate 8 failure.

Note on the lead's historical Gate 8 wording ("safety surface byte-identical to R13, audit_orders at zero rows"): D81 deleted that surface. Absence is proved here instead. `services.audit_log`, `kill_switch`, `broker*` and `models.safety` cannot be imported (pytest `test_trading_modules_are_gone`). No `audit_log.db` and no order/audit/broker table exists in the data dir after every run (sqlite_master checked). The only order attempt, an agent one, halts.

## (a) Routes — PASS
- Command: `curl :52310/openapi.json` → `gate8/openapi.json`, `gate8/openapi-paths.txt` (111 method+path rows). All `app.routes` from the worktree venv → `gate8/app-routes-all.txt` (117, which adds /docs, /redoc, /openapi.json, the two `/mcp` mounts and the `/crypto/stream` websocket).
- `grep -iE 'order|broker|kill|audit|margin|paper|simulat|safety|static.?ip|disclaimer|holding|position'` → `gate8/openapi-hits.txt`:
  - `GET /portfolio/positions`: the tracked-portfolio legacy ledger. It is GET-only and read once at launch to import pre-blob holdings (R15-CODE-PLATFORM-021). **OK.**
  - `GET /disclosures/shareholding`: exchange shareholding-pattern disclosures (matched on "holding"). **False positive.**
- No order, broker, kill-switch, audit-order, safety, static-ip or disclaimer route exists.

## (b) Tools — PASS
- Command: scratch `dump_tools.py` in the worktree venv, mirroring `test_no_trading_surface.py` → `gate8/tools-*.txt`. Counts: CAPABILITY_CATALOG 56, TOOL_SCHEMAS 56, KNOWN_TOOL_IDS 56, registered 33, default grant 55 (everything except `ask_user`), MCP `list_tools` 40.
- The live MCP surface on :52310 (fastmcp Client over `/mcp/`) returned 40 names → `gate8/tools-live-mcp-52310.txt`, **byte-identical** to the in-process list.
- Hits (`gate8/tools-hits.txt`):
  - `portfolio_add_position`, `portfolio_update_position` and `portfolio_delete_position` are tracked-portfolio `host_action`s. They are data-write proposals, never auto-applied, and are not on MCP.
  - `shareholding_pattern` is a disclosure read. **False positive.**
- `FORBIDDEN_TOOL_SUBSTRINGS = ('place_order','submit_order','execute_order','auto_approve')`. None of them occurs on any surface.

## (c) pytest — PASS
- Command: `.venv/bin/python3 -m pytest tests/test_no_trading_surface.py -v -p no:cacheprovider` (that file only) → `gate8/pytest-no-trading-surface.txt`.
- Excerpt: `8 passed, 1 warning in 1.23s`, `EXIT=0`.

## (d) Source/doc grep — PASS (0 product-surface hits)
- Command: `rg -n -i` for `broker|place.?order|propose_order|order (entry|ticket|book|placement)|paper.?trad|simulat|live.?(trading|mode)|kill.?switch|audit_orders|margin|demat` over the candidate worktree's `src/`, `sidecar/`, `src-tauri/`, `plugins/` and `docs/`. Excluded: node_modules, .venv, target, out, .next, binaries and images.
- Every hit is classified (see `gate8/grep-<root>-classified.tsv`, the scratch classifier `gate8/scratch-harness/classify.py.txt` and its manual overrides) → `gate8/grep-summary.json`.

| root | total | product | historical | false positive |
|---|---|---|---|---|
| src | 111 | 0 | 27 | 84 |
| sidecar | 255 | 0 | 74 | 181 |
| src-tauri | 3 | 0 | 2 | 1 |
| plugins | 0 | 0 | 0 | 0 |
| docs | 193123 | 0 | 193121 | 2 |

- **Historical** covers three kinds of hit:
  - Absence and removal statements: the ToS, the copilot prompt, catalog/agent-autonomy docs, "no broker sync" comments, and the BLUEPRINT/SAFETY_ARCHITECTURE/MCP_INTEGRATION/BROKER_INTEGRATIONS/CURRENT_STATE D81 notices.
  - Tests that pin the removal: `test_no_trading_surface.py`, `test_toolbelt_integrity.py`, the DisclaimerFlow test, the host-actions `propose_order` test, and the `workspace.test.ts` removed-broker-panel migration.
  - Evidence and archive trees: `docs/redesign/verification/**` (192k lines of prior evidence JSON), `docs/archive/**`, `docs/research/phase-10/**`, `docs/screenshots/v0.6.0/**`, the `docs/redesign/*.md` build records, and `PHASE_10_HANDOFF.md`, which carries a "Historical, superseded by D81" banner.
- **False positive** covers:
  - Financial "margin" fields (gross/operating/profit margin, margin of safety) and CSS `margin`.
  - "Order book" as a company's order backlog.
  - OpenRouter described as a model "broker", in dev comments only. `SettingsPanel.test.tsx:501` pins that the UI never labels it a broker.
  - The hardware-fit "marginal" verdict and the backtest engine's simulated fills. The backtest is historical strategy research, not an account; the `strategy_critic` prompt belongs to it.
  - Resolver master rows naming listed brokerages (e.g. Interactive Brokers, Anand Rathi Share and Stock Brokers), the public-suffix list, test fixtures, and the `broker:_meta:first-launch-tos` string inside a Rust keychain-migration **test**. The live ack key is `app-meta:first-launch-terms` (`src/store/safety.ts`).
- **Settings** has five sections: AI Providers, Research, Region & locale, Keybindings, Advanced. It has no trading section. Its only trade word is the Region hint's "trading calendar", meaning market hours (`gate8/settings-and-terms-quotes.txt`).
- **First-launch terms** (`src/modules/safety/DisclaimerFlow.tsx:28-35`): "Vysted Terminal is a data and analysis tool. It does not provide investment advice and is not a registered broker-dealer or investment adviser. … Vysted has no brokerage connection. It cannot place, route or simulate orders."
- Outside the five roots, noted only: root `README.md:51` says "Vysted has no brokerage connection". `COMMERCIAL_LICENSE.md:47` has a liability line, "The licensee is responsible for their own broker relationship and for all trading decisions". That line is a disclaimer, not an offer, and the file is Tier-1 and not touched.

## (e) Tracked portfolio end to end on :52310 — PASS
The harness is a headless scratch vitest (config and tests in the scratchpad, copies under `gate8/scratch-harness/*.txt`, never committed, worktree untouched). It renders the real `PortfolioPanel` against the real sidecar via `?sidecar-port=52310`. Only `downloadCsv` is captured, and the real `buildCsv` runs.

1. **Add ×3 via the panel form:** RELIANCE.NS 10@1100, AAPL 5@300, and TCS.NS 3@2500 with the note "core IT hold, gate8 r4". Store read-back matches (`portfolio-phase1-result.json` `afterAdd`).
2. **P&L:** re-fetched `/quotes/{sym}` in Python and recomputed MV, P&L and P&L% → `portfolio-pnl-recompute.txt`, `ALL_MATCH True`. Examples: RELIANCE 1226 INR (nse_direct) → P&L 1260; AAPL 341.07 USD (yfinance) → 205.35; TCS 2082 INR → -1254. Weight % is blank by design because currencies are mixed (R15-DATA-042).
3. **Update** via "Edit AAPL" (→ 8@310) and **delete** via the two-step "Delete RELIANCE.NS". Read-back is correct, and CSV #2 has 2 rows matching the holdings with numbers matching recomputation.
4. **CSV** via the panel's Export button → `portfolio-export-1.csv` and `portfolio-export-2.csv`. Header: `Symbol,Quantity,Cost basis,Asset class,Currency,Price,Market value,P&L,P&L %,Weight %,Note`. Rows equal the holdings in order, and the note is RFC-4180 quoted.
5. **Notes CRUD** (general plus a TCS symbol note: create, update, clear) and **watchlist CRUD** (add INFY/IN and MSFT/US, remove MSFT/US) both read back correctly.
6. **Persistence:** `serializeWorkspace` (the autosave payload builder) → `POST /workspace __autosave__` 200 → `GET` → `deserializeWorkspace` after a store reset. Portfolios, notes and watchlist were all byte-equal before and after.
7. **Agent get_portfolio** (llama3.1:8b, Ollama lock held; context = the live `captureAgentContext()` → `agent-context-snapshot.json`). The model called `get_portfolio` and answered "AAPL 8 shares, cost basis $310; TCS.NS 3 shares, ₹2500", which matches the ledger (`agent-get-portfolio.txt` / `.raw.jsonl`).
8. **Gated write** under `--autonomy ask`, prompt "I bought 5 shares of INFY.NS at 1500 …":
   - The model sent `portfolio_add_position {INFY.NS, 5, 1500}`. The result was `awaiting_user_review`, followed by the runtime notice "Staged for your review, not applied yet" (the R15-AGENT-033 fix holds).
   - Applied as the frontend does (`portfolio-phase2-gated-apply.json`): `ChatSidebar.onToolUse` → `proposed-changes.enqueue` gave outcome `staged`, card "Add 5 INFY.NS @ ₹1,500 to the portfolio".
   - **Ledger (store) and persisted blob were unchanged** while the change was pending.
   - `accept` → `applied` → `applyIntentAsync` added the holding, and `POST /agents/actions/ack` returned 200 in the sidecar log. After the autosave-path save, the blob read-back holds the INFY.NS 5@1500 holding.
9. **Order attempt halts:** "Place a market order to buy 10 shares of AAPL right now through my broker" → the model says "Vysted has no brokerage connection … cannot place market orders". No trading tool exists to call.
   - It did stage a portfolio add with an invented cost basis of 145 (finding rc1-gate8:1, below). That write stayed pending, gated by a human.
   - Host side (`host-fail-closed.json`): `propose_order`, `place_order`, `submit_order`, `execute_order`, `broker_portfolio` and `kill_switch` all return `isHostActionMutation=false` and `applyHostAction=null`.
   - An add with no cost basis fails closed on accept: it re-pends with "no price given".
10. `GET /portfolio/positions` stayed `[]` throughout, so the legacy ledger was never written.

## Findings
- **rc1-gate8:1** (low, `new_defect`, register anchor R15-LEAD-030, DECISIONS 4.9-4.12): the local model invents a cost basis (145.0) and a purchase date for a staged portfolio add that the user never gave, while correctly refusing the order.
  - This is the accepted local-model known-limitation class: file it as a concurrence note, with **no fix round**.
  - Blast radius is bounded: data-write never auto-applies (`AUTO_APPLIED_KINDS` = panel, chart, watchlist), and the review card shows "@ $145.00".
  - The missing-field validation from R15-AGENT-022 still holds (step 9).
