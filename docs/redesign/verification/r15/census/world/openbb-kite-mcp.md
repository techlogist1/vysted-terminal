# R15 Census — World Sweep: OpenBB, Kite MCP, and the finance-MCP landscape

**Sweep:** `WORLD-OBB` (world/research)
**Date of research:** 2026-09-19
**Model:** `claude-opus-5[1m]`
**Scope:** OpenBB Workspace + its agents/copilot + MCP story; Zerodha Kite MCP (tools, read-only vs orders, how people actually use it); other finance MCP servers and broker APIs an Indian BYOK desktop agent could ride.
**Method:** live web (WebSearch + WebFetch). Every claim below carries a URL and a quote or a concretely-described observation. Where a site blocked fetching or a fetch returned a summary rather than verbatim text, it is labelled as such.

**Headline:** the single most important world fact for Vysted this cycle is that **OpenBB — the reference point for "open-source Bloomberg" — is shutting down as a company and open-sourcing everything (2026-08-25).** That simultaneously removes the incumbent and dumps its entire codebase into the commons. The second is that **Zerodha's official Kite MCP is deliberately, permanently read-only on its hosted endpoint** — which is exactly the safety posture Vysted already locked in §6.5, meaning Vysted is *aligned with*, not behind, the largest Indian broker's own stance.

---

## 1. OpenBB — the incumbent just folded

### 1.1 OpenBB the company is closing; the whole suite goes permissive open source

**RAW-FINDING**
```json
{"raw_id": "WORLD-OBB-1", "title": "OpenBB (the primary 'open-source Bloomberg' comparable) announced it is shutting down and open-sourcing its entire suite on 2026-08-25", "severity": "high", "area": "release", "subsystem": "competitive-landscape", "repro": "Read openbb.co/blog/openbb-belongs-to-everyone/", "evidence": "https://openbb.co/blog/openbb-belongs-to-everyone/ (pub. 2026-08-25)", "notes": "Not a Vysted defect — a market event that changes positioning, messaging and the 'why not just use OpenBB' objection. Vysted's README/positioning docs almost certainly still treat OpenBB as a live commercial incumbent."}
```

