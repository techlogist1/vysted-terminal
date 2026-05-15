# Changelog

Engineering log for Vysted Terminal — build-time decisions, failed approaches,
and per-phase outcomes. This is the _why_ record. Current-state docs live in
`CLAUDE.md` and `docs/BLUEPRINT.md`; this file is append-only history.

## v0.3.0 — Phase 2: Charting depth + Plugin runtime + OpenBB plugin (2026-05-15)

The chart panel goes from "credible" to TradingView-comparable, and the locked
`types/plugin.ts` contract gets its first real runtime consumer plus its first
real third-party-shaped data plugin (OpenBB ODP).

Built as three parallel Opus teammates from `main` after three foundation
commits — chart-features (A), plugin-runtime (B), openbb-plugin (C) — merged in
risk order B → A → C with one trivial hand-resolved merge on `sidecar/app.py`
(B added the `plugins` router; C added the `openbb` router + lifespan; the
union of both shipped). The 3-teammate decomposition was right-sized for the
surface: chart-features is highly cohesive and best owned by one agent, and the
lead absorbed the docs / screenshot composition / release work directly.

### Foundation (lead, pre-teammate dispatch)

- **`fix(yfinance): normalize dot-tickers (BRK.B → BRK-B)`** — yfinance returns
  502 for symbols with dots; its API expects the dash form. Added
  `_normalize_symbol()` and threaded it through every public `get_*` entry
  point. The returned model carries the normalized symbol so downstream
  re-fetches use the canonical form. 14 dedicated tests; resolves a
  v0.2.1-verification backlog item.
- **`feat(types): plugin-runtime support types`** — `types/plugin-runtime.ts`
  introduces `PluginManifest`, `LoadedPluginState`, `LoadedPlugin`,
  `HealthSample`, `PluginRuntimeEvent`, `PluginPersistedConfig`. Wraps the
  locked `VystedPlugin` contract; does NOT modify it.
- **`feat(types): chart drawing-tool spec`** — `types/drawings.ts` defines
  `DrawingKind`, `DrawingPoint`, `DrawingStyle`, `DrawingSpec`, and the
  `WorkspaceDrawings` JSON shape. Each drawing kind renders via an
  `ISeriesPrimitive` (the same pattern the existing
  `IchimokuCloudPrimitive` and `VolumeProfilePrimitive` use); workspace
  persistence rides the existing `.vysted-workspace` JSON path.

### Chart features (Teammate A)

- **30 new indicators** (catalog total now 50): Moving Averages (WMA / HMA /
  DEMA / TEMA / KAMA), Momentum (TSI / KST / Awesome Oscillator / PPO /
  Ultimate Oscillator), Volatility (Std Dev / Bollinger Bandwidth / Donchian
  Channels / Chaikin Volatility), Volume (A·D Line / Chaikin Money Flow /
  Force Index / Ease of Movement / VPT), Trend (Aroon / Aroon Oscillator /
  Vortex / Mass Index / Pivot Points / SuperTrend), Statistical (Linear
  Regression / Std Error Bands / HLC3 / OHLC4 / Median Price). Each follows
  the existing `compute_*` / `_BUILDERS` dispatch pattern with conventional
  aliases.
- **Indicator catalog UI** grouped into six section headers so the 50-entry
  selector stays scannable. New `category` field on `IndicatorDef` (TypeScript
  only — kept off the wire payload to avoid cross-language sync).
- **Ten drawing tools** as `ISeriesPrimitive` instances under
  `src/modules/chart/drawings/`: trendline, horizontal-line, vertical-line,
  ray, rectangle, ellipse, fib-retracement (0/0.236/0.382/0.5/0.618/0.786/1),
  fib-extension (same levels), parallel-channel, text. Toolbar UI with
  click-to-create + Esc/Delete keys + lock toggle + drawing inspector.
- **Drawing persistence** through `.vysted-workspace` JSON. `chartDrawings` is
  optional in `SerializedWorkspace` so older workspaces apply cleanly with an
  explicit `replaceAll({byPanel:{}})` reset on load.
- **Multi-chart sync** — chart panel converted to `singleton: false`;
  `useChartSyncBus` Zustand store with three independent flavors (crosshair /
  visibleRange / symbol). Subscribers self-identify by `source` so they skip
  self-echoes.
