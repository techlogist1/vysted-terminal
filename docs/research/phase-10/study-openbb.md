# OpenBB Platform — Architecture Study for Vysted Integrations Hub

**Date:** 2026-05-29
**Author:** Phase-10 research subagent (senior-engineer extraction pass)
**Subject repo:** `github.com/OpenBB-finance/OpenBB`, monorepo subtree `openbb_platform/`
**Pinned commit read:** `41214261c1a95c9454e3102279e0b16efda080fc` (develop)
**Method:** Read actual source via GitHub contents API + docs.openbb.co WebFetch. Every claim below is cited to a real file path. Docs pages on `docs.openbb.co/platform/developer_guide/*` 404'd repeatedly (the docs site reorganised under `/odp/python/developer/*`), so the architectural claims are taken from source, not prose docs.

---

## 0. Why OpenBB is the right thing to study for Vysted

OpenBB Platform is the closest existing analogue to the *data half* of Vysted: a single product that has to ingest ~30+ heterogeneous financial-data vendors behind one consistent surface, let third parties add new vendors without touching the core, and feed the result to a UI, an Excel add-in, a REST API, **and** AI agents. That is exactly Vysted's "integrations hub + data-connector breadth + extensibility" problem. The difference in constraints is the interesting part, and it is where the lessons live:

- OpenBB is a **pip-installed Python library**; extension discovery is Python *entry points*. Vysted is a **signed Tauri desktop binary** with a PyInstaller `--onefile` sidecar — entry-point discovery of arbitrary pip packages is not available to Vysted at runtime (the binary is frozen). This single fact reshapes most of the "how do we copy this" answers.
- OpenBB stores credentials in a **plaintext `user_settings.json`** and passes the *entire* credential dict to every fetcher. Vysted stores BYOK secrets in the **OS keychain** (only Tauri Rust can read them) and passes only **per-plugin-scoped** secrets (`PluginConfig.secrets`, `types/plugin.ts:42`). Vysted is strictly more secure here; the lesson is *what to keep* from OpenBB's credentials-hub UX without inheriting its security model.

---

## 1. Provider / data-connector architecture (the TET pipeline + standard models)

### 1.1 The four-class contract

Every OpenBB data connector is built from four classes, three of which a new provider subclasses:

1. **`QueryParams`** — `openbb_core/provider/abstract/query_params.py`. A Pydantic `BaseModel` of *input* parameters for an endpoint.
2. **`Data`** — `openbb_core/provider/abstract/data.py`. A Pydantic `BaseModel` of *output* fields. Configured `extra="allow"`, `populate_by_name=True`, with an `AliasGenerator` (camelCase validation alias, snake_case serialization alias) and an `__alias_dict__` class attribute for explicit field-name remapping (`data.py:71-99`).
3. **`Fetcher[Q, R]`** — `openbb_core/provider/abstract/fetcher.py`. Generic over the query type `Q` and return type `R` (usually `list[D]`). Implements the **TET pipeline**.
4. **`Provider`** — `openbb_core/provider/abstract/provider.py`. The extension entry point object that bundles a provider's fetchers and declares its credentials.

### 1.2 TET: Transform → Extract → Transform

`Fetcher` (`fetcher.py:39-90`) defines exactly three overridable static methods and one orchestrator:

```python
class Fetcher(Generic[Q, R]):
    require_credentials = True               # class-level flag, fetcher.py:42

    @staticmethod
    def transform_query(params: dict) -> Q: ...        # dict -> validated QueryParams
    @staticmethod
    async def aextract_data(query: Q, credentials: dict|None) -> Any: ...  # hit the vendor
    @staticmethod
    def transform_data(query: Q, data: Any, **kw) -> R: ...  # raw -> list[Data]

    @classmethod
    async def fetch_data(cls, params, credentials=None, **kw):  # fetcher.py:73
        query = cls.transform_query(params=params)
        data  = await maybe_coroutine(cls.extract_data, query=query, credentials=credentials)
        return cls.transform_data(query=query, data=data)
```

