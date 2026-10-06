# Sidecar API

The Python sidecar (`sidecar/`) is a FastAPI service on localhost that serves the
data layer. The Tauri core spawns it on a free port at launch and resolves the
per-OS application data directory for it; the frontend reaches it over HTTP and
WebSocket.

This document is the contract. It is updated in the same commit as any sidecar
API change.

## Connecting

- **Port** — assigned by the Tauri core and exposed to the frontend via the
  `get_sidecar_port` Tauri command. `src/lib/sidecar-client.ts` wraps this:
  `getSidecarBaseUrl()` returns `http://127.0.0.1:<port>` (cached).
- **Origin guard** — the sidecar binds to `127.0.0.1` only and answers `403`
  (`{"detail": "origin not allowed"}`; a WebSocket closes with `1008`) to any
  request whose `Origin` header is not one of `ALLOWED_ORIGINS` in
  `sidecar/app.py`: `tauri://localhost`, `http(s)://tauri.localhost` and the Vite
  dev server (`http://localhost:5173`, `http://127.0.0.1:5173`). A request with no
  `Origin` (curl, the Python MCP bridge) passes. The same list drives the CORS
  middleware, so the WebView uses plain `fetch` with no `tauri-plugin-http`.
- **Data directory** — the Tauri core passes `--data-dir <path>` (the per-OS app
  data dir). The sidecar owns the portfolio SQLite database and saved
  `.vysted-workspace` files beneath it. See `sidecar/config.py`.
- **Errors** — provider failures return HTTP `502` with `{"detail": "..."}`.
  `sidecarGet` throws `SidecarError` (carrying `status` + message).

## Providers

| Data class                                                    | Provider                                    | Notes                                    |
| ------------------------------------------------------------- | ------------------------------------------- | ---------------------------------------- |
| Equity quotes / history / fundamentals / statements / ratings | **yfinance**                                | No API key required — the default.       |
| Crypto quotes / history / live stream                         | **ccxt** (Bybit, Binance, Kraken, Coinbase) | ccxt.pro WebSockets for the live stream. |
| Macro / economic series                                       | **FRED / ECB / IMF / World Bank**           | Through `/macro` (see the route index).  |

### OpenBB ODP — deferred to Phase 2

Phase 1.A ships yfinance + ccxt as the working providers. The OpenBB Platform
(`openbb`) is **not** in `requirements.txt` this phase. Rationale (a Tier-3
decision — see `CLAUDE.md` "Decision authority"):

- The sidecar is a PyInstaller `--onefile` binary. The OpenBB meta-package is a
  very large dependency tree whose `--onefile` bundling cannot be vetted against
  the macOS CI runner locally — a real run-consuming risk.
- The blueprint already schedules an **"OpenBB ODP wrap plugin"** for Phase 2 as
  a data-only plugin. Building it there, on the plugin contract, is cleaner than
  baking it into the core sidecar now and re-extracting it later.
- `services/provider_registry.py` is provider-agnostic and
  `services/openbb_provider.py` is an import-guarded seam — OpenBB slots in later
  with no router or panel changes.

yfinance covers equity quotes, history, fundamentals, the three financial
statements, and analyst ratings; ccxt covers crypto. Together they serve every
Phase 1 panel. Macro series are served by the FRED, ECB, IMF and World Bank
providers (see `/macro`).

## REST endpoints

### Health

- `GET /health` → `{ status, service, version, providers }` — liveness probe;
  `providers` reports which provider currently backs each data class.

### Quotes — `Quote`

- `GET /quotes/{symbol}?asset_class=equity|crypto` → `Quote`
- `GET /quotes?symbols=AAPL,MSFT,NVDA&asset_class=equity` → `Quote[]` — batch for
  the watchlist; a symbol that fails to resolve is skipped, not fatal.

### History — `OHLCVSeries`

- `GET /history/{symbol}?timeframe=1d&range=1y&asset_class=equity` → `OHLCVSeries`
  - `timeframe`: `1m`, `5m`, `15m`, `30m`, `1h`, `1d`, `1wk`, `1mo`
  - `range`: optional provider lookback override (e.g. `5d`, `1y`, `max`)

### Crypto

- `GET /crypto/exchanges` → `{ exchanges: string[] }`
- `GET /crypto/ticker?exchange=binance&symbol=BTC/USDT` → `Quote`
- `GET /crypto/history?exchange=binance&symbol=BTC/USDT&timeframe=1d` → `OHLCVSeries`

### Fundamentals

- `GET /fundamentals/{symbol}` → `Fundamentals`
- `GET /fundamentals/{symbol}/income` → `IncomeStatement`
- `GET /fundamentals/{symbol}/balance` → `BalanceSheet`
- `GET /fundamentals/{symbol}/cashflow` → `CashFlowStatement`
- `GET /fundamentals/{symbol}/ratings` → `AnalystRating`

### Macro

- `GET /macro/{series_id}` → `MacroSeries` (or `MacroSeriesExtended` when a
  `provider` of FRED / ECB / IMF / World Bank is passed);
  `GET /macro/search` and `GET /macro/catalog` list the available series.