- **Comparison overlay** — second-symbol fetch at the active timeframe;
  optional normalize via `(close[i]/close[0]-1)*100` ridden on its own
  `priceScaleId: 'left'` so the candle scale is unaffected.
- **Pre-emptive fix:** stable empty references in `chart-sync.ts` /
  `ChartPanel` for fallback `useSyncExternalStore` reads, blocking a "Maximum
  update depth exceeded" infinite loop A diagnosed during integration.

### Plugin runtime (Teammate B)

- **`PluginRuntime` class** (`src/lib/plugin-runtime.ts`) — pure TypeScript,
  no Tauri invoke (decision A1). Discover / load / unload / health-check;
  capability negotiation gated on the `capabilities.contributesX` flags (a
  flag set without its getter `error`s the plugin without throwing); rolling
  health history bounded at 20 samples; typed `PluginRuntimeEvent`s with
  listener-error isolation.
- **`useModulesStore.appendModules()`** extends the registry without
  replacing — preserves `enabled[id]` from workspace replay, deduplicates on
  plugin id.
- **`usePluginsStore`** — React projection of the runtime: loaded plugins,
  dataSources, agents, nodes (the latter three not yet consumed by Phase-2
  UI but wired so Phase-3 can plug in without a runtime change).
- **Plugin Manager Panel** — lifecycle state badge, metadata, error banner,
  health-history strip, enable/disable toggle. Reachable via cmd+K
  (`/plugins`).
- **Sidecar-owned per-plugin config** — SQLite-backed `plugins_store` +
  `/plugins` router. Mirrors the workspace_store / portfolio_db pattern. **No
  new browser storage.**
- **`plugins/example/`** — minimal plugin proving the contract end-to-end:
  declares `contributesData=true` + `contributesCommands=true` +
  `supportsControlPlane=true`, exports one `DataSource` (`example-prices`)
  and one slash command (`/example`).
- **`bootstrapPlugins()`** wires the runtime into `src/app/page.tsx` on mount.
  Falls back to in-memory persistence when Tauri is absent so `pnpm dev`
  loads plugins as `active` instead of `error` for visual verification.

### OpenBB ODP plugin (Teammate C — Tier 2 separate-process)

- **Bundling decision: Tier 2 (separate-process).** Pivoted from Tier 1 after
  `pnpm sidecar:build` hit `ResolutionImpossible`: `openbb-core 1.6.9`
  strictly pins `fastapi <0.129` and `uvicorn <0.41`, both incompatible with
  Vysted's main-sidecar pins (0.136 / 0.46). Downgrading would have leaked
  strict pinning into every Vysted release; the brief's §A2 escape hatch
  applies exactly.
- **OpenBB lives in its own venv** under `sidecar/openbb_subprocess/`,
  packaged as its own PyInstaller `--onefile` binary by
  `scripts/ensure-openbb-sidecar.mjs`. Subprocess uses
  `RouterLoader.from_extensions()` + `CommandRunner.sync_run` (NOT `import
openbb` — the meta-package triggers static-package codegen that writes into
  `site-packages`, fatal under `--onefile` read-only fs).
- **Subprocess pins:** `fastapi==0.128.8`, `uvicorn==0.40.0`,
  `openbb-core==1.6.9`, `openbb-equity==1.6.1`, `openbb-economy==1.6.1`,
  `openbb-yfinance==1.6.2`, `openbb-fred==1.6.0`, `openbb-fmp==1.6.0`.
- **Bundle delta: +43 MB** for the new OpenBB subprocess binary on Windows.
  Main sidecar binary unchanged at 56.9 MB; total Phase-2 binary footprint
  ≈ 100 MB.
- **`plugins/openbb/`** — exports a `VystedPlugin` declaring `pluginType:
"data-source"` + `contributesData=true`. `getDataSources()` enumerates
  equity / fundamentals / macro classes. `healthCheck()` reports the real
  state of the subprocess.
- **`provider_registry`** gains OpenBB-prefer wrappers for fundamentals /
  income statement / balance sheet / cash flow / analyst rating, each
  falling back to yfinance on `ProviderError` (logged at WARNING). Macro is
  OpenBB-only — clean ProviderError when unavailable.
