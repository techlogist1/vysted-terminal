# Gate 8 (D81) — rc1 gate round 5 — rc1-gate8

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98` (scratch worktree `rc1-round-5-cand`, HEAD checked, `git status` clean after the run). Own sidecar from candidate source on **:52310**, data dir `scratchpad/rc1-round-5-data-rc1-gate8` (cp -R of `rc1-round-5-seed-data`), sleep pid 10423, stopped at the end. Model: local llama3.1:8b via Ollama, each call under `/tmp/vysted-r15-ollama.lock`. Nothing else was needed from the hosted lane (no spend).

**Verdict: PASS.** There's no order, broker, kill-switch, audit-order or simulated-account path on any surface: routes, tools, MCP, source, docs, data dir or the agent. The tracked portfolio works end to end: panel CRUD, P&L against live quotes, CSV export, notes, watchlist, `get_portfolio`, and a gated agent write that is applied at human accept. Product-surface hits: **0**. Portfolio breaks: **0**.

Raw rg output (never committed) is in **`/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/gate8-5/`** (`src.txt`, `sidecar.txt`, `src-tauri.txt`, `plugins.txt`, `docs.txt` — the last is 122 MB). The same directory holds the sidecar log and the e2e scratch copy.

## (a) Routes

- Command: `curl :52310/openapi.json` → `gate8/openapi-paths.txt` (111 method+path pairs). Then `grep -iE 'order|broker|kill|audit|margin|paper|simulat|safety|static.?ip|disclaimer|holding|position'` → `gate8/openapi-hits.txt`.
- Hits:
  - `GET /disclosures/shareholding`: NSE/BSE shareholding-pattern data (the word "holding" inside "shareholding"). Not trading.
  - `GET /portfolio/positions`: the legacy tracked-portfolio ledger, read once for import. It is GET-only: no POST/PUT/DELETE and no `/{position_id}` route (R15-CODE-PLATFORM-021).
- No `/brokers`, `/orders`, `/safety`, `/kill-switch`, `/audit-log`, `/margins`, `/disclaimer-*` or `/static-ip*` route exists. **PASS.**

## (b) Tools and MCP

- Command: the worktree venv with `PYTHONPATH=sidecar`, the same imports as `test_no_trading_surface.py`. Script: `scratchpad/gate8-5/dump_tools.py`.
- Files: `gate8/tools-CAPABILITY_CATALOG.txt` (56, with kind), `tools-TOOL_SCHEMAS.txt` (56), `tools-KNOWN_TOOL_IDS.txt` (56), `tools-registered_tools.txt` (33) and `tools-mcp_list_tools.txt` (40).
- Live MCP: `tools/list` over streamable HTTP on `:52310/mcp/` → `tools-mcp-live-52310.txt` (40). It is **identical** to the in-process list. `GET /mcp/status` → `mcp-status-live.json` (`toolCount: 40`).
- Hits under the same term grep:
  - `get_portfolio` (per_invocation), and `portfolio_add_position`, `portfolio_update_position` and `portfolio_delete_position` (host_action). All four are the tracked portfolio.
  - `shareholding_pattern` (read_handler): disclosure data.
  - The live MCP surface's only hit is `shareholding_pattern`. The portfolio host actions are not projected to MCP.
- `FORBIDDEN_TOOL_SUBSTRINGS = ('place_order','submit_order','execute_order','auto_approve')`. **PASS.**

## (c) pytest

- Command: `sidecar/.venv/bin/python -m pytest -p no:cacheprovider tests/test_no_trading_surface.py -v` (PYTHONDONTWRITEBYTECODE=1). Output: `gate8/pytest-no-trading-surface.log`.
- Result: **8 passed, 1 warning, 0 failed, 0 skipped (1.43 s).**
- Test integrity: `git diff a122dbf6 HEAD` of this file (a122dbf6 is the newest `feat(d81)` merge). The two changes since then tighten the test and weaken nothing:
  - The legacy ledger is asserted `== {"GET"}` and has no `/{position_id}` route.
  - ProposedChangeKind is read from the `PROPOSED_CHANGE_KINDS` list it is derived from.

## (d) Grep

- Command: `rg -n -i` with the pattern `broker|place.?order|propose_order|order (entry|ticket|book|placement)|paper.?trad|simulat|live.?(trading|mode)|kill.?switch|audit_orders|margin|demat`.
  - Roots: `src sidecar src-tauri plugins docs`.
  - Excluded: `node_modules .venv target out .next binaries *.pyc __pycache__`. rg also honours `.gitignore` and skips hidden paths.
  - The pattern was not narrowed or widened.
- No hit touched `R15_BRIEF*` or `r15/local/`: a path count of 0 was checked before anything was read.
- Classification: `gate8/grep-classify.py`. It applies rules, plus 14 hand overrides written after reading each hit the rules left unclassified. Every hit is classified; 0 are unclassified.

| root | total | product | historical | false_positive |
|---|---:|---:|---:|---:|
| src | 111 | 0 | 27 | 84 |
| sidecar | 262 | 0 | 76 | 186 |
| src-tauri | 3 | 0 | 2 | 1 |
| plugins | 0 | 0 | 0 | 0 |
| docs | 195,857 | 0 | 160,230 | 35,627 |

- `gate8/grep-summary.json`: the counts above.
- `gate8/grep-product-hits.tsv`: header only (0 product hits).
- `gate8/grep-examples.tsv`: at most 200 rows per root per class. For src, sidecar and src-tauri that is every hit. The docs root is cut to 200 per class so the file stays under the 20 MB limit (it is 173 KB). No pattern was changed to shrink the raw count.

How the hits were classified:

- **src / sidecar / src-tauri, historical:**
  - Statements that the product has no brokerage: the ToS text, `agent-autonomy.ts`, the copilot/runtime prompt ("no brokerage connection: you cannot place, stage or simulate trades"), the catalog's portfolio tool descriptions, and the portfolio "no broker sync" docstrings.
  - Guard code and tests that pin the absence: `FORBIDDEN_TOOL_SUBSTRINGS`, `test_no_trading_surface.py`, `host-actions.test.ts` ("applyHostAction has no order path"), `DisclaimerFlow.test.tsx`, and `workspace.test.ts`, which drops removed broker panels from old blobs.
  - `keychain.rs:491/506`: a `#[test]` migration fixture that uses the old key name `broker:_meta:first-launch-tos` (renamed to `app-meta:first-launch-terms` by D81).
