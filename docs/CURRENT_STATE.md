# Vysted Terminal — Current State (as of 2026-05-30, pre-redesign baseline)

> An honest inventory of what exists today, written to anchor the "Cursor for
> finance" redesign. It records the working foundation worth keeping and, just
> as deliberately, the scaffolding, dead wiring, and unverified surfaces that
> the redesign should not mistake for done. Sourced from a subsystem-by-
> subsystem read of the live code at `main` HEAD `3123e7c` (Phase 10 handoff),
> the Phase-10 handoff report, and `BLOCKERS.md`. The standing honesty caveat:
> the codebase is **green on every machine-checkable gate** (`pnpm ci-local`
> exit 0, 619 vitest, 942 pytest, §6.5 9/9) and **unproven on most
> human-checkable ones** — live UX, populated visuals, and any BYOK/live-broker
> round-trip are unverified because the harness cannot drive the WKWebView with
> real data and macOS screen capture failed mid-Phase-10.

---

## 0. Foundation update (2026-05-31, branch `001-agent-native-redesign`)

> The body below is the **pre-redesign baseline** (2026-05-30). The redesign's
> **foundation window** has since landed on `001-agent-native-redesign` (not on
> `main`). It does **not** build the user-facing P1/P2/P3 phases, but it closes
> the documented copilot/catalog/runtime gaps the baseline records. Full detail +
> gate results: **`docs/redesign/FOUNDATION_BUILD_REPORT.md`**. Deltas that
> supersede statements below:
>
> - **Single capability catalog** (`sidecar/services/agent_tools/catalog.py`) is
>   now the one source of truth; `TOOL_SCHEMAS`, the custom-agent allow-list, and
>   the external MCP surface all derive from it (Constitution Principle II).
> - **§4 "~11 registered handlers unreachable" → CLOSED.** Every registered,
>   agent-intended handler has a schema (SC-006); 27 internal capabilities.
> - **§4 "Gemini multi-round likely broken" → FIXED** (tool name threaded onto
>   the tool-result message; SC-005).
> - **§11/§4 "custom-agent allow-list stale" → RECONCILED** to the catalog
>   (`KNOWN_TOOL_IDS` is derived; 0 unresolvable tools).
> - **§3.7 MCP "11 hand-maintained tools" → PROJECTED from the catalog** (26
>   tools; same names/schemas as the internal copilot; `readOnlyHint` from
>   `read_only`; standing SC-004 parity audit). A `news` tool now serves both
>   surfaces.
> - **§3.4 "manifest↔instance + `requiredHostVersion` checks documented but not
>   implemented" → IMPLEMENTED** (rejected at load, surfaced); **`PluginConfig`
>   secret resolution** is now keychain-backed (FR-054/SC-015).
> - **§1 "`shell:allow-open` probably denied" → GRANTED.**
> - **§2 boot-path `.expect()` panics → HARDENED** (port-0 sentinel + temp-dir
>   fallback; the app no longer panics with no window).
> - **§4 "shipped default routes to absent Ollama" → GATED**: a keyless provider
>   must be reachable before the first agent call (no silent failure).
>
> §6.5 LOCKED files + `types/plugin.ts` are **byte-for-byte untouched**; the §6.5
> audit stays 9/9.

---

## 1. Executive summary — what the app IS today

- A **Tauri 2.x desktop terminal** (Rust core + Next.js 16 static-export
  frontend + Python 3.13 FastAPI sidecar + two bundled MCP subprocesses) that is
  **local-first and bring-your-own-keys**: no Vysted backend, no account, no
  telemetry. Everything lives under the OS app-data dir + the OS keychain.
- A **multi-panel cockpit** (dockview layout engine) with ~18 first-party
  modules: Chart (50 server-computed indicators + 10 drawing tools),
  Watchlist, News (RSS + optional NewsAPI, VADER sentiment), Portfolio (manual,
  SQLite), Equity Overview, plus Phase-6 analysis panels — Macro, SEC Filings,
  Earnings, Analyst Ratings, Screener, Quant (QuantLib) — and Phase-4/5
  Backtest, Node Editor (workflow), Agent Builder.
- A **real agentic AI copilot** (Phase 10): the tool-use loop in the sidecar is
  now live — adapters send provider-native `tools=` schemas, the model calls
  read/host-action tools, and the loop iterates up to 6 rounds. 13 first-party
  agents (a terminal-aware `copilot` router + 12 investor personas) plus
  user-authored custom agents.
- **BYOK across 7 LLM providers** (Anthropic, OpenAI, Gemini, Groq, Ollama,
  DeepSeek, xAI — five adapters; DeepSeek/xAI ride the OpenAI adapter via
  base-url override). Keys never persist; they ride the request and are read
  from the OS keychain on demand.
- A **read-only broker layer**: genuine Kite Connect OAuth (`generate_session`)
  - read-only positions/holdings/P&L for three Indian brokers (Kite, Dhan,
    Angel One). A full §6.5-safety-gated execution machine (propose→confirm→place,
    kill switch, append-only audit log, position limits) exists in code but is
    **paper-only by hard default and never live-validated**.
- A **plugin platform**: one serializable Tier-1 contract (`types/plugin.ts`,
  six capabilities) + a pure-TS runtime. Three plugins are actually loaded
  (`example`, `openbb-mcp`, `tradesa-v2`); seven broker plugins exist in the
  tree but are **not wired**. No filesystem/marketplace loader yet.
- **Vysted speaks MCP on both sides**: as a _client_ it proxies two bundled MCP
  subprocesses (openbb-mcp fundamentals/macro, sec-edgar-mcp filings) into plain
  REST routes; as a _server_ it re-exposes 11 of its own endpoints as MCP tools
  for external clients (Claude Desktop / Code).
- **Ships unsigned, no release pipeline, version strings stuck at `0.8.0`**
  despite Phase 8/9/9.5/10 merged to `main`. The auto-updater is configured but
  produces no artifacts. Distribution today is "download the CI artifact."

---

## 2. Architecture at a glance

Three processes, one machine, loopback only. The Tauri Rust core owns the OS
surface (windowing, keychain, global kill-switch shortcut, sidecar lifecycle,
dynamic port assignment). The Next.js frontend is a static export served as
files by the core — there is **no Node server at runtime**. The Python FastAPI
sidecar is the data + AI compute brain; it binds `127.0.0.1` on an
OS-assigned port. Two MCP subprocesses are separate PyInstaller binaries the
core spawns and supervises.

```
                       ┌──────────────────────────────────────────────┐
                       │  Tauri Rust core  (src-tauri/src/lib.rs)       │
   OS keychain ◀──────▶│  • keychain_set/get/delete  • kill-switch      │
   (keyring v3)        │  • pick_free_port → SidecarPort(u16)           │
   Cmd+Ctrl+Shift+K ──▶│  • spawns + reaps 3 sidecars  • auto-updater   │
                       └───┬───────────────┬───────────────────┬────────┘
        get_sidecar_port,  │ Rust Command  │ Rust Command      │ shell.sidecar
        keychain_*,        │ (env handoff) │ (env handoff)     │ (--port,--data-dir)
        get_*_mcp_port     │               │                   │
   (Tauri IPC invoke)      ▼               ▼                   ▼
 ┌──────────────────┐  ┌──────────┐   ┌──────────────┐   ┌─────────────────────────┐
 │ Next.js frontend │  │ openbb-  │   │ sec-edgar-   │   │  Python FastAPI sidecar │
 │ (static export,  │  │ mcp      │   │ mcp          │   │  (sidecar/app.py)       │
 │  WKWebView)      │  │ subproc  │   │ subproc      │   │  ~107 HTTP routes,      │
 │  Zustand stores  │  │ :PORT    │   │ :PORT        │   │  1 WS, 1 MCP mount      │
 │  dockview panels │  └────▲─────┘   └──────▲───────┘   │                         │
 │  ChatSidebar     │       │ Streamable-HTTP│ (MCP)     │  binds 127.0.0.1:<port> │
 └────────┬─────────┘       └────────────────┴───────────┤  CORS *  (loopback)     │
          │  HTTP/SSE/WS over 127.0.0.1:<sidecar-port>    │                         │
          └──────────────────────────────────────────────▶  /quotes /history ...   │
                                                           │  /agents /llm/chat ... │
                                          external MCP ───▶│  /mcp  (FastMCP, 11    │
                                          (Claude Code)    │        tools, ASGI)    │
                                                           └─────────────────────────┘
```

