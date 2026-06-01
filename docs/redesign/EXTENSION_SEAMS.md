# Extension seams — where Pass B plugs in

_Pass A's overarching principle was **piggyback foundations**: wherever a system was
touched, leave it clean and extensible so the Pass-B work (deep multi-source stock
research + India/region-aware data & feeds) plugs in via **config + an adapter**, not a
refactor. This document is the map of those seams — for each: where a new thing
registers, one concrete example, and how clean the seam is today. Pass A built **no**
research or Indian-data features; it left the seams._

Four headline seams (capabilities, providers, models, regions) + four supporting ones.

---

## 1. Agent capabilities / research tools — `catalog.py`

**Where:** `sidecar/services/agent_tools/catalog.py` is the ONE source of truth
(Constitution Principle II). Declaring a `Capability` auto-projects it to `TOOL_SCHEMAS`
(`schemas.py`), the custom-agent allow-list (`models/custom_agent.KNOWN_TOOL_IDS`), and —
unless internal-only — the external MCP surface, all by the same name. A handler module
registers the implementation; `registry_v0_6_0.py` wires its `register()`.

**Example — add a `deep_research` tool (the core Pass-B capability):**

1. `sidecar/services/agent_tools/deep_research.py`: `async def _deep_research(args) -> dict`
   returning `{"ok": True, ...}` + a `register()` calling `register_tool("deep_research", _deep_research)`.
2. `catalog.py`: add `_cap("deep_research", ..., domain="research", read_only=True, kind="read_handler")`.
   It auto-projects to schemas + the allow-list + MCP. If `"research"` isn't in the `Domain`
   Literal (catalog.py ~:34), add it.
3. Wire `register()` into `registry_v0_6_0.register_v0_6_0_tools()`.
4. Add `"deep_research"` to a first-party agent's JSON `tools` allow-list to make it reachable.
5. `pytest test_capability_catalog.py test_mcp_catalog_parity.py` (the parity gates).

**Cleanliness:** ✅ Very clean — this IS the extension subsystem. A new read tool = 2 files
(catalog + handler) + one aggregator line + one agent JSON. No refactor for Pass-B research.

---

## 2. Data providers — `provider_registry.py` (the India equity seam)

**Where:** `sidecar/services/provider_registry.py` is already an **adapter registry** — a
preference-ordered `_PROVIDERS` tuple of `ProviderDeclaration(id, rank, asset_classes,
serves={...callables})` keyed by model-key (quote / ohlcv / fundamentals / statements /
analyst / macro_series). `yfinance_provider.py` is the reference no-key equity provider
(each fn raises `ProviderError`, sets `provider`, normalizes symbols; **.NS India tickers
already resolve through it**, and `screener_universes/nifty50.json` already ships).

**Example — add an India NSE provider:**

1. `sidecar/services/india_provider.py` exposing the same callables as yfinance
   (`get_quote` / `get_history` / `get_fundamentals`), `provider="nse"`.
2. Append `ProviderDeclaration(id="nse", rank=20, asset_classes=frozenset({"equity"}),
region=frozenset({"IN"}), serves={"quote": ..., "ohlcv": ...})`.
3. `/health` picks it up automatically via `active_providers()`.

**Cleanliness:** ✅ very clean adapter registry, with ONE ~15-line refactor remaining to
unlock **region routing**: add `region: frozenset[str] = frozenset()` to
`ProviderDeclaration` (mirroring the existing `asset_classes` field + `serves_asset_class`
predicate) and a `region` param (default `"US"`, empty set = any) to `_candidates` /
`_resolve_*` / the public accessors. No router changes (accessors keep the US default).
**Pass A intentionally did NOT make this edit** (it would be a no-op until India data
exists); it is the single, well-scoped change that turns this into a pure config+adapter
region seam. Supporting tables: macro upstreams (`macro/macro_router.py` `_PROVIDERS` dict +
the frozen `MacroProvider` Literal — widen to a registry-derived set for a pure seam), news
sources (`news_provider.py` `_MARKET_RSS_FEEDS` — extract to a region-keyed `feeds` config),
screener universes (drop `<id>.json` into `screener_universes/` + the `ScreenerUniverseId`
Literal). The `is_available()`-gated MCP-subprocess provider (`sec_filings_provider.py`,
`openbb_mcp_provider.py`) is the cleanest template for a heavyweight research source.

---

## 3. Model registry — `model_registry.json` (made clean in Pass A item 5)