Notable engineering details verified in source:
- **Sync/async auto-selection** (`fetcher.py:60-69`): `__init_subclass__` rewrites `extract_data = aextract_data` if the subclass implemented the async variant, and *raises at class-definition time* if neither is implemented. The contract is enforced when the module is imported, not when it is called.
- **A built-in `.test()` harness** (`fetcher.py:113-237`) runs all three TET stages and asserts: the query is the right type and carries the supplied values; the raw extracted data is **not yet transformed** (deliberately asserts `issubclass(type(data[0]), data_type) is False` — i.e. raw stage must be plain dicts, proving the pipeline boundary is real); and the transformed data *is* of the standard type with the expected fields. This is how OpenBB guarantees ~30 providers all conform — there is one generic test that every fetcher must pass.

### 1.3 Standard models are the decoupling spine

The genius is the split between *standard* models and *provider* models. Example, equity quote:

- **Standard** (`openbb_core/provider/standard_models/equity_quote.py`): `EquityQuoteQueryParams` (just `symbol`, upper-cased by validator) and `EquityQuoteData` (~45 fields: bid/ask, last_price, OHLC, year_high… each with a `Field(description=...)`). Field `change_percent` carries `json_schema_extra={"x-unit_measurement": "percent", "x-frontend_multiply": 100}` — **frontend rendering hints baked into the schema** (`equity_quote.py` standard model).
- **Provider** (`openbb_platform/providers/fmp/openbb_fmp/models/equity_quote.py`): `FMPEquityQuoteData(EquityQuoteData)` adds FMP-only fields (`ma50`, `ma200`, `market_cap`) and an `__alias_dict__` mapping FMP's wire names to the standard names (`"last_price": "price"`, `"high": "dayHigh"`, `"prev_close": "previousClose"`…). `FMPEquityQuoteFetcher(Fetcher[FMPEquityQuoteQueryParams, list[FMPEquityQuoteData]])` does the HTTP call in `aextract_data`, reads `credentials.get("fmp_api_key")`, and a `field_validator` normalizes `change_percent` from FMP's 0-100 to a 0-1 fraction.

So: **a provider subclasses the standard model, remaps its native field names via `__alias_dict__`, and adds vendor-specific extras.** Consumers always see the standard shape; the provider is free to be messy underneath. `__json_schema_extra__ = {"symbol": {"multiple_items_allowed": True}}` lets a provider declare capability extensions (FMP supports comma-separated symbols) without changing the standard.

### 1.4 The `Provider` object and credential namespacing

`fmp/openbb_fmp/__init__.py` constructs:

```python
fmp_provider = Provider(
    name="fmp",
    website="https://financialmodelingprep.com",
    description="...",
    credentials=["api_key"],                       # <-- declared, not stored
    fetcher_dict={"EquityQuote": FMPEquityQuoteFetcher, "BalanceSheet": ..., ...},  # ~70 entries
    repr_name="Financial Modeling Prep (FMP)",
    deprecated_credentials={"API_KEY_FINANCIALMODELINGPREP": "fmp_api_key"},
    instructions="Go to: https://site.financialmodelingprep.com/developer/docs ...",  # markdown w/ screenshots
)
```

Key mechanic (`provider.py:43-50`): `credentials=["api_key"]` is **namespaced** into `fmp_api_key` — the constructor prepends `{name.lower()}_` to every declared credential. So credential keys are globally unique and self-describing. `fetcher_dict` keys are **standard-model names** (`"EquityQuote"`), which is how the router later resolves "who can answer this command".

The `instructions` field is a per-provider, markdown, how-do-I-get-an-API-key blob with embedded screenshots — surfaced directly in the credentials UX. `deprecated_credentials` maps old env var names to the canonical key for migration.

### 1.5 Lesson for Vysted

Vysted's `DataSource` (`types/plugin.ts:76-87`) is currently a thin advertisement — `{id, label, kinds, realtime, description}`. It declares *that* a plugin serves equity/crypto/macro data but says nothing about the *shape* of that data or how to invoke it. OpenBB's split shows what a mature data-connector layer needs that Vysted does not yet have:

- **Standard output models per data kind.** Vysted already half-has this: `types/data.ts` mirrors `sidecar/models/` by hand (per CLAUDE.md Gotcha). That manual mirror *is* a de-facto standard-model layer, but it is not yet the contract a `DataSource` binds to. The adoptable move is to make `DataSourceKind` (`equity | crypto | macro | news | fundamentals | custom`, `types/plugin.ts:73`) map to a canonical Pydantic/TS model pair, so any plugin claiming `kinds: ["equity"]` must serve `EquityQuote`-shaped data. Today nothing enforces that two equity providers return the same fields — OpenBB enforces it structurally and Vysted does not.
- **The `__alias_dict__` + standard-subclass pattern is the single most copyable idea.** When Vysted adds a second equity vendor alongside the OpenBB-MCP one, the sidecar provider should subclass the canonical model and remap field names, not return a bespoke shape. This is the difference between "breadth of connectors" being O(n) integration work versus O(n) *thin* adapters.
- **Per-provider `instructions` markdown + `website` belong in the integrations hub.** OpenBB's credentials UX shows the user *exactly* how to get each key, inline. Vysted's broker plugins already gesture at this (`alpaca/index.ts:75` describes "api_key + api_secret stored in the OS keychain") but it lives in a command description, not a structured per-source onboarding blob. Add an `instructions?: string` + `website?: string` + `credentialFields?: {id, label, secret}[]` to the data-source/plugin metadata so the hub can render a proper connect card.
- **A generic `.test()` conformance harness per data kind.** OpenBB's `Fetcher.test()` is the reason 30 providers don't drift. Vysted should ship one parametrised pytest that, given any registered sidecar provider for kind `equity`, asserts it returns the canonical model — the same defense-in-depth instinct already codified in `tests/test_safety_end_to_end.py` for §6.5, applied to data breadth.
- **Do NOT copy `require_credentials = True` defaults blindly.** OpenBB defaults every fetcher to needing credentials; many Vysted sources (yfinance fallback, the OpenBB-MCP free path) are keyless. Keep the flag but default it the other way for a BYOK-optional product.

---

## 2. Extension / plugin model (router, provider, obbject extensions) and decoupling

### 2.1 Three entry-point groups

`openbb_core/app/extension_loader.py` is the whole story. `ExtensionLoader` (a singleton, `extension_loader.py:39`) discovers extensions through Python **entry points** in three groups (`OpenBBGroups`, `extension_loader.py:20-37`):

| Group entry-point name        | Loads into     | What it contributes |
|-------------------------------|----------------|---------------------|
| `openbb_core_extension`       | `Router`       | Commands (REST routes) — e.g. the whole `equity` namespace |
| `openbb_provider_extension`   | `Provider`     | Data connectors / fetchers — e.g. `fmp`, `polygon` |
| `openbb_obbject_extension`    | `Extension`    | Post-processing of command output + extra credentials — e.g. `charting` |

A provider declares itself in its `pyproject.toml` (verified, `fmp/pyproject.toml`):

```toml
[tool.poetry.plugins."openbb_provider_extension"]
fmp = "openbb_fmp:fmp_provider"
```

`ExtensionLoader._load_entry_points` (`extension_loader.py:160-210`) loads each group with a type-guard: core entries must be a `Router` (or a FastAPI `APIRouter`, auto-wrapped via `Router.from_fastapi`); provider entries must be a `Provider` (and `ModuleNotFoundError` is swallowed so a missing optional dep degrades gracefully rather than crashing the platform — `extension_loader.py:202-208`); obbject entries must be an `Extension`.

### 2.2 How decoupling actually holds

The decoupling is structural, not conventional:

- **Routers never name providers.** A command is `@router.command(model="EquityQuote")` over a body of literally `return await OBBject.from_query(Query(**locals()))` (`equity/price/price_router.py:21-30`). The route declares a *standard model name* and nothing else. It has zero knowledge of which providers exist.
- **Providers never name routes.** A provider declares `fetcher_dict={"EquityQuote": ...}` — keyed by the same standard-model name. It has zero knowledge of the REST path `/equity/price/quote`.
- **The `ProviderInterface` is the join.** `Query.execute()` (`app/query.py:73-95`) builds a `query_executor`, then calls `execute(provider_name, model_name=self.name, params=..., credentials=..., preferences=...)`. The executor looks up `(model_name, provider_name) -> Fetcher` and runs TET. The route and the provider meet only through the model-name string and the `ProviderInterface` registry — never directly.
- **`CommandMap` derives coverage from this join** (`app/router.py:283-420`). It walks every route's `openapi_extra["model"]`, looks up `ProviderInterface().map[model]` to find which providers implement it, and produces `provider_coverage` / `command_coverage` maps. This is how OpenBB renders "this command is available from fmp, polygon, intrinio" — it is *computed*, never hand-maintained.

### 2.3 The obbject extension is an output-side hook worth stealing

`openbb_obbject_extension` (e.g. `charting`) is the most under-appreciated layer. An `Extension` can register `on_command_output` callbacks scoped to route paths (`extension_loader.py:64-75`): `command_output_paths or ["*"]` → the callback fires after any matching command produces an `OBBject`. This is how charting auto-attaches a Plotly figure to results without any command knowing charting exists. Obbject extensions can *also* declare their own `credentials` (`credentials.py:78-96`, `from_obbject`), so a cross-cutting feature (a charting service, a future telemetry/AI annotator) participates in the same credentials hub as data providers.

### 2.4 Lesson for Vysted — the load-bearing one

**Vysted cannot adopt entry-point discovery, and should not pretend to.** The runtime is a frozen PyInstaller binary + a Next.js static export; CLAUDE.md is emphatic that arbitrary subprocess/extension discovery is fraught (the `--onefile` Popen deadlock, the `--add-data`/`--collect-data`/`--copy-metadata` bundling traps, the staleness-aware ensure scripts). Vysted's analogue is already correct and should be recognised as the *right* shape, not a temporary one:

- `src/lib/plugin-bootstrap.ts::BUNDLED_PLUGINS` is Vysted's static registry — the moral equivalent of OpenBB's entry-point list, except resolved at build time (which is exactly what static export + a signed binary demands). `PLUGIN_COMPANIONS` (CLAUDE.md Gotcha) is the panel-component side of the same static map.
- **The decoupling lesson transfers even though the discovery mechanism does not.** Vysted's plugin contract is *capability-keyed* (`PluginCapabilities`, `types/plugin.ts:59-66`) rather than *model-keyed*. That is a different and arguably better axis (it separates data/panels/commands/agents/nodes/control-plane), but it is missing OpenBB's killer property: **a plugin's data contribution is not joined to a standard model.** Two plugins can both claim `contributesData` + `kinds:["equity"]` and the host has no computed coverage map telling the user "AAPL quote is available from openbb-mcp and vendor-X." Adopt OpenBB's `CommandMap.provider_coverage` idea: derive a coverage view from `(DataSourceKind, pluginId)` so the integrations hub can show breadth per asset class and let the user pick a default provider per kind. This is the single most valuable thing the hub is currently missing.
- **Adopt the obbject-extension output-hook as Vysted's cross-cutting layer.** Vysted has no equivalent of `on_command_output`. The use cases are real and near-term: an AI-annotation pass that enriches any data-source result before it hits a panel; a sentiment-tagger that runs on any `news` result; the charting that already exists could be expressed as such a hook. This would be a *seventh* capability or, more conservatively, a sidecar-side middleware keyed by `DataSourceKind`. Worth a Tier-3 design note — but note this touches `types/plugin.ts` (Tier-4), so it is a *block-and-ask*, not an autonomous change.
- **Graceful degradation on missing deps is already Vysted's instinct** (the openbb-mcp plugin falls back to yfinance, `openbb-mcp/index.ts:108`). OpenBB's `ModuleNotFoundError`-swallow (`extension_loader.py:202`) is the same instinct at the loader level — keep doing this.