**Layer model.** Frontend → sidecar HTTP only (no panel reads a provider API or
the keychain directly). Sidecar routers → `services/` providers (routers never
import a concrete provider; they go through `provider_registry` or a domain
module). Secrets cross the boundary **renderer-reads-keychain → secret in
request → sidecar holds in memory for the request only** — the sidecar
**cannot** read the OS keychain; only Rust can.

**Port assignment + handoff.** `pick_free_port()` binds `127.0.0.1:0`, reads
the OS-chosen port, releases it (a narrow unguarded TOCTTOU window), and stores
`SidecarPort(u16)`. The two MCP subprocesses are spawned first **on parallel
threads** and `join`ed before the main sidecar spawns, so their
`VYSTED_*_MCP_PORT` env vars are settled — the _entire_ MCP handshake is an env
var, no IPC negotiation. The frontend learns the sidecar port via
`get_sidecar_port` and `/health`-probes with backoff (120s deadline) before
declaring connected.

**Fragility flags at the boundary.** The main-sidecar spawn + `app_data_dir`
resolve + `create_dir_all` all `.expect()` → any failure **panics the app at
boot with no UI**. The MCP children, by contrast, never panic — they
`register_unavailable` (port 0) and degrade gracefully (openbb→yfinance,
sec→501). The `wait_for_port` main-sidecar readiness check is fire-and-forget
logging; nothing blocks the UI on readiness, so the frontend tolerates a
not-yet-up sidecar.

---

## 3. Subsystems

### 3.1 Desktop core & lifecycle (Tauri / Rust)

`src-tauri/src/main.rs` is a 5-line shim into `lib.rs` + four modules
(`keychain.rs`, `kill_switch.rs`, `openbb_mcp.rs`, `sec_edgar_mcp.rs`). Four
Tauri plugins registered: `shell`, `updater`, `notification`, and the custom
`kill_switch` (wrapping `global-shortcut`). Single window: 1280×832, dark theme,
`dragDropEnabled: false` (load-bearing — `true` installs an OS drag-drop handler
that swallows in-webview HTML5 drag events, which broke dockview tab reorder +
node-editor palette drop on macOS WKWebView too). `security.csp` is `null`.

**Keychain (`keychain.rs`).** Three async commands — `keychain_set` / `get`
(`NoEntry`→`Ok(None)`) / `delete` (idempotent) — service name
`"vysted-terminal"`, account = namespaced secret id. `keyring` v3 platform
features `["apple-native","windows-native","sync-secret-service","crypto-rust"]`
are load-bearing (default-features build silently no-ops `set_password`). The
roundtrip unit test **skips silently** with no usable credential store, so
headless-runner keychain behaviour is unverified by CI.

**Kill switch (Rust half).** OS-wide `CmdOrCtrl+Shift+K` via
`global-shortcut`; on press emits Tauri event `kill-switch:requested`
`{firedBy:"user-keyboard"}` — the Rust side does **no HTTP**; the frontend
`useSafetyStore` issues `POST /safety/kill-switch`. Registration failure
degrades gracefully (the toolbar button is the always-available fallback).

**Auto-updater — plumbed at config only, non-functional end-to-end.** Registered
in Rust, endpoint + minisign pubkey in `tauri.conf.json`, but
`createUpdaterArtifacts: false` and **no frontend code calls the updater** (zero
`.check()`/`downloadAndInstall` usages in `src/`). Flag as incomplete.

**Capability bug (probable latent).** `capabilities/default.json` grants
`core:default`, `global-shortcut:allow-is-registered`, `notification:default` —
but **not** `shell:allow-open`, while the frontend calls `plugin-shell`'s
`open()` in ≥3 places (Kite OAuth login URL, SEC "open in browser"). Those calls
will likely be **denied at runtime**. Marked unverified, but the capability JSON
lacks the permission. (Rust-side `app.shell().sidecar(...)` spawns are unaffected
— capability gates frontend `invoke` only.)

Rust commands exposed: `get_sidecar_port`, `keychain_set/get/delete`,
`kill_switch_emit`, `get_openbb_mcp_port`, `get_sec_edgar_mcp_port` (0 =
unavailable). `RunEvent::Exit` reaps the main sidecar + both MCP children via
`child.kill()` — but PyInstaller `--onefile` re-execs a worker, so `kill()` on
the bootloader **may orphan the worker** (documented for Node smoke scripts;
unverified for the Rust path).

### 3.2 Sidecar app & endpoints (FastAPI)

