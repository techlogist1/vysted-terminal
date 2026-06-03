# Vysted Rebuild Spec — the AI-native finance OS

> Branch `003-vysted-rebuild`. This is the design + architecture spec the rebuild
> is built against, authored from a Phase-1 research run (14 agents, live web +
> current-code recon, 2026-06-03). It is a **decision document**, not a survey —
> every pillar states the pick, the rationale, the exact files, the failure modes
> it must make impossible, and acceptance. The engine is kept; the **experience**
> is rebuilt.

## 0. Thesis, scope, floor

**Thesis.** Vysted today is "a data viewer with a raw LLM chat bolted on" that
works on machine gates but feels vintage, jargon-heavy, and breaks on small
things (empty data, phantom proposals, enter-to-send, clipped menus). The engine
(sidecar, §6.5 safety, dockview, Kite read path, copilot tool-loop, the
IterResearch/Heavy deep-research harness) is strong and **stays**. We rebuild the
_surface_: agent UX, visual identity, research presentation, data depth, a native
screener, and an OS-for-finance workspace — so Vysted becomes the comfort
go-to app for a trader the way Obsidian is for notes and Cursor is for code.

**KEEP (do not rebuild).** The FastAPI sidecar + provider registry; the §6.5
safety layer byte-for-byte; dockview + the workspace-blob persistence model; Kite
read-only OAuth; the copilot tool loop + capability catalog; the IterResearch +
Heavy-mode harness _with its existing wall guards_; the deterministic typed-block
brief renderer; BYOK keychain flow; MCP-on-both-sides.

**FLOOR (sacred, every commit).** §6.5 audit 9/9. Tier-1 LOCKED files byte-for-
byte untouched: `types/plugin.ts`, `types/safety.ts`, `types/broker.ts`,
`sidecar/models/{safety,broker,audit_log,kill_switch}.py`,
`sidecar/services/broker_base.py`, `src-tauri/src/kill_switch.rs`,
`tests/test_safety_end_to_end.py`, CI workflows, `tauri.conf.json`. Orders never
auto-apply; every mutation routes the diff/accept gate; broker secrets stay
keychain-only, never logged/echoed. If a surface seems to need a LOCKED file →
route around and log it. Mac-first; design for Windows, don't break it. No merge
to main, no version bump.

---

## 1. Research model — swappable slot, non-thinking default (Pillar: models)

**Verified live OpenRouter catalog (2026-06-03, per-1M tokens in/out):**

| Slug                         | In/Out                                | Ctx  | Thinking?            | Note                                                 |
| ---------------------------- | ------------------------------------- | ---- | -------------------- | ---------------------------------------------------- |
| `minimax/minimax-m3`         | $0.30/$1.20 (promo; list $0.60/$2.40) | 1M   | **No**               | agentic/tool-use native, multimodal, BrowseComp 83.5 |
| `qwen/qwen3.6-flash`         | $0.1875/$1.125                        | 1M   | **No**               | rock-bottom cost floor                               |
| `moonshotai/kimi-k2.6`       | $0.684/$3.42                          | 262K | **No**               | native sub-agent swarm, best OPEN BrowseComp 86.3    |
| `deepseek/deepseek-v4-pro`   | $0.435/$0.87                          | 1M   | **Yes (high/xhigh)** | MIT, value power option — cap reasoning              |
| `deepseek/deepseek-v4-flash` | $0.098/$0.197                         | 1M   | **Yes**              | cheapest 1M ctx but **reasoning → hang risk**        |
| `qwen/qwen3.7-max`           | $1.25/$3.75                           | 1M   | mixed                | verified BFCL v4 #1 tool-caller (0.750)              |
| `qwen/qwen3.7-plus`          | $0.40/$1.60                           | 1M   | mixed                | cheaper agentic tool-caller                          |

**Decisions.**