---

## 3. Command / router structure and standardized output (`OBBject`)

### 3.1 Router assembly

A `Router` (`app/router.py:47-208`) wraps a FastAPI `APIRouter`. Namespaces compose by nesting: `equity_router.py` builds `Router(prefix="")` then `include_router(price_router)`, `include_router(fundamental_router)`, etc. — and `equity` itself is the entry-point object loaded under `/equity`. `RouterLoader.from_extensions()` (`router.py:443-462`, `@lru_cache`) walks every `openbb_core_extension` entry and `include_router(prefix=f"/{name}")`. The full REST tree is assembled from independently-shippable router extensions at import time.

### 3.2 The `@router.command` decorator does heavy lifting

`Router.command` (`router.py:88-176`) + `SignatureInspector.complete` (`router.py:213-280`) is where a one-line command body becomes a fully-typed REST endpoint:

- The decorator takes `model="EquityQuote"`. `SignatureInspector` validates the function has the canonical `(cc, provider_choices, standard_params, extra_params)` signature, then **injects FastAPI dependencies**: `provider_choices` → the enum of providers that implement that model; `standard_params` → the standard QueryParams; `extra_params` → the union of all providers' extra params. It also injects the return annotation `OBBject[EquityQuoteData]`. The developer writes 3 lines; the framework synthesises the full OpenAPI schema, the provider dropdown, and per-provider parameter validation.
- `openapi_extra` carries `model`, `examples`, and optionally `widget_config` (OpenBB Workspace rendering) and `mcp_config` (AI tool exposure — see §4). These ride along in the OpenAPI spec so downstream consumers (Workspace UI, MCP server, Excel add-in) configure themselves from one schema (`router.py:106-114`).
- Standard error responses (204/400/404/500/502 with `OpenBBErrorResponse`) are attached uniformly (`router.py:131-160`).

### 3.3 `OBBject` — the universal output envelope

`app/model/obbject.py` is the single return type of every command (`OBBject(Tagged, Generic[T])`):

```python
results:  T | None         # the actual standard-model data
provider: str | None       # which provider answered
warnings: list[Warning_]   # non-fatal issues (e.g. unsupported param, obbject.py + query.py warnings)
chart:    Chart | None      # attached by the charting obbject-extension
extra:    dict             # metadata, incl. results_metadata from AnnotatedResult
```

Plus a fat set of converters: `to_df`/`to_dataframe`, `to_polars`, `to_numpy`, `to_dict`, and crucially **`to_llm()`** (`obbject.py:316-333`) which serialises results to compact JSON records for an LLM context. `from_query` (`obbject.py:347-366`) is the bridge: it runs the query, and if the result is an `AnnotatedResult` it lifts the metadata into `extra["results_metadata"]`.

### 3.4 Lesson for Vysted

- **Adopt a single output envelope for sidecar data routes.** Vysted's sidecar routers (`sidecar/routers/*.py`) currently return bare Pydantic models or `list[...]` (e.g. `plugins.py` returns `list[PluginConfigPayload]`). OpenBB's `OBBject` shows the value of a uniform `{results, provider, warnings, extra}` wrapper: the UI always knows *which* provider answered (critical once a kind has multiple providers + fallback), and `warnings` carries soft failures (e.g. "openbb-mcp down, served from yfinance") without an error status. Vysted already *computes* this provenance informally (the MCP status probe, `openbb-mcp/index.ts:104-124`) — formalise it into the response envelope so every panel can render "source: yfinance (degraded)".
  - Note the FastMCP gotcha already in CLAUDE.md: "tools must return a dict" — a uniform envelope *also* solves that, since `{results: [...], provider, warnings}` is always a dict. The v0.4.0 `{"agents": [...]}` wrap was an ad-hoc instance of exactly this pattern; generalise it.
