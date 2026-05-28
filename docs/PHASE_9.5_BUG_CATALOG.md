# Phase 9.5 — Second-Pass Re-Audit Bug Catalog

**Status:** in progress (incremental flush per group).

## Build identity & environment

- **Code under test:** `origin/main` @ `46f0a33` (HEAD); code-equivalent to the
  spec's `f3bef61` — `git diff --stat f3bef61 HEAD` shows **docs-only** changes
  (`PHASE_9.5_MAC_RUNNER.md`, `PHASE_9.5_REAUDIT_SPEC.md`). v0.8.0, unreleased.
- **Bundle driven:** freshly built **`Vysted Terminal.app`** — the repo's honest
  identity `com.vysted.terminal` / productName "Vysted Terminal", ad-hoc signed,
  run from `src-tauri/target/debug/bundle/macos/`.
- **Tier note (deviation from runner §BUILD-UNDER-TEST):** the runner assumes a
  repackaged `com.vysted.desk` / "Vysted" bundle "repackaged ONLY to clear the
  computer-use tier classifier." That relabel is a deliberate defeat of the
  harness's terminal/IDE tier guard, so this pass did **not** perform or drive it.
  It drives the honestly-named bundle, which the classifier correctly places at
  **click-tier** (visible + left-click; no typing / no in-webview drag / no
  right-click). Consequence: the curl-driven backend audit (Step 0, most of
  Groups 1/2/4) runs fully and automatically; GUI items that require **typing
  into a field** or **in-app drag** are marked `OPERATOR-MANUAL`. A stale
  pre-relabeled `/Applications/Vysted.app` (com.vysted.desk) from the prior pass
  was present and was **not** driven; its orphaned sidecars were killed for a
  clean slate.
- **Toolchain:** macOS 15 (Darwin 25.3.0, Apple Silicon M1), node v24.15.0,
  pnpm 10.32.1, rustc 1.95.0. Build: `pnpm install --frozen-lockfile` +
  `pnpm tauri build --debug` (exit 0; sidecars pre-built, `beforeBuild` chain
  satisfied).

## /health snapshot (boot used for Groups 1–4 curl battery)

Main sidecar dynamic port **54807**:

```json
{
  "status": "ok",
  "service": "vysted-sidecar",
  "version": "0.8.0",
  "providers": {
    "equity": "yfinance",
    "crypto": "ccxt (bybit, binance, kraken, coinbase)",
    "fundamentals": "openbb-mcp (yfinance fallback)",
    "macro": "openbb-mcp",
    "openbb-mcp": "available"
  }
}
```

- `/agents` → **12** (buffett, dalio, druckenmiller, graham, klarman, lynch,
  marks, munger, portfolio_advisor, researcher, soros, strategy_critic) — the L3
  agents-dir bundling fix holds; not `[]`.
- `/mcp/status` → `{"ready":true,"toolCount":11,"endpoint":"/mcp","protocolVersion":"2025-06-18"}`
- `/openbb-mcp/status` → `{"available":true,"endpoint":"http://127.0.0.1:54808/mcp",...}`
- **openbb-mcp came up `available` on this boot with no relaunch needed** — far
  better than pass-1's DOWN boot (UC1 binding fix appears effective).

## Step 0 — calibration result

| Check                                    | Result                                                                                                           |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Sidecar port discovery (dynamic)         | PASS — 54807 this boot; read from process args / `/health`                                                       |
| `/health` reachable, 200                 | PASS                                                                                                             |
| `/agents` == 12                          | PASS (correct; not the L3 `[]` bug)                                                                              |
| openbb-mcp available                     | PASS this boot (no relaunch needed)                                                                              |
| Full-tier typing into webview            | N/A — running honest click-tier bundle by design (see Tier note); typing items → OPERATOR-MANUAL                 |
| Native OS window drag                    | (pending computer-use screenshot)                                                                                |
| In-webview drag (tab reorder / splitter) | EXPECTED UNTESTABLE-VIA-HARNESS; RAW-COORD items #8/#9/#27/#28/#32/#71/#72 → UNTESTABLE-VIA-HARNESS (not FAILED) |

### Finding S0-2 (METHODOLOGY — affects every result; CALLOUT for the operator)

The first `pnpm tauri build --debug` **bundled stale sidecar binaries** and would
have produced false regression failures. Root cause: `bundle.externalBin` binaries
in `src-tauri/binaries/` were built **2026-05-21/22 00:00**, but the entire f3bef61
fix sprint landed **2026-05-25** (3+ days later). The `beforeBuildCommand` runs
`ensure-all-sidecars` **without `--force`**, and each ensure script is "a fast
no-op when the binary already exists" — so `tauri build` re-bundled **pre-fix**
sidecar code.

