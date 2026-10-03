# Gate 8 (D81) — gate round 6-rc2 — rc1-gate8

Candidate `ace7dd768c3b809b0e72b20b20cfc94eea2368bd` (worktree `scratchpad/rc1-round-6-rc2-cand`, HEAD verified).
Own sidecar: candidate `sidecar/` source, `--port 52310`, data dir `scratchpad/rc1-round-6-rc2-data-rc1-gate8`
(copy of the seed). Sleep pid 49015 / worker 49016; stopped by killing 49015 only. Shared stack and the live app were not touched.

**Verdict: PASS.** No order, broker or simulated-account path at any layer, and the tracked portfolio works end to end.

Scratch dir (never committed): `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/454f42d1-ac9f-4d44-ba99-216c6bad682f/scratchpad/gate8-6-rc2/`
holds the raw rg dumps (`<root>.txt`), the classifier (`classify.py`), the tool-dump and MCP client scripts, and the headless e2e code (`e2e/p1.e2e.tsx`, `e2e/p3.e2e.tsx`, `e2e/vitest.config.mts`).

## (a) Routes — PASS

- Command: `curl 127.0.0.1:52310/openapi.json` → `gate8/openapi.json`. Every method+path → `gate8/openapi-paths.txt` (111 lines).
- `grep -iE 'order|broker|kill|audit|margin|paper|simulat|safety|static.?ip|disclaimer|holding|position'` → `gate8/openapi-hits.txt`:
  - `GET /disclosures/shareholding`: NSE/BSE shareholding-pattern filings (corporate disclosure data). Not trading.
  - `GET /portfolio/positions`: the legacy tracked-portfolio ledger. It is GET-only and read once for import (R15-CODE-PLATFORM-021). Holdings live in the workspace blob.
- No `/brokers`, `/orders`, `/safety`, `/kill-switch`, `/audit-log`, `/margins`, `/static-ip*` or `/disclaimer-*` route exists. The `/mcp` mount is a Starlette mount, so it is absent from openapi. It is covered in (b).

## (b) Tools — PASS

- Command: `PYTHONPATH=<cand>/sidecar <cand>/sidecar/.venv/bin/python scratch/dump_tools.py` (the same imports and registration as `test_no_trading_surface.py`).
- `gate8/tools-CAPABILITY_CATALOG.txt` (56, id + kind), `tools-TOOL_SCHEMAS.txt` (56), `tools-KNOWN_TOOL_IDS.txt` (56), `tools-registered_tools.txt` (33), `tools-mcp_list_tools.txt` (39).
- Live MCP surface: initialize + `tools/list` over streamable HTTP at `http://127.0.0.1:52310/mcp/` → `gate8/tools-mcp-live-52310.txt` (39 tools, byte-identical to the in-process list). `/mcp/status`: `{"ready":true,"toolCount":39}`.
- `FORBIDDEN_TOOL_SUBSTRINGS = ('place_order','submit_order','execute_order','auto_approve')`.
- Hits for order|broker|kill|audit|margin|paper|simulat|safety|trade|trading|position|holding|portfolio:
  - `get_portfolio` (per_invocation), plus `portfolio_add_position`, `portfolio_update_position` and `portfolio_delete_position` (host_action). These are the tracked portfolio, and their writes are staged through the proposed-changes gate as `data-write`.
  - `shareholding_pattern` (read_handler): disclosure data.
  - Nothing else matched. No order, broker or kill-switch tool exists on any surface.

## (c) pytest — PASS

- Command: `cd <cand>/sidecar && <main-repo>/sidecar/.venv/bin/python -m pytest tests/test_no_trading_surface.py -v`. The candidate venv has no pytest, so the main repo's dev venv ran the candidate's files. `REPO_ROOT` is derived from the test file path, so the scans cover the candidate tree.
- Result: **8 passed, 0 failed, EXIT=0** (`gate8/pytest-no-trading.txt`). This includes routes, the catalog and its projections, the MCP surface, module absence, file absence, identifier scan, `ProposedChangeKind` having no `order`, and the legacy ledger staying read-only.
- Gate source checked: `types/proposed-change.ts` `PROPOSED_CHANGE_KINDS = [chart, panel, watchlist, data-write, settings]` and `AUTO_APPLIED_KINDS = [panel, chart, watchlist]`. `data-write` (portfolio) is never auto-applied.
- `kill_switch`, `audit_log` and `brokers` are absent, as D81 expects.

