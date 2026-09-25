# RC1 Gate 8: no trading path, tracked portfolio end to end

Candidate `4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a` (rc1-cand worktree, read-only). Own sidecar
started from `rc1-cand/sidecar` on :52310 with a copy of `rc1-seed-data` (`rc1-data-rc1-gate8`),
MCP env set to the shared :52153/:52154. It was stopped by killing its own sleep pid (59904).
Raw outputs are in `gate8/`. Summary: `gate8.json`. Findings: `findings/rc1-gate8.json`.

**Verdict: FAIL, on one document only.** No order, broker or simulated-account route, tool, MCP
tool, module, setting or UI string exists in code. The tracked portfolio passes all 13 steps.
The one failure is a user-facing doc: `docs/PHASE_10_HANDOFF.md`. `docs/README.md` indexes it as
the "Latest phase handoff", and it still explains how to connect Kite (finding rc1-gate8:1).

## (a) Routes

Command: `curl /openapi.json` → `gate8/openapi-paths.txt` (111 method+path rows, 101 paths). The
same dump from `app.routes` → `gate8/app-routes.txt` (117). The difference is `/docs`, `/redoc`,
`/openapi.json`, the `/mcp` mount, the `/crypto/stream` websocket and the `:path` converters.

`grep -iE 'order|broker|kill|audit|margin|paper|simulat|safety|static.?ip|disclaimer|holding|position'`
(`gate8/openapi-paths-grep.txt`):

```
GET /disclosures/shareholding
GET /portfolio/positions
```

- `/disclosures/shareholding` is the NSE/BSE shareholding-pattern data route. Not trading.
- `/portfolio/positions` is the tracked portfolio's legacy ledger. It is GET-only and read once for
  import (R15-CODE-PLATFORM-021). There is no POST/PUT/DELETE on it.

No `/brokers`, `/orders`, `/safety`, `/kill-switch`, `/audit-log`, `/disclaimer-*` or `/static-ip`
route exists. **PASS.**

## (b) Tools

Command: `gate8_tools.py` in the rc1-cand venv (the imports `test_no_trading_surface.py` uses).
Output files:

- `tools-CAPABILITY_CATALOG.txt` (56)
- `tools-TOOL_SCHEMAS.txt` (56)
- `tools-KNOWN_TOOL_IDS.txt` (56)
- `tools-registered_tools.txt` (33)
- `tools-default_grant.txt` (55)
- `tools-mcp_list_tools.txt` (40)
- the live `/mcp/` surface on :52310 via a FastMCP client → `tools-mcp-live-52310.txt` (40; `/mcp/status` says toolCount 40)
- full schema text → `tools-TOOL_SCHEMAS-full.json`, grepped into `tools-TOOL_SCHEMAS-desc-grep.txt`

What the hits are:

- `portfolio_add_position` / `portfolio_update_position` / `portfolio_delete_position` are the
  tracked portfolio's host actions (kind `host_action`). Each description says "Edits the user's
  local tracked portfolio (manual holdings). Vysted has no brokerage connection."
- `shareholding_pattern` is data.
- "margins" in `fundamentals`, `compare_symbols` and `financial_statements` means profit margins.
- `run_custom_backtest` "SIMULATED backtest engine" is the historical backtest. It is kept: the
  BLUEPRINT v1.0 scope lists "backtest engine", and D81 removed simulated *accounts*.

`catalog.FORBIDDEN_TOOL_SUBSTRINGS = ('place_order','submit_order','execute_order','auto_approve')`.
No trading id appears on any surface. **PASS.**

## (c) pytest

Command: `sidecar/.venv/bin/python3 -m pytest tests/test_no_trading_surface.py -v -p no:cacheprovider`
→ `gate8/pytest-no-trading.txt`. Result: **8 passed**, 1 unrelated Starlette deprecation warning. **PASS.**

## (d) Source and doc grep

Command: `rg -n -i` with the pattern
`broker|place.?order|propose_order|order (entry|ticket|book|placement)|paper.?trad|simulat|live.?(trading|mode)|kill.?switch|audit_orders|margin|demat`.
It ran over each root of rc1-cand and skipped node_modules, .venv, target, out, .next, binaries and
images. The raw hits are in `gate8/grep-<root>.txt`. Every hit is classified in
`gate8/grep-<root>.classified.tsv` (class, reason, hit) by `scratchpad/gate8_classify.py`. No hit
was left unclassified.

