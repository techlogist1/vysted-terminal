# Vysted Terminal — Blueprint v1.0

**Status:** Locked, ready for Phase 0 execution
**Generated:** 2026-05-14
**Owner:** Lokavya (github.com/techlogist1)
**Repo (planned):** github.com/techlogist1/vysted-terminal
**Domain structure:** vysted.com (org) + terminal.vysted.com (product)
**License:** AGPL-3.0 + Commercial Dual License

---

## TL;DR

Vysted Terminal is an **open-source AI-native finance terminal** — Bloomberg-level coverage, TradingView-killer charting, JARVIS-style AI sandboxability, all in a desktop app that runs locally with bring-your-own-keys. Tradesa V2 is the first plugin proving the platform architecture.

**Product identity:** *Finance sandbox* — modular, plug-and-play, infinitely extensible by users and plugins.

**Positioning:** An open, extensible alternative to closed financial terminals — Bloomberg-level coverage and AI-native research, with a plugin architecture as the core differentiator.

**v1.0 scope:** ~38 modules, 12 AI agents, full plugin architecture, MCP server, node editor for workflow automation, backtest engine, Tradesa V2 plugin shipped.

**Launch budget: $0.** Upgrade path defined for when revenue/business interest justifies it.

---

## 1. Brand & Positioning

**Org name:** Vysted
**Product name:** Vysted Terminal (the flagship; future products plug under the org)
**Domain structure:**
- vysted.com — org/lab landing page
- terminal.vysted.com — Vysted Terminal product page + download

**Voice:** Research lab style (Tauric Research, OpenBB, Anthropic). Serious, technical credibility. Not startup-pitch energy. Not retail-app energy.

**Tagline candidates** (TBD — not v1.0 critical path):
- "Open-source AI toolkit for finance"
- "The finance sandbox"
- "Open-source intelligence terminal for traders, quants, and researchers"

**Positioning:** Professional-grade market tooling has long been gated behind closed terminals and five-figure subscriptions. Vysted Terminal opens that ground — Bloomberg-level data coverage, AI-native research and workflow automation, and a plugin architecture that lets users and third parties extend the platform — for everyone who doesn't need exclusive institutional feeds.

---

## 2. Locked Decisions Summary

| Decision | Locked |
|----------|--------|
| Product name | Vysted Terminal |
| Org name | Vysted |
| Domain | vysted.com + terminal.vysted.com |
| Stack (UI) | Tauri 2.x + Next.js 16 + TypeScript + Tailwind 4 + shadcn/ui |
| Stack (charts) | lightweight-charts + react-flow + Framer Motion + Zustand |
| Backend | Local Python sidecar (FastAPI on localhost) |
| Data layer | OpenBB ODP wrapped as runtime sidecar (~100 providers) |
| AI | BYOK for all major LLM providers + local Ollama + 12 pre-built agents + Custom Agent Builder |
| Plugin architecture | Full VystedPlugin contract; Tradesa V2 = plugin #1 |
| License | AGPL-3.0 + Commercial Dual License |
| OS targets | Windows + macOS + Linux at v1.0 |
| Distribution | GitHub Releases + Tauri auto-updater + SignPath.io (Win, free OSS) + ad-hoc + bypass docs (Mac at $0 launch) + AppImage (Linux) + Homebrew cask |
| Customization | Sandbox model — default layout + drag-drop + module toggles + workspace export/share (NO role-based presets) |
| MCP server | In v1.0 |
| Backtest engine | In v1.0 (Python sidecar) |
| Node editor | In v1.0 (react-flow) |
| Broker execution | Global broker support + execution in v1.0 — six brokers + ccxt crypto wrap, paper-mode default, shared safety layer (§6.5) |
| Web companion | Deferred to v2.0+ |
| Hosted backend | None — fully local, BYOK |

---

## 3. Architecture

### 3.1 Tech Stack (multi-language by design)

**Rust layer (Tauri 2.x core):**
- Desktop shell (windowing, system tray, OS integration)
- File system access
- Secure key storage (OS keychain integration on each platform)
- Auto-updater (built into Tauri 2.x)
- Code signing pipeline integration (SignPath for Win, ad-hoc for Mac)

**Python layer (sidecar via FastAPI on localhost):**
- OpenBB ODP wrapped — gives 100+ data providers (Polygon, FMP, FRED, Intrinio, Tiingo, ECB, FINRA, SEC, etc.)
- QuantLib via Python bindings (Black-Scholes, Binomial, Monte Carlo, VaR, Greeks, yield curves, duration/convexity, bond optimization)
- Backtest engine (vectorbt + backtrader patterns)
- AI agent orchestration (LangGraph)
- ccxt for unified crypto WebSockets (Bybit, Binance, Kraken, Coinbase)
- MCP server for external AI tool access

**TypeScript + React layer (Next.js 16 + React 19):**
- All UI rendering
- Lightweight-charts for financial charting
- react-flow for node editor
- Framer Motion for animations
- Zustand for state
- Tailwind + shadcn/ui for design system

**Communication:**
- Tauri commands for Rust ↔ JS (system access)
- HTTP localhost calls for JS ↔ Python sidecar (data + AI requests)
- WebSocket for real-time JS ↔ Python streaming
- MCP server (Python) for external AI tool integration

### 3.2 System Layers (visual)

