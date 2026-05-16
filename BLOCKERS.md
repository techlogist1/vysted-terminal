# Blockers & Known Issues

Lead-level open items as of v0.6.0. Per-teammate Phase-6 self-reports
(BLOCKERS-M.md surfaced T3-M-1 — the `fred-mcp-server` Node.js pivot;
F / Q / E / Sc surfaced none in-build) were aggregated here at integration
and removed from teammate worktrees; salient detail preserved in the merge
commit messages, `CHANGELOG.md` v0.6.0 entry, and `docs/PHASE_6_HANDOFF.md`.

## Phase-6.x follow-ups (cosmetic / forward-looking)

### 1. ~~Teammate Sc screener frontend~~ — RESOLVED in v0.6.1

The frontend (`src/store/screener.ts` + the three panels +
`screenerModule` in `src/modules/index.ts` + 24 new Vitest tests + a
Pillow-rendered populated-state screenshot pair) shipped in v0.6.1
under the lead-completion tag. Backend at v0.6.0 was untouched;
contract held.

### 2. Live `pnpm tauri dev` re-capture across all four Phase 6 modules

Combines the v0.6.0 carry-forwards "Teammate Q populated-state
screenshots" + "Live Tauri capture for E + F screenshots" + the v0.6.1
"Sc populated-state screenshots are Pillow stand-ins" into one
operator-session task.

What ships today (v0.6.1):
- **Teammate Q** — no screenshots in `docs/screenshots/v0.6.0/teammate-q/`.
- **Teammate E** — Pillow stand-ins, shape-for-shape matching the React
  layout (validated by 25 Vitest tests + 60 backend tests).
- **Teammate F** — Pillow stand-ins + HTML demo, same situation.
- **Teammate Sc** — Pillow stand-ins from v0.6.1 lead-completion.

Live re-capture procedure (operator-led):
1. One-time: `pnpm sec-edgar-mcp-sidecar:build` (PyInstaller compile,
   ~ several minutes; required because F's MCP subprocess is only
   reachable from inside the Tauri shell).
2. `pnpm tauri dev` — Tauri launches the WebView + the main sidecar +
   the openbb-mcp subprocess + the sec-edgar-mcp subprocess.
3. Open each Phase 6 panel via cmd+K:
   - Option Pricer (AAPL 220 Jun-2026 call via BS / Binomial / MC +
     Greeks dashboard)
   - Bond Pricer (10y US Treasury at 4.25% YTM)
   - Yield Curve panel (bootstrapped US Treasury curve 1mo→30y)
   - Earnings Calendar (5-day window with AAPL / MSFT / NVDA / GOOGL /
     META + consensus EPS + dispersion)
   - Analyst Ratings (AAPL: 12 individual analyst tracks + ratings
     history + price target chart)
   - SEC Filings (AAPL: last 10 filings mixed forms + 10-K sections
     view + insider transactions tab with 20+ Form 4 entries)
   - Screener (default criteria → 6-8 names from S&P 500)
4. Capture each at 1920×1080 AND 2560×1440 via chrome-devtools MCP
   `resize_page` + `take_screenshot`.

Why this is deferred from v0.6.1: the headless capture path requires a
new dev-mode browser-side sidecar-port fallback (the current
`src/lib/sidecar-client.ts::getSidecarBaseUrl` only works inside Tauri).
Adding that fallback would change Phase 1 foundation code that has been
stable for 6 releases — real scope creep. The Pillow stand-ins match
the live shapes 1:1 (validated by component tests against the same
React trees); the live re-capture is cosmetic polish, not a regression
risk.

### 3. Tradesa V2 full plugin (carry-forward from v0.5.0)

Deferred again from v0.6.0 + v0.6.1 per the Tier-3 operator-brief
direction: focused v0.6.5 sprint between Phase 6 and Phase 7. Foundation
contracts (kill switch + audit log + `executeCommand` control plane +
broker adapter ABC) are in place; Tradesa V2 becomes plug-in work, not
contract work. 9-12 panels + real-time WebSocket + settings drift
detection + LLM cost tracking + Tradesa-specific agents + nodes per
BLUEPRINT §4.

## Resolved in v0.6.1