- **src / sidecar / src-tauri, false_positive:**
  - Financial "margin" metrics (gross/operating/net margin, margin of safety), CSS margins, and hardware-fit `MARGINAL`.
  - "OpenRouter is a (model) broker".
  - Listed-company names in the resolver masters (for example "Anand Rathi Share and Stock Brokers Ltd") and public-suffix-list entries.
  - "Live model catalog".
  - A corporate "order book" (revenue backlog) in test fixtures.
  - The historical-data backtest engine's simulated fills (`backtest_engine.py`, `run_custom_backtest.py`, "never touches order paths"). This is research over past prices, not a simulated account.
  - The strategy-critic persona's "might fail in live trading" critique.
  - A generic `EmptyState.test.tsx` fixture label "Connect broker". This is a component-test string rendered by no product surface.
- **docs, historical:**
  - 194,785 hits are under `docs/redesign/verification/` (evidence from past runs).
  - The rest: `docs/archive/`, `docs/research/phase-10/` (pre-D81 research notes), `docs/screenshots/` (v0.6.0 demos), and the dated run specs/reports under `docs/redesign/*.md`.
  - `PHASE_10_HANDOFF.md` has a "Historical … removed permanently (D81)" banner.
  - Every hit in `CURRENT_STATE.md`, `SAFETY_ARCHITECTURE.md` and `BROKER_INTEGRATIONS.md` was read in full; they are D81 removal records. The same holds for `BLUEPRINT.md` ("Trading … was removed permanently (D81)", and Phase 5 "removed permanently by D81"), `README.md` (the "Removal note" row) and `MCP_INTEGRATION.md` ("No broker tool exists").