```
┌─────────────────────────────────────────────────┐
│  UI Layer (Next.js + React + TS)                 │
│  Panels, charts, command bar, node editor       │
└───────────────┬─────────────────────────────────┘
                │ Tauri commands + HTTP localhost
┌───────────────▼─────────────────────────────────┐
│  Rust Layer (Tauri Core)                         │
│  Shell, FS, keychain, auto-update               │
└───────────────┬─────────────────────────────────┘
                │ Subprocess + HTTP
┌───────────────▼─────────────────────────────────┐
│  Python Sidecar (FastAPI on localhost)           │
│  - OpenBB ODP (100+ providers)                  │
│  - QuantLib (pricing/risk)                      │
│  - Backtest engine                              │
│  - AI agent orchestration (LangGraph)           │
│  - MCP server (external AI access)              │
└───────────────┬─────────────────────────────────┘
                │ Plugin SDK contracts
┌───────────────▼─────────────────────────────────┐
│  Plugins                                         │
│  - Tradesa V2 plugin (plugin #1)                │
│  - OpenBB ODP wrap plugin (data-only)           │
│  - Future plugins                               │
└─────────────────────────────────────────────────┘
```

### 3.3 Plugin Contract

Each plugin is a self-contained module that implements the `VystedPlugin` interface and declares which capabilities it contributes. Capability negotiation means panels/commands/agents that a plugin doesn't provide are gracefully omitted.

```typescript
export interface VystedPlugin {
  // Identity
  pluginId: string;              // "tradesa-v2", "openbb-odp", "forge-bot"
  pluginName: string;            // "Tradesa V2 (Bybit testnet)"
  pluginType: PluginType;        // "trading-bot" | "data-source" | "agent-collection" | "analytics"
  version: string;

  // Lifecycle
  initialize(config: PluginConfig): Promise<void>;
  shutdown(): Promise<void>;
  healthCheck(): Promise<HealthStatus>;

  // Capability declaration (graceful degradation)
  capabilities: {
    contributesData: boolean;
    contributesPanels: boolean;
    contributesCommands: boolean;
    contributesAgents: boolean;
    contributesNodes: boolean;
    supportsControlPlane: boolean;
  };

  // Data contribution
  getDataSources?(): DataSource[];

  // Panel contribution
  getPanels?(): PanelSpec[];

  // Command-bar contribution (slash commands)
  getCommands?(): CommandSpec[];

  // AI agent contribution
  getAgents?(): AgentSpec[];

  // Node editor contribution
  getNodes?(): NodeSpec[];

  // Real-time subscriptions (if supported)
  subscribe?(channel: string, callback: (event: any) => void): Unsubscribe;

  // Control plane (if supported)
  executeCommand?(commandId: string, args: any): Promise<CommandResult>;
}
```

**Tradesa V2 plugin** implements all six capabilities. **OpenBB ODP wrap plugin** implements only `contributesData`. Future plugins pick whichever capabilities fit.

### 3.4 AI Sandboxability Architecture

**Three layers of AI:**

**Layer 1: Per-panel context.** Every panel that benefits from AI has an inline AI sidebar/chat. The AI agent knows the panel's context (current ticker, current chart timeframe, current portfolio). User opens AAPL chart → AI knows AAPL is the context.

**Layer 2: Specialized workflow agents.** 12 pre-built agents shipped at v1.0:

| Agent | Role |
|-------|------|
| Warren Buffett | Value investing — business quality, margin of safety |
| Benjamin Graham | Deep value — Buffett's mentor framework |
| Peter Lynch | Growth at reasonable price (PEG) |
| Charlie Munger | Mental models, lattice thinking |
| Howard Marks | Cycles, risk-first |
| Seth Klarman | Contrarian value, distressed |
| Ray Dalio | Macro principles, all-weather |
| Stanley Druckenmiller | Macro + concentrated bets |
| George Soros | Reflexivity, macro speculation |
| AI Researcher | General research workflow (the equity-researcher pattern) |
| AI Portfolio Advisor | Portfolio analysis + rebalancing suggestions |
| Custom Agent Builder | User-defined agents (UI for creating new) |

**Layer 3: Multi-agent orchestration via node editor.** Users chain agents in visual workflows. Example: `AI Researcher pulls thesis → AI Strategy Critic critiques → if score > 7, alert via Telegram → otherwise log to journal`.

**Agent spec format (each agent is a config):**
```json
{
  "id": "buffett",
  "name": "Warren Buffett",
  "philosophy": "Value investing, margin of safety, business quality",
  "systemPrompt": "...",
  "tools": ["price_data", "fundamentals", "news", "ratios"],
  "defaultProvider": "anthropic",
  "icon": "buffett.svg"
}
```

Adding agents = adding JSON configs. Plugins can contribute agents. Custom Agent Builder UI lets users define their own without code.

---

## 4. Module Catalog (~38 modules in v1.0)

### Foundation (8)
1. Tauri 2.x desktop shell (Win/Mac/Linux)
2. Next.js 16 frontend skeleton
3. Tailwind + shadcn/ui design system (Vysted aesthetic: charcoal + warm amber + sage + serif-meets-monospace typography)
4. Command bar with slash commands (cmd+K)
5. Multi-window / multi-tab layout
6. Zustand state management
7. Theming engine (dark default + light option + future custom themes)
8. Python sidecar bootstrap (FastAPI on localhost, auto-managed by Tauri)