### Delegate runs — `RunSummary` / `RunDetail`

Durable background agent runs (`routers/runs.py`, models in `models/run.py`).
Every key is **snake_case, in both directions**; there are no camelCase aliases
(the frontend reader is `src/lib/delegate-runs.ts`, pinned by
`sidecar/tests/test_runs_router.py`).

- `POST /agents/{agent_id}/runs` → `201 { run_id }` — body
  `{ prompt, context_snapshot?, provider?, model?, api_key?, budget?, options? }`;
  `budget` is `{ max_tokens?, max_spend_usd?, max_wall_seconds?, max_steps? }`
  (each > 0; an omitted ceiling takes the server default). An unknown key is a
  `422`. `api_key` crosses for the run only: never stored, logged or echoed.
- `GET /runs` → `{ runs: RunSummary[] }`, newest first. `RunSummary` is
  `{ id, agent_id, agent_name, mode, status, cost, budget, provider, model, plan,
activity, detail, question, created_at, updated_at }`; `cost` is
  `{ tokens, spend_usd, steps }` (`spend_usd` is an estimate, not a billed
  figure); timestamps are epoch seconds.
- `GET /runs/{run_id}` → `RunDetail` = `RunSummary` +
  `{ transcript, checkpoint_messages, answer, brief, host_actions }`;
  `host_actions` items are `{ tool_call_id, name, input }`. Unknown id → `404`.
- `POST /runs/{run_id}/cancel` → `{ cancelled: true }`;
  `POST /runs/{run_id}/start` → `{ started: true }`;
  `POST /runs/{run_id}/answer` (body `{ answer }`) → `{ resumed: true }`;
  `POST /runs/{run_id}/resume` → `{ resumed: true }`. Start, answer and resume
  take the BYOK key in the `X-LLM-Api-Key` header. Unknown run → `404`; an
  illegal state change → `409`.

## WebSocket endpoints

- `WS /crypto/stream?exchange=binance&symbol=BTC/USDT` — pushes a JSON-serialised
  `Quote` on every ticker update. No frontend client opens it (R15-DATA-109 removed
  the unused `openCryptoStream()` helper; the watchlist polls REST). The ccxt.pro
  exchange is always closed on disconnect.

## Route index

Every route the sidecar serves, generated from its `/openapi.json` (111
operations). The sections above describe the contracts that need more than
a line; this index is the complete list. Regenerate it from `/openapi.json`
when a route changes.

### `health`

- `GET /health` — Health

### `quotes`

- `GET /quotes/{symbol}` — Get Quote
- `GET /quotes` — Get Quotes

### `history`

- `GET /history/{symbol}` — Get History

### `crypto`

- `GET /crypto/exchanges` — List Exchanges
- `GET /crypto/ticker` — Crypto Ticker
- `GET /crypto/history` — Crypto History

### `data-sources`

- `GET /data-sources` — Get Data Sources

### `disclosures`

- `GET /disclosures/announcements` — Get Announcements
- `GET /disclosures/results` — Get Results
- `GET /disclosures/shareholding` — Get Shareholding
- `GET /disclosures/corporate-actions` — Get Corporate Actions
- `GET /disclosures/deals` — Get Deals

### `fundamentals`

- `GET /fundamentals/{symbol}` — Get Fundamentals
- `GET /fundamentals/{symbol}/narrative` — Get Company Narrative
- `GET /fundamentals/{symbol}/income` — Get Income Statement
- `GET /fundamentals/{symbol}/balance` — Get Balance Sheet
- `GET /fundamentals/{symbol}/cashflow` — Get Cash Flow
- `GET /fundamentals/{symbol}/ratings` — Get Analyst Rating
- `GET /fundamentals/{symbol}/ratings/history` — Get Ratings History
- `GET /fundamentals/{symbol}/ratings/price-target-history` — Get Price Target History
- `GET /fundamentals/{symbol}/ratings/individual` — Get Individual Analysts

### `macro`

- `GET /macro/search` — Search Macro Series
- `GET /macro/catalog` — Get Macro Catalog
- `GET /macro/{series_id}` — Get Macro Series

### `indicators`

- `GET /indicators` — List Indicators
- `GET /indicators/suggested` — Suggested Indicators
- `GET /indicators/{symbol}` — Get Indicators

### `portfolio`

- `GET /portfolio/positions` — List Positions

### `news`

- `GET /news` — Get News
- `GET /news/sources/status` — Get News Sources Status

### `resolve`

- `GET /resolve` — Resolve Symbol
- `GET /resolve/autocomplete` — Autocomplete Symbols

### `workspace`

- `GET /workspace` — List Workspaces
- `POST /workspace` — Save Workspace
- `GET /workspace/{name}` — Get Workspace
- `DELETE /workspace/{name}` — Delete Workspace

### `plugins`

- `GET /plugins` — List Plugin Configs
- `GET /plugins/{plugin_id}/config` — Get Plugin Config
- `POST /plugins/{plugin_id}/config` — Save Plugin Config
- `DELETE /plugins/{plugin_id}/config` — Delete Plugin Config

