# Reference study: OpenBB Platform (ODP)

Source tree studied: `/Users/lokavyasingh/Documents/dev/reference/OpenBB`
Focus: the architecture Vysted should absorb for its sidecar + plugin contract +
MCP-as-framework goal. Every claim cites a file path. Lessons for Vysted are
called out inline and collected at the end.

OpenBB's own one-liner (`README.md:18-20`) is the thesis worth stealing:

> "connect once, consume everywhere" infrastructure layer that consolidates and
> exposes data to multiple surfaces at once: Python environments, OpenBB
> Workspace and Excel, MCP servers for AI agents, and REST APIs.

That is _exactly_ Vysted's "MCP-as-framework" goal stated by a mature codebase.
The whole platform is built so that **one set of provider definitions projects
into N consumption surfaces** (Python API, REST, MCP, CLI, Workspace widgets)
with zero per-surface re-authoring. Vysted should treat that projection
discipline as the north star, not the specific data models.

---

## 1. The provider / standardized-model / extension pattern

This is OpenBB's core idea and the most directly transferable piece. It has
four layers.

### 1.1 The abstract contract (`core/openbb_core/provider/abstract/`)

Four small base classes define the entire data-connector contract:

- **`QueryParams`** (`abstract/query_params.py`) — a Pydantic `BaseModel`
  subclass for _inputs_. `extra="allow"`, an `__alias_dict__` for renaming
  fields to a provider's wire names at `model_dump` time, and a
  `__json_schema_extra__` hook that lets each provider tag a field with
  per-provider metadata (e.g. `{"symbol": {"multiple_items_allowed": True}}`)
  that gets merged into the OpenAPI schema (`query_params.py:18-52`).
- **`Data`** (`abstract/data.py`) — Pydantic `BaseModel` for _outputs_.
  `extra="allow"`, plus an `AliasGenerator` that validates camelCase and
  serializes snake_case (`data.py:77-96`). The model is deliberately permissive
  so heterogeneous provider payloads still validate.
- **`Provider`** (`abstract/provider.py`) — the registration object. A provider
  package constructs ONE `Provider(name, description, website, credentials,
fetcher_dict, instructions, ...)`. The `fetcher_dict` maps a **standard model
  name** (e.g. `"EquityHistorical"`) → a `Fetcher` class. Credentials are
  auto-namespaced: passing `credentials=["api_key"]` becomes `fmp_api_key`
  (`provider.py:46-51`). `instructions` is freeform markdown telling the user
  how to get a key.
- **`Fetcher[Q, R]`** (`abstract/fetcher.py`) — the data-fetch engine. It is a
  three-stage **TET pipeline**: `transform_query` (dict → provider QueryParams),
  `extract_data` / `aextract_data` (call the upstream API), `transform_data`
  (raw payload → list of provider Data). `__init_subclass__` enforces that a
  subclass implements at least one of the extract methods and prefers the async
  one (`fetcher.py:60-71`). A built-in `Fetcher.test(...)` (`fetcher.py:115-233`)
  runs the whole TET and asserts the contract holds (query type, raw data has
  pre-transform shape, transformed data is the right subclass) — every provider
  ships fetcher tests against this.

### 1.2 Standard models = the cross-provider contract

(`core/openbb_core/provider/standard_models/`, 181 files)

A **standard model** is the provider-agnostic schema for one data concept.
`equity_historical.py` defines `EquityHistoricalQueryParams` (symbol, start_date,
end_date) and `EquityHistoricalData` (date, open, high, low, close, volume, vwap)
with shared field descriptions pulled from `utils/descriptions.py`
(`standard_models/equity_historical.py:17-61`). This is the "least common
denominator" every provider must satisfy.

### 1.3 A provider implements by _subclassing_ the standard model

(`providers/fmp/openbb_fmp/models/equity_historical.py`)

The FMP equity-historical model shows the full pattern:

- `FMPEquityHistoricalQueryParams(EquityHistoricalQueryParams)` adds
  `__alias_dict__ = {"start_date": "from", "end_date": "to"}` (provider wire
  names), `__json_schema_extra__` to mark `symbol` as multi-item, and
  _provider-only_ fields (`interval`, `adjustment`) with validation
  (`fmp/.../equity_historical.py:21-49`).