### Plugin Architecture (7)
9. VystedPlugin TypeScript interface
10. Plugin registry + manifest format
11. Plugin lifecycle management (init / shutdown / health)
12. Panel-slot contribution system
13. Command-bar contribution system
14. Agent-capability contribution system
15. Node-spec contribution system

### Data Layer (5)
16. OpenBB ODP wrap (bundled Python sidecar) — 100+ providers
17. ccxt unified crypto WebSocket (Bybit, Binance, Kraken, Coinbase)
18. yfinance + alpha_vantage fallbacks (no API key needed for basic use)
19. News intelligence (RSS + NewsAPI + AI sentiment scoring)
20. Macro / economic data (FRED + ECB + IMF + World Bank via ODP)

### Charting & Analysis (6)
21. Lightweight-charts integration (multi-pane sync)
22. 50+ technical indicators (RSI, MACD, MA/EMA/SMA, Bollinger, Volume Profile, ADX, Stochastic, ATR, OBV, MFI, Ichimoku, Keltner, etc.)
23. 10+ drawing tools (trendlines, channels, Fib retracements, harmonic patterns, support/resistance)
24. Multi-chart sync (linked timeframes across symbols)
25. Comparison overlays (peer comparison on same chart)
26. Volume profile + market profile

### Portfolio & Risk (3)
27. Position tracking + P&L attribution (local SQLite)
28. Risk analytics (Sharpe, Sortino, Calmar, VaR, Beta, max drawdown, correlation matrix)
29. Paper trading sandbox engine (event-driven simulation)

### Research (4)
30. Equity overview panel (price + ratios + statements + analyst ratings in one view)
31. SEC filings reader (10-K, 10-Q, 8-K, Form 4, via OpenBB SEC provider)
32. Earnings calendar
33. Analyst ratings aggregator

### AI / Automation (5)
34. Multi-LLM chat sidebar (OpenAI / Anthropic / DeepSeek / Groq / Gemini / xAI / Ollama)
35. 12 pre-built agents (config-driven, listed in §3.4)
36. Custom Agent Builder UI (define agent without code)
37. Node editor for workflow automation (react-flow based)
38. Backtest engine (Python sidecar, event-driven, walk-forward support, AI Strategy Critic integration)

### Customization Layer (3, baked into core)
- License gate UI (AGPL/commercial choice on first launch)
- Module toggle UI in settings (every module enable/disable)
- Workspace save/load/export/import (`.vysted-workspace` JSON files)

### Broker & Trading Plugins

Execution is a v1.0 capability, not a deferral. Each broker is a **separate plugin** implementing the existing `VystedPlugin` contract — no contract changes (data via `getDataSources`, panels via `getPanels`, order actions via `executeCommand`). Every broker plugin routes execution through the shared safety layer in §6.5.

**Tradesa V2 plugin** (one plugin, multi-panel) — still the proof-of-platform exercise, implementing all six plugin capabilities:
- 9-12 panels (decisions feed, open positions, P&L chart, trade history, watcher activity, sentinel/health, alerts, LLM cost, settings drift, reflection stream)
- Real-time WebSocket connection to the Tradesa bot
- Crypto execution via Bybit testnet, wrapped in the §6.5 safety layer
- Optional control plane (kill switch trigger, manual position close)
- Tradesa-specific agents (Decision Reviewer, Reflection Analyst) and node-editor nodes (e.g., "Wait for Tradesa decision")

**Broker execution plugins** (v1.0) — six brokers plus a ccxt crypto execution wrap, seven broker integrations in total, each free or near-free for retail:

| Plugin | Region | API cost | Python SDK | Notes |
|--------|--------|----------|------------|-------|
| Dhan | India | Free | `dhanhq` (MIT, v2.1.0+) | Orders, holdings, 200-level market depth, WebSocket; built-in static-IP management |
| Angel One SmartAPI | India | Free, incl. historical data | `smartapi-python` | REST + WebSocket; no static-IP requirement |
| Zerodha Kite Connect | India | Personal API free for execution + account data; Connect API ₹500/mo (~$6 USD) adds real-time + historical data | `kiteconnect` | **Static IP required for order placement since 1 April 2025** — SEBI/NSE algo-trading rule, not a Zerodha policy; up to 2 static IPs per account; data/holdings/positions endpoints unaffected |
| Alpaca | US / global | Free Basic trading (commission-free US equities/options/crypto); paid Algo Trader Plus for full market data; paper trading free | `alpaca-py` | Use `alpaca-py` — not the deprecated `alpaca-trade-api` |
| Interactive Brokers | Global, multi-asset | Free, account-based | `ib_async` (v2.1.0) | Use `ib_async` (github.com/ib-api-reloaded/ib_async) — not the discontinued `ib_insync`; requires TWS or IB Gateway running locally |
| OANDA v20 | Forex | Free with an fxTrade account (demo or live) | `oandapyV20` (community) | No API cost beyond holding the brokerage account |
| Crypto (ccxt) | Global | Per-exchange | `ccxt` | Execution wrap over the Phase 1 ccxt data layer — same §6.5 safety layer as every other broker plugin |