- **FastAPI lifespan** calls `openbb_provider.shutdown()` on app shutdown so
  a `pnpm tauri dev` restart does not orphan the OpenBB binary. Subprocess
  inherits the stdin-EOF watchdog Phase-1 already validated.

### Decisions

- **3-teammate decomposition** (Tier-3): the brief floated four; the operator
  approved three because the chart-features scope is highly cohesive and
  splitting it would have manufactured conflict surface on `ChartPanel.tsx`.
  Lead absorbed docs + screenshot composition + release work directly.
- **OpenBB Tier 2 over Tier 1** (Tier-3): per the documented escape hatch
  in plan §A2, after `ResolutionImpossible` was reproduced twice (once
  direct-resolve, once after manually downgrading `fastapi` to 0.128.8 to
  surface the uvicorn conflict).
- **`category` field on `IndicatorDef` (TS only, not Pydantic)** (Tier-3):
  the sidecar already returns enough (`name` + `panel`); category is a pure
  UI grouping concern, no need to thread it through the wire payload and
  cross-language sync.
- **All ten drawing renderers in one `renderers.ts`** (Tier-3): each
  renderer class is small (~30 lines); a single file makes the
  kind→renderer mapping in `factory.ts` and the FIB_LEVELS constant
  trivially shared.
- **Subprocess lifecycle owned by main sidecar, not by plugin** (Tier-3):
  the plan's "launched on plugin enable, killed on plugin disable" needs
  cross-process control plane that Phase 2 doesn't ship. Lazy-launch on
  first request + main-sidecar shutdown is semantically equivalent for the
  v0.3.0 bundled-only-plugins regime and reuses the existing
  Tauri-supervised stdin-EOF watchdog pattern.
- **In-memory persistence fallback at plugin bootstrap** (Tier-3): the
  runtime should work in dev mode for visual verification, not just
  production with the sidecar. Added inside `bootstrapPlugins()`; production
  unchanged.

### Failed approaches & fixes

- **Tier-1 OpenBB bundling fails on `pnpm sidecar:build`.** `openbb-core
1.6.9` strictly pins `fastapi (>=0.128.0,<0.129.0)` and `uvicorn
(>=0.40.0,<0.41.0)`, both incompatible with Vysted's main-sidecar pins.
  Fixed by pivoting to Tier 2 (separate-process). Recorded as the canonical
  example of when the §A2 escape hatch applies.
- **`subprocess.Popen` → bundled-OpenBB on Windows hangs in prewarm.**
  The same binary launched via PowerShell `Start-Process` reaches HTTP/200
  in ~3-4 s; under `subprocess.Popen` the prewarm thread deadlocks
  indefinitely (anyio + PyInstaller `_MEIPASS` + Windows handle inheritance
  interaction). Tested every plausible `stdin` / `creationflags` /
  `close_fds` combination + rewrote the subprocess's stdin-EOF watchdog from
  `sys.stdin.buffer.read` to `os.read(fd,...)` — none changed the deadlock.
  **Cached-failure logic ensures the registry's yfinance fallback is fast on
  subsequent calls** so users still get fundamentals/macro data; the
  subprocess is a dormant performance optimization that lights up only when
  the launch path is fixed. Phase-3 fix candidates: spawn via Tauri Rust
  `Command::new` (different Windows handle semantics), or wrap the launch
  in a small Rust helper. See `BLOCKERS.md` for the full investigation log.
- **"Maximum update depth exceeded" infinite loop in chart-sync.** Diagnosed
  by Teammate A during integration: `useSyncExternalStore` was seeing a
  fresh empty-object reference on every render of the fallback path. Fixed
  with module-level frozen empty references in `chart-sync.ts` and
  `ChartPanel`.
- **Lead missed `rustc` on PATH for `pnpm sidecar:build`.** The Rust
  toolchain at `~/.cargo/bin` is not on the default shell PATH; the build
  script's `rustc -vV` target-triple probe failed. Fixed by prepending the
  cargo bin dir before invoking `pnpm sidecar:build`. Documented in
  CLAUDE.md gotchas (and in `~/.claude/projects/.../memory/`).