**Where:** `sidecar/config/model_registry.json` is now the single source of truth for
providers, per-provider `default_model` + `known_models`, and the BudgetGuard price table.
The sidecar derives `PROVIDER_INFO`, `_resolve_model`, `budget_guard` pricing, and
`custom_agent.KNOWN_PROVIDER_IDS` from it; `GET /llm/providers` serves `default_model` +
`known_models` to the frontend (consumed at runtime; the static `DEFAULT_PROVIDERS` /
`KNOWN_MODELS_BY_PROVIDER` are an offline fallback only).

**Example — add/update a model:** edit ONE JSON row's `default_model` / `known_models` /
`prices`. No code change. **Add a new provider:** the JSON row + the closed `LLMProviderId`
Literal in `sidecar/models/llm.py` AND `types/ai.ts` (kept closed by design for type safety)

- a one-line case in the `get_provider()` dispatch factory.

**Cleanliness:** ✅ clean for models (JSON-only). Adding a _provider_ is config + 2 Literal
edits + one factory case — acceptable and explicit (type safety, not drift). This was a
6-copies-across-2-languages mess before item 5.

---

## 4. Region / locale — `region.ts` + `settings` + `format.ts` (sidecar `config.py`)

**Where (frontend):** `src/lib/region.ts` is the pure registry (`REGIONS` = US / IN /
GLOBAL, each with `locale` + `currency`). The active region is a `region` field on the
settings bundle (`store/settings.ts`, default `US`, persisted + a Settings → Preferences
dropdown). The read seam is `src/lib/format.ts` `activeLocale()` — the formatters read the
active region's locale (default US → `en-US`, identical to before).

**Where (sidecar, for Pass B):** add `get_region() -> str` (default `"US"`) to
`sidecar/config.py`, and thread it as the `region` hint into `provider_registry` accessors
(seam #2) + the screener/macro handlers (which hardcode US defaults: `sp500`, `fred`).

**Example — make data India-first (Pass B):** set the region to `IN`; the
`provider_registry` region param (seam #2) prefers the `region={"IN"}` NSE provider;
screener defaults to `nifty50`; macro defaults to an India upstream; `format.ts` already
uses `en-IN` grouping; add FX so `currency` (already carried in `region.ts`) applies to
converted values.

**Cleanliness:** ✅ greenfield seam — Pass A created the setting + the single frontend read
point with **zero default behavior change** (US). Pass B adds the sidecar `get_region()`
read + the provider region param. **Pass A built no Indian data/feeds** (per scope) — only
the setting and the read seam. The catalog schemas are already region-ready (they enumerate
`nifty50`, ECB/IMF/world-bank) — only the handler-side region default is missing.

---

## Supporting seams

- **Host actions (cockpit-driving).** `catalog.py` `_cap(..., kind="host_action",
read_only=False)` auto-stages on the sidecar; pair it with a frontend edit in
  `src/lib/host-actions.ts` (`HOST_ACTION_NAMES` + a `describeHostAction`/`applyHostAction`
  case). _Note: `HOST_ACTION_NAMES` is a hand-maintained mirror of the catalog's host-action
  ids with no parity test — a Pass-B candidate for a generated constant or a cross-check._
  The chart act-path now uses the always-consumed `store/chart-command.ts` channel — a clean
  place for a future `name→ticker` resolver to plug in (Pass-B research could deepen it).
- **Agent autonomy.** `store/agent-autonomy.ts` (`ask | auto`) is orthogonal to the four
  intent modes; the auto-apply hook is the single `enqueue` chokepoint in
  `store/proposed-changes.ts` (orders hard-excluded). A new autonomy level adds a value + a
  branch there.
- **Crypto exchanges.** `ccxt_provider.SUPPORTED_EXCHANGES` tuple + `DEFAULT_CRYPTO_EXCHANGE`.
- **Shared cache.** New providers should route reads through `services/data_cache.py`
  (SQLite TTL) rather than re-rolling caching.

---

## What Pass A changed to make these clean

- **Model registry (item 5):** collapsed 6 hardcoded provider/model copies into one JSON;
  extended `GET /llm/providers` so the frontend consumes it at runtime.
- **Region (item 8):** created `region.ts` + the settings field + the `format.ts` read point.
- **Chart command channel (item 6):** `store/chart-command.ts` — a clean host→chart seam
  that replaced the dropped opt-in sync-bus broadcast.
- Everything else (capability catalog, provider registry, macro/news/universe tables) was
  **already** a clean-ish seam; this doc records the one small refactor each needs (noted
  inline) so Pass B plugs in via config + an adapter.