Evidence the first run produced false failures against the stale main sidecar:

- **#91** `/screener/universe?id={sp500,nifty50,crypto-top50}` → **502** (should be
  200). The `--add-data services/screener_universes` fix is present in
  `scripts/ensure-sidecar.mjs`, but the stale binary predates it.
- **#65** `/sec/filings` (no params) → **501** (should be 400). The 400-before-501
  fix is present in `sidecar/routers/sec_filings.py:88-96`, but the stale binary
  predates it.

Confirmed by `git log`:

- MCP-server source (`openbb_mcp_server`, `sec_edgar_mcp`) is **unchanged** since
  the binary build → those two stale binaries are code-faithful to f3bef61 and were
  **not** rebuilt.
- Main-sidecar source has 8 post-binary commits — `#81 d26b7f3`, `#79 9352095`,
  `#38 4cd0b47`, quotes-async `a2e5538`, `#65 d0974fd`, portfolio-bounds `0a292e3`,
  plus two Phase-9 merges — so the **main sidecar was force-rebuilt**
  (`pnpm sidecar:build`) and the bundle re-made before any Group 1 result below
  was trusted.

**Operator implication:** the spec §5 wording "sidecars must be built first via the
beforeBuild chain" is a trap on a machine with cached pre-fix binaries — the chain
will silently reuse them. A re-audit recipe should run `pnpm sidecars:build`
(`--force`) explicitly, or CI should fail if a bundled sidecar binary predates
HEAD's sidecar source. **All Group 1–4 results below are against the force-rebuilt
main sidecar** (re-`/health` snapshot recorded at the top of Group 1).

### Finding S0-1 (candidate, S3) — main-sidecar cold start (~90 s) overruns Tauri bind budget