- `FMPEquityHistoricalData(EquityHistoricalData)` adds an `__alias_dict__`
  mapping the standard `open/high/low/close` onto FMP's `adjOpen/adjHigh/...`
  and _extra_ fields (`change`, `change_percent`) tagged with frontend-hint
  metadata (`"x-unit_measurement": "percent"`) (`fmp/.../equity_historical.py:52-77`).
- `FMPEquityHistoricalFetcher(Fetcher[FMPEquityHistoricalQueryParams,
list[FMPEquityHistoricalData]])` implements the three TET methods; the body
  of `aextract_data` is a one-line delegate to a helper
  (`fmp/.../equity_historical.py:79-131`).

The provider package's `__init__.py` (`providers/fmp/openbb_fmp/__init__.py`)
is a flat manifest: import every fetcher, then build one `fmp_provider =
Provider(name="fmp", credentials=["api_key"], fetcher_dict={... 70+ entries
...})`. The same standard model name `"EquityHistorical"` appears in FMP,
yfinance, intrinio, tiingo, etc. — that shared key is what makes them
interchangeable.

### 1.4 Discovery is via Python packaging entry points (zero central registry)

(`core/openbb_core/app/extension_loader.py`)

Providers/routers/post-processors are **never** listed in a central file. Each
package declares an entry point in its `pyproject.toml`:

```toml
[tool.poetry.plugins."openbb_provider_extension"]
fmp = "openbb_fmp:fmp_provider"

[tool.poetry.plugins."openbb_core_extension"]      # routers
equity = "openbb_equity.equity_router:router"

[tool.poetry.plugins."openbb_obbject_extension"]   # result post-processors
openbb_charting = "openbb_charting:ext"
```

`ExtensionLoader` (a singleton, `extension_loader.py:34-54`) enumerates three
entry-point groups — `openbb_core_extension` (routers), `openbb_provider_extension`
(providers), `openbb_obbject_extension` (output transforms) — and loads each via
`importlib.metadata.entry_points(group=...)` (`extension_loader.py:141-203`).
`RegistryLoader.from_extensions()` (`provider/registry.py:34-55`, `@lru_cache`)
folds them into a `Registry{name → Provider}`. **Installing a `pip` package is
the entire install-a-plugin flow** — no manifest edit, no rebuild. Loading is
fault-tolerant: a provider that fails to import is warned-and-skipped, not fatal
(`registry.py:44-54`, `extension_loader.py:190-196`).

> **Lesson for Vysted (data layer / plugin contract).** OpenBB's
> standard-model-as-contract is the cleanest known answer to the problem Vysted
> already half-solved with `sidecar/services/provider_registry.py` (which
> hand-dispatches by `asset_class` to yfinance / ccxt / openbb-mcp). Vysted's
> registry is **dispatch-by-hardcoded-if** (`provider_registry.py:35-49`);
> OpenBB's is **dispatch-by-standard-model-name across a discovered registry**.
> For Vysted's plugin goal, the transferable shape is:
> (a) define a small set of standard Pydantic models in `sidecar/models/` as the
> cross-provider contract (Vysted already mirrors these into `types/data.ts` by
> hand — that mirror IS the standard-model idea, just one-directional);
> (b) have a plugin contribute a `Provider`-like object whose data capability
> declares `{standardModelName → fetcher}`; (c) make the registry resolve by
> model name + a preference order, not by an `if asset_class == "crypto"` chain.
> Vysted's `plugin.ts` `DataSource` already has `id`/`label`/`kind`
> (`types/plugin.ts` `DataSourceKind = equity|crypto|macro|news|fundamentals|custom`)
> — promote `kind` into a typed standard-model key so two plugins serving the
> same kind are genuinely interchangeable.
>
> The **entry-point discovery** trick does NOT port cleanly: Vysted is a
> PyInstaller `--onefile` sidecar, and `importlib.metadata.entry_points` over a
> frozen binary is exactly the metadata-dropping trap already documented in
> CLAUDE.md ("PyInstaller `--onefile` silently drops package metadata"). Vysted's
> plugin discovery must stay the explicit static-import map it already uses
> (`PLUGIN_COMPANIONS` / `BUNDLED_PLUGINS` in `src/lib/plugin-bootstrap.ts`,
> `provider_registry` imports). The lesson is the _registration shape_
> (one object per provider, model-name keyed `fetcher_dict`, fault-tolerant
> load), not the _discovery mechanism_.

