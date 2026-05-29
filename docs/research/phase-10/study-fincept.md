# Study: Fincept Terminal — adoptable architecture for Vysted (Phase 10)

**Date:** 2026-05-29
**Author:** senior-engineer study (headless)
**Subject:** `github.com/Fincept-Corporation/FinceptTerminal` (shallow clone → `/tmp/study-fincept`)
**Method:** read actual source in `fincept-qt/` (Qt6/C++20 + embedded Python), cited file:line. Branding/memecoin baggage ignored. Compared against Vysted's current source (`src/`, `sidecar/`, `types/`).

> **What this is.** Fincept Terminal v4 is a native **C++20 / Qt6** desktop app with **embedded Python** for analytics — a different stack from Vysted (Tauri + Next.js + Python sidecar). It is NOT the old DearPyGUI Python version. The *architecture patterns* port directly even though the language doesn't. It is enormous: **55 screens**, ~78 data connectors, 21 brokers, 37 AI personas. It is the right thing to mine for breadth and registry patterns.

---

## 0. Stack reality check (so we don't cargo-cult)

- App is `fincept-qt/` — Qt6 widgets, C++20, CMake. `README.md` "pure native C++20 desktop application … embedded Python for analytics".
- C++ side owns UI + service singletons; Python (`scripts/`) owns agents, analytics, quant. The C++ `AgentService` shells out to `scripts/agents/finagent_core/main.py` via a `PythonRunner` / `QProcess` + stdin bridge (`src/services/agents/AgentService.h:17-21`, `AgentService.h:178-181`). **This is structurally identical to Vysted's Tauri-frontend ↔ Python-sidecar split** — C++ ServiceSingleton == our Zustand store + REST client; QProcess stdin == our FastAPI HTTP. Every pattern below maps cleanly.
- Result emission is signal-based with a `request_id` correlator so concurrent panels ignore each other's results (`AgentTypes.h:39-46`, `AgentService.h:34-36`). Vysted's equivalent is per-request React state; the *correlator* idea is worth stealing for the copilot when multiple chats run.

---

## 1. AI agent persona system  ⭐ highest-value extraction

### What Fincept does

**Personas are declarative JSON files**, discovered at runtime, merged with DB-saved custom agents, grouped by category, cached, and surfaced in a 3-panel editor. This is the single most directly-adoptable thing in the repo and Vysted already has the skeleton of it.

**Persona definition format** (`scripts/agents/finagent_core/configs/*.json`, 16 first-party files; `scripts/agents/TraderInvestorsAgent/configs/agent_definitions.json`; README claims 37 total across categories):

```jsonc
{
  "id": "renaissance_technologies",
  "name": "Renaissance Technologies Medallion Fund",
  "description": "...",          // one-line, shown as subtitle
  "category": "hedgeFundAgents",  // drives the category filter dropdown
  "version": "2.0.0",
  "provider": "local",            // local | custom | (provenance)
  "capabilities": ["signal_discovery", "risk_assessment", ...],  // searchable tags
  "config": {
    "model": { "provider": "openai", "model_id": "gpt-4o",
               "temperature": 0.7, "max_tokens": 4096 },  // PER-AGENT model + sampling
    "instructions": "…long system prompt…",
    "tools": ["yfinance", "openbb", "tavily", ...],        // declared tool allow-list
    "output_format": "markdown",                            // text | json | markdown
    "memory": true, "agentic_memory": true,                 // capability flags
    "scoring_weights": { "moat_analysis": 0.30, ... },      // structured scoring rubric
    "data_sources": {                                       // required keys/metrics
      "required_api_keys": ["FINANCIAL_DATASETS_API_KEY"],
      "financial_metrics": ["ROE", "D/E"], "years_of_data": 10 },
    "output_schema": { "type": "InvestmentSignal",          // structured-output contract
      "fields": { "signal": "bullish|bearish|neutral", "confidence": "float (0-1)" } },
    "knowledge_base": "buffett_philosophy",
    "ui_parameters": { "advanced_options": ["knowledge_base", ...] },  // drives the editor form
    "agents": [ {"id":"signal_scientist","name":"Signal Scientist","role":"…"}, ... ],  // sub-agents
    "teams":  [ {"id":"research_team","name":"Research Team","members":[...]}, ... ]
  }
}
```