- **Keyless/low-cost DEFAULT → `minimax/minimax-m3`.** HARD RULE: the keyless
  default MUST be a **non-thinking** model. The _current_ default
  `deepseek-v4-flash` is a reasoning model — it reproduces the exact 8-min-hang
  class that killed Tongyi. Swap it. Floor alternative: `qwen/qwen3.6-flash`.
- **POWER deep-research → `moonshotai/kimi-k2.6`** (native swarm maps onto Heavy
  mode; non-thinking; best open BrowseComp). Budget runner-up
  `deepseek/deepseek-v4-pro` **with a reasoning/effort cap**.
- **TOOL-CALLER → `qwen/qwen3.7-max`** (measured BFCL #1). The operator's "Qwen
  3.6 Plus 94%" is **fabricated/unverified** — do not bake it in.
- All three are **swappable from the live catalog** (the warm catalog already
  exists). Pin pricing to live `/api/v1/models`, never hardcode (MiniMax promo
  reverts). Prefer paid slugs over `:free` for the harness engine (free tiers
  rate-limit and stall multi-step runs); keep `:free` only as a labeled no-key
  fallback.

**Current code reality (model-deepresearch-wiring track).** Backend selection via
`config.get_deep_research_backend()` ContextVar threaded at
`agent_runtime.invoke_agent():660-665`; `deep_research.py` has
`_run_native/_run_tongyi/_run_perplexity`; `research/tongyi.py:resolve_model()`
probes OpenRouter (8s) and falls back to a non-thinking qwen. Wall guards exist:
`deep.py:_PER_ROUND_WALL_SECS=90`, `_LLM_CALL_TIMEOUT_SECS=60`, abort→synthesize.

**Build = swap + tighten, not rebuild.** (a) Change the keyless default model id
to `minimax/minimax-m3`. (b) Add a **three-tier wall envelope**: per-inner-LLM-
call timeout ~25-30s (below the 60s call cap) on plan/distill/reflect/extract, so
one slow "thinking" call can't eat a 90s round; on inner timeout → treat as empty
completion (loop already degrades). (c) **Non-thinking guard:** when a user swaps
in a reasoning model (deepseek-v4-\*, qwen3.6-max-preview), keep the BudgetGuard
step/wall ceiling tight so it can't hang. (d) Surface which coverage dimension was
thin on abort in `brief.note`.

**Failure modes prevented:** model hangs 8+ min (non-thinking default + 3-tier
guard); silent fallback (emit a downgrade step); cost blowout on Kimi swarm
(BudgetGuard meters it).

---

## 2. Deep-research protocol — verify pass, source ranking, confidence (Pillar: research-protocol)

The harness already matches Tongyi IterResearch (Markovian report reconstruction,
`_REPORT_CHAR_CAP=6000`) and Heavy mode (2-3 parallel angles + merge) — **keep
as-is**. Add the high-leverage gaps:

- **Chain-of-Verification (CoVe) pass before final synthesis** — the single
  biggest credibility win. After the distilled report: extract load-bearing
  factual claims (esp. every **number**), generate a verification question per
  claim, answer each **independently** by re-pulling the SAME structured tools
  _without showing the model its prior claim_ (isolation kills confirmation bias),
  then correct mismatches and **drop unverifiable numbers** rather than ship them.
  A distinct `ResearchStep('verify',…)`, **budget-gated** (skipped, not
  half-run, on breach → synthesize unverified with a note).
- **Source-quality ranking** in `_Findings.all_sources()` — a pure-Python
  heuristic: SEC/EDGAR, exchanges, company IR, Reuters/Bloomberg/FT/WSJ, and
  `vysted://` structured provenance rank above generic/SEO domains. Order `[n]`
  markers by score, cap the list. **Soft rank, never hard filter**; never drop
  `vysted://` sources.
- **Confidence reporting** on the brief — derived from coverage dims met / 4 +
  source-quality + verify pass-rate + clean-vs-abort. Surface as a small chip +
  one line ("Confidence: Medium — fundamentals thin, 2/6 claims unverified").
  Weight by source quality + verify rate (a naive 4/4-coverage = "high" misleads).
- **Analyst-template brief output**: thesis + stance → narrative → metrics/
  valuation **table** (screener-grade, verified numbers only) → catalysts with
  timing → risks → confidence + **sparing** rank-ordered citations. Never
  fabricate analyst fields (price target, DCF) the harness can't back —
  `deriveMetrics` discipline (null → no card).
- **NO multi-model council** (Heavy already buys the test-time-scaling gain at
  1/N cost for a one-key BYOK app). Optional off-by-default second-opinion
  verifier only.

---

## 3. Data depth — region-gated fundamentals, fix the dashes, autocomplete (Pillar: data)

**Root cause of the ROUTE all-dashes.** `yfinance_provider.get_fundamentals()`
has **no region gating**; `provider_registry` ranks NSE-native (jugaad) above
yfinance for quote/ohlcv but for **fundamentals there is no IN-ranked provider**,
so it falls straight to sparse yfinance for NSE. The `-88.58` is the
dividend-yield normalization (yfinance returns % vs the fraction contract;
`yfinance_provider.py:~153`). Dashes render by design when a field is `null`
(`EquityOverviewPanel.tsx:13-21`).

**Honest data constraint (decided).** There is **no globally-reachable keyless
India fundamentals source in 2026** — `nselib`/`NseIndiaApi`/`0xramm` geo-block
at nseindia.com from abroad; `jugaad-data` is EOD quote/OHLCV only. So:

1. **Keyless fix first (the foundational win):** (a) reproduce `-88.58`, fix the
   dividend-yield normalization with NaN/None guards; (b) **region-gate
   fundamentals** like quotes already are — add an India fundamentals path that
   uses yfinance `.NS` best-effort and badges provenance; (c) **expand the
   Fundamentals model** with screener-grade fields: `revenue_ttm`,
   `net_income_ttm`, `free_cash_flow`, `debt_to_equity`, `roe`, `roa`,
   `current_ratio`, `quick_ratio`, `shares_outstanding`, `dividend_per_share`,
   plus the Indian non-negotiables where available (promoter %, but flag if
   unavailable). Mirror in `types/data.ts` same commit.
2. **EODHD BYOK rung (screener-grade supplement, surfaced honestly):** a
   Yahoo-independent EODHD fundamentals provider, BYOK-gated, ranked between
   openbb-mcp and yfinance for region IN; an **"Add EODHD key"** empty state when
   India fundamentals are thin. Never silently dash.
3. **True autocomplete:** `/autocomplete?q=` endpoint backed by `symbol_resolver`
   - bundled masters (US + NSE/BSE), on-keystroke, <100ms for bundled, keeping the
     0.72 disambiguation. Wire it into the symbol search box and `@`-mention.
4. **Correctness gate** extended to flag all-null India fundamentals (not just
   symbol-mismatch/staleness). **Provider + freshness badges** on
   `EquityOverviewPanel` (`Quote.provider`/`Fundamentals.provider` +
   `Quote.freshness` are produced but not rendered). Replace bare `—` with a
   reason ("Not applicable — banking sector" / "Add EODHD key").

**Do NOT** bundle the geo-blocked NSE libs; do NOT depend on 0xramm.

**Locale-native (constitution VIII):** Rs. Crores default + IST timestamps + NSE/
BSE exchange badge on every price for IN; USD/US-hours for US. Region drives
resolution, currency, formatting, freshness.

---

## 4. Agent UX — clean composer, kill the bugs, spaces (Pillar: agent-ux)

The spine is already **two modes** (`agent`/`delegate`, `types/agent-modes.ts`) —
good. Rebuild the chrome and fix the 5 pinned bugs (`ChatSidebar.tsx`):

- **Composer = one compound input.** Full-width text area; **mode pill**
  (Quick / Deep / Manual mapping to existing agent/deep-research/edit) on the
  left; **model picker chip** on the right; attachment + slash trigger between.
  An **autonomy badge (ASK / AUTO)** as a colored pill _above_ the input (green =
  AUTO, amber = ASK) — never a checkbox buried in settings; never ambiguous.
  **Deep Research is a toggle button** in the composer (Perplexity pattern), not a
  jargon slash a normal user won't find.
- **Bug 1 — enter-to-send** (`:1239-1246`/`:1194-1215`): rework the keydown↔submit
  handshake so picker-accept is synchronous and, when no picker is open, Enter
  always submits exactly once (no double-send, no swallow).
- **Bug 2 — phantom permission bar** (`:370-386`): build the statusLine message
  from the autonomy state _at enqueue time_; **clear statusLine on autonomy
  toggle and on pending-change resolution** (add the effect hook that's missing).
  AUTO vs ASK must be correct and unambiguous; never claim "proposed in the
  permission bar" when nothing is pending.
- **Bug 3 — clipped slash/mention picker** (`:1220-1237`): viewport-aware
  positioning (flip up/down based on space) + `max-w` matched to the panel; open
  **upward**, max 6-8 items, fuzzy, grouped (Research / Data / Layout / Agent /
  Settings). Never clipped off-screen.
- **Bug 4 — header bloat** (`:776-836`): collapse the 5 stacked rows
  (ModeBar + RosterStrip + AgentHud + AutonomyToggle + BudgetConfig) into one
  compact bar + a settings popover; BudgetConfig only in Delegate.
- **Bug 5 — no clarifying question** (`mentions.ts:216-253`): wire
  `needs_disambiguation` into the agent context so the agent **asks** ("Route
  Mobile → the Indian CPaaS stock ROUTE.NS, or Route Mobile Inc?") instead of
  guessing or dead-ending.
- **Multiple agent pages/spaces** — support more than one chat thread/space.
- **Streaming UX**: 3-line skeleton shimmer on submit → 2px blinking cursor
  (~500-800ms) on first token → rAF-batched appends (bypass Framer Motion) →
  scroll-intent stop at >60px → prominent **Stop** → "response stopped" on stop.
- The §6.5 diff/accept gate (`proposed-changes.ts`, orders never auto-apply)
  **stays**.

---

## 5. Visual identity — zinc near-black + teal, Inter + Geist Mono, drop "TERMINAL" (Pillar: visual)

Re-value **two files in lockstep** (`styles/tokens.css` + `src/lib/chart-theme.ts`);
token **names stay historical** (`charcoal-*`, `amber-*`) per the 92-file
zero-churn rule — only hexes change.

- **Background ladder (zinc / Geist):** base `#09090b`, raised `#18181b`,
  elevated `#27272a`, overlay `#3f3f46`, inset `#0d0d0f`.
- **Text:** primary `#fafafa`, secondary `#a1a1aa`, muted `#71717a`,
  disabled `#3f3f46`.
- **Borders:** default `#27272a`, subtle `#18181b`, strong `#3f3f46`.
- **Accent (single, teal):** `#2dd4bf` / hover `#5eead4` / pressed `#0d9488` /
  subtle `rgba(45,212,191,0.12)`. Applied ONLY to active sash, focused inputs,
  streaming cursor, active agent node. Distinct from P&L green.
- **Finance signals:** positive `#22c55e` / bright `#4ade80` / muted `#166534`;
  negative `#ef4444` / bright `#f87171` / muted `#7f1d1d`; warning `#f59e0b`
  (stale/paper). Update `chart-theme.ts`: `CHART_SURFACE→#18181b`,
  `CHART_TEXT→#a1a1aa`, `ACCENT_CORAL→#2dd4bf` (+ `ACCENT_CORAL_RGB`).
- **Type:** Inter Variable (UI) + Geist Mono (numbers), both OFL, `next/font`.
  `tnum`+`ss01` (slashed zero) on numerics. Dense scale: 13px body, 12px labels,
  12px mono-data, headings 14/18/24 with negative tracking.
- **Motion tokens:** durations 100/160/240ms; ease-out `cubic-bezier(0,0,0.2,1)`,
  ease-in-out `cubic-bezier(0.4,0,0.2,1)`; **node-glow**
  `0 0 0 1px var(--accent), 0 0 12px 2px rgba(45,212,191,0.18)`; streaming cursor;
  all pulse/glow wrapped in `@media (prefers-reduced-motion: no-preference)`.
- **Wordmark:** drop "TERMINAL" everywhere in chrome → **"Vysted"** (Inter 600,
  tracking -0.02em). Update `page.tsx:185-189`, `OnboardingFlow` title,
  `layout.tsx` `<title>`. Verify WCAG AA on muted-on-elevated; verify zinc doesn't
  read sterile at 1920×1080 before committing.

---

## 6. Research brief deepening (Pillar: brief)

Renderer already does typed blocks + GFM table parse + clickable `$CASHTAG` chips
→ chart (`brief-blocks.tsx`). Add:

- **Real screener-grade tables**: add a `screener` leg to the FAST fan-out
  (`fast.py`) + extend `BriefStructured` (`types/brief.ts`) with `analyst`,
  `earnings`, `screener` legs → native `TableBlock`s (the sidecar already has
  `analyst_tools`/`earnings_tools`), instead of pipe-prose the parser must recover.
- **Ask-follow-up-on-a-brief**: ride `brief.query`+`structured` in the
  `__terminal__` snapshot so "what's the 5y FCF trend?" pre-fills the prior symbol.
- **Storyline/narrative**: a `chapters` field (plan / catalyst / valuation / risk),
  mapping IterResearch per-round findings 1:1 → an accordion brief.
- **Ticker menu**: chip → menu (Open chart / Equity overview / Add to watchlist /
  Research this) using existing host-actions, not chart-only.
- **Fixes:** bare-uppercase chip recall (seed known-set from the resolved bundle /
  S&P500 whitelist; guard 2-char words like "IT"/"AI"); the 120s structured
  carry-over **cross-symbol contamination** (key by symbol, not recency window).

---

## 7. Native screener — drill-down, formula grammar, presets (Pillar: screener)

Screener is a functional **island** (AND-only, 13 numeric fields, no drill-down).
Build to screener.in grade:

- **Cockpit drill-down (highest-value gap):** row `onClick` → `panel-context` bus
  (`source='screener'`) → chart + equity-overview switch symbol. <200ms perceived.
- **Expose filtered-but-hidden fields** in result rows (forward_pe, peg, p/b, div
  yield, eps, beta, 52w) + the new screener-grade fields from Pillar 3.
- **OR / group logic + formula evaluator** (`CriterionGroup` with AND|OR; arithmetic
  custom ratios) — screener.in English-phrase grammar (ROCE, ROE, OPM, promoter
  holding, FII/DII, "Sales growth 5Years", "Down from 52w high"…), autocomplete
  field picker.
- **Pre-ship the 8 popular screens** (quality compounder, magic formula, 52w
  breakout+volume, turnaround, undervalued-vs-industry-PE, high-div-low-debt, FII
  accumulation, Graham net-net) as clonable presets; save/load custom presets.
- **Grow sp500 → full 500** (tiered "expand to full" run). Pagination/virtual
  scroll > 100 rows. **CSV export.** Timestamp results ("based on Mar 2026 filing").

---

## 8. Workspace / OS-for-finance (Pillar: workspace)

Named workspaces already exist (save/load/delete via cmd+K). Add:

- **Per-stock research spaces**: optional `ticker` on `SerializedWorkspace` +
  "New Research Space for [TICKER]" (applies research-cockpit + loads ticker;
  saved `research-[TICKER]`); group/badge in the dialog.
- **Notes panel module**: free-text scratchpad persisted in the workspace blob
  (`notes` key; per-stock `Record<symbol,string>`).
- **Export-to-Excel/CSV**: screener, portfolio, watchlist (follow the audit-log
  CSV pattern). A universal "Export table as CSV" affordance.
- **macOS native menu bar** (`tauri-plugin-menu` in `Cargo.toml` + `lib.rs`
  `setup()` + capability): **Window → Fundamental Analysis / Technical Analysis /
  Macro Scan / Compare / Reset Layout** wired to existing layout templates;
  Workspaces → Save/Load. **Mac-first**, guard with `cfg!(target_os="macos")`;
  Windows gets a custom title-bar menu later. IPC event channel must not
  double-apply with the cmd+K path. `tauri.conf.json` is LOCKED — build the menu
  in Rust `setup()`, don't edit the locked config; capability lives in
  `capabilities/default.json` (not locked).
- **Active-workspace status affordance** (VS Code branch-picker style).

---

## 9. Build sequence & failure-mode master table

**Sequence** (lead-authored, coherent commits; agents used for read-only
diagnosis, isolated artifact generation, and review — never teammate writes into
the lead tree, per the contamination rule):

1. **Visual tokens + type + motion + wordmark** (mechanical, unblocks every
   surface looking right; fast).
2. **Data depth** (foundational — research/screener are worthless on thin data):
   reproduce + fix `-88.58`, region-gate + expand fundamentals, autocomplete,
   badges, EODHD BYOK rung.
3. **Research model swap + 3-tier guard** (small; default → minimax-m3).
4. **Agent UX** (composer + 5 bug fixes + spaces + streaming).
5. **Brief deepening** (tables, follow-up, storyline, ticker menu) — needs 2.
6. **Screener** (drill-down, grammar, presets, export) — needs 2.
7. **Research-protocol** (CoVe verify, source ranking, confidence) — layered on 3/5.
8. **Workspace/OS** (research spaces, notes, export, menu bar) — most Rust-risk.
9. **Verify** (rig live+populated 1920/2560, `pnpm ci-local`, smoke-test, §6.5 9/9).

**Failure mode → prevention:**

| Surface        | Failure mode                             | Prevention baked in                                                             |
| -------------- | ---------------------------------------- | ------------------------------------------------------------------------------- |
| Composer       | Enter doesn't send / double-sends        | synchronous picker-accept + single-fire submit; E2E test                        |
| Permission bar | phantom "proposed…" when nothing pending | message built at enqueue; cleared on autonomy toggle + resolution               |
| Slash/mention  | clipped off-screen                       | viewport-aware flip + max-w; opens upward; ≤8 items                             |
| Symbol         | wrong-stock / dead-end on ambiguity      | `needs_disambiguation` → agent asks a clarifying question                       |
| Stock page     | all dashes / `-88.58`                    | region-gated fundamentals, normalization fix, reason-not-dash, provenance badge |
| Search         | no autocomplete                          | `/autocomplete` on-keystroke, bundled masters + live fallback                   |
| Research       | model hangs 8+ min                       | non-thinking default + 3-tier wall envelope + BudgetGuard                       |
| Research       | wrong numbers shipped                    | CoVe verify pass (independent re-pull), drop unverifiable                       |
| Brief          | cross-symbol metric contamination        | key structured carry-over by symbol, not 120s recency                           |
| Screener       | island, can't act on results             | row-click → panel-context bus → cockpit                                         |
| Data           | synthetic/stale shown as live            | provenance + freshness badges; correctness gate; labels                         |

**Open questions for the operator (batched; Tier-4 / taste only — everything else
decided autonomously):**

1. Wordmark: **"Vysted"** title-case (picked) vs lowercase "vysted" (softer,
   Arc/Perplexity energy). I shipped title-case; trivially swappable.
2. India screener-grade fundamentals depend on **EODHD BYOK (paid ~€60/mo)** —
   confirm that's an acceptable "honest supplement" surface (keyless gets
   yfinance best-effort + the bug-fix; EODHD unlocks the rest). Surfaced as an
   opt-in "Add key", never a forced paywall.
3. Accent **teal `#2dd4bf`** (picked) vs indigo `#818cf8`. Shipped teal.

These do not block any track; I build all of them on the picked defaults.