---

## 2. The dynamic standardized-model merge (the clever part)

(`core/openbb_core/app/provider_interface.py`, `provider/registry_map.py`)

This is the machinery that turns "5 providers each subclassing EquityHistorical"
into "one `/equity/price/historical` endpoint whose params are the union of all
providers' params and whose response is a discriminated union of all providers'
data". Worth understanding because it is the hard part Vysted has not solved.

- `RegistryMap` (`registry_map.py:20-207`) walks every provider's `fetcher_dict`,
  and for each standard model splits each provider's fields into **standard**
  (defined in a file under `standard_models/`) vs **extra** (provider-only), by
  checking the file each field's class is declared in
  (`registry_map._extract_info:142-181`). It also merges `__json_schema_extra__`
  across providers so one schema field carries per-provider flags
  (`registry_map._update_json_schema_extra:108-131`).
- `ProviderInterface` (a singleton, `provider_interface.py:70-118`) then
  _synthesizes Pydantic/dataclass types at runtime_:
  - `ProviderChoices` — a dataclass with `provider: Literal[<all providers for
this model>]` (`_generate_model_providers_dc:543-574`).
  - `StandardParams` / `ExtraParams` — dataclasses built with `make_dataclass`;
    standard params are required-shared, extra params are every provider-only
    field made `Optional` and tagged with `title=<provider>` so the executor can
    later filter them (`_extract_params:372-446`, `_generate_params_dc:500-541`).
  - the return annotation — an `OBBject[Union[Annotated[FMPData, Tag("fmp")],
Annotated[YFData, Tag("yf")], ...]]` with a Pydantic `Discriminator` keyed on
    a hidden `_provider` attr (`_get_annotated_union:678-697`,
    `_generate_return_annotations:699-741`). One endpoint, provider-correct
    response schema.
- When two providers redefine the same field with different descriptions,
  `_merge_fields` (`provider_interface.py:174-242`) fuses them — if descriptions
  are >0.8 similar it appends `(provider: fmp, intrinio)`, else concatenates —
  and unions the annotations. This is how the generated OpenAPI/MCP schema reads
  coherently despite N providers.

