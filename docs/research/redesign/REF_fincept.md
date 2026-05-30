# Reference Study: Fincept Terminal (`fincept-qt`)

Engineering teardown of the Fincept Terminal v4 reference repo at
`/Users/lokavyasingh/Documents/dev/reference/FinceptTerminal`. Branding,
memecoin/wallet noise, and the aggressive AGPL/commercial license theatre are
ignored. This is about the architecture — what they built, what's real, what's
vapor, and what each thing teaches Vysted.

> **Stack at a glance.** Pure native **C++20 + Qt6.8** desktop monolith, single
> binary, **embedded Python 3.11** for analytics + agents. No Electron, no web
> runtime. The opposite axis from Vysted (Tauri + Next.js + Python sidecar),
> which makes it a useful contrast: same product category, inverted UI tech, and
> a far heavier native core. Source: `README.md`, `fincept-qt/CMakeLists.txt`.

---

## 0. Real vs aspirational — read this first

The repo mixes a genuinely large, working C++ core with **stale/marketing
READMEs** that over-claim. Be skeptical of their prose; trust the source tree.

| Claim (in their docs) | Reality in the tree | Verdict |
|---|---|---|
| "16 broker integrations" (`README.md:55`) | **22** broker dirs under `src/trading/brokers/` (zerodha, angelone, upstox, fyers, dhan, groww, kotak, iifl, fivepaisa, aliceblue, shoonya, motilal, ibkr, alpaca, tradier, saxo, samco, tradejini, flattrade, paytm, icicidirect, metaapi) | Under-claimed; real |
| "100+ data connectors" (`README.md:54`) | **117** connectors registered across 10 `connectors/*.cpp` files; the `ConnectorRegistry.h` header comment still says "78" | Real, registry comment stale |
| "37 agents… custom FinAgent Core framework" (`README.md:53`, `scripts/agents/README.md`) | Agents are **JSON config files**, not the per-investor Python classes the README lists. `scripts/agents/README.md` cites `base_agent.py`, `llm_executor.py`, `agent_manager.py`, `warren_buffett_agent.py`, `agno_trading/` — **none exist**. Runtime is a config-driven wrapper over the third-party **Agno** framework, not bespoke | README ~70% aspirational; runtime real but mis-described |
| `docs/agentic-research/README.md` describes `design/03_architecture.md`, `papers/SUMMARY.md`, `04_impl_plan.md`, etc. | **Only the README exists** — every referenced design/papers/patterns file is absent. It's a research-plan index pointing at deleted/never-committed outputs | Pure aspiration |
| "30+ agents powered by local LLMs (Ollama)" | Multi-provider is real (OpenAI/Anthropic/Gemini/Groq/DeepSeek/Ollama/Fincept-hosted); Ollama is one of many. Agent count by config: 11 trader/investor + 16 finagent_core configs + geopolitics/economic sets | Real, "Ollama-only" framing stale |

**Lesson for Vysted:** their docs rot because they ship marketing copy as
engineering docs and never reconcile. Vysted's `CLAUDE.md` "living document"
discipline + per-phase handoffs are the antidote — but the failure mode to avoid
is exactly this: a README that lists files/agents that don't exist. Audit doc
claims against the tree at release time (Vysted already greps for stale version
strings; extend that to "do the files this doc names actually exist").

---

## 1. Feature breadth (panels / modules / data domains)

This is the single most impressive axis. **55 screen modules** under
`fincept-qt/src/screens/`, each a dockable panel. Inventory (verbatim dir names):

- **Markets & equity:** `markets`, `equity_research`, `equity_trading`, `watchlist`,
  `dashboard`, `sectors` (via services), `asia_markets`, `akshare` (China data)
- **Derivatives & options:** `derivatives`, `fno` (futures & options),
  `options` (service), options strategy builder (`trading/OptionsStrategyBuilder.cpp`)
- **Quant:** `quantlib` (18 modules per README), `ai_quant_lab` (ML/factor/HFT/RL),
  `backtesting`, `algo_trading`, `surface_analytics`, `trade_viz`
- **Crypto:** `crypto_center`, `crypto_trading` (Kraken + HyperLiquid WebSocket)
- **Macro & gov:** `economics`, `dbnomics`, `gov_data`, `geopolitics`, `maritime`
  (vessel tracking), `relationship_map`, `surface_analytics`