### Known issues (carried into v0.3.0 ship)

Recorded in `BLOCKERS.md` — none blocks the v0.3.0 tag:

- **OpenBB subprocess hangs under `subprocess.Popen` on Windows.** The
  bundle and the standalone path both work; the Python-spawned path
  deadlocks. Registry falls back to yfinance; user-facing fundamentals /
  macro still work. Phase-3 fix candidate documented above.
- **On-canvas drawing screenshots not captured via chrome-devtools.**
  lightweight-charts rejects synthesised mouse events (`isTrusted` check),
  so chrome-devtools cannot exercise the click-to-create gesture.
  Drawings have full unit-test canvas-call coverage, and the toolbar UI
  - drawing-inspector populated screenshots prove the wiring; an end-user
    `pnpm tauri dev` session demonstrates them live.

### Verification

- `pnpm typecheck` / `pnpm lint` / `pnpm format:check` / `pnpm test` (139
  passed) / `pnpm build`.
- `sidecar` `pytest` (190 passed) / `ruff check` / `ruff format --check`.
- `cargo fmt --check` / `cargo clippy -D warnings` / `cargo test` (1 passed).
- `pnpm sidecar:build` — main sidecar `--onefile` binary 56.9 MB (unchanged
  from v0.2.1).
- `pnpm openbb-sidecar:build` — OpenBB subprocess `--onefile` binary 43 MB
  (additive). Total binary footprint ≈ 100 MB on Windows.
- CI green on Windows, macOS, Linux (verified locally on Windows; CI
  matrices verifies all three).

### Visual proof

`docs/screenshots/v0.3.0/`:

- **`teammate-a/`** — chart with multiple new indicators across all six
  categories; drawing toolbar in active state; populated chart at both
  resolutions.
- **`teammate-b/`** — plugin manager panel showing the example plugin loaded
  and active, with metadata + health-history strip; cmd+K filtered on the
  example plugin's `/example` slash command.
- **`teammate-c/`** — Equity Overview populated with AAPL data sourced via
  OpenBB (provider field reads `openbb`); per-folder README documents
  provenance.

## v0.2.1 — Phase 1 polish pass (2026-05-15)

Every `BLOCKERS.md` item from v0.2.0 resolved, plus scrollbar + panel-fit
visual polish. Built as four parallel Opus teammates from `main` — chart-polish,
state-lift, equity-fix, visual — merged in risk order C → D → B → A. The
conflict-free decomposition held with one trivial auto-merge on
`WatchlistPanel.tsx` (B import-line, D container-className).

### Fixes

- **Chart — Volume Profile horizontal-histogram primitive.** The 24-bucket data
  is now returned through a dedicated `volume_profile` field on
  `IndicatorResponse` (real `price: float` per bucket) — retiring the v0.2.0
  `time`-field overload. The frontend draws it via a new
  `ISeriesPrimitive` (`src/modules/chart/volume-profile-primitive.ts`) attached
  to the candle series: right-anchored amber bars positioned by
  `priceToCoordinate(bucket.price)`, height auto-derived from adjacent-bucket
  spacing.
- **Chart — Parabolic SAR dot markers.** Replaced the line-series rendering
  with `createSeriesMarkers` circle dots — sage below-bar for uptrend
  (SAR < close), negative-clay above-bar for downtrend (SAR > close). The
  Wilder math is unchanged.
- **Chart — VWAP session-anchoring (intraday).** `compute_vwap` now infers
  intraday from the median bar-to-bar gap and resets the cumulative numerator
  /denominator at each calendar-date boundary; daily+ keeps the running
  whole-series cumulative. The line label switches to "VWAP (session)" when
  anchored.
- **Chart — Ichimoku forward cloud.** `compute_ichimoku` infers the bar
  interval and emits Senkou A/B on the extended time axis (`times + 26 future
timestamps`) so the +26 shift is preserved as a forward projection rather
  than dropped. A new `ISeriesPrimitive`
  (`src/modules/chart/ichimoku-cloud-primitive.ts`) fills the band between
  Senkou A and B — semi-transparent sage where A ≥ B, semi-transparent negative
  where B > A.