### `llm`

- `GET /llm/providers` — Get Providers
- `GET /llm/models` — Get Models
- `POST /llm/keys/validate` — Validate Key
- `POST /llm/chat` — Chat Stream

### `agents`

- `POST /agents/actions/ack` — Ack Action
- `GET /agents` — List Agents
- `POST /agents/{agent_id}/invoke` — Invoke Agent

### `custom-agents`

- `GET /custom-agents` — List Custom Agents
- `POST /custom-agents` — Create Custom Agent
- `GET /custom-agents/tool-ids` — List Tool Ids
- `GET /custom-agents/{agent_id}` — Get Custom Agent
- `PUT /custom-agents/{agent_id}` — Update Custom Agent
- `DELETE /custom-agents/{agent_id}` — Delete Custom Agent

### `runs`

- `POST /agents/{agent_id}/runs` — Launch Run
- `GET /runs` — List Runs
- `GET /runs/{run_id}` — Get Run
- `POST /runs/{run_id}/cancel` — Cancel Run
- `POST /runs/{run_id}/start` — Start Run
- `POST /runs/{run_id}/answer` — Answer Run
- `POST /runs/{run_id}/resume` — Resume Run

### `mcp`

- `GET /mcp/status` — Get Mcp Status
- `GET /openbb-mcp/status` — Get Openbb Mcp Status

### `sec`

- `GET /sec/status` — Get Status
- `GET /sec/filings/search` — Search Companies
- `GET /sec/filings` — List Filings
- `GET /sec/filings/{accession}` — Get Filing
- `GET /sec/insider/{identifier}` — List Insider Transactions

### `workflow`

- `POST /workflow/run` — Run Workflow
- `GET /workflow/node-types` — List Node Types
- `POST /workflow/save` — Save Workflow
- `GET /workflow/saved` — List Saved Workflows
- `GET /workflow/saved/{workflow_id}` — Get Saved Workflow
- `DELETE /workflow/saved/{workflow_id}` — Delete Saved Workflow
- `GET /workflow/schedules` — List Schedules
- `POST /workflow/schedules` — Create Schedule
- `PATCH /workflow/schedules/{schedule_id}` — Update Schedule
- `DELETE /workflow/schedules/{schedule_id}` — Delete Schedule
- `PUT /workflow/webhooks/{ref}` — Register Webhook
- `GET /workflow/webhooks` — List Webhooks

### `backtest`

- `POST /backtest/run` — Run Backtest
- `GET /backtest/strategies` — List Strategies
- `POST /backtest/strategies/custom/validate` — Validate Custom Strategy
- `GET /backtest/runs` — List Runs
- `GET /backtest/runs/{run_id}` — Get Run

### `quant`

- `POST /quant/option/price` — Option Price
- `POST /quant/option/greeks` — Option Greeks
- `POST /quant/bond/price` — Bond Price
- `POST /quant/yield-curve` — Yield Curve Bootstrap
- `GET /quant/option/chain/{symbol}` — Option Chain View

### `earnings`

- `GET /earnings/upcoming` — Get Upcoming
- `GET /earnings/{symbol}/history` — Get History
- `GET /earnings/{symbol}/surprises` — Get Surprises
- `GET /earnings/{symbol}/estimates` — Get Estimate Detail

### `screener`

- `POST /screener/run` — Run Screener
- `POST /screener/run/stream` — Run Screener Stream
- `POST /screener/formula/validate` — Validate Formula
- `GET /screener/default-universe` — Get Default Universe
- `GET /screener/universe` — Get Universe

### `search`

- `GET /search/status` — Search Status
- `GET /search/searxng/status` — Searxng Status
- `POST /search/searxng/setup` — Searxng Setup
- `POST /search/searxng/teardown` — Searxng Teardown

### `system`

- `GET /system/hardware` — Get Hardware
- `GET /system/local-model-recommendation` — Local Model Recommendation
- `GET /system/ollama/status` — Ollama Status
- `POST /system/ollama/pull` — Pull Ollama Model
- `GET /system/provider-health` — Get Provider Health
- `POST /system/provider-health/trip` — Trip Provider Health
- `POST /system/provider-health/reset` — Reset Provider Health
- `GET /system/diagnostics` — Get Diagnostics

## Models & the TypeScript contract

Pydantic models live in `sidecar/models/`. `types/data.ts` is a **hand-maintained
TypeScript mirror** of them. When a Pydantic model changes, update the matching
interface in `types/data.ts` in the same commit. Datetimes cross the wire as
ISO-8601 strings (typed `string` in TypeScript).

Models: `Quote`, `OHLCVBar`, `OHLCVSeries`, `MacroObservation`, `MacroSeries`,
`Fundamentals`, `StatementLine`, `FinancialStatement`, `IncomeStatement`,
`BalanceSheet`, `CashFlowStatement`, `AnalystRating`, `NewsItem`, `Position`,
`PositionInput`.

## Testing

`sidecar/tests/` — every provider is mocked (`tests/conftest.py`); no test makes
a live network call. Run from `sidecar/`: `pytest`.