- **Prediction markets:** `polymarket`, `alpha_arena` (model competition arena)
- **Portfolio & M&A:** `portfolio`, `ma_analytics` (DCF, merger model, LBO),
  `alt_investments`
- **AI:** `ai_chat`, `agent_config`, `mcp_servers`, `node_editor` (visual workflows)
- **Productivity / shell:** `code_editor`, `excel`, `file_manager`, `notes`,
  `report_builder`, `data_mapping`, `data_sources`, `forum`, `docs`, `devtools`,
  `settings`, `profile`, `auth`, `setup`, `recovery`, `launchpad`, `action_center`

**Data domains via 117 connectors** (`src/screens/data_sources/connectors/`):
- Market data (19): Yahoo, Alpha Vantage, Finnhub, IEX, Twelve Data, Quandl,
  Binance, Coinbase, Kraken, CoinGecko, Tiingo, Intrinio, Reuters, Tradier…
- **Generic infra connectors** — this is the surprise: it's a *universal data
  hub*, not just finance APIs. Relational DBs (Postgres, MySQL, Snowflake,
  CockroachDB…), NoSQL (Mongo, Redis, Cassandra, DynamoDB, Neo4j…), time-series
  (InfluxDB, QuestDB, kdb+, ClickHouse, Prometheus…), cloud storage (S3, GCS,
  Azure Blob, R2…), file formats (CSV, Parquet, Avro, ORC, Feather…), streaming
  protocols (REST, GraphQL, WebSocket, gRPC, Kafka, MQTT, NATS…), open banking
  (Plaid, MX, TrueLayer…), search/warehouse (Elasticsearch, BigQuery, Redshift,
  Databricks…), and alternative data (RavenPack, SafeGraph, Thinknum…).

**Lesson for Vysted:**
1. **The "universal data connector" idea is the strongest steal.** Vysted is
   BYOK + local-first + max-extensibility. A `DataSourcesScreen` where a user
   wires their *own* Postgres / S3 / Kafka / Parquet into the terminal — not just
   curated finance feeds — is directly on Vysted's "the data isn't the limit"
   positioning, and Vysted's plugin `data` capability is the natural home for it.
   Fincept proves the breadth is achievable with a flat self-registering registry.
2. **Breadth without depth is a trap.** 55 screens is a lot of surface; many are
   thin (the geopolitics/maritime/relationship-map panels lean on LLM prose over
   hard data). Vysted's "no Phase 2 / full-scope" DNA should resist breadth-for-
   breadth. Pick the domains where Vysted has *real* data depth (Phase 6 macro/SEC/
   QuantLib already do) and let plugins fill the long tail.

Cite: `src/screens/` (55 dirs), `src/screens/data_sources/connectors/*.cpp`
(per-file domain comments), `src/services/` (44 service dirs mirroring screens).

---

## 2. Agent personas + agentic-research design

### 2.1 Persona model — config-driven, Agno-backed

Personas are **JSON, not code**. Example structure (`scripts/agents/
TraderInvestorsAgent/configs/agent_definitions.json`, 11 investors — Buffett,
Graham, Lynch, Munger, Klarman, Marks, Greenblatt, Einhorn, Miller, Eveillard,
Whitman):

```json
{
  "id": "warren_buffett_agent",
  "name": "Warren Buffett Investment Agent",
  "description": "...moats, owner earnings, capital allocation...",
  "category": "TraderInvestorsAgent",
  "capabilities": ["moat_analysis", "owner_earnings", ...],
  "config": {
    "model": {"provider": "openai", "model_id": "gpt-4-turbo", "temperature": 0.3},
    "instructions": "You are a value-investing analyst in the Buffett tradition...
                     Every recommendation has a named moat source, a returns-on-
                     capital number, a management check, and a valuation. ...
                     INPUTS to gather: yfinance/financial_datasets: 10y of revenue...
                     FRAMEWORK (every section required): 1. MOAT: name it... "
  }
}
```

The **instructions are a rigorous analyst rubric**, not personality cosplay —
"you are a business analyst, not a personality cosplay" is literally in the
Buffett prompt. Each persona is just `(model config + tool allow-list + a long
structured system prompt)`. There are 16 more `finagent_core/configs/*.json`
(macro cycle, central bank, currency strategist, sentiment, supply chain,
behavioral finance, institutional flow, polymarket risk, Renaissance, etc.).