- **News ↔ watchlist linking.** The watchlist module's store moved to a shared
  `src/store/symbols.ts` (`useSymbolsStore`, `SymbolEntry`, `DEFAULT_SYMBOLS`,
  and a `toNewsSymbol` mapper that drops the quote leg from pair symbols —
  `BTC/USDT` → `BTC`). The news feed subscribes to it and re-fetches when the
  watchlist changes; the hardcoded `DEFAULT_SYMBOLS` is gone.
- **Equity Overview — dividend yield units.** yfinance 1.3.0 returns
  `dividendYield` as a percentage number (verified across AAPL/MSFT/KO/VZ/T);
  `get_fundamentals` now divides by 100 so `Fundamentals.dividend_yield` is a
  true fraction and the panel's existing `* 100` display is correct. AAPL now
  renders 0.36% rather than 36%.
- **Scrollbars — Vysted-themed.** `globals.css` adds a global webkit +
  Firefox scrollbar block — 8 px, transparent track, amber-500 @ 40% thumb,
  brighter on hover.
- **Panel-fit pass.** Tabular scroll containers switched from `overflow-auto`
  to `overflow-y-auto overflow-x-hidden` with `scrollbar-gutter: stable`;
  tables use `table-fixed` with constrained label cells so no accidental
  horizontal scroll is forced. `default-layout` resizes the chart group to
  ~63 % of the host width via post-placement `panel.api.setSize`, splitting
  the right column into three roughly-even thirds — verified visually at
  1920×1080 and 2560×1440.

### Lead integration

- `chore(lint): ignore .claude/ worktrees and nested build output in eslint
config` — a teammate's `pnpm build` inside their `.claude/worktrees/agent-*`
  checkout leaves a `.next/build/` tree there; the root-only `.next/**` glob
  did not match it. Added `.claude/**` plus `**/.next/**` /
  `**/node_modules/**` / `**/out/**` so lint stays scoped to first-party source
  regardless of worktree state.

### Visual proof

`docs/screenshots/v0.2.1/`:

- `chart-volume-profile-sar-ichimoku.png` — the three new chart renderers
  rendering against live SPY data, zero console errors.
- `chart-vwap-intraday.png` — SPY 1h with the session-anchored VWAP labelled
  "VWAP (session)".
- `equity-dividend-yield.png` — AAPL now reading 0.36 %.
- `scrollbar-themed.png` — the amber Vysted scrollbar on the news feed.

`docs/screenshots/v0.2.1-equity-fit/` — the layout pair was recaptured in
commit `00606e7` (Equity Overview overflow fix) and now lives there rather
than alongside the v0.2.1-tag shots; the original v0.2.1-tag `layout-*.png`
was overwritten in-place and is unrecoverable. See the folder's `README.md`
and `CLAUDE.md` → **Screenshot organization**.

- `layout-1920x1080.png`, `layout-2560x1440.png` — post-fix, AAPL populated,
  chart-dominant proportions, no accidental horizontal scrollbars.

### Verification

- `pnpm typecheck` / `pnpm lint` / `pnpm format:check` / `pnpm test` (63
  passed) / `pnpm build`.
- `sidecar` `pytest` (98 passed) / `ruff check` / `ruff format --check`.
- `cargo fmt --check` / `cargo clippy -D warnings` / `cargo test`.
- `pnpm tauri dev` boots end-to-end; sidecar healthy; the five panels'
  HTTP / WebSocket requests succeed; zero runtime warnings or sidecar errors.
- CI green on Windows, macOS, Linux.

## v0.2.0 — Phase 1: Data Layer + Core Panels (2026-05-15)

Real market data flowing through five core panels, a dockview layout engine,
module toggles, workspace save/load, and a wired command palette. Built as a
five-agent autonomous sprint: a lead-owned data-layer + scaffold foundation,
four parallel teammates in isolated worktrees, then lead integration.

### Shipped

- **Sidecar data layer.** Restructured into `models/` + `services/` +
  `routers/`. Providers: yfinance (no-key equity default) and ccxt including
  ccxt.pro WebSockets (Bybit/Binance/Kraken/Coinbase), behind a provider
  registry. Pydantic models — `Quote`, `OHLCV*`, `Macro*`, `Fundamentals`, the
  three financial statements, `AnalystRating`, `NewsItem`, `Position`,
  `Indicator*` — mirrored by hand in `types/data.ts`. REST plus a crypto
  WebSocket stream; documented in `docs/SIDECAR_API.md`. Tests mock every
  provider — no live API calls in CI.