| root | total | product | historical | false positive |
|---|---|---|---|---|
| src | 111 | 0 | 21 | 90 |
| sidecar | 244 | 0 | 71 | 173 |
| src-tauri | 3 | 0 | 2 | 1 |
| plugins | 0 | 0 | 0 | 0 |
| docs | 5414 | **11** | 5401 | 2 |

How each class was decided:

- **False positives:**
  - `margin` means profit, operating or gross margin, margin of safety, CSS margin, the hardware-fit
    verdict "marginal", or the ECB marginal lending rate.
  - OpenRouter described as an LLM "broker".
  - Listed company names in the instrument masters ("Anand Rathi Share and Stock Brokers",
    "Simulations Plus").
  - "order book" as a company's backlog in research text.
  - `dematerialisation` in a BSE filing.
  - The backtest's simulated fills.
  - Test-harness "simulate" wording.
  - The generic `EmptyState` test fixture ("Connect broker"), which renders no product surface.
  - A fake plugin id `broker` in the marketplace boot-guard test.
  - The strategy-critic prompt's "fail in live trading" (critique voice, no path).
- **Historical, or a statement of absence:**
  - The terms text.
  - The copilot prompt "Vysted has no brokerage connection; if asked to trade, say so" (`agents/copilot.json`, `agent_runtime.py:172`).
  - `agent-autonomy.ts:15-16`.
  - `catalog.py:19-22`.
  - The guard tests (`test_no_trading_surface.py`, the `place_order|submit_order|execute_order` audits, `host-actions.test.ts` "no order path").
  - The legacy-blob fixtures showing that a removed `broker-connect-panel` is dropped on restore.
  - The Rust keychain-migration fixture `broker:_meta:first-launch-tos` (renamed `app-meta:first-launch-terms`, D81).
  - In docs:
    - everything under `docs/archive/`, `docs/redesign/verification/`, `docs/research/` and `docs/screenshots/`
    - the dated `docs/redesign/*` specs, briefs and reports (pre-D81 build history and the D81 decision itself)
    - the D81 removal notices in BLUEPRINT, SAFETY_ARCHITECTURE, CURRENT_STATE, BROKER_INTEGRATIONS, MCP_INTEGRATION, README and KEYCHAIN_DEV_SIGNING
- **Product surface (FAIL):** all 11 hits are in `docs/PHASE_10_HANDOFF.md`. `docs/README.md:32` lists
  it as "Latest phase handoff". Lines 116-140 read:

  > ## 3. Broker + integrations hub — how to connect Kite (Phase E, headline)
  > **Where:** Settings → **Integrations** (the discoverable surface) lists Zerodha, Dhan, Angel One with a Connect button. ...
  > New `GET /brokers/{id}/positions|holdings|margins`, `POST /brokers/{id}/disconnect` ... The `broker_portfolio` agent tool lets the copilot analyse your **real** account

  The file has no D81 notice. Finding **rc1-gate8:1** (gate8, medium). The fix is doc-only:
  archive the file to `docs/archive/` or give it a D81 notice, and repoint the README index.

`docs/redesign/R12_HAND_TESTING_GUIDE.md:37` has an "Orders (the safety showcase)" step. It is a
dated R12 phase record under `docs/redesign/`, so it is classed as historical. Archiving it
alongside rc1-gate8:1 would be a cheap tidy-up.

### What the product itself says about trading

- **First-launch terms** (`src/modules/safety/DisclaimerFlow.tsx:28-32`): "Vysted Terminal is a data
  and analysis tool. It does not provide investment advice and is not a registered broker-dealer or
  investment adviser. ... Vysted has no brokerage connection. It cannot place, route or simulate
  orders." The kill-switch promise is gone, and `DisclaimerFlow.test.tsx` pins that.
- **Settings** (`src/components/SettingsPanel.tsx`): there is no trading, broker, order or
  position-limit setting. The only trading word is the Region hint at :1422: "which market's symbol
  resolver, trading calendar, macro/news providers and screener universe the sidecar uses". The
  autonomy doc (`src/store/agent-autonomy.ts:15`) says: "Vysted has no brokerage connection, so no
  host action can place, stage or simulate a trade in any mode."