**Runtime:** `CoreAgent` (`scripts/agents/finagent_core/core_agent.py`) is "one
agent to rule them all" — a single configurable class that instantiates a
per-`(user_id, agent_id)` **`PersonaRuntime`** (`persona_runtime.py`) wrapping an
**Agno `Agent`** plus memory/storage/knowledge/guardrails/tracing modules. The
"100+ tools" and "40+ providers" are Agno's, not theirs (`persona_runtime.py`
imports `agno.memory`, `agno.storage.sqlite`; `__init__.py` header says "Pure
Agno Implementation").

### 2.2 Multi-agent orchestration

Three coexisting patterns:
- **`SuperAgent` triage router** (`super_agent.py`) — LLM classifies a query into
  one of 9 intents (trading/portfolio/analysis/risk/news/geopolitics/economics/
  research/general) and routes to the matching persona. **LLM-first with a keyword
  fallback** for offline/no-key — clean degradation.
- **`deepagents` orchestrator** (`scripts/agents/deepagents/`) — a LangChain-style
  multi-subagent system (research / data-analyst / trading / risk-analyzer /
  portfolio-optimizer / backtester / reporter / macro-economist roles). When the
  LLM supports tool-calling it uses the `deepagents` lib; when not (Fincept-hosted
  LLM, Ollama) it falls back to `FinceptOrchestrator` — **pure HTTP + prompt-loop
  that produces the identical output schema** (`orchestrator.py`). Single best
  idea here: *same output contract regardless of backend capability*.
- **Hedge-fund org sims** (`scripts/agents/hedgeFundAgents/`) — only Renaissance
  is actually built out: a multi-persona *organization* with `organization/
  hierarchy.py`, `personas.py`, `communication.py`, and a `tracing/
  workflow_tracer.py`. The other 7 funds named in the README are config stubs.

### 2.3 The "true agentic" upgrade (the real gem)

`scripts/agents/finagent_core/agentic/` — **2.6 kLOC of genuinely good durable-
agent engineering**, the part most worth stealing:

- **`runner.py` (791 LOC) `AgenticRunner`** extends a `ResumableTaskRunner` with
  per-step event emission + cooperative pause/cancel. Control signalling is
  **DB-status-polled between steps** (a sibling subprocess flips
  `agent_tasks.status` to `pause_requested`/`cancel_requested`; the running loop
  re-reads it). Crash-resume works because plan + completed steps persist in a
  SQLite `agent_tasks` table — LangGraph-style `(thread_id, step, state_blob)`
  checkpointing, hand-rolled.
- **`budget.py` `BudgetGuard`** — four independent ceilings (max_tokens,
  max_cost_usd, max_wall_s, max_steps), first breach aborts with a `budget_stop`
  event. Has a conservative `_PRICING_PER_1K` table per model. This is the
  long-running-agent safety primitive Vysted lacks.
- **`reflector.py` `Reflector`** — Reflexion-pattern (arXiv:2303.11366) post-step
  LLM critic that returns `continue | replan | question | done`. Best-effort:
  any error falls back to `continue` so a flaky critic never breaks a run.
- **`skill_library.py`** — Voyager-style persistent recipe store; top-K semantic
  search (FTS5 with LIKE fallback) injects matching past recipes into the planner
  prompt. **`archival_memory.py`** (Letta/MemGPT tier-3 durable facts),
  **`reflexion_store.py`** (per-step critiques seasoning the next plan),
  **`scheduler.py`** (cron-ish DSL: "every 30m", "daily 09:30", "weekday 16:00"),
  **`eval_harness.py`** (eval cases), **`daemon.py`**.

The C++ side (`src/services/agents/AgentService.h`) exposes the **whole lifecycle**:
`start_task / resume_task / pause_task / cancel_task / get_task / list_tasks /
reply_to_question` (HITL), `schedule_create_task` + cron, plus read-only library
inspection (`skills_list`, `archival_list`, `reflexion_list`). Per-step events
stream over both a Qt signal AND a DataHub topic `task:event:<task_id>`. UI is a
dedicated **`AgenticTasksPanel`** + `PlannerViewPanel` (`src/screens/agent_config/`).

**Lessons for Vysted (high value):**
1. **Vysted's agent loop is single-turn-ish; Fincept's durable runner is the
   upgrade path.** Vysted already has `invoke_agent` + the tool schema catalog
   (per the Phase-10 gotcha). The missing layer is exactly what `agentic/` adds:
   SQLite-checkpointed resumable tasks, a budget guard, a reflexion critic, HITL
   pause-for-question, and a scheduler. The `(task_id, step, state_blob)` on
   SQLite design is cheap and maps onto Vysted's sidecar persistence model.