One app built by `create_app()` in `sidecar/app.py`. 24 router modules,
~107 HTTP routes + 1 WebSocket + 1 mounted MCP sub-app. CORS fully permissive
(`*`) — justified because the sidecar binds loopback only (but **the bind itself
is `main.py`/uvicorn's job, not enforced in `app.py`**). A single
`ProviderError → HTTP 502` exception handler; SSE (`text/event-stream`,
`data: {json}\n\n`) is the streaming convention for `/llm/chat`,
`/agents/{id}/invoke`, `/backtest/run`, `/workflow/run` (the encode helpers are
**duplicated verbatim** across four routers, two unused). `version="0.8.0"` is a
hardcoded literal at `app.py:161` — a separate source of truth that has drifted
before (`/health` now derives from `request.app.version`).

The v0.6.0/v0.6.5 runtime-extension aggregators (`app.py:131,145`) are called at
build time but are **live no-op stubs** per their own docstrings — dead
scaffolding kept for per-release-stamp parity. Quotes/crypto are thread-offloaded
(`asyncio.to_thread`); **`/history/{symbol}` is NOT** — it calls the blocking
provider synchronously on the request thread (a real event-loop-blocking
asymmetry). Caching is per-router, not centralized.

**Full endpoint inventory** (full mounted paths; "Service" = delegate):

| Method              | Path                                                                                       | Purpose                                          | Service / notes                                                               |
| ------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------ | ----------------------------------------------------------------------------- |
| GET                 | `/health`                                                                                  | Liveness (Tauri polls on launch)                 | `provider_registry.active_providers()`; version from `request.app.version`    |
| GET                 | `/quotes/{symbol}`                                                                         | Single latest quote                              | `provider_registry.get_quote` via `asyncio.to_thread`                         |
| GET                 | `/quotes`                                                                                  | Batch quotes (`?symbols=`)                       | fan-out `asyncio.gather`; failed symbols silently skipped                     |
| GET                 | `/history/{symbol}`                                                                        | OHLCV (`?timeframe=&range=&asset_class=`)        | `provider_registry.get_history` — **NOT thread-offloaded**                    |
| GET                 | `/crypto/exchanges`                                                                        | Supported ccxt exchanges                         | `ccxt_provider.SUPPORTED_EXCHANGES`                                           |
| GET                 | `/crypto/ticker`                                                                           | REST ticker (`?exchange=&symbol=`)               | `ccxt_provider.get_ticker` via thread                                         |
| GET                 | `/crypto/history`                                                                          | OHLCV (`?exchange=&symbol=&timeframe=`)          | `ccxt_provider.get_ohlcv` via thread                                          |
| WS                  | `/crypto/stream`                                                                           | Live ticker WebSocket                            | `ccxt_provider.watch_ticker` (ccxt.pro)                                       |
| GET                 | `/indicators`                                                                              | List supported indicator keys                    | declared before `/{symbol}` so it matches first                               |
| GET                 | `/indicators/{symbol}`                                                                     | Compute indicators (`?indicators=`)              | `indicators.compute`; unknown key → 400                                       |
| GET                 | `/fundamentals/{symbol}`                                                                   | Valuation ratios + profile                       | `provider_registry.get_fundamentals`                                          |
| GET                 | `/fundamentals/{symbol}/income` `/balance` `/cashflow`                                     | Financial statements                             | `provider_registry.get_*_statement`                                           |
| GET                 | `/fundamentals/{symbol}/ratings`                                                           | Aggregated analyst rating                        | `provider_registry.get_analyst_rating`                                        |
| GET                 | `/fundamentals/{symbol}/ratings/history` `/price-target-history` `/individual`             | Extended ratings                                 | `analyst_ratings_extended` + `data_cache` (TTL 6h)                            |
| GET                 | `/news`                                                                                    | RSS+NewsAPI news, VADER sentiment, symbol-tagged | `news_provider.fetch_news` + `sentiment.score_text`                           |
| GET                 | `/macro/search` `/catalog`                                                                 | Catalog search / featured                        | `macro_router` (FRED/ECB/IMF/world-bank)                                      |
| GET                 | `/macro/{series_id}`                                                                       | Macro series (`?provider=`)                      | new dispatcher (`MacroSeriesExtended`) or legacy openbb-mcp path              |
| GET                 | `/sec/status`                                                                              | sec-edgar-mcp readiness                          | only `/sec` route that works when subprocess down                             |
| GET                 | `/sec/filings/search` `/filings` `/filings/{accession}[/sections]` `/insider/{identifier}` | EDGAR filings + insider                          | `sec_filings_provider`; **501** when subprocess unbound                       |
| GET                 | `/earnings/upcoming` `/{symbol}/history` `/surprises` `/estimates`                         | Earnings calendar/history                        | `earnings_provider` + `data_cache` (6h/24h TTLs)                              |
| POST                | `/screener/run`                                                                            | Run screener (`ScreenerRequest`)                 | `screener.run_screener`; universe failure → 502, unknown → 400                |
| GET                 | `/screener/universe`                                                                       | Resolve universe (`?id=`)                        | `screener.resolve_universe`; `custom` → 400                                   |
| GET/POST/PUT/DELETE | `/portfolio/positions[/{id}]`                                                              | Manual positions CRUD                            | `portfolio_db` (SQLite); 201/204/404                                          |
| POST                | `/quant/option/price` `/option/greeks` `/bond/price` `/yield-curve`                        | QuantLib pricing                                 | `services.quant.*`; `ValueError` → 400                                        |
| POST                | `/backtest/run`                                                                            | SSE `BacktestRunEvent`                           | `backtest_engine.run_backtest` + `bar_loader`; cached                         |
| GET                 | `/backtest/strategies` `/runs` `/runs/{id}`                                                | Strategy + run catalog                           | in-memory `backtest_store`                                                    |
| POST                | `/workflow/run`                                                                            | SSE `WorkflowRunEvent`                           | `workflow_engine.run_workflow`                                                |
| POST/GET/DELETE     | `/workflow/save` `/saved[/{id}]`                                                           | Workflow persistence                             | `workflow_store`                                                              |
| GET                 | `/agents`                                                                                  | List first-party agents                          | `agent_runtime.list_agents()` (custom NOT merged)                             |
| POST                | `/agents/{agent_id}/invoke`                                                                | SSE `LLMStreamEvent`                             | `agent_runtime.invoke_agent`; 404 if unknown                                  |
| GET/POST/PUT/DELETE | `/custom-agents[/{id:path}]`                                                               | Custom-agent CRUD                                | `agents_store` (SQLite); 409 collision; `custom:` prefix enforced             |
| GET                 | `/llm/providers`                                                                           | BYOK provider catalog                            | `services.llm.list_provider_info`                                             |
| POST                | `/llm/keys/validate`                                                                       | Probe a key                                      | transport error → `{ok:false}` (never raises)                                 |
| POST                | `/llm/chat`                                                                                | SSE `LLMStreamEvent`                             | `adapter.stream_chat`; unknown provider → 400                                 |
| GET                 | `/brokers` `/{id}/state` `/account` `/positions` `/holdings` `/margins`                    | Read-only broker state                           | `adapter.*`; session-expired → 419                                            |
| POST                | `/brokers/{id}/connect` `/disconnect` `/mode` `/read-only`                                 | Session/mode control                             | `adapter.*`; mismatch → 400                                                   |
| POST                | `/brokers/{id}/orders[/{proposal_id}/confirm]` `/orders/cancel`                            | Propose→confirm→place / cancel                   | `adapter.propose_order` / `confirm_and_place`; in-memory `_pending_proposals` |
| GET/POST            | `/brokers/kite/static-ip` `/session`                                                       | Kite static IP + real OAuth exchange             | `kite.exchange_request_token` (SHA-256 + `/session/token`)                    |
| GET                 | `/safety/audit-log[/export.csv]`                                                           | Tail / CSV append-only log                       | `audit_log`; limit 1–5000                                                     |
| POST/GET            | `/safety/kill-switch[/reset][/status]`                                                     | Fire / reset / status                            | `kill_switch.get_bus()`; reset needs `acknowledged=true`                      |
| GET/POST            | `/safety/disclaimer-status` `/disclaimer-ack`                                              | Session disclaimer acks                          | `disclaimer_session`                                                          |
| GET                 | `/safety/static-ip-status`                                                                 | Configured-vs-detected IP                        | `static_ip_detector` (advisory, no block)                                     |
| GET                 | `/tradesa-v2/*` (14 routes)                                                                | Read-only Tradesa bot mirror                     | `TradesaV2Provider`; GET-only by audit invariant; creds in headers            |
| GET/POST/DELETE     | `/plugins[/{id}/config]`                                                                   | Persisted plugin configs                         | `plugins_store` (SQLite)                                                      |
| GET/POST/DELETE     | `/workspace[/{name}]`                                                                      | Workspace blob persistence                       | `workspace_store`; opaque JSON                                                |
| GET                 | `/mcp/status` `/openbb-mcp/status`                                                         | Vysted MCP + openbb-mcp readiness                | `mcp_server.tool_count()` / `openbb_mcp_provider.status()`                    |
| (JSON-RPC)          | `/mcp/`                                                                                    | FastMCP Streamable-HTTP transport                | mounted sub-app for external MCP clients                                      |

### 3.3 Market-data & analytics services

All under `sidecar/services/`. `provider_registry.py` is the single dispatch
point (routing by `asset_class`): crypto → ccxt (`DEFAULT_CRYPTO_EXCHANGE =
"binance"`, hardcoded), equity → yfinance; fundamentals/statements/ratings →
openbb-mcp **if bundled** else yfinance; macro → openbb-mcp only else
`ProviderError`. `get_quote`/`get_history` are **synchronous** here.

- **`yfinance_provider.py`** — no-key default for equities. Load-bearing
  details: `BRK.B`→`BRK-B` rewrite; **dividend-yield divided by 100** (yfinance
  1.3.0 returns a percentage, the contract wants a fraction — a silent corruption
  risk if upstream changes); aggregate rating reads only the single most-recent
  recommendation row.
- **`ccxt_provider.py`** — ccxt (sync REST) + ccxt.pro (async WS). Exchanges:
  bybit, binance, kraken, coinbase. Backs `/crypto/*`.
- **`openbb_mcp_provider.py`** (conditional) — richer fundamentals/macro via the
  openbb-mcp subprocess over Streamable-HTTP. Port 0/unset → `is_available()`
  False → registry falls back. **Whether the binary ships in a given build is
  unverified from service code alone.**
- **`news_provider.py`** — RSS (Yahoo, MarketWatch, per-symbol Yahoo; always on)
  - NewsAPI (BYOK `NEWSAPI_KEY` only). Shared pooled `httpx.AsyncClient` (the
    cold-start TLS-cascade fix). No caching — re-fetches live every request.
- **`sentiment.py`** — VADER lexicon (a deliberate Tier-3 choice: FinBERT would
  drag `torch` into the bundle). Coarse, "at a glance," **not finance-grade** —
  flagged honestly in the docstring.
- **`earnings_provider.py`** — yfinance calendar/estimates/surprises. Fiscal
  period **inferred from calendar month** (best-effort, UI-only); EPS stddev is
  an approximation `(high−low)/4`. Router-side caching.
- **`analyst_ratings_extended.py`** — yfinance has **no individual-analyst
  names** (firm used as label), **no real price-target timeline** (often a single
  synthetic "Consensus" anchor row). Honest degeneracy baked in.
- **`sec_filings_provider.py`** (conditional) — sec-edgar-mcp subprocess. Narrow
  form coverage (10-K/10-Q/8-K/DEF 14A/3/4/5); extractors heavily defensive
  against upstream shape drift. Caches via `data_cache`.
- **`screener.py` + `screener_universes/`** — fan-out filter engine. Universes:
  `sp500` (**only top 100**, label admits it), `nifty50` (50), `crypto-top50`
  (50, "refresh from ccxt" worker does **not exist**), `custom`. AND-only
  criteria; OR-grouping reserved.
- **`services/macro/`** — four in-process providers (FRED requires
  `FRED_API_KEY`; ECB/IMF/world-bank keyless). Hand-curated `_FEATURED` catalogs;
  full catalog browsing deferred. `fred-mcp-server` turned out to be Node.js →
  pivoted to in-process `fredapi`.
- **`services/quant/`** — in-process QuantLib (Tier-3: quality over bundle size).
  Options (BS/binomial/MC; **MC Greeks not computed**), Greeks, bonds, yield
  curve (synthetic `VYSTED-IBOR`, not SOFR/ESTR). `monte_carlo.py`
  (Asian/barrier) is **not wired to any endpoint**.
- **`indicators.py`** — pure pandas/numpy, **49 indicators + volume_profile**
  (50). Frontend never computes an indicator; the sidecar does.
- **`data_cache.py`** — generic SQLite TTL cache, **TTL-per-`get`**, stale rows
  **not auto-evicted**. Notably uncached: news, quotes/history/equity-fundamentals
  through the registry, all quant pricing.
- **`bar_loader.py`** — daily-bar loader for the backtest engine; per-symbol
  `ProviderError` degrades to empty series.

**Documented-but-unimplemented "richer later" hooks:** openbb-mcp
earnings/analyst enrichment, ccxt crypto-top50 refresh, individual analyst
names/accuracy, real price-target timelines, full SEC form coverage, full macro
catalog, surface vol/yield curves, HTTP wiring for path-dependent MC.

### 3.4 Plugin system

`types/plugin.ts` (**Tier-1, highest blast radius**) — a deliberately
framework-free serializable contract: four fixed sections (identity, lifecycle,
six-boolean `capabilities`, optional getters) + six capabilities
(`contributesData/Panels/Commands/Agents/Nodes`, `supportsControlPlane`).
`PanelSpec.component` is a **string id** resolved host-side (keeps the contract
serializable). Negotiation checks the _flag_, not the method.

`PluginRuntime` (`src/lib/plugin-runtime.ts`, pure TS): discover → loadPlugin
(honors persisted `enabled:false`) → collect contributions through
`callIfFlagged` (a buggy getter emits `errored`, returns `[]`) → 30s health
poll. **Honesty flag:** `PLUGIN_DEVELOPMENT.md` claims the runtime asserts
manifest↔instance id/version match + checks `requiredHostVersion` — **none of
those checks exist** in the code. Aspirational doc.

`bootstrapPlugins()` runs once from `page.tsx`. `BUNDLED_PLUGINS` = exactly
three (`example`, `openbb-mcp`, `tradesa-v2`). Because the contract is
serializable, React components ride the **static `PLUGIN_COMPANIONS` map**
(only `tradesa-v2` ships panels). Per-plugin config persists sidecar-side
(SQLite `plugin_configs`), never browser storage. Plugin secret resolution via
`PluginConfig.secrets` is **effectively a no-op** (default `resolveSecrets`
returns `{}`); plugins fetch creds out-of-band.

| Bundled plugin   | Type        | Capabilities (true)                              | Status                                                                                                                         |
| ---------------- | ----------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| `vysted-example` | data-source | data, commands, control-plane                    | Pedagogical; proves contract end-to-end. Working.                                                                              |
| `openbb-mcp`     | data-source | data only                                        | Declares 3 DataSources; `healthCheck` probes `/openbb-mcp/status`. Data actually flows through sidecar routes, not the plugin. |
| `tradesa-v2`     | trading-bot | data, panels, commands (control-plane **false**) | Read-only wrapper, **7 panels** + 7 cmd+K commands; the only bundled plugin exercising panels + the companion map.             |

**Two real gaps between narrative and wiring:** (1) `contributesAgents` /
`contributesNodes` paths are **unexercised** by any bundled plugin (empty in
practice; first-party AI agents load via a separate sidecar JSON path). (2) The
**seven broker plugins** under `plugins/brokers/` each export a full
`VystedPlugin` but are **not in `BUNDLED_PLUGINS`, not imported anywhere under
`src/`** — they are contract-conformance artifacts + test fixtures, not live
plugins. Broker execution bypasses the plugin subsystem entirely.

### 3.5 Broker layer (Kite read-only + BYOK)

Built for full execution; **only read-only account/positions/P&L for three
Indian brokers is reachable today.** `bootstrap_default_adapters()` registers
**only** Dhan, Angel One, Kite. Alpaca/IB/OANDA/ccxt-exec adapters are fully
implemented but **never registered → dead at runtime**.

The **real Kite Connect OAuth** is the canonical BYOK path and genuinely
end-to-end: user pastes api_key/api_secret → `openKiteLogin` opens the Kite
login in the system browser → user manually pastes the redirect URL/bare
`request_token` (the registered redirect `http://127.0.0.1:43117/kite/callback`
has **no Rust loopback listener** — deliberate v1 manual-paste flow) →
`POST /brokers/kite/session` runs the real `KiteConnect.generate_session`
(SHA-256 checksum + `/session/token`) → daily access token → `connect()`. Token
**expires daily** (~6am IST); expiry maps to **HTTP 419** for a reconnect cue.
`api_secret` crosses to the sidecar for the exchange only — never stored/echoed.

`/positions`, `/holdings`, `/margins` all **currently return the same
`AccountSummary` as `/account`** — no adapter defines the granular
`*_info` methods; the `account_info()` duck-typing is forward-looking
scaffolding. In **paper mode / `_client is None`, a "connected" broker returns a
synthetic ₹1,000,000 account with empty positions** — fake data, not real
holdings.

**Execution is deferred at every concrete level.** Paper is the hard `__init__`
default with **no constructor path to live** (only `set_mode("live")`). Every
`_place_confirmed` short-circuits to `_synthetic_paper_result` in paper. Kite's
live `_place_confirmed` exists (hardcoded `variety="regular"`, `product="CNC"`
— cash-only, no MIS/NRML/product selection) but **is unverified — no live order
has been placed through any broker.** The Phase-10 integrations hub is read-only
by design ("Order execution is not enabled here").

**Static-IP UX (Kite/SEBI-NSE, effective 2026-04-01):** `static_ip_detector`
one-shot GETs `api.ipify.org` (never raises); `set_mode("live")` writes a
forensic audit row with the match status. **Order placement does NOT pre-block**
on mismatch — advisory banner only; the panel passes `configuredIp=null`
(always compares against "no configured IP").

### 3.6 Safety architecture (§6.5)

The execution-safety layer enforces BLUEPRINT §6.5's eight non-negotiable
safeguards across sidecar + Rust + frontend, gated by
`tests/test_safety_end_to_end.py`. **Verified 2026-05-30: 9/9 audit pass; 58
passed combined with the Tradesa V2 read-only audits (~30s, pytest 9.0.3).**

| #   | Guarantee                   | Site                                                                  | Test              |
| --- | --------------------------- | --------------------------------------------------------------------- | ----------------- |
| 1   | Paper-mode default          | `broker_base.py` `self._mode="paper"` (no constructor flips it)       | `test_audit_1`    |
| 2   | Every order human-confirmed | `_place_confirmed` private, sole caller `confirm_and_place`           | `test_audit_2`    |
| 3   | Position-size limits        | `propose_order` raises before any broker call                         | `test_audit_3`    |
| 4   | Append-only audit log       | SQLite `RAISE(ABORT)` triggers on UPDATE/DELETE + `query_only` reader | `test_audit_4`    |
| 5   | Global kill switch < 2s     | `KillSwitchBus.fire` instruments p50/p95/max ack                      | `test_audit_5`    |
| 6   | AI-order gate               | no `place_/submit_/execute_order` tool; AI can only propose           | `test_audit_6`    |
| 7   | Read-only mode              | `_read_only` checked in propose + re-checked in confirm               | `test_audit_7`    |
| 8   | Layered disclaimers         | keychain (TOS + per-broker) + sidecar in-memory (per-session)         | `test_audit_8/8b` |

**Defense-in-depth template (canonical for this codebase):** type/structure gate
(`_place_confirmed` only called from `confirm_and_place`, which requires
`human_confirmed` + re-checks kill-switch/read-only) **+** DB-level invariant
(SQLite triggers raising `IntegrityError` with literal messages, plus a
`query_only` reader) **+** grep-time CI audit (`test_audit_2/6` grep the whole
tree for call-sites / `auto_approve`). Each layer catches a different failure
mode.

**Honest gaps (real, documented):**

- **`_place_confirmed` is convention-private, not language-private** — the
  "name-mangled" docstring is wrong; the actual enforcement is the grep gate, a
  CI check, not a type gate.
- **Stale exception-type docstrings** — `models/audit_log.py` +
  `services/audit_log.py` say `OperationalError`; the asserted + live type is
  `sqlite3.IntegrityError`.
- **Kill-switch fired state does NOT survive a sidecar restart** — module
  singleton in process memory; a crash/restart silently un-halts. Only durable
  trace is the audit row.
- **Kill switch does not cancel open orders** — it blocks new placements + forces
  read-only; cancel-all is a subclass responsibility, unimplemented in the base.
- Audit-log live tail is **2s polling**, not push.

**Tier-1 LOCKED files** (changing them is a §6.5/Tier-4 event, byte-identical to
pre-Phase-10 baseline): `types/safety.ts`, `types/broker.ts`,
`sidecar/models/safety.py`, `sidecar/models/broker.py`,
`sidecar/models/audit_log.py`, `sidecar/services/broker_base.py`,
`src-tauri/src/kill_switch.rs`, `sidecar/models/kill_switch.py`,
`types/plugin.ts`, `tests/test_safety_end_to_end.py`.

### 3.7 MCP integration (both sides, both real)

**As client:** two MCP subprocesses (`openbb-mcp-server==1.4.0` + 6 OpenBB
extensions; `sec-edgar-mcp==1.0.8`), each its own PyInstaller binary with a
**separate venv** (openbb-core strict-pins `fastapi<0.129`/`uvicorn<0.41`,
incompatible with the main sidecar's 0.136/0.46), spawned by Rust
`app.shell().sidecar(...)` (NOT `subprocess.Popen` — the v0.4.0 fix for a Windows
`_MEIPASS`+anyio+handle-inheritance deadlock). Each `main.py` is a thin launcher:
parse `--port`, start a raw-`os.read` stdin-EOF watchdog, rewrite `sys.argv` to
`--transport streamable-http`, delegate to the upstream `main()`. The provider
seam is a **REST proxy, not MCP passthrough** — `openbb_mcp_provider` /
`sec_filings_provider` expose the same surface a yfinance provider would, so the
registry swap is one line. `mcp_client.py` (lazy session, reconnect-on-error,
generation-counter race guard) supports http + stdio, but **only http has a real
consumer** (stdio is dead code reserved for filesystem plugins).

**As server:** `mcp_server.py` is a real FastMCP 3.x server mounted at `/mcp`
over Streamable-HTTP. **11 tools** (`get_quote/history/fundamentals/news/
macro_series`, `list_agents`, `invoke_agent` — collapses the SSE stream into one
unary string, `list_workspaces`, `get_workspace`, `run_workflow`,
`list_workflows`). **Architecture: protocol adapter, zero logic duplication** —
each tool is a thin shim calling the sidecar's own HTTP endpoint via an
in-process `httpx.ASGITransport` bound by `bind_app(app)`. Every tool returns a
`dict` (FastMCP rejects bare lists). A subtle lifespan invariant:
`get_streamable_http_app()` is cached because the SAME instance must drive both
the mount and the parent lifespan, or every request raises "Task group is not
initialized." No authentication (loopback only, by design); external-client
config is a manual copy-paste flow (Claude Desktop needs `mcp-remote`).

**Fragilities:** subprocess cold-bind is the dominant one — ~34s isolated on
M1, worse under concurrent `_MEI*` extraction disk-I/O contention; budget raised
to `MCP_PORT_WAIT_SECS=45 × 2 = 90s`; the true fix (`--onedir`) is deferred. Doc
drift: protocol version (`2025-06-18` code vs `2025-11-25` in `types/mcp.ts`),
tool count (`MCP_INTEGRATION.md` says 9, code ships 11). No `/sec-edgar-mcp/status`
route (asymmetric with openbb). The smoke-test gate now TCP-probes bind but does
**not** verify endpoint data (`/agents` count > 0).

### 3.8 Frontend shell, layout & state

Next.js 16 App Router **static export** (`output:"export"`), served as files by
the core — no Node server. SSR-safety rests on one invariant: **`PanelHost`
returns a loading placeholder until modules register** (dockview is not
SSR-safe; module registration runs in a `page.tsx` `useEffect` that never fires
during prerender). **Dark theme only** — `<html className="dark">` hard-coded, no
toggle (light theme is a Tier-4 BLOCKER until v1.1).

**dockview** is the chosen layout engine (Tier-3). A `VystedModule` bundles
`panels`/`commands`/`panelComponents`/`commandHandlers`; `useModulesStore` holds
modules + an `enabled` map; `PanelHost` builds the `componentId → Component` map
and mounts `DockviewReact`. **`collectPanelComponents` does a flat
`Object.assign` — two modules with the same component id silently collide
(last wins), no guard.** Default layout: Chart over Equity Overview (left),
Watchlist/News/Portfolio stacking right, AI Assistant far-right column.

**18 first-party modules** hard-listed in `src/modules/index.ts` (edit-once-
per-phase so parallel work doesn't contend). Plugins bridge into the _same_
registry via `moduleForPlugin` (id `plugin:<id>`) — no second registry.

**Workspace blob persistence:** `SerializedWorkspace` round-trips layout +
`enabledModules` + `chartDrawings?` + `defaultProviderId?` + `watchlist?`
through `/workspace` as one opaque blob (sidecar stores it verbatim, never
validates). Open index signature → new fields need no sidecar change but
**require editing four call-sites** (interface, `serializeWorkspace`,
`deserializeWorkspace` with an older-blob guard, `autosaveLayout`) — duplicated
payload assembly, kept in lockstep by hand. Restore is defensive: an
unknown-component guard skips to default rather than letting `fromJSON` throw;
`enabled` map rolls back on a throwing restore; disposed-api guards for
StrictMode/HMR. Autosave debounced 1500ms; **failures silently swallowed**.

**Theme tokens — names are historical, not literal:** `amber-*` renders CORAL
(`#d97757`), `charcoal-*` renders ESPRESSO, `brass-*`/`sage-*` are warm
NEUTRALS. Names kept so 80+ files reskin by re-valuing `tokens.css` alone.
**Canvas can't read CSS vars** → the chart palette is hand-mirrored in
`src/lib/chart-theme.ts`; a reskin must change **both** or canvas drifts (3
values, incl. a forbidden cyan, had silently drifted pre-Phase-10).

**Zustand stores:** workspace, modules, app (sidecar URL+status —
**computed but not surfaced** in the header), symbols (watchlist, single source
of truth, default 6 symbols SPY/QQQ/BTC-USDT/ETH-USDT/NVDA/AAPL — differs from
the canonical 7-symbol visual protocol), command-palette, panel-context
(pub/sub bus feeding the chat sidebar). cmd+K is substring match only — no
fuzzy, no ranking, no recents.

### 3.9 Panels — market (Chart / Equity Overview / Watchlist / News / Portfolio / Screener)

| Module          | Panel                          | Singleton        | Endpoints                                                       |
| --------------- | ------------------------------ | ---------------- | --------------------------------------------------------------- |
| chart           | `ChartPanel.tsx` (~1150 lines) | no (multi-chart) | `/history/{symbol}`, `/indicators/{symbol}`                     |
| equity-overview | `EquityOverviewPanel.tsx`      | yes              | `/quotes`, `/fundamentals` + `/income/balance/cashflow/ratings` |
| watchlist       | `WatchlistPanel.tsx`           | yes              | `/quotes` (batch), `/crypto/ticker` (per crypto)                |
| news            | `NewsFeedPanel.tsx`            | yes              | `/news`                                                         |
| portfolio       | `PortfolioPanel.tsx`           | yes              | `/portfolio/positions` CRUD, `/quotes/{symbol}`                 |
| screener        | `ScreenerPanel.tsx`            | yes              | `/screener/run`, `/screener/universe`                           |

**Chart** is the heaviest panel: `lightweight-charts` candlesticks, 8-step
timeframe, 50-indicator multi-select (server-computed; frontend never computes
one), 10 drawing tools (`ISeriesPrimitive`, click-to-create, serializable
`DrawingSpec` per-panel store), comparison overlay (failures silently swallowed),
three cross-chart sync slices (crosshair/range/symbol). **isTrusted limitation:**
drawing/pan/zoom gestures are gated by lightweight-charts on trusted events —
chrome-devtools MCP synthesised events are rejected, so canvas-interactive
features **cannot be visually regression-tested** (only data models + toolbar
wiring). Equity Overview fans out 6 parallel calls with graceful partial
failure. Watchlist polls 5s. News auto-retries with exponential backoff
(self-heals the ~30s cold-boot sidecar bind). Portfolio computes P&L
client-side; honest edge cases (`null` for zero-cost-basis, divides by
resolved-cost). Screener: client-side sort with null-last pinning.

### 3.10 Panels — analysis (Macro / SEC / Earnings / Analyst / Quant / Backtest / Node Editor / Agent Builder / Chat / Integrations)

All data stores call `sidecarGet` (GET) or a `fetch`-based POST/SSE consumer;
none use `localStorage`. Notable surfaces:

- **Backtest** — schema-driven params form from `GET /backtest/strategies`; SSE
  run stream; "Open in Strategy Critic" drops a `/agent strategy_critic` line
  into the chat composer (BLUEPRINT Use Case 2, end-to-end unverified).
- **Node Editor** — `@xyflow/react` 12.x; HTML5 DnD palette→canvas (why
  `dragDropEnabled:false` is required); 10 built-in nodes unioned with plugin
  nodes; config schema lives host-side (NodeSpec stays locked/serializable). A
  **second workflow consumer** (`store/workflow.ts`) exists with a
  desktop-notification-intent slice that has **no found dispatcher** — treat as
  unwired.
- **Agent Builder** — sidecar-backed custom-agent CRUD; `custom:` prefix
  enforced.
- **Chat sidebar** (`ChatSidebar.tsx`) — the most cross-cutting surface (6+
  stores). Default agent `copilot`; bare text routes to it; clickable persona
  chip roster; `/ask` raw escape hatch. `executeHostAction` maps copilot tool
  calls to live store mutations (`set_chart_symbol`/`open_panel`/`add_to_watchlist`);
  `propose_order` only surfaces a review chip → §6.5 dialog. BYOK key resolved
  from the **agent's** `defaultProvider` (not the UI default), read from keychain
  on demand. `defaultModelFor` **hard-codes one model per provider** (may drift).
- **Integrations** (`ConnectCard.tsx`) — no `index.ts`, rendered inside
  `SettingsPanel`; one dialog drives any `IntegrationSpec`. Kite OAuth runs in
  the **sidecar**, not Rust.

### 3.11 Agent personas

13 first-party agents under `sidecar/agents/*.json` (read-only, discovered at
import, validated against `_schema.json` draft-07, count hard-asserted by three
tests). 12 investor personas (Buffett, Graham, Lynch, Munger, Marks, Klarman,
Dalio, Druckenmiller, Soros, Researcher, Portfolio Advisor, Strategy Critic) +
the Phase-10 `copilot` router. Each persona's prompt is 1.5–4 KB; only `copilot`
(ollama/`qwen2.5:7b`) and `researcher` (openai) deviate from anthropic default.
The `sidecar/agents/` dir is bundled via an explicit `--add-data` (it has no
`__init__.py`; was silently dropped for 3 releases — Phase 8 finding).

**Custom agents:** CRUD'd via `/custom-agents`, SQLite store, `custom:` prefix
required. **Caveat — the custom-agent tool allow-list is stale + out of sync:**
`KNOWN_TOOL_IDS` lists only 5 tools (`price_data, fundamentals, news,
backtest_summary, macro`), but first-party agents bypass the allow-list and
legitimately use tools (`screener_run`, `set_chart_symbol`, `broker_portfolio`)
that **a custom agent cannot select**. Worse, `news`/`macro` pass custom
validation but **are not keys in `TOOL_SCHEMAS`** — so a custom agent
allow-listing them never resolves the tool. A real, unfixed inconsistency.

### 3.12 Build, CI & distribution

Three PyInstaller `--onefile` sidecars built from a clean checkout (no binary
committed): `vysted-sidecar` (89 MB), `vysted-openbb-mcp-sidecar` (49 MB),
`vysted-sec-edgar-mcp-sidecar` (81 MB). Bundle-inclusion flags
(`--hidden-import` / `--copy-metadata` / `--collect-all` / `--collect-data` /
`--add-data`) are load-bearing — each maps to a real shipped-and-crashed
regression. Ensure scripts are **staleness-aware** (binary older than its source
auto-rebuilds; editing the build recipe invalidates the binary).

**Two standing pre-tag gates:** `pnpm ci-local` (mirrors CI byte-for-byte:
install → ensure-all-sidecars → eslint → prettier → tsc → cargo fmt → clippy -D
→ ruff 0.15.12 → vitest → cargo test → pytest) **and**
`scripts/smoke-test-sidecars.mjs` (spawns each built binary, polls `/health`,
TCP-probes MCP bind, tree-kills on exit — catches the `PackageNotFoundError`-at-
startup class that `cargo test` can't, since it never runs the binary).
`ci-local` does **not** run the smoke test or `tauri build`.

**Distribution is partly stubbed:** bundles built **unsigned** (no signing/
notarization anywhere → Gatekeeper/SmartScreen will trip); auto-updater
configured but `createUpdaterArtifacts:false` → no signed artifacts/`latest.json`;
**no release/publish workflow exists** (CI only runs on push/PR + uploads
ephemeral artifacts). **Version sources stuck at `0.8.0`** (`package.json`,
`Cargo.toml`, `tauri.conf.json`, `app.py`, `HOST_VERSION`) despite Phase
8/9/9.5/10 merged — unverified whether intentional (no release cut) or oversight.

### 3.13 Persistence & BYOK (see §6 for the consolidated model)

---

## 4. The copilot today (load-bearing for the redesign)

The copilot is an **agentic tool-use loop running entirely in the sidecar**,
invoked over SSE. This is the Phase-10 unlock: the loop in
`agent_runtime.invoke_agent` already existed but was **dead** — no adapter ever
sent a `tools=` schema, so no model ever called a tool. Phase 10 made it live.

**The loop (`agent_runtime.py:341`).** Resolve spec → resolve provider/model
(override → agent default → hardcoded per-provider fallback table) → coerce
history (last 10 turns) → `tool_ids = list(spec.tools)` → build per-invocation
local tools → compose `[system, context preamble, …history, user]` → `while
True`: stream from `adapter.stream_chat(messages, model, api_key,
tool_ids=tool_ids)`; yield `tool_use` events to the UI; on `done` with tools
fired and `rounds < 6` swallow the terminator and loop; reconstruct the
assistant tool-call turn, dispatch every pending tool, append one `role="tool"`
result per call, increment, loop. **Hard cap `_MAX_TOOL_ROUNDS = 6.`** Errors
never crash the stream — a structured "tool not available" surfaces and the
model recovers.

**The keystone — `agent_tools/schemas.py`.** `TOOL_SCHEMAS` is one
provider-neutral `{tool_id: {description, input_schema}}` catalog. Three
serialisers project it natively: `anthropic_tools`, `openai_tools` (also Groq /
Ollama / DeepSeek / xAI), `gemini_tools`. **Every adapter MUST
`kwargs.pop("tool_ids")`** — forwarding it to the SDK breaks the call (confirmed
all five pop it). **To add a tool you need all three:** a registered handler, a
`TOOL_SCHEMAS` entry, and the id in some agent's allow-list — or it is invisible
to every model.

**Context injection (terminal awareness).** The frontend captures a structured
`__terminal__` snapshot (focused symbol/timeframe/indicators, watchlist,
portfolio, open panels) and sends it on agent calls. Two paths surface it: a
terse system preamble (`_render_terminal_preamble`, with the deixis line —
"when the user says 'this'/'it', they mean {focusedSymbol}… never invent figures
— call a tool") and two on-demand pull tools (`get_terminal_state`,
`get_portfolio`).

**Host-action tools drive the terminal.** `open_panel`, `set_chart_symbol`,
`add_to_watchlist`, `propose_order` are per-invocation closures that return a
_synthetic_ success — the **real UI work happens frontend-side** in
`ChatSidebar.executeHostAction`, dispatched off the streamed `tool_use` event,
not the synthetic result (the `host_action` payload on the wire is effectively
dead today). **`propose_order` NEVER places** (returns `awaiting_user_review` →
§6.5 dialog); it is deliberately not named `place_*`/`submit_*` because
`test_safety_end_to_end.py` greps for those.

**Personas.** 13 first-party agents (§3.11). `copilot` is the terminal-aware
default whose allow-list is the broadest (14 tool ids incl. all host actions).

**Provider/model (BYOK).** `get_provider` is a synchronous stateless factory; 7
provider ids → 5 adapters (DeepSeek/xAI ride OpenAI via base-url override). Keys
never held on the adapter — passed per call, read frontend-side from the
keychain.

**The 14-id `TOOL_SCHEMAS` catalog — but only ~10 are reachable:**

| Tool id                                                                                                                                                                                                                        | What it does                                                         | Reachable by an agent?                                      |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------- | ----------------------------------------------------------- |
| `price_data`                                                                                                                                                                                                                   | ≤90 OHLCV bars + latest quote                                        | yes                                                         |
| `fundamentals`                                                                                                                                                                                                                 | valuation ratios + profile                                           | yes                                                         |
| `backtest_summary`                                                                                                                                                                                                             | digest a cached BacktestResult                                       | yes                                                         |
| `broker_portfolio`                                                                                                                                                                                                             | read-only connected-broker account                                   | yes                                                         |
| `screener_run`                                                                                                                                                                                                                 | run the screener                                                     | yes                                                         |
| `macro_series`                                                                                                                                                                                                                 | one macro series (schema omits required `provider`; handler rejects) | yes                                                         |
| `earnings_history`                                                                                                                                                                                                             | past earnings (≤12 quarters)                                         | yes                                                         |
| `analyst_history`                                                                                                                                                                                                              | rating-change history                                                | yes                                                         |
| `sec_filings_list`                                                                                                                                                                                                             | filings index (degrades if sec-edgar down)                           | yes                                                         |
| `get_terminal_state` / `get_portfolio`                                                                                                                                                                                         | snapshot reads                                                       | yes (runtime-resolved)                                      |
| `open_panel` / `set_chart_symbol` / `add_to_watchlist` / `propose_order`                                                                                                                                                       | host actions                                                         | yes (runtime-resolved)                                      |
| `macro_search`, `earnings_upcoming`, `earnings_estimates`, `analyst_individual`, `price_target_history`, `sec_filing_content`, `sec_insider_transactions`, `price_option`, `compute_greeks`, `price_bond`, `yield_curve_value` | registered handlers, callable over REST                              | **NO — no `TOOL_SCHEMAS` entry → invisible to every model** |

**Material catalog gap:** ~11 registered handlers (the entire QuantLib quartet,
extended earnings/analyst/SEC tools, macro search) have no schema entry and are
**unreachable through the LLM loop** — the schema is the only thing that produces
a `tool_use` block.

**Honest copilot caveats:**

- **Shipped default routes to Ollama `qwen2.5:7b`** — a local model that may not
  be installed; without a running daemon the default agent fails at first call
  unless the user overrides. It is also the agent doing the most tool
  orchestration, on the smallest model.
- **Gemini multi-round tool use is likely broken** — Gemini keys
  `function_response` by tool _name_ read from `metadata["name"]`, but the runtime
  appends tool-result messages with only `tool_call_id` and no `name` → every
  result serialises `name=""`. Single-text Gemini calls are fine. OpenAI-family +
  Anthropic key by id and are correct.
- **Live answers are proven only against a mocked provider**
  (`test_tool_loop_e2e.py`). A real answer needs a BYOK key. Anthropic/OpenAI/Groq
  are higher confidence; Gemini/Ollama are confidence-6-7.

---

## 5. Safety & Tier-1 locks — what must NOT break in the redesign

The §6.5 execution-safety layer is the **most trustworthy surface in the
codebase** — byte-identical to the pre-Phase-10 baseline, 9/9 audit, defense-in-
depth that survives a mistake at any single layer. Any redesign must preserve:

1. **`types/plugin.ts`** — the serializable plugin contract. Any change is Tier-4
   (blocks to operator). It has held through all six capabilities + the broker
   plugins' control-plane shape without a change.
2. **The §6.5 LOCKED files** (§3.6) — `broker_base.py` (the ABC carrying all 8
   enforcements), the append-only audit-log DDL, the kill-switch contracts, the
   broker/safety Pydantic+TS mirrors, the audit suite. Editing any requires
   re-running the audit suite as a hard gate.
3. **Paper-mode hard default + no AI path to placement** — paper is the
   `__init__` default with no constructor path to live; `propose_order` never
   places; the grep gate (`test_audit_2/6`) fails CI if a `_place_confirmed`
   call-site or `auto_approve` appears anywhere.
4. **Append-only audit log at the DB level** — SQLite `RAISE(ABORT)` triggers +
   `query_only` reader; not convention.
5. **The renderer-reads-keychain → secret-in-request invariant** — the sidecar
   cannot read the OS keychain; only Rust can. Never log/echo/persist a secret.
6. **Read-only trading-wrapper enforcement** (Tradesa V2) — three independent
   layers: no write methods on the provider surface (audit-tested), no non-GET
   routes (audit-tested), `supportsControlPlane: false`.

Known §6.5-adjacent test gaps to be aware of (feature works, the gap is the
test): `resetKillSwitch()` is entirely untested (a camelCase/snake_case drift on
`reAck` would permanently lock the kill switch with nothing catching it);
`propose_order`'s invalid-`order_type` path is untested. Kill-switch fired state
not surviving a restart is a real fragility (§3.6).

---

## 6. Persistence & local-first model

**No cloud, no account, no sync, no telemetry.** State lives in exactly three
places with a clean ownership split. `get_data_dir()` reads `VYSTED_DATA_DIR`
(set by the core via `--data-dir`), falling back to `~/.vysted-terminal` outside
Tauri.

| Surface                                                                               | Owner      | Backing store                       | Location                                       |
| ------------------------------------------------------------------------------------- | ---------- | ----------------------------------- | ---------------------------------------------- |
| Workspace blob (layout, modules, drawings, default provider, watchlist)               | Sidecar    | `<name>.vysted-workspace` JSON      | `get_data_dir()/workspaces/`                   |
| BYOK secrets (LLM keys, MCP endpoints, broker creds, plugin secrets, disclaimer acks) | Tauri Rust | OS credential store                 | macOS Keychain / Win Cred Mgr / Secret Service |
| Portfolio positions                                                                   | Sidecar    | SQLite `positions`                  | `get_data_dir()/portfolio.db`                  |
| Order audit log                                                                       | Sidecar    | SQLite `audit_orders` (append-only) | `get_data_dir()/audit_log.db`                  |
| Upstream-data TTL cache                                                               | Sidecar    | SQLite `cache` (WAL)                | `get_data_dir()/data_cache.db`                 |

**The sidecar owns all filesystem persistence so the frontend never needs file
access** — it reaches persistence only through `/workspace`, `/portfolio`,
`/safety/audit-log` over loopback. The workspace blob is **opaque JSON** the
sidecar stores verbatim (never validates); name safety is a `^[A-Za-z0-9 _-]+$`
regex. An `__autosave__` slot holds the last session; restore skips cleanly to
the bundled default on an unknown-component reference rather than corrupting the
grid.

**BYOK invariant:** secrets never touch disk/`localStorage`/cookies. The only
frontend path is `src/lib/keychain.ts` (`setSecret`/`getSecret`/`deleteSecret`
→ Tauri `invoke`). Namespaces: `llm-provider:<id>`, `mcp-server:<id>`,
`plugin-secret:<pluginId>:<key>`, `broker:<brokerId>:<field>`, disclaimer-ack
meta. The `provider-keys` store tracks **presence only**
(`configured|missing|unknown`), never the value. **BYOK is effectively
Tauri-only** — outside the shell `getSecret` rejects → `"unknown"`, no
localStorage fallback by design.

**Honest gaps:** **no DB migrations anywhere** (all three SQLite stores use
`CREATE TABLE IF NOT EXISTS` — adding a column to an existing install would not
migrate); workspace blobs are server-unvalidated (corruption caught only at
`fromJSON` on the client); autosave is best-effort (a transient failure silently
fails to persist until the next layout change); `data_cache` stale rows are never
auto-evicted.

---

## 7. Consolidated status — works / buggy / deferred

Reference HEAD `3123e7c` (Phase 10). **Last release tag `v0.8.0`; Phase
8/9/9.5/10 sit on `main` unreleased/untagged.** "Works" below almost always means
"automated gates pass against mocks," **not** "live/visually validated by a
human."

| Item                                                                                   | Status                                                                                                        | Source                                |
| -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| `pnpm ci-local` (full CI parity)                                                       | **Works** — exit 0: 619 vitest, 6 cargo, 942 pytest                                                           | PHASE_10_HANDOFF §"Gate results"      |
| §6.5 execution-safety layer                                                            | **Works** — 9/9 audit; 6 LOCKED files byte-identical to baseline                                              | PHASE_10_HANDOFF; SAFETY_ARCHITECTURE |
| All 3 sidecar binaries spawn + bind                                                    | **Works** — `smoke-test-sidecars.mjs` exit 0 (freshness + bind probe)                                         | PHASE_10_HANDOFF                      |
| Static-export build                                                                    | **Works** — `next build` compiles (Fraunces + plugin-shell resolve)                                           | PHASE_10_HANDOFF                      |
| Copilot agentic tool loop                                                              | **Works against a mocked provider** (`test_tool_loop_e2e.py`); live answers unverified                        | PHASE_10_HANDOFF §2; CLAUDE.md        |
| Kite read-only OAuth exchange                                                          | **Works (unit/curl)** — real `generate_session`; live round-trip unverified                                   | PHASE_10_HANDOFF §3                   |
| 5 core data panels + 50 indicators + dockview + workspace save/load                    | **Works** (mature, prior tags) — but reskinned in Phase 10, so visuals re-verify                              | §15; CHANGELOG                        |
| Phase-6 analysis panels (macro/SEC/earnings/analyst/screener/quant)                    | **Works** (tests); backend liveness unverified from frontend                                                  | §11                                   |
| Persisted watchlist + defaultProviderId                                                | **Works** — ride the workspace blob, survive relaunch                                                         | PHASE_10_HANDOFF §5                   |
| "Claude after dark" reskin                                                             | **Builds**; every panel's rendered appearance is operator-eyeball                                             | PHASE_10_HANDOFF §4                   |
| MCP cold-bind latency                                                                  | **Buggy/fragile** — 34s isolated, worse under I/O contention; mitigated (45s×2, graceful fallback), not crash | BLOCKERS Phase 9.5 UC1                |
| openbb/sec-edgar `_MEIPASS` deadlock root cause                                        | **Buggy** — worked around at the supervisor, NOT actually fixed                                               | BLOCKERS carry-forward #7             |
| Smoke-test endpoint-data gap                                                           | **Buggy** — binds-but-empty-data still passes the gate                                                        | BLOCKERS S2 #8                        |
| Non-India broker adapters (Alpaca/IB/OANDA/ccxt)                                       | **Dead at runtime** — implemented, never registered, not in `BUNDLED_PLUGINS`                                 | BLOCKERS S2 #5                        |
| 7 broker plugins under `plugins/brokers/`                                              | **Dead-wired** — never imported under `src/`; execution bypasses the plugin runtime                           | §8                                    |
| `contributesAgents` / `contributesNodes` plugin paths                                  | **Unexercised** — empty in practice                                                                           | §8                                    |
| Gemini multi-round tool use                                                            | **Likely broken** — `function_response` keyed by empty name                                                   | §4                                    |
| `/positions` `/holdings` `/margins` distinct data                                      | **No** — all alias `account_info()`; granular methods don't exist                                             | §6 broker                             |
| `resetKillSwitch()` / invalid-order-type tests                                         | **Untested** (feature works; test gap is the bug)                                                             | BLOCKERS S1                           |
| Plugin manifest↔instance + `requiredHostVersion` checks                                | **Documented but not implemented**                                                                            | §8                                    |
| Capability `shell:allow-open` for frontend `open()`                                    | **Probably denied at runtime** — permission not granted                                                       | §1 desktop                            |
| Custom-agent tool allow-list                                                           | **Stale/out of sync** — 5 ids; `news`/`macro` not in `TOOL_SCHEMAS`                                           | §11                                   |
| Live order execution                                                                   | **Designed + paper-only, never live-validated** — no live order ever placed                                   | §15; SAFETY_ARCHITECTURE              |
| Kite `request_token` Rust-loopback auto-capture                                        | **Deferred** — manual paste is the v1 flow                                                                    | BLOCKERS Phase-10 #4                  |
| Copilot roster depth (`/agents/roster`, 3-pane panel, `delegate_to_persona`)           | **Deferred**                                                                                                  | BLOCKERS Phase-10 #5                  |
| Customizability follow-ups (connector hub, panel gallery, saved screens)               | **Deferred** — DataSource registry currently inert                                                            | BLOCKERS Phase-10 #6                  |
| `--onedir` MCP packaging (true cold-bind fix)                                          | **Deferred** — needs `tauri build`-verifiable change ci-local can't check                                     | BLOCKERS Phase 9.5                    |
| Light theme                                                                            | **Deferred to v1.1** — dark-only ships                                                                        | BLOCKERS S2 #10                       |
| Launch ops (signing, updater wiring, channels, landing page, LICENSE flip, TOS dialog) | **Mostly deferred** (Phase 7 → still open)                                                                    | BLOCKERS v0.7.0→Phase 10              |
| `auto_export`/auto-updater end-to-end                                                  | **Non-functional** — `createUpdaterArtifacts:false`, no frontend caller, no release workflow                  | §1, §14                               |
| Version strings (`0.8.0` everywhere)                                                   | **Stale** — Phase 8/9/9.5/10 unbumped; intent unverified                                                      | §14                                   |
| mypy/lint debt, a11y gaps, Linux transitive advisories                                 | **Known debt** — see BLOCKERS S2/S3/S4                                                                        | BLOCKERS                              |

**Bottom line:** green on every machine-checkable gate, unproven on every
human-checkable one. The §6.5 safety layer is the trustworthy core. The two
standing fragilities to watch are MCP cold-bind contention (worked around, not
root-fixed) and the unregistered non-India broker adapters (dead despite shipping
in the tree).

---

## 8. What the redesign keeps vs rebuilds

The "Cursor for finance" redesign should treat this codebase as a **strong
foundation with a thin, dated experience layer** — keep the substrate, rebuild
the surface and the agent-centrality.

### KEEP (the working foundation — do not rebuild)

- **The sidecar + data layer.** ~107 REST routes, the `provider_registry`
  dispatch seam, yfinance/ccxt/news/VADER/macro/QuantLib/49-indicators, the
  data-cache, the SSE convention. This is the data brain; it works and is broadly
  tested. The redesign consumes it, it does not replace it.
- **The §6.5 safety layer, intact.** Tier-1 LOCKED. The paper-default,
  append-only audit log, kill switch, AI-order gate, and defense-in-depth
  template are the most trustworthy assets — preserve byte-for-byte and run the
  audit suite as a hard gate on any touch (§5).
- **dockview panels + the workspace-blob persistence model.** The layout engine,
  the module registry, the opaque-blob round-trip, the unknown-component restore
  guard, the local-first ownership split (sidecar files + OS keychain). The
  _arrangement_ may change; the persistence + SSR-safe mounting mechanics are
  hard-won and should survive.
- **Kite read-only broker connect.** The genuine `generate_session` OAuth +
  read-only positions/holdings/P&L is the canonical BYOK pattern and the one
  end-to-end broker path. Keep it; the redesign can deepen it (granular reads,
  more brokers) without reopening §6.5.
- **The copilot tool loop + tool-schema contract.** The `invoke_agent` loop,
  `TOOL_SCHEMAS` + per-provider serialisers, the `tool_ids`-pop contract, the
  metadata-carried assistant tool-call turn, host-action execution, and
  terminal-state context injection. This is the spine of the agent experience —
  built once, working, and load-bearing. Keep the mechanism; expand the catalog.
- **BYOK + MCP-on-both-sides plumbing.** The keychain-mediated secret flow and
  the dual MCP role (proxy-in + serve-out) are real and reusable.

### REBUILD (the experience + agent-centrality + MCP-as-framework)

- **The experience / UI.** The shell is "a data viewer with a raw LLM chat
  bolted on" (Phase-10's own framing). The dark-only, header-less, command-
  palette-as-substring-match shell with no connection indicator and no light
  theme is the surface to rethink for an agent-first, "Cursor for finance"
  posture. Keep dockview as an engine; rebuild the chrome, the entry points, and
  the information hierarchy around the copilot.
- **Agent-centrality.** Today the copilot is one panel among 18. The redesign
  should promote it to the primary interaction model — but first **close the
  catalog gap** (~11 registered tools are invisible to every model for lack of a
  `TOOL_SCHEMAS` entry), **fix the Gemini multi-round break**, **reconcile the
  custom-agent allow-list** with the real catalog, and **resolve the default
  agent** (the shipped `copilot` defaults to an Ollama model that may not exist).
  The deferred roster depth (`/agents/roster`, 3-pane panel,
  `delegate_to_persona`) is the natural first build.
- **MCP-as-framework.** Today MCP is plumbing (two proxied subprocesses + a
  serve-out surface with a manual copy-paste external-client flow). A
  "Cursor for finance" thesis likely wants MCP as the _extension framework_ —
  the inert DataSource/connector registry, the dead stdio transport reserved for
  filesystem plugins, and the missing marketplace/signing/loader are where this
  becomes real. The contract supports it; the wiring does not exist yet.
- **The plugin runtime's missing guarantees.** Before leaning on plugins as the
  extension story, implement the manifest↔instance + `requiredHostVersion`
  checks the docs already claim, wire `PluginConfig.secrets`, and decide the fate
  of the seven dead-wired broker plugins (register them through the runtime, or
  retire them).
- **Distribution.** Unsigned, no release pipeline, stale version strings, a
  non-functional updater. A shippable product needs signing/notarization, the
  updater wired (`createUpdaterArtifacts:true` + a publish workflow), and the
  version-of-truth drift closed.

**One-line redesign thesis:** keep the sidecar, the safety layer, the panels,
the persistence model, the Kite read path, and the copilot tool loop; rebuild
the shell into an agent-first experience, promote MCP from plumbing to extension
framework, and close the copilot's catalog/provider gaps that quietly cap what
the agent can do today.