- **`to_llm()` is the pattern for the AI sidebar.** Vysted's agents (`AgentSpec`, `types/plugin.ts:143-158`) will need to feed panel data into LLM context. A canonical `to_llm()`-style serializer per `DataSourceKind` (compact, ISO dates, records orientation) avoids each agent re-inventing data flattening and keeps token cost down.
- **The thin-command pattern is the right altitude.** OpenBB commands are 3 lines because all logic lives in the model/fetcher/executor. Vysted's broker plugins are already thin shells over sidecar routes (`alpaca/index.ts` is pure proxy, per its own header comment) — that instinct matches OpenBB. Keep frontend plugins dumb; keep the compute in the sidecar.
- **`widget_config`/`mcp_config` per-route metadata is the model for multi-surface config.** OpenBB configures three different consumers (Workspace widgets, MCP tools, Excel) from per-route `openapi_extra` rather than maintaining three configs. Vysted's analogue: when a data source needs panel hints *and* AI-tool exposure hints, attach them as structured metadata on the source/command spec, not in three separate places.

---

## 4. The AI / agent story (MCP server + OpenBB Workspace agents)

OpenBB has **two distinct AI integration paths**, and Vysted is already touching the first.

### 4.1 Path A — MCP server (commands → tools)

`openbb_platform/extensions/mcp_server/` (the package Vysted already wraps as `openbb-mcp-server`, per `plugins/openbb-mcp/index.ts` header). From the package README and structure (`openbb_mcp_server/{app,service,skills,utils}`):

- **Every REST command auto-becomes an MCP tool.** Tools are derived from FastAPI routes; parameters come from the endpoint signature. No manual tool registration.
- **Tools are categorized by API path** — first path segment after the prefix = category (`equity`, `crypto`, `economy`, `news`…), with subcategories (`equity_price`, `equity_fundamental`).
- **Per-session progressive tool activation** to fight context bloat — the key idea. Admin tools `available_categories`, `available_tools`, `activate_tools`/`activate_category`, `deactivate_tools` let an agent discover and enable only the tools it needs for a session. Inactive tools stay *discoverable* (descriptions visible) but unloaded.
- **Config knobs:** `default_tool_categories` (defaults `["all"]`; set to `["admin"]` to start minimal), `allowed_tool_categories` (hard server-level boundary on what can *ever* activate), `enable_tool_discovery` (gates whether admin tools register at all).
- **Per-route opt-out / shaping** via `openapi_extra.mcp_config` on FastAPI routes: `expose` (hide a route from MCP), `exclude_args` (drop params), `prompts` (associate workflow prompts). This is the `mcp_config` kwarg already visible in `Router.command` (`router.py:110-111`).

### 4.2 Path B — OpenBB Workspace custom agents (`agents.json` + SSE)

A separate, higher-level contract (docs.openbb.co/workspace + `agents-for-openbb` / `copilot-for-openbb` repos):

