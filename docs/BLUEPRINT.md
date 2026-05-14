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

**Internal thesis (NOT marketing):** What Claude is doing to professional tools across domains, Vysted does to Bloomberg/TradingView in finance.

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

**Internal thesis (for engineering team mental model only):** Claude is invading every professional domain — code (Claude Code), legal, design, video. Vysted does this for finance. Vysted Terminal kills Bloomberg's $27K/year moat for everyone who doesn't need exclusive institutional feeds.

---

## 2. Locked Decisions Summary

| Decision | Locked |
|----------|--------|
| Product name | Vysted Terminal |
| Org name | Vysted |
| Domain | vysted.com + terminal.vysted.com |
| Stack (UI) | Tauri 2.x + Next.js 14 + TypeScript + Tailwind + shadcn/ui |
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

**TypeScript + React layer (Next.js 14):**
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
| AI Researcher | General research workflow (Raghav-PFC pattern) |
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
2. Next.js 14 frontend skeleton
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

### Tradesa V2 Plugin (one plugin, multi-panel)
Implements all six plugin capabilities:
- 9-12 panels (decisions feed, open positions, P&L chart, trade history, watcher activity, sentinel/health, alerts, LLM cost, settings drift, reflection stream)
- Real-time WebSocket connection to Tradesa bot
- Optional control plane (kill switch trigger, manual position close)
- Tradesa-specific agents (Decision Reviewer, Reflection Analyst)
- Tradesa-specific node-editor nodes (e.g., "Wait for Tradesa decision")

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

**Commercial license pricing (suggested starting point — adjust per buyer):**
- Solo professional: $99/year
- Small fund (1-5 seats): $499/year
- Mid-size institution: $2,000-5,000/year
- Enterprise (negotiable): custom

Compare: Fincept commercial license is $10,200/year. Lokavya can start lower and raise as value compounds.

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
- 30 more technical indicators (50 total)
- 10 drawing tools
- Multi-chart sync
- Comparison overlays
- Plugin registry + manifest loader (live in app)
- OpenBB ODP wrap plugin (data-only plugin, proves data-plugin pattern)

### Phase 3 — AI Layer
- Multi-LLM provider integration (OpenAI, Anthropic, DeepSeek, Groq, Gemini, xAI, Ollama)
- 12 pre-built agents shipped as configs
- Custom Agent Builder UI
- Per-panel AI context wiring
- MCP server (FastAPI in sidecar exposing Vysted's data + capabilities to external AI tools)

### Phase 4 — Sandbox: Node Editor + Backtest
- Node editor (react-flow based)
- Workflow execution engine (Python sidecar coordinates node graph)
- Backtest engine (event-driven, walk-forward support, vectorbt+backtrader patterns)
- AI Strategy Critic agent (analyzes backtest results)
- Workspace export/import as `.vysted-workspace` files

### Phase 5 — Tradesa V2 Plugin
- Tradesa V2 full plugin implementation
- 9-12 panels for Tradesa observability
- Real-time WebSocket to Tradesa bot
- Optional control plane (kill switch, manual position close)
- Settings drift detection
- LLM cost tracking
- Tradesa-specific agents + nodes

### Phase 6 — Macro + Research + QuantLib
- Macro/economic data panels (FRED, ECB, IMF, World Bank)
- SEC filings reader
- Earnings calendar
- Analyst ratings aggregator
- QuantLib pricing modules (Black-Scholes, Binomial, Monte Carlo, VaR, Greeks, yield curves)
- Screener / scanner panel

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
- [ ] Tradesa V2 plugin connects to user's Supabase + bot WebSocket, shows real-time decisions
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
- Broker integration scaffold (read-only at first)
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
- Real broker integrations (16+ brokers like Fincept)
- Multi-bot plugins (Forge Bot, Kite real-trading, etc.)
- Alternative data (maritime tracking, satellite, geopolitical)
- Mac App Store / Microsoft Store submissions

---

## 10. Reference: Goated Use Cases

### Use Case 1: Solo Founder's Quant Day (Lokavya)
Morning open → Tradesa V2 overnight check → AI Risk Analyst review → backtest new strategy → push config to bot via Tradesa plugin control plane.

### Use Case 2: Research Workflow (the Raghav-PFC story)
Cmd+K → "Research PFC" → AI Researcher pulls everything → chart + news in adjacent panels → backtest dividend strategy → save workspace.

### Use Case 3: Earnings Playbook
Build node-editor workflow → AI generates thesis per earnings name → alert on entry trigger → desktop notification → review thesis → trade externally.

### Use Case 4: Academic Researcher
Custom AI agent fine-tuned to research domain → workflow pulls SEC + sentiment → outputs to chart → workspace becomes reproducible dissertation methodology.

### Use Case 5: Macro Thesis Watcher (Dalio-style)
Workspace with yield curves + central bank tracker + commodity dashboard → AI Macro Researcher monitors news → notifications on thesis-confirming events.

### Use Case 6: Plugin Ecosystem (year 2+)
Indie trading bot devs implement Vysted's plugin contract → their users get Vysted Terminal as free dashboard → Vysted becomes standard UX layer for open-source trading infrastructure.

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
