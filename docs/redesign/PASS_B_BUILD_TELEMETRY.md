# Pass B — build telemetry (cumulative)

Running tally of the Pass-B build window (branch `001-agent-native-redesign`).
One section per phase; the lead (Opus 4.8, 1M) appends as each phase closes.

## Running totals

| Metric                | Value (through B6 — PASS B COMPLETE)                                            |
| --------------------- | ------------------------------------------------------------------------------- |
| Phases complete       | **6 / 6** (B1, B2, B3, B4, B5, B6) — no key gates (operator: no spend)           |
| Sub-agents dispatched | 4 (B1) + 3 recon + 5 (B2) + 5 (B3) + 4 (B4) + 4 (B5/B6) = **25**                 |
| New tests             | ~270 across B1–B6                                                                |
| Test suite            | sidecar **1236** · vitest **845** · §6.5 **9/9**                                 |
| New dependency        | `jugaad-data==0.33.1` (keyless NSE) — no new dep in B5/B6                        |
| Sidecar binary        | rebuilt B1–B6 (new `/resolve` router folded in; no new PyInstaller flags)        |
| Commits               | 9fcb146·5e9ea9a (B1) · bb29fd6 (B2) · 4c94888 (B3) · df1b6e4 (B4) · 4c4af93 (B5) · fe23f15 (B6) |

## Rig verification sweep (closeout — `docs/screenshots/passB-b5b6/`)

Live sweep on the rig (`tauri dev --features dev-tools`) driving the **freshly rebuilt
`--onefile` binary** through the tauri-mcp bridge (`__vystedStores` / `__vystedDockview`). All
shots **populated + dark**. The M1 display can't host a 16:9 point-window large enough, so each
shot is captured at the Retina-2× native **2560×1664** with an aspect-preserved **1920×1248**
downscale (`<name>@1920.png`) — both mandated resolutions, no distortion.

| Shot                              | SC(s)            | What it proves (live)                                                            |
| --------------------------------- | ---------------- | ------------------------------------------------------------------------------- |
| `b5-slash-picker`                 | SC-023           | `/` opens the curated picker with all **11** commands ranked                     |
| `b5-mention-apple-US`             | SC-023           | `@apple` → `@AAPL · US · Apple Inc.` first (prominence-ranked), live `/resolve`  |
| `b5-mention-reliance-IN`          | SC-017/023       | IN region: `@reli` → `@RELIANCE · NSE` first, all-NSE candidates (locale-aware)  |
| `b6-research-cockpit-NVDA`        | SC-016/019       | NVDA chart + MA/RSI/MACD/Volume + `NVDA via yfinance` provenance                 |
| `b6-honest-brief-NVDA`            | SC-020           | the honest **"structured-data-only — no web backend configured"** brief banner   |
| `b6-india-RELIANCE-IN`            | SC-017/019 + CF2 | RELIANCE (NSE) chart + **news re-fetched to India coverage on the region switch**|
| `b6-portfolio-p1-populated`       | SC-024           | portfolio (RELIANCE+NIFTYBEES) **₹** market-value + P&L + concentration          |
| `b6-flagship-cockpit-US-NVDA`     | SC-016/025       | the flagship cockpit, hero/hand-off state                                        |
| `b5b6-baseline-restored-cockpit`  | SC-016/020       | workspace-blob restore: cockpit + honest brief survive a relaunch                |

**Live behaviors confirmed on the rig:** the binary-level `/resolve` serves locale-first
(RELIANCE→NSE/IN, Apple→AAPL/US); every curated slash action + cockpit mutation rode the
**proposed-changes gate** and AUTO auto-applied (orders excluded by construction); the live
DeepSeek copilot reached `set_chart_symbol` + `get_portfolio` through the gate (proving the
agent→gate→AUTO path end-to-end). The default DeepSeek model's chatty wandering (the documented
qwen/DeepSeek tool-use inconsistency) is why the coherent cockpit was composed via the host-action
gate directly (identical path) rather than relying on a single free-form LLM turn — the
agent-authored full cockpit is the B2/B4 flagship already on record.