> **Lesson for Vysted.** This runtime type-synthesis is _powerful but probably
> over-engineered for Vysted's stage_. The takeaway is the **principle**: a
> standard-model field set + per-provider extras + a provider discriminator, so
> the agent/UI sees ONE schema and the response is unambiguously attributable to
> a provider. Vysted can get 80% of the value with a much simpler rule:
> standard model = the Pydantic model in `sidecar/models/`, providers may add
> `extra` fields (Pydantic `extra="allow"` — Vysted's models should adopt this
> like OpenBB's `Data`), and the response always carries a `provider` field
> (Vysted's `Quote`/`OHLCVSeries` should add one). Do NOT build the
> `make_dataclass` merge engine unless/until multiple plugins serve the same
> model and the param-union actually matters. Flag this as a Tier-3 decision when
> the second same-kind data plugin lands.

---

## 3. Router / command structure

(`core/openbb_core/app/router.py`, `extensions/equity/.../price_router.py`)

Routers are how a domain (equity, crypto, news) exposes commands. The pattern is
strikingly thin and is the model Vysted's FastAPI routers should converge toward.

- A domain extension builds an `openbb_core.app.router.Router(prefix="/price")`
  and decorates command functions with `@router.command(model="EquityHistorical",
examples=[...])` (`price_router.py:14,46-60`). Sub-routers nest via
  `include_router` (`router.py:173-186`); the equity router composes
  `price/fundamental/estimates/...` sub-routers.
- **The command body is a one-liner**:
  ```python
  @router.command(model="EquityHistorical", examples=[...])
  async def historical(cc: CommandContext, provider_choices: ProviderChoices,
                       standard_params: StandardParams, extra_params: ExtraParams) -> OBBject:
      """Get historical price data..."""
      return await OBBject.from_query(Query(**locals()))
  ```
  All the wiring is in the decorator. `@router.command` + `SignatureInspector`
  (`router.py:227-374`) inspects the `model=` name and **rewrites the function's
  type annotations**, injecting the model-specific `ProviderChoices`,
  `StandardParams`, `ExtraParams` (built by `ProviderInterface`) as FastAPI
  `Depends()` and replacing the return annotation with the discriminated-union
  `OBBject_<Model>` (`router.py:242-282`, `inject_dependency:337-343`). So a
  three-line function becomes a fully-typed, fully-documented, provider-aware
  FastAPI route at import time.
- `model=` is the link to §2: it ties the route to a standard model, which is how
  `CommandMap.get_provider_coverage` (`router.py:432-461`) can report which
  providers back which route.
- The command path is: REST route → `Query(**locals())` (`app/query.py:17-80`) →
  `QueryExecutor.execute(provider, model, params, credentials)`
  (`provider/query_executor.py:65-97`) → `Fetcher.fetch_data` (the TET). `Query`
  also **filters extra params per provider and warns** if you pass an FMP-only
  param to intrinio (`query.py:36-64`), and pulls credentials from
  `user_settings.credentials` (`query.py:78`).

`OBBject` (`core/openbb_core/app/model/obbject.py`) is the universal result
envelope every command returns: `{results, provider, warnings, chart, extra}`
plus `to_df/to_dataframe/to_polars/to_numpy/to_dict` and — notably —
**`to_llm()`** (`obbject.py:337-353`) which serializes results to compact JSON
records explicitly for LLM consumption. The envelope is generic over `T` and
carries the route + params as private attrs for downstream post-processors.

> **Lesson for Vysted.** Two things.
> (1) The **decorator-injects-the-signature** trick is what lets OpenBB keep
> command bodies trivial and still produce rich OpenAPI (which then feeds MCP and
> Workspace). Vysted doesn't need the full magic, but it should adopt the
> discipline that **a command/route declares its standard model + examples in the
> decorator**, so the same declaration drives the REST schema, the MCP tool
> schema, and the agent-tool schema from one source. Right now Vysted maintains
> agent-tool schemas by hand in `sidecar/services/agent_tools/schemas.py`
> (`TOOL_SCHEMAS` + per-vendor `anthropic_tools/openai_tools/gemini_tools`) AND
> separate FastAPI routes AND a hand-written MCP shim — three copies of the same
> surface. OpenBB has one.
> (2) Adopt a `to_llm()`-style serializer on Vysted's result envelope. When an
> agent tool returns data, it should go through one canonical "compact records
> for the model" path, not ad-hoc per-tool formatting.

---

## 4. The CLI

(`cli/openbb_cli/`)

The CLI is the proof that the "introspect-once, project-everywhere" model
generalizes to a _fourth_ surface, and it does it the same way MCP does.

- `PlatformController` (`controllers/base_platform_controller.py:31-71`)
  wraps the **already-built Python API** (`from openbb import obb`) and feeds it
  to `ArgparseClassProcessor`
  (`argparse_translator/argparse_class_processor.py`), which introspects the
  `obb` object tree + the OpenBB OpenAPI reference (`obb.reference["paths"]`,
  `base_platform_controller.py:53-57`) and **auto-generates an argparse parser
  per command** — the CLI menu, the `--symbol`/`--provider` flags, help text, and
  tab-completion all fall out of the same metadata that built the REST/MCP
  schemas. No command is hand-written in the CLI.
- An interesting CLI-only idea: an **OBBject registry** (`obbject_registry.py`,
  `base_platform_controller._link_obbject_to_data_processing_commands:73-104`)
  lets a user pipe the result of one command (`OBB0`, or a named key) as the
  `--data` input of the next — a session-scoped data clipboard. This is how a
  REPL composes commands without re-fetching.

> **Lesson for Vysted.** The CLI is the strongest evidence for the central
> thesis: OpenBB built ONE API and got Python + REST + MCP + CLI + Excel +
> Workspace _for free_ by introspecting it. Vysted's analog is the sidecar's
> FastAPI app — every surface (MCP server, agent tools, future CLI/automation)
> should be a _projection_ of those routes, generated from their OpenAPI, not a
> parallel hand-maintained list. The OBBject-registry "pipe results between
> commands" idea also maps directly onto Vysted's node-editor / workflow engine
> (`sidecar/services/workflow_engine.py`): a node's output is the next node's
> input — same clipboard pattern, already in Vysted's DNA.

---

## 5. Credentials / BYOK hub

(`core/openbb_core/app/model/credentials.py`)

OpenBB's BYOK model is a single dynamically-built `Credentials` Pydantic model:

- `CredentialsLoader.load()` (`credentials.py:119-169`) asks `ProviderInterface`
  for every provider's required credential keys (`from_providers:115-117`,
  each already namespaced like `fmp_api_key`), adds obbject-extension creds, then
  `create_model("Credentials", ...)` builds one model with every key as an
  `Optional[SecretStr]` field (`format_credentials:60-92`). Each field's
  `description` records which provider owns it.
- Resolution precedence (`credentials.py:119-169` + `model_post_init:193-201`):
  **env var > `~/.openbb_platform/user_settings.json` > unset**. Any
  `*_API_KEY` env var is auto-detected (`credentials.py:142-148`). Values are
  `SecretStr` so they never render in logs/`repr`; a separate `show()` method
  must be called to unmask (`credentials.py:211-219`).
- At query time, `QueryExecutor.filter_credentials` (`query_executor.py:36-63`)
  takes the full `Credentials` dump, keeps only the keys the chosen provider
  declared, and raises a helpful "Missing credential 'fmp_api_key'. Check
  <website> to get it." if a required one is absent — but a provider can set
  `require_credentials = False` (`fetcher.py:40`) to opt out (free data sources).

> **Lesson for Vysted.** OpenBB stores keys in a plaintext JSON
> (`user_settings.json`) — Vysted's keychain model (Tauri Rust
> `keychain_set/get/delete`, renderer-reads-then-passes-in-request) is strictly
> better and should NOT regress to OpenBB's file model. What IS worth copying:
> (a) **credential keys are owned/declared by the provider** (`fmp_api_key` is
> auto-namespaced from `name + credential`), so the BYOK UI can render
> "this provider needs key X, get it at <website>, here are <instructions>"
> directly from the provider object — Vysted's `Provider`-like plugin object
> should carry `credentials: [...]`, `website`, and `instructions` exactly like
> `provider.py:42-54`. (b) The `require_credentials` opt-out flag for free
> sources (yfinance needs none) keeps the "missing key" UX honest. (c) The
> per-query `filter_credentials` that passes a provider ONLY its own keys is the
> right least-privilege shape for Vysted's "renderer passes secret in request
> header" flow (the v0.6.5 Tradesa pattern) — never hand a plugin the whole
> keychain, only its declared keys.