2. **BudgetGuard is a §6.5-adjacent safety primitive.** Vysted gates *broker
   execution* with defense-in-depth; it should gate *autonomous agent spend* the
   same way. A token/$/wall-clock/step ceiling that hard-aborts is the agentic
   analog of the kill switch — and it's ~150 LOC.
3. **Personas-as-JSON-with-a-rubric, not personas-as-code, is the right call.**
   Vysted already ships agent JSONs (`copilot.json`, the Buffett/Dalio/… roster).
   Fincept validates that the *quality lever is the structured rubric prompt*
   ("every section required: MOAT / RETURNS ON CAPITAL / VALUATION"), not bespoke
   Python per investor. Keep Vysted's agents declarative; invest in rubric depth.
4. **Same output contract across tool-calling vs prompt-loop backends** (their
   `deepagents` ↔ `FinceptOrchestrator` split) is worth copying for BYOK: a user's
   weak local Ollama model should produce the same shaped result as Claude, just
   lower quality. Vysted's adapter-per-provider design can enforce this.

Cite: `scripts/agents/finagent_core/{core_agent.py, super_agent.py,
persona_runtime.py}`, `scripts/agents/finagent_core/agentic/*.py`,
`scripts/agents/deepagents/{orchestrator.py, subagents.py, agent.py}`,
`src/services/agents/AgentService.h`, `src/screens/agent_config/`.

---

## 3. Data connectors + credentials hub

### 3.1 Connector registry

`src/screens/data_sources/ConnectorRegistry.h` — a singleton with
**static-init self-registration**: each `connectors/*.cpp` file defines a
`QVector<ConnectorConfig>` and registers it; the registry is effectively
read-only after `QApplication::exec()`. A `ConnectorConfig` carries:
`id, name, icon glyph, color, description, hasApiKey, requiresAuth, fields[]`
where each field is `{id, label, FieldType (Text/Password/Select/...), placeholder,
secret, default, options[]}`. The UI (`DataSourcesScreen`) renders a generic
config dialog (`ConnectionConfigDialog`) purely from this schema, tests the
connection (`ConnectionTester`), and supports `ImportExportConnections`.

### 3.2 Credentials hub / secure storage

`src/storage/secure/SecureStorage.h` — **local credential store: SQLite +
AES-256-GCM**. Key is derived once per process from
`QSysInfo::machineUniqueId()` + a fixed app salt, SHA-256'd. Per-row random 96-bit
IV + 128-bit GCM tag (tamper → decryption fails, not corrupt plaintext). The
header is refreshingly honest about its threat model: protects against casual
grep, profile-copy-to-another-machine, and bit-flips; **does NOT** protect against
another process running as the same user, kernel-memory forensics, or targeted
malware. Notes AES-NI / ARM-crypto hardware accel keeps per-call cost sub-1ms.

Plus `src/core/keys/KeyConfigManager` for API-key config and `src/auth/`
(PinManager, InactivityGuard, SessionGuard, SecurityAuditLog) for app-level lock.

**Lessons for Vysted:**
1. **The generic-config-dialog-from-schema pattern is the credentials-hub design
   Vysted should adopt.** A connector/broker declares its credential fields
   (label, type, `secret: true`) and the host renders the form, masks secrets,
   and round-trips test-connection — zero per-connector UI code. Vysted's
   `IBroker`-style `BrokerProfile.credential_fields` (below) already does this for
   brokers; generalize it to all data sources and into the plugin `data` contract.
2. **Their AES-GCM-on-SQLite is a *weaker* model than Vysted's OS-keychain
   (Tauri Rust `keychain_*`).** Machine-ID-derived keys are crackable by any same-
   user process; the OS keychain isn't. **Do not regress to this.** But steal the
   *honesty*: Fincept documents exactly what its store does and doesn't protect.
   Vysted should keep an equivalent written threat model for its BYOK keychain
   flow (it already has the renderer→keychain→request-header pattern documented).
3. **Import/export of connections** (`ImportExportConnections`) is a nice
   portability touch for a local-first BYOK app — lets users move their wired-up
   data sources between machines. Low cost, on-positioning for Vysted.