The **system prompts are genuinely good** and worth reading for prompt-craft: the Buffett (`TraderInvestorsAgent/configs/agent_definitions.json`) and Currency Strategist (`finagent_core/configs/currency_strategist_agent.json`) prompts are 300–600 words, framework-first, with explicit "BEFORE you answer confirm…", "INPUTS to gather… (named tools)", "FRAMEWORK (every section required)", "OUTPUT (markdown headers)", and a hard "DO NOT" list. They forbid roleplay/quote-invention and force named numbers. This is exactly the research-lab voice Vysted's CLAUDE.md mandates.

**Discovery + surfacing** (`src/services/agents/AgentService_Discovery.cpp:37-170`):
1. `discover_agents()` checks a cache (`agents:list`, TTL 5 min — `AgentService.h:158`), discards an empty cache and re-discovers.
2. On miss, `run_python_light("discover_agents")` enumerates the bundled JSON.
3. **Merges DB-saved custom agents** (`AgentConfigRepository::instance().list_all()`, `AgentService_Discovery.cpp:120-145`) — skipping ids already present, tagging them `provider:"custom"`.
4. Builds `cat_counts` → `QVector<AgentCategory>{name, count}` so the UI shows category chips with counts.
5. Caches the merged result and emits `agents_discovered(agents, categories)`.

**Runtime** is an LRU `PersonaRegistry` keyed by `(user_id, agent_id)`, cap 8, env-tunable, evict-closes runtimes (`scripts/agents/finagent_core/persona_registry.py:1-84`). Each `PersonaRuntime.build()` (`persona_runtime.py:133`) wires memory/storage/knowledge/agentic-memory backends from the config flags.

**Surfacing in UI** — `AgentConfigScreen` has view modes `{Agents, Create, Teams, Workflows, Planner, Tools, Chat, System, Agentic}` (`AgentTypes.h:13`). The **Agents view is a 3-panel layout**: left = agent list + category dropdown + count label; center = config editor (name/desc, LLM profile picker with resolved provider/model pill, instructions, tools list, JSON-editor toggle); right = live query/test panel (`AgentsViewPanel.h:19-72`). The **Create view** is the same 3-column shape plus capability toggles as checkable tag buttons: reasoning / memory / knowledge / guardrails / agentic_memory / storage / tracing / compression / hooks / evaluation, with collapsible sub-fields for knowledge (vectordb/embedder/urls) and export/import JSON (`CreateAgentPanel.h:21-90`). Agentic mode (long-running tasks, HITL, scheduling) is a whole extra surface (`AgentService.h:55-119`) — that's Phase-2/3 territory in their own `docs/agentic-research/` plan.

### How Vysted compares (read against `sidecar/agents/`, `types/plugin.ts`)

Vysted **already has this pattern, in a cleaner BYOK shape**, but thinner:
- 12 first-party personas as `sidecar/agents/<id>.json`, validated at startup against `_schema.json` (`sidecar/agents/README.md`). The Buffett prompt (`sidecar/agents/buffett.json`) is just as good as Fincept's — same framework-first, no-roleplay discipline.
- `AgentSpec` (`types/plugin.ts:143-158`, LOCKED): `id, name, philosophy, systemPrompt, tools[], defaultProvider, defaultModel?, icon?`.
- Custom agents already carry a reserved `custom:` id prefix and live in a separate SQLite store (`README.md`), and plugins contribute agents via `getAgents()` — **so Vysted already has Fincept's "bundled + DB-custom merge" design baked into the contract.**