---

## 6. Agent / copilot / LLM integration — and how it calls the platform

OpenBB's LLM strategy is **"don't build an agent loop; expose the platform as
tools and let the client's agent drive."** There is no LLM-provider abstraction,
no chat runtime, no model-calling code in this repo. The integration is three
surfaces:

### 6.1 `OBBject.to_llm()` — the data→LLM serializer

(`model/obbject.py:337-353`) — the only LLM-aware code in core. Every result can
be flattened to compact JSON records for a model's context.

### 6.2 The MCP server — the primary agent entry point

(`extensions/mcp_server/openbb_mcp_server/app/app.py`, README) — covered in §7.

### 6.3 The Workspace agent/widget bridge

(`extensions/platform_api/`) — `openbb-api` launches the FastAPI app as an
OpenBB Workspace "custom backend" and auto-generates a `widgets.json`
(`platform_api/.../utils/widgets.py`, `merge_agents.py`) from the OpenAPI spec so
Workspace's AI agents and dashboards can consume the endpoints. Same projection
principle: introspect the OpenAPI → emit a widget manifest. Agents-for-Workspace
themselves live in a separate repo (`README.md:55-57`,
`OpenBB-finance/agents-for-openbb`), confirming the platform stays
agent-runtime-agnostic.

> **Lesson for Vysted.** This is the sharpest contrast with Vysted's current
> design and the most important strategic finding. **OpenBB has no
> `agent_runtime`, no `llm-providers`, no per-vendor tool schemas** — it pushes
> all of that to the client (Claude Desktop, Cursor, Workspace agents) and only
> ships _tools + skills + prompts_ over MCP. Vysted has gone the other way: it
> ships a full in-house agent loop (`sidecar/services/agent_runtime.py`),
> multi-vendor adapters (`src/store/llm-providers.ts`, `sidecar/services/llm/`),
> AND a hand-maintained per-vendor tool schema catalog
> (`agent_tools/schemas.py`). Both are valid — Vysted's positioning (a
> self-contained desktop terminal, BYOK, works offline-of-an-external-agent)
> _justifies_ owning the loop in a way a data library doesn't. But the OpenBB
> lesson stands: **the tool SURFACE the agent sees should be generated from the
> route definitions, not hand-written three times.** Vysted's CLAUDE.md already
> records the pain ("a model only calls tools if the adapter SENT a `tools=`
> schema... add a handler AND a `TOOL_SCHEMAS` entry AND an agent allow-list —
> all three"). OpenBB's `FastMCP.from_fastapi` eliminates the second of those by
> construction. Vysted should converge: one route declaration → derived
> JSON-Schema → per-vendor tool schema via a thin transformer, so adding a route
> automatically offers it to in-house agents AND the MCP server.

---

## 7. How OpenBB exposes itself programmatically (Python / REST / MCP)

### 7.1 Python API — a _generated_ static package

(`core/openbb_core/app/static/package_builder.py`, `core/openbb/package/`)

`obb.equity.price.historical("AAPL")` is not hand-written. `PackageBuilder`
(`static/package_builder.py`) introspects `RouterLoader` + `ProviderInterface` +
the OpenAPI reference and **writes real `.py` files** into `core/openbb/package/`
with full type hints, docstrings, and per-provider parameter docs. The result is
IDE-autocompletable, statically-typed, and zero-runtime-cost. `Container` /
`app_factory.py` assemble the `obb` object from these generated modules. (The
import side reads `obb.reference["paths"]` — the same metadata the CLI consumes.)

### 7.2 REST API

(`core/openbb_core/api/rest_api.py`) — a stock FastAPI app. `AppLoader.add_routers`
mounts the auto-built `router_commands` (the package router) plus `system` /
`coverage` / auth routers under `system.api_settings.prefix`
(`rest_api.py:74-88`). Exception handlers map `OpenBBError`/`EmptyDataError` to
clean 4xx/5xx JSON (`api/exception_handlers.py`). Launched via `openbb-api`
(`platform_api`) on `127.0.0.1:6900`. This single FastAPI app is the substrate
everything else is generated from.

### 7.3 MCP — `FastMCP.from_fastapi(app)`, the framework keystone

(`extensions/mcp_server/openbb_mcp_server/app/app.py:527-534`)

This is the single most important file for Vysted's MCP-as-framework goal. The
entire MCP server is **derived from the FastAPI app** — every REST route becomes
an MCP tool automatically. Highlights:

- `create_mcp_server(settings, fastapi_app)` calls
  `FastMCP.from_fastapi(app, mcp_component_fn=customize_components,
route_maps=..., auth=...)` (`app.py:346-534`). No tool is hand-registered;
  they fall out of the routes.
- **Per-route MCP metadata via `openapi_extra["mcp_config"]`** — the same
  `@router.command(..., mcp_config={...})` channel that carries `widget_config`
  (`router.py:99-106`). `customize_components` (`app.py:404-518`) reads it to
  rename the tool, set tags, `expose: False` to hide a route, exclude args,
  compress the JSON-Schema (`compress_schema`, `app.py:457-464`), and trim
  verbose descriptions for token economy.
- **Tool categorization + progressive discovery** to fight context-window bloat
  (`app.py:379-549`, README §"Tool Discovery"). Tools are grouped into
  `category/subcategory` from the route path (`app.py:423-449`). With
  `enable_tool_discovery`, ALL tools start _disabled_ and the server exposes four
  admin tools — `available_categories`, `available_tools`, `activate_tools`,
  `activate_category` (`app.py:599-734`) — so an agent browses the catalog and
  enables only what it needs, **per-session** (each client has its own active
  toolset; `mcp.disable(all)` then selective `enable`, `app.py:536-549`).
- **Bundled skills + prompts as first-class MCP citizens** (`app.py:140-342`,
  `561-594`). The server ships Markdown SKILL guides
  (`skills/{develop_extension,build_workspace_app,configure_mcp_server,
work_with_server}/SKILL.md`) exposed as MCP resources at
  `skill://<name>/SKILL.md`, vendor skill providers (Claude/Cursor/VSCode/Copilot/
  Codex/Gemini/Goose/OpenCode — `app.py:65-74`), a configurable system prompt,
  JSON-defined "server prompts" that encode multi-tool workflows (the
  `equity_analysis` prompt in the README chains 5 tools), and an `install_skill`
  tool that lets an agent write a new skill at runtime (`app.py:741-869`).
  `PromptsAsTools`/`ResourcesAsTools` transforms expose prompts+resources even to
  tool-only clients (`app.py:738-739`).
- Transports: `stdio` (Claude Desktop) and `streamable-http`/`sse`
  (`app.py:935-1021`). Auth is optional basic-auth, server- and client-side
  (README §Authentication).

> **Lesson for Vysted (THE headline).** Vysted's `sidecar/services/mcp_server.py`
> currently hand-writes each MCP tool as "a thin shim that calls the
> corresponding sidecar HTTP endpoint via an in-process `httpx.AsyncClient`"
> (its own docstring). That is N hand-maintained shims that drift from the
> routes. **OpenBB proves the shim is unnecessary: `FastMCP.from_fastapi(app)`
> turns the whole FastAPI app into the MCP surface in one call.** Vysted runs the
> same FastMCP library — it should adopt `from_fastapi` and delete the per-tool
> shims, keeping hand-written tools only for the genuinely non-REST ones
> (`invoke_agent`, which aggregates an SSE stream — note OpenBB also special-cases
> nothing like this because it has no agent loop). Then steal four concrete
> mechanisms wholesale: (1) **`openapi_extra["mcp_config"]` per-route control**
> (rename/hide/tag/exclude-args/compress) — Vysted's safety story benefits
> directly: mark every non-GET broker route `expose: False` so it can NEVER
> surface as an agent-callable tool, a fourth defense-in-depth layer on top of
> the §6.5 model. (2) **Schema compression + brief-description trimming** for
> token economy. (3) **Progressive tool discovery** (start disabled, browse +
> activate per session) — Vysted's plugin catalog will eventually exceed a
> sane initial tool list; this is the proven fix. (4) **Skills as MCP
> resources + server-prompts as encoded multi-tool workflows** — this is a
> first-class way to ship Vysted's "research-lab" playbooks (e.g. the
> Strategy-Critic / Buffett-agent workflows) to any external MCP client, and it
> maps onto Vysted's existing first-party-agent JSONs.