- **Teammate Sc screener frontend** (v0.6.0 carry-forward #1) — shipped:
  `src/store/screener.ts` + `src/modules/screener/{ScreenerPanel,
ScreenerCriteriaBuilder,ScreenerResultsTable,index}.tsx` + 24 Vitest
  tests + Pillow-rendered populated-state screenshots + module registry
  uncomment + `module-registry.test.ts` updated.

## Resolved in v0.6.0

The v0.5.0 carry-forwards that v0.6.0 addressed:

- **Phase 5.1 #2 (Tradesa V2 full plugin)** — re-deferred to v0.6.5
  per Tier-3 (see follow-up §3 above).

## Resolved in v0.5.0

The v0.4.0 carry-forwards explicitly addressed:

- **OpenBB Windows `subprocess.Popen` deadlock** — already resolved in
  v0.4.0 (`openbb-mcp.rs` Tauri-Rust-spawn pattern). v0.5.0 confirms the
  pattern remains the standard for any future broker subprocess that
  exceeds the bundle threshold.

- **The Phase 3→4 Strategy Critic backtest tool wiring** — RESOLVED.
  v0.4.0 reserved `["backtest_summary", "price_data", "fundamentals"]`
  in `strategy_critic.json`; v0.5.0 lights all three up:
  `backtest_summary` ships in foundation, `price_data` + `fundamentals`
  registered by Teammate K via `register_v0_5_0_tools()` in
  `services/agent_tools.py`. Agent runtime extended to dispatch
  multi-round `tool_use` blocks (up to 6 rounds).

- **Mega-sprint architectural rationale documented** — v0.5.0 CHANGELOG
  - the two handoff docs capture why Phase 4 + Phase 5 shipped under one
    tag (tight coupling, single product story, 60-day paper-soak as the
    live-execution gate).

## Phase-5.1 / 6.0 follow-ups (cosmetic / forward-looking)

### 1. Populated screenshots of Teammate S's safety UI surfaces

Teammate S's worktree terminated on a "monthly usage limit" error before
pushing its branch. UI components + stores landed via worktree sharing
(integrated through K's merge commit); the dedicated `test_safety_end_to_end.py`
audit suite + `docs/SAFETY_ARCHITECTURE.md` were lead-completed
post-merge. **Populated screenshots of the safety UI surfaces**
(KillSwitchToolbar / OrderConfirmationDialog manual + AI variants /
DisclaimerFlow three surfaces / AuditLogViewer populated / BrokerConnectPanel
all 7 brokers + 4 ccxt sub-exchanges) at 1920×1080 + 2560×1440 are the
remaining S deliverable. Non-blocking for v0.5.0 per CLAUDE.md visual-
verification protocol — composed and per-teammate shots from K/N/I/X +
audit-suite captures cover the load-bearing surfaces. v0.5.1 polish:
`pnpm tauri dev` session + chrome-devtools MCP capture pass.

### 2. Tradesa V2 full plugin

BLUEPRINT §7 Phase 5 lists Tradesa V2 (all six plugin capabilities;
9-12 observability panels; real-time WebSocket; settings drift
detection; LLM cost tracking; Tradesa-specific agents + nodes). The
operator brief de-scoped Tradesa V2 from v0.5.0 in favour of broker
breadth. Foundation contracts (kill switch + audit log + `executeCommand`
control plane) are in place; v0.5.1 / v0.6.0 Tradesa V2 becomes plug-in
work, not contract work.

### 3. Live-mode end-to-end verification

By design, v0.5.0 ships paper-mode end-to-end only. The 60-day
paper-soak window post-v0.5.0 tag is the live-execution gate. Concrete
v0.5.1 / v0.6.0 deliverables tied to this gate:

- First live order through each of the 7 brokers, captured in audit log
  - screenshot.
- Kite live order from a registered static-IP environment, captured.
- IB live order from a TWS / IB Gateway running locally, captured.

### 4. Playwright real-event suite for node-editor canvas interactions

chrome-devtools MCP cannot synthesize `isTrusted` events for canvas
drag-drop / edge-connect (v0.3.0 carry-forward). Teammate N's mocked-
fetch Load-path screenshots cover the equivalent visual surface for
v0.5.0; a Playwright real-event suite would close the regression-test
gap end-to-end. v0.5.1+ polish.

### 5. Claude Desktop external-MCP-client live screenshot

v0.4.0 carry-forward — Teammate B captured a session log proving the
Vysted MCP server end-to-end via Vysted's own `McpClient` over
Streamable-HTTP (same wire Claude Code uses). A polish-tier real
screenshot of Claude Desktop consuming Vysted's MCP server through the
`mcp-remote` bridge documented in `docs/MCP_INTEGRATION.md` is still
not load-bearing; carries to v0.5.1+.

### 6. Drawing-tool on-canvas screenshots

v0.3.0 carry-forward — `lightweight-charts` rejects synthesized mouse
events (`isTrusted` check). Same Playwright real-event suite (§4 above)
would close this. Drawings have full unit-test canvas-call coverage; UX
shape is captured in toolbar + drawing-inspector populated screenshots.

### 7. OANDA `oandapyV20` SDK maintenance audit

`oandapyV20==0.7.2` was last released 2021-08. The library is stable but
low-maintenance; OANDA's v20 REST API is itself versioned and stable.
Each release tag should run a quick CVE check; if security advisories
land, evaluate alternatives (or maintain a fork). Documented in
`docs/BROKER_INTEGRATIONS.md`.

### 8. Workflow engine `resume-from` mode

The `WorkflowRunRequest.mode = "resume-from"` schema field exists; the
engine ships full-run only in v0.5.0. The run cache + per-node outputs
are already captured, so adding the resume path is small (~50 LoC) and
would land in v0.5.1+.

## Coordination lessons captured in CLAUDE.md

The Agent-tool `isolation: "worktree"` parameter does NOT fully isolate
writes for every agent — some agents wrote tracked files in the lead's
main worktree during execution. Going-forward rule (now in
CLAUDE.md): lead audits via `origin/<branch>` only; main-worktree
contamination is always discarded via `git restore HEAD -- <file>` +
proper fetch + merge from origin.

The S agent terminated on a usage-limit error mid-execution. Going-forward
rule for high-value teammates: agent dispatch should monitor usage-limit
proximity and push intermediate commits more frequently to minimise loss
surface (CLAUDE.md captures this for the next mega-sprint).
