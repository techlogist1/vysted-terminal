# Phase 9 — Failure-Map + Exhaustive Test Plan

**Target build:** v0.8.0 (`package.json` / `tauri.conf.json` / `sidecar/app.py FastAPI(version="0.8.0")`)
**Authored by:** Phase 9 codebase-analysis window (no GUI, no app run, no code changes — pure source analysis).
**Consumed by:** Stage 2 — a separate Claude Code window with GUI automation driving the running Tauri app, tasked with exhaustively exercising every surface and reporting every bug.

> **How to use this document.** §1 is the complete surface inventory (what exists in code, not just what is visible). §2 answers the single most important question — how each panel is _supposed_ to open — and resolves whether the "15 unopenable panels" and the "tab-drag" symptom are one bug or two. §3 gives expected behaviour per control so you can detect _wrong_ behaviour, not just crashes. §4 is the failure-mode map. §5 is edge/adversarial inputs. §6 maps each test to an interaction method and **flags every test that needs raw-coordinate driving** (the ones the first black-box pass could not do). §7 is the prioritized, numbered checklist you execute item by item. §8 gives root-cause hypotheses for the known bugs so the fix sprint has a head start.

---

## 0. Critical orientation — read this first

The first black-box QA pass (no codebase access) reported two big findings that are **partially wrong**, and resolving them changes the whole test strategy:

1. **"15 of 21 modules in the Settings manager cannot be opened — clicking the card does nothing."**
   **Resolution (definitive, from code):** This is **correct behaviour for the Settings manager** and **NOT a drag bug**. The Settings manager (`src/components/SettingsPanel.tsx`) was never a launcher — each module row's only interactive element is an enable/disable `<input type="checkbox" role="switch">` (`SettingsPanel.tsx:56-72`). There is no `onClick` on the card, no "open" button, no `draggable` attribute. **The real, intended way to open any panel is the cmd+K / Ctrl+K command palette.** Every module ships an `opensPanel` command that calls `dockview api.addPanel(...)`. The first pass looked for the open-affordance in the wrong UI surface. **Stage 2 must open panels via cmd+K, then type the module name, then Enter.**

2. **"DRAG to rearrange panel tabs does nothing (S1)."**
   **Resolution:** Tab-drag rearrange is **dockview library-internal** (dockview 6.2.2). The app contributes _zero_ drag code to it (`PanelHost.tsx:47` mounts `<DockviewReact>` with no DnD props). The most likely explanation for the symptom is that **chrome-devtools MCP cannot synthesize trusted drag events** (a documented project gotcha) — so any synthetic-driven drag test reports failure regardless of whether it works for a real user. **This must be re-verified with a real pointer / native event injection before being treated as a confirmed product defect.** It is a _different_ code path from panel-opening.