---

## 8. Cross-cutting observations worth keeping

- **Singletons everywhere for the expensive, idempotent maps** — `ExtensionLoader`,
  `ProviderInterface`, `RegistryMap` are `SingletonMeta`/`@lru_cache`. The
  registry build is paid once. Vysted's `provider_registry`/`mcp_server` already
  cache (`get_mcp_server` lazy-builds once) — keep that.
- **`extra="allow"` is load-bearing**, not laziness — it is _what makes provider
  extras possible_ without contract churn. Vysted's `sidecar/models/` should
  adopt `extra="allow"` on the data models that plugins will extend, mirroring
  `Data` (`data.py:77-85`). (Keep strict `extra="forbid"` on the safety-critical
  ones — broker orders, audit log — where unknown fields must be rejected.)
- **Fault-tolerant load** — one bad provider warns, never crashes the registry
  (`registry.py:44-54`). Vysted's plugin loader should match: a plugin that fails
  `initialize()` degrades to "unavailable" in the plugin manager, never takes
  down the sidecar.
- **The result envelope carries provenance** — `OBBject.provider` + `warnings` +
  `extra.results_metadata`. Vysted's data responses should always say which
  provider served them (critical once multiple plugins serve one `kind`).
- **AGPL-3.0** (`README.md:153`) — same license family as Vysted's AGPL/commercial
  dual license; OpenBB's provider/extension split is a real-world template for
  keeping the open core open while commercial providers stay separate packages.

