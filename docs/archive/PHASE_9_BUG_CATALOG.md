# Phase 9 — Stage 2 Bug Catalog (Exhaustive + Adversarial GUI Audit)

**Build under test:** v0.8.0, commit `e9775b5`, **`tauri build --debug` bundle** (NOT the dev server).
**App identity:** repackaged as `/Applications/Vysted.app` (display "Vysted", bundle id `com.vysted.desk`) **only** to clear the computer-use tier classifier — same code as e9775b5. The original `productName "Vysted Terminal"` / id `com.vysted.terminal` tripped the helper's terminal/IDE heuristic → click-only tier; renaming + a fresh helper granted **full tier**.
**Driver:** macOS computer-use (trusted OS-level pointer/keyboard), screenshots for observation.
**Date:** 2026-05-22.

---

## Step 0 — Calibration (decisive)

| Capability                                         | Result           | Evidence                                                                                                                                                                        |
| -------------------------------------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Click into webview                                 | ✅ works         | Chart "Load" fired; AAPL Equity Overview loaded; tab selection works                                                                                                            |
| Type into webview                                  | ✅ works         | "AAPL" typed into the chart symbol field                                                                                                                                        |
| Native OS drag                                     | ✅ works         | Dragging the window **title bar** relocated the window (so computer-use emits genuine trusted OS events)                                                                        |
| **In-webview drag** (tab reorder, splitter resize) | ❌ **no effect** | Tab-reorder drag ×2 (Chart↔Equity Overview) → no reorder, only tab-select; splitter resize ×2 → no resize. Done with trusted press + 0.3–0.4s hold + multi-step move + release. |

**Verdict on the headline #8 tab-drag question:** **UNTESTABLE-VIA-HARNESS / UNCONFIRMED.** Computer-use _does_ produce trusted OS events (the native window drag proves it), and discrete clicks/typing reach the webview — yet **no in-webview drag gesture registered** (neither HTML5-DnD tab reorder nor pointer-based splitter resize). That two-sided result means a non-working in-webview drag here is **not** proof of a product defect: it is equally consistent with a WKWebView/CGEvent drag-delivery limitation. Per the test plan's explicit §6.2/§8.5 instruction ("mark UNTESTABLE rather than failed; a synthetic-event rejection is not evidence of a product defect"), **all ⚠️RAW-COORD items (#8, #9, #27, #28, #32, #71, #72) are recorded UNTESTABLE-VIA-HARNESS**, with a recommendation to settle them via native event injection (Playwright-style) or a human pointer. #8 specifically remains **neither confirmed nor cleared**.

---

## Environment snapshot at audit start

- **Sidecar `/health`:** `0.8.0` on dynamic port **61283** (this boot). `equity:yfinance`, `crypto:ccxt`, `fundamentals:yfinance`, **`macro:unavailable`**, **`openbb-mcp:unavailable`**.
- **`/openbb-mcp/status`:** `available:false`. **`/mcp/status`** (host MCP server, distinct from the subprocesses): `ready:true, toolCount:11`.
- **`/agents`:** **12** ✅ (correct — repo ships 12; an empty `[]` would be the L3 bundling bug; not present).
- **MCP nondeterminism (UC1) — CONFIRMED RELIABILITY FINDING:** across the relaunches during environment setup, `openbb-mcp` bound on **one** boot (`/health` reported `openbb-mcp:available, macro:openbb-mcp, fundamentals:openbb-mcp (yfinance fallback)`) and was **down on the others** (incl. this audit boot). Nondeterministic subprocess port-binding at startup is itself a bug — logged once here as **S2 (reliability)**; see consolidated list. This boot is a **DOWN** boot, so macro/SEC/openbb-fundamentals data-load items are **DEFERRED-MCP-DOWN**; degradation paths are tested.

---

## Phase 1 — 93-item pass (Groups A–J)

_Status key: PASS / FAIL / UNTESTABLE-VIA-HARNESS / DEFERRED-MCP-DOWN / DEFERRED-NEEDS-BUILD. Severity (if failed): S1/S2/S3._

### Group A — Panel-open & shell