## Phase B6 — get_portfolio context-bus parity + carry-forwards + polish (Pillar B · US16/US17)

**Orchestration:** B5 + B6 ran as ONE continuous dynamic workflow (`pass-b5b6-build`, 4
file-isolated units; first run aborted on an internet disconnect — re-launched via
`scriptPath`, all units green). Lead owned: the `ChatSidebar` composer integration (B5), the
brief-docking layout template (B6), the resolve-router registration, `get_portfolio` parity
verification, and every diff review.

**Built (FR-110/111, SC-024):** `get_portfolio` zero-divergence — `PortfolioPanel` publishes the
ACTIVE portfolio's full holdings (symbol / quantity / costBasis / assetClass + resolved
marketValue / pnl per row, `null` where no live quote) onto the panel-context bus;
`captureTerminalState` extracts them into `TerminalState.portfolio`; `agent_runtime.get_portfolio`
returns that same captured snapshot — the tool and the panel read ONE source, so they cannot
diverge (verified source-level + chained read).

**Four Pass-B carry-forwards cleared:**

- **Brief docking** — `research-cockpit` template docks the cited `BriefPanel` BESIDE the chart
  (right column, focused), never a chart-group tab.
- **News region re-fetch** — `NewsFeedPanel` re-fetches on a region switch (`region` added to the
  fetch-effect deps).
- **Native citation emission** — left code-complete-but-unvalidated by operator decision (no key
  spend); noted, not regressed.
- **Compare axis-lock** — stays deferred (not cheap) per the brief.

**Polish:** `DataBadges` (provenance + staleness) on the new surfaces; locale currency +
empty/loading/error states on the brief; `SettingsPanel` region/provider polish.

**Gates:** sidecar 1236; vitest 845; §6.5 9/9; Tier-1 LOCKED empty; order-grep clean;
typecheck/lint/format/ruff clean. Rig sweep evidence in `docs/screenshots/passB-b5b6/`.

## Phase B5 — Curated `/`-commands + `@`-mentions composer (Pillar D · US15)

**Orchestration:** the front half of the `pass-b5b6-build` workflow — units for the slash
registry, the mention surface + `/resolve` route, the two pickers, and the portfolio/context
parity. Lead integrated the composer (`ChatSidebar`): picker open/active/resolve state, keyboard
nav, token splicing, the curated-dispatch precedence, and the mention-prefix routing.

**Built (FR-100/101, SC-023):**

- **11 curated slash commands** (`slash-commands.ts`): prompt-kind (`/research` `/deep` `/compare`
  `/screener` compose a templated agent prompt) + action-kind (`/chart` `/watch` `/portfolio`
  `/layout` `/export` `/sources` `/clear`) routed through the SAME diff/accept gate the agent uses
  — AUTO auto-applies the UI/layout/chart/watchlist action, ASK queues it. `matchSlash` (fuzzy,
  prefix-wins) + `parseSlashInvocation` precede the legacy `/ask|/agent|/provider|/key` parser; a
  composed template that itself starts with `/` is routed as raw agent text, not re-parsed.
- **9 `@`-mentions** (`mentions.ts`): surfaces (`@chart/@news/@filings/@terminal`), scopes
  (`@watchlist/@portfolio`), agents (`@analyst/@quant` — `applyMentionPrefixes` rewrites the turn
  via a prompt prefix without switching the active agent), and DYNAMIC instruments (`@TICKER`)
  resolved live + locale-aware against the read-only `/resolve` route (GET, `symbol_resolver` on a
  worker thread; degrades to static on miss).
- **Pickers** (`SlashCommandPicker` / `MentionPicker`): presentational listboxes; `ChatSidebar`
  owns ↑/↓/↵/⇥/Esc nav, a seq-guarded async mention resolve, and `/cmd @entity` composition (the
  matchers key off different parse states). Highlight + stale-mention guard are DERIVED, not
  effect-driven (no cascading setState — `react-hooks/set-state-in-effect` clean).

**Gates:** vitest 845 (incl. slash 28, mention 21, resolve router 9); §6.5 9/9; Tier-1 LOCKED
empty; order-grep clean; typecheck/lint/format/ruff clean.