### Infrastructure (5, not user-facing)
- MCP server for external AI tool access
- GitHub Releases pipeline with Tauri auto-update
- Code signing pipeline (SignPath integration for Win, ad-hoc for Mac)
- CLA gate on PRs (so dual-license stays clean)
- Opt-in anonymous telemetry (basic crash + usage; respects privacy posture)

---

## 5. Sandbox Customization Layer

**No role-based presets.** Users get one sensible default layout on first launch and customize from there.

### 5.1 Default first-launch layout (4-6 panels)
- Main chart (default: SPY) — 50% of screen
- Watchlist (pre-loaded: SPY, QQQ, BTC, ETH, NVDA, AAPL)
- News feed (filtered to watchlist tickers)
- AI chat sidebar (with welcome message + suggested first commands)
- Portfolio panel (empty until user adds positions)
- Optional: Tradesa V2 plugin panel if connected

### 5.2 Customization primitives
- Drag-drop panel layout (resize, hide, pop-out to second window)
- Tab groups (multiple panel sets in one window)
- Named workspaces (save layout, switch between them)
- Workspace export/import as `.vysted-workspace` JSON files
- Module enable/disable in settings (disabled modules don't load, don't appear in command bar)
- Command bar (cmd+K) for discovery without UI clutter
- Module-specific settings (e.g., chart timeframe defaults, color schemes per module)

### 5.3 Future: workspace sharing (v2.0)
- Community workspace gallery
- Import from GitHub gist URL
- Share via QR code / link

---

## 6. Distribution & Licensing

### 6.1 License

**AGPL-3.0 (default) + Commercial Dual License (paid)**

- `LICENSE` file in repo: full AGPL-3.0 text
- `COMMERCIAL_LICENSE.md`: commercial terms + pricing + contact (placeholder: commercial@vysted.com)
- `README.md` explicit: "Free for personal, academic, and open-source use under AGPL-3.0. Commercial use requires a paid license."
- CLA required on all contributions (so Lokavya retains right to dual-license contributed code)

**Commercial license pricing (TBD, finalized at v1.0 launch):**
- Solo professional: TBD
- Small fund (1-5 seats): TBD
- Mid-size institution: TBD
- Enterprise (negotiable): TBD

### 6.2 Distribution Pipeline

```
push git tag v1.0.0
  ↓
GitHub Actions builds Tauri bundles:
  ├── Linux: .AppImage + .deb (unsigned, fine)
  ├── macOS: .dmg ad-hoc signed (first-launch bypass at $0 launch)
  ├── Windows: .msi signed by SignPath.io (free OSS tier)
  ↓
Attached to GitHub Release v1.0.0
  ↓
Tauri auto-updater on existing installs pulls update
  ↓
terminal.vysted.com/download serves "Download for [your OS]" via GitHub Releases API
  ↓
Homebrew cask updated separately (PR to homebrew-cask)
```

**v1.0 launch budget: $0.**

**When revenue/business interest arrives:**
- $99/year Apple Developer Program → fully notarized macOS builds, zero install friction
- Eventually: Microsoft Store / Mac App Store submissions

### 6.3 First-launch Mac instructions

Until paid Apple Developer cert: `terminal.vysted.com/install/mac` shows:
- Screenshot of the unsigned-app warning
- Instructions: "Right-click Vysted Terminal in Applications → Open → Open again to confirm"
- OR: "System Settings → Privacy & Security → Click 'Open Anyway' next to Vysted Terminal"
- ~30 second one-time bypass per Mac

### 6.4 Execution liability

From v1.0, Vysted Terminal places live orders against real brokerage accounts. Order placement carries real financial risk — market, execution, and operational risk all sit with the user, not the software.

- **Vysted Terminal is a tool, not financial advice.** Nothing the terminal displays, computes, or generates — including AI-agent output — is a recommendation to buy, sell, or hold any instrument. Trading decisions and their consequences are the user's alone.
- **No warranty for trading losses.** The AGPL-3.0 (§15 Disclaimer of Warranty, §16 Limitation of Liability) already disclaims all warranties and all liability for the software. For the avoidance of doubt, that disclaimer extends explicitly to trading and financial losses — including losses arising from defects, data errors, latency, failed or duplicated orders, or AI-agent behaviour. The software is provided "as is."
- **The user owns the broker relationship.** Each broker's own terms, margin rules, and regulatory obligations continue to apply. Vysted Terminal is not a broker, an introducing broker, or an investment adviser.

`COMMERCIAL_LICENSE.md` mirrors this with an explicit no-warranty-for-trading-losses clause, so commercial licensees carry the same disclaimer in their own contract. The operational safety design that backs these commitments is §6.5.

### 6.5 Safety Architecture for Execution

Live order placement is gated behind a fixed set of safeguards. These are non-negotiable design constraints for every broker plugin — Phase 5 implements them, and no broker plugin ships without them.

**1. Paper mode is the default.** Every broker plugin starts in paper-trading mode. Live trading is opt-in per broker, toggled by the user, and the first time a plugin is switched to live it shows a dedicated disclaimer dialog that must be explicitly acknowledged. There is no global "enable everything" shortcut — the decision is made one broker at a time.

**2. Every order is confirmed.** No order — paper or live — is placed without a confirmation dialog showing the full order: symbol, quantity, side, order type, limit price, estimated value, broker, and account ID. There are no one-click trades anywhere in the app, in any panel, for any broker.