- An external agent is a service exposing **`/agents.json`** — a discovery contract with `{name, description, image, endpoints.query, features}`. `features` flags capabilities like `streaming`, `widget-dashboard-select`, `widget-dashboard-search`. Workspace fetches this to configure the agent dynamically — the same "advertise capabilities, host degrades gracefully" pattern as Vysted's `PluginCapabilities`.
- The query endpoint receives a `QueryRequest` (conversation history: messages with `role: "human"|"ai"` + `content`) and **streams SSE** (`MessageChunkSSE` chunks, reasoning steps, widget-data requests, visualizations) back via `EventSourceResponse`.
- The **OpenBB AI SDK (`openbb-ai`)** provides type-safe SSE event models so agent authors don't hand-craft the wire protocol.
- Agents can request widget data (the dashboard's current widget params) as context — i.e. the agent sees what the user is looking at.

### 4.3 Lesson for Vysted

- **The per-session tool-activation model is directly adoptable and important.** Vysted's `openbb-mcp` plugin currently proxies a fixed set of routes through the sidecar (`openbb-mcp/index.ts:51-74` advertises 3 data sources). As Vysted's MCP surface grows (every data kind × every provider × the agent tools in `sidecar/services/agent_tools/`), naive "expose everything" will blow the LLM context. Adopt OpenBB's `available_tools`/`activate_tools` admin-tool pattern and `default_tool_categories=["admin"]` so Vysted agents pull tools on demand. This matters more for Vysted than OpenBB because Vysted ships *multiple* MCP subprocesses (openbb-mcp + sec-edgar-mcp, per CLAUDE.md `externalBin`).
- **`agents.json` ≈ Vysted's `AgentSpec` — converge them.** Vysted's `AgentSpec` (`types/plugin.ts:143-158`) already mirrors this: `{id, name, philosophy, systemPrompt, tools[], defaultProvider}`. The gap vs OpenBB is the *runtime* contract: OpenBB agents stream SSE with reasoning steps and can request widget context. Vysted's agents are config-only today. The adoptable piece is the **`features`-style capability advertisement for streaming + panel-context access** — an agent should be able to declare "I want to see the current panel's data" the way OpenBB's `widget-dashboard-select` does. This is a Tier-3 design (DNA: AI-native, max extensibility) but if it touches `AgentSpec` it becomes Tier-4 (block-and-ask).
- **`mcp_config.expose=false` is the model for keeping broker-execution tools out of the agent surface.** OpenBB lets a route opt out of MCP. Vysted's §6.5 safety story *requires* this: order-placement routes must never become freely-callable agent tools (the propose→confirm two-step is human-gated, `alpaca/index.ts:6-8`). Adopt a per-route/per-command `exposeToAgents: false` default-deny for any control-plane/execution command. This dovetails with the existing v0.6.5 defense-in-depth (no non-GET routes on read-only providers, `supportsControlPlane=false`) — make "not an agent tool" a third explicit layer for execution surfaces.
- **`to_llm()` (see §3.4) is the data-side of the agent story** — the same serializer feeds both the MCP tool results and the Workspace-style agent context.

---

## 5. Concrete deltas: what to build into Vysted's integrations hub

Ranked by leverage:

1. **Standard-model binding for `DataSourceKind`.** Make each kind map to a canonical model pair (`types/data.ts` ↔ `sidecar/models/`), and require sidecar providers to subclass + `__alias_dict__`-remap into it. This converts connector breadth from N bespoke integrations into N thin adapters. (Source: §1.3, `fmp/models/equity_quote.py`.) — Tier-2/3, sidecar-only, no contract change.
2. **Computed provider-coverage map in the hub.** Derive "which sources serve kind X" from the registry the way `CommandMap.provider_coverage` does, and let the user set a default provider per kind with fallback. (Source: §2.2, `router.py:330-380`.) — Tier-3, host + sidecar.
3. **Uniform output envelope (`{results, provider, warnings, extra}`) on sidecar data routes**, carrying provenance + soft-failure warnings + an LLM serializer. (Source: §3.3, `obbject.py`.) — Tier-2, sidecar-only; also fixes the FastMCP "must return dict" gotcha generally.
4. **Per-session MCP tool activation** (`admin` tools + `default_tool_categories`) to cap agent context as the MCP surface grows across multiple subprocesses. (Source: §4.1, mcp_server README.) — Tier-3, sidecar + MCP layer.
5. **Default-deny agent exposure for execution/control-plane commands** (`exposeToAgents:false`), as a third §6.5 defense layer. (Source: §4.3, `mcp_config.expose`.) — Tier-3 design, but touches the safety story → coordinate with §6.5 owner.
6. **Per-source `instructions`/`website`/`credentialFields` metadata** for proper connect cards in the hub. (Source: §1.4, `fmp/__init__.py` `instructions`.) — Tier-2/3; if it lands on `types/plugin.ts` it's Tier-4 (block-and-ask).
7. **Output-side hook layer** (OpenBB's `obbject_extension` `on_command_output`) for cross-cutting enrichment (AI annotation, sentiment tagging). (Source: §2.3, `extension_loader.py:64-75`.) — Tier-4 if it extends `PluginCapabilities`; design first, then ask.

## 6. What NOT to copy from OpenBB

- **Plaintext `user_settings.json` credential storage** (`user_service.py:32-49`, `credentials.py:load`). OpenBB writes API keys to a JSON file and `model_dump()`s the *entire* credential set into *every* query (`query.py:93`). Vysted's keychain + per-plugin scoped `secrets` (`types/plugin.ts:42`, the v0.6.5 "renderer reads keychain → passes secret in request header" pattern) is strictly better. Keep Vysted's model; only borrow the *UX* (the credentials hub, the `instructions` blobs, the per-provider connect cards).
- **Entry-point / arbitrary-pip-package discovery** (`extension_loader.py`). Incompatible with a signed Tauri binary + PyInstaller `--onefile` (the bundling/Popen/staleness traps documented across CLAUDE.md). Vysted's build-time `BUNDLED_PLUGINS` static registry is the correct adaptation — recognise it as the answer, not a stopgap.
- **`require_credentials=True` default.** OpenBB assumes paid providers; Vysted is BYOK-optional with keyless fallbacks. Default the flag the other way.
- **Global mutable credential dict passed everywhere.** OpenBB's `Credentials` is one giant model handed to all fetchers. Vysted's per-plugin secret scoping is the security boundary that model lacks — do not regress to a global secrets bag for the sake of OpenBB parity.

---

## Appendix — files read (all at commit `41214261c1`)

OpenBB:
- `openbb_platform/core/openbb_core/provider/abstract/fetcher.py` — TET pipeline + `.test()` harness
- `openbb_platform/core/openbb_core/provider/abstract/provider.py` — `Provider` object, credential namespacing
- `openbb_platform/core/openbb_core/provider/abstract/data.py` — `Data` base, `__alias_dict__`, alias generator
- `openbb_platform/core/openbb_core/provider/standard_models/equity_quote.py` — standard model example
- `openbb_platform/providers/fmp/openbb_fmp/__init__.py` — concrete `Provider` with ~70 fetchers
- `openbb_platform/providers/fmp/openbb_fmp/models/equity_quote.py` — concrete Fetcher (TET) + alias remap
- `openbb_platform/providers/fmp/pyproject.toml` — `openbb_provider_extension` entry point
- `openbb_platform/core/openbb_core/app/extension_loader.py` — three entry-point groups, singleton loader
- `openbb_platform/core/openbb_core/app/router.py` — `Router`, `@command`, `SignatureInspector`, `CommandMap`, `RouterLoader`
- `openbb_platform/core/openbb_core/app/query.py` — `Query.execute`, credential injection path
- `openbb_platform/core/openbb_core/app/model/obbject.py` — `OBBject` envelope + `to_llm`/converters
- `openbb_platform/core/openbb_core/app/model/credentials.py` — dynamic `Credentials` model, SecretStr, env override
- `openbb_platform/core/openbb_core/app/service/user_service.py` — plaintext `user_settings.json` persistence
- `openbb_platform/extensions/equity/openbb_equity/equity_router.py` + `price/price_router.py` — router composition
- `openbb_platform/extensions/mcp_server/` (tree + README) — MCP tool gen, per-session activation, `mcp_config`
- docs.openbb.co/workspace/developers/agents-integration — `agents.json` + SSE agent contract

Vysted (for grounding the lessons):
- `types/plugin.ts` — `VystedPlugin`, `PluginCapabilities`, `DataSource`, `AgentSpec`, `PluginConfig.secrets`
- `plugins/openbb-mcp/index.ts` — existing OpenBB-MCP data-source plugin + yfinance fallback
- `plugins/brokers/alpaca/index.ts` — thin proxy broker plugin, control-plane shape
- `sidecar/routers/plugins.py` — per-plugin config CRUD (sidecar-owned persistence)