- **Five panels with real data.** Chart (lightweight-charts, multi-pane,
  20 server-computed indicators), Watchlist (pre-loaded SPY/QQQ/BTC/ETH/NVDA/
  AAPL, add-remove, polled live quotes), News (RSS + optional NewsAPI, VADER
  sentiment per item), Portfolio (manual positions in local SQLite, P&L /
  weight / concentration computed client-side), Equity Overview (fundamentals +
  ratios + statement excerpts + analyst ratings).
- **Platform.** dockview layout engine with a curated first-launch layout
  (BLUEPRINT §5.1); a `VystedModule` registry; a Settings panel with per-module
  enable/disable; `.vysted-workspace` save/load (sidecar-owned persistence);
  cmd+K wired to list, filter, keyboard-navigate, and execute commands.
- **Tauri core.** `get_sidecar_port` command; per-OS app-data directory passed
  to the sidecar as `--data-dir`.
- **CLAUDE.md** gained a "Decision authority" section (four decision tiers) so
  future autonomous sessions self-resolve spec ambiguities.

### Decisions

- **OpenBB ODP deferred to Phase 2** (Tier-3). The PyInstaller `--onefile`
  macOS bundle of the OpenBB meta-package cannot be vetted locally, and the
  blueprint already schedules an OpenBB ODP wrap _plugin_ for Phase 2 — cleaner
  than baking it into the core sidecar then re-extracting it. yfinance + ccxt
  serve every Phase 1 panel; the provider registry slots OpenBB in later with
  no router or panel changes.
- **dockview** as the layout engine (Tier-3): a native fit for the BLUEPRINT
  §5.2 customization primitives, maximum sandboxability per product positioning.
- **Sidecar-owned persistence** (Tier-3): the sidecar owns the portfolio SQLite
  database and the `workspaces/` directory, avoiding a `tauri-plugin-fs`
  dependency; the frontend never touches the filesystem.
- **Lexicon sentiment (VADER)** over a model-based scorer (Tier-3): FinBERT/torch
  cannot be safely bundled in the `--onefile` binary. Tradeoff: coarser,
  social-media-tuned scores.
- **Phase 1.A shipped as two lead commits** — the sidecar data layer plus a
  frontend module-registry/dockview scaffold — because the brief assumed a
  "module registry pattern" that Phase 0 had not actually built. The four
  teammates branched from both.
- **Conflict-free teammate decomposition.** Each teammate owned a disjoint file
  set (own module directory + own sidecar router/service/test); only one
  touched `package.json`, one `requirements.txt`, one the shared stores. All
  four merges were clean — zero conflicts.
- Visual verification used the **chrome-devtools MCP** — the session-available
  browser-automation MCP — driving the browser-rendered frontend against a live
  sidecar via a mocked Tauri bridge.

### Failed approaches & fixes

- **Local `main` diverged from `origin/main`.** Lead doc commits were made to
  local `main` but not pushed before branching; the rebase-merge of the Phase
  1.A PR re-created all four commits with fresh SHAs and `git pull --ff-only`
  then failed. Fixed with `git reset --hard origin/main` — no content lost,
  origin was the superset.
- **PyInstaller `--onefile` orphan-worker `EBUSY`.** Smoke-testing the sidecar
  binary directly and killing the bootloader PID left the re-exec'd worker
  alive, holding the binary locked and breaking the next `ensure-sidecar.mjs`
  copy. Fixed by killing by name wildcard (`vysted-sidecar*`); recorded in
  CLAUDE.md Gotchas.
- **`test_app.py` scaffold test went stale.** The Phase 1.A-2 test asserted four
  stub routers returned a `_status` payload; Phase 1.B replaced the stubs with
  real endpoints. At integration the test was rewritten to verify the real
  routers are mounted via the OpenAPI schema, and the vestigial `_status`
  endpoints were removed.

### Known issues / cosmetic

Recorded in `BLOCKERS.md` — none needs operator action:

- **Chart indicators**: all 20 are computed and unit-tested server-side; five
  have simplified rendering/semantics — Volume Profile is computed but not yet
  drawn (needs a horizontal-histogram renderer), Parabolic SAR draws as a line
  rather than dots, VWAP is running rather than session-anchored, Ichimoku has
  no forward cloud projection.
- **News ↔ watchlist linking** is deferred — the feed filters a built-in symbol
  set rather than the live watchlist store (a module boundary the parallel
  teammates could not cross).
- **Equity Overview dividend yield** renders ~100× too large (a yfinance 1.3.0
  units quirk) — cosmetic, single field.

## Scope update — global broker execution in v1.0 (2026-05-14)

**Docs-only.** No code changed — `types/plugin.ts` and every other source file are
untouched. The existing plugin contract already supports broker plugins via
`getDataSources` / `getPanels` / `executeCommand`. This entry records a scope
decision taken between Phase 0 and Phase 1.

### Decision

Broker integrations move from the v1.1/v2.0 deferred lists into v1.0 with full
execution capability. Vysted Terminal is an open-source platform from day one, and
its value proposition — see your portfolio, analyze it with AI, execute — is
incomplete without the execute step. A read-only-only v1.0 ships a thinner product
than the positioning promises. Execution belongs in the first release.

### Scope

- Six broker plugins plus a ccxt crypto execution wrap (seven broker integrations
  total): Dhan, Angel One SmartAPI, Zerodha Kite Connect, Alpaca, Interactive
  Brokers, OANDA v20, and ccxt for crypto. Each is a separate plugin on the existing
  `VystedPlugin` contract.
- A shared execution safety layer is baked in, not optional — paper-mode default,
  per-order confirmation, configurable position-size limits, a local SQLite audit
  log, a global kill switch, an extra gate on AI-initiated orders, per-plugin
  read-only mode, and layered liability disclaimers. Full design in
  `docs/BLUEPRINT.md` §6.5.
- Phase 5 absorbs this: its estimate grows from ~3-5 days (Tradesa V2 alone) to
  ~6-8 days (Tradesa V2 + broker integration + safety layer). The phase is not split
  and the numbering is unchanged. The v1.0 calendar target still holds at the
  operator's 2-3 sessions/day velocity.

### Research corrections

The broker landscape was verified by web search this session. Four corrections to
earlier assumptions, recorded as historical decisions:

- **IBKR Python SDK is `ib_async`, not `ib_insync`.** `ib_insync` was forked to the
  `ib-api-reloaded` org and renamed `ib_async` after the original maintainer, Ewald
  de Wit, passed away in early 2024. `ib_async` (current v2.1.0) is the active
  library; use it going forward.
- **Zerodha Kite Connect pricing is ₹500/month (~$6 USD)**, not the ~$14/month
  figure assumed earlier. The price was reduced in May 2025 after NSE algo-trading
  regulatory clarification.
- **Kite Connect Personal API is free for execution + account data.** Order
  placement and account/holdings/positions endpoints are included at no cost; the
  paid ₹500/month Connect tier adds real-time and historical market data only.
- **Kite requires a static IP for order placement, since 1 April 2025.** This is a
  SEBI/NSE algo-trading regulation, not a Zerodha policy. Order requests from
  unregistered IPs are rejected; up to 2 static IPs are allowed per account; other
  endpoints (data, holdings, positions) work from any IP. A material UX constraint
  for Vysted users on residential dynamic IPs — the Kite plugin must surface it
  in-app.

## v0.1.0 — Phase 0: Foundation (2026-05-14)

The greenfield foundation: a working local dev environment plus all scaffolding
that Phases 1–7 plug into. `pnpm install && pnpm tauri dev` opens a Vysted
Terminal window with a Welcome panel and a cmd+K command palette; a Python
sidecar is spawned and supervised by the Tauri core.

### Shipped

- Greenfield repo + GitHub remote (`techlogist1/vysted-terminal`), flat
  (non-monorepo) layout.
- Tauri 2.x core (Rust) — windowing, Python sidecar lifecycle, updater plugin
  stub.