Source: [OpenBB belongs to everyone](https://openbb.co/blog/openbb-belongs-to-everyone/), published **2026-08-25**.

Observed content (fetched, summarised by the fetch tool; the verbatim fragments it returned are quoted):

- Products being open-sourced: **OpenBB Workspace, Open Data Platform, OpenBB Copilot, and the OpenBB Excel Add-in** — i.e. the *entire* suite, not just the already-open Platform SDK.
- License: described only as a **"permissive open source license"**; the specific SPDX identifier is **not named** in the post as of this fetch.
- Company status: **closing, not acquired.** Didier Lopes (co-founder) states the firm "couldn't find the product-market fit needed to build a sustainable business" and, on finding a home with a larger company, "we weren't able to make that happen".
- Timing: "We will share more details about the order and timing of each release as we complete that work." — no dated schedule.
- Backing for the decision: OSS Capital / Joseph Jacks thanked for "enabling the technology to live beyond the company".

Corroboration of the same facts from search-result snippets (search, not fetch): a search for `OpenBB open sourcing entire product suite permissive license OSS Capital August 2026` returns the same blog as top hit and the snippet "OpenBB is open-sourcing its entire product suite under a permissive open source license with the support of OSS Capital. This includes OpenBB Workspace, Open Data Platform, OpenBB Copilot and the OpenBB Excel Add-in." and "over 5 years of engineering, millions of dollars invested in R&D".

**Why this matters to Vysted, concretely:**
1. The "why not just use OpenBB?" objection changes shape. It is no longer "OpenBB is a funded company with a team"; it is "OpenBB is an abandoned codebase that anyone may fork." A *maintained* agent-native terminal is now a differentiator on its own.
2. Vysted's AGPL-3.0 + commercial dual license (locked, `docs/BLUEPRINT.md` §2) is now the **stricter** of the two. OpenBB going permissive means a well-capitalised firm can close-source a fork of OpenBB; they cannot do that with Vysted. That is a positioning asset worth stating out loud.
3. OpenBB's death is a cautionary datapoint *about the business model Vysted shares*: free/open desktop finance tool, monetised by teams/enterprise. Lopes's own stated cause was PMF, not technology. Vysted's India-first + BYOK + agent-native wedge is a different bet, but the census should record that the closest comparable failed commercially.

### 1.2 OpenBB Terminal (the CLI) was already sunset before this

Source: [Sunsetting OpenBB Terminal: Why, How, and What now?](https://openbb.co/blog/sunsetting-openbb-terminal-why-how-and-what-now/) — surfaced in search; the Workspace replaced the terminal, and [Introducing the new OpenBB Workspace, the first AI-powered research and analytics workspace](https://openbb.co/blog/introducing-the-new-openbb-terminal/) is the replacement announcement. So the "terminal" form factor was abandoned by OpenBB **in favour of a browser workspace** — Vysted's bet on a *native desktop* app (Tauri) runs against the incumbent's own direction of travel. That is a deliberate contrarian bet (local-first, keychain, offline), but it should be an explicit, defended position rather than an unexamined assumption.

### 1.3 OpenBB Copilot was cloud + OpenAI, rate-limited, and NOT BYOK at the free tier

**RAW-FINDING**
```json
{"raw_id": "WORLD-OBB-2", "title": "OpenBB's free Copilot tier was capped at 20 queries/day and keyed to OpenAI/Azure — BYOK was a paid-tier feature; Vysted's unlimited BYOK is a genuine differentiator that is probably not stated anywhere in Vysted's own copy", "severity": "medium", "area": "agent", "subsystem": "positioning/copilot", "repro": "Compare openbb.co/pricing Community row against Vysted's BYOK model", "evidence": "https://openbb.co/pricing/ — Community: '20 daily Copilot queries'; Pro: 'Bring your API key'", "notes": "Vysted's BYOK is table-stakes-plus here, not behind. Worth checking Vysted's landing copy actually says 'no query caps, your key, your spend'."}
```

Source: [OpenBB Pricing](https://openbb.co/pricing/) (fetched 2026-09-19). Observed tiers:

| Tier | Price | Hosting | Copilot |
|---|---|---|---|
| Community | Free, individual license | **cloud-hosted by OpenBB** | **20 Copilot queries/day** |
| Lite | $1,200/yr (50% off through Aug 31; list $2,400) | self-hosted on-prem or VPC, teams <10 | — |
| Pro | Custom | self-hosted on-prem or VPC | "deployed Copilot", **"Bring your API key"** |
| Snowflake | $500/yr/seat | Snowflake-hosted | — |

Notable: **"Workspace MCP server"** is listed as included **across all tiers**, including free Community. So MCP access was never the paywalled part — the *model* was.

Source for the Copilot's model stack: [Copilot Basics | OpenBB Workspace Docs](https://docs.openbb.co/workspace/analysts/ai-features/copilot-basics) — the page states the Copilot is "leveraging the latest models from OpenAI" and references "Azure OpenAI" for enterprise deployments. **Honest limitation:** the fetched page did **not** document BYOK, query limits, local vs cloud execution, or an enumerated data-source list — those specifics came from the pricing page above, not the docs. The docs are thin on exactly the questions a BYOK-first competitor cares about.

### 1.4 OpenBB Workspace is an MCP *client*, not primarily an MCP server, for its agents

Source: [AI Features — MCP Tools Integration | OpenBB Workspace Docs](https://docs.openbb.co/workspace/developers/ai-features/mcp-tools).

Quoted from the page: *"The agent acts as an orchestrator between the OpenBB workspace and MCP servers, translating tool calls into executable functions."* The documented flow is: *"User sends query to agent with available MCP tools in request payload"* → *"Frontend executes MCP tool and returns results."* Enablement is a flag in the agent manifest: `agents.json` with `"mcp-tools": True`.

Two things the page **does not** document (checked, absent — an honest gap rather than a claim): supported MCP **transports**, and **authentication**/credential management for MCP servers. It also "explicitly states no limitations", which for a security-relevant integration is itself a documentation weakness.

**Architecturally this means:** OpenBB's agents execute MCP tools **in the frontend/browser**. Vysted executes MCP tools in a Rust-spawned subprocess on the user's machine (`src-tauri/src/openbb_mcp.rs` precedent, per project CLAUDE.md). Vysted's model is strictly better for local/private data and for tools that need filesystem or keychain reach; OpenBB's is better for zero-install. This is a real architectural fork in the road, not a bug.

### 1.5 Workspace MCP — OpenBB *also* shipped the server direction, with a governance story

**RAW-FINDING**
```json
{"raw_id": "WORLD-OBB-3", "title": "OpenBB shipped 'Workspace MCP' (May 2026) letting Claude Code/Codex drive the workspace — entitlement inheritance, central credential management and data lineage on every output. Vysted's MCP server has no documented equivalent of 'entitlements apply to the agent exactly as they apply to the user' or per-output lineage.", "severity": "medium", "area": "agent", "subsystem": "mcp-server/provenance", "repro": "Read openbb.co/blog/introducing-workspace-mcp/ and compare to docs/MCP_INTEGRATION.md", "evidence": "https://openbb.co/blog/introducing-workspace-mcp/ (pub. 2026-05-26) — 'Entitlements apply to the agent exactly as they apply to the user behind it'; 'Every output carries data lineage'", "notes": "Vysted has FR-041 provenance labels on broker reads (synthetic/mode/provider). The world's framing is broader: lineage on EVERY agent output, not just broker reads. Possible extension of an existing Vysted capability rather than net-new."}
```

Source: [Introducing Workspace MCP: agentic financial workflows, governed by design](https://openbb.co/blog/introducing-workspace-mcp/), published **2026-05-26**.

Verbatim quotes returned by the fetch:
- *"MCP, short for Model Context Protocol, is an open standard that lets AI agents connect to external data sources and take actions through them."*
- *"Entitlements apply to the agent exactly as they apply to the user behind it"*
- *"The artifacts an agent builds are governed too"*
- *"API keys and credentials are managed centrally"*
- *"Every output carries data lineage"*

Described observation: the post demonstrates **Claude Code, Codex, and Cortex Code** connecting to OpenBB through Workspace MCP, including "Codex building a complete application from a product requirements document" and agents "performing portfolio risk assessments across multiple data sources simultaneously". Agents can reach "any data source you have set up in your workspace", "query that data, transform it, and combine sources", and create "working widgets, dashboards, and full apps".

Corroborating search snippet (from the first search): *"Investment firms are running long-running agents like Claude Code and Codex that plan and execute work across hours."*

**The proven pattern:** the *durable, multi-hour, external-agent-driven* workflow is the direction the professional end of the market moved in 2026. Vysted already has the substrate for this (durable Delegate runs, `services/run_manager.py`, `BudgetGuard`, runs SQLite store, and an MCP server projecting the capability catalog). The gap is not capability — it is that OpenBB wrapped it in a **governance narrative** (entitlements, lineage, central credentials) and Vysted has not.

### 1.6 Building agents for OpenBB required hand-wiring the loop

Source: [Building AI agents for OpenBB Workspace with Pydantic AI](https://openbb.co/blog/building-ai-agents-for-openbb-workspace-with-pydantic-ai/) + [Agents Integration | OpenBB Workspace Docs](https://docs.openbb.co/workspace/developers/agents-integration).

Described observation (search snippet, page titles confirmed): users "can use the built-in Copilot with OpenAI, or build an integration from scratch using the OpenBB AI SDK which provides the protocol but requires wiring up LLM calls, tool orchestration, and streaming events." Recommended stack: **FastAPI with `EventSourceResponse` from `sse_starlette` and the `openbb-ai` SDK**.

That is *exactly* Vysted's sidecar stack (Python 3.13 FastAPI). The bring-your-own-agent surface OpenBB documented is a protocol over SSE + a POST endpoint. Vysted's first-party agent JSON roster is a higher-level abstraction; the world's proven pattern is *both* — a built-in agent **and** a documented protocol for third-party agents to plug in. There is an [AI Vendors](https://openbb.co/ai-vendor/) page, i.e. OpenBB ran a *marketplace of third-party copilots*, not just its own.

---

## 2. Zerodha Kite MCP — what is actually proven

### 2.1 The full official tool surface (22 tools), verbatim

Source: [zerodha/kite-mcp-server README](https://github.com/zerodha/kite-mcp-server/blob/master/README.md) (fetched via raw.githubusercontent.com, 2026-09-19).

| Category | Tool | Description (verbatim from README) |
|---|---|---|
| Setup | `login` | "Login to Kite API and generate authorization link" |
| Market data | `get_quotes` | "Get real-time market quotes" |
| | `get_ltp` | "Get last traded price" |
| | `get_ohlc` | "Get OHLC data" |
| | `get_historical_data` | "Historical price data" |
| | `search_instruments` | "Search trading instruments" |
| Portfolio | `get_profile` | "User profile information" |
| | `get_margins` | "Account margins" |
| | `get_holdings` | "Portfolio holdings" |
| | `get_positions` | "Current positions" |
| | `get_mf_holdings` | "Mutual fund holdings" |
| Trading | `place_order` | "Place new orders" |
| | `modify_order` | "Modify existing orders" |
| | `cancel_order` | "Cancel orders" |
| | `get_orders` | "List all orders" |
| | `get_trades` | "Trading history" |
| | `get_order_history` | "Order execution history" |
| | `get_order_trades` | "Get trades for a specific order" |
| GTT | `get_gtts` | "List GTT orders" |
| | `place_gtt_order` | "Create GTT orders" |
| | `modify_gtt_order` | "Modify GTT orders" |
| | `delete_gtt_order` | "Delete GTT orders" |

**The gate, verbatim:** *"You can exclude specific tools by setting the `EXCLUDED_TOOLS` environment variable with a comma-separated list of tool names. This is useful for creating read-only instances."* — example given: `EXCLUDED_TOOLS=place_order,modify_order,cancel_order`.

**The hosted posture, verbatim:** *"The hosted version at `mcp.kite.trade` excludes potentially destructive trading operations for security."* and *"For accessing the other operations you can generate your own API keys and run the server locally."*

Config surface: `APP_MODE` (`stdio` | `http` | `sse` | `hybrid`, default `http`), `APP_PORT` (8080), `APP_HOST` (localhost), `KITE_API_KEY`, `KITE_API_SECRET`. Hosted endpoints: `https://mcp.kite.trade/mcp` and `https://mcp.kite.trade/sse`. The recommended client config is `npx mcp-remote https://mcp.kite.trade/mcp` — i.e. **the officially blessed consumption path is a remote HTTP MCP endpoint bridged into a desktop client via `mcp-remote`.**

**RAW-FINDING**
```json
{"raw_id": "WORLD-KITE-1", "title": "India's largest broker ships an OFFICIAL MCP server whose hosted endpoint is deliberately read-only — Vysted's §6.5 read-only-broker stance matches the market leader's own posture and should be stated as alignment, not as a limitation", "severity": "medium", "area": "docs", "subsystem": "positioning/safety", "repro": "Read the kite-mcp-server README hosted-version note", "evidence": "https://github.com/zerodha/kite-mcp-server/blob/master/README.md — 'The hosted version at mcp.kite.trade excludes potentially destructive trading operations for security.'", "notes": "Vysted docs likely frame read-only as 'order execution deferred to 1.0 roadmap' (an apology). The world evidence supports framing it as the correct default that Zerodha itself chose."}
```

### 2.2 Zerodha's own user-facing claims and the admitted gaps

Source: [Connect your Zerodha account to AI assistants with Kite MCP — Z-Connect](https://zerodha.com/z-connect/featured/connect-your-zerodha-account-to-ai-assistants-with-kite-mcp), published **2025-05-20**. Also [Kite MCP product page](https://zerodha.com/products/mcp/) and [Zerodha support article](https://support.zerodha.com/category/trading-and-markets/general-kite/others-kite/articles/connect-zerodha-ai-assistant).

Verbatim / near-verbatim from the Z-Connect post:
- Capability: *"Real-time data access: Access current market prices, not just historical data"*; portfolio analysis with sector exposure and diversification; *"Research stocks in natural language while seeing how they would fit with your existing portfolio"*.
- **Admitted gaps, verbatim:** *"Order placement, historical trade data, portfolio data, and some other features are currently unavailable."*
- Also unavailable: pledged holdings for Loan Against Securities (LAS).
- Security: *"Your Zerodha credentials never pass through Claude. Instead, authentication happens externally through Kite's secure two-factor authentication flow."*
- Clients: *"MCP is supported by multiple AI platforms including Claude, Windsurf, and Cursor"*; VS Code + GitHub Copilot also noted.
- Setup friction: requires **Node.js** installed and per-client JSON config editing.

From the first search's snippet on the same topic: *"The tokens granted to AI tools are short-lived and scoped to read-only operations (e.g., holdings, order history, live quotes), preventing unauthorized trading actions."*

**Note the contradiction worth recording:** the README lists `place_gtt_order`/`modify_gtt_order`/`delete_gtt_order` as tools, and the Z-Connect post markets **GTT creation and management** as a *feature* while calling order placement unavailable. So the hosted endpoint is "read-only **plus GTT**" — a GTT is a standing conditional order that *becomes* a live order. That is a meaningful safety nuance: **the market leader's "read-only" MCP can still arm a trade.** Vysted's §6.5 model (append-only audit, confirm-before-place type gate, kill-switch) is stricter than Zerodha's hosted MCP on this specific point.

**RAW-FINDING**
```json
{"raw_id": "WORLD-KITE-2", "title": "Zerodha's hosted 'read-only' Kite MCP still exposes GTT create/modify/delete — a standing conditional order that can become a live trade; marketing calls it read-only", "severity": "medium", "area": "agent", "subsystem": "safety/competitive", "repro": "Compare README GTT tool rows against the Z-Connect 'order placement unavailable' claim", "evidence": "README https://github.com/zerodha/kite-mcp-server/blob/master/README.md lists place_gtt_order/modify_gtt_order/delete_gtt_order; https://zerodha.com/z-connect/featured/connect-your-zerodha-account-to-ai-assistants-with-kite-mcp says 'Order placement ... currently unavailable' while marketing GTT management as a feature", "notes": "Vysted should NOT copy this. It is an argument FOR Vysted's stricter gate, and a concrete talking point: 'the largest broker's agent can arm a trade; ours cannot touch one.'"}
```

### 2.3 The daily-login tax — a structural friction every Indian broker agent inherits

Source: [Kite Connect developer forum](https://kite.trade/forum/discussion/13884/what-is-the-earliest-time-in-the-day-i-can-generate-the-access-token-for-the-day) and related threads ([token expires too frequent](https://kite.trade/forum/discussion/734/token-expires-too-frequent), [exact time of access token expiry](https://kite.trade/forum/discussion/4108/exact-time-of-my-access-token-expiry), [access token validity](https://kite.trade/forum/discussion/7759/access-token-validity)), plus [Kite Connect v3 User API docs](https://kite.trade/docs/connect/v3/user/).

Described observations from those threads (forum text, surfaced via search):
- Access tokens are **flushed daily in the morning** — staff answers cite ~07:30 IST with retry after 07:35; users report observed expiry anywhere from **06:00 to 07:30 IST**.
- *"It is mandatory by the exchange that a user has to manually log in at least once a day"* — and automating that login is explicitly **not recommended**.
- **Only one access token is active per app**; generating a new one invalidates the previous.

**RAW-FINDING**
```json
{"raw_id": "WORLD-KITE-3", "title": "Every Indian-broker agent inherits a mandatory once-daily manual login + morning token flush (~06:00-07:30 IST) and a one-active-token-per-app rule — an always-on desktop agent MUST handle this as a first-class lifecycle state, not an error", "severity": "high", "area": "lifecycle", "subsystem": "broker-auth", "repro": "Leave a Kite-connected session running overnight; next morning every broker read 401s", "evidence": "https://kite.trade/forum/discussion/13884/... ('mandatory by the exchange that a user has to manually log in at least once a day'); https://kite.trade/docs/connect/v3/user/ ; https://kite.trade/forum/discussion/4108/...", "notes": "Vysted's Kite flow is a manual request_token paste (v1, per CLAUDE.md). The question the census must answer against the code: does the UI DISTINGUISH 'token expired, this is normal, re-login' from 'broker down / your key is wrong'? A raw 401 shown as an error is a table-stakes miss. Single-active-token also means Vysted competes with the user's OWN other tools for the one token."}
```

This is the kind of thing that makes an Indian finance desktop app feel either professional or broken, and it is invisible to anyone building against US brokers. It also interacts badly with the single-active-token rule: if the user runs Kite MCP in Claude Desktop *and* Vysted, whichever logs in second **kills the other's session**. A desktop terminal that silently dies because the user opened Claude is a support nightmare — and an opportunity if Vysted detects and explains it.

### 2.4 Kite MCP as actually consumed by users

Source: [How to Connect Your Zerodha Account to Claude Using Kite MCP — Analytics Vidhya](https://www.analyticsvidhya.com/blog/2025/06/zerodha-mcp/) (June 2025). Described observation from the search snippet and title: a step-by-step walkthrough aimed at connecting **Claude Desktop** to Kite MCP, consistent with the Zerodha docs' `npx mcp-remote` path.

The consumption pattern that is *proven in the wild* is therefore: **general-purpose chat client (Claude Desktop / Cursor / Windsurf) + remote broker MCP + JSON config editing + Node.js prerequisite.** There is no evidence in these sources of a *purpose-built desktop finance client* that ships broker MCP pre-wired. That absence is the opportunity (see §5).

### 2.5 Community forks went the other way — toward execution

Sources:
- [Sundeepg98/kite-mcp-server](https://github.com/Sundeepg98/kite-mcp-server) — repo description, verbatim from the search result: *"Self-hosted MCP for Zerodha Kite — order placement, RiskGuard safety, paper trading, Greeks, backtesting, Telegram alerts. ~110 tools."*
- [aptro/zerodha-mcp](https://github.com/aptro/zerodha-mcp) — "Mcp server to connect with zerodha's kite trade apis".
- [sukeesh/zerodha-mcp-go](https://playbooks.com/mcp/sukeesh/zerodha-mcp-go).
- [sid077/homebrew-chatmem PR #1](https://github.com/sid077/homebrew-chatmem/pull/1) — "Add read-only Zerodha MCP server for Kite and Coin holdings". Search snippet describes this class of server as providing *"ten read-only tools with no order placement tool, and the HTTP client only issues GETs"*.
- [zicurojj kitetrading-mcp-server](https://lobehub.com/mcp/zicurojj-kitetrading-mcp-server-claude) — advertises "Fully Automated Authentication", i.e. someone is already automating the login Zerodha says not to automate.

Observation: the community split into two camps — **~110-tool execution-capable forks with bolted-on "RiskGuard"**, and **minimal GET-only forks**. Nobody in this sample is shipping the middle: a read-only surface with *auditable, DB-enforced* safety and a real research layer on top. That middle is Vysted's exact position (append-only SQLite audit with `RAISE(ABORT)` triggers, `PRAGMA query_only=ON` reader, kill-switch, grep-time call-site audit).

Note also: the `sid077` read-only server's design — *"the HTTP client only issues GETs"* — is **the same three-layer pattern Vysted's read-only wrapper plugins already enforce** (no mutating method names on the provider surface, no non-GET routes, `supportsControlPlane = false`). Independent convergence on Vysted's design is evidence the design is right.

---

## 3. The wider finance-MCP and Indian-broker-API landscape

### 3.1 Indian broker MCP servers that exist today

Source: search `Indian broker MCP server Upstox Dhan Angel One Groww AI agent API 2026` and the pages below. These are **community/third-party** unless stated.

| Broker | Server | What it exposes (as described by the listing) | Source |
|---|---|---|---|
| Zerodha | **official** `zerodha/kite-mcp-server` | 22 tools; hosted = read-only + GTT; self-host = full execution | [GitHub](https://github.com/zerodha/kite-mcp-server) |
| Upstox | `adibhattar95/upstox-mcp-server` | "Upstox market, technical, and account data as MCP tools"; NSE/BSE/MCX real-time; RSI/MACD/Bollinger; portfolio — **"strictly read-only mode"** | [Glama](https://glama.ai/mcp/servers/adibhattar95/upstox-mcp-server) |
| Upstox | `ravikant1918/mcp-server-upstox` | second independent Upstox server | [mcpservers.org](https://mcpservers.org/servers/ravikant1918/mcp-server-upstox) |
| Angel One | SmartAPI MCP | "trade Indian stocks, manage orders and GTT rules, read holdings/positions/funds, fetch quotes/candles/**OI/Greeks**, and estimate **margin/brokerage** with TOTP login and built-in safety guards" | search snippet, Angel One SmartAPI MCP |
| Dhan | DhanHQ MCP | "holdings, orders, trade history, and token renewal via DhanHQ APIs" | search snippet; [Dhan API alternatives comparison](https://www.multibagg.ai/market-pulse/articles/dhan-api-alternatives-indian-brokers-cmpgarbdyhotqp40j24hrogv2) |
| Groww | Groww MCP | "fetch portfolio data, get live stock quotes and historical market data, and place, modify, or cancel stock orders" | [github topics/groww](https://github.com/topics/groww) |
| Multi-broker | `sharuniyer/indian-broker-mcp` | "support for Groww, INDmoney, Zerodha, Angel One, Upstox, and 5paisa" | [LobeHub](https://lobehub.com/mcp/sharuniyer-indian-broker-mcp) |
| Market data (no broker) | `Sparker0i/indian-stock-mcp-agent` | "MCP Server that deals with Indian Stocks, MFs, Crypto, etc." | [GitHub](https://github.com/Sparker0i/indian-stock-mcp-agent) / [LobeHub](https://lobehub.com/mcp/sparker0i-indian-stock-mcp-agent) |

Survey-of-the-field source: [Indian Stock Market MCP: The Best MCP Servers for NSE & BSE Data (2026) — DEV](https://dev.to/govind_sisara/indian-stock-market-mcp-the-best-mcp-servers-for-nse-bse-data-2026-p28). Quoted framing from the snippet: *"The Model Context Protocol (MCP) is an open standard that lets AI assistants discover tools, call live data services, and act on the results. An Indian stock market MCP server applies that standard to NSE and BSE data so AI assistants can query real-time data instead of relying on memory."*

**RAW-FINDING**
```json
{"raw_id": "WORLD-MCP-1", "title": "A populated ecosystem of Indian broker MCP servers already exists (Zerodha official + Upstox x2, Angel One, Dhan, Groww, 5paisa, INDmoney, multi-broker) — Vysted's plugin system can RIDE these instead of hand-writing each broker adapter", "severity": "medium", "area": "data", "subsystem": "brokers/plugins", "repro": "Enumerate the servers in the table in §3.1", "evidence": "https://glama.ai/mcp/servers/adibhattar95/upstox-mcp-server ; https://lobehub.com/mcp/sharuniyer-indian-broker-mcp ; https://github.com/zerodha/kite-mcp-server", "notes": "Vysted already spawns MCP subprocesses via Rust (openbb_mcp.rs precedent) and already bundles an openbb-mcp plugin. 'Add a broker' could become 'point at an MCP server + declare it read-only' rather than 'write a Python adapter'. Needs a code-side check of whether the plugin contract can express an MCP-backed read-only broker today."}
```

### 3.2 Angel One is the most capability-rich Indian broker surface

The Angel One SmartAPI MCP description is the only one in the sample that names **open interest, option Greeks, margin and brokerage estimation, and TOTP login**. For an F&O-literate Indian audience (the actual Indian retail centre of gravity), OI + Greeks + margin/brokerage estimation are the data an equity-only terminal simply does not have. TOTP login also matters: it is the one Indian broker auth flow that can be made **non-interactive** without violating the "no automated login" guidance the way Kite's does.

**RAW-FINDING**
```json
{"raw_id": "WORLD-MCP-2", "title": "Angel One SmartAPI exposes OI, option Greeks, and margin/brokerage estimation with TOTP login — the F&O data Indian retail actually trades on, and the only surveyed Indian broker auth that is cleanly non-interactive", "severity": "high", "area": "data", "subsystem": "brokers/derivatives", "repro": "Compare the Angel One SmartAPI MCP tool list against Vysted's broker read shapes (positions/holdings/margins)", "evidence": "search result for Angel One SmartAPI MCP: 'read holdings/positions/funds, fetch quotes/candles/OI/Greeks, and estimate margin/brokerage with TOTP login and built-in safety guards'", "notes": "Vysted's granular broker reads are positions/holdings/margins (models/broker_reads.py). No OI/Greeks/brokerage-estimate shape. For an Indian-market terminal claiming 'Bloomberg-level coverage', missing OI + Greeks is closer to a table-stakes gap than a nice-to-have. Kite Connect itself also serves OI in quotes."}
```

### 3.3 Kite Connect: the commercial reality under the MCP

Source: [Kite Connect v3 docs](https://kite.trade/docs/connect/v3/user/) and the Kite Connect developer forum threads cited in §2.3.

Described observations relevant to a desktop agent:
- Single active access token per app; daily mandatory interactive login; morning flush.
- The MCP's hosted path removes the need for the user to hold an API key at all — **the hosted `mcp.kite.trade` requires "no installation or API keys"** (search snippet from the Kite MCP product page). That is a materially lower barrier than Kite Connect's paid API subscription.

That last point is strategically sharp: **Zerodha made the read-only agent path free and keyless, while the execution path still needs a paid Kite Connect subscription.** A BYOK desktop terminal that wants zero-friction onboarding should ride the free hosted read-only MCP, not demand a Kite Connect key.

**RAW-FINDING**
```json
{"raw_id": "WORLD-KITE-4", "title": "Zerodha's hosted Kite MCP needs no API key and no install — a zero-friction, zero-cost read-only broker connection that Vysted could offer as the DEFAULT onboarding path instead of manual request_token paste", "severity": "high", "area": "lifecycle", "subsystem": "onboarding/brokers", "repro": "Compare Vysted's documented Kite flow (manual request_token paste, user supplies api_key+api_secret) with 'add https://mcp.kite.trade/mcp to your AI client'", "evidence": "https://zerodha.com/products/mcp/ and README https://github.com/zerodha/kite-mcp-server/blob/master/README.md — hosted config is npx mcp-remote https://mcp.kite.trade/mcp; product page states the hosted version 'requires no installation or API keys'", "notes": "Vysted's CLAUDE.md records 'Manual request_token paste is the v1 flow' and api_secret crossing to the sidecar for the exchange. Riding the hosted MCP would remove the api_secret from the threat model ENTIRELY and cut onboarding to one click. Vysted already spawns MCP subprocesses from Rust. This is arguably the highest-leverage single change surfaced by this sweep."}
```


### 3.4 Kite Connect commercial terms — timeline, honestly reported (the sources disagree by date)

Two Zerodha sources say different things because the pricing moved:

- [Free personal APIs from Kite Connect — Z-Connect](https://zerodha.com/z-connect/updates/free-personal-apis-from-kite-connect), **2025-04-24**, verbatim: *"The execution APIs free, and we only charge ₹ 2000 for data."* Per this post, historical data was **not** in the free offering.
- [Revising Kite Connect fees from ₹2000 to ₹500 per month — Kite Connect forum](https://kite.trade/forum/discussion/15015/revising-kite-connect-fees-from-2000-to-500-per-month) and [Historical data is now free (with base Kite Connect subscription)](https://kite.trade/forum/discussion/14806/historical-data-is-now-free-with-base-kite-connect-subscription) — later, fees cut to **₹500/month per API key**, with live **and** historical data included. Corroborated by [Zerodha support: historical and live market data payment plan](https://support.zerodha.com/category/trading-and-markets/general-kite/kite-api/articles/historical-data-and-live-market-data-payment-plan).

**Net, as of this sweep:** a user wanting programmatic Kite access pays about **₹500/month**; a user wanting only agent-driven *reads* pays **nothing** and installs nothing by pointing at `https://mcp.kite.trade/mcp`. Source: [Kite MCP product page](https://zerodha.com/products/mcp/), verbatim: *"a protocol that lets AI assistants like Claude, Cursor, and VS Code securely connect to your Zerodha account"*, *"No code. Just chat."*, capabilities *"your portfolio, P&L, positions, margins, and market data in real-time"*, and the posture stated plainly as **"Read-only access."** Supported clients listed: Claude Desktop (macOS, Windows), Cursor, VS Code (Copilot Chat or Claude), Windsurf, Claude CLI on Linux.

**Note the discrepancy worth carrying forward:** the *product page* says flatly "Read-only access", while the *README* ships GTT write tools and the *Z-Connect post* markets GTT management as a feature. Zerodha's own three surfaces do not agree on whether the hosted MCP can write. Treat "Kite MCP is read-only" as **true for orders, false for GTT** until tested directly.

### 3.5 Browser-scraping MCPs are the no-API-key escape hatch — and they are fragile

Source: [Sparker0i/indian-stock-mcp-agent](https://github.com/Sparker0i/indian-stock-mcp-agent) (fetched).

Tools: `broker_connect` / `broker_disconnect` / `broker_status`; reads `get_holdings`, `get_positions`, `get_fno_positions`, `get_mutual_funds`, `get_us_stocks`, `get_gold`, `get_orders`, `get_portfolio_summary`; market data `search_stock`, `get_quote`. Brokers: **Groww, Zerodha Kite, INDmoney**. Technique: *"network interception"* to capture internal API responses rather than DOM scraping. Auth: *"No paid broker API subscriptions required"* — the user logs into the broker web app in a visible Chrome window.

Stated limitations, verbatim: *"Browser scraping is fragile — broker UIs and internal APIs change without notice"*; *"Automated access to broker web apps may violate their terms"*; OTP/TOTP needs manual presence; no real-time streaming; single-user design.

**Read for Vysted:** this is a road Vysted should **not** take (ToS risk, fragility, and it breaks the local-first/no-GUI-automation posture). But it is evidence of real demand: people are scraping browsers because the paid-API + daily-token path is too much friction for a read-only portfolio view. The hosted Kite MCP is the legitimate answer to the same demand.

### 3.6 screener.in — India's fundamentals benchmark has no official API, and the gap is filled by scrapers

Sources: [ronyv89/screener-mcp](https://github.com/ronyv89/screener-mcp) ("MCP Server for using data from screener.in"), [screener-mcp on Glama](https://glama.ai/mcp/servers/ronyv89/screener-mcp), [ashu017/screener-mcp](https://glama.ai/mcp/servers/ashu017/screener-mcp), and a cluster of Apify-hosted MCP actors: [scrapyx/screener-in-stocks-scraper](https://apify.com/scrapyx/screener-in-stocks-scraper/api/mcp), [solidcode/screener-in-scraper](https://apify.com/solidcode/screener-in-scraper/api/mcp), [shashwattrivedi/screener-in](https://apify.com/shashwattrivedi/screener-in/api/mcp), [data_daemon/tickertape-stocks-scraper](https://apify.com/data_daemon/tickertape-stocks-scraper/api/mcp), [fascinating_lentil/nse-bse-scraper](https://apify.com/fascinating_lentil/nse-bse-scraper/api/mcp), [fingolfin/india-stock-market-api](https://apify.com/fingolfin/india-stock-market-api/api/mcp).

Described observations from the listings: these expose "company info, financials, ratios, quarterly results, shareholding, and stock screening", "up to 13 years of quarterly results, profit & loss, balance sheet, cash flow, ratio trends, shareholding pattern and recent announcements", with "5-minute result caching" and field-selection to keep responses small. They use **screener.in's public data with no API key**.

**RAW-FINDING**
```json
{"raw_id": "WORLD-IN-1", "title": "screener.in — the stated data benchmark — has no official API; at least 8 independent scraper-MCPs exist to fill the gap, all fragile and ToS-grey", "severity": "medium", "area": "data", "subsystem": "fundamentals/india", "repro": "Search for screener.in MCP servers; note every one is a scraper", "evidence": "https://github.com/ronyv89/screener-mcp ; https://apify.com/scrapyx/screener-in-stocks-scraper/api/mcp ; https://apify.com/fascinating_lentil/nse-bse-scraper/api/mcp — listings state they use screener.in public data with no API key", "notes": "Vysted's moat claim is 'data trust'. A durable, LICENSED or first-party-sourced Indian fundamentals pipeline (NSE/BSE filings + XBRL, which Vysted already parses per CLAUDE.md) is defensible in a way that 8 scrapers are not. This is a strength to press, not a gap to close by adding a 9th scraper."}
```

---

## 4. The research benchmark: what Perplexity Finance proved, and what it admits it gets wrong

### 4.1 What it shipped (the bar)

Sources: [Perplexity for Stock Research in 2026: Strengths, Limits, and How to Use It — Helm Terminal](https://helmterminal.dev/blog/perplexity-stock-research) (fetched); [TechCrunch, 2025-08-18](https://techcrunch.com/2025/08/18/perplexity-now-supports-live-earnings-call-transcripts-for-indian-stocks/) (fetched); [Perplexity changelog](https://www.perplexity.ai/changelog/what-we-shipped-august-15th); [Perplexity Finance Launches India-Focused Platform With Free Real-Time BSE and NSE Data](https://completeaitraining.com/news/perplexity-finance-launches-india-focused-platform-with/); [AI CERTs coverage](https://www.aicerts.ai/news/ai-meets-markets-perplexity-finance-brings-real-time-stock-transcripts-to-india/); [Wright Research blog](https://www.wrightresearch.in/blog/how-perplexity-free-stock-data-is-redefining-a-game-for-indian-retail-traders/).

Verbatim / described feature set:
- *"quotes, candlestick charts with moving averages, market heatmaps, options and crypto data, fund and ETF pages"*
- Earnings Hub: *"earnings calendar plus transcripts and slides"* — and it can **transcribe and summarise a call in near real time while the call is still in session**, extracting revenue and EPS as they are spoken.
- **India specifically:** TechCrunch (2025-08-18), verbatim: *"live transcriptions of Indian public companies' quarterly earnings calls"* and *"a calendar to show schedules for post-results conference calls"*. (The TechCrunch piece does **not** state which exchanges, who the data provider is, or the price — recorded here as unknown rather than guessed.)
- Watchlists **with AI briefings**, price alerts, insider and politician trade data.
- A **natural-language screener for US *and Indian* equities**.
- **Tasks** — verbatim: *"Tasks, which run a recurring research query on a schedule"*.
- **Portfolio** (launched **March 2026**): Plaid-backed, *"read-only aggregation of holdings and transactions with AI analysis on top"* (US and Canada).
- Pricing: finance hub largely **free**; Pro **$20/month**; Max **$200/month** with agent features prioritised. Corroborated: real-time BSE and NSE tracking "all without requiring a subscription".

### 4.2 What it admits it gets wrong — this is Vysted's thesis, stated by a competitor's reviewer

Verbatim from the Helm Terminal review:
- *"It misreads financial documents"* — a test showed it **misinterpreting a 10-K by a factor of 1,000**.
- *"Precise numbers can still be hallucinated"* despite sounding specific.
- Unreliable on small caps and thinly covered companies.
- *"It retrieves, it does not reason about you"* — no awareness of position size or thesis logic.
- Portfolio aggregation "doesn't retain reasoning for holdings or re-test theses against new filings".

**RAW-FINDING**
```json
{"raw_id": "WORLD-PPLX-1", "title": "The research benchmark's documented failure mode is exactly Vysted's stated moat: numeric hallucination, 1000x unit errors on filings, and no portfolio-aware reasoning", "severity": "high", "area": "research", "subsystem": "trust/citations", "repro": "Read the 'Limits' section of the Helm Terminal review of Perplexity Finance", "evidence": "https://helmterminal.dev/blog/perplexity-stock-research — 'It misreads financial documents' (10-K off by a factor of 1,000); 'Precise numbers can still be hallucinated'; 'It retrieves, it does not reason about you'", "notes": "Vysted already has the machinery that would beat this: XBRL/SEC arbitrary-precision numbers crossing the wire as STRINGS (per CLAUDE.md, avoiding exactly the JS float/unit class of error), deriveMetrics returning null rather than fabricating (src/modules/research/brief-blocks.tsx), and a cite-check pass (sidecar/tests/test_research_citecheck.py). None of this is EVIDENCED to the user. The moat exists in code and is invisible in the product."}
```

Vysted's own code already encodes the defence. Two anchors:
- `sidecar/models/` XBRL/SEC values cross the wire as strings and are parsed to `BigInt` only when computing (project CLAUDE.md, "Arbitrary-precision numbers cross the wire as strings"). That is precisely the 1000x-unit-error class Perplexity fell into.
- `sidecar/tests/test_research_citecheck.py` exists — there is a citation-checking pass in the research path.

The gap is **demonstration**, not capability. A benchmark page showing "here is the 10-K figure Perplexity got wrong by 1000x, here is Vysted's answer, here is the XBRL fact it came from" is a stronger argument than any feature list.

---

## 5. The direct competitor nobody in the repo docs seems to have logged: Fincept Terminal

**RAW-FINDING**
```json
{"raw_id": "WORLD-COMP-1", "title": "Fincept Terminal is a near-identical competitor — native desktop + embedded Python analytics + 37 BYOK AI agents + MCP + drag-and-drop node editor + 16 brokers incl. Zerodha/Angel One/Upstox/Fyers + AGPL-3.0 free edition with a paid commercial license. Same architecture, same license model, same India brokers.", "severity": "critical", "area": "release", "subsystem": "competitive-landscape", "repro": "Read solosoft.dev/post/fincept-terminal-open-source-2026/ and github.com/topics/bloomberg-alternative", "evidence": "https://www.solosoft.dev/post/fincept-terminal-open-source-2026/ (pub. 2026-05-01) — 'C++20, Qt6, and embedded Python 3.11.9'; 'AGPL-3.0 (free for personal, academic, and open-source use)'; '37 AI agents'; 'integration with the Model Context Protocol (MCP) for tool orchestration'; 'Drag-and-drop node editor'; '16 broker integrations' incl. 'Zerodha, Angel One, Upstox, Fyers'; 'Commercial License ~$10,200/year'", "notes": "Severity critical not because it is a defect but because a census that misses a competitor replicating Vysted's exact architecture AND exact license model AND exact India broker set is a census that failed. This needs an explicit differentiation position in the launch narrative."}
```

Detail, with sources:

| Dimension | Fincept Terminal | Vysted Terminal |
|---|---|---|
| Shell | C++20 + Qt6, single binary, no Electron/Node | Tauri 2 (Rust) + Next.js static export |
| Analytics runtime | embedded Python 3.11.9 | Python 3.13 FastAPI sidecar (PyInstaller) |
| Agents | "37 AI agents" across Trader/Investor, Economic, Geopolitical frameworks | 14 first-party agent JSONs (`sidecar/agents/`: buffett, dalio, druckenmiller, graham, klarman, lynch, marks, munger, soros, copilot, researcher, portfolio_advisor, strategy_critic) |
| LLM model | BYOK — "OpenAI, Anthropic, Gemini, and local models via Ollama" | BYOK, OS-keychain-held |
| MCP | "integration with the Model Context Protocol (MCP) for tool orchestration" | MCP server projected from the capability catalog; 2 hardcoded MCP subprocesses |
| Node editor | "Drag-and-drop node editor" for workflow automation | `@xyflow/react` node editor (`src/modules/node-editor`) |
| Brokers | **16**, incl. Zerodha, Angel One, Upstox, Fyers, IBKR, Alpaca, Kraken, HyperLiquid | Kite (read-only) + example/broker plugins |
| License | AGPL-3.0 free edition + commercial (~$10,200/yr) | AGPL-3.0 + commercial dual license |

Sources: [SoloSoft write-up, 2026-05-01](https://www.solosoft.dev/post/fincept-terminal-open-source-2026/); [themenonlab](https://themenonlab.blog/blog/bloomberg-fincept-terminal-open-source-alternative); [Cybernews: "Bloomberg Terminal challenger gains traction on GitHub"](https://cybernews.com/security/bloomberg-terminal-challenged-by-freemium-app/); [openalternative.co Bloomberg Terminal alternatives](https://openalternative.co/alternatives/bloomberg-terminal). Vysted-side anchors: `sidecar/agents/` directory listing (14 JSON agents); `src/modules/node-editor`; `src-tauri/src/openbb_mcp.rs` + `src-tauri/src/sec_edgar_mcp.rs`.

**Fincept's stated weaknesses (verbatim from the SoloSoft piece) — every one is an opening:**
- *"Not a Bloomberg replacement for professionals"*
- *"Meme token launch created credibility concerns"* ← the single biggest gift. A serious, no-token, audited-safety terminal is trivially differentiated.
- *"Strict dependency requirements complicate source builds"* ← Vysted ships a `--onefile` signed binary with a staleness-aware build orchestrator.
- *"API credits expire after one month"* ← Vysted is pure BYOK, nothing to expire.
- Limited A-share support.

Also on the topic page: [`asymmetrica/sextant`](https://github.com/topics/bloomberg-alternative) — TypeScript, last updated 2026-06-04, described as *"The open financial data terminal for humans and agents. Multi-asset (FX, equities, crypto, news, macro)"* and explicitly *"agent-native (MCP)"*. Zero stars; early. And `Archsec-Emman/Financial-Orchestrator` (Python, 2 stars, updated 2026-09-05) carries a description that is a **verbatim copy of Fincept's** ("37 AI agents, 100+ data connectors, 16 broker integrations... visual node editor") but is **MIT licensed** — i.e. someone appears to be relicensing an AGPL project's description/claims. Recorded as an observation; not investigated further.

---

## OPPORTUNITIES FOR VYSTED

Each: what the world lacks or does badly → the evidence → the Vysted capability it sits **one step** from.

**O1 — The incumbent's seat is empty, and Vysted's license is now the stronger one.**
*World gap:* OpenBB is closing and dumping its suite under a permissive license ([openbb.co/blog/openbb-belongs-to-everyone/](https://openbb.co/blog/openbb-belongs-to-everyone/), 2026-08-25: "couldn't find the product-market fit needed to build a sustainable business"). An abandoned permissive codebase can be closed-sourced by any acquirer; an AGPL one cannot.
*One step from:* Vysted's already-locked AGPL-3.0 + commercial dual license (`docs/BLUEPRINT.md` §2). The step is **narrative only** — say it in the README and launch copy: "the maintained one, and the one that stays open."

**O2 — One-click, keyless, install-free broker connect.**
*World gap:* nobody ships a *purpose-built finance desktop app* with the hosted Kite MCP pre-wired; the proven path is "edit a JSON file, install Node, run `npx mcp-remote`" ([kite-mcp-server README](https://github.com/zerodha/kite-mcp-server/blob/master/README.md)). Zerodha made this path free and keyless ([zerodha.com/products/mcp/](https://zerodha.com/products/mcp/): "No code. Just chat.", "Read-only access.").
*One step from:* Vysted already spawns MCP subprocesses from Rust (`src-tauri/src/openbb_mcp.rs`, `src-tauri/src/sec_edgar_mcp.rs`). Pointing a third at `https://mcp.kite.trade/mcp` replaces the manual `request_token` paste (`sidecar/services/brokers/kite.py:14`) and **removes `api_secret` from the threat model entirely** (`kite.py:507`). Highest leverage single change in this sweep.

**O3 — "Add any MCP server" is table stakes in the ecosystem and absent in Vysted.**
*World gap:* the point of MCP is that users bring their own servers; the Indian ecosystem alone has Upstox ×2, Angel One, Dhan, Groww, 5paisa, INDmoney, multi-broker, and ~8 screener.in servers (§3.1, §3.6).
*One step from:* `sidecar/routers/mcp.py` exposes only `/mcp/status` and `/openbb-mcp/status` (lines 28, 44); a repo-wide grep for `mcp_servers|mcpServers|add_mcp|external_mcp|custom_mcp` across `sidecar/`, `src/`, `src-tauri/src/`, `types/` returns **zero hits**. The two MCP subprocesses are hardcoded. A user-config'd MCP server list turns every server in §3.1 into a Vysted data source for free.

**O4 — The entire finance-MCP ecosystem is US-centric, explicitly.**
*World gap:* verbatim from [Chart Library's nine-server comparison](https://chartlibrary.io/blog/financial-mcp-servers-compared): *"International coverage gap: Only EODHD explicitly addresses non-US markets; most focus on US equities."* [Financial Datasets](https://docs.financialdatasets.ai/mcp-server) — the most-starred of them — covers "US Treasury", "central bank policy rates", "US CPI series", SEC filings; no India coverage stated.
*One step from:* Vysted's existing India resolver work (`sidecar/services/nse_symbol_change.py`, `enrich_nse_sectors`, `sidecar/tests/test_screener_india.py`). Vysted can be *the* Indian finance MCP server — a role literally nobody credible occupies.

**O5 — Numeric trust as a demonstrated, benchmarked claim.**
*World gap:* the research benchmark misread a 10-K **by a factor of 1,000** and "precise numbers can still be hallucinated" ([helmterminal.dev](https://helmterminal.dev/blog/perplexity-stock-research)).
*One step from:* Vysted already carries strings-on-the-wire for arbitrary-precision XBRL, `deriveMetrics` that returns `null` rather than a fabricated value (`src/modules/research/brief-blocks.tsx`), and `sidecar/tests/test_research_citecheck.py`. The step is a **public benchmark page** that shows the delta, not more code.

**O6 — Portfolio-aware research.**
*World gap:* verbatim: *"It retrieves, it does not reason about you"* — no position-size or thesis awareness; Plaid Portfolio "doesn't retain reasoning for holdings or re-test theses against new filings" ([helmterminal.dev](https://helmterminal.dev/blog/perplexity-stock-research)).
*One step from:* Vysted has broker reads (`sidecar/models/broker_reads.py`), a `portfolio_advisor` agent (`sidecar/agents/portfolio_advisor.json`), and a research brief that already threads `structured` metrics. Joining "your actual position" to "this filing" is a prompt/context-assembly step over data Vysted already holds locally — and it is the thing a *local-first* app can do that a cloud one structurally cannot do privately.

**O7 — Scheduled, recurring research.**
*World gap:* Perplexity ships **Tasks** — *"run a recurring research query on a schedule"*; OpenBB's pitch was firms "running long-running agents like Claude Code and Codex that plan and execute work across hours" ([openbb.co/blog/introducing-workspace-mcp/](https://openbb.co/blog/introducing-workspace-mcp/)).
*One step from:* Vysted already has **detached durable runs** — `sidecar/services/run_manager.py` spawning `asyncio.create_task`, `sidecar/services/runs_store.py` (SQLite), `sidecar/routers/runs.py`, with `BudgetGuard` ceilings. What is missing is only a **trigger**: a grep for `schedule|cron|recurring` across `sidecar/`, `src/`, `types/` hits only earnings *calendars* and cache warmers, never a user-scheduled task. This is a scheduler over an engine that already exists — the cheapest big win here.

**O8 — Lineage on every agent output, not just broker reads.**
*World gap / proven pattern:* OpenBB's governance framing, verbatim: *"Entitlements apply to the agent exactly as they apply to the user behind it"*, *"Every output carries data lineage"* ([openbb.co/blog/introducing-workspace-mcp/](https://openbb.co/blog/introducing-workspace-mcp/), 2026-05-26).
*One step from:* Vysted's FR-041 provenance label (`synthetic`/`mode`/`provider`) already rides **every broker read result** (`sidecar/models/broker_reads.py:30` `BrokerReadProvenance`, inherited by `BrokerPositionsResult:64`, `BrokerHoldingsResult:90`, `BrokerMarginsResult:110`). Generalising that one base model to every agent tool result is a small, mechanical extension of a pattern already proven in-tree.

**O9 — Be stricter than Zerodha, and say so.**
*World gap:* the market leader's "read-only" MCP still exposes `place_gtt_order`/`modify_gtt_order`/`delete_gtt_order` ([README](https://github.com/zerodha/kite-mcp-server/blob/master/README.md)) while the product page says flatly "Read-only access" and Z-Connect says "Order placement... currently unavailable". A GTT arms a trade.
*One step from:* Vysted's §6.5 model is already stricter — DB-enforced append-only audit (`sidecar/models/audit_log.py` `AUDIT_LOG_DDL` with `RAISE(ABORT)` triggers), `PRAGMA query_only=ON` reader, kill-switch, and read-only wrapper plugins that admit **no non-GET routes**. The step is a one-paragraph comparison in the safety docs.

**O10 — Credibility is a differentiator because the nearest clone burned it.**
*World gap:* Fincept's own coverage lists *"Meme token launch created credibility concerns"* and *"API credits expire after one month"* ([solosoft.dev](https://www.solosoft.dev/post/fincept-terminal-open-source-2026/), 2026-05-01).
*One step from:* Vysted has no token, pure BYOK (nothing expires), and a documented, test-enforced safety architecture. Free positioning.

**O11 — A documented third-party agent protocol + an agent marketplace.**
*World gap / proven pattern:* OpenBB ran an [AI Vendors page](https://openbb.co/ai-vendor/) — third-party copilots plugging into the workspace over an SSE + POST protocol ([Building AI agents for OpenBB Workspace with Pydantic AI](https://openbb.co/blog/building-ai-agents-for-openbb-workspace-with-pydantic-ai/), [Agents Integration docs](https://docs.openbb.co/workspace/developers/agents-integration)).
*One step from:* Vysted has `src/modules/marketplace`, `src/modules/agent-builder`, a plugin contract with an `agents` capability (`types/plugin.ts`), and custom agents with a catalog-derived allow-list (`sidecar/models/custom_agent.KNOWN_TOOL_IDS`). The bring-your-own-*agent* story is mostly built and, going by the module list, not told.

**O12 — Own the daily-login tax that every Indian broker agent suffers.**
*World gap:* mandatory once-daily interactive login, morning token flush ~06:00–07:30 IST, **one active token per app** ([kite.trade forum](https://kite.trade/forum/discussion/13884/what-is-the-earliest-time-in-the-day-i-can-generate-the-access-token-for-the-day), [v3 user docs](https://kite.trade/docs/connect/v3/user/)). Every competitor either ignores it or automates it against Zerodha's guidance ([zicurojj "Fully Automated Authentication"](https://lobehub.com/mcp/zicurojj-kitetrading-mcp-server-claude)).
*One step from:* the sidecar **already** distinguishes it — `sidecar/services/brokers/kite.py:498-505` maps `TokenException` to `"kite: session expired — reconnect (daily token expiry)"`, and `sidecar/routers/brokers.py:185-188` turns that into **HTTP 419 `kite-session-expired`** with the comment *"so the frontend shows a 'reconnect' cue instead of a generic red error."* The frontend never reads it (see T1). Finishing that one wire turns a structural market annoyance into a moment where Vysted visibly behaves better than everything else.

**O13 — Open interest and broker-sourced options data.**
*World gap:* among Indian broker MCPs, only Angel One SmartAPI is described as serving *"quotes/candles/OI/Greeks"* plus *"margin/brokerage"* estimation with TOTP login (§3.2) — and India's retail centre of gravity is F&O.
*One step from:* Vysted has analytic Greeks already (`sidecar/routers/quant.py:12` — `POST /quant/option/greeks`, "analytic Greeks dashboard helper", plus `sidecar/services/quant/greeks`). What is missing is **market-observed** OI and an options chain: `sidecar/models/broker_reads.py` defines only positions/holdings/margins shapes (classes at lines 50, 64, 77, 90, 98, 110) — no OI field anywhere in `sidecar/` or `types/` outside the quant tests. Pairing computed Greeks with live OI is the F&O view no open competitor has done well.

**O14 — Licensed/first-party Indian fundamentals instead of a ninth scraper.**
*World gap:* screener.in has no official API and the gap is filled by ≥8 scrapers (§3.6), all fragile, all ToS-grey.
*One step from:* Vysted already parses SEC/XBRL with arbitrary-precision handling and ships a `sec_edgar_mcp` subprocess; `sidecar/routers/disclosures.py` and `sidecar/services/nse_symbol_change.py` show the India filing plumbing exists. Sourcing Indian fundamentals from **exchange filings + XBRL** rather than screener.in HTML is the only version of "data trust" that survives contact with a broken scraper.

**Opportunity count: 14.**

---

## TABLE-STAKES GAPS

Where this research shows Vysted is **behind** what a demanding Indian owner would already expect, with a code anchor for each.

**T1 — The 419 "session expired, reconnect" cue is emitted and never consumed. (high)**
The sidecar goes out of its way to distinguish the daily token expiry: `sidecar/services/brokers/kite.py:498-505` raises `"kite: session expired — reconnect (daily token expiry)"`, and `sidecar/routers/brokers.py:185-188` maps it to `HTTPException(status_code=419, detail="kite-session-expired")` with the stated intent *"so the frontend shows a 'reconnect' cue instead of a generic red error."* A grep for `419` across `src/` (`--include=*.ts --include=*.tsx`) returns **zero hits**, and `src/modules/broker-connect/BrokerReadsSection.tsx:52-53` catches everything into `setError(err instanceof Error ? err.message : "Could not read the account.")`. Every morning, every user sees a generic red error for the single most predictable event in the Indian broker day. Evidence the world treats this as structural: [kite.trade forum](https://kite.trade/forum/discussion/13884/what-is-the-earliest-time-in-the-day-i-can-generate-the-access-token-for-the-day) ("mandatory by the exchange that a user has to manually log in at least once a day").

**T2 — No price alerts. (high)**
Perplexity Finance ships "watchlists with AI briefings and price alerts" *for free* ([helmterminal.dev](https://helmterminal.dev/blog/perplexity-stock-research)). Vysted has a watchlist module (`src/modules/watchlist`) but a grep for `price_alert|priceAlert|createAlert` across `sidecar/`, `src/`, `types/` returns **zero hits**; the only `alert` hit in `sidecar/` is `sidecar/tests/test_search_extract.py`. A finance terminal without alerts is not a terminal.

**T3 — No scheduled / recurring research. (high)**
Perplexity ships **Tasks** ("run a recurring research query on a schedule"); OpenBB's whole 2026 pitch was long-running agents. Vysted has the durable-run engine (`sidecar/services/run_manager.py`, `sidecar/services/runs_store.py`, `sidecar/routers/runs.py`, `BudgetGuard`) but no trigger: a grep for `schedule|cron|recurring` across `sidecar/`, `src/`, `types/` hits only `sidecar/routers/earnings.py` (earnings *calendar*), `sidecar/services/fundamentals_warm.py` (cache warming) and `src/lib/layout-templates.ts`. The engine is built and unfired.

**T4 — No way to add an arbitrary MCP server. (high)**
MCP's entire premise is user-supplied servers, and the Indian ecosystem is populated (§3.1). Vysted hardcodes exactly two subprocesses (`src-tauri/src/openbb_mcp.rs`, `src-tauri/src/sec_edgar_mcp.rs`) and `sidecar/routers/mcp.py` exposes only `/mcp/status` (line 28) and `/openbb-mcp/status` (line 44). Zero hits for `mcp_servers|mcpServers|add_mcp|external_mcp|custom_mcp` repo-wide. For a product whose CLAUDE.md calls MCP "the universal tool layer", being MCP-server-**only** and not MCP-**client**-extensible is a positioning contradiction.

**T5 — No earnings-call transcripts. (medium)**
The benchmark transcribes Indian earnings calls **live, mid-call**, for free ([TechCrunch 2025-08-18](https://techcrunch.com/2025/08/18/perplexity-now-supports-live-earnings-call-transcripts-for-indian-stocks/): "live transcriptions of Indian public companies' quarterly earnings calls"). Vysted has `src/modules/earnings` and `sidecar/routers/earnings.py`, but every `transcript` hit in the repo is an **agent run transcript** (`sidecar/models/run.py`, `sidecar/services/runs_store.py`, `sidecar/routers/runs.py`), not an earnings call. For an India-first research product, the highest-signal Indian primary source is absent.

**T6 — No market-observed open interest or options chain. (medium)**
Angel One's MCP serves OI + Greeks; Kite Connect serves OI in quotes. Vysted computes Greeks analytically (`sidecar/routers/quant.py:12`) but carries no OI anywhere outside quant tests, and `sidecar/models/broker_reads.py` defines no OI-bearing shape (classes at lines 30–110 cover only provenance, leg positions, holdings, margins). "Bloomberg-level coverage" for an Indian audience without OI is a claim that will not survive a demo to an F&O trader.

**T7 — Broker onboarding is materially harder than the free alternative. (medium)**
Vysted: user obtains a Kite Connect API key + secret, logs in at kite.zerodha.com, pastes a `request_token` URL back (`sidecar/services/brokers/kite.py:14-18`, `:507`), and the `api_secret` crosses to the sidecar for the exchange. Zerodha's own free path: paste one URL into a config, no key, no secret, no install ([zerodha.com/products/mcp/](https://zerodha.com/products/mcp/)). Vysted is asking for more, from a paid (₹500/mo) prerequisite, to deliver less than the free option — for read-only use.

---

## Sources (distinct, 24)

1. https://openbb.co/blog/openbb-belongs-to-everyone/ — *fetched*
2. https://openbb.co/blog/introducing-workspace-mcp/ — *fetched*
3. https://openbb.co/pricing/ — *fetched*
4. https://docs.openbb.co/workspace/developers/ai-features/mcp-tools — *fetched*
5. https://docs.openbb.co/workspace/analysts/ai-features/copilot-basics — *fetched*
6. https://openbb.co/blog/building-ai-agents-for-openbb-workspace-with-pydantic-ai/ — *search snippet only*
7. https://docs.openbb.co/workspace/developers/agents-integration — *search result*
8. https://openbb.co/ai-vendor/ — *search result*
9. https://openbb.co/blog/sunsetting-openbb-terminal-why-how-and-what-now/ — *search result*
10. https://github.com/zerodha/kite-mcp-server (+ raw README) — *fetched*
11. https://zerodha.com/products/mcp/ — *fetched*
12. https://zerodha.com/z-connect/featured/connect-your-zerodha-account-to-ai-assistants-with-kite-mcp — *fetched*
13. https://zerodha.com/z-connect/updates/free-personal-apis-from-kite-connect — *fetched*
14. https://kite.trade/docs/connect/v3/user/ + forum threads 734 / 4108 / 7759 / 13884 / 14806 / 15015 — *search snippets of forum text*
15. https://support.zerodha.com/category/trading-and-markets/general-kite/kite-api/articles/historical-data-and-live-market-data-payment-plan — *search result*
16. https://helmterminal.dev/blog/perplexity-stock-research — *fetched*
17. https://techcrunch.com/2025/08/18/perplexity-now-supports-live-earnings-call-transcripts-for-indian-stocks/ — *fetched*
18. https://chartlibrary.io/blog/financial-mcp-servers-compared — *fetched*
19. https://docs.financialdatasets.ai/mcp-server — *fetched*
20. https://www.solosoft.dev/post/fincept-terminal-open-source-2026/ — *fetched*
21. https://github.com/topics/bloomberg-alternative — *fetched*
22. https://github.com/Sparker0i/indian-stock-mcp-agent — *fetched*
23. https://glama.ai/mcp/servers/adibhattar95/upstox-mcp-server ; https://lobehub.com/mcp/sharuniyer-indian-broker-mcp ; https://github.com/Sundeepg98/kite-mcp-server ; https://dev.to/govind_sisara/indian-stock-market-mcp-the-best-mcp-servers-for-nse-bse-data-2026-p28 — *search results, Indian broker MCP inventory*
24. https://github.com/ronyv89/screener-mcp + Apify screener.in/NSE-BSE MCP actors (scrapyx, solidcode, shashwattrivedi, data_daemon, fascinating_lentil, fingolfin) — *search results*

**Fetch honesty note:** items marked *fetched* were retrieved and their quoted fragments are verbatim from the fetch. Items marked *search snippet / search result* were surfaced by search and are reported as described observations, not verbatim page text. The two OpenBB docs pages returned summaries that explicitly flagged absent information (transports, auth, BYOK, query limits); those absences are reported as documentation gaps rather than as claims about the product.