## (e) Tracked portfolio, end to end on :52310

The harness is a scratch vitest (`scratchpad/gate8-e2e/portfolio.gate8.test.tsx`, never committed).
Its config has root=rc1-cand, a scratch cacheDir and jsdom. It drives the real stores, the real
`PERSISTED_SLICES` restore, the `/workspace` POST body that `flushAutosave` sends, and the real
`PortfolioPanel`, against live :52310. Only `downloadCsv` is replaced, to capture the file.
`git status` in rc1-cand stayed clean. Step results are in `gate8/portfolio-steps-crud.json` and
`gate8/portfolio-steps-apply.json`.

| # | step | result | evidence |
|---|---|---|---|
| 1 | Add 3 holdings: RELIANCE 10 @ 1100 (NSE), AAPL 5 @ 180 (US), INFY 20 @ 1500 with note "Core IT holding, review after Q2 results" | ok | `portfolio-01-after-add.blob-portfolios.json` |
| 2 | Read back: GET blob equals the store; empty the store, restore the slice from the blob, equal again | ok | same |
| 3 | P&L: the panel's published mv/pnl equal an independent `(price − cost) × qty` from raw `/quotes`. RELIANCE 1219.2 → +1192 ₹; AAPL 335.92 → +779.60 $; INFY 1014.5 → −9710 ₹ | ok | `portfolio-02-panel-bus-payload.json`, `portfolio-02-raw-quotes.json` |
| 4 | CSV through the panel's own Export button: header `Symbol,Quantity,Cost basis,Asset class,Currency,Price,Market value,P&L,P&L %,Weight %,Note`, 3 rows, each matching the holding and the recompute. Weight % is blank because currencies are mixed (R15-DATA-042). The quoted note survives. | ok | `portfolio-03-export.csv` |
| 5 | Update AAPL to 8 @ 190 with note "added on dip", delete RELIANCE, read back (2 holdings) | ok | `portfolio-04-after-update-delete.blob-portfolios.json` |
| 6 | Notes: create (general + INFY), read, update, delete, each read back from the blob | ok | `portfolio-05-notes.json` |
| 7 | Watchlist: add RELIANCE, read, remove QQQ, read | ok | `portfolio-06-watchlist.json` |
| 8 | Agent context captured exactly as the chat does (`captureAgentContext`) | ok | `agent-context.json` |
| 9 | Agent (llama3.1:8b, `--autonomy ask`): "What is in my portfolio?" makes `tool_use get_portfolio`. The context portfolio equals the blob ledger (ids, qty, cost). The reply lists AAPL 8 and INFY 20 with the right cost bases, but writes AAPL's as "₹190" (finding rc1-gate8:2, low). | ok | `agent-01-get-portfolio.{stdout,jsonl}` |
| 10 | Gated write: "I bought 5 shares of TCS at 3500 rupees each. Add them" makes `tool_use portfolio_add_position {symbol:TCS, quantity:5, cost_basis:3500}`, then `research_step` "Staged for your review, not applied yet". After the turn the blob portfolios are byte-identical (`cmp` → LEDGER_UNCHANGED) and `/portfolio/positions` is `[]`. | ok | `agent-02-add-position.{stdout,jsonl}`, `agent-00-…before.json`, `agent-03-…after-propose.json` |
| 11 | Apply it as the frontend does: `useProposedChangesStore.enqueue` (autonomy ask) returns `staged` (kind `data-write`, "Add 5 TCS @ ₹3,500 to the portfolio"). Store and blob are unchanged while it is pending. | ok | `portfolio-steps-apply.json` |
| 12 | `accept(id)` returns `applied`. Read back: blob holds AAPL, INFY and TCS 5 @ 3500. | ok | `portfolio-07-after-apply.blob-holdings.json`, `agent-04-blob-portfolios-after-apply.json` |

**Tracked portfolio: PASS (13/13 steps, including the context capture).**

## Stack hygiene

- The shared :52152/:52153/:52154 stack was only read.
- Only my own :52310 sidecar was written to, and it is stopped (sleep pid 59904 killed; the port is free).
- rc1-cand was never edited, installed into or built.
- Both agent runs were free and local (Ollama). The spend ledger was read first.