- Next.js 16 + React 19 + TypeScript frontend, statically exported.
- Tailwind 4 (CSS-first `@theme`) + shadcn/ui + Zustand + Framer Motion.
- Vysted design tokens (`styles/tokens.css`) — charcoal / amber / sage palette,
  serif + monospace type.
- One mock Welcome panel; cmd+K / ctrl+K command palette skeleton (no commands
  wired).
- Python 3.13 FastAPI sidecar with a `/health` endpoint; PyInstaller one-file
  bundling via `scripts/ensure-sidecar.mjs`; spawned by the Tauri core on a
  free port and killed on exit.
- `types/plugin.ts` — the `VystedPlugin` contract, all six capabilities.
- CI: `build` / `lint` / `test` workflows, matrixed across Windows, macOS, and
  Linux.
- Licensing: AGPL-3.0 (`LICENSE`) + draft commercial dual-license
  (`COMMERCIAL_LICENSE.md`).
- Docs: `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`, sanitized
  `docs/BLUEPRINT.md`.

### Decisions

- **Next.js 16**, not the literal "Next.js 14" named in the brief — operator-
  approved; the same brief also required "latest stable as of May 2026".
- **Python 3.13** (the installed version), not 3.12 — operator-approved; fully
  supported by FastAPI and PyInstaller.
- **ESLint pinned to 9.39.4**, not 10.x — `eslint-config-next@16.2.6` ships
  `eslint-plugin-react@7.37.5`, which calls `context.getFilename()`, removed in
  ESLint 10. The Next 16 lint preset is not yet ESLint-10-compatible.
- **`types/plugin.ts` uses `unknown`** where blueprint §3.3 wrote `any` (the
  `subscribe` event and `executeCommand` args) — a flagged hardening so type
  safety is not lost at every plugin boundary.
- **Tailwind 4 (CSS-first).** Design tokens are an `@theme` block in
  `styles/tokens.css`; semantic shadcn mapping lives in `src/app/globals.css`.
- **Bundle targets** explicitly `[deb, appimage, nsis, app, dmg]` — excludes
  `rpm` (no `rpmbuild` on `ubuntu-latest`) and `msi` (avoids a WiX dependency).
- **Sidecar build is idempotent** and wired into Tauri's `beforeDevCommand` /
  `beforeBuildCommand`, so a bare `pnpm tauri dev` builds the sidecar on first
  run.
- **Updater is a real-keypair stub** — the public key is in `tauri.conf.json`;
  the private key `src-tauri/vysted-updater.key` is gitignored and handed to the
  operator for Phase 7. `createUpdaterArtifacts` stays `false`.
- `rustfmt` and `clippy` components were added to the local Rust toolchain via
  `rustup component add` — required by the lint workflow.

### Failed approaches & fixes

- **ESLint flat config via `FlatCompat`** threw a circular-reference error
  validating `eslint-config-next`'s shareable configs. Fixed by importing
  `eslint-config-next`'s native flat-config arrays directly and dropping
  `@eslint/eslintrc`. (ESLint 10 itself then proved incompatible — see
  Decisions.)
- **PyInstaller `--onefile` orphaned the sidecar worker.** The one-file
  bootloader re-execs a worker child; killing the bootloader (Tauri's
  `child.kill()`, or a `Stop-Process`) left the worker alive and holding a lock
  on the binary. Fixed with a stdin-EOF watchdog in `sidecar/main.py`: when the
  Tauri core drops the `CommandChild`, stdin closes and the worker self-exits.
- **`ensure-sidecar.mjs` copy hit `EBUSY`** — a freshly built `.exe` is briefly
  locked by antivirus / the search indexer. Added a copy-retry with backoff.
- **Flaky `macos-latest` CI build** — `cargo metadata` resolved to `rustup-init`
  on some runner images. Fixed by prepending `~/.cargo/bin` to `$GITHUB_PATH`
  and re-asserting `rustup default stable` in all three workflows.

### Known issues / cosmetic

- `pnpm tauri dev` exits with code `4294967295` on Windows when the window is
  closed — a WebView2-teardown artifact, not a real failure. Does not affect
  `tauri build` or CI.
- GitHub Actions notes that `actions/*` and `pnpm/action-setup` still run on
  Node 20 (deprecation notice, not an error). Revisit before the June 2026
  enforcement date.