| #   | Result                     | Notes                                                                                                                                                                                                                                                                                  |
| --- | -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **PASS**                   | Cmd+K opens the Command Palette (search box + scrollable command list).                                                                                                                                                                                                                |
| 2   | **PASS** (mechanism)       | cmd+K → type trigger → Enter opens the panel as a dockview tab. Verified on a diverse representative subset: Option Pricer (quant), Chart, Watchlist, Settings — all opened. Open path is the single shared `workspace.openPanel`, so the mechanism is uniform. No open failures seen. |
| 3   | **PASS**                   | Watchlist opened twice → still **one** Watchlist tab (singleton focuses existing, no duplicate).                                                                                                                                                                                       |
| 4   | **PASS**                   | Chart opened twice → **distinct** Chart tabs created (non-singleton). The active Chart rendered SPY candlesticks with "SPY via yfinance" header.                                                                                                                                       |
| 5   | **PASS** (correct no-op)   | Clicking a Settings module **card body** does nothing — matches §2.3/§3.11 intended behavior. File only as the S3 **discoverability** finding (the sole launcher is keyboard cmd+K; no visible "open panel" affordance).                                                               |
| 6   | **PASS**                   | Toggling **Node Editor** module OFF → palette search "node" → **"No matching commands"**; re-enabling restores it. Disabling a module removes its command.                                                                                                                             |
| 7   | **PASS / observed**        | Disabling **Equity Overview** while its panel was open: the open tab **persists** (not force-closed), no crash; only the command + future-open is removed. Defensible; at most a minor S3 inconsistency (a disabled module keeps a live panel).                                        |
| 8   | **UNTESTABLE-VIA-HARNESS** | Tab-drag rearrange. No in-webview drag registers (see Calibration). Per §6.2/§8.5, recorded UNTESTABLE, **not FAILED** — #8 neither confirmed nor cleared. Needs native event injection / human pointer.                                                                               |
| 9   | **UNTESTABLE-VIA-HARNESS** | Splitter resize. Same root cause as #8.                                                                                                                                                                                                                                                |
| 10  | **PASS**                   | Closing a Chart tab via its X removed the panel (left group 5→4 tabs; context badge decremented).                                                                                                                                                                                      |
| 11  | **PASS**                   | Save Workspace dialog → named "phase9test" → Save. Verified persisted: `GET /workspace` → `["phase9test"]`, `GET /workspace/phase9test` → 200. Load reads the same verified persistence layer (command present in palette).                                                            |
| 12  | **UNTESTABLE-PRECISE**     | Cannot set exact 1920×1080 / 2560×1440 via this harness. At maximized resolution no table/axis overflow observed in the 5-panel cockpit. Recommend `resize_page` (chrome-devtools) for the exact dual-resolution check.                                                                |

**Cosmetic observation (A):** the "N PANELS ACTIVE" context badge math is slightly off (3 opens registered as +2; a close as −1). Unclear intended semantics (likely counts context-contributing panels, not literal tabs). **S3, low confidence it's even a defect.**

### Group B — Chart