**3. Position-size limits are configurable per plugin.** Each broker plugin carries soft default caps — maximum order value, maximum percentage of account, and maximum position size per symbol. The user can raise a limit, but only through an explicit confirmation step; the defaults are conservative on purpose.

**4. Every order is audit-logged.** Each order — whether placed manually or initiated by an AI agent — is written to a local SQLite audit log: timestamp, broker, full request payload, broker response, and outcome. The log is exportable and survives app restarts. It is the user's own record of what the terminal did on their behalf.

**5. There is a global kill switch.** A prominent, always-visible "Halt All Trading" control in the main UI immediately disables order placement across every broker plugin at once. It is designed to be found and used under stress, without hunting through settings.

**6. AI-initiated orders carry an extra gate.** When a node-editor workflow or an AI agent attempts to place an order, the confirmation dialog opens **defaulted to declined** and names the agent: "AI agent `<name>` is requesting this order." An optional auto-approve mode exists but is off by default and must be enabled explicitly, per agent. The terminal never lets an AI place an order the user did not see.

**7. Plugins can be marked read-only.** Even with live trading globally enabled, any individual broker plugin can be set to view-only — useful, for example, for an Interactive Brokers institutional account the user wants to research from but never execute against. Read-only is enforced at the plugin boundary, not just in the UI.

**8. Liability is disclosed at every entry point.** The disclaimers in §6.4 are surfaced to the user at four touchpoints, not buried in a file:
- **AGPL-3.0 `LICENSE`** — §15–16 disclaim all warranty and liability; §6.4 records that this extends explicitly to trading losses. (The AGPL text itself is verbatim and unmodified.)
- **`COMMERCIAL_LICENSE.md`** — an explicit no-warranty-for-trading-losses clause, so commercial licensees carry the same disclaimer.
- **First-launch app TOS dialog** — a one-time acknowledgment the user must accept before *any* broker plugin can be enabled at all.
- **Per-broker first-connect dialog** — a broker-specific terms-and-conditions reminder shown the first time the user connects each broker.

Together these make the execution path conservative by construction: paper by default, confirmed every time, capped, logged, haltable, extra-gated for AI, and disclosed up front.

---

## 7. Phase Breakdown (Phase 0 → v1.0 Launch)

All phases ship as part of v1.0 — no MVP, no Phase 2 deferrals. Phases are **Claude Code execution windows**, fresh window per phase. Each window: Opus 4.7 + xhigh + plan-mode + AGENT_TEAMS=1.

### Phase 0 — Foundation
- Repo scaffold (github.com/techlogist1/vysted-terminal)
- Tauri 2.x + Next.js 14 + TypeScript bootstrap
- Tailwind + shadcn/ui + Vysted design tokens
- Python sidecar bootstrap (FastAPI on localhost, lifecycle managed by Tauri)
- Plugin architecture types defined (full `VystedPlugin` TypeScript interface)
- ONE mock panel: "Welcome to Vysted Terminal" with placeholder content
- Command bar skeleton (cmd+K opens, slash command list empty)
- CI: GitHub Actions for build (Win/Mac/Linux) + lint + test
- `LICENSE` + `COMMERCIAL_LICENSE.md` + CLA bot setup
- `CLAUDE.md` at repo root (project context, stack, standards, constraints)
- `terminal.vysted.com` landing page (Vercel deploy, "Coming soon" + GitHub link)

**Phase 0 success criteria:**
- `pnpm tauri dev` opens window with mock panel
- Design tokens visible (Vysted aesthetic)
- Plugin interface compiles without errors
- CI green for all OS builds
- Tag v0.1.0 pushed

### Phase 1 — Data Layer + Core Panels
- OpenBB ODP integration in Python sidecar
- ccxt integration (crypto WebSockets)
- yfinance fallback
- 5 core panels with real data:
  1. Chart panel (lightweight-charts + 20 indicators)
  2. Watchlist panel
  3. News feed panel (with sentiment scoring)
  4. Portfolio panel (read positions from local SQLite)
  5. Equity overview panel (fundamentals + ratios + statements)
- Module toggle UI in settings
- Workspace save/load (local only at this phase)

### Phase 2 — Charting + Plugin Architecture

**Shipped in v0.3.0 (2026-05-15).**

- 30 more technical indicators (50 total) ✓
- 10 drawing tools ✓ (workspace-persisted)
- Multi-chart sync ✓ (opt-in crosshair / visible-range / symbol toggles)
- Comparison overlays ✓ (with normalize toggle)
- Plugin registry + manifest loader (live in app) ✓ (bundled-import loader,
  Phase 2 scope; filesystem-installed/marketplace deferred to v1.0+)
- OpenBB ODP wrap plugin (data-only plugin, proves data-plugin pattern) ✓
  (Tier 2 separate-process pattern after `openbb-core` strict pins ruled out
  in-process bundling; +43 MB binary delta on Windows)

### Phase 3 — AI Layer

**Shipped in v0.4.0 (2026-05-16).**

- Multi-LLM provider integration ✓ (OpenAI, Anthropic, DeepSeek, Groq,
  Gemini, xAI, Ollama — 5 native adapters + 2 OpenAI-compatible via
  `base_url` override; SDK pins verified current on ship date)