**Gap vs Fincept (fields Vysted's `AgentSpec`/schema lacks):**
| Fincept field | Vysted has? | Value to Vysted |
|---|---|---|
| `category` | ❌ | Enables category chips + filter in the picker. Cheap, high-UX. |
| `capabilities[]` (tags) | ❌ | Searchable/filterable lens tags. Makes the picker discoverable beyond name. |
| per-agent `model` (temperature/max_tokens) | partial (`defaultModel` only) | Buffett-style agents want low temp; a critic wants different. |
| `output_schema` (structured output) | ❌ | Forces machine-parseable agent verdicts → feeds workflow/backtest nodes. |
| `scoring_weights` | ❌ | Makes the rubric explicit + tunable in UI. |
| `data_sources.required_api_keys` | ❌ | Lets the picker *tell the user which key is missing* before they run. Ties persona → integrations hub. |
| `memory` / `agentic_memory` flags | ❌ | Long-running copilot prerequisite. |
| `teams` / sub-`agents` | ❌ | Multi-agent debate (Fincept's `debate_orchestrator.py`). |

### How this should inform Vysted's copilot

1. **`AgentSpec` is Tier-1 LOCKED — do NOT edit it.** But the *discovery convention* in `sidecar/agents/` is sidecar-internal (README explicitly says the schema there is a "sidecar-internal convention and may evolve" / Tier-2). **Extend the sidecar JSON format with optional `category`, `capabilities[]`, `recommendedModel`, `requiredKeys[]` fields, surfaced through a NEW host-side picker view-model — not through the locked contract.** The contract stays serializable; the richer metadata is host-resolved like `PLUGIN_COMPANIONS` already is for panels.
2. **Build the persona-picker as a 3-pane editor like `AgentsViewPanel`**: list (with category chips + count) → config preview (resolved provider/model pill, system-prompt preview, tool list) → live test. Vysted's chat sidebar currently just lists agents; this is the upgrade path.
3. **Wire persona → integrations hub via `requiredKeys`**: when a persona declares `required_api_keys`, grey it out / show a "connect X" CTA if the key is missing in keychain — reuse `useProviderKeysStore` (`src/store/provider-keys.ts`) probe pattern, generalized to data-provider keys.
4. **Steal the prompt structure for any new personas**: "BEFORE you answer confirm / INPUTS (named tools) / FRAMEWORK (required sections) / OUTPUT (md headers) / DO NOT". It is reproducibly good.
5. **Defer** teams/debate/agentic-mode to a later phase; Fincept's own `docs/agentic-research/README.md` says ~80% of agentic primitives pre-existed and the work was "wiring + exposure + reflection/budget layers." Vysted is in the same place.

---

## 2. Integrations / credentials / connections hub  ⭐ second-highest value

### What Fincept does — the registry pattern Vysted needs

**A self-registering connector registry of ~78 data sources** across 11 categories, each a fully declarative config with a dynamic form spec. This is the gold standard for an integrations hub.

**The type** (`src/screens/data_sources/DataSourceTypes.h`):
```cpp
struct FieldDef {
  QString name, label;  FieldType type;  // Text|Password|Number|Url|Select|Textarea|Checkbox|File
  QString placeholder;  bool required;  QString default_value;  QVector<SelectOption> options;
};
struct ConnectorConfig {
  QString id, name, type;  Category category;  // 11 categories (enum + str + label helpers)
  QString icon /*emoji*/, color /*hex*/, description;
  bool testable = true;  bool requires_auth = false;
  QVector<FieldDef> fields;   // ← drives a DYNAMIC config form, zero bespoke UI per connector
};
```

**The registry** (`src/screens/data_sources/ConnectorRegistry.{h,cpp}`):
- Singleton holding all connector definitions. `add()`, `all()`, `get(id)`, `by_category(cat)`, `count()`.
- **Each connector .cpp self-registers via a static-init bool**; `register_all_connectors()` just forces the linker to include the translation units (`ConnectorRegistry.cpp:8-16`). New connector = new file, no central edit.
- Categories: Databases (relational + 15 NoSQL), APIs, Files, Streaming, Cloud Storage, Time Series, **Market Data (19: Yahoo, Alpha Vantage, Finnhub, IEX, Binance, Coinbase, Kraken, CoinGecko, Tiingo…)**, Search & Analytics, Data Warehouses, **Alternative Data (9: RavenPack, SafeGraph, Thinknum…)**, **Open Banking (5: Plaid, MX, Finicity, TrueLayer, FDX)** — see file header comments in `src/screens/data_sources/connectors/*.cpp`.

**The UX** (`src/screens/data_sources/`):
- Two view modes: **Gallery** (browse/add connector types) and **Connections** (your saved instances) — `DataSourceTypes.h` `enum ViewMode {Gallery, Connections}`.
- `ConnectionConfigDialog` renders the form from `FieldDef[]` dynamically.
- `ConnectionTester` (`ConnectionTester.h`): async TCP/URL probe on a worker thread; derives a provider-specific probe URL (`provider_probe_url(provider_id, cfg)`) or falls back to host+port; result dialog + queued UI-thread callback. Non-testable connectors short-circuit gracefully. There's also a background poll timer that re-probes without a dialog.
- `ImportExportConnections` (`ImportExportConnections.h`): JSON round-trip — **export all connections, import (each gets a fresh UUID), and `download_connector_template()` dumps a blank template of every registered connector grouped by category.** Excellent onboarding/sharing affordance.

**Brokers are a parallel registry** (`src/trading/BrokerRegistry.{h}`): factory + lookup for 21 broker implementations (`src/trading/brokers/`: zerodha, angelone, upstox, fyers, dhan, groww, alpaca, ibkr, tradier, saxo…), `register_all()`, `get(id)`, `list_brokers()`, `has(id)`. Plus 2 crypto exchanges (`src/trading/exchanges/`: kraken, hyperliquid).

**Notifications are a THIRD registry** (`src/screens/settings/NotificationsSection.h`): 15 providers (telegram, discord, slack, email, whatsapp, pushover, ntfy, pushbullet, gotify, mattermost, teams, webhook, pagerduty, opsgenie, sms) as a per-provider accordion with `enabled` toggle + dynamic `fields` + inline `test_btn` + `status_lbl`. Same declarative-fields + test-button shape as connectors.

### How Vysted compares

Vysted's integrations are **hardcoded per-broker, no unified hub**:
- `BROKER_CREDENTIAL_FIELDS: Record<BrokerId, Array<{key, label}>>` in `src/modules/broker-connect/BrokerConnectPanel.tsx:40` — the equivalent of `FieldDef[]`, **but only `{key, label}`** — no `type` (so no password masking metadata, no url/select), no `placeholder`, no `required`, no validation, no `testable`, no `requires_auth`, no icon/color/description.
- The panel lists 7 brokers + ccxt sub-exchanges in two hardcoded groups, status badge, connect → credentials dialog writing keychain `broker:<id>:<field>` (`BrokerConnectPanel.tsx:4-15`). Good safety story (first-connect disclaimer, kite static-IP banner) but **no data-provider connections at all** — Vysted has no MongoDB/Postgres/Tiingo/Plaid connector concept. Data sources are baked into the sidecar (yfinance, FRED, etc.), not user-connectable.
- LLM provider keys have their own store (`src/store/provider-keys.ts`) probing keychain per provider — a fourth, separate credential surface.

### How this should inform Vysted's integrations hub

1. **Introduce a single `ConnectorSpec` registry** mirroring `ConnectorConfig`: `{ id, name, category, icon, color, description, testable, requiresAuth, fields: FieldDef[] }` where `FieldDef = { name, label, type: "text"|"password"|"url"|"number"|"select"|"checkbox"|"file", placeholder?, required?, default?, options? }`. One declarative table → one dynamic `ConnectionConfigDialog`. This unifies **brokers + data providers + LLM providers + notification channels** behind one form engine instead of four bespoke surfaces. (Vysted's plugin contract already has `contributesData` — connectors can be plugin-contributed, which is *better* than Fincept's static-link self-registration.)
2. **Adopt the Gallery / Connections two-view split.** Gallery = "what can I connect" (browse by category chip); Connections = "what I've connected" (status badge + test). Vysted's broker panel is connections-only today.
3. **Add a `ConnectionTester`** — a sidecar `POST /connections/{id}/test` that does a real auth/connectivity probe per connector, surfaced as an inline "Test" button with status. This is the difference between "I think my key works" and "verified." Fincept's per-provider `provider_probe_url` is the template.
4. **Add import/export + blank-template download.** Cheap, and a strong onboarding affordance ("here's a JSON with every connector you could fill in"). Reuse keychain for secrets — export should redact / reference, not dump secrets (Fincept dumps to plain JSON; Vysted's keychain model is stricter and should stay so — export connection *shapes*, not secret values).
5. **Don't copy 78 connectors.** Vysted is local-first BYOK finance; the relevant categories are Market Data, Alternative Data, Open Banking (Plaid for portfolio import), and the brokers it already has. Pick ~15–20 that match the product, register them through the plugin `contributesData` capability.

---

## 3. Command palette / command system

### What Fincept does — a unified action registry feeding everything

**One `ActionRegistry` is the single source of truth for command palette + hotkeys + menus + help/cheatsheet + telemetry.** This is markedly more sophisticated than Vysted's palette.

`ActionDef` (`src/core/actions/ActionDef.h:79-89`):
```cpp
struct ActionDef {
  QString id;                  // "window.cycle_forward" — stable, persistence + bus key
  QString display, category;   // label + top-level grouping (Window/Panel/Layout/…)
  QStringList aliases;         // extra search/command-bar tokens
  QKeySequence default_hotkey; // empty = none; user can rebind
  ActionPredicate predicate;   // [](ctx){ return ctx.focused_frame != nullptr; } — greys out when wrong context
  ActionHandler handler;       // Result<void>(ctx); empty = no-op placeholder
  QList<ParameterSlot> parameter_slots;  // guided/parameterised commands
};
```
- `CommandContext` (`ActionDef.h:31-37`) carries `shell, focused_frame, focused_panel, args` so handlers make policy decisions without knowing concrete types.
- `ParameterSlot` (`ActionDef.h:46-54`): `{ name, display, type, required, suggestion_source, default_value }` — the palette parser asks for missing args; `suggestion_source` ("symbol", "layout_name", "panel_id") drives completion lists. **Parameterised commands** — e.g. "open chart for <symbol>".
- `ActionRegistry` (`ActionRegistry.h`): `register_action` (idempotent on id, emits `action_replaced`), `unregister_action`, `find`, `match(prefix, max)` with documented relevance ordering (exact id → id starts-with → display → alias), `invoke(id, ctx)` which **runs the predicate first** and short-circuits with an error Result if it fails.
- `CommandPalette` (`src/ui/command/CommandPalette.h`): Ctrl+K overlay, fuzzy search over a `SuggestionIndex`, centered on the focused frame (multi-monitor aware), Esc dismiss, Enter invoke. ~41 builtin actions (`builtin_actions.cpp`).

### How Vysted compares

Vysted's palette is **minimal** (`src/components/CommandPalette.tsx`, `src/store/command-palette.ts`):
- Cmd/Ctrl+K toggle ✅, motion-animated, accessible.
- **`includes()` substring filter on `title`/`trigger` only** — no fuzzy ranking, no relevance ordering (`CommandPalette.tsx:75-80`).
- `CommandSpec` (`types/plugin.ts:118-133`, LOCKED): `{ id, trigger, title, description?, icon?, commandId?, opensPanel? }`. A command either forwards `commandId` to `executeCommand()` or opens a panel.
- **No categories, no hotkeys, no predicates/context-gating, no parameter slots, no aliases.** Commands are a flat list aggregated from enabled modules at startup.

### How this should inform Vysted's command system

1. **`CommandSpec` is LOCKED** — but it's already extensible enough for v1 (commandId + opensPanel). The *host-side palette* can be upgraded without touching the contract:
   - **Add categories** by grouping on the contributing module id (host knows which module each command came from) — no contract change.
   - **Add fuzzy ranking + relevance order** (exact trigger → trigger starts-with → title → description). Pure host logic. A small fuzzy matcher (fzf-style) over `trigger`+`title`+`description` is a 1-file change to `CommandPalette.tsx`.
   - **Add `aliases`** as an *optional* `CommandSpec` field if/when a contract revision happens (Tier-4 — block & ask). Until then, fold synonyms into `description` (already searched).
2. **Predicate/context-gating is the bigger idea worth adopting carefully.** Fincept greys out commands when focus is wrong. Vysted's panel-context (`src/store/panel-context.ts`, `types/panel-context.ts`) already tracks focused-panel state — the palette could filter/grey commands based on it. This needs a host-side `available?(ctx)` resolver keyed off `commandId`, NOT a contract change.
3. **Parameterised commands** (`ParameterSlot`) are how "open chart AAPL" or "/connect alpaca" become guided. Vysted's `/connect <broker>` story (broker.ts mentions `contributesCommands` "/connect alpaca") would benefit — but this likely needs a contract field. **Defer to a deliberate Tier-4 contract revision; don't bolt it on.**
4. **Unify hotkeys + palette + help off one registry like Fincept.** Vysted has no global hotkey system yet; when it adds one, make the command list the source of truth (Fincept's explicit design intent: `ActionRegistry.h` "single source of truth feeding hotkey binding, command bar, help/cheat-sheet, telemetry").

---

## 4. Settings design + information architecture

### What Fincept does — left-rail of focused sections

`SettingsScreen` (`src/screens/settings/SettingsScreen.h`) is a **left-nav + `QStackedWidget`** shell; each section is its own `*Section.{h,cpp}`. Sections present (`ls src/screens/settings/`):

`General · Appearance · Keybindings · LLM Config · Credentials · Data Sources · MCP Servers · Notifications · Security · Storage · Python Env · Profiles · Voice · Developer · Logging`

Notable IA decisions:
- **`CredentialsSection`** (`CredentialsSection.h`): API keys → OS keychain via `SecureStorage`, "never written to disk plain", status labels + masked fields, reload-on-show. **Same security posture as Vysted's keychain-only BYOK.**
- **`LlmConfigSection`** (`LlmConfigSection.h`): two tabs — **Providers** (list + add/delete, api-key/base-url, **fetch-models** dynamic discovery, **test-connection**, per-provider model combo) and **Profiles** (named profiles: name/provider/model/key/baseurl/temp/tokens/system-prompt + set-default). Global settings (temp/max-tokens/tool-rounds/system-prompt) at the bottom of the Providers tab. **The Profiles concept is good: a named bundle of (provider, model, params, prompt) that agents reference** (`AgentsViewPanel` has an `llm_profile_combo_`).
- **`NotificationsSection`**: 15-provider accordion + alert-trigger toggles (in-app/price/news/orders) with news sub-options.
- Language-change rebuilds every section via stored factories and re-wires signals (`SettingsScreen.h:46-66`) — i18n-robustness; not Vysted's concern yet.

### How Vysted compares

Vysted's `SettingsPanel.tsx` is **one scrolling page, 4 sections** (`SettingsPanel.tsx:53-56`): **Providers · Layouts · Modules · About**. Flat, no left-rail, no sub-navigation. Providers section manages BYOK keys (keychain). Layouts = saved dockview layouts. Modules = enable/disable. About = version.

### How this should inform Vysted's settings + customizability

1. **Move to a left-rail + content-pane IA** once settings grows past ~5 sections. Vysted is at 4 and about to add an integrations hub, agent config, keybindings, notifications — that's 8+, past the scroll-page threshold. Mirror Fincept's section list, pruned to Vysted scope: **General · Appearance/Theme · Layouts · Modules & Plugins · AI Providers · Integrations (data + brokers) · Agents · Keybindings · Notifications · Security · About**.
2. **Adopt the "Profiles" concept for LLM config.** A named `(provider, model, temperature, maxTokens, systemPromptOverride)` bundle that personas/chats reference, instead of every agent re-specifying model params. This is the clean way to let users say "run all my agents on local Ollama" with one switch. Maps to Vysted's `src/store/llm-providers.ts`.
3. **Add per-provider "fetch models" + "test connection"** to the AI Providers section (Fincept's `on_fetch_models` / `on_test_connection`). Vysted currently stores a key but can't verify it or enumerate the provider's models — this is the same gap as the data-connector tester (#2.3).
4. **Keep the keychain-only credential posture** — Fincept's `CredentialsSection` validates the design Vysted already follows (only Tauri Rust touches keychain; `provider-keys.ts` probes status without holding values). No change, just confirmation the architecture is right.

---

## 5. Data-connector architecture (how unified)

Covered structurally in §2. The architectural answer to "how many / how registered / how unified":

- **How many:** ~78 data connectors (11 categories) + 21 brokers + 2 crypto exchanges + 15 notification channels + N LLM providers + MCP servers (marketplace). README markets "100+ data connectors".
- **How registered:** four parallel registries, all the same shape — a singleton holding declarative configs, populated by self-registering units (`ConnectorRegistry`, `BrokerRegistry`) or static catalogs (`McpMarketplace`, notification providers). New connector = new declarative entry, no central wiring edit.
- **How unified at the data layer:** there's a **`DataHub`** pub/sub bus (`src/datahub/DataHub.{h}`, `Producer.h`, `TopicPolicy.h`) — services are `Producer`s that publish on topic patterns (e.g. `agent:output:<run_id>`, `task:event:<task_id>`); panels subscribe. `AgentService` is a "push-only producer" that retires disposable per-run topics to bound memory (`AgentService.h:139-149`). There's a 9-phase datahub migration documented (`docs/datahub-phases/phase-02…phase-10`) — they unified *consumption* behind one bus after the fact. A **`DataNormalizationService`** + `DataMappingScreen` (`src/services/data_normalization/`, `src/screens/data_mapping/`) lets users map arbitrary connector output → a normalized schema. **MCP** is the other unification layer: `McpMarketplace` (`src/mcp/McpMarketplace.h`) is a declarative catalog of preset external MCP servers (`{name, description, command, args, env_keys, env_placeholders, category}`) and a `TerminalMcpBridge` exposes terminal capabilities as MCP tools to the LLM.

**Inform Vysted:**
- Vysted's **plugin contract IS the unification layer** Fincept reached for after the fact — `contributesData` + the panel-context publish/subscribe (`src/store/panel-context.ts`, `panel-context-publishers.test.tsx`) is Vysted's DataHub equivalent, and it's contract-first rather than retrofitted. **Vysted is ahead here.** Don't build a separate DataHub; route connectors through `contributesData`.
- **The MCP marketplace catalog is directly adoptable.** Vysted already runs MCP subprocesses (`sidecar/openbb_mcp_subprocess`, `sec_edgar_mcp_subprocess`; `types/mcp.ts`; `src-tauri/src/openbb_mcp.rs`). A declarative `MarketplaceEntry`-style catalog (`{name, description, command, args, envKeys, envPlaceholders, category}`) for *user-installable* MCP servers, surfaced in the integrations hub, is a clean Phase-10+ feature. The `env_keys` + `env_placeholders` pattern is exactly how to prompt for required secrets in a dynamic form.
- **`DataNormalizationService` / `DataMappingScreen`** (map connector fields → canonical schema) is over-scoped for Vysted now but is the right answer if Vysted ever lets users connect arbitrary REST/DB sources. Note it for later; don't build yet.

---

## 6. Overall feature breadth — screens Vysted lacks

**Fincept: 55 screens** (`ls src/screens`). **Vysted: 18 modules** (`src/modules/index.ts:55-78`): chart, watchlist, news, portfolio, equity-overview, chat, platform, plugin-manager, agent-builder, node-editor, backtest, broker-connect, safety, macro, sec, quant, earnings, analyst-ratings, screener.

Mapping — what Fincept has that Vysted does NOT (architecture/feature only, branding ignored):

| Fincept screen | Vysted equivalent | Gap / opportunity |
|---|---|---|
| `data_sources` + `data_mapping` | broker-connect only | **Integrations hub** (§2) — biggest gap. |
| `mcp_servers` (+ marketplace) | MCP subprocess (no UI) | User-installable MCP catalog UI (§5). |
| `agent_config` (Create/Teams/Workflows/Planner/Tools/Agentic) | agent-builder + chat | Multi-agent teams, planner, agentic tasks, scheduling. |
| `report_builder` (canvas + components + properties) | ❌ | Drag-drop research report builder → export. Strong for a research-lab product. |
| `relationship_map` (graph scene) | ❌ | Entity/holdings relationship graph. ReactFlow already in Vysted — cheap. |
| `watchlist` (dedicated screen) | watchlist module ✅ | parity |
| `code_editor`, `devtools`, `excel`, `file_manager`, `notes` | ❌ | Power-user workbench surfaces. `notes` + `file_manager` are low-cost wins. |
| `crypto_center`, `crypto_trading`, `polymarket`, `fno`, `derivatives` | quant/backtest partial | Asset-class breadth. Polymarket (prediction markets) is a distinctive angle. |
| `geopolitics`, `maritime`, `gov_data`, `economics`, `dbnomics`, `news` | macro + news | Alt-data / global-intelligence breadth (Fincept's differentiator). |
| `equity_research`, `ma_analytics`, `surface_analytics`, `trade_viz` | equity-overview + analyst-ratings | Deeper research surfaces. |
| `ai_quant_lab`, `alpha_arena`, `algo_trading`, `quantlib` | quant + backtest | ML/factor/RL lab; QuantLib (Vysted Phase 6 has quant module — partial parity). |
| `forum`, `support`, `docs`, `info`, `about`, `profile` | about only | Community/help/in-app docs. |
| `voice` / `stt` / `tts` services + `VoiceConfigSection` | ❌ | Voice copilot. Distinctive; sidecar TTS/STT is heavy (PyInstaller size — see Vysted's 120 MB gotcha). Defer. |
| `action_center` | safety module partial | Unified order/alert action center. |
| `recovery`, `launchpad` (+ onboarding tour) | onboarding-banner | First-run launchpad + guided tour. |

**The honest read:** Fincept is **broad and shallow** (55 screens, kitchen-sink, AGPL+commercial, memecoin-adjacent funding). Vysted is **narrow and deep** (18 well-tested modules, locked contract, safety-first, real CI discipline). Vysted should NOT chase breadth parity. The 4 worth lifting on merit:
1. **Integrations hub** (§2) — the clearest, highest-leverage gap.
2. **Report builder** — fits the research-lab DNA; ReactFlow/dockview primitives already exist.
3. **Relationship map** — cheap given `@xyflow/react` is already a dependency.
4. **MCP marketplace UI** (§5) — small, builds on existing MCP infra.

---

## Concrete recommendations (priority order)

1. **Integrations hub.** Introduce a declarative `ConnectorSpec` + `FieldDef` registry (mirror `ConnectorConfig`/`FieldDef`), a dynamic config dialog, a Gallery/Connections two-view UI, a sidecar connection-tester, and import/export with a blank-template download. Unify brokers + data providers + LLM providers + notifications behind it. Route connectors through the existing `contributesData` capability (no contract change). — *file refs: `DataSourceTypes.h`, `ConnectorRegistry.{h,cpp}`, `ConnectionTester.h`, `ImportExportConnections.h`.*
2. **Persona-picker upgrade.** Extend the *sidecar* agent JSON (Tier-2, NOT `types/plugin.ts`) with optional `category`, `capabilities[]`, `recommendedModel`, `requiredKeys[]`; build a 3-pane picker (list+chips → preview → test) like `AgentsViewPanel`; grey out personas whose `requiredKeys` are missing from keychain. — *file refs: `AgentService_Discovery.cpp:37-170`, `AgentsViewPanel.h`, `configs/*.json`, `persona_registry.py`.*
3. **Command palette ranking + categories.** Add fuzzy ranking + relevance ordering + module-derived categories to `CommandPalette.tsx` — pure host logic, no `CommandSpec` change. Defer aliases/parameter-slots/predicates to a deliberate contract revision. — *file refs: `ActionDef.h`, `ActionRegistry.h`, `CommandPalette.h` vs Vysted `CommandPalette.tsx`.*
4. **Settings IA → left-rail.** Restructure `SettingsPanel.tsx` to a left-nav + content-pane with sections (General/Appearance/Layouts/Modules/AI Providers/Integrations/Agents/Keybindings/Notifications/Security/About). Add LLM "Profiles" (named param bundles) + per-provider fetch-models/test-connection. — *file refs: `SettingsScreen.h`, `LlmConfigSection.h`, `CredentialsSection.h`.*
5. **MCP marketplace UI** (later). Declarative `MarketplaceEntry` catalog of user-installable MCP servers with `envKeys`+`envPlaceholders`, surfaced in the integrations hub. — *file ref: `McpMarketplace.h`.*

---

## What I did NOT get to (time-box honesty)

- **Did not read the C++ `.cpp` implementations** of `ConnectionConfigDialog`, `DataSourcesScreen_Layout`, the palette `SuggestionIndex`, or `builtin_actions.cpp` in full — read headers + key methods only. The dynamic-form render loop and fuzzy matcher internals would refine the §2/§3 implementation detail.
- **Did not study the DataHub topic-policy / backpressure** (`TopicPolicy.h`, `RateLimiter`) — relevant only if Vysted ever builds a bus, which §5 argues against.
- **Did not read the agentic-research design docs in depth** (`docs/agentic-research/design/03_architecture.md`, `04_impl_plan.md`) — only the README. These are Fincept's own plan for long-running agents and would directly inform a Vysted "agentic copilot" phase (HITL, budget controller, skill library, reflexion). Strong follow-up read.
- **Did not exercise any code** (headless; C++/Qt won't build here anyway). All claims are source-read, not runtime-verified.
- **Did not catalog all 78 connectors / 37 personas individually** — sampled representative ones per category from file-header comments and a handful of full configs.
- **Voice/STT/TTS, quant lab, alpha_arena, geopolitics agents** — noted for breadth (§6) but not architecturally dissected; out of Vysted's near-term scope.