---

## 9. Concrete Vysted action map (priority order)

1. **Adopt `FastMCP.from_fastapi(app)` in `sidecar/services/mcp_server.py`** and
   delete the per-tool httpx shims; keep only `invoke_agent` hand-written. Single
   biggest leverage for the MCP-as-framework goal. (§7.3)
2. **Add `openapi_extra["mcp_config"]` to Vysted's FastAPI routes** — use
   `expose: False` on every non-GET / broker-execution route as a 4th
   defense-in-depth layer; use tags/compression for token economy. (§7.3)
3. **Make the agent-tool schema a derivation of the route OpenAPI**, not a
   third hand-maintained copy in `agent_tools/schemas.py`. One route → derived
   JSON-Schema → per-vendor transform. (§3, §6)
4. **Give the plugin `DataSource` capability a `Provider`-shaped registration**:
   `{standardModelKey → fetcher}`, plus `credentials`, `website`, `instructions`
   so the BYOK UI renders from the plugin object. Resolve the registry by model
   key + preference order, not `if asset_class`. (§1, §5)
5. **Add `provider` + `extra="allow"` to non-safety `sidecar/models/`** so plugins
   can extend data shapes without contract changes; add a `to_llm()`-style
   compact serializer on the result path. (§2, §3, §8)
6. **Ship skills + server-prompts over MCP** (workflows like Strategy Critic,
   per-agent playbooks) as MCP resources/prompts — projects Vysted's research-lab
   IP to any external agent client for free. (§7.3)