- 12 pre-built agents shipped as configs ✓ (11 §3.4-named + AI Strategy
  Critic per the §3.4-vs-§4 Tier-3 roster resolution; the 12th slot is
  forward-compatible with the Phase-4 backtest engine)
- Custom Agent Builder UI ✓ (Module 36, separate from the 12-agent
  count; sidecar SQLite-backed; `custom:`-prefix on user-defined ids)
- Per-panel AI context wiring ✓ (`usePanelContextBus` Zustand bus +
  publishers in all five Phase-1 panels; chat sidebar subscribes via
  `selectSnapshot`)
- Vysted MCP server ✓ (FastMCP 3.2.4 mounted at `/mcp` over
  Streamable-HTTP transport; 9 tools — 5 data + 2 agent + 2 workspace;
  external MCP clients via `mcp-remote` bridge for Claude Desktop or
  `claude mcp add` for Claude Code)
- MCP client + openbb-mcp-server ✓ (Phase-2 OpenBB Tier-2 plugin
  retired; replaced by `plugins/openbb-mcp/` consuming
  `openbb-mcp-server` 1.4.0 spawned via Tauri Rust `Command::new` —
  the architectural fix for the Phase-2 Windows `subprocess.Popen`
  deadlock; data surface preserved end-to-end)

### Phase 4 — Sandbox: Node Editor + Backtest

**Shipped in v0.5.0 (2026-05-16) as part of the Phase 4 + Phase 5 mega-sprint.**

- Node editor ✓ (`@xyflow/react@12.10.2` — npm rebrand of `reactflow`;
  canvas + drag-drop palette + edge connect + run overlay)
- Workflow execution engine ✓ (custom asyncio engine in
  `sidecar/services/workflow_engine.py`; Kahn's-algorithm cycle detection;
  parallel waves via `asyncio.gather`; SSE event stream)
- Backtest engine ✓ (custom event-driven engine in
  `sidecar/services/backtest_engine.py`; walk-forward; Sharpe / Sortino /
  Calmar / win-rate; NOT vectorbt/backtrader at runtime per Tier-3
  bundle-size + maintenance reasoning)
- AI Strategy Critic agent ✓ (Phase-3-reserved tools list `["backtest_summary",
  "price_data", "fundamentals"]` lit up end-to-end; agent runtime extended
  with multi-round `tool_use` dispatch loop; Use Case 2 round-trip
  captured: mean_reversion SPY 2024-2025, 18 trades, Sharpe -0.16,
  win-rate 61.1%)
- Workspace export/import (Phase-1 already shipped; no v0.5.0 change)

### Phase 5 — Broker & Trading Plugins

**Shipped in v0.5.0 (2026-05-16) as part of the Phase 4 + Phase 5 mega-sprint.**

- **Shared execution safety layer** ✓ (BLUEPRINT §6.5 8-point dedicated
  audit suite passes 9/9; max kill-switch ack 20.08 ms vs 2000 ms budget;
  SQLite triggers raise on UPDATE/DELETE of `audit_orders`; AI-order
  gate strictly enforced — Tier-3 tightening removes BLUEPRINT's
  "auto-approve mode" mention; live execution capability ENABLED).
- **Tradesa V2 full plugin** — DEFERRED to v0.5.1 or v0.6.0 per Tier-3
  operator-brief de-scoping. Foundation contracts (kill switch + audit
  log + `executeCommand` control plane) are in place; Tradesa V2 becomes
  plug-in work, not contract work.
- **Global broker execution plugins** ✓ — Dhan (`dhanhq 2.1.0`), Angel One
  SmartAPI (`smartapi-python 1.5.5`), Zerodha Kite Connect (`kiteconnect
  5.2.0` with SEBI/NSE static-IP UX path live), Alpaca (`alpaca-py
  0.42.0`), Interactive Brokers (`ib_async 2.1.0`, requires TWS/IB
  Gateway on `127.0.0.1:7497`), OANDA v20 (`oandapyV20 0.7.2`), ccxt
  unified crypto execution (Bybit, Binance, Kraken, Coinbase) — each a
  separate plugin on the locked `VystedPlugin` contract, routed through
  the shared safety layer. All 7 broker SDKs ship in main sidecar
  (F9-measured 67.4 MB main bundle; no subprocess split needed).

Original Phase 5 was the Tradesa V2 plugin alone (~3-5 days); v0.5.0
absorbed broker integration + safety layer + node editor + workflow +
backtest under one tag. The architectural rationale is in `CHANGELOG.md`
v0.5.0 and `docs/superpowers/plans/2026-05-16-phase-4-5-mega-sprint.md`.

### Phase 6 — Macro + Research + QuantLib

**Shipped in v0.6.0 (2026-05-16).** Plan at
`docs/superpowers/plans/2026-05-16-phase-6-macro-research-quantlib.md`;
handoff at `docs/PHASE_6_HANDOFF.md`.

- Macro/economic data panels ✓ — FRED (via `fredapi`), ECB (via
  `ecbdata`), IMF (via `sdmx1`), World Bank (via `wbgapi`); all
  in-process after the M Tier-3 pivot from the originally-planned
  `fred-mcp-server` subprocess (Node.js package).
- SEC filings reader ✓ — `sec-edgar-mcp` subprocess (Tauri Rust spawn
  pattern, precedent v0.4.0 openbb_mcp.rs) covers 10-K / 10-Q / 8-K /
  DEF 14A + insider Forms 3/4/5 + XBRL-precise financials with string
  precision preservation.