## Phase B4 — Research engine: fast + deep + B+A output (Pillar B · US12/US13)

**Plan change (operator):** no Exa/Perplexity key, no spend, no key stops. B3 closed unkeyed
(Exa shows "needs a key"; the honest no-web fallback is the real default path). B4 native deep
loop is the working default; Perplexity Sonar is present-but-unconfigured (opt-in, never
auto-selects, "needs a key" if chosen).

**Orchestration:** 4-agent dynamic workflow (`pass-b4-build`, 290,318 output tokens) — BriefPanel

- brief store, the research service (FAST structured bundle + DEEP BudgetGuard loop with parallel
  researchers + abort→synthesize), the Perplexity backend, the research/deep_research handlers + a
  one-shot LLM helper. Lead owned: catalog (research / deep_research / publish_brief), the
  publish_brief host-action (mode-normalized FAST|DEEP), the LLM-creds contextvar + invoke_agent
  publish, copilot tools + the research-flow prompt (explicit "honest no-web → structured data only,
  never fabricate"), registry wiring.

**Built (FR-070–075, SC-016/018/019/021):** FAST = prompt-driven (research bundle → cockpit +
indicators + publish_brief), provenance-tagged; DEEP = budget-bounded loop (rounds 3/max5, wall
120s/max300s, coverage floor, **abort→synthesize, never a bare timeout**); BriefPanel (markdown +
inline [n] citations + sources tray + metadata + dev step-log + the **prominent honest
"structured-data-only" banner** when web is unavailable).

**Verified (source-level, no keys):** `research(NVDA)` returns real structured data with provenance
(yfinance price/fundamentals, rss news) and `web.available=false` + the honest note — never
fabricated. Gates: sidecar 1227; vitest 794; §6.5 9/9; Tier-1 LOCKED empty; order-grep clean;
format/lint clean. Live rig demo follows.

## Phase B3 — Web search, three tiers (Pillar C · US14) — CODE DONE, paused at Exa key

**Orchestration:** 5-agent dynamic workflow (`pass-b3-build`, 367,351 output tokens) over
file-isolated units — search-core interface+registry+normalizer, Exa BYOK backend, SearXNG
local backend, native-search injection across all 4 LLM adapters + citation normalizer,
frontend tier/key wiring. Lead owned: catalog `web_search` + `research` domain, the
`web_search` handler, agent-runtime native dispatch + per-run search cap, the Exa/SearXNG/tier
per-request contextvars + middleware, the registry↔searxng class-name/region fix.

**Built (FR-080–084, SC-020):** three-tier search — (1) **native** on the user's key for
Anthropic/OpenAI/Gemini/Groq/xAI (adapter injection + max_uses cap, tool withheld so search
isn't double-run); (2) **BYOK Exa** (locale domain allow-lists US/IN); (3) **local SearXNG**
(autodetect + BYO URL, nothing leaves the machine). Honest fallback (FR-082) when nothing is
configured — never fabricates a source. Per-run search cap (FR-081). Citations normalized to
{url,title,excerpt}. Secrets ride per-request headers → contextvars, process-memory-only.

**Gates green:** full sidecar 1185 + 5; §6.5 9/9; vitest/typecheck/lint/format clean; Tier-1
LOCKED empty; order-grep clean. All BYOK/native HTTP **mocked** in tests.

**PAUSED → operator stop #2:** the Exa BYOK path must be validated against the **real Exa key**
(demo tokens don't cover it; never mocked for the gate). Native-search live validation
additionally needs a native-capable LLM key. See report.

## Phase B2 — JARVIS capability completeness + 2 seamlessness fixes (Pillar D · US15)

**Orchestration:** 3 parallel recon agents (B2 cockpit + B2 indicators + B3 search surface)
then a **5-agent dynamic workflow** (`pass-b2-build`, 252,547 output tokens) over file-isolated
units — compare_symbols handler, indicator-presets, layout-templates, chart-command channel,
completeness audit. Lead owned catalog + host-actions + registry integration and reviewed
every diff. **Did NOT run a parallelizable phase lead-only** (per operator correction).

**Built (FR-090–094, SC-016/022/025):** `compare_symbols` (read), `set_chart_indicators`
(host_action) + per-asset-class presets, `arrange_layout` named templates (single-focus /
research-cockpit / compare / macro-scan), chart-command indicator+comparison channel,
`indicators` domain, SC-022 completeness audit.

**Two operator-reported seamlessness fixes folded in (lead):**

- AUTO chart-open silently failed → `set_chart_symbol`/`set_chart_indicators` ensureChartOpen()
  (by component); copilot narration de-coupled from "confirm in the proposal bar".
- Default provider not persisting → added the missing `useLLMProvidersStore` autosave
  subscription in page.tsx.

**Rig-verified live:** AUTO + set_chart_symbol on an empty cockpit → chart opens + loads
(Bug 1 fixed, reproduced-then-fixed); `research-cockpit` on NVDA → multi-panel cockpit +
MA(50/200)+RSI+MACD+Volume preset (SC-016, screenshot `b2-research-cockpit-NVDA.png`); Bug 2
restore live-verified (DeepSeek default persisted across reload). §6.5 9/9, Tier-1 LOCKED empty.

## Phase B1 — Locale-native data foundation (Pillar A · US11)

**Wall-clock:** single build session, 2026-06-01.

**Sub-agents dispatched (4):**

| Agent                                     | Role                                                           | Reported output tokens |
| ----------------------------------------- | -------------------------------------------------------------- | ---------------------- |
| Explore — frontend region-flow map        | recon (read-only)                                              | n/r                    |
| Explore — rig launch procedure map        | recon (read-only)                                              | n/r                    |
| Build — frontend region wiring            | sidecar-client header + format currency + context + dev-stores | 50,821                 |
| Build — news/screener/macro region-keying | region-keyed feeds + macro/screener defaults                   | 95,481                 |

Lead authored the correctness-critical spine directly (config region, `locale.py`,
`correctness_gate.py`, `india_provider.py`, `symbol_resolver.py`, `provider_registry`
region routing, `resolve_symbol` catalog capability, the ASGI region middleware).

**Files changed (B1):** see `git diff --stat` — 20 modified (+561/−63) + new:
`sidecar/services/{locale,correctness_gate,india_provider,symbol_resolver}.py`,
`sidecar/services/agent_tools/resolve_symbol.py`,
`sidecar/services/resolver_masters/{__init__.py,us_instruments.json,nse_instruments.json}`,
and 7 new test files.

**Tests added:** 44 (locale 9, symbol_resolver 8, correctness_gate 9, india_provider 8,
provider_registry_region 7, region_middleware 4, resolve_symbol_tool 4) — `_quote` fake in
the existing `test_provider_registry` updated to satisfy the new correctness gate.

**Gate results:**

- `pytest` full sidecar suite — **1095 passed**, 0 failed.
- §6.5 `test_safety_end_to_end.py` — **9/9**.
- `pnpm typecheck` 0 · `pnpm lint` clean · `pnpm test` (vitest) **745 passed**.
- `prettier --check .` clean · `ruff format --check` clean · `ruff check` clean.
- `node scripts/smoke-test-sidecars.mjs` — all sidecars booted cleanly.
- Built-binary HTTP verification — India basket via `provider=nse`/INR, US via
  `yfinance`/USD, GOLDBEES routed to NSE with no region header (master hint).
- Tier-1 LOCKED diff — **empty** (byte-for-byte). Order-execution grep — **clean**.
- Rust (cargo fmt/clippy/test) — not re-run; **no Rust files changed** this phase.

**Flagged-uncertainty validations (B1):**

- Keyless India reliability — **resolved**: jugaad-data `stock_df` EOD serves 14/15 basket
  symbols cleanly (GOLDBEES's lone first-call `FileExistsError` is a cache-dir race, fixed
  with `makedirs(exist_ok=True)` + retry); live NSE quote endpoints (NSELive/nsepython) are
  blocked from this host → quotes derived from EOD bars (T+1, as ratified). Correctness gate
  - preference-ordered fallthrough proven to fire (unit + live).
- EODHD/Exa/Perplexity real keys — **not needed for B1** (keyless path only).