## (d) Source/docs grep — PASS (0 product-surface hits)

- Command (candidate worktree): `rg -n -i -e 'broker|place.?order|propose_order|order (entry|ticket|book|placement)|paper.?trad|simulat|live.?(trading|mode)|kill.?switch|audit_orders|margin|demat' <root>`. Excluded: `node_modules`, `.venv`, `target`, `out`, `.next`, `binaries`, image/db files; rg also honours `.gitignore`. Output went to the scratch dir only (`docs.txt` is 198,416 lines / 120 MB, which is why it never goes under the evidence dir).
- Every hit was classified by `scratch/classify.py`, and the residual was reviewed by hand. These are the rules, applied in order:
  1. Lines carrying only weak tokens are **false_positive**: CSS `margin`, financial gross/operating/net margin, `marginal`, test or backtest "simulate", and "LIVE model catalog".
  2. Third-party data is **false_positive**: resolver masters (listed companies named "… Stock Brokers Ltd"), the public-suffix list (`broker` TLD) and exchange fixtures.
  3. `broker` meaning OpenRouter as an LLM routing broker is **false_positive**. So is "order book" meaning a company's revenue backlog (BDL, CG Power).
  4. **historical**:
     - everything under `docs/redesign/verification/`, `docs/archive/`, `docs/research/`, `docs/redesign/*` (internal build records) and `docs/PHASE_*_HANDOFF`
     - current docs and source lines that state the removal: "no brokerage connection", "cannot place, route or simulate orders", "removed permanently (D81)", the forbidden-substring lists
     - tests that pin the absence
     - the `src-tauri/src/keychain.rs` migration-test fixture, which uses the old `broker:_meta:first-launch-tos` key
  5. Everything else counted as **product** until reviewed. 36 lines landed there. Every one was read in context and reclassified with a named reason (manual overrides listed in `classify.py`). Some were "live model" LLM comments. Some were safety comments naming the forbidden substrings. One was `models/backtest.py` "simulated fill" (the backtest engine, kept by BLUEPRINT's v1.0 scope; it is not a simulated account). The rest were continuation lines of D81 removal paragraphs in `CURRENT_STATE.md`, `SAFETY_ARCHITECTURE.md`, `BROKER_INTEGRATIONS.md` and `RELEASE_RUNBOOK.md` ("do not re-ship pre-D81 tags"), plus `BLUEPRINT.md:511`, whose header is followed by "Shipped v0.5.0; removed permanently by D81".

| root | total | product | historical | false_positive |
|---|---|---|---|---|
| src | 117 | 0 | 24 | 93 |
| sidecar | 262 | 0 | 67 | 195 |
| src-tauri | 3 | 0 | 2 | 1 |
| plugins | 0 | 0 | 0 | 0 |
| docs | 198416 | 0 | 152649 | 45767 |

- Evidence: `gate8/grep-summary.json`, `gate8/grep-product-hits.tsv` (header only: 0 rows) and `gate8/grep-examples.tsv` (at most 200 rows per root per class, 169 KB). No pattern was widened or dropped. The examples file was capped at 200 rows from the start; none of this round's files is near 20 MB.
- **First-launch terms** (`src/modules/safety/DisclaimerFlow.tsx:28-35`): "Vysted Terminal is a data and analysis tool. It does not provide investment advice and is not a registered broker-dealer or investment adviser. … Vysted has no brokerage connection. It cannot place, route or simulate orders." `DisclaimerFlow.test.tsx:58-67` pins it, including that there is no kill-switch or connect-a-broker text.
- **Settings** (`src/components/SettingsPanel.tsx`) contains no trading, broker or order-placement copy. Its only "order" hits are the LLM provider *fallback order*. `SettingsPanel.test.tsx:510` pins "OpenRouter is never labelled a broker".
- The agent system prompt (`sidecar/services/agent_runtime.py:166`) says: "no brokerage connection: you cannot place, stage or simulate trades".

## (e) Tracked portfolio end to end on :52310 — PASS

Headless runs used scratch vitest/jsdom code with root set to the candidate (`e2e/vitest.config.mts`, page URL `?sidecar-port=52310`). They render the real `PortfolioPanel` and real stores, and use real `fetch` against :52310. Two things were substituted. First, `downloadCsv` is mocked to capture the CSV string, as `PortfolioPanel.test.tsx` does. Second, with no dockview mounted, `dockviewApi.toJSON` is stubbed to `{}`; that is the only dockview call `saveWorkspace` makes.

| step | result |
|---|---|
| Add via the panel form: RELIANCE.NS 10 @ 1200 (NSE), AAPL 5 @ 200 (US), MSFT 3 @ 400 with note "gate8 thesis: cloud margin" | store reads back all 3 with the note (`portfolio-e2e-p1.json` `added`) |
| P&L recompute from my own `GET /quotes/{sym}` | RELIANCE 1167.7 INR → −323 vs CSV −323. AAPL 333.69 → 668.45 vs 668.45. MSFT 517.53 → 352.59 vs 352.59. **3/3 match** |
| CSV export via the panel's Export button | 11 columns (Symbol, Quantity, Cost basis, Asset class, Currency, Price, Market value, P&L, P&L %, Weight %, Note). 3 rows = 3 holdings, symbols match, note carried. Weight % is blank for a mixed INR/USD book (R15-DATA-042 rule) |
| Update (panel Edit AAPL → qty 8) | AAPL 8 @ 200 |
| Delete (panel ConfirmButton, 2 clicks, RELIANCE.NS) | 2 holdings left |
| Notes CRUD | general set; AAPL set then updated to v2; MSFT set then cleared → `symbolsWithNotes = [AAPL]` |
| Watchlist CRUD | +NVDA, +TCS (IN) then −NVDA → final list carries TCS, no NVDA |
| Persist: `saveWorkspace("gate8-e2e")` → `POST /workspace`; `GET /workspace/gate8-e2e`, stores reset, global slices restored | holdings, notes and watchlist **all match** |
| Agent `get_portfolio` (llama3.1:8b, `--autonomy ask`, context from `captureAgentContext()` mapped to the wire shape exactly as `streaming.ts:225-229` does) | tool_use `get_portfolio` ok. Answer lists AAPL qty 8 cost 200, MV 2669.52, P/L 1069.52 and MSFT qty 3 cost 400, MV 1552.59, P/L 352.59. **Figures match the ledger.** It prints "₹" for USD holdings even though `currency: "USD"` is in the payload (low finding rc1-gate8:1) |
| Gated write: "add 4 NVDA at 180" under `--autonomy ask` | tool_use `portfolio_add_position {NVDA,4,180}`, then runtime notice "Staged for your review, not applied yet". Sidecar ledger unchanged (workspace blob sha `b142bb6f…` before and after, `/portfolio/positions` `[]` before and after) |
| Apply as the frontend does (ChatSidebar `onToolUse` → `enqueue`, autonomy ask → `accept(id)`) | enqueue outcome `staged`, kind `data-write`, status `pending`. Ledger unchanged while pending. `accept` → `applied`; NVDA 4 @ 180 added; saved and read back → **match** (`portfolio-e2e-p3-gated-apply.json`) |

The review-card title reads "Add 4 NVDA @ ₹180" for a US lot under the IN default region. That is the open low **R15-LEAD-042** (already in the register), not a new finding.

The first agent run was a harness error: the context file used the frontend's camelCase keys, so the sidecar saw an empty `by_source`. It is kept as `agent-get-portfolio-run1-harness-camelcase.*` and was rerun with the wire shape.

The Ollama lock (`/tmp/vysted-r15-ollama.lock`) was held for each of the 3 llama calls and released by trap. There were no lock timeouts.