- Earnings calendar ✓ — upcoming + history + surprises + estimates with
  consensus mean / high / low / dispersion stddev approximation.
- Analyst ratings aggregator ✓ — ratings history + price-target
  timeline + per-firm individual analyst tracks with five-bucket
  AnalystAction normalisation.
- QuantLib pricing modules ✓ — Black-Scholes / Cox-Ross-Rubinstein
  binomial / Monte Carlo options + Greeks + fixed-rate bonds (duration,
  modified duration, convexity) + PiecewiseLinearZero yield-curve
  bootstrapping. In-process via `QuantLib==1.42.1` (Tier-3: quality
  posture removed bundle-size constraint).
- Screener / scanner — backend shipped (Teammate Sc); frontend deferred
  to v0.6.1 lead-completion after Sc's agent terminated mid-execution
  on a socket-closed error.

16 new agent tools registered + 9 new workflow node types — Use Cases 4
(academic research) and 5 (macro thesis watcher) materially more capable.

### Phase 6.5 — Tradesa V2 Wrapper Plugin

**In progress (v0.6.5, 2026-05-17).** Plan at
`docs/superpowers/plans/2026-05-16-tradesa-v2-wrapper-plugin.md`;
handoff lands at `docs/PHASE_6.5_HANDOFF.md` with the release commit.

First-party wrapper plugin for Lokavya's existing Tradesa V2 multi-
agent LLM crypto perp trading bot (techlogist1/tradesa). Operator
brief slotted v0.6.5 between Phase 6 and Phase 7 launch ops so the
v1.0 narrative includes "first real third-party-shaped trading-system
plugin proving the platform."

- **READ-ONLY by operator decision.** No commands flow from Vysted to
  the bot in v0.6.5 (the bot itself is in an unstable state right now);
  write capability is v0.6.6+ scope. Three defense-in-depth layers
  enforce this: provider has no write methods (audit-tested), router
  has no non-GET routes (audit-tested), plugin's
  `supportsControlPlane=false` (contract-level gate).
- **Supabase passthrough.** Tradesa V2's operator interface is Telegram-
  only — no REST API. The wrapper reads the bot's existing Supabase
  remote-sync project via `sidecar/services/tradesa_v2_provider.py`
  using a service-role key in the OS keychain. RLS is deferred Tradesa-
  side to its v0.1.7.0 milestone; the wrapper API surface is unchanged
  when RLS lands.
- **7 panels** surfacing the bot's key state: Live Positions, Trade
  History & P&L, Brain Decisions, Sentinel, Health, Settings & Drift,
  Self-Tuning / Discovery / Reflection — all with shared
  `<TradesaBotStatusStrip />` showing mode + kill-switch + heartbeat
  age.
- **Generic wrapper pattern.** `docs/PLUGIN_DEVELOPMENT.md` documents
  the layout (`connection.ts` implements `TradingBotReadAdapter`;
  companion `panels.ts` exports the component map; bootstrap glue in
  `src/lib/plugin-bootstrap.ts::PLUGIN_COMPANIONS` wires it up).
  TauricResearch and future trading-system plugins mirror the same
  shape — zero contract change required.
- **Polling, not Realtime** (Tier-3 scope decision). Supabase Realtime
  proxy deferred to v0.6.6 to avoid the asyncio-task lifecycle
  complexity. Per-panel polling cadences (10s positions / 30s decisions
  / 60s settings) deliver equivalent "is the bot alive" UX.

### Phase 7 — Polish + Distribution + Launch
- SignPath.io setup for Windows code signing (free OSS application)
- Tauri auto-updater wired to GitHub Releases
- Homebrew cask submission
- terminal.vysted.com full landing page (download button, screenshots, docs)
- README polish + getting-started docs
- Tag v1.0.0
- Launch announcement

---

## 8. Success Criteria (v1.0 launch)

- [ ] User downloads from terminal.vysted.com, installs on their OS, opens app in <30 seconds (Linux/Win), <90 seconds for Mac with bypass step
- [ ] All 38 modules functional and accessible
- [ ] 12 AI agents work with at least 3 LLM providers tested end-to-end
- [ ] Backtest engine runs a 60-day strategy in <30 seconds on standard hardware
- [ ] Tradesa V2 plugin connects to user's Supabase via the read-only wrapper, shows decisions via per-panel polling (v0.6.5 shipped scope; Realtime SSE proxy + write capability deferred to v0.6.6+)
- [ ] Workspace export/import round-trips correctly across platforms
- [ ] MCP server responds to external Claude/GPT queries
- [ ] CI green for all OS builds
- [ ] `LICENSE` + `COMMERCIAL_LICENSE.md` + CLA in place
- [ ] terminal.vysted.com live with download links
- [ ] At least one external user successfully installs without help (validate via Discord or beta program)

---

## 9. Deferred (v1.1 / v1.5 / v2.0)

**v1.1 (post-launch patches, weeks 1-4 after launch):**
- Additional indicators (50 → 100)
- More AI agents (12 → 20+)
- Additional broker plugins — Upstox, Fyers, Samco, Shoonya, Tradier, DEGIRO, MT5 bridge — community-pluggable on the existing plugin contract
- Plugin marketplace UI (locally browse, no online catalog yet)