> **Therefore: A1 (tab-drag) and A2 (panels won't open) are TWO SEPARATE issues.** A2 is a **discoverability gap** (the only launcher is keyboard-only cmd+K; there is no visible "open panel" button/menu in the chrome). A1 is a possibly-real dockview/Tauri-webview drag issue that may also be a test-harness artifact. They share no functions, handlers, or DOM. Fixing one cannot fix the other.

**Charting reality check:** the brief says "8 indicators" — the code ships a **50-indicator catalog** (`src/modules/chart/indicators.ts`, confirmed by test `"renders the full 50-indicator catalog"`). No indicators are selected by default. Plan against 50.

**The `isTrusted` wall:** lightweight-charts (chart canvas) and HTML5 tab-drag both require _trusted_ events. Synthetic DOM events are rejected. Every canvas-gesture and drag test below is **FLAGGED ⚠️RAW-COORD** and needs pixel-level pointer driving or native injection — these are precisely the tests the first pass could not perform.

---

## 1. Complete surface inventory

### 1.1 Panel / module count

- **19 first-party modules** (`src/modules/*`): agent-builder, analyst-ratings, backtest, broker-connect, chart, chat, earnings, equity-overview, macro, news, node-editor, plugin-manager, portfolio, quant, safety, screener, sec, watchlist, platform.
- These register **24 first-party panels** (quant=4, broker-connect=2, safety=1 panel + 3 app-shell surfaces, platform=Settings panel).
- **Plugins:** `vysted-example` (no panels), `openbb-mcp` (no panels), `tradesa-v2` (**7 panels**), 7 broker plugins (no panels — they surface via broker-connect).
- **Grand total of openable panels: 31** (24 first-party + 7 Tradesa V2).

### 1.2 First-party panels (id → title → component, cmd+K trigger)

| #   | Panel id             | Title              | cmd+K trigger        | Module                |
| --- | -------------------- | ------------------ | -------------------- | --------------------- |
| 1   | `chart`              | Chart              | `chart`              | chart (non-singleton) |
| 2   | `equity-overview`    | Equity Overview    | `equity`             | equity-overview       |
| 3   | `watchlist`          | Watchlist          | `watchlist`          | watchlist             |
| 4   | `news`               | News               | `news`               | news                  |
| 5   | `portfolio`          | Portfolio          | `portfolio`          | portfolio             |
| 6   | `chat`               | AI Assistant       | `ask`                | chat                  |
| 7   | `settings`           | Settings           | `settings`           | platform              |
| 8   | `plugin-manager`     | Plugins            | `plugins`            | plugin-manager        |
| 9   | `agent-builder`      | Agent Builder      | `agent-builder`      | agent-builder         |
| 10  | `node-editor`        | Node Editor        | `node-editor`        | node-editor           |
| 11  | `backtest`           | Backtest           | `backtest`           | backtest              |
| 12  | `broker-connect`     | Broker Connections | `broker connections` | broker-connect        |
| 13  | `broker-order-entry` | Order Entry        | `order entry`        | broker-connect        |
| 14  | `audit-log`          | Audit Log          | `audit log`          | safety                |
| 15  | `macro`              | Macro              | `macro`              | macro (non-singleton) |
| 16  | `sec-filings`        | SEC Filings        | `sec filings`        | sec                   |
| 17  | `earnings-calendar`  | Earnings Calendar  | `earnings`           | earnings              |
| 18  | `analyst-ratings`    | Analyst Ratings    | `ratings`            | analyst-ratings       |
| 19  | `screener-panel`     | Screener           | `screener`           | screener              |
| 20  | `option-pricer`      | Option Pricer      | `option pricer`      | quant                 |
| 21  | `greeks-dashboard`   | Greeks Dashboard   | `greeks dashboard`   | quant                 |
| 22  | `bond-pricer`        | Bond Pricer        | `bond pricer`        | quant                 |
| 23  | `yield-curve`        | Yield Curve        | `yield curve`        | quant                 |

Plus two control-plane cmd+K commands (no panel): **Save Workspace**, **Load Workspace** (open `WorkspaceDialog`).

### 1.3 Tradesa V2 plugin panels (id → title → component)

| #   | Panel id                   | Title            | cmd+K trigger       |
| --- | -------------------------- | ---------------- | ------------------- |
| 24  | `tradesa-v2.positions`     | Live Positions   | `tradesa positions` |
| 25  | `tradesa-v2.trade-history` | Trade History    | `tradesa history`   |
| 26  | `tradesa-v2.brain`         | Brain Decisions  | `tradesa brain`     |
| 27  | `tradesa-v2.sentinel`      | Sentinel         | `tradesa sentinel`  |
| 28  | `tradesa-v2.health`        | Health           | `tradesa health`    |
| 29  | `tradesa-v2.settings`      | Settings & Drift | `tradesa settings`  |
| 30  | `tradesa-v2.meta-agents`   | Meta-Agents      | `tradesa meta`      |

(Plugin id `tradesa-v2`, type `trading-bot`, `supportsControlPlane: false` — read-only enforced.)

### 1.4 Default startup layout (6 panels)

`src/config/default-layout.ts` — at boot, `applyDefaultLayout` adds these 6 panels **only if their module is enabled**: `chart`, `equity-overview`, `watchlist`, `news`, `portfolio`, `chat`. Canonical cockpit (per CLAUDE.md visual convention): left column Chart over Equity Overview (tabs); right column Watchlist / News / Portfolio / AI Assistant. **Settings is intentionally NOT opened at boot** — it is reached via cmd+K. The other 24 panels are opened on demand via cmd+K.

### 1.5 All cmd+K commands

Aggregated in `useCommandPalette.commands` from two sources:

- **Module commands** — `useModulesStore.enabledCommands()` (**only ENABLED modules' commands appear**; disabling a module removes its open-command from the palette). Includes all 25 `opensPanel` commands above + Save/Load Workspace.
- **Plugin commands** — appended by `moduleForPlugin` (`plugin-bootstrap.ts:188`), e.g. the 7 Tradesa V2 commands and all broker-plugin commands (see §1.9).

### 1.6 Chat slash commands (in-chat, separate from cmd+K)

`src/modules/chat/slash-commands.ts`: `/ask <prompt>`, `/agent <id> <prompt>`, `/provider <id>`, `/key set <provider>`, `/clear`, `/help`. Bare text = raw chat continuation. These do **not** open panels.

### 1.7 All AI agents (sidecar/agents/*.json)

buffett, dalio, druckenmiller, graham, klarman, lynch, marks, munger, portfolio_advisor, researcher (default provider openai), soros, strategy_critic (used by Backtest "Open in Strategy Critic"). Plus **custom agents** built in Agent Builder (id-prefixed `custom:`, stored sidecar-side, surfaced in the chat AgentPicker). `GET /agents` returns the first-party set; **an empty list signals the `agents/`-dir PyInstaller bundling regression** (v0.8.0 `L3` — see §4.9).

### 1.8 All brokers (10 ids — `types/broker.ts:42`)

`dhan, angelone, kite, alpaca, ib, oanda, ccxt-bybit, ccxt-binance, ccxt-kraken, ccxt-coinbase`. Modes: `paper` (default) | `live`; plus `readOnly` flag. Order types: market/limit/stop/stop-limit; sides buy/sell. Per-broker credential fields in `BrokerConnectPanel.tsx:40` (e.g. kite: api_key/api_secret/access_token/static_ip; angelone: api_key/client_code/pin/totp_secret; ib: host/port/client_id).

### 1.9 Broker plugin cmd+K commands

- **alpaca** (`broker-alpaca`): `alpaca connect`, `alpaca account`, `alpaca paper`, `alpaca live` (gated)
- **angelone** (`vysted-angelone`): `connect angelone`, `angelone-account`, `angelone-halt`
- **ccxt-exec** (`ccxt-exec`): `connect ccxt-bybit/binance/kraken/coinbase` + `halt all ccxt` (4 broker ids)
- **dhan** (`vysted-dhan`): `connect dhan`, `dhan-account`, `dhan-halt`
- **ib** (`broker-ib`): `ib connect`, `ib account`, `ib paper`, `ib live` (gated)
- **kite** (`vysted-kite`, `requiresStaticIp: true`): `connect kite`, `kite-account`, `kite-halt`, `kite-static-ip`
- **oanda** (`broker-oanda`): `oanda connect`, `oanda account`, `oanda demo`, `oanda live` (gated)

### 1.10 All workflow node types (18)

**Built-in (10)** — `data.fetch_quote`, `data.fetch_history`, `compute.indicator`, `ai.agent_invoke`, `logic.branch`, `logic.compare`, `action.log`, `action.notify_desktop`, `transform.json_path`, `flow.sleep`.
**Phase-6 data nodes (8)** — `data.fetch_macro_series`, `data.fetch_sec_filing`, `data.fetch_insider_transactions`, `data.fetch_earnings_calendar`, `data.fetch_earnings_history`, `data.fetch_analyst_history`, `data.fetch_price_target_history`, `analysis.screener_query`.
Categories: trigger | transform | condition | action | output. Plugin nodes unioned in via `VystedPlugin.contributesNodes`.

### 1.11 BYOK LLM providers (7)

anthropic (claude-opus-4-7), openai (gpt-4.1-mini), gemini (gemini-2.5-pro), groq (llama-3.3-70b-versatile), ollama (llama3.1:8b — no key), deepseek (deepseek-chat), xai (grok-2-latest). Keys stored in OS keychain via Tauri; sidecar reads from request, never persists.

### 1.12 Sidecar routers (24) and their external dependencies

- health → `/health` — in-process (version from `app.version`)
- quotes → `/quotes/{sym}`, `/quotes?symbols=` — yfinance / ccxt
- history → `/history/{sym}` — yfinance / ccxt
- crypto → `/crypto/exchanges|ticker|history`, `WS /crypto/stream` — ccxt / ccxt.pro
- fundamentals → `/fundamentals/{sym}[/income|balance|cashflow|ratings|ratings/history|...]` — openbb-mcp → yfinance fallback
- indicators → `/indicators`, `/indicators/{sym}` — yfinance + in-process compute
- macro → `/macro/search|catalog|{id}` — fredapi (BYOK), ECB/IMF/WB SDKs, legacy openbb-mcp
- news → `/news?symbols=` — RSS (Yahoo/MarketWatch) + optional NewsAPI + VADER
- portfolio → `/portfolio/positions` CRUD — local SQLite
- plugins → `/plugins`, `/plugins/{id}/config` — local SQLite
- workspace → `/workspace[/{name}]` CRUD — local SQLite/file
- custom_agents → `/custom-agents[/{id}]` CRUD — local SQLite
- mcp → `/mcp/status`, `/openbb-mcp/status` — MCP probes
- sec_filings → `/sec/status|filings|filings/{acc}|insider` — sec-edgar-mcp subprocess
- earnings → `/earnings/upcoming|{sym}/history|surprises|estimates` — yfinance (cached)
- screener → `POST /screener/run`, `/screener/universe` — yfinance/ccxt fan-out
- quant → `POST /quant/option/price|greeks`, `/bond/price`, `/yield-curve` — **in-process QuantLib (no subprocess)**
- llm → `/llm/providers`, `POST /llm/keys/validate`, `POST /llm/chat` (SSE) — BYOK provider APIs
- agents → `GET /agents`, `POST /agents/{id}/invoke` (SSE) — agent specs + LLM
- backtest → `POST /backtest/run` (SSE), `/strategies`, `/runs` — in-process engine
- workflow → `POST /workflow/run` (SSE), `/save`, `/saved` — in-process engine
- safety → `/safety/audit-log[/export.csv]`, `/kill-switch[/reset|/status]`, `/disclaimer-*`, `/static-ip-status` — SQLite (append-only, LOCKED)
- brokers → `/brokers`, `/brokers/{id}/connect|account|orders|mode|read-only`, `/brokers/kite/static-ip` — broker SDKs (LOCKED `broker_base`)
- tradesa_v2 → 11 GET routes (`/status`, `/positions`, `/trade-history`, `/decisions`, `/meta-agent-runs`, `/cost-today`, `/health`, `/kill-switch-events`, `/sentinel`, `/settings`, `/settings/drift`, `/meta-agents/{kind}`) — Supabase passthrough (read-only)

---

## 2. How each panel is supposed to open (the central question)

### 2.1 The single runtime add-panel path

`src/store/workspace.ts:30-55` — `openPanel(panelId)`:

- resolves the `PanelSpec` from `useModulesStore.findPanel(panelId)` (searches **all registered modules**, even disabled ones);
- singleton panels: if already open, `existing.api.setActive()` (focus); else `api.addPanel({id, component, title})` (`workspace.ts:46`);
- non-singleton panels (chart, macro): always `addPanel` with a freshly minted unique id (`workspace.ts:54`).

The dockview API handle is captured at mount in `PanelHost.tsx:26-27` (`handleReady`).

### 2.2 The user-facing trigger chain

cmd+K / Ctrl+K → CommandPalette opens (`CommandPalette.tsx:22-30`) → user types, ArrowUp/Down to highlight, **Enter** or click a command button (`CommandPalette.tsx:99,132`) → `executeCommand(command)` (`commands.ts:10-19`):

- if `command.opensPanel` → `workspace.openPanel(command.opensPanel)` → `dockview addPanel`;
- else if `command.commandId` → `modules.commandHandler(id)()` (control-plane handler, e.g. open WorkspaceDialog).

**There is no other user path to open a panel. There is NO drag-from-manager path anywhere in the codebase.**

### 2.3 Settings manager vs Plugin manager affordances

- **Settings panel** (`SettingsPanel.tsx`): per-module row with a single enable/disable switch. No open button, no click-to-open, no drag. The `platform` module's switch is locked on. **Clicking a card doing "nothing" is correct.**
- **Plugin manager panel** (`PluginManagerPanel.tsx`): per-plugin row with an enable/disable switch (`runtime.loadPlugin`/`unloadPlugin`) + state badge + health-history bars. Also no open-panel affordance — opening a plugin's panels is still via cmd+K (e.g. `tradesa positions`).

### 2.4 Definitive answer

> **The 15 "unopenable" panels open fine via cmd+K.** They are not blocked by anything. The symptom was a discoverability failure: the launcher is keyboard-only (cmd+K), and there is no visible "open panel" button/menu in the app chrome, so a tester who only clicked Settings cards saw nothing happen. **This is a UX/discoverability finding (S2/S3-class), distinct from the tab-drag bug (A1).**
>
> **Tab-drag rearrange (A1)** is a separate matter handled entirely inside dockview; the app adds no code to it. Re-verify with a real pointer before filing as a product defect (synthetic events cannot drive trusted drags).

### 2.5 Keyboard shortcuts affecting panels/layout

- **cmd+K / Ctrl+K** — toggle command palette (the only global panel/layout shortcut and the gateway to opening every panel).
- Within palette: ArrowUp/ArrowDown highlight, Enter runs.
- **Cmd/Ctrl+Shift+K** — fires the kill-switch request (Tauri event `kill-switch:requested`, handled by `KillSwitchToolbar`).
- Chart panel (when focused): **Escape** disarms drawing tool / deselects; **Delete/Backspace** removes selected drawing.
- No other keys close or rearrange panels (close is via dockview tab close button).

---

## 3. Expected behaviour per surface (detect _wrong_, not just crashes)

### 3.1 Chart (panel `chart`, `src/modules/chart/ChartPanel.tsx`) — lightweight-charts 5.2.0

- **Symbol input + Load** (`:851-869`): uppercases+trims, refetches `/history/{sym}`, `setData` + `fitContent`, broadcasts symbol-sync, header shows `<symbol> via <provider>`. Empty/whitespace input must **no-op**.
- **Timeframe** (8 buttons: `1m,5m,15m,30m,1h,1d,1wk,1mo`, default `1d`, `:871-888`): exactly one `aria-pressed=true`; changing it refetches history, indicators, AND comparison overlay; **selected indicators persist** across timeframe change.
- **50 indicators** (grouped buttons `:1093-1127`): toggle on → amber pressed + "computing…" → price-overlay indicators on pane 0, oscillators on incrementing panes. "Clear (N)" resets all. **No per-indicator parameter UI** — periods are server defaults (RSI 14, SMA 20, MACD 12/26/9). Nothing selected by default. Special renders:
  - **VWAP**: price overlay; intraday resets cumulative per calendar day (label "VWAP (session)"); daily+ runs continuous. Wrong if intraday runs across days or daily resets.
  - **Parabolic SAR**: **circle markers** (green dot belowBar in uptrend, clay aboveBar in downtrend), NOT a line.
  - **Ichimoku**: 5 lines + filled cloud projecting 26 bars ahead; small gap at A/B crossovers is **expected** (trapezoid intentionally skipped).
  - **Volume Profile**: horizontal histogram from the right edge, max bar 25% pane width.
  - Indicator colors cycle through only 5 colors — a >5-line indicator repeats colors (expected).
- **Compare / overlay symbol** (`:967-1014`): Add fetches `/history/{compareSym}`, draws sage line; `%` toggle (default ON) normalizes to `(close/close[0]−1)*100` on a **left** price scale, OFF = raw closes on **right** scale; title `"<SYM> %"`/`"<SYM>"`; `×` clears. Bad compare symbol is **silently swallowed** — must not break the primary chart.
- **Drawing tools / draw-arm** (10 tools: Trend, H-Line, V-Line, Ray, Rect, Ellipse, Fib Retr, Fib Ext, Channel, Text): click a tool button to ARM (DOM), then click the canvas the required number of times (1 click: H-Line/V-Line/Text; 2: Trend/Ray/Rect/Ellipse/Fib Retr; 3: Fib Ext/Channel). Final click commits + disarms. Fib levels `0/.236/.382/.5/.618/.786/1`. Inspector list has per-drawing Select/Lock/Delete + "clear (N)". **Lock is metadata only — no drag-edit exists.** Escape disarms; Delete/Backspace removes selected.
- **Multi-chart sync** (3 toggles Cx/Zm/Sy): crosshair-time sync, visible-range/zoom sync, symbol sync — each independent; self-echo skipped; closed panels stop echoing (unmount `unregisterPanel`).

### 3.2 Watchlist (`watchlist`)

Add-symbol form (text input + Equity/Crypto select + Plus submit) → `addSymbol`. Quote table: row click → `setSelectedSymbol`; per-row X → `removeSymbol`. Polls `/quotes` + `/crypto/ticker` every 5s; prices tick. States: "Loading quotes…" / "No symbols tracked." / error banner.

### 3.3 News (`news`)

Refresh button → `fetchNews(watchlist)`. Rows are external links (`target=_blank`), with SentimentBadge (positive/negative/unscored) + symbol chips. Filtered to watchlist symbols. States: "Loading news…" / error + **Retry** button / "No news for the current watchlist." **Known: initial fetch may fail → Retry recovers (S2) — see §4.3 & §8.3.**

### 3.4 Portfolio (`portfolio`)

Add/edit form (Symbol, Quantity, Cost basis, Note, Equity/Crypto, Plus "Add"/"Save", Cancel-edit X) → `createPosition`/`updatePosition`. Summary strip (market value, total P&L, concentration, unresolved). Rows with live Price/Mkt value/P&L/Weight + per-row Edit/Delete. States: "Loading portfolio…" / "No positions yet — add one above." / error banner.

### 3.5 Equity Overview (`equity-overview`)

Symbol form + "Load" → `loadEquityOverview`. Renders header (price/change/sector), 10 valuation ratios, analyst consensus, 3 statement tables (Income/Balance/Cash flow). Per-section "Unavailable." on partial failure; error banner only when **all** sections fail.

### 3.6 AI Assistant / chat (`chat`)

AgentPicker select (No agent / first-party / custom). ContextBadge. Composer (input + Send, disabled while streaming). KeyEntryDialog via `/key set`. 7 providers. Slash commands per §1.6. Empty BYOK key → graceful error in stream.

### 3.7 Agent Builder (`agent-builder`)

Form: ID (prefix `custom:`), Name, Philosophy, System prompt textarea, Tools toggles (`price_data, fundamentals, news, backtest_summary, macro`), Default provider select, Default model, Icon. Submit "Create agent"/"Save changes"; Cancel when editing. List column with per-agent edit/delete. → `POST/PUT/DELETE /custom-agents`. Validation errors per field; "No custom agents yet…" empty state.

### 3.8 Backtest (`backtest`)

StrategyPicker (radio list) → ParamsForm (per-strategy schema). Universe inputs: Symbols, Start/End dates, Initial capital, Walk-forward slices (1–10). "Run backtest" (testid `run-backtest`) → SSE `/backtest/run`. Result: metrics (Return/Sharpe/Sortino/Calmar/MaxDD/WinRate/Trades), equity+drawdown chart, walk-forward strip, sortable trade table, "Open in Strategy Critic" (injects `/agent strategy_critic` into chat). States: idle / pending / streaming / `run-error` testid / "No trades yet."

### 3.9 Node Editor (`node-editor`)

Toolbar: Workflow name input, New, Load (`/workflow/saved`), Save (dialog → `/workflow/save`), Run (SSE `/workflow/run`). NodePalette (draggable cards, MIME `application/x-vysted-node-type`) → drop on ReactFlow canvas → connect edges. PropertiesPanel (typed config per node; plugin nodes get free-form JSON + Apply; Delete node). WorkflowRunOverlay (per-node status, Close, Rerun). LoadDialog / SaveDialog. **Node drag-from-palette and edge-drawing are canvas gestures — ⚠️RAW-COORD.**

### 3.10 Plugin Manager (`plugin-manager`)

Header summary (active/loaded counts). Per-plugin row: state badge (discovered/initializing/active/stopping/stopped/error), enable/disable switch → `loadPlugin`/`unloadPlugin`, error box, HealthHistory bars. No open-panel affordance.

### 3.11 Settings (`settings`, platform module)

Per-module enable/disable switch only; `platform` locked on. WorkspaceDialog (Save: name input + Save; Load: list with per-row name button → `loadWorkspace`, Delete; Cancel). Backed by `/workspace` (sidecar-persisted).

### 3.12 Safety surfaces

- **Audit Log Viewer** (`audit-log`): filters — Broker select (all + 10 + `_meta`), Action select (12 actions), DateRange From/To (`datetime-local`), Reset, **Export CSV** (downloads `/safety/audit-log/export.csv`). Polls `/safety/audit-log?limit=200` every 2s. Table ID/Time/Broker/Action/Payload/Source/Outcome. Empty: "No audit entries match the filter."
- **KillSwitchToolbar** (fixed top-right, always present): armed "Halt All Trading" destructive button → `POST /safety/kill-switch`; fired-state "Kill switch fired — Reset". Cmd/Ctrl+Shift+K fires it. Banner shows subs/p95/max ack ms + dismiss.
- **OrderConfirmationDialog**: manual vs AI variant; AI requires "I reviewed this AI-proposed order" checkbox to enable Confirm; live orders require "I understand — place live order"; Decline/Confirm.
- **DisclaimerFlow**: first-launch ToS dialog; per-broker first-connect dialog.

### 3.13 Macro (`macro`)

Provider tabs FRED/ECB/IMF/World Bank → search input (debounced → `/macro/search`) → results listbox → `loadSeries`. MacroChart (lightweight-charts). Default FRED/DGS10 on mount. States: "Loading {id}…" / `macro-error` testid / "Select a series."

### 3.14 SEC Filings (`sec-filings`)

Symbol/CIK input + Load → `loadFilings`. Form select (all/10-K/10-Q/8-K/DEF 14A). Tabs Filings/Insider. FilingsListTable (sortable form_type/filed_date/period). FilingViewer (Close, "View original on EDGAR ↗", section nav). InsiderTradingTable (form-type filter + Date/Reporter/Title/Form/Code/Direction/Shares/Price/Value). Default AAPL on mount.

### 3.15 Earnings Calendar (`earnings-calendar`)

Form: Window days (1–60), Watchlist (comma-sep), Apply → `loadUpcoming`. Sortable table (Symbol/Date/Time/Consensus EPS/Dispersion·#analysts). Row click expands drill-down (surprise chart + EPS estimate grid). States: "Loading…" / "No upcoming earnings in this window." / error.

### 3.16 Analyst Ratings (`analyst-ratings`)

Symbol form + Load → history/price-targets/individual. Three tabs: History / Price Targets / Individual. Sub-tables + price-target timeline chart. Idle: "Enter a symbol…"; per-tab inline error.

### 3.17 Screener (`screener-panel`)

Universe select (sp500/nifty50/crypto-top50/custom) + custom-symbols input. CriteriaBuilder: "Add criterion" → rows with category (Numeric/String/Set), field select (13 numeric / 3 string / 3 set), operator (gt/lt/gte/lte/between), value(s), remove. "Run screener" (testid `run-screener-button`) → `POST /screener/run`. ResultsTable (sortable Symbol/Name/Sector/MktCap/PE/Price/1d%/Volume). Empty: "No rows matched the criteria."

### 3.18 Quant (4 panels)

- **Option Pricer**: method radiogroup (Black-Scholes / Binomial CRR / Monte Carlo), Call/Put, European/American, Spot/Strike/r/q/σ, dates, conditional Tree steps / MC paths+seed, incompatibility alert (American+BS / American+MC), "Price" (testid `price-option`) → price + (MC std error).
- **Greeks Dashboard**: Call/Put, Spot/Strike/r/q/σ, dates, "Compute Greeks" (testid `compute-greeks`) → price + Δ/Γ/ν/Θ/ρ.
- **Bond Pricer**: Face/Coupon, coupons-per-year (1/2/4), Issue/Maturity/Settlement, YTM, "Price" (testid `price-bond`) → Clean/Dirty/Accrued + Macaulay/Modified Duration + Convexity.
- **Yield Curve**: valuation date, instrument rows (depo/swap, rate, tenor unit mo/yr, tenor), add/remove, sample count, "Bootstrap" (testid `bootstrap-curve`) → curve chart + table.

### 3.19 Tradesa V2 (7 panels)

Shared `_PanelShell`: branches on connection status — skeleton / `unauthenticated` (Connect button → `TradesaSettingsDialog`) / `supabase-error` (Retry) / `bot-offline` banner / `partial` banner / healthy body. SettingsDialog: Supabase URL (testid `tradesa-settings-url`), service-role key + show/hide, Cancel + "Save & Connect" (stored in keychain, sent as `X-Tradesa-Supabase-*` headers). Per-panel content per §1.3. **All read-only; non-GET must be impossible (405).**

---

## 4. Failure-mode map (per surface — where it can break)

### 4.1 Global / cross-cutting

- **CORS-masks-500 trap**: any 5xx surfaces in the browser console as "blocked by CORS policy" (`app.py:145-155` — CORS headers not added to error responses). When a panel shows a CORS error, **curl the endpoint directly** to find the real status. Don't chase CORS config.
- **`ProviderError` → 502** is the global contract; some routers pre-translate to 400/501.
- **Sidecar down**: every fetch is connection-refused → in-browser looks like CORS. Distinguish via direct curl / `/health`.

### 4.2 Chart

- Empty bars → blank chart, **no error banner**, state `ready` (could hide a data bug).
- Bad/unknown symbol → 502 → error overlay + Retry. **Retry may be a no-op** (sets symbol to same string → React bails) — verify Retry actually issues a new `/history` call (§8 hypothesis).
- `/indicators` failure → inline indicator error, price data stays intact.
- Comparison fetch failure → **silently swallowed** (must not break primary).
- Rapid timeframe toggling → cancel-flag guards last-click-wins, but compare+indicator effects rebuild series — watch for transient double-add / orphaned series / flicker (no debouncing).
- **Drawings persist across symbol switch** (anchored to absolute time/price, stored per panel not per symbol) — a trendline on SPY still renders after switching to NVDA, landing in a nonsensical spot. By design; UX trap to verify.
- Stale compare legend after primary symbol change (§8.1); price-axis label overlap with dual scales (§8.2).

### 4.3 News (the known S2)

- First fetch fails / Retry recovers: `fetch_news` raises only when **every** source fails (`news_provider.py:237-238`) → 502. Cold-network first request (cold DNS + TLS, no shared httpx client, 10s timeout, Yahoo/MarketWatch 429 on burst, per-symbol fan-out multiplying cold connections) trips all-failed; warm retry succeeds. **Provoke:** launch fresh, immediate `GET /news`, expect intermittent 502 then Retry → 200. Not a VADER warmup issue.
- Partial failure → 200 with partial results. Watchlist with no matches → empty 200. `limit` out of 1–200 → 422.

### 4.4 Quotes / History / Crypto

- Single bad symbol → 502; batch bad symbol → dropped, 200 with fewer rows.
- `BRK.B`→`BRK-B` normalized (test dot tickers).
- Unknown timeframe on history → silently defaults to `1d/1y` (not an error).
- Empty frame → `bars=[]`, 200.
- Crypto unsupported exchange → 502; WS stream unsupported → close code **1011**; client disconnect → clean.

### 4.5 Fundamentals / Equity Overview

- openbb-mcp up but errors → falls back to yfinance (provider field flips).
- openbb-mcp not bound → straight to yfinance (200).
- yfinance also fails → 502.
- Extended ratings (history/price-target/individual) → 502 on ProviderError; thin coverage → empty arrays 200; cache corruption → refetch.

### 4.6 Macro

- Missing `FRED_API_KEY` → 502 "requires FRED_API_KEY".
- Unknown provider literal → legacy path → 501 if openbb-mcp not bound.
- FRED/ECB/IMF/WB paths unaffected by openbb-mcp. Empty search → `[]` 200. Cache corruption → refetch.

### 4.7 SEC Filings

- Subprocess not bound → **501** on every route except `/status`.
- ProviderError (bad CIK / MCP tool failure) → 502.
- `/sec/filings` with neither cik nor symbol → 400.

### 4.8 Quant

- **No subprocess dependency — pure in-process QuantLib.** Only failure: bad params (negative vol, empty instrument list, malformed curve) → 400. Brief's claim that quant depends on MCP is **wrong** — correct here.

### 4.9 MCP subprocess degradation matrix (openbb-mcp / sec-edgar-mcp)

- `/fundamentals/*` base, openbb quotes → yfinance fallback (200) when subprocess NOT bound
- legacy `/macro/{id}` (no provider) → 501
- `/macro?provider=fred|ecb|imf|world-bank`, search, catalog → unaffected
- `/sec/*` (except `/sec/status`) → 501
- `/sec/status`, `/openbb-mcp/status`, `/mcp/status` → 200 (`available:false`)
- `/quant/*`, `/screener/*`, `/earnings/*` → unaffected

- **`agents/` dir bundling**: if `--add-data` missing, `GET /agents` returns `[]` 200 → AgentPicker empty, all named agents unavailable. **Verify `/agents` returns the full first-party set (an empty list is the bug).**
- **`screener` universe snapshot bundling**: missing universe JSON → 502 "missing universe snapshot."
- **Smoke-test gap**: "alive after 10s" doesn't TCP-probe the port; a subprocess can be alive-but-not-listening. Confirm via `/health` `providers.openbb-mcp` and `/openbb-mcp/status`.

### 4.10 Portfolio / Plugins / Workspace / Custom Agents (SQLite)

- Unknown id → 404; bad body → 422; SQLite I/O error (bad data dir) → 500.
- Workspace name with `../`/slashes/empty → 400 (path-traversal guard).
- Custom agent id without `custom:` prefix → 400/422; duplicate id → 409; unknown tool id → 422.

### 4.11 LLM / Agents / Backtest / Workflow (SSE)

- These return **HTTP 200 then emit errors as SSE `error`+`done` frames** — not HTTP error codes. Bad provider/agent id → 400/404 _before_ streaming. Missing BYOK key surfaces inside the stream.
- Backtest bad symbol / no bar loader → `run-error` SSE frame. Unknown run_id → 404.
- Workflow validation failures → run-error events; unknown saved id → 404.

### 4.12 Safety

- Audit-log `limit` out of 1–5000 → 400; CSV with exactly one of start/end → 400; kill-switch reset without `acknowledged:true` → 400.
- Static-ip detector network-blocked → `matches:false` 200 (never raises).
- Disclaimer ack is session-scoped — resets on sidecar restart.

### 4.13 Brokers

- Unknown broker id → 404; connect body broker ≠ path broker → 400; bad creds → 400; other → 502.
- Confirm stale/unknown proposal_id → 404. **Proposals are in-memory — lost on sidecar restart.**
- Kite static-IP does NOT pre-block orders; rejection happens at order time → 400 + graceful dialog.

### 4.14 Tradesa V2 (degradation matrix)

- Missing either credential header: `/status` → 200 `unauthenticated` (renders settings dialog); all other routes → **401**.
- Supabase unreachable / bad URL / client init fail / `supabase-py` missing → `supabase-error` → 502 (but `probe_connection`/`/status` returns it as 200 state, never raises).
- Heartbeat stale >5min or no rows → `bot-offline` 200; schema drift → `partial` 200.
- `/meta-agents/{kind}` bad kind → 422; limit out of bounds → 422.
- **Read-only invariant**: POST/PUT/DELETE to any `/tradesa-v2/*` → **405** (no non-GET route registered).

---

## 5. Edge cases + adversarial inputs (per surface)

- **Symbol inputs (chart/equity/watchlist/portfolio/sec/ratings):** empty/whitespace (must no-op), lowercase (→ uppercased), dot tickers `BRK.B`, junk `ZZZZZ` (→ 502 → error UI), very long string, unicode/emoji, leading/trailing spaces, crypto pair `BTC/USDT` vs equity, SQL-ish `'; DROP`, extremely rapid repeated submits.
- **Watchlist:** add duplicate symbol; add 100+ symbols (polling load); remove last symbol (→ empty state); rapid add/remove.
- **Portfolio:** quantity = 0, negative, huge (1e15), fractional; cost basis negative/0; empty submit; edit then cancel; delete all (→ empty); crypto vs equity asset-class mismatch.
- **Backtest:** Start > End dates; Start = End; initial capital 0/negative; walk-forward slices 0 / 11 (out of 1–10); symbols empty; junk symbols; very long date range.
- **Quant:** negative volatility/rates; time-to-expiry 0 or negative (expiry ≤ valuation); strike 0; American+Black-Scholes / American+Monte-Carlo (incompatibility alert); empty yield-curve instruments; coupon > 100%; maturity before settlement.
- **Screener:** custom universe with junk symbols (low evaluated_count, 200); `between` with min > max; empty criteria (matches all); 20+ criteria; non-numeric value in numeric field.
- **Macro:** empty search; search returning nothing; switch provider mid-load; FRED with no key; rapid series switching.
- **Earnings:** window days 0 / 61 (out of 1–60); empty watchlist; thin-coverage tickers.
- **Chat:** empty submit; `/agent <unknown>`; `/provider <unknown>`; `/key set` with no provider; huge prompt; rapid-fire sends while streaming (Send disabled?); switch agent mid-stream.
- **Agent Builder:** id without `custom:` prefix; duplicate id (→ 409); empty required fields; very long system prompt; toggle all tools off; delete an agent in use by chat.
- **SEC:** CIK vs symbol; neither (→ 400); junk CIK; form filter with no matching filings.
- **Node Editor:** save with empty name; duplicate workflow name; run with disconnected/cyclic graph; delete a node mid-edit; plugin node with malformed JSON config.
- **Safety:** audit-log limit 0 / 5001; CSV with only start (or only end); kill-switch reset without acking; fire kill-switch repeatedly.
- **Tradesa V2:** save with empty URL/key; malformed Supabase URL; connect then bot offline; rapid panel switching while unauthenticated.
- **Workspace:** save with name `../x`, empty name, duplicate name; load then delete the loaded workspace.
- **General UI:** rapid theme toggling (dark only ships), window resize between 1920×1080 and 2560×1440 (table overflow), open the same singleton panel twice (→ focus existing), open many non-singleton chart/macro panels, close all panels, workspace swap mid-stream.

---

## 6. Interaction method per test + raw-coordinate flags

**⚠️RAW-COORD** = requires trusted pixel-level pointer or native event injection; synthetic events are rejected (`isTrusted`). These are the tests the first black-box pass could NOT perform — prioritize confirming/denying them.

### 6.1 Normal DOM interactions (standard click/type)

- **Opening any panel:** press **Ctrl+K / Cmd+K** → type the trigger (e.g. `macro`, `screener`, `option pricer`) → **Enter**. (This is the canonical way to reach all 31 panels — do NOT expect Settings cards to open them.)
- All toolbar buttons, dropdowns/selects, text inputs, form submits, tab buttons, radio groups, checkboxes, enable/disable switches, table sort headers, drawing-tool ARM buttons (arming only), inspector Select/Lock/Delete buttons, Retry/Refresh/Export-CSV buttons.
- Keyboard: Ctrl+K, Escape, Delete/Backspace (chart drawings), Arrow/Enter in palette, Ctrl+Shift+K (kill-switch).

### 6.2 ⚠️RAW-COORD — require trusted pointer / native injection (FLAGGED)

- **Tab-drag rearrange (A1/S1)** — drag a dockview tab header onto another panel's tab strip or center drop-zone — dockview HTML5 drag needs trusted events
- **Chart drawing placement** — click inside the chart canvas (`data-testid="chart-container"`); 1–3 clicks per tool — lightweight-charts `subscribeClick` only fires on trusted canvas events
- **Chart drag-to-pan** — horizontal drag inside the chart canvas — built-in gesture
- **Chart scroll-zoom** — mouse-wheel over chart canvas — built-in gesture
- **Crosshair hover (drives crosshair-sync)** — mouse-move over chart canvas (2 chart panels with Cx on) — `subscribeCrosshairMove` trusted-only
- **dockview splitter/panel resize** — drag the divider between two adjacent panels — drag gesture
- **Node Editor: drag node from palette** — drag a card from the left NodePalette onto the ReactFlow canvas — HTML5 drag
- **Node Editor: draw edge between nodes** — drag from a node's output handle to another node's input handle — canvas pointer gesture

> For each ⚠️RAW-COORD test: screenshot, locate the landmark, compute pixel coords, drive with a real pointer. **If the tool genuinely cannot synthesize trusted events, mark the test "UNTESTABLE via this harness" rather than "failed"** — a synthetic-event failure is not proof of a product defect.

### 6.3 Tests needing a built binary (not the dev server)

- **Next.js dev badge (S2):** only the `tauri build` static export (`../out`) is authoritative — the dev server injects the dev indicator (§8.4). Verify the badge is ABSENT in a real build.
- **`/agents` count** and **screener universe loads** — runtime data-bundling checks meaningful against the built sidecar binary.

---

## 7. Prioritized, numbered test checklist

Severity key: **S1** = blocks core use / data loss / safety; **S2** = major feature broken or wrong data; **S3** = visual/polish/edge. Each item: action → expected → drive → severity-if-failed.

### A. Panel-open & shell (resolves the central question)

1. Press Ctrl+K → palette opens. Expected: overlay with searchable command list. Drive: keyboard. **S1** if palette never opens.
2. Ctrl+K → type each of the 25 module triggers → Enter. Expected: each opens its panel into dockview (singletons focus if already open). Drive: keyboard. **S1** per panel that fails to open.
3. Open a singleton panel twice via cmd+K. Expected: second invocation focuses the existing panel, no duplicate. Drive: keyboard. **S2**.
4. Open `chart` twice and `macro` twice. Expected: non-singletons create distinct panels. Drive: keyboard. **S2**.
5. Settings panel: click a module card body (not the switch). Expected: **nothing happens (correct)**. Drive: DOM click. **S3** (file as discoverability finding only).
6. Settings: toggle a module off → reopen palette. Expected: that module's open-command disappears; toggle on → reappears. Drive: DOM. **S2**.
7. Settings: toggle off a module whose panel is open. Expected: define/observe behaviour. Drive: DOM. **S2**.
8. ⚠️RAW-COORD: drag a panel tab to a new dock position. Expected: tab moves / panel re-docks. Drive: native pointer. **S1** if it fails with a real pointer; if the harness can't synthesize trusted drag, mark UNTESTABLE.
9. ⚠️RAW-COORD: drag the splitter between two panels. Expected: panels resize. Drive: native pointer. **S2**/UNTESTABLE.
10. Close a panel via its tab X. Expected: panel closes, `closePanel` runs. Drive: DOM. **S2**.
11. Save workspace → rearrange/close panels → Load workspace. Expected: layout restored. Drive: DOM. **S2**.
12. Resize window 1920×1080 ↔ 2560×1440. Expected: no overflow; price-axis labels not clipped. Drive: resize. **S3**.

### B. Chart

13. Symbol input: load AAPL, then SPY, then BTC/USDT. Expected: candles refit, header `<sym> via <provider>`, symbol-sync broadcast. **S2**.
14. Empty/whitespace symbol submit. Expected: no-op. **S3**.
15. Junk symbol `ZZZZZ`. Expected: 502 → error overlay + Retry. **S2**.
16. Click Retry on a junk-symbol error. Expected: a new `/history` request fires. **Watch the no-op risk.** **S2** if Retry issues no request.
17. Cycle all 8 timeframes. Expected: exactly one pressed; history+indicators+compare refetch; selected indicators persist. **S2**.
18. Toggle each of the 50 indicators on, observe render, then Clear (N). Expected per §3.1. **S2** per broken indicator.
19. VWAP on intraday (5m) vs daily (1d). Expected: intraday resets per day, daily continuous. **S2**.
20. Parabolic SAR. Expected: circle markers above/below bars, not a line. **S3**.
21. Ichimoku. Expected: 5 lines + projected cloud; small crossover gap fine. **S3**.
22. Volume Profile. Expected: horizontal histogram from right edge. **S3**.
23. Compare: add QQQ with `%` ON then OFF; clear with `×`. Expected: normalized left-scale vs raw right-scale; title `QQQ %`/`QQQ`. **S2**.
24. Compare bad symbol. Expected: silently swallowed, primary chart intact. **S2** if primary breaks.
25. **Stale compare legend (S3 known):** add compare QQQ, then change PRIMARY symbol to NVDA. Expected: compare legend updates/clears. Observed bug: stale `QQQ %` persists. **S3** (§8.1).
26. **Price-axis overlap (S3 known):** compare ON (`%`) + several oscillators at 2560×1440 and 1920×1080. Expected: axis labels not overlapping. **S3** (§8.2).
27. ⚠️RAW-COORD: arm each of the 10 drawing tools (DOM), then place required clicks on canvas. Expected: drawing commits after final click, disarms; inspector lists it. **S2**/UNTESTABLE.
28. ⚠️RAW-COORD: drag-to-pan and scroll-zoom. Expected: chart pans/zooms. **S3**/UNTESTABLE.
29. Drawing inspector: Select / Lock / Delete / clear(N). Expected per §3.1; Lock is metadata only. **S3**.
30. Escape disarms tool; Delete removes selected drawing. **S3**.
31. Draw on SPY, switch symbol to NVDA. Expected: drawing persists at absolute anchors (UX trap). **S3**.
32. ⚠️RAW-COORD: 2 chart panels, toggle Cx/Zm/Sy individually, hover/zoom/change-symbol on one. Expected: only matching sync flavor propagates; no self-echo; closing one stops echo. **S2**/partial-UNTESTABLE.
33. Rapid timeframe toggling with indicators+compare active. Expected: last-click wins, no orphaned/duplicate series, no flicker. **S2**.
34. Empty-data symbol (delisted). Expected: blank chart, no crash, note absence of error banner. **S3**.

### C. Watchlist / News / Portfolio / Equity

35. Watchlist: add AAPL, MSFT, NVDA, SPY, QQQ, BTC/USDT, ETH/USDT. Expected: rows with ticking prices (5s poll). **S2**.
36. Watchlist: add duplicate; add junk; remove rows; remove last (empty state). **S3**.
37. News: load with populated watchlist. Expected: 3–5 articles with sentiment badges + symbol chips. **S2**.
38. **News first-fetch failure (S2 known):** fresh launch, immediate news load. Expected: articles load. Observed: may show error → Retry → recovers. **S2** (§8.3).
39. News empty watchlist / no matches. Expected: "No news for the current watchlist." **S3**.
40. Portfolio: add ≥1 AAPL position with qty + cost. Expected: live P&L, summary strip. **S2**.
41. Portfolio: edit, cancel-edit, delete; qty 0/negative/huge/fractional; empty submit. **S3**.
42. Equity Overview: load AAPL. Expected: all sections populated. **S2**.
43. Equity Overview: junk symbol → all sections fail → error banner; partial failure → per-section "Unavailable." **S2**.

### D. AI / Agents / Backtest

44. Chat: send a prompt with NO BYOK key configured. Expected: graceful error in stream. **S2**.
45. Chat: configure a key via `/key set anthropic`, pick an agent, send. Expected: streamed response. **S2**.
46. Chat: `/help`, `/clear`, `/provider <unknown>`, `/agent <unknown>`, empty submit, rapid sends while streaming. **S3**.
47. AgentPicker: confirm all first-party agents + any custom agents appear. Expected: full first-party set listed (empty = §4.9 bundling bug). **S1** if list empty.
48. Agent Builder: create a custom agent (valid), edit it, delete it. Expected: appears in chat picker. **S2**.
49. Agent Builder: id without `custom:` prefix; duplicate id; empty required fields; all tools off. Expected: validation / 409. **S3**.
50. Backtest: run a strategy on SPY with valid params. Expected: SSE progress → metrics + equity chart + trades. **S2**.
51. Backtest: Start>End; capital 0/negative; slices 0/11; junk symbols. Expected: validation / run-error frame. **S3**.
52. Backtest: "Open in Strategy Critic." Expected: injects `/agent strategy_critic` into chat. **S2**.

### E. Quant (4 panels)

53. Option Pricer: price a call with all 3 methods (BS/Binomial/MC). Expected: price (+ MC std error). **S2**.
54. Option Pricer: American+Black-Scholes and American+Monte-Carlo. Expected: incompatibility alert. **S3**.
55. Option Pricer: negative vol / expiry ≤ valuation / strike 0. Expected: 400 error surfaced. **S3**.
56. Greeks Dashboard: compute. Expected: price + Δ/Γ/ν/Θ/ρ. **S2**.
57. Bond Pricer: price. Expected: Clean/Dirty/Accrued + durations + convexity. **S2**.
58. Bond Pricer: maturity before settlement; coupon > 100%. Expected: 400. **S3**.
59. Yield Curve: bootstrap with depo+swap instruments. Expected: curve chart + table. **S2**.
60. Yield Curve: empty instruments. Expected: 400. **S3**.

### F. Macro / SEC / Earnings / Analyst / Screener

61. Macro: default FRED/DGS10 loads; switch provider tabs FRED→ECB→IMF→World Bank; search + select a series. Expected: chart renders. **S2**.
62. Macro: FRED with no `FRED_API_KEY`. Expected: 502 "requires FRED_API_KEY" (graceful error UI). **S2**.
63. Macro: empty search / rapid series switching / switch provider mid-load. **S3**.
64. SEC: default AAPL filings load; form filter; open a filing; section nav; EDGAR link; Insider tab. Expected per §3.14. **S2**. (Subprocess down → 501 graceful — verify the message.)
65. SEC: load by CIK; neither cik nor symbol (→400); junk CIK (→502). **S3**.
66. Earnings: Apply with window 7 + watchlist. Expected: sortable upcoming table; row expand → surprise chart + estimate grid. **S2**.
67. Earnings: window 0/61; empty watchlist; thin-coverage ticker. **S3**.
68. Analyst Ratings: load AAPL; three tabs. Expected: tables + timeline chart. **S2**.
69. Screener: sp500 universe, add criteria, Run. Expected: results table, sortable. **S2**.
70. Screener: custom universe with junk symbols; `between` min>max; empty criteria; 20+ criteria. **S3**.

### G. Node Editor / Workflow

71. ⚠️RAW-COORD: drag a node from each palette category onto the canvas. Expected: node appears. **S2**/UNTESTABLE.
72. ⚠️RAW-COORD: connect two nodes with an edge. Expected: edge drawn. **S2**/UNTESTABLE.
73. PropertiesPanel: edit a built-in node's typed config; a plugin node's free-form JSON + Apply; Delete node. **S2**.
74. Save a workflow, Load it, run it (SSE overlay), Rerun, Close overlay. **S2**.
75. Workflow: save empty name; duplicate name; run disconnected/cyclic graph; malformed plugin-node JSON. Expected: validation / run-error. **S3**.

### H. Plugins / Brokers / Safety

76. Plugin Manager: enable/disable each plugin; observe state badge + health bars. Expected: load/unload reflected; Tradesa V2 commands appear/disappear in palette. **S2**.
77. Broker Connect: open panel, attempt connect with bad creds for each broker. Expected: 400 graceful error; no live order path without gating. **S2** (do NOT attempt live orders).
78. Broker mode toggle paper↔live; read-only toggle. Expected: state reflected; live gated behind confirmation. **S2**.
79. Audit Log: open viewer; apply Broker + Action + DateRange filters; Reset; Export CSV. Expected: filtered rows; CSV downloads. **S2**.
80. Audit Log adversarial: confirm limit/range guards. **S3**.
81. Kill Switch: arm "Halt All Trading" (paper context); observe fired state; Reset (requires ack). Also Ctrl+Shift+K. **S1** (safety surface).
82. Order Confirmation: trigger a paper order proposal; confirm AI-review checkbox gates Confirm; Decline path. **S1**.
83. Disclaimer flow: first-launch ToS; per-broker first-connect. Expected: dialogs gate. **S2**.

### I. Tradesa V2 (7 panels)

84. Open each of the 7 Tradesa panels via cmd+K with NO credentials. Expected: `_PanelShell` shows `unauthenticated` state with Connect button. **S2**.
85. Open SettingsDialog, save bad/empty Supabase URL+key. Expected: validation / `supabase-error` retry state. **S2**.
86. With (mock/real) Supabase config: confirm each panel renders data or empty state. **S2**.
87. Bot offline (stale heartbeat) → `bot-offline` banner; schema drift → `partial`. **S3**.
88. Confirm read-only: no write/place/cancel control anywhere in Tradesa panels; non-GET to `/tradesa-v2/*` → 405. **S1** (safety invariant).

### J. Build-artifact & runtime-bundling checks (built binary)

89. **Dev badge (S2 known):** in a real `tauri build`, confirm NO Next.js dev indicator overlaps the chart control. Expected: absent in build. **S2** (§8.4).
90. `/agents` returns the full first-party set (not `[]`). Drive: AgentPicker / curl. **S1** if empty (§4.9).
91. Screener universe (sp500) loads (not "missing universe snapshot" 502). **S2**.
92. Sidecar-down behaviour: stop sidecar, observe panels. Expected: graceful errors (NOT silent blanks); confirm CORS-masking trap (curl shows real cause). **S2**.
93. MCP subprocess not-listening: confirm `/health` `providers.openbb-mcp:unavailable`, fundamentals fall back to yfinance (200), legacy macro/sec → 501 graceful. **S2**.

---

## 8. Codebase-level root-cause hypotheses for known bugs

### 8.1 Stale "SPY %" compare legend after symbol change (S3)

**Real defect.** The comparison-overlay effect's deps are `[compareSymbol, compareNormalize, timeframe]` (`ChartPanel.tsx:761`) — it does **NOT** depend on the primary `symbol`. The overlay title is built once (`:745`) and normalized to the compare series' own `close[0]` (`:151`). When the primary symbol changes, this effect doesn't re-run; the prior overlay + its `%` legend persist against the stale window. **Fix:** add `symbol` to the effect deps at `:761`, or clear/rebuild the overlay inside the price-load effect on primary-symbol change.

### 8.2 Price-axis label overlap (S3)

With `compareNormalize` ON, the overlay uses a **left** price scale (`:748`) while candles + price-pane indicators use the **right** scale; multiple `lastValueVisible:true` tags stack on the right axis. There is **no `scaleMargins` / label-collision config** — `CHART_THEME` (`:64-77`) sets only border colors. **Fix:** manage scale margins / dedupe last-value labels / disable `lastValueVisible` on overlay indicators.

### 8.3 News first-fetch fails / Retry recovers (S2)

`fetch_news` raises only when **every** source fails (`news_provider.py:237-238`) → 502. Fragility is cold-network + no-retry + all-or-nothing: synchronous one-shot `httpx.get` per feed, no shared client/pool, hard 10s timeout, `raise_for_status()` turns transient 429/5xx into failures, default watchlist fans out one feed per symbol (up to ~8 cold sequential calls). Warm retry succeeds. **Not** a VADER warmup issue. **Fix:** shared `httpx.Client` with pooling + keep-alive, per-source retry with backoff, raise only on total failure after retries, optionally prewarm connections at startup, don't 502 when _some_ sources succeed.

### 8.4 Next.js dev-tools badge overlapping a chart control (S2)

`next.config.ts` sets `output:"export"` + `images.unoptimized` but no `devIndicators` key, so the dev indicator is at framework default (shown in `next dev`). The badge was observed because the audit ran against the dev server. **The static export shipped by `tauri build` does NOT include it.** **Fix (optional):** add `devIndicators: false`; verify against a real `tauri build`.

### 8.5 Tab-drag rearrange does nothing (A1/S1)

No app code touches dockview tab DnD (`PanelHost.tsx:47` mounts `<DockviewReact>` with no DnD props). The drag is dockview-internal. Two candidates: (a) synthetic events can't drive trusted HTML5 drag — so harness-based QA reports failure regardless (most likely the prior S1 was a harness artifact); (b) a Tauri WebView drag-interception quirk. **Action:** first re-test with a real pointer; only if it still fails investigate Tauri webview drag config / dockview version. **Distinct from the panel-open issue.**

### 8.6 "15 panels won't open" (A2)

**Not a bug in the open path** — all open fine via cmd+K. Root cause is **discoverability**: the only launcher is keyboard-only cmd+K, no visible "open panel" button/menu, and the Settings/Plugin managers only enable/disable. **Fix (UX, optional):** add a visible launcher — a feature gap, not a regression.

---

## Appendix — key file references

- Panel open: `src/store/workspace.ts:30-55`, `src/lib/commands.ts:10-19`, `src/components/CommandPalette.tsx`, `src/config/default-layout.ts`, `src/components/{SettingsPanel,PluginManagerPanel}.tsx`, `src/components/PanelHost.tsx:47`, `src/lib/plugin-bootstrap.ts:188-241`.
- Chart: `src/modules/chart/ChartPanel.tsx`, `indicators.ts`, `drawings/{base,factory,renderers}.ts`, `src/store/{chart-drawings,chart-sync,symbols}.ts`, `types/drawings.ts`, `src/modules/chart/{volume-profile,ichimoku-cloud}-primitive.ts`, `src/modules/chart/api.ts`.
- Sidecar: `sidecar/app.py:138-185`, `sidecar/routers/*.py`, `sidecar/services/*.py`, `sidecar/{openbb_mcp_subprocess,sec_edgar_mcp_subprocess}/main.py`, `src-tauri/src/{openbb_mcp,sec_edgar_mcp,lib}.rs`.
- News bug: `sidecar/services/news_provider.py:57,112-159,193-238`, `sentiment.py:30`.
- Dev badge: `next.config.ts`, `src-tauri/tauri.conf.json:6-11`, `src/lib/sidecar-client.ts:42-50`.
- Plugins: `plugins/{example,openbb-mcp,tradesa-v2}/`, `plugins/brokers/*`, `types/{plugin,tradesa_v2,broker,workflow}.ts`.
- LOCKED (read-only reference): `types/plugin.ts`, `sidecar/services/{broker_base,kill_switch,audit_log}.py`, `sidecar/tests/test_safety_end_to_end.py`.

> **Stage-2 reminder:** when a ⚠️RAW-COORD test cannot be driven because the harness can't synthesize trusted events, record it as **UNTESTABLE-VIA-HARNESS**, not **FAILED** — and recommend native-event injection. A synthetic-event rejection is not evidence of a product defect.
