# Phase 9.5 — Mac Claude Code Runner Prompt

This is the paste-ready runner prompt for the second-pass GUI re-audit, run on
the Mac via first-party computer use against the **`f3bef61`** debug bundle. It
lives here so it survives across machines. Copy everything inside the block
below into a fresh Mac Claude Code session (the app already built + installed per
the env recipe in `docs/PHASE_9.5_REAUDIT_SPEC.md` §5).

---

```
You are running the Phase 9.5 second-pass GUI re-audit of Vysted Terminal on macOS
via first-party computer use. You are a TESTER, NOT a fixer.

READ FIRST: docs/PHASE_9.5_REAUDIT_SPEC.md — it is your reference. It lists the 6
fixes to regression-verify (§1), the async-refactor blast radius to sweep (§2), the
deferred-on-setup items to clear (§3), the ~33 clean items to SKIP (§4), the env
recipe (§5), the operator-manual lane (§6), and the visual-observation protocol (§7).

BUILD UNDER TEST: origin/main @ f3bef61 (post–Phase-9 fix sprint, still labelled
v0.8.0, unreleased). App is /Applications/Vysted.app (display "Vysted", bundle id
com.vysted.desk) — repackaged ONLY to clear the computer-use tier classifier; same
code as f3bef61.

HARD RULES:
- NO source edits. The ONLY file you write is docs/PHASE_9.5_BUG_CATALOG.md.
- NO commits, NO git operations, NO tag. The operator commits/audits.
- Write the catalog INCREMENTALLY — flush your findings to disk after each group
  (regression / async-sweep / deferred / adversarial / visual). Do not hold all
  results in memory to the end.
- Status keys: PASS / FAIL (with S1/S2/S3) / UNTESTABLE-VIA-HARNESS /
  OPERATOR-MANUAL / DEFERRED-NEEDS-SETUP / DEFERRED-MCP-DOWN.

ENV FACTS (do not relitigate):
- /agents must return 12 (the full first-party set). An empty [] would be the L3
  bundling bug — already fixed; 12 is CORRECT.
- The sidecar port is DYNAMIC per boot. Discover it from /health before any
  direct-curl (see Step 0).
- UC1: openbb-mcp subprocess binding is nondeterministic. A cold first boot may
  report openbb-mcp:unavailable. RELAUNCH clears it — relaunch until /health shows
  openbb-mcp:available before running any MCP-dependent item. If it still degrades
  after several relaunches, that is the DOCUMENTED RESIDUAL (BLOCKERS.md) — note it,
  do NOT treat as a new defect.
- CORS-masks-500: a browser "CORS policy" error on a sidecar route is almost always
  a 5xx whose exception response lacks a CORS header. DIRECT-CURL the endpoint to
  read the true status BEFORE concluding anything about CORS.

STEP 0 — CALIBRATION (decisive, do this first):
1. Discover the sidecar port: find the dynamic port (read the app's network calls or
   the health surface) and curl http://127.0.0.1:<port>/health. Record: version,
   port, equity/crypto/fundamentals providers, macro + openbb-mcp status, and
   confirm /agents == 12. If openbb-mcp is unavailable, relaunch per UC1 before the
   MCP items.
2. Confirm full-tier computer use: click into the webview (load a chart) and type
   into the symbol field — both must land. Confirm a NATIVE OS drag works (drag the
   window title bar — it should move the window, proving trusted events).
3. Confirm in-webview drag still does NOT register: attempt a tab-reorder drag and a
   splitter resize. EXPECT these to fail (WKWebView/CGEvent drag-delivery limit).
   Mark all RAW-COORD items (#8, #9, #27, #28, #32, #71, #72) UNTESTABLE-VIA-HARNESS
   — NOT FAILED. A synthetic-event rejection is not proof of a product defect.

GROUP 1 — REGRESSION-VERIFY THE 6 FIXES (spec §1). For each, do the GUI check AND
direct-curl the endpoint where listed:
- #79 Audit Log: open the Audit Log panel (ideally fresh data dir) → must render an
  empty/populated table, NEVER a 500/CORS error. Curl /safety/audit-log?limit=200 →
  200. (Safety surface — top priority.)
- #91 Screener: run an sp500 preset (and nifty50, crypto-top50) → universe resolves,
  screen runs. Curl /screener/universe?id=sp500 → 200.
- #3 Quotes: this is verified in the async sweep + adversarial Vector 3 (below).
- #38 News: on a FRESH launch (cold network), News must populate on the FIRST fetch
  (no "Could not reach the news service"). Partial-source success must still render
  articles.
- #5 Portfolio: cold start with empty DB → "No positions yet" clean empty state,
  never a red error. With residual test positions present → they RENDER. Induce a
  failure → error WITH Retry, and Retry recovers.
- #15 Chart: load ZZZZZ → distinct "no data for symbol" state (no silent blank, no
  false "ZZZZZ via yfinance" success header). Valid symbol → renders.
- UC1 MCP: relaunch several times, check /health openbb-mcp+macro across boots —
  should be far more reliable than pass 1. Residual cold-boot degrade is expected
  and documented, not a new defect.
- S3: #25 (change primary after compare → overlay rebuilds), #81 (curl reset empty
  body → 400 not 422), #65 (curl /sec/filings no params → 400 not 501), portfolio
  bounds (curl negative/huge qty → 422), sidecar-down message ("sidecar unavailable"
  not "Load failed"), panel-open affordance (visible launcher present).
Flush Group 1 to the catalog.

GROUP 2 — ASYNC BLAST-RADIUS SWEEP (spec §2):
- With a ≥50-symbol watchlist polling (5 s), open a Chart and switch timeframes / add
  indicators (history.py + indicators.py run sync on the loop). History + indicator
  loads must stay responsive and NOT stall while quotes fan out. If they stall, log
  it (do not fix).
- Profile News with a large result set — flag any visible hitch from the synchronous
  sentiment-scoring loop.
- SSE/WS contention: open a long-running SSE (agent invoke or backtest run) and, while
  it streams, let the watchlist auto-refresh / open a chart. Neither should stall the
  other. Kill an SSE mid-stream → loop recovers, other routes resume.
- Confirm clean app startup (httpx client) and clean shutdown (no hang/warning on
  client close).
Flush Group 2 to the catalog.

GROUP 3 — CLEAR DEFERRED-ON-SETUP ITEMS (spec §3), with whatever setup the operator
configured. Always-runnable (no external setup) FIRST: #36, #39, #41, #54-55, #57,
#58-60, #67, #70, #76, and the #73-75 node-editor panel/save-load UI (NOT the graph
drags). Then, IF configured: BYOK key → #45,#46,#48-49,#50-52; FRED key → #61-63;
MCP up → #43,#61,#64,#65 happy paths + openbb-fundamentals; Supabase → #85-87; paper
broker creds → #77 connect,#78. Mark anything still unconfigured DEFERRED-NEEDS-SETUP.
Flush Group 3 to the catalog.

GROUP 4 — HEAVIER ADVERSARIAL VECTORS not run in pass 1 (spec §8):
- Re-run Vector 3 (≥50-symbol watchlist, 5 s poll) — THE primary #3 regression:
  quote batch latency must be far lower than pass 1's 26 s, and polls must NOT pile
  up (the in-flight guard skips overlaps). Re-run Vector 5 (workspace swap mid-poll)
  — other routes must no longer be starved.
- 1000-row / huge-number portfolio & quant inputs (server must validate/clamp; no
  crash).
- 20+ screener criteria (now unblocked by #91).
- Literal close-ALL-panels empty-dockview edge.
Flush Group 4 to the catalog.

GROUP 5 — VISUAL / DENSITY OBSERVATIONS (spec §7) — collect into a SEPARATE catalog
section "§Visual Observations — Design-Overhaul Input". Screenshot-backed, per panel:
sparseness / low density, generic-default styling, label overlap/truncation (check
1920×1080 AND 2560×1440), un-technical/un-JARVIS reads, cross-panel inconsistency.
ONE line each: panel + screenshot + issue. NO proposed fix, NO severity — this is
INPUT to the future design overhaul; aesthetic direction is the operator's call.
Flush Group 5 to the catalog.

OPERATOR-MANUAL (spec §6) — do NOT attempt; list as OPERATOR-MANUAL: all RAW-COORD
drag/canvas items (#8/#9/#27/#28/#32/#71/#72), live broker connect/order placement,
any flow behind a secret the operator won't expose, and the design DIRECTION itself.

WHEN DONE: ensure docs/PHASE_9.5_BUG_CATALOG.md is complete (header with build
identity + /health snapshot + Step-0 calibration result, then the 5 groups + the
operator-manual + visual sections), and report a short summary back. Do NOT commit,
do NOT tag — hand back to the operator.
```

---

**After the Mac pass:** the operator reviews `docs/PHASE_9.5_BUG_CATALOG.md`,
decides what (if anything) needs a Phase 9.6 fix loop, and only then considers the
design overhaul (a separate effort) and the v0.8.x → v0.9 version bump. No tag is
implied by this audit.