Cite: `src/screens/data_sources/{ConnectorRegistry.h, DataSourceTypes.h,
ConnectionConfigDialog.cpp, ConnectionTester.cpp, ImportExportConnections.cpp}`,
`src/storage/secure/SecureStorage.h`, `src/core/keys/`, `src/auth/`.

---

## 4. Broker integrations

**22 brokers** under `src/trading/brokers/`, all behind one abstract base:
`src/trading/BrokerInterface.h` → `class IBroker`. This is the **best single file
in the repo for Vysted to study** because it's exactly the broker-execution-plugin
contract problem Vysted faces in Phase 5 / §6.5.

`IBroker` design highlights:
- **`BrokerProfile profile()`** — single source of truth per broker for the UI:
  `id, display_name, region, currency, credential_fields[], exchanges[],
  product_types[], supports_bracket_order, has_native_paper,
  default_paper_balance, default_watchlist[], brokerage_info`. The order form and
  credentials dialog render entirely from this — *the same schema-driven UI idea
  as connectors*, applied to brokers.
- **Pure-virtual core**: `exchange_token`, `place_order`, `modify_order`,
  `cancel_order`, `get_orders`, `get_positions`, `get_holdings`, `get_funds`,
  `get_quotes`, `get_history`. Everything else (GTT orders, market depth, option
  chain, calendar/clock, ~30 historical-bars/quotes/trades variants, basket
  margin) is a **virtual with a `"Not supported"` default** — so a thin broker
  implements ~10 methods and a rich one (Alpaca) overrides 40+.
- **Shared fallback logic in the base class**: `cancel_all_orders` (walks the
  order book), `close_all_positions` / `close_position` (places market counter-
  orders), `get_multi_quotes` (sequential fallback), and an
  `estimate_order_margin()` free function (20% intraday / 100% delivery / 10%
  futures / premium for option buys / 15% SPAN for option sells). Brokers without
  a native margin API inherit the heuristic.
- **Credentials**: `CredentialField` enum (ApiKey, ApiSecret, AuthCode,
  Environment, ClientCode, Password, TotpSecret, UserId) so per-broker auth
  (Zerodha TOTP auto-login, AngelOne separate client code, Alpaca live/paper
  toggle) is expressed declaratively. Some brokers (`zerodha/Totp.cpp`,
  `ZerodhaAutoLogin.cpp`) ship full auto-login flows.

Crypto exchanges are separate (`src/trading/exchanges/{kraken,hyperliquid}/`) with
their own WebSocket account/data streams. There's a full execution stack around
this: `PaperTrading`, `SmartOrderEngine`, `OrderValidator`, `OrderMatcher`,
`RateLimiter`, `LatencyTracker`, `AccountDataStream`, `WebhookListener`,
`UnifiedTrading`.

**Lessons for Vysted:**
1. **`IBroker` + `BrokerProfile` is the contract Vysted's broker-execution
   plugins want.** Vysted's blueprint puts global broker execution in v1.0 behind
   the §6.5 safety layer. Fincept's pattern — *one abstract interface, a declarative
   `BrokerProfile` driving all UI, virtuals-with-safe-defaults so partial brokers
   are first-class, and shared close-all/cancel-all/margin fallbacks in the base*
   — is a proven shape Vysted should mirror in its broker plugin contract. The
   "every advanced method defaults to `Not supported`" convention is how you ship
   22 brokers without 22× the surface.
2. **Declarative credential enums + per-broker auto-login** is the right answer to
   "every Indian broker has a different login dance." Vysted already special-cases
   Kite static-IP + manual request-token paste (Phase 10 gotcha); Fincept shows
   the generalized version (TOTP secret, client code, environment toggle as
   first-class credential field types).
3. **CAUTION — this is where Fincept is *least* safe and Vysted must NOT copy.**
   `IBroker::place_order` is on the *same* interface as `get_quotes`. There's an
   `OrderValidator` but **no §6.5-style append-only audit log, no type-level
   "confirmed-only execution" gate, no read-only-by-construction provider class.**
   Vysted's defense-in-depth (type gate + DB-enforced append-only audit +
   grep-able audit test, per the v0.5.0 §6.5 precedent) is materially stronger.
   Steal Fincept's *ergonomics* (the interface shape, the profile-driven UI), keep
   Vysted's *safety architecture*.

Cite: `src/trading/BrokerInterface.h`, `src/trading/brokers/*/` (22 dirs),
`src/trading/exchanges/{kraken,hyperliquid}/`, `src/trading/{PaperTrading,
SmartOrderEngine,OrderValidator,RateLimiter,UnifiedTrading}.cpp`.