- **docs, false_positive:** financial-metric margins, OpenRouter "broker", "live model" and similar.
- **Stale doc, not a product surface:** `docs/redesign/R12_HAND_TESTING_GUIDE.md:37` still describes an "Orders (the safety showcase)" tour and has no D81 banner. It is an operator-only hand-testing guide dated R12 (pre-D81) and is not shipped in the bundle, so it is classified historical. It is listed in the notes as doc hygiene, not as a gate failure.

**What the product tells the user about trading:**

- First-launch terms (`src/modules/safety/DisclaimerFlow.tsx`, `TOS_BODY`) say: *"Vysted Terminal is a data and analysis tool. It does not provide investment advice and is not a registered broker-dealer or investment adviser. … Vysted has no brokerage connection. It cannot place, route or simulate orders."*
- Settings (`SettingsPanel.tsx`) says nothing about trading. The only related word is the Region hint "…which market's symbol resolver, **trading calendar**, macro/news providers and screener universe the sidecar uses", which refers to a market calendar. There is no broker, order, paper or kill-switch setting.

**PASS.**

## Data dir: audit_orders

- Command: `sqlite3 -readonly <db> .tables` over every `.db` in my data dir → `gate8/datadir-tables.txt`.
- Result: there is no `audit_log.db`, and no table is named audit/order/broker/margin/paper/kill. The only tables are `positions`, `cache`, `meta`, `runs`, `fundamentals`, `plugin_configs`, `custom_agents`, `schedules` and `workflows`, and the legacy `positions` table has 0 rows. "audit_orders at zero rows" holds trivially: the table does not exist (D81 removed it).

## (e) Tracked portfolio end to end (:52310)

**Harness:**