**v1.5 (months 2-6 after launch):**
- More macro data (more countries, more series)
- Advanced backtest features (Monte Carlo, walk-forward optimization, parameter sweeps)
- Mobile companion app (read-only, view watchlists + alerts) — separate React Native codebase
- Web companion (lightweight browser version for trial)
- Additional plugin contracts (more types of plugins)

**v2.0 (year 1+):**
- Online plugin marketplace + community workspace gallery
- Workspace sharing community
- Hosted version (subscription SaaS option) — requires hosted backend, decided when revenue justifies it
- Multi-bot plugins (Forge Bot, etc.)
- Alternative data (maritime tracking, satellite, geopolitical)
- Mac App Store / Microsoft Store submissions

---

## 10. Reference: Goated Use Cases

### Use Case 1: Solo Founder's Quant Day (Lokavya)
Morning open → Tradesa V2 overnight check (READ-ONLY observation surface as of v0.6.5 — 7 panels surfacing positions, trade history, decisions, sentinel, health, settings drift, meta-agents) → AI Risk Analyst review → backtest new strategy → _(v0.6.6+ target)_ push config to bot via Tradesa plugin control plane.

### Use Case 2: Research Workflow (the equity researcher's story)
Cmd+K → "Research XYZ" → AI Researcher pulls everything → chart + news in adjacent panels → backtest dividend strategy → save workspace.

### Use Case 3: Earnings Playbook
Build node-editor workflow → AI generates thesis per earnings name → alert on entry trigger → desktop notification → review thesis → trade externally.

### Use Case 4: Academic Researcher
Custom AI agent fine-tuned to research domain → workflow pulls SEC + sentiment → outputs to chart → workspace becomes reproducible dissertation methodology.

### Use Case 5: Macro Thesis Watcher (Dalio-style)
Workspace with yield curves + central bank tracker + commodity dashboard → AI Macro Researcher monitors news → notifications on thesis-confirming events.

### Use Case 6: Plugin Ecosystem (year 2+)
Indie trading bot devs implement Vysted's plugin contract → their users get Vysted Terminal as free dashboard → Vysted becomes standard UX layer for open-source trading infrastructure.

### Use Case 7: Multi-Broker Portfolio Aggregation
A user holds positions across Zerodha Kite, Dhan, and Alpaca. One Vysted workspace pulls all three broker plugins into a unified view: aggregate P&L up top, per-broker drilldown panels below, and cross-broker risk metrics — concentration, correlation, total exposure — computed across the combined book. Execution stays per-broker and behind every §6.5 safeguard; the aggregation is read-side only.

---

## Appendix A: Stack Verification

The Tauri + Next.js stack is proven viable for this scope — **Fincept Terminal v3 used the exact same stack** (Tauri + React + TypeScript + Python sidecar + Rust) and delivered comparable feature coverage before pivoting to native C++ for v4. Going native C++ would require a paid team — for solo dev with Claude Code, multi-language sidecars (Rust core + Python compute + TS UI) are the optimal choice.

## Appendix B: Reference Repos (clone for inspiration, do NOT copy code)

- **github.com/Fincept-Corporation/FinceptTerminal** — AGPL-3.0 + Commercial License; reference for feature breadth, agent design, node editor
- **github.com/OpenBB-finance/OpenBB** — AGPL-3.0; reference for data layer architecture, provider abstraction patterns, MCP server design
- **github.com/TauricResearch/TradingAgents** — open source; reference for multi-agent orchestration patterns, LangGraph usage

**Critical reminder:** Fincept's dual-license explicitly prohibits commercial use without paid license, AND prohibits forks that strip their APIs. We do NOT copy their code. We READ their code as research material and WRITE our own implementations. Features aren't copyrightable; specific code is. We're safe pattern-matching what they ship.

## Appendix C: Next Steps After Blueprint Lock

1. **Phase 0 megaprompt produced** (next conversation turn) — paste-ready triple-backtick block for Claude Code
2. **Fresh Claude Code window opened**: Opus 4.7 + xhigh + plan-mode + AGENT_TEAMS=1
3. **Phase 0 paste-and-execute** — operator pastes megaprompt into Claude Code
4. **Operator reviews Phase 0 output**, gates Phase 1
5. **Phase 1 megaprompt produced** in next Claude.ai chat turn
6. Repeat per phase until v1.0 ships

## Appendix D: Working Style Reminders (for Phase prompts)

- **bash_tool for all VPS/server operations** — but Vysted Terminal doesn't have a VPS; this only applies if user has Tradesa V2 plugin enabled
- **Goal+constraint level prompts** to Claude Code (not spoon-fed implementation)
- **Worktree discipline non-negotiable** — teammates push to `worktree-agent-{name}` branches only, lead reviews diff before merging to main
- **Ship-cycle rule** — before closing Claude Code window after a ship, ask "any hot patches or polish items needed first?"
- **Risk-critical files** (plugin contract types, license boilerplate, build pipeline) → Opus 4.7 lead, never delegate to Sonnet teammates without lead review
- **CLAUDE.md** at Vysted Terminal repo root must cover: project context, stack, coding standards, constraints, plugin contract requirements

---

*End of blueprint. Locked. Phase 0 megaprompt produced next.*