---

## 5. UI/UX structure + the (missing) plugin model

### 5.1 Docking shell

Qt + **Advanced Docking System (ADS)**, driven by `src/app/DockScreenRouter.h`.
Every screen is wrapped in a `CDockWidget` that can dock / tab / float /
auto-hide / tear-off to a new monitor. Strong primitives:
- **Lazy factories** — screens register a `std::function<QWidget*()>` factory;
  the heavy widget is built only on first navigation (avoids constructing all ~46
  screens at boot). A `suppress_visibility_materialize_` guard prevents
  `restoreState()` from eagerly instantiating everything.
- **Multi-window** — `tear_off_to_new_frame`, `move_panel_to_frame`,
  `duplicate_panel` (synthetic `<base>#dup<N>` ids), `tile_2x2`, per-monitor
  placement. Layout + per-panel state persist by `PanelInstanceId` (UUID).
- **Symbol-group linking** — `wrap_with_group_badge` + `GroupBadge`: panels can
  join a colored symbol group so changing the ticker in one linked panel updates
  all of them (Bloomberg-style "linked launchpad" groups).
- **Stateful screens** — `IStatefulScreen` save/restore so a duplicated or moved
  panel reopens with the same ticker/watchlist loaded.

Theme: `src/ui/theme/` — `ThemeManager`, `Theme`, `ThemeTokens.h`, `StyleSheets`
(token-based, like Vysted's `tokens.css` approach). Plus a deep `src/ui/`
component library (charts, tables, command palette, notifications, markdown,
pushpins, workspace).

### 5.2 The DataHub (their best architectural idea)

`src/datahub/DataHub.h` — an in-process **pub/sub bus** with typed topics that
*everything* streams through: quotes, order books, news, vessel tracks, broker
ticks, geopolitical events, **agent outputs, and LLM token streams**. Topic
naming is a consistent `<family>:<sub>:<id>[:<qualifier>]` grammar
(`market:quote:AAPL`, `ws:kraken:ticker:BTC-USD`, `news:general`,
`broker:<id>:<acct>:positions`, `agent:stream:<run_id>`, `llm:session:<id>:stream`).
A `Producer` interface + `TopicPolicy` (`min_interval_ms` rate gate,
`max_requests_per_sec`, push-only vs pull-through, coalescing of high-rate topics).
Per-run topics (`agent:output:<run_id>`) are **retired on completion** to bound
memory. Docs: `fincept-qt/docs/agents/datahub-guide.md`.

### 5.3 MCP + node editor — the actual "extensibility"

There is **no first-party plugin/extension SDK**. Every screen, broker, and
connector is **compiled into the monolith** (`grep` for plugin/extension dirs →
nothing). Extensibility comes from two other directions:
- **MCP** (`src/mcp/`) — Fincept is both an MCP *client* (can install external MCP
  servers via a `McpMarketplace` catalog: Fetch, Time, Git, SQLite, … each a
  `{command, args, env_keys}` preset) **and** an MCP *server* exposing ~81 internal
  tool modules (`src/mcp/tools/*.cpp`) to LLM callers — including 4 generic
  **DataHub tools** (`datahub_list_topics / peek / request / subscribe_briefly`)
  that let an agent observe *any* live stream by topic name.
- **Node editor** (`src/screens/node_editor/`) — visual workflow builder (canvas/
  palette/properties/toolbar) for chaining tools/agents into automation pipelines.

**Lessons for Vysted:**
1. **The DataHub is the thing to seriously consider adopting.** Vysted's modules
   each own their data fetching; a typed pub/sub bus with a topic grammar + a
   `TopicPolicy` rate/coalesce layer would (a) decouple producers from panels, (b)
   give the AI agent a *uniform observation surface* over every live stream (their
   `datahub_subscribe_briefly` "watch this topic for 5s" tool is genuinely clever
   for letting an agent reason about a *volatile* feed, not just a snapshot), and
   (c) bound memory via retire-on-completion for per-run topics. This fits Vysted's
   plugin `data` + `agents` capabilities cleanly. **Biggest single architectural
   idea worth lifting.**
2. **MCP-as-extensibility is the model Vysted is already aligned with.** Fincept
   chose MCP (client marketplace + internal tool server) *instead of* a bespoke
   plugin SDK — and it's the weaker choice for a *UI* extension story (you can't
   ship a new panel via MCP). **Vysted's `VystedPlugin` contract is strictly
   better positioned**: it has a real panel/command/node/control-plane capability
   surface Fincept lacks. Lesson: Vysted should keep MCP for *tool* extensibility
   but not abandon the typed plugin contract for *UI/data* extensibility — that's
   the gap Fincept never closed (monolith of 55 compiled screens).
