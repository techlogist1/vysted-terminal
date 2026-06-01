# Pass B — build-window kickoff (read this first, fully)

_A self-contained handoff for a **fresh** window that will build Pass B. Read this end-to-end and you
have everything: what's locked, what's already built (don't rebuild), what Pass B adds, the seams, the
rig, and the hard safety rules. The spec is **operator-ratified and locked**; this window **builds it**,
phase by phase. Authored 2026-06-01 by the spec-authoring window (Opus 4.8, 1M)._

> **The build is greenlit per phase by the operator.** Do **not** run all phases blind. Each phase ships
> full-scope, is rig-verified, passes `ci-local` + the §6.5 audit, and is reviewed by the operator before
> the next phase starts.

---

## 0. The 60-second orientation

Vysted Terminal is becoming a **BYOK, local-first, open-source, agent-native** competitor to Perplexity
Finance — **better because the agent ("JARVIS") builds the research workspace**. You say "research NVDA"
and JARVIS arranges the cockpit, loads locale-correct data, applies sensible indicators, pulls
filings/news, runs a light web round, and drops a synthesized **cited brief** — like it read your mind.
The illusion rests on three pillars that must each be complete: **capability completeness** (every
obvious action), **smart-defaults judgment** (a thoughtful cockpit, not one tile), and **resourcefulness**
(never dead-end / never raw JSON / never wrong data).

Pass A + A.2.0 already built the **foundation**. Pass B builds the **research layer** on top. You are in
the Pass-B build window.

## 1. Read order (canonical)

1. **`specs/001-agent-native-redesign/spec.md`** — the LOCKED spec. Pass B = US11–US17, FR-060–FR-111,
   SC-016–SC-025, Clarifications → **Session 2026-06-01** (the 12 ratified decisions), Open Product
   Decisions — Pass B.
2. **`specs/001-agent-native-redesign/plan.md`** — the **phased plan** (B1–B6), each with seams + a
   rig-verifiable gate. **This is your build order.**
3. **`docs/redesign/PASS_B_RESEARCH.md`** — the 42-agent verified grounding (India data stack, symbol
   resolution, the 3 search tiers, the dexter/deep-research loop, Perplexity teardown, indicator/layout
   taste, /@ command precedents). Cite it; it corrects several myths (yfinance is broken for NSE; native
   search is billable-not-free; Bing is dead; dexter is TypeScript).
4. **`docs/redesign/EXTENSION_SEAMS.md`** — the four Pass-A seams Pass B plugs into (capability catalog,
   provider registry, model registry, region). Pass B = **config + adapters**, not refactors.
5. **`.specify/memory/constitution.md`** — now **v1.1.0**; Principle VIII (Locale-Native & Correct,
   Everywhere) was added for Pass B. The principle wins on conflict.
6. **`docs/CURRENT_STATE.md`** §0/§0.5/§3–§8 — the honest baseline (what works vs is scaffolding).
7. **`CLAUDE.md`** — active rules + gotchas (sidecar spawn, catalog single-source-of-truth, dockview,
   versioning, verification gates). **Authoritative for how-to.**

## 2. What is ALREADY BUILT (do NOT rebuild — consume it)

- **Sidecar + data layer:** ~107 REST routes, the `provider_registry` resolve-by-model-key seam,
  yfinance/ccxt/news/macro/49-indicators/QuantLib, the SSE convention, `data_cache`.
- **The capability catalog** (`sidecar/services/agent_tools/catalog.py`) is the **one source of truth** —
  `TOOL_SCHEMAS`, the custom-agent allow-list, and the external MCP surface all derive from it. The
  Gemini multi-round break is fixed; the ~11-handler gap is closed (27 caps). **Add a tool = catalog
  entry + handler + `registry_v0_6_0` wiring + an agent allow-list id.** Never hand-edit the projections.
- **JARVIS host-actions + the diff/accept gate:** `open_panel / close_panel / focus_panel / arrange_layout
/ set_chart_symbol / add_to_watchlist / propose_order` route through `src/store/proposed-changes.ts`
  (orders hard-excluded at the enqueue chokepoint). **ASK/AUTO autonomy** (`src/store/agent-autonomy.ts`):
  AUTO auto-applies UI/layout/chart/watchlist only; **an order never auto-applies in any mode**.
- **The chart command channel** (`src/store/chart-command.ts`) — `loadSymbol` lands on the chart;
  `set_chart_symbol` is verified. Indicators are **server-computed** (49 + volume_profile); the canvas
  palette is single-sourced in `src/lib/chart-theme.ts` (canvas can't read CSS vars).
- **Multi-portfolio store** (`src/store/portfolios.ts`, Pass A.2.0) — named portfolios, manual holdings,
  persisted in the workspace blob. The fake `+107.69%` demo is gone. _(The `get_portfolio` agent read
  diverges — that's Pass-B Phase B6, Pillar F.)_
- **Durable Delegate runs + BudgetGuard** (`run_manager` / `runs_store` / `budget_guard`) — reuse these
  for the deep-research budget (Phase B4).
- **Provider registry + BYOK credentials hub + marketplace** (Pass A P2/P3) — data sources are plugins;
  secrets in the OS keychain (renderer reads, passes per request; the sidecar cannot read the keychain).
- **Region seam** (`src/lib/region.ts` + `settings` + `format.ts`) — frontend region setting exists;
  **the sidecar `get_region()` does not yet** (Phase B1).
- **Warm theme + animations + Cursor-grade settings/keybindings** (Pass A/A.2.0). _(The spec's US6
  "minimal-dark" is a separate redesign track; Pass B does not re-skin.)_

## 3. What Pass B ADDS (the six pillars → six phases)

| Phase  | Pillar                       | Adds                                                                                                                                                                                                      | Gate (rig)                                                                                               |
| ------ | ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| **B1** | A — locale data              | `get_region()`; provider-registry region routing; `india_provider` (keyless jugaad-data/NSE-Bhavcopy); symbol resolver + masters; **correctness gate**; region-keyed news/screener/macro; locale currency | GOLDBEES/TATASTEEL (IN) correct or honest-unavailable; US unaffected; provenance; 0 dead-ends/wrong data |
| **B2** | D — JARVIS completeness      | `set_chart_indicators` + presets; `arrange_layout` named templates; `compare_symbols`; resourcefulness wired to B1 fallback                                                                               | "set up NVDA" → research-cockpit (not one tile); every action reachable; GOLDBEES no raw-JSON; all gated |
| **B3** | C — web search               | search-backend interface; native-on-key dispatch + citation normalizer + per-run cap; honest fallback; **Exa** BYOK plugin; SearXNG local                                                                 | grounded search on user's key; honest fallback; locale domains; 0 silent fails                           |
| **B4** | B — research engine          | fast loop (≤15s, B+A) + deep loop (BudgetGuard-bounded, abort→synthesize) + Perplexity Sonar opt-in; **BriefPanel** (citations/sources/step-log)                                                          | "research NVDA" → cockpit + brief ≥3 cites ≤15s; deep bounded; opt-in cost-shown                         |
| **B5** | E — /@ commands              | curated 11 slash + 9 @ (locale-aware @TICKER; @analyst/@quant prompt-prefix)                                                                                                                              | pickers resolve; `/compare @AAPL @MSFT` composes                                                         |
| **B6** | F — portfolio truth + polish | portfolio panel publishes holdings to the context bus → agent reads real store; empty/loading/error polish; full SC verification                                                                          | agent portfolio == UI portfolio, 0 divergence; full SC suite green                                       |

**The 12 ratified decisions** (spec Clarifications → Session 2026-06-01) — build to these exactly:
US+India both deep · keyless jugaad-data/Bhavcopy default (yfinance gated) · get_portfolio via context bus
· prompt-driven assembly · native-search default + honest fallback · Exa default BYOK search · FAST
default + /deep (rounds 3/wall 120s) · Perplexity Sonar opt-in · research-cockpit + brief-as-dockview-panel
· curated 11+9 commands (custom deferred) · BYO SearXNG URL + autodetect · Principle VIII added.

## 4. HARD safety rules (every phase — non-negotiable)

- **§6.5 + Tier-1 LOCKED files are byte-for-byte sacred:** `types/plugin.ts`, `types/safety.ts`,
  `types/broker.ts`, the safety/broker/audit/kill-switch models, `sidecar/services/broker_base.py`,
  `src-tauri/src/kill_switch.rs`, `sidecar/tests/test_safety_end_to_end.py`,
  `src-tauri/tauri.conf.json`, CI workflows. **Do not touch them.** If a pillar seems to need it →
  **STOP-AND-SURFACE** to the operator and route around.
- **Brokers stay read-only; no execution path.** No `place_/submit_/execute_order`, no `auto_approve`
  (the grep gate `test_audit_2/6` fails CI otherwise). `propose_order` never places.
- **Every agent mutation rides the diff/accept gate.** AUTO auto-applies **UI/layout/chart/watchlist
  only** — **never an order, in any mode**. §6.5 is never bypassed.
- **Min panel sizes stay HOST-SIDE** (PanelHost / component→min map), never in `PanelSpec`
  (`types/plugin.ts` is LOCKED).
- **Secrets:** renderer reads the OS keychain and passes per request (header for read-only plugins); the
  **sidecar cannot read the keychain**; never log/echo/persist. Loopback only.
- **Run the §6.5 audit (`test_safety_end_to_end.py` → 9/9) as a hard gate on any sidecar touch.**

## 5. The rig (tauri-mcp) — dev-only, how to drive it

- **Start a session** then drive the **real running Tauri app**: `list_windows` → `focus_window` (always
  **focus the window BEFORE a screenshot** — an occluded/asleep WKWebView returns a black frame) →
  `screenshot` / `snapshot` (DOM) / `click` / `fill` / `press_key` / `evaluate_script` / `get_logs`.
- **The rig is DEV-ONLY** (feature flag + `NODE_ENV` guards). The dev store handle `__vystedStores` and
  `__vystedDockview` are `NODE_ENV`-stripped. Never ship rig hooks to prod.
- **Verify against the live DOM + live pixels, not just code** — Pass A/A.2.0 caught three live-only bugs
  the code-readers missed (abyss-shell cold tabs, a 443px palette overflow, the sidecar-not-code fake
  portfolio). When the display may be asleep, a `caffeinate` keeps it awake; DOM/computed-style reads are
  valid structural evidence when pixels aren't available.
- **chrome-devtools MCP can't synthesize trusted (`isTrusted`) events** — canvas-interactive features
  (chart drawings, drag-to-pan, lightweight-charts gestures, node-editor DnD) need Playwright/native
  injection, not chrome-devtools.
- **Screenshots used as proof MUST show POPULATED state** (real data), dark theme, at **both** 1920×1080
  and 2560×1440, in a per-tag subfolder under `docs/screenshots/`, **never overwriting** existing shots.

## 6. dockview / sidecar / build gotchas (learned, active)

- **dockview is the layout engine** (`src/components/PanelHost.tsx`): a module registers a `PanelSpec`
  whose `component` id maps to a React component; `PanelHost` mounts `DockviewReact` only after modules
  register (static-export SSR-safe). dockview 4 nests a `.dv-shell.dockview-theme-abyss` that re-declares
  `--dv-*` — the vysted theme must extend `.dockview-theme-vysted .dv-shell` or tabs render cold.
- **`dragDropEnabled: false`** in `tauri.conf.json` is REQUIRED for in-webview HTML5 drag (dockview tab
  reorder + node-editor palette). _(That file is LOCKED — don't change it.)_
- **`setConstraints` vs `setSize`**, rAF-throttle dockview resize calls; workspace-restore gates on the
  sidecar being up (see the `memory/` rig-and-engine-gotchas note).
- **Persisted UI state rides the workspace blob** (`src/lib/workspace.ts`), not localStorage — add a field
  → include in `serializeWorkspace` + `autosaveLayout`, restore in `deserializeWorkspace` (guard older
  blobs). The BriefPanel + new portfolio-publish state must persist correctly.
- **Spawn port-owning subprocesses via Tauri Rust `app.shell().sidecar(...)`**, never Python
  `subprocess.Popen`. PyInstaller `--onefile` silently drops `--copy-metadata` / `--collect-data` /
  `--add-data` — audit each new sidecar dep (a new India lib, the resolver masters, an Exa SDK). The
  smoke-test, not `cargo test`, catches the binary-runtime gap.
- **Version lives in many sources** (`package.json` + `Cargo.toml` + `tauri.conf.json` + `app.py` +
  `HOST_VERSION`) — **do not bump version in the spec window**; the build window bumps at its release tag.
- **Long commands (>~30s: pytest, sidecar builds) run in the background** with job tracking; never pipe a
  long command through `head`/`tee` in the foreground (deadlocks + masks exit code).
- **CORS-error-masks-500:** FastAPI doesn't add CORS headers to exception responses — a 500 surfaces as a
  "CORS policy" error; direct-`curl` the endpoint to distinguish.

## 7. Verification gates (before any release tag)

- **`pnpm ci-local`** mirrors CI byte-for-byte (install → ensure-all-sidecars → lint → format:check →
  typecheck → cargo fmt → clippy `-D warnings` → ruff → vitest → cargo test → pytest).
- **`node scripts/smoke-test-sidecars.mjs`** catches the binary-runtime gap (spawns each built sidecar,
  polls `/health`, checks MCP subprocesses survive).
- **`pnpm format:check`** before every push; before any Python commit: `ruff format <files> && ruff format
--check sidecar && ruff check sidecar`.
- Per-phase: the phase's **rig gate** (§3 table) + the **§6.5 audit 9/9** + the **Tier-1 LOCKED diff is
  empty**.

## 8. Open uncertainties to validate during the build (flagged, not blockers)

- **Keyless India sources are reliability-caveated** — NSE JSON endpoints are cookie/session-fragile;
  jugaad-data wraps the new NSE site but its ETF/fundamentals coverage is thin. The **correctness gate
  (FR-063) + fallback (FR-062)** are the mitigation. Smoke-test the India basket against ≥10 mid-caps +
  the ETF set before declaring B1 done.
- **EODHD/Exa/Perplexity require real keys to validate** (demo tokens don't cover NSE / are limited) —
  validate the BYOK paths with a real key in the build window, not against mocks alone.
- **Crypto OI/funding sub-panes (FR-092)** need a derivatives feed the sidecar may not have — degrade to
  price+volume+RSI if absent.
- **`compare` template needs a shared time-axis lock** across two dockview panels — evaluate the
  implementation cost (Zustand broadcast of `setVisibleRange` vs one chart with two panes) early in B2/B4.
- **Get-portfolio reconciliation:** the Pass A.2.0 report said `get_portfolio` reads sidecar SQLite; the
  live code (`agent_runtime.py:331`) reads the request-scoped context snapshot. Either way the agent can
  answer from a non-UI portfolio. The ratified fix (publish holdings → context bus) covers both; verify
  the actual current read path first.

---

**One-line build thesis:** consume the Pass-A foundation untouched; add Pass B as config + adapters +
new catalog capabilities + new panels/host-actions, phase by phase (B1→B6), each rig-verified and §6.5-
clean; never reskin, never touch a LOCKED file, never show wrong data, never dead-end.