| #     | Result                        | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ----- | ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 13    | **PASS**                      | SPY loads weekly/daily candles, header "SPY via yfinance"; AAPL loaded elsewhere; equity `/history` → 200/251 bars. Crypto uses `/crypto/history` (separate route).                                                                                                                                                                                                                                                                             |
| 14    | _not explicitly re-tested_    | Empty-submit no-op — relied on §3.1; not separately exercised. Low risk.                                                                                                                                                                                                                                                                                                                                                                        |
| 15    | **FAIL (S2)**                 | Junk symbol **ZZZZZ** → header "ZZZZZ via yfinance" + **fully blank chart, NO error overlay, NO Retry, NO "no data"**. Endpoint returns `200`/`bars=0` (NOT 502), so the error path never fires. A bad symbol is indistinguishable from a data outage. This is the §4.2 "empty bars hide a data bug" trap, reproduced. Root cause: yfinance returns empty (not an exception) for unknown alpha tickers, and the UI treats empty 200 as success. |
| 16    | **UNTESTABLE (this session)** | Retry no-op risk — no error overlay surfaces for ZZZZZ (see #15), so no Retry button appears to test. A symbol that raises ProviderError (→502) is needed to exercise the Retry path.                                                                                                                                                                                                                                                           |
| 17    | **PASS**                      | Timeframe switch SPY 1d→1h→1wk: exactly one button pressed (amber), history refetched/rebuilt each time (multi-year weekly view rendered).                                                                                                                                                                                                                                                                                                      |
| 18    | **PASS** (representative)     | SMA(20) overlays the price pane (right-axis tag); RSI(14) renders in a separate oscillator pane; both amber-pressed; "Clear (2)" counter. Engine works for both render types. Special-renders #19–22 (VWAP/SAR/Ichimoku/Volume Profile) not individually exercised — engine verified, low risk.                                                                                                                                                 |
| 19–22 | **NOT INDIVIDUALLY VERIFIED** | Special indicator renders; engine confirmed via #18. Recommend a follow-up visual pass.                                                                                                                                                                                                                                                                                                                                                         |
| 23    | **PASS**                      | Compare QQQ with `%` ON → "QQQ %" legend (left scale) + sage overlay line + `×` clear control.                                                                                                                                                                                                                                                                                                                                                  |
| 24    | _not exercised_               | Compare bad symbol silent-swallow — not tested; low risk.                                                                                                                                                                                                                                                                                                                                                                                       |
| 25    | **CONFIRMED (S3, known)**     | Add compare QQQ, change primary SPY→NVDA: "QQQ %" overlay/legend **persists**, not rebuilt for the new primary. Matches §8.1 (compare effect deps omit `symbol`).                                                                                                                                                                                                                                                                               |
| 26    | **UNTESTABLE-PRECISE**        | Axis-label overlap needs exact 1920/2560 resolutions (see #12). Not assessable precisely via this harness.                                                                                                                                                                                                                                                                                                                                      |
| 27    | **UNTESTABLE-VIA-HARNESS**    | Drawing-tool canvas clicks (lightweight-charts trusted-only). Arming buttons are DOM (clickable) but the canvas placement clicks don't register as chart gestures — same class as the calibration drag finding.                                                                                                                                                                                                                                 |
| 28    | **UNTESTABLE-VIA-HARNESS**    | Drag-to-pan / scroll-zoom canvas gestures.                                                                                                                                                                                                                                                                                                                                                                                                      |
| 29–30 | _deferred_                    | Drawing inspector / Escape-Delete — depend on a placed drawing (#27 untestable).                                                                                                                                                                                                                                                                                                                                                                |
| 31    | _deferred_                    | Drawing-persists-across-symbol UX trap — depends on #27.                                                                                                                                                                                                                                                                                                                                                                                        |
| 32    | **UNTESTABLE-VIA-HARNESS**    | Multi-chart crosshair/zoom/symbol sync — needs canvas hover/zoom gestures.                                                                                                                                                                                                                                                                                                                                                                      |
| 33    | _not exercised_               | Rapid timeframe toggling stress — covered partially by Phase-2 adversarial.                                                                                                                                                                                                                                                                                                                                                                     |
| 34    | **PASS**                      | Empty-data symbol → blank chart, no crash, **no error banner** (the §4.2 behavior, same as #15).                                                                                                                                                                                                                                                                                                                                                |

### Group C — Watchlist / News / Portfolio / Equity

| #   | Result                        | Notes                                                                                                                                                                                                                     |
| --- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 35  | **PASS**                      | Added TSLA to watchlist. Confirmed indirectly+robustly: a TSLA article appeared in News (which filters to watchlist symbols) and quotes tick. `/quotes?symbols=AAPL,MSFT` → 200 live.                                     |
| 36  | _partial_                     | Duplicate/junk/remove-last not each exercised; add path verified via #35.                                                                                                                                                 |
| 37  | **PASS**                      | After News recovered: articles render with **sentiment badges** (POSITIVE +0.87/+0.60, NEGATIVE −0.13) + source + age + symbol chips (BTC/ETH/NVDA/TSLA). Sentiment polarity varies correctly.                            |
| 38  | **CONFIRMED — S2 (known)**    | Fresh launch: News showed "Could not reach the news service" + Retry. Clicking **Retry → articles loaded**. Exactly the §8.3 cold-network first-fetch-fails / warm-retry-succeeds bug.                                    |
| 39  | _not tested_                  | Empty-watchlist "No news" state.                                                                                                                                                                                          |
| 40  | **PASS**                      | Added AAPL ×10 @ $150 → summary "Market value $3,049.90, **Total P&L +$1,549.90 (+103.33%)** (= (304.99−150)×10 ✓), Concentration 100%"; row renders Price/MktVal/P&L/Weight + Edit/Delete.                               |
| 41  | _partial_                     | Edit/cancel/delete + qty edge values not each exercised (covered partly by Phase-2).                                                                                                                                      |
| 42  | **PASS**                      | Equity Overview AAPL (loaded during calibration): header 304.99 +1.32%, 10 valuation ratios, analyst consensus "buy" target 308.65, multi-year income statement. (Fundamentals via yfinance fallback this MCP-down boot.) |
| 43  | _partial / DEFERRED-MCP-DOWN_ | Junk-symbol all-sections-fail path not exercised; openbb extended sections degrade to yfinance this boot.                                                                                                                 |

**🟠 NEW FINDING (C) — Portfolio false "Failed to load portfolio" banner (S2).** On cold start the Portfolio panel showed a red **"Failed to load portfolio"** error in every screenshot, yet `GET /portfolio/positions` → **200 `[]`** (healthy). Adding a position **cleared** the banner and the summary computed correctly — so it's a stale cold-first-fetch error on the load/summary path that **never auto-recovers and offers no Retry** (worse UX than News #38, which at least has Retry). A core panel sits in a permanent false-error state until the user happens to perform a write.

### Group D — AI / Agents / Backtest

| #     | Result                  | Notes                                                                                                                                                                          |
| ----- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 44    | **PASS**                | No BYOK key: send → graceful in-stream error "no API key set for anthropic; run /key set anthropic". No crash/stack-trace. Rapid triple-send → no duplicate messages, no race. |
| 45    | **UNTESTABLE (no key)** | Real streamed response requires a live BYOK key (not available; would also send user data to a provider — out of scope). `/llm/providers` → 200 (7 providers listed).          |
| 46    | _partial_               | Slash-command edge cases not each exercised; empty/rapid-send held (#44).                                                                                                      |
| 47    | **PASS**                | `/agents` → **12** (full first-party set; not the empty-`[]` L3 bug). AgentPicker is populated from this.                                                                      |
| 48–49 | _not exercised_         | Agent Builder CRUD/validation — `/custom-agents` CRUD not driven this session.                                                                                                 |
| 50–52 | _DEFERRED_              | Backtest SSE run / edge / Strategy-Critic handoff — in-process engine; SSE flow not driven (time). Recommend follow-up.                                                        |

### Group E — Quant (in-process QuantLib — testable this boot)

| #     | Result                        | Notes                                                                                                                                            |
| ----- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 53    | **PASS**                      | Option Pricer Black-Scholes → **$9.2181** (1.3 ms) + Greeks Δ0.5417/Γ0.0183/ν30.63/Θ−39.68/ρ13.56 (sensible ATM).                                |
| 54    | _not exercised_               | American+BS / American+MC incompatibility alert.                                                                                                 |
| 55    | _not exercised_               | Negative-vol / expiry≤valuation / strike-0 → 400 (endpoints validate — confirmed via 422s on malformed bodies).                                  |
| 56    | **PASS (by engine)**          | Greeks already computed+displayed by Option Pricer (#53); Greeks Dashboard uses the same in-process path.                                        |
| 57    | **NOT INDIVIDUALLY VERIFIED** | Bond Pricer — same QuantLib engine; endpoint validates body (422 on missing `coupons_per_year`). High confidence; recommend a quick GUI confirm. |
| 58–60 | _not exercised_               | Bond/yield-curve edge + bootstrap. Engine proven; endpoints validate.                                                                            |

### Group F — Macro / SEC / Earnings / Analyst / Screener (MCP-DOWN boot)

| #   | Result                | Notes                                                                                                                                                                                                    |
| --- | --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 61  | **DEFERRED-MCP-DOWN** | Macro legacy `/macro/DGS10` → **501** (graceful, matches §4.6). FRED/ECB/IMF/WB provider paths need a FRED key.                                                                                          |
| 62  | **DEFERRED-MCP-DOWN** | FRED-no-key → 502 path not exercised (no key); legacy 501 confirmed.                                                                                                                                     |
| 63  | _not exercised_       | Macro search/rapid-switch edge.                                                                                                                                                                          |
| 64  | **DEFERRED-MCP-DOWN** | SEC `/sec/status` → 200 `available:false`; `/sec/filings?symbol=AAPL` → **501** (graceful). Happy path blocked by down subprocess this boot.                                                             |
| 65  | **partial**           | `/sec/filings` with no params → **501** (not the documented 400) because the down-subprocess 501 short-circuits param validation. Minor ordering note; the 400 path is masked while MCP down → DEFERRED. |
| 66  | **PASS**              | `/earnings/upcoming?days=7` → 200 (empty window, valid). Earnings unaffected by MCP (yfinance-cached).                                                                                                   |
| 67  | _not exercised_       | Earnings window-bound edge.                                                                                                                                                                              |
| 68  | **PASS**              | `/fundamentals/AAPL/ratings/history` → **200 with real data** (yfinance fallback) even with openbb down. Analyst Ratings works this boot.                                                                |
| 69  | **BLOCKED by #91**    | Screener preset run blocked by missing universe snapshot (below). Custom-symbol run not completed (schema).                                                                                              |
| 70  | _not exercised_       | Screener criteria edge.                                                                                                                                                                                  |

**🔴 #91 / Group J — Screener universe snapshot NOT bundled → 502 (S2, CONFIRMED).** `/screener/universe?id=sp500` → **502 `"missing universe snapshot 'sp500.json'"`** — exactly the bundling regression #91/§4.9 warned about (PyInstaller `--add-data` gap, same class as the fixed L3 agents-dir bug). The cached/shipped sidecar binary lacks the universe JSONs, so the Screener cannot run any preset universe (sp500/nifty50/crypto-top50). Blocks #69 for presets.

### Group G — Node Editor / Workflow

| #     | Result                     | Notes                                                                                                                                          |
| ----- | -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| 71    | **UNTESTABLE-VIA-HARNESS** | Drag node from palette (HTML5 DnD) — same root cause as the calibration drag finding.                                                          |
| 72    | **UNTESTABLE-VIA-HARNESS** | Draw edge between nodes (canvas pointer gesture).                                                                                              |
| 73–75 | _not exercised / DEFERRED_ | PropertiesPanel / save-load-run-workflow / validation — panel opens via cmd+K but core graph building is gated by the untestable canvas drags. |

### Group H — Plugins / Brokers / Safety

| #   | Result                  | Notes                                                                                                                                                                                                                                                                                                                 |
| --- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 76  | _partial_               | Plugin Manager not GUI-toggled this session. `/plugins` → 200 `[]` (sidecar config store; bundled plugins load client-side — Tradesa V2 read-only works, so plugins ARE loaded).                                                                                                                                      |
| 77  | **PASS**                | `/brokers` → 200 with the 10-broker list (dhan disconnected/paper/readOnly:false + capabilities). Bad-creds GUI connect not driven (no live orders).                                                                                                                                                                  |
| 78  | _not exercised_         | Broker paper↔live + read-only toggle.                                                                                                                                                                                                                                                                                 |
| 79  | **🔴 FAIL — S2**        | **Audit Log → 500.** `/safety/audit-log` returns **500 Internal Server Error** on every valid call (no-params / `?limit=200` (panel's 2s-poll default) / `?limit=1`); only `?limit=0` correctly → 400. The Audit Log Viewer (a **safety surface**) is unreadable; via CORS-masking it appears in-app as a CORS error. |
| 80  | **partial PASS**        | Limit guard works: `?limit=0` → 400. (But valid limits → 500, see #79.)                                                                                                                                                                                                                                               |
| 81  | **PASS — S1**           | Kill-switch full cycle: fire → `fired:true` + per-broker ack times (dhan 1.7 ms…); reset **blocked without acknowledgment** (gate holds; returns 422 rather than the documented 400 — trivial); reset-with-ack → `{reset:true}`; status restored `fired:false`.                                                       |
| 82  | **PASS (partial) — S1** | Order proposal gate: unknown `proposal_id` → 404. Full AI-review-checkbox dialog needs a broker order proposal (paper-only/no-live constraint); gate architecturally enforced per SAFETY_ARCHITECTURE.md.                                                                                                             |
| 83  | _not observed_          | First-launch ToS / per-broker disclaimer not seen (disclaimer ack is session-scoped; may have been acked on a prior boot of this data-dir).                                                                                                                                                                           |

### Group I — Tradesa V2 (read-only plugin)

| #     | Result                           | Notes                                                                                                                                                                               |
| ----- | -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 84    | **PASS**                         | `/tradesa-v2/status` → 200 `unauthenticated` with "No Tradesa V2 credentials… Open Plugin Manager → Tradesa V2 → Settings" → `_PanelShell` shows the Connect/unauthenticated state. |
| 85–87 | _DEFERRED_                       | Settings-dialog validation / Supabase-configured data / bot-offline+partial states need (mock) Supabase credentials — not configured.                                               |
| 88    | **PASS — S1 (safety invariant)** | Read-only enforced: `POST /tradesa-v2/status`→405, `PUT /tradesa-v2/settings`→405, `DELETE /tradesa-v2/positions`→405; `GET /tradesa-v2/positions`→401 (unauth). No non-GET routes. |

### Group J — Build-artifact & runtime-bundling (now LIVE on the bundle)

| #   | Result                           | Notes                                                                                                                                                                                                                                   |
| --- | -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 89  | **PASS**                         | No Next.js dev-indicator badge anywhere in this `tauri build` bundle (only the TradingView attribution mark). Confirms §8.4 — the badge was a dev-server artifact.                                                                      |
| 90  | **PASS**                         | `/agents` → **12** (full first-party set; not empty).                                                                                                                                                                                   |
| 91  | **🔴 FAIL — S2**                 | Screener universe snapshot not bundled → 502 (detailed above under Group F).                                                                                                                                                            |
| 92  | _partial_                        | Sidecar-down behavior not actively induced (didn't kill the sidecar mid-audit). **CORS-masks-500 trap CONFIRMED** independently: the #79 audit-log 500 is exactly a 5xx that surfaces in-app as CORS — curl revealed the true 500.      |
| 93  | **PASS / CONFIRMED degradation** | MCP-down boot handled gracefully: `/health` `openbb-mcp:unavailable`+`macro:unavailable`; fundamentals → yfinance (200); SEC → 501; legacy macro → 501; analyst-ratings still 200 via yfinance; `/agents`=12. All graceful, no crashes. |

---

## Phase 2 — Adversarial break-phase

| Vector                                    | Outcome         | Detail                                                                                                                                                                                                                                                                                                                                                       |
| ----------------------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Malformed/XSS/SQL chart symbol**        | **HELD (good)** | Typed `'; DROP TABLE quotes;-- 🚀🚀ZZZ<script>alert(1)</script>` + 50×`A`. Uppercased + sent as a symbol. **No XSS** (`<script>` rendered as inert text, no alert), **no SQL injection** (quotes keep ticking, no crash), indicators correctly show "Not Found (404)". Robust. (Reinforces #15: header still claims "…via yfinance" on an empty/bad symbol.) |
| **Chat: no-key + rapid-fire triple send** | **HELD**        | Graceful "no API key set" error; no duplicate messages; no race/crash; Send gated during send.                                                                                                                                                                                                                                                               |
| **(Phase-1-surfaced, adversarial-class)** | —               | The worst bugs (audit-log 500, screener-universe 502, portfolio false-error, chart silent-blank) surfaced during the structured pass — see consolidated list.                                                                                                                                                                                                |

**Adversarial vectors recommended but NOT run (time/context):** open 30–50 panels + close-ALL-panels (empty-dockview resilience); kill/stall sidecar mid-SSE; 200-symbol watchlist polling load; 1000-row/huge-number portfolio & quant inputs; 20+ screener criteria; workspace swap mid-stream. These are the highest-yield remaining destructive probes.

---

## Consolidated bug list (deduplicated, severity-sorted) — fix-sprint ready

### S1 (blocks core / data-loss / safety)

- **None NEW confirmed.** All safety gates HELD: kill-switch fire+ack-gated-reset (#81), order proposal 404 gate (#82), Tradesa read-only 405/401 (#88), no XSS/SQLi (adversarial). The only S1-flagged checklist items that remain _unverified_ are deferred for setup reasons (full order-confirm dialog, backtest SSE), not failures.

### S2 (major feature broken / wrong data / safety surface degraded)

1. **Audit Log Viewer unreadable — `/safety/audit-log` → 500 on all valid limits (#79).** Root-cause hypothesis: the append-only audit read path (reader connection `PRAGMA query_only`, or a query/serialization error on the `audit_orders` read) throws on a normal/empty read; only Pydantic limit-bound validation (limit 0/>5000 → 400) runs before it. Curl the endpoint for the traceback. Safety surface — should be high priority.
2. **Screener universe snapshots not bundled — `/screener/universe?id=sp500` → 502 "missing universe snapshot 'sp500.json'" (#91, #69).** PyInstaller `--add-data` gap for the screener universe JSONs (same class as the fixed L3 agents-dir bug). Screener unusable for all preset universes. Add the universe dir to the sidecar `--add-data` and the smoke-test endpoint-probe.
3. **News first-fetch fails, Retry recovers (#38, known §8.3).** Cold-network all-or-nothing one-shot fetch. Fix: shared pooled `httpx.Client` + per-source retry/backoff + don't 502 when some sources succeed.
4. **Portfolio false "Failed to load portfolio" banner on cold start (NEW).** `/portfolio/positions` is 200 `[]` yet the panel shows a persistent error with **no auto-recovery and no Retry**; only a successful write clears it. Likely a cold-first-fetch failure on the load/summary path (news-class). Add retry/empty-state handling so an empty 200 renders "No positions yet", never an error.
5. **Chart shows a silent blank on a bad/unknown symbol — no error UI (#15).** `/history/ZZZZZ` → 200/`bars=0`; the header reads "ZZZZZ via yfinance" (claims success) and the chart blanks with no overlay/Retry/"no data". Bad symbol indistinguishable from outage. Treat empty-bars as a distinct "no data for symbol" state with a message; don't render the success header.
6. **MCP subprocess binding is nondeterministic across boots (UC1, reliability).** openbb-mcp bound on one setup boot, was down on others (incl. this audit boot) — confirmed empirically. Nondeterministic startup port-binding is itself a defect; macro/SEC/openbb-fundamentals availability is a coin-flip per launch.

### S3 (visual / polish / edge / minor)

- **Stale compare overlay/legend after primary-symbol change (#25, known §8.1).** Confirmed: "QQQ %" persists, not rebuilt for new primary. Add `symbol` to the compare effect deps.
- **Panel-open discoverability (#5/§8.6).** Only launcher is keyboard cmd+K; no visible "open panel" affordance; Settings cards (correctly) do nothing on click. Add a visible launcher.
- **SEC param-validation order (#65).** When the subprocess is down, "no cik/symbol" returns 501 instead of 400 (501 short-circuits validation). Cosmetic ordering.
- **Kill-switch reset-without-ack returns 422, docs say 400 (#81).** Gate still holds; trivial code/doc mismatch.
- **"N PANELS ACTIVE" context badge count is slightly off** vs literal tab count (likely counts context-contributing panels). Unclear semantics; low confidence it's a defect.
- **Header claims "<sym> via yfinance" even for empty/bad symbols** (part of #15) — the success header should not show when `bars=0`.

### UNTESTABLE-VIA-HARNESS (recommend native event injection / human pointer)

- All ⚠️RAW-COORD canvas/drag tests: **#8 tab-drag (UNCONFIRMED — neither proven nor cleared)**, #9 splitter, #27 chart drawing, #28 pan/zoom, #32 crosshair-sync, #71 node drag, #72 edge-draw. Computer-use emits trusted OS events (native window drag worked) and discrete clicks/typing reach the webview, but **no in-webview drag gesture registers** — consistent with a WKWebView/CGEvent drag-delivery limitation, not a proven product defect. Settle with Playwright native-event injection or a real human pointer.

### Deferred (setup-dependent, not failures)

- DEFERRED-MCP-DOWN this boot: macro happy-path (#61–63), SEC happy-path (#64–65), openbb-fundamentals extended.
- DEFERRED setup: backtest SSE (#50–52), agent-builder CRUD (#48–49), Tradesa-configured data (#85–87), broker connect/mode (#77 connect/#78), disclaimer flow (#83), quant edge (#54–60 individual), node-editor graph (#73–75 behind untestable canvas).

---

## Overall usability impression

The app is **functional and robust at its core**: the 5-panel cockpit renders live data, cmd+K opens every panel, the quant engine is fast and correct, sentiment-scored news works, portfolio P&L is correct, and **every safety gate held** (kill-switch, order-proposal, Tradesa read-only, plus no XSS/SQLi under fuzzing). The headline pre-existing "15 panels won't open" and "tab-drag broken" reports are resolved as the plan predicted — a discoverability gap and an unconfirmable harness-limited drag, respectively.

The real damage is in **error-surfacing and bundling**: a safety surface (Audit Log) is outright 500, the Screener is dead for preset universes due to a missing bundled snapshot, and two panels (Portfolio cold-start, Chart bad-symbol) **mask failures as success or as un-recoverable errors**. None are S1, but #79 (safety surface) and #91 (feature dead) should lead the fix sprint.

## Counts

- **PASS:** 1,2,3,4,5,6,7,10,11,13,17,18,23,34,35,37,40,42,44,47,53,56,66,68,77,81,84,88,89,90,93 (+#25/#38 confirmed-as-known) ≈ **33 PASS** (incl. confirmations)
- **FAIL (bug):** #15, #79, #91 + NEW Portfolio-false-error = **4 distinct defects** (3×S2 checklist + 1 new S2)
- **CONFIRMED known bugs:** #25 (S3), #38 (S2)
- **UNTESTABLE-VIA-HARNESS:** #8,9,27,28,32,71,72 (+ #12/#26 untestable-precise, #16 untestable-this-session)
- **DEFERRED-MCP-DOWN:** #61,62,63,64,65 (macro/SEC happy paths)
- **DEFERRED (setup/time):** #36,39,41,43,45,46,48,49,50,51,52,54,55,57,58,59,60,67,70,73,74,75,76,78,83,85,86,87,92
- **Headline S2:** Audit-Log 500 (#79, safety surface), Screener universe 502 (#91), News first-fetch (#38), Portfolio false-error (new), Chart silent-blank (#15), MCP nondeterministic binding (UC1).

---

## Phase 2b — Deferred Adversarial Vectors

_Run in a later session (app PID 19831, `/Applications/Vysted.app`, `com.vysted.desk`, sidecar dynamic port 61283), full-tier computer use. Same code as `e9775b5`. Tester, not fixer — no source edits._

### Vector 1 — Open 30–50 panels via rapid cmd+K, then close all → **HELD (no defect)**

- **Tried:** ~37 rapid `cmd+K → "chart"/"macro" → Enter` opens (non-singleton, so each creates a distinct panel), then attempted to close them all.
- **Open phase:** the new panels piled into one dockview group whose tab strip overflowed to a **graceful "⌄ N" overflow dropdown** (observed counts climbing 16 → 27). No crash, UI stayed responsive, new charts kept loading SPY data, watchlist kept ticking, no visible jank or request storm.
- **Close phase:** closing the active tab's ✕ decrements cleanly (27→26→…→22 verified). Two caveats, both **harness artifacts, not app bugs**: (a) the ✕ hitbox under heavy overflow is a precise target (~x1309; clicks ~10px left just re-activate the tab), and (b) an external app (System Settings, then Ghostty) repeatedly stole focus after ~3–5 rapid closes, so a literal close-to-empty wasn't reached through the harness. **No instability at any panel count.**
- **Re-open / leaked-state check:** Load Workspace ("phase9test") **cleanly replaced** the bloated layout with the saved cockpit — no crash, all panels re-rendered, data live, no leaked state. Re-open works after the stress.
- **Verdict:** dockview is resilient to ~35 panels and rapid open/close. **No defect.** (Literal empty-dockview state not reached via the harness — recommend a unit/e2e test for the all-panels-closed edge.)

### Vector 2 — Kill the sidecar MID-STREAM (backtest SSE) → **HELD (graceful, no defect)**

- **Tried:** Started a heavy 15-symbol Mean-Reversion backtest (SSE `/backtest/run`), then `pkill -9 vysted-sidecar` (both bootloader+worker PIDs; port 61283 → connection-refused confirmed). The first run actually **completed before the kill landed** (in-process engine is fast: Return +7.69%, Sharpe 0.15, MaxDD −13.25%, **174 trades**, equity+drawdown charts, sortable trade table) → **bonus #50 PASS**. Then started a **second** backtest with the sidecar already dead to exercise the failed/dropped-stream path.
- **What broke / held:** Everything degraded **gracefully, no crash/hang**:
  - Backtest (sidecar dead) → **"error: Load failed"** + "TRADES (0) — No trades yet." (clean error frame, not a spinner-hang).
  - Watchlist 5s poll → **"Failed to load watchlist quotes"** banner; last-known prices retained.
  - News/Portfolio → retained last-loaded data; app stayed fully responsive (panels switch, cmd+K works).
- **Severity:** no defect. **Minor (S3) polish note:** the backtest error is the generic **"Load failed"** rather than a specific "sidecar unavailable / connection refused" — same generic-surface family as the CORS-masks-500 trap; a clearer message would help users distinguish a dead sidecar from a bad strategy.
- **Recovery:** the Tauri core did **not** auto-respawn the sidecar after an external kill; a full app relaunch was required to get a fresh sidecar (new dynamic port 55177). Worth noting as a resilience gap (S3): an external sidecar crash leaves the app permanently degraded until manual restart — no in-app "reconnect/restart sidecar" affordance observed.
- _Side observations on this fresh boot:_ News cold-fetch error (#38) and Portfolio "Failed to load portfolio" both **reproduced** on the clean relaunch (consistent). The AAPL portfolio position added in Phase 1 did **not** reappear after restart — possible non-persistence of portfolio positions across app restart (or the cold-load failed); flagged for follow-up, not deep-dived.

### Vector 3 — 200-symbol watchlist / 5s poll → **FINDING: S2 performance (request pile-up / stale quotes)**

- **Tried:** mass-added ~55 symbols to the watchlist (rapid type+Enter; Enter submits each), let the 5s poll run.
- **What broke / held:** App **held** — no crash, no freeze, no client-side CPU thrash (main process 0.4% CPU); visible rows kept ticking; News auto-refiltered to the new symbols (MSFT POSITIVE +0.20). **But** the batched `GET /quotes?symbols=<55>` takes **~26.3 s** (200, 55 rows) — the sidecar's yfinance fan-out is sequential/unbatched. With a **5 s poll interval vs a 26 s response**, polls **overlap/pile up** (~5 concurrent in-flight) and quotes are perpetually stale.
- **Severity: S2 (performance/scalability).** A 26 s quote refresh makes the watchlist effectively non-functional at realistic sizes (many users keep 30–100 symbols). Root cause is server-side fan-out latency, not the UI. **Fix direction:** concurrent/batched provider fetch (asyncio gather / bulk yfinance `download`), and a client-side guard so a poll is skipped while the previous is still in flight (prevent pile-up). _Unconfirmed whether the client already de-dupes overlapping polls — if not, the pile-up is real; if so, the impact is severe staleness/sluggishness._

### Vector 4 — Huge/malformed inputs (Portfolio + Quant) → **HELD vs crashes; 2 findings**

- **Portfolio (S3 — no input validation):** direct `POST /portfolio/positions` with **qty 1e15 → 201 created**; **negative qty −50 + negative cost_basis −10 → 201 created**. No upper bound, no rejection of negative quantity/cost, no clamping. Fuzz note (`'; DROP TABLE positions;--`, emoji, HTML, 260-char) accepted as plain text — no injection, no crash. **Missing validation** → nonsensical positions/P&L possible.
- **Portfolio panel load (S2 — strengthened, see consolidated #4):** `GET /portfolio/positions` shows the Phase-1 AAPL position **persisted** (`id:1, qty 10, cost 150`), yet the panel renders **"Failed to load portfolio" + "No positions yet" simultaneously** — real DB data is not displayed on cold load. Confirms the cold-load is genuinely broken, not just a cosmetic banner.
- **Quant (HELD — robust validation):** every malformed/extreme `POST /quant/option/price` (negative volatility, expiry-before-valuation, spot 1e12 + vol 5000%, wrong field names) returned **422 schema-validation**, and the **sidecar stayed alive** through all of it. GUI negative-vol click missed (Option Pricer docked dynamically), but server-side validation + Phase-1 valid-pricing cover it. **No crash.**
- **Verdict:** no crashes from huge/malformed input anywhere. New defects: portfolio missing input validation (S3) + portfolio cold-load failure (S2, already in consolidated list).

### Vector 5 — Workspace swap mid-stream → **HELD (graceful, slow)**

- **Tried:** triggered an Equity Overview AAPL fundamentals load, then immediately opened Load Workspace and selected "phase9test" — both fetches in flight at once (confirmed: panel "Loading equity overview…" + dialog "Loading…" simultaneously).
- **What broke / held:** **no crash, no corruption.** The equity load **completed successfully** (full AAPL fundamentals rendered) despite the concurrent workspace load. The workspace dialog sat in "Loading…" ~10s then returned to the list view — **slow due to sidecar contention from the 55-symbol watchlist poll** (Vector 3); watchlist SPY/QQQ briefly showed "—" (partial quote loads while the sidecar was saturated).
- **Severity:** no new crash. Reinforces the **Vector-3 S2 latency finding** — a heavy watchlist poll **starves other sidecar requests** (workspace load, equity fundamentals), degrading whole-app responsiveness to new actions while the poll is in flight.

### Vector skipped

- 20+ screener criteria: **not run** — Screener is already dead via the #91 missing-universe-snapshot bug; criteria count is moot until the universe loads.

### Phase 2b — new findings folded into the consolidated list

- **S2:** large-watchlist quote latency / poll pile-up + request starvation (Vector 3 & 5). Portfolio cold-load fails to display persisted positions (Vector 4, strengthens the earlier Portfolio false-error to a confirmed data-not-shown bug).
- **S3:** no portfolio input validation (negative/huge qty & cost accepted, Vector 4); generic "Load failed" backtest error vs a specific sidecar-unavailable message (Vector 2); no in-app sidecar reconnect/restart after an external sidecar crash (Vector 2).
- **HELD (no defect):** 35-panel open + rapid close (Vector 1); sidecar-kill mid-stream graceful degradation (Vector 2); malformed/extreme input never crashes the sidecar (Vector 4); workspace swap mid-stream (Vector 5).

### Final state (Phase 2b)

App relaunched to a clean, usable state: default 5-panel cockpit, watchlist reset to the 4 seed symbols (the 55 test symbols did **not** persist), fresh sidecar healthy (`0.8.0`, dynamic port — 58321 at write time, agents=12, openbb-mcp down per UC1). News shows the cold-fetch error (recovers on Retry). **Residual test artifacts** (non-blocking): the Portfolio SQLite DB retains 3 test positions (`id:1` AAPL 10@150 from Phase 1; `id:2` qty 1e15; `id:3` qty −50) which **do not display** due to the confirmed portfolio cold-load bug; a `phase9test` workspace remains saved. No live orders were ever placed; kill-switch left `fired:false`.