7. **Do NOT copy**: entry-point discovery (breaks under PyInstaller `--onefile`),
   plaintext `user_settings.json` credential storage (keychain is better), or the
   full `make_dataclass` param-merge engine (premature until 2+ same-kind plugins).

---

### Key file index (for the next session)

| Concern                       | OpenBB file                                                                      |
| ----------------------------- | -------------------------------------------------------------------------------- |
| Fetcher TET contract          | `core/openbb_core/provider/abstract/fetcher.py`                                  |
| Standard input/output models  | `core/openbb_core/provider/abstract/{query_params,data}.py`                      |
| Provider registration object  | `core/openbb_core/provider/abstract/provider.py`                                 |
| Standard model example        | `core/openbb_core/provider/standard_models/equity_historical.py`                 |
| Provider impl example         | `providers/fmp/openbb_fmp/models/equity_historical.py` + `__init__.py`           |
| Entry-point discovery         | `core/openbb_core/app/extension_loader.py`, `provider/registry.py`               |
| Dynamic model merge           | `core/openbb_core/app/provider_interface.py`, `provider/registry_map.py`         |
| Router + signature injection  | `core/openbb_core/app/router.py`, `extensions/equity/.../price_router.py`        |
| Query → executor path         | `core/openbb_core/app/query.py`, `provider/query_executor.py`                    |
| Result envelope (+ to_llm)    | `core/openbb_core/app/model/obbject.py`                                          |
| Credentials / BYOK hub        | `core/openbb_core/app/model/credentials.py`                                      |
| Generated Python API          | `core/openbb_core/app/static/package_builder.py`                                 |
| REST app                      | `core/openbb_core/api/rest_api.py`                                               |
| MCP-from-FastAPI (keystone)   | `extensions/mcp_server/openbb_mcp_server/app/app.py`                             |
| MCP framework playbook        | `extensions/mcp_server/README.md`                                                |
| Workspace widget/agent bridge | `extensions/platform_api/`                                                       |
| CLI auto-generation           | `cli/openbb_cli/controllers/base_platform_controller.py`, `argparse_translator/` |