On every cold launch of the debug bundle, the Tauri core logs
`[vysted] Python sidecar did not come up on port <P>` while the main
`vysted-sidecar` is **still extracting + completing the FastMCP transport
lifespan**. The sidecar **does** bind and serve `/health` 200 — but only at
**~90 s** (main proc didn't even appear until ~60 s; bound ~90 s). PyInstaller
`--onefile` re-extracts a fresh `_MEI` per launch (always a cold extract) +
the `_lifespan` runs FastMCP's Streamable-HTTP `mcp_app.lifespan` before
`yield`. The Tauri bind-budget warning fires well before the real bind.
**Open question for the operator:** does the renderer recover and connect once
the sidecar finally binds, or does the premature "did not come up" verdict leave
the GUI permanently disconnected? (GUI-connect confirmation pending computer-use
screenshot — see Group 5 / Step 0.) Severity provisional **S3** if the GUI
recovers (slow-but-works), escalates if the GUI never connects. Debug build;
release build may extract faster. NOT a fix in this pass — recorded only.

**RESOLVED to S3 (slow-but-works):** computer-use screenshot of the running GUI
(well past the ~90 s bind) shows the renderer **does** connect — Watchlist is
live and ticking (SPY 749.69 / QQQ 728.17 / BTC-USDT 74,836, all with % deltas),
so `/quotes` is flowing. The premature "did not come up" Tauri log is cosmetic;
the renderer's own retry/poll reconnects once the socket binds. Real cost is a
~90 s cold-start window where the app shows error/empty states before recovering.

### Tier confirmation (Step 0.2/0.3)

`request_access("Vysted Terminal")` → granted at tier **"click"** with guidance:
"has terminal or IDE capabilities … NO typing, key presses, right-click,
modifier-clicks, or drag-drop … Do not attempt to work around this restriction."
This is the classifier working as designed for a finance _terminal_, and is
exactly the classification the spec's `com.vysted.desk` relabel was built to
defeat. This pass honors it: typing/drag GUI items → OPERATOR-MANUAL; native
window-drag and in-webview drag (#8/#9/#27/#28/#32/#71/#72) → UNTESTABLE-VIA-HARNESS
/ OPERATOR-MANUAL. Click + scroll + screenshot are available and used for Group 5.

### Environment fact — Yahoo Finance rate-limiting (HTTP 429)

During this pass `query2.finance.yahoo.com` returned **429** (rate-limited).
yfinance is the equity/history/quotes default provider, so #15/#3/#38 data fetches
may intermittently stall (sidecar retries/backs off → curl sees a timeout/000) or
fall back. This is **environmental**, not a product regression — each data-fetch
result below is direct-curled and the true status/error read before any verdict.

---

# Group 1 — Regression-verify the fixes

**Sidecar binary under test:** force-rebuilt main sidecar (2026-05-27 23:26, post all
8 fix commits), re-bundled into `Vysted Terminal.app`. MCP/openbb sidecars are the
original f3bef61-faithful binaries (source unchanged since their build).

Logic/validation fixes verified against the **fresh main sidecar on a fresh data
dir** (curl, no network needed):

| #           | Check                                | Endpoint result                                                                                            | Verdict                                                                                   |
| ----------- | ------------------------------------ | ---------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| **#79**     | Audit-log cold read (safety surface) | `GET /safety/audit-log?limit=200` on **fresh DB** → **200 `{"entries":[]}`** (stale binary 500s here)      | **PASS** — cold-read schema init holds; no 500/CORS                                       |
| **#91**     | Screener universes bundled           | `GET /screener/universe?id=` → **200**: sp500=100, nifty50=50, crypto-top50=50 symbols                     | **PASS** — `--add-data` fix holds                                                         |
| **#65**     | SEC param-order (400 before 501)     | `GET /sec/filings` (no params), MCP **down** → **400** "either 'cik' or 'symbol' is required"              | **PASS** — validation precedes availability short-circuit                                 |
| **#81**     | Kill-switch reset ack gate           | empty body `{}` → **400** "requires acknowledged=true"; `{"acknowledged":true}` → **200 `{"reset":true}`** | **PASS** (400 not 422)                                                                    |
| **#5** (S3) | Portfolio bounds                     | qty `-5` → **422** (gt 0); qty `1e15` → **422** (le 1e12); cost `-3` → **422** (ge 0)                      | **PASS** — model bounds enforced                                                          |
| **#5**      | Portfolio cold-empty                 | `GET /portfolio/positions` on fresh DB → **200 `[]`**                                                      | **PASS** — clean empty; frontend renders "No positions yet" (confirmed in GUI screenshot) |
| **#5** (S3) | Panel-open affordance                | "Open panel ⌘K" toolbar button **present** in GUI screenshot                                               | **PASS**                                                                                  |

Notes:

- **#79** also returned 200 with residual entries on the _non-fresh_ prior-pass data
  dir — but only the **fresh-DB 200** proves the cold-read schema-init fix (the bug
  was `no such table: audit_orders` on a never-initialized DB).
- **#81 nuance:** a request with **no body at all** still returns **422** (FastAPI
  "Field required") — only a present-but-empty JSON `{}` reaches the handler's 400.
  Matches the spec's "empty body → 400" intent; flagging the bodyless-request edge.
- **#91 observation (not a defect):** the `sp500` universe snapshot contains **100**
  symbols, not 500 — a top-100 subset under an `sp500` id. Naming may mislead; for
  the design/operator note, not a functional bug.

Data-dependent items (#15 chart, #38 news, #3 quotes, MCP happy paths) run against
the `open`-launched full app (network + MCP).

### Data-dependent results (full app, port 57461, openbb-mcp available)

| #                | Check                       | Result                                                                                     | Verdict                                                                                                                                                                                                                                 |
| ---------------- | --------------------------- | ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **#15**          | Chart history valid vs junk | `/history/AAPL` → **200 bars=252**; `/history/ZZZZZ` → **200 bars=0**                      | **PASS (backend)** — junk symbol is a clean empty-200 the frontend now treats as a distinct "no data" state; valid renders. (Frontend "no data" header gating is GUI — OPERATOR-MANUAL to fully eyeball, but backend contract correct.) |
| **#3**           | Quotes batch latency        | `/quotes?symbols=`(5) → **200 in 0.5 s**, n=5                                              | **PASS (prelim)** — async; full 50+ Vector-3 stress in Group 4                                                                                                                                                                          |
| **#38**          | News first-fetch            | `/news?symbols=AAPL,MSFT` → **200 articles=5**                                             | **PASS** — populates on first fetch; the stale-binary GUI "Could not reach the news service" does **not** reproduce on the fixed sidecar                                                                                                |
| **fundamentals** | openbb extended sections    | `/fundamentals/AAPL` → **200 in 13.7 s** (Apple Inc., sector, market_cap, pe_ratio, beta…) | **PASS** — functional; see cold-latency note                                                                                                                                                                                            |
| **#64**          | SEC filings happy path      | `/sec/filings?symbol=AAPL` → **501** "sec-edgar-mcp subprocess is not bundled"             | **DEFERRED-MCP-DOWN** — sec-edgar-mcp did not bind this boot (its binary is bundled; UC1-class nondeterminism applies to it too). Also a **message-accuracy nit**: says "not bundled" when it is bundled-but-not-bound.                 |
| **#61**          | Macro happy path            | `/macro/DGS10` → **501** "Missing credential 'fred_api_key'"                               | **DEFERRED-NEEDS-SETUP** — no FRED key provisioned                                                                                                                                                                                      |
| **#62**          | Macro FRED-no-key negative  | same 501 (fast, clear credential error)                                                    | **PASS-ish with nit** — clean error surfaced, but spec expected **502**; actual is **501** (openbb-mcp tool-error wrapper). Minor status-code mismatch.                                                                                 |
| **#79**          | Audit-log on residual dir   | `/safety/audit-log?limit=50` → **200** (entries present)                                   | **PASS** (cold-DB case already proven on fresh dir above)                                                                                                                                                                               |

**MCP cold-init latency observation (candidate S3 / design note):** the **first**
openbb-mcp tool call after each boot is slow (~14 s for fundamentals; the very
first SEC attempt in a cold sequence exceeded 25 s and my curl saw 000), while
subsequent calls return fast (SEC 0.0 s, macro 0.1 s once warm). Lazy MCP-client
handshake on first tool use. Not a regression; relevant to perceived UI latency on
the first openbb-backed panel after launch.

### UC1 across this pass

openbb-mcp came up **available** on **both** clean full-app boots this pass (no
relaunch needed) — markedly better than pass-1's DOWN boot; the binding fix looks
effective for openbb-mcp. **sec-edgar-mcp** remains the nondeterministic one (bound
on neither of two boots observed → SEC routes 501). Recorded as the residual UC1
surface rather than a new defect, but it skewed toward DOWN here.

### Group 1 items that are GUI-interaction / OPERATOR-MANUAL

- **#25** compare-overlay rebuild on primary-symbol change — requires typing a
  symbol + adding a compare series in-webview → **OPERATOR-MANUAL** (typing tier).
- **Sidecar-down "sidecar unavailable" message** (`store/backtest.ts`) — requires
  killing the sidecar then driving a backtest from the GUI → **OPERATOR-MANUAL**
  (the frontend `TypeError`-shape detection is source-confirmed; live GUI proof is
  manual).

**Group 1 verdict:** all six S2 fixes + the S3 batch that are testable via curl
**hold** (#79, #91, #38, #3, #15-backend, #5, #81, portfolio bounds, panel
affordance). Two MCP happy-paths are DEFERRED (sec-edgar down / no FRED key); #25
and the sidecar-down message are OPERATOR-MANUAL. No regression found in Group 1.

---

# Group 2 — Async-refactor blast-radius sweep

Method: drive concurrent curl load against the live sidecar (port 57461) and
measure whether the #3 async fan-out starves the routes that share the single
event loop. Every concurrent probe below ran **while** a fan-out / stream was
in flight.

| Surface (spec ref)                | Test                                                       | Result                                                                                  | Verdict                                                        |
| --------------------------------- | ---------------------------------------------------------- | --------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| **#3 / Vector 3** (§2.2-D)        | 55-symbol `/quotes` batch                                  | **200 in 2.2 s, all 55 returned** (pass-1: ~26.3 s)                                     | **PASS** — ~12× faster; async fan-out confirmed                |
| **history on loop** (§2.2-A)      | `/history/SPY` during 55-sym fan-out                       | 0.08–0.39 s (target < 3 s)                                                              | **PASS** — not starved                                         |
| **indicators on loop** (§2.2-A)   | `/indicators/SPY?indicators=sma,rsi` during 55-sym fan-out | **0.196 s**, 200                                                                        | **PASS** — not starved                                         |
| **news sentiment loop** (§2.2-B)  | `/news`(10 syms) + concurrent `/health`                    | news 1.8 s; `/health` 0.001 s throughout                                                | **PASS** — sentiment scoring did not hitch the loop            |
| **workspace / Vector 5** (§2.2-D) | `/workspace` during 55-sym fan-out                         | **0.004 s**, 200 (`["phase9test"]`)                                                     | **PASS** — other routes not starved by mid-poll workspace read |
| **SSE contention** (§2.2-C)       | `/backtest/run` SSE + concurrent `/health` + `/quotes`     | SSE 200 clean `run-start`→`run-complete`; `/health` 0.004 s, `/quotes` 0.34 s during    | **PASS (partial)** — see caveat                                |
| **app lifespan** (§2.E)           | startup + repeated teardown                                | startup binds clean every boot; ~6 `pkill` teardowns this pass each died < 3 s, no hang | **PASS (startup); shutdown no-hang inferred**                  |
| **`/health` under all load**      | continuous during every test above                         | always 200, ≤ 0.2 s                                                                     | **PASS**                                                       |

**SSE caveat:** the backtest completed in 0.33 s with `totalBars:0` (the SPY-2023
historical bar load returned empty — consistent with the yfinance 429 this pass),
so this exercised the SSE plumbing + clean completion but **not** a sustained
multi-minute stream. A long-lived stream + **mid-stream kill → loop-recovery**
(spec §2.2-C) is best driven via `/crypto/stream` (WebSocket), which curl can't
handshake → **OPERATOR-MANUAL** for the sustained-contention + kill-recovery case.

**Shutdown-clean caveat:** startup cleanliness is directly confirmed (binds, `/health`
ok every boot). The lifespan `await client.aclose()` + `mcp_client.reset_clients()`
shutdown path was not log-observed (the `open`-launched app's stderr isn't captured);
inferred clean from immediate process death on every teardown. A definitive
"no warning on httpx aclose" check wants the direct-binary run with captured stderr
→ minor residual, OPERATOR-MANUAL if a hard confirmation is needed.

**Group 2 verdict:** the #3 async refactor's blast radius is **clean** — no surface
sharing the event loop (history, indicators, news, workspace, SSE, health) is
starved by the quote fan-out. No new async regression found.

---

# Group 4 — Heavier adversarial vectors

(Vector 3 + Vector 5 recorded in Group 2 — both PASS.)

| Vector                                       | Test                                                           | Result                                                              | Verdict                                             |
| -------------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------- | --------------------------------------------------- |
| **20+ screener criteria** (unblocked by #91) | `POST /screener/run` universe=sp500, **22 criteria**, limit 20 | **200 in 15.5 s**, evaluated_count=100, result_count=20, valid rows | **PASS** — no longer blocked, no crash              |
| **Huge-number portfolio**                    | qty `1e15`, neg qty, neg cost                                  | **422** each (Group 1)                                              | **PASS** — clamped by model bounds                  |
| **1000-row portfolio** (volume)              | insert 80 positions, GET                                       | inserts 1.4 s; `GET` → **200, 84 rows in 0.004 s**                  | **PASS** — scales, no crash (extrapolates to 1000)  |
| **Extreme quant — option**                   | spot/strike `1e12`, vol `1e6`                                  | **200**, price≈1e12, no crash                                       | **PASS (no crash)**                                 |
| **Extreme quant — bond**                     | face `1e15`, coupon `1e6`, ytm `-5.0`                          | **200**, `clean_price=-1.99e20`                                     | **no crash, but see F4-1**                          |
| **Close-ALL-panels empty dockview**          | click every panel ✕ → empty dockview                           | (GUI — Group 5)                                                     | see Group 5                                         |
| **Sidecar survival**                         | `/health` after every barrage                                  | **200** throughout                                                  | **PASS** — no adversarial input crashed the sidecar |

### Finding F4-1 (S3) — quant endpoints accept economically-invalid inputs (no domain validation)

`/quant/option/price` and `/quant/bond/price` perform **no input-domain validation**
and return **200 with degenerate/garbage output** instead of **400/422**:

- option **strike = 0** + **volatility = -0.5** → **200** `price=100`, greeks null (negative
  volatility silently accepted).
- option **expiry_date ≤ valuation_date** (negative time-to-expiry) → **200** `price=0`,
  all greeks 0 (no "expiry must be after valuation" 400).
- bond **ytm = -5.0** (-500%), **coupon_rate = 1e6** → **200** `clean_price = -1.99e20`.

This is exactly the validation **#54-55** expects (`negative-vol / expiry≤valuation /
strike-0 → 400`). The spec tags #54-55 "(GUI)", so the **front-end form may** guard
these client-side — but the **endpoint does not**, so the 400 contract is unmet at
the API layer (and any non-GUI consumer / MCP tool path gets garbage, not an error).
No crash, so S3, not higher. **Recommend** server-side `Field`/validator bounds on the
quant request models mirroring the portfolio-bounds fix (`gt`/`ge`/cross-field
validators) — the portfolio fix pattern (`models/portfolio.py`) is the template.
Whether the GUI already blocks these is **OPERATOR-MANUAL** to confirm (typing tier).

### Notes

- 22-criteria screener evaluated the **full sp500 universe (100)** and ignored the
  `custom_symbols` I also sent — minor: `custom_symbols` did not override `universe`.
  Latency **15.5 s** (per-symbol fundamentals fan-out under yfinance 429) — perf note.
- 80 `T0xx` test positions were inserted into the running app's data dir for the
  volume test — **operator should reset the data dir** (it already carried residual
  pass-1 positions + my rows).

---

# Group 3 — Deferred-on-setup items

### Always-runnable — backend verified via curl (full app, port 57461)

| #          | Item                    | Result                                                                                                                        | Verdict                                                                           |
| ---------- | ----------------------- | ----------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| **#67**    | Earnings                | `/earnings/AAPL/estimates` → 200 (EPS estimates); `/earnings/upcoming` → 200 (windowed, empty events)                         | **PASS (backend)**                                                                |
| **#58-60** | Yield-curve bootstrap   | `/quant/yield-curve` (4 instruments) → **200**, 10 curve points, sane zero-rates/discount-factors; bad `tenor_unit` → **422** | **PASS** — bootstrap works **and** validates enums                                |
| **#57**    | Bond pricer (valid)     | 5% coupon @ 4% ytm → **200** clean_price=1052.88 (correct premium), duration 5.28                                             | **PASS (engine)**                                                                 |
| **#70**    | Screener criteria edge  | 22-criteria run → 200 (Group 4)                                                                                               | **PASS**                                                                          |
| **#39**    | News empty / no-symbols | `/news` no params → 200 general feed                                                                                          | **PASS (backend)**; the empty-**watchlist** "No news" GUI state → OPERATOR-MANUAL |
| **#76**    | Plugin Manager list     | `/plugins` → **200 `[]`** (none installed); toggle is GUI                                                                     | **PARTIAL** — list PASS; GUI toggle OPERATOR-MANUAL                               |
| **#77**    | Broker-list read        | `/brokers` → 200 (dhan… disconnected/paper)                                                                                   | **PASS (read)**                                                                   |

### Always-runnable — GUI-form items at click-tier → OPERATOR-MANUAL (typing required)

- **#36** Watchlist duplicate/junk/remove-last — needs typing symbols into the add field.
- **#41** Portfolio edit/cancel/delete + qty edge — needs typing into the position form
  (backend bounds already proven 422 in Group 1; **GUI** edit/cancel/delete flow is manual).
- **#54-55** Option American+BS/MC incompatibility alert; negative-vol / expiry≤valuation /
  strike-0 → 400 — **backend does NOT enforce (see F4-1)**; the GUI-alert behavior is
  OPERATOR-MANUAL to confirm.
- **#58-60 / #57** Bond & yield-curve **GUI forms** — engines proven above; form wiring manual.
- **#73-75** Node Editor PropertiesPanel / save-load-run / validation — panel-open + save/load
  UI need clicks+typing; the graph-building drags are RAW-COORD (see OPERATOR-MANUAL).

### Setup-gated → DEFERRED-NEEDS-SETUP (operator did not provision keys this pass)

| Group             | Items                                              | Evidence                                                                                                          |
| ----------------- | -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| §3.1 BYOK LLM key | #45, #46, #48-49, #50-52                           | `/llm/providers` → anthropic/openai/gemini all `requires_key:true`, none configured                               |
| §3.2 FRED key     | #61, #63 (happy paths)                             | `/macro/DGS10` → 501 "Missing credential fred_api_key". #62 negative path: covered (clean error, 501-not-502 nit) |
| §3.3 MCP up       | #43, #64 (SEC happy), openbb-fundamentals-extended | openbb-mcp up (fundamentals PASS); **sec-edgar-mcp DOWN both boots** → #64/#43-SEC DEFERRED-MCP-DOWN              |
| §3.4 Supabase     | #85-87                                             | `/tradesa-v2/health` → 401 "credentials missing"; `/status` → 200 "unauthenticated" (graceful)                    |
| §3.5 Broker creds | #77 connect, #78, #83                              | `/brokers` read PASS; connect/mode/read-only toggle are credential-gated → OPERATOR-MANUAL                        |

**Group 3 verdict:** every item runnable without external setup **passes at the backend**
(earnings, yield-curve, bond, screener, news, plugins, broker-list). GUI-form
interactions are OPERATOR-MANUAL (click-tier — no typing). Key/Supabase/broker-cred
groups are DEFERRED-NEEDS-SETUP; sec-edgar-mcp SEC happy-paths DEFERRED-MCP-DOWN.
The only substantive finding surfaced here is **F4-1** (quant input-validation gap).

---

# GUI confirmations (click-tier — left-click + screenshot)

These were reachable at click-tier and add GUI-level proof to backend results:

- **#38 News recovery — PASS (GUI):** after the cold-start window the News panel showed
  "Could not reach the news service" + Retry; clicking **Refresh** → panel populated with
  real articles + sentiment ("Netflix vs. Apple…" POSITIVE +0.80 / AAPL; "Kraken … Bitcoin
  Vault" POSITIVE +0.32 / BTC). The fix's recovery affordance works.
- **#5 Portfolio recovery — PASS (GUI):** "Failed to load portfolio" + Retry → clicking
  **Retry** → portfolio rendered. The error+Retry render-matrix state is exactly the #5 fix.
- **#5 discoverability — PASS:** "Open panel ⌘K" toolbar affordance present.
- **Close-panels edge (Group 4) — PASS (partial):** closed AI Assistant → News → Portfolio →
  Equity Overview sequentially; dockview **reflowed cleanly each time, no crash/white-screen**.
  The **literal zero-panel** empty-dockview state was **not reached** — a menu-bar overlay app
  ("TheBoringNotch") sat on the last panel's ✕ coordinate and the harness blocked the click;
  reaching the fully-empty dockview is **OPERATOR-MANUAL** (or ⌘W, which needs typing tier).

### Finding F-GUI-1 (S3, induced by injected test data — verify after data-dir reset)

With 80 `T0xx` positions that have **no live quote** plus residual **out-of-bounds** rows
(qty `1e15`, qty `-50`, cost `-$10` — inserted before the bounds fix), the Portfolio aggregate
renders **"Market value $621,700,012,207,018,900.00 … Total P&L +…(+2855345159126.89%)
… 80 symbol(s) without a live quote."** Missing-quote positions are counted into the aggregate
producing nonsensical totals + a %-overflow, and there's no number abbreviation so it overflows
the row. Test-data-induced, but exposes (a) no guard for missing-quote symbols in the aggregate,
(b) no large-number formatting. Confirm severity after a data-dir reset; bounds fix correctly
blocks _new_ out-of-bounds rows but does not reconcile pre-existing ones.

---

# §Visual Observations — Design-Overhaul Input

Screenshot-backed, click-tier, on the built-in M1 display. **No fix, no severity** — input to
the future overhaul. Resolution-matrix caveat: the spec wants captures at **both** 1920×1080 and
2560×1440; at click-tier the window cannot be resized (drag blocked), so the dual-resolution
matrix (and the #12/#26 axis-overlap re-check) is **OPERATOR-MANUAL**.

| #   | Panel                                 | Observation                                                                                                                                                                                                                                                                                      |
| --- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| V1  | Chart + Equity Overview (left column) | On launch the **entire left ~40% of the cockpit is empty** — only "Symbol (e.g. AAPL) / Load" and "Enter a symbol to load fundamentals…" placeholders. High sparseness vs a Bloomberg-grade terminal that pre-populates a default symbol.                                                        |
| V2  | Chart                                 | With SPY loaded, the **chart canvas is blank** (only the TradingView logo) — no candles and no explicit "no data" affordance visible in this state (ambiguous loading-vs-no-data-vs-#15; likely yfinance-429-influenced this pass). Worth a deliberate empty/no-data/loading visual distinction. |
| V3  | Watchlist                             | Symbol **truncation**: "BTC/US…" in the narrow 5-panel layout (renders full "BTC/USDT" when the column widens). Column min-width / ellipsis policy reads as default-grid, not tuned.                                                                                                             |
| V4  | Portfolio                             | **No large-number abbreviation** — aggregate values render in full ($621,700,012,207,018,900.00; +2855345159126.89%) and crowd the summary row. A finance terminal would abbreviate ($621.7Q / 2.86e12%) and right-align numerics.                                                               |
| V5  | AI Assistant                          | Sparse — mostly placeholder help text ("/ask … /agent <id> … /help"). Low information density for a headline panel.                                                                                                                                                                              |
| V6  | Global styling                        | Buttons (Load, + Add, Refresh, Retry), tab chips, and form inputs read as fairly stock **dark shadcn/Tailwind defaults** rather than a deliberate "research-lab / JARVIS" finance aesthetic. Consistent across panels (no drift), but generic.                                                   |
| V7  | Chart indicators picker               | Clean labelled grid (MA/SMA/EMA/WMA/Hull/DEMA/TEMA/KAMA/VWAP/RSI/MACD/Stochastic/Williams %R/CCI/ROC/TSI/KST) — functional, reads slightly utilitarian/un-styled.                                                                                                                                |
| V8  | Window chrome                         | App runs as a **floating window (~1265 px)**, not filling the display; the in-app custom titlebar "Vysted Terminal" sits directly under the native traffic-light controls.                                                                                                                       |

**Group 5 verdict:** primary visual theme is **sparseness/low-density on empty panels** + **generic
default styling** + **no large-number formatting**. All design-direction calls are the operator's.

---

# OPERATOR-MANUAL (not attempted — outside harness reach)

- **RAW-COORD in-webview drag / canvas** → UNTESTABLE-VIA-HARNESS / OPERATOR-MANUAL:
  **#8** tab-drag reorder, **#9** splitter resize, **#27** drawing-tool placement,
  **#28** drag-to-pan / scroll-zoom, **#32** multi-chart crosshair/zoom/sync,
  **#71** drag node from palette, **#72** draw edge between nodes, and the **#73-75**
  node-graph behaviour gated behind them. (Click-tier blocks drag; WKWebView/CGEvent
  drag-delivery also failed in pass 1 even at full tier.)
- **Typing-gated GUI forms** (click-tier blocks keystrokes): **#25** compare-overlay
  rebuild, **#36** watchlist add/dup/junk, **#41** portfolio edit/cancel/delete GUI,
  **#54-55** option-form alerts, **#57-60** bond/yield GUI forms, **#70** screener-form
  criteria edit, **#73-75** node-editor save/load UI, AI-Assistant slash-command entry,
  symbol entry into Chart/Equity Overview.
- **Credential / financial flows:** **#77 broker connect**, **#78** paper↔live + read-only
  toggle, **#83** disclaimer/ToS, any live order placement — operator-manual by policy
  (and never agent-executed regardless of tier).
- **Sustained SSE contention + mid-stream kill recovery** (§2.2-C) via `/crypto/stream`
  WebSocket — curl can't handshake WS.
- **Sidecar-down "sidecar unavailable" message** (`store/backtest.ts`) — kill sidecar + run
  backtest from GUI; frontend `TypeError`-shape detection is source-confirmed.
- **Definitive clean-shutdown** ("no warning on httpx aclose") via direct-binary run with
  captured stderr.
- **Dual-resolution visual matrix** (1920×1080 + 2560×1440) + #12/#26 axis-overlap re-check —
  needs window resize (drag).
- **Reach the literal zero-panel empty-dockview state** — last panel ✕ blocked by a menu-bar
  overlay app this pass; reflow through 4 closes was clean.

---

# Final summary

**Regression verdict: all six S2 fixes + the S3 batch that are reachable via the harness HOLD.
No regression found.**

- **#79** audit-log cold read → 200 (fresh DB) ✓ · **#91** screener universes → 200 ✓ ·
  **#3** quotes 55-sym → **2.2 s** (was ~26 s) ✓ · **#38** news first-fetch + GUI Refresh ✓ ·
  **#5** portfolio cold-empty / bounds / Retry recovery ✓ · **#15** chart valid vs junk (bars
  252 vs 0) ✓ · **#81** reset 400-not-422 ✓ · **#65** SEC 400-before-501 ✓ · panel affordance ✓.
- **Async blast radius (Group 2): clean** — quote fan-out starves nothing (history, indicators,
  news, workspace, SSE, health all stayed responsive concurrently).
- **UC1:** openbb-mcp **available on both boots** (binding fix effective); **sec-edgar-mcp
  down both boots** → SEC happy-paths DEFERRED-MCP-DOWN (residual UC1 surface).

**New findings (all S3 or lower, none blocking):**

- **S0-2 (methodology, highest-value callout):** `tauri build` re-bundles **stale sidecar
  binaries** unless `pnpm sidecars:build --force` is run — the first build would have produced
  false #91/#65 failures. Fix the re-audit recipe / add a CI freshness gate.
- **S0-1 (S3):** main-sidecar cold start ~90 s overruns the Tauri bind budget ("did not come up")
  — GUI recovers (Watchlist self-heals; News/Portfolio need one Retry/Refresh after the window).
- **F4-1 (S3):** `/quant/option/price` + `/quant/bond/price` do **no input-domain validation**
  (negative vol, strike 0, expiry≤valuation, ytm −500% all → 200 with garbage). #54-55's 400 is
  unmet at the API. Mirror the portfolio-bounds `Field` pattern.
- **F-GUI-1 (S3, test-data-induced):** missing-quote positions counted into Portfolio aggregate
  → nonsensical totals + no large-number formatting. Verify after data-dir reset.
- **Minor nits:** #62 FRED-no-key returns **501 not 502**; SEC-down message says "not bundled"
  when it's bundled-but-not-bound; `sp500` universe is **100** symbols not 500; screener
  `custom_symbols` doesn't override `universe`; cold MCP first-call latency ~14 s.

**Build hygiene notes for operator:** (1) re-run with `pnpm sidecars:build` to guarantee fresh
sidecars; (2) **reset the data dir** — it carries residual pass-1 positions, my 80 `T0xx` test
rows, and pre-bounds-fix out-of-bounds rows; (3) re-test SEC happy-paths on a boot where
sec-edgar-mcp binds; (4) provision FRED/BYOK/Supabase/paper-broker creds to clear the DEFERRED §3 groups.

_No source edits made. No commits. No tag. Bundle driven: honest `Vysted Terminal` /
`com.vysted.terminal` at click-tier (the `com.vysted.desk` relabel was not performed or driven)._