- `git archive 9bc600ec` produced a scratch copy (`scratchpad/gate8-5/e2e-src`, with `node_modules` symlinked to the candidate's). The candidate worktree itself was not written to.
- A scratch vitest (jsdom) file, `gate8/portfolio-e2e-scratch.test.tsx.txt`, drives the real code: `PortfolioPanel` (the form, Edit, Delete ConfirmButton and Export buttons), the `portfolios`, `notes` and `symbols` stores, `PERSISTED_SLICES` (save and restore), `fetchPositionQuotes` + `buildPortfolioSummary`, `captureAgentContext`, and `useProposedChangesStore.enqueue/accept` (what `ChatSidebar.onToolUse` calls).
- Everything is persisted with the autosave body (`POST /workspace {name:"__autosave__"}`) and read back with `GET /workspace/__autosave__` on :52310.
- Two things are stubbed:
  - `saveTextArtifact`, the Rust file-write boundary. The stub captures the CSV text.
  - The dockview api, whose `toJSON` returns the saved layout (there is no dockview in jsdom).
- Results: `gate8/portfolio-e2e-crud.json` and `gate8/portfolio-e2e-apply.json`.

| # | step | result | evidence |
|---|---|---|---|
| 1 | Seed autosave restored through the global slices (empty default portfolio, seed watchlist) | pass | crud.json `seed-restore` |
| 2 | Add 3 through the panel form: RELIANCE.NS 10 @ 1200 (NSE), AAPL 5 @ 180 (US), MSFT 3 @ 400 with a note | pass | `add-3-via-panel-form` |
| 3 | Persist and read back: the blob holdings (ids, qty, cost, note) equal the store | pass | `persist+readback-after-add` |
| 4 | CSV via the panel Export button. Columns: `Symbol,Quantity,Cost basis,Asset class,Currency,Price,Market value,P&L,P&L %,Weight %,Note`; rows equal the holdings | pass | `portfolio-export-after-add.csv` |
| 5 | P&L recomputed from `/quotes/{sym}`: RELIANCE.NS 1226 INR (nse_direct) → +260; AAPL 341.07 USD → +805.35; MSFT 516.17 USD → +348.51. Recompute equals the panel's figures exactly; 0 % drift between the panel and raw quotes. Mixed currencies give per-currency subtotals, blank Weight %, and no cross-currency total | pass | `pnl-recompute-from-quotes` |
| 6 | Update AAPL to 7 @ 175 through Edit (same holding id); delete RELIANCE.NS through the Delete ConfirmButton (two clicks) | pass | `update-and-delete-via-panel` |
| 7 | Persist and read back; restore round trip from an emptied store through the slices | pass | `persist+readback-after-update-delete`, `restore-roundtrip` |
| 8 | CSV after the update: 2 rows equal the holdings. USD only, so weights are 60.66 / 39.34 | pass | `portfolio-export-after-update.csv` |
| 9 | Notes CRUD: create a general note and an MSFT note, update MSFT, delete both, reading the blob back after each step | pass | `notes-crud` |
| 10 | Watchlist CRUD: add INFY.NS (IN), read back, remove, read back; the list returns to the seed list | pass | `watchlist-crud` |
| 11 | Agent `get_portfolio` (llama3.1:8b, `--autonomy ask`, context from `captureAgentContext`): a `get_portfolio` call, ok. The reply lists AAPL 7 @ $175 and MSFT 3 @ $400, total 3936, market values 2387.49 / 1548.51, which equals the ledger | pass | `agent-get-portfolio.{jsonl,log}`, `agent-context-snapshot.json` |
| 12 | Gated write under `--autonomy ask`: "Add 4 shares of NVDA … at 120 dollars" produces `portfolio_add_position {NVDA, 4, cost_basis 120}` with the runtime notice "Staged for your review, not applied yet". The `__autosave__` blob is byte-identical before and after the run, so the ledger is unchanged | pass | `agent-add-position-ask.{jsonl,log}`, `blob-{before,after}-propose.portfolios.json` |
| 13 | Applied as the frontend does: `enqueue` returns `staged` with the store unchanged; `accept` returns `applied`; persist; read back holds AAPL, MSFT and NVDA 4 @ 120 | pass | apply.json `enqueue-stages-without-applying`, `accept-applies-and-persists`, `final-portfolio-blob.json` |
| 14 | Human accept fails closed on an order: `isHostActionMutation("propose_order")` is false, so the chat never stages it. `applyHostAction("propose_order")` returns null. A forged staged `propose_order` → `accept` = `failed` ("unknown action"), and holdings are unchanged | pass | apply.json `order-accept-fails-closed` |
| 15 | Order attempt halts (llama3.1:8b, **`--autonomy auto`**): "Buy 10 shares of RELIANCE at market…" produces no order tool (none exists). The model tried `portfolio_add_position` without a cost basis; the validator rejected it ("missing cost_basis — ask the user for it; do not guess"), so the R15-AGENT-022 fix holds. The reply says "Vysted has no brokerage connection. I can't place trades or simulate them." The blob is byte-identical | pass | `agent-order-attempt.{jsonl,log}` |

Observations that are not gate failures:

- Step 13's review title reads "Add 4 NVDA @ ₹120" for a USD listing under the default IN session region. This reproduces the open low **R15-LEAD-042**; it is a concurrence, not a new defect.
- In step 12 the model's prose opens "I've added…" and then says "pending review and will only be applied once you accept it". The runtime notice and the gate are truthful, and the ledger was unchanged.

**PASS.**

## Harness notes

- The first rg invocation failed on an invalid `--binary=false` flag and wrote empty files; it was rerun without the flag.
- The first e2e runs failed for harness reasons: `sidecar/config` was missing from the archive, and there is no dockview in jsdom.
- One aborted run persisted holdings. My own `__autosave__` was reset from the seed copy before the clean run; a stale vitest process from the aborted run was killed first.
- One bare `GET :11434/api/tags` reachability probe went out without the Ollama lock. It was not a model call. All three model calls held the lock.