3. **Lazy panel factories + per-instance UUID state + symbol-group linking** are
   directly portable to Vysted's dockview host. Vysted already lazy-mounts
   dockview after modules register; the *symbol-group linking* (change ticker in
   one panel → all linked panels follow) is a high-value UX feature Vysted's
   "AAPL anchor cockpit" convention would benefit from and doesn't have yet.
4. **Multi-window tear-off to a second monitor** is table-stakes for a "terminal"
   and Fincept nails the hard parts (close-and-recreate move preserving UUID +
   group membership). Vysted's Tauri multi-window story should learn from the
   PanelInstanceId-preservation approach rather than live cross-window reparenting.

Cite: `src/app/DockScreenRouter.h`, `src/datahub/{DataHub.h, Producer.h,
TopicPolicy.h}`, `fincept-qt/docs/agents/datahub-guide.md`, `src/mcp/
{McpManager.h, McpMarketplace.h, tools/*.cpp}`, `src/screens/node_editor/`,
`src/ui/theme/`, `src/ui/`.

---

## 6. Top transferable lessons, ranked

1. **Adopt a typed in-process pub/sub DataHub** with a topic grammar + policy
   layer, and expose generic `peek / subscribe_briefly` tools to the agent. This
   is Fincept's best idea and maps onto Vysted's plugin data + agents contract.
   (`src/datahub/`, `docs/agents/datahub-guide.md`)
2. **Steal the durable-agent layer wholesale** — SQLite-checkpointed resumable
   tasks + BudgetGuard + Reflexion critic + HITL pause-for-question + scheduler.
   It's ~2.6 kLOC of clean Python that directly upgrades Vysted's agent loop.
   (`scripts/agents/finagent_core/agentic/`)
3. **Generalize the schema-driven config-dialog pattern** (used for both
   connectors and brokers) into Vysted's credentials hub: a source declares
   `credential_fields[]`, the host renders/masks/tests — zero per-source UI.
   (`BrokerInterface.h::BrokerProfile`, `ConnectorRegistry.h`)
4. **Copy `IBroker`'s ergonomics, keep Vysted's §6.5 safety.** Abstract interface
   + declarative `BrokerProfile` + virtuals-default-to-`Not-supported` + shared
   close-all/margin fallbacks. But Fincept has *no* append-only audit / type-gated
   execution — Vysted's defense-in-depth is the safety layer Fincept is missing.
   (`src/trading/BrokerInterface.h`)
5. **Universal data connectors** (DBs, cloud, files, streaming protocols — not
   just finance APIs) is on-positioning for Vysted's "the data isn't the limit"
   and belongs in the plugin `data` capability. (`connectors/*.cpp`, 117 entries)
6. **Personas-as-JSON-with-a-rubric** validates Vysted's declarative agent design;
   the quality lever is the structured analyst prompt, not per-investor code.
   (`TraderInvestorsAgent/configs/agent_definitions.json`)
7. **Honest threat-model docs + reconcile-docs-with-tree.** Fincept's
   `SecureStorage.h` threat model is exemplary; its agent READMEs (which list
   non-existent files) are the anti-pattern. Vysted's living-doc discipline should
   include "does this doc name files that exist?" at release time.

---

## 7. What NOT to copy

- **AES-GCM-on-SQLite credential store** (machine-ID-derived key, crackable by
  same-user processes) — Vysted's OS keychain is strictly safer; do not regress.
- **Broker execution without an audit log / type-level execution gate** — Vysted's
  §6.5 architecture is the whole point of the safety layer; Fincept skips it.
- **Compiled-in-monolith extensibility** (55 hard-coded screens, no plugin SDK) —
  the exact thing Vysted's `VystedPlugin` contract exists to avoid.
- **Marketing-as-engineering-docs** — the `scripts/agents/README.md` and
  `docs/agentic-research/README.md` describe systems/files that aren't in the tree.
- **The aggressive license/enforcement theatre** in the README (irrelevant to
  Vysted's AGPL-3.0 + commercial dual-license, which is already a Locked decision).
