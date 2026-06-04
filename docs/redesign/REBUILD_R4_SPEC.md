# Vysted Terminal — R4 Rebuild Spec (the experience layer)

> **Status:** SPEC — authored in a dedicated spec/architecture window. **No feature code was written
> here.** A separate fresh build window executes this spec start-to-finish.
> **What this is:** the **executable master spec for the ground-up rebuild of the experience layer**.
> It is an _execution_ spec that sits **on top of** the operator-ratified product spec
> `specs/001-agent-native-redesign/spec.md` (US1–US17, FR-001–111, SC-001–025) and the Constitution
> v1.1.0 — it does **not** reopen them; it **extends** them with the experience-layer requirements
> (US18–US25, FR-112–130, SC-026–039) and the build plan the brief commissioned.
> **Version stays `0.8.0`. Branch only (`003-vysted-rebuild` or a fresh `004` off it). No merge to
> main. No version bump.**

**Supporting docs (this spec is the spine; these are the limbs — the build reads all five):**

- `R4_DESIGN_LANGUAGE.md` — the original "Cold Instrument" visual system (§3 here references it).
- `R4_STALE_CODE_REGISTER.md` — every old-vs-new collision + orphan + drift to remove (§7).
- `R4_FAILURE_MODE_MATRIX.md` — the per-surface state contract (§2/§5).
- `R4_BUILD_SEQUENCE.md` — the priority spine + dependency ledger + verification contract (§8/§9).

---

## 0. Grounding (the honest baseline this spec builds on)

A 20-agent recon (7 codebase digesters with file:line anchors, 4 redesign-doc digesters, 9 live-
research agents) established the ground truth. The load-bearing facts:

- **The agent-OS spine is already substantially wired** on `003-vysted-rebuild`: 9 host actions
  (`open/close/focus_panel`, `arrange_layout`, `set_chart_symbol/indicators`, `add_to_watchlist`,
  `publish_brief`, `propose_order`), the §6.5 **propose-then-accept gate** (`proposed-changes.ts` →
  `applyHostAction`/`routeOrderProposal`; orders never auto-apply, three enforced layers), the live
  `__terminal__` situational snapshot (focused symbol/panels/viewport, deixis resolution for "this"),
  the four-mode spine, and the BudgetGuard. R4 **hardens and completes** this — it does not build it
  from zero.
- **Research is sprawled:** 5 paths (FAST / deep-single / deep-iter / heavy / Perplexity) behind 2
  tools + 3 chat triggers (`/research`, `/deep`, `/deep heavy`). The brief's #1 coherence ask.
- **The screener is slow + lossy by construction:** per-symbol `yf.Ticker().info` scrape, 12-wide,
  30s timeout → ~176s and **242/506 silently skipped** (Yahoo rate-limit casualties). The recursive
  AND/OR `CriterionGroup` grammar is fully wired server-side but the UI emits only a flat OR.
- **The "orphan" features are not in the codebase:** ⌘K is real-but-flat; Notes is a bare
  `<textarea>`; the screener "formula grammar" does not exist. `cmdk`/`@tiptap/*`/`mathjs` are
  **uninstalled**. R3's drafts live only in a transcript — **rebuild fresh, do not salvage.**
- **The design is generic-by-construction:** unmodified shadcn-zinc + `indigo-400`, no type/spacing/
  density system, stale warm-clay fallbacks. Market-session awareness is **0% covered**.
- **Models verified live (2026-06-05):** `deepseek/deepseek-v4-flash` serves and is **non-thinking by
  default** (R3's hang fear overstated) — it is the _current_ keyless default (not minimax). Tongyi
  has **zero providers** (correctly deleted). The keyless-first guarantee holds.

R4's job, in the brief's words: make the agent the app's operating system, make the app cohere, give
it an original face, build the named features properly, fix the perf + bugs, and remove the stale —
**all verified by rendered pixels, nothing claimed without a screenshot.**

---

## 1. PILLAR #1 — The agent is the app's operating system (ranked above everything)

The agent drives every surface and reaches the internet, at **three coherent speeds**, always routed
through the §6.5 proposal/accept bar so it is **magical AND safe** (never blasts everything open,
never silently guesses wrong). This synthesizes the 2026 app-driving-agent patterns (orchestrator-
workers; **state-in-the-loop**; "the agent proposes, the system disposes"; Intent Preview; three-speed
by reversibility×stakes) onto Vysted's existing gate + snapshot + BudgetGuard.

**(a) FAST — instant, LLM-free.** A bare `@TICKER` or a quick command opens the **default cockpit set
instantly**, with no model round-trip. _Gap to build:_ today `@TICKER` only inserts a composer token;
wire the instant path on the existing `loadSymbolIntoChart` + `arrange_layout` primitives. Idempotent
UI/read ops the agent just _does_.

**(b) ORCHESTRATED — propose, and ask when genuinely unsure.** "Open Route Mobile" → the agent
**proposes** the panel set as a scannable Intent Preview ("Equity Overview + Brief + Chart for
ROUTE.NS — also peers + news?") and **asks a clarifying question when confidence is genuinely low**,
then drives the panels — **through the existing §6.5 proposed-changes bar** (diff + reason + accept/
reject; AUTO mode auto-applies UI/layout/chart/watchlist only, never an order). _Two gaps to build:_
the bare-ticker still routes to FAST, and `planner.decompose` **never asks today** (it always degrades
to one step) — add a bounded clarify affordance.

**(c) DEEP — one coherent research path.** The single collapsed research model (§2.1).

**Situational awareness (the spine's nervous system).** The agent **always knows the live cockpit
state** (open panels, focused ticker, viewport) via the `__terminal__` snapshot injected every turn,
so "tell me more about **this**" resolves the focused symbol. R4: unify the two duplicate capture
sites; **after any app-mutating host action, force a state re-read** (the computer-use "evaluate the
outcome" rule) so the agent never acts on assumed success.

**Host-action completeness.** The agent can open/close/arrange panels, set symbols/indicators/
timeframes, manage the watchlist, publish briefs, and propose orders today. R4 **adds** the missing
verbs the brief requires: **write/configure screener filters** (today the agent can _run_ a screen but
cannot write filters into the panel), **drawings/annotations**, **save workspace**, **remove from
watchlist**, and makes `set_chart_indicators`/`close_panel`/`focus_panel` plan-stageable. Every new
mutating capability is registered in `catalog.py` (Principle II) and rides the §6.5 gate (never
auto-applies; orders never qualify for FAST).

→ **FR-112, FR-113, FR-114. SC-026, SC-027.**

---

## 2. Coherence audit — "careful engineering" with teeth

### 2.1 Collapse the research modes into ONE seamless model

Remove the 3 chat triggers and the 5-path user-visibility. There is **one** research entry; `mode`/
`angles`/`backend`/`single` become **internal escalation**, not user knobs. "Go deeper" escalates the
_same_ run in place. Unify the two parallel deep loops (`deep.py` single-pass + `iter.py`) into one
defined path (keep single-pass only as the _named_ fallback, register `S-9`). Perplexity Sonar becomes
an **explicit, cost-shown, opt-in-per-run** DEEP backend (FR-073) or the dead surface is removed
(`S-10`) — no half-wired orphan.

### 2.2 One interaction language

- **Model-swap mid-conversation preserves context** on **every** path. The agent path already reads
  the model per-message and keeps history; the **raw-chat path drops history** (`ChatSidebar.tsx:742`
  sends a single-turn message) — fix it so a swap never loses the conversation.
- **Enter sends, every time.** The composer's explicit `onKeyDown` Enter handler is correct today;
  R4 verifies it across **every** composer/input that sends, and that a picker-open state never
  swallows a send.
- **One mode system.** The four-mode `agent-mode.ts` picker and the `planner.classify_intent`
  inference both exist; one is vestigial (`S-15`). Decide the single source and remove the dead one.
- **Find everything hardcoded that should be dynamic and fix or guard it** (register `F`): the 4
  copies of the default model, the doubled base URLs, the `_resolve_model` literal, the equity-
  hardcoded brief metrics. Fix the contract drift (brief `BriefMode` casing `S-6`, `BriefStepKind`
  `S-7`) so a real brief renders its real mode badge.

### 2.3 Every interactive element has a complete state set

Every interactive element and data surface specifies **and visibly renders** `default/hover/active/
focus-visible/disabled/loading` + `empty/loading/error/market-closed/symbol-not-found/stale`
(`R4_FAILURE_MODE_MATRIX.md`). Enforced **once** via shared primitives (design §9), not hand-rolled
20×. No silent `—`, no raw JSON, no silent skip.

→ **FR-115, FR-116, FR-117, FR-119. SC-028, SC-029, SC-030.**

---

## 3. UI overhaul — a total, original design language

The complete system is `R4_DESIGN_LANGUAGE.md` ("Cold Instrument"). The decision, in brief: the
genericness is **missing craft, not the hue** — so R4 **keeps** the R3-ratified cool-indigo accent +
mark-only brand (no thrash) and builds the system that was never built. Synthesized from the
_principles_ of Linear (perceptual rigor, density-as-craft), Apple HIG (deference, contrast floors),
Perplexity (accent budget), Claude's _typographic_ hierarchy — an **original** system, explicitly
rejecting Claude's warm/cream/serif execution (the forbidden clone), neon/glow, and SaaS gradients.

Concretely: re-derive the **zinc ramp + accent in OKLCH** (perceptually even; a deliberate "cold
instrument" character, ~12–15% desaturated accent) re-valued into the **historical token names**
(zero-churn across ~92 files; single-sourced across the 3 canvas places in lockstep); a real **type
scale** (~1.20, none today), **spacing scale** (4/8, none today), **unified motion tokens** (one
vocabulary, 120/180/240ms ease-out asymmetric, feedback-only), **elevation by luminance step** (remove
the neon glow primitives), the **accent rationed to ≤5% of pixels** (active/focus/primary/live only).
Every micro-element is specified to feel intentional (design §6 component-state contract, §7
accessibility floors). Purge the warm-clay fallbacks (`S-1`) and rewrite the stale `DESIGN_SYSTEM.md`
(`S-2`).

→ **FR-128. SC-037.** Uses the `frontend-design` skill (steered to minimalism) + `ui-ux-pro-max` (for
rigor only), per the brief.

---

## 4. Features to build (full scope, no half-ships)

The first three were R3 **orphan drafts** (transcript-only, deps uninstalled) — **build properly, not
salvaged** (register `S-21`).

### 4.1 ⌘K Raycast-grade palette → **FR-120, SC-031**

`pnpm add cmdk` (it powers Linear/Vercel/shadcn; absent from `package.json` today). Grouped + scoped,
in this fixed order with cross-group score offsets in the custom `filter`: **Ask AI (forceMount, top)
→ Agents → Actions → Panels → Symbols**. Symbols are **query-gated, capped, virtualized** and ranked
**below** agents (flip the current backwards weighting where symbols `0.8` outrank agents `0.7`).
Recency/frequency boost. `Backspace`-on-empty pops a sub-scope. The **AI-ask row** echoes the live
query (`Ask agent: "{q}"`) and routes it to the agent (Raycast Quick-AI Tab pattern) — let the agent's
tool allow-list resolve it, not a regex. Never flood cmdk (>3k items degrades it).

### 4.2 Tiptap/Obsidian-grade notes → **FR-121, SC-032**

`pnpm add @tiptap/react @tiptap/markdown @tiptap/extension-table …` (validated: `@tiptap/markdown` is
now first-party MIT; React 19 supported since 2.10.0). Build on the **existing** `store/notes.ts`
scoping + workspace-blob plumbing (the bare `<textarea>` is the only stub). Headless extensions (not
the React-18-leaning prebuilt UI Components); `useEditor({ immediatelyRender: false })` + `'use
client'` for static export; **markdown is the canonical persisted blob** written via a **Rust atomic
temp+rename** Tauri command (JS `writeTextFile` races/ isn't crash-safe). Per-stock + general scoping,
slash menu, tables, `[[`-wikilinks, markdown round-trip, share/export to `.md`.

### 4.3 Screener formula-grammar → **FR-122, SC-033**

`pnpm add mathjs`. Expose the **existing** recursive `CriterionGroup` AND/OR grammar as a
screener.in-style **nested group editor** (backend already evaluates the tree; the UI only sends flat
OR today) + a **custom formula-leaf** evaluated with **`mathjs` in a Web Worker**. **NEVER `expr-eval`
(CVE-2025-12735, CVSS 9.8 RCE).** Agent-configurable via the new `write_screener_filters` host action.

### 4.4 Research presentation deepening → **FR-123, SC-035**

Real `<table>` blocks (kill the wall-of-pipes — mostly done), **ask-a-follow-up on a brief**,
storyline/narrative structure, and **excellent clickable + deduplicated SOURCES**: one entry per
unique source **across** the structured + web legs (today deduped per-run only), inline `[n]`
hover-preview + click-to-jump, source-type badges (filing vs feed vs news), broken citations **shown,
not hidden**. Fix the 0-source floor and the mode-badge casing.

### 4.5 Company-overview AI narrative → **FR-124, SC-035**

The synthesis "story" section R3 left unbuilt (core overview shipped). Structure: **The Take →
business in one breath → storyline/what's driving it → balanced bull/bear → watch-items/risks**,
rendered as typed blocks **beside** the deterministic metric cards (reuse the `brief-blocks.tsx`
architecture). **Numbers never originate in the LLM**; a **post-generation numeric-verification pass**
asserts every numeral in the prose exists in the supplied structured metrics (the highest-leverage
hallucination guardrail) — strip/mark any that don't. Cite every claim; no buy/sell recommendation.
Reachable from every ticker surface (`open_equity_overview` host action).

### 4.6 Shareable briefs — client-side only, no backend → **FR-125, SC-035**

- **Markdown:** serialize from `brief.structured` + the parsed block AST; copy via `ClipboardItem`
  (user-gesture, focus-sensitive) + save via Tauri `plugin-dialog` `save()` + `plugin-fs`.
- **PNG:** `pnpm add html-to-image`; `toPng({ pixelRatio: 2 })` — oklch-safe in the WebView. **Do not
  use html2canvas** (crashes on Tailwind-4 `oklch()`). Pre-empt the WebKit font double-render (call
  twice / pin `fontEmbedCSS`).
- **PDF:** `window.print()` + a dedicated `@media print` stylesheet (paginated, selectable, oklch-safe;
  Tauri has **no** cross-platform print API). `jsPDF` + `jspdf-autotable` as the silent-save fallback.
  All sharing/export is **client-side — no backend, no hosted link.**

---

## 5. What it needs — additions

### 5.1 First-run that TEACHES the agent's power → **FR-129, SC-038**

Today onboarding teaches **key setup**, not capability (one buried "research NVDA" line). Add a
first-run that teaches the agent: interactive **"try this" chips that actually run** — "open Reliance",
"screen for quality compounders", "research NVDA" — demonstrating the agent driving the cockpit. The
keyless-first guarantee is foregrounded ("it already works with zero keys").

### 5.2 Graceful states everywhere + keyboard-first nav → **FR-119, FR-129, SC-030**

The full failure-mode matrix (§2.3); keyboard-first navigation throughout (the constitution's
keyboard-first mandate) with the palette teaching its own shortcuts.

### 5.3 Session restore + per-research-space agent memory → **FR-130, SC-038**

Session restore exists. Per-research-space _agent memory_ does **not** (brief/notes persist, but the
agent's working context does not). Add a **typed research-space field** (replace the fragile
`RESEARCH_SPACE_PREFIX` name-matching, `S-19`) and persist per-space agent context in the workspace
blob so reopening a research space restores its conversation.

### 5.4 Screener performance + reliability → **FR-126, SC-034**

Root cause: per-symbol `.info` scrape, 12-wide, 30s timeout. The fix (full architecture in
`R4_BUILD_SEQUENCE.md` Tier-2.4): **Yahoo v7 batch quote endpoint** (≤50 symbols/req → 506 calls
become ~11; cookie+crumb reused), **`httpx.AsyncClient` + `Semaphore(8)` + `gather(return_exceptions=
True)`**, `read=15s` timeout, **caching tiers** (quote 15–60s, fundamentals hours), a **warm-universe
precompute** worker, and **visible skip-accounting** (`requested − returned` set diff, itemized —
**never silently drop 242/506**). Target: **cold ≤ single-digit seconds** for full S&P 500,
**sub-second warm**, **<5% skips all itemized**. No new Python dep that breaks the onefile binary
(see §8 / operator Q4).

### 5.5 Sources / citation trust UX → **FR-123, FR-124**

Inline numbered footnotes + hover-preview + a **deduplicated, source-type-badged Sources rail**, with
broken citations shown explicitly (the AlphaSense/Hebbia/Perplexity/Daloopa convergent pattern). Reuse
the FR-041 provenance labels and extend them to narrative sources.

---

## 6. Bugs to fix / confirm (visual proof required — failure-matrix §4)

1. **Screener column overlap** — R3 falsely claimed fixed. SYMBOL→NAME _is_ fixed, but the **header
   `<th>` still collides** ("SECTOMARKET CAP") and the width budget is unsound at narrow widths.
   Fix: **responsive table** — truncate every column incl `<th>`; narrow panel **horizontal-scrolls**
   below a `min-width`. Prove with a header-row screenshot at 1920×1080 **and** a <700px split.
2. **502 "empty series" chart flake** — a designed correctness-gate behavior, not a flake. Downgrade
   an all-providers-empty history to a **clean 200-empty** (or brief retry) so the chart shows "No
   price data", not "(502)".
3. **Date-change crash** — there is no date picker; it's a **timeframe switch** hitting an unguarded
   `setVisibleRange` under synced charts. Guard it (finite + `from<to` + try/catch) and null-check the
   series ref. Prove with Playwright **trusted events**.
4. **macOS Layout menu** — **fixed in code** (`Builder::on_menu_event`); confirm it switches modes via
   **native Computer Use / human click** (the rig cannot synthesize native menu clicks).

→ **FR-127. SC-036.**

---

## 7. Cleanup

The full ledger is `R4_STALE_CODE_REGISTER.md` (8 categories, file:line anchors). The build **removes
the stale, never stacks**: purge the warm-clay `globals.css` fallbacks + comments (`S-1`) and rewrite
`DESIGN_SYSTEM.md` (`S-2`); fix the contract drift (`S-6/S-7`); collapse the redundant deep loops /
mode systems / `__terminal__` sites / versioned registry modules (`S-9/S-15/S-16/S-18`); remove the
tongyi `.pyc` (`S-5a`); rebuild (not salvage) the C/F/G orphans (`S-21`). **`CLAUDE.md` is sign-off-
only** — its 10 stale lines (`S-G`) are reported to the operator; the build does not edit it.

→ **FR-117. SC-039** (cleanup acceptance greps).

---

## 8. New requirements (extend specs/001 — Spec Kit brownfield)

These extend `specs/001-agent-native-redesign/spec.md` without colliding (next-free: **US18+,
FR-112+, SC-026+**). They are mirrored into that spec as a **Pass C / R4 session** (Spec Kit stays the
source of truth). All comply with the Constitution v1.1.0 and preserve the §6.5 boundary + Tier-1
LOCKED files byte-for-byte.

### New User Stories

- **US18 (P1):** Agent-as-OS — the agent drives the whole app at three coherent speeds (FAST/
  ORCHESTRATED/DEEP) with live situational awareness, every mutation through the §6.5 bar.
- **US19 (P1):** One coherent app — collapsed research, context-preserving model-swap, Enter-sends,
  one mode system, no hardcoded-should-be-dynamic.
- **US20 (P2):** ⌘K Raycast-grade palette. **US21 (P2):** Tiptap notes. **US22 (P2):** Screener
  formula-grammar. **US23 (P2):** Research presentation + overview narrative + shareable briefs.
- **US24 (P1):** Screener returns the full universe in seconds with zero silent skips.
- **US25 (P2):** Original design language + graceful states everywhere + teach-the-agent first-run +
  per-research-space memory.

### New Functional Requirements

- **FR-112** — The agent MUST drive the app at three speeds: **FAST** (bare `@TICKER`/quick command →
  default cockpit **instantly, LLM-free**), **ORCHESTRATED** (proposes a panel set + **asks when
  genuinely unsure**, routed through the §6.5 proposed-changes bar), **DEEP** (one research path).
- **FR-113** — The agent MUST have continuous **situational awareness** (live open-panels/focused-
  symbol/viewport snapshot every turn; "this"/"it" resolves the focus) and MUST **re-read app state
  after any mutating action** rather than assuming success.
- **FR-114** — The host-action surface MUST be **complete** for obvious app-driving verbs: write/
  configure screener filters, drawings/annotations, save-workspace, remove-from-watchlist, and plan-
  stageable indicators/close/focus — each registered in the catalog and gated by §6.5 (orders never
  auto-apply, never FAST).
- **FR-115** — Research MUST collapse to **ONE** user-facing model: one entry, "go deeper" escalates
  in place; `mode`/`angles`/`backend`/`single` are internal; **0 redundant user-visible research
  triggers**; one deep loop (Perplexity = explicit opt-in-per-run or removed).
- **FR-116** — **One interaction language:** model-swap mid-conversation **preserves context on every
  path** (incl raw chat); **Enter sends in every composer**; **one** mode system (the vestigial one
  removed).
- **FR-117** — **No hardcoded-that-should-be-dynamic** (guarded/derived) and **no contract drift**
  (TS↔Python brief mode/step kinds reconciled); the stale-code register is executed.
- **FR-118** — The system MUST have **locale-aware market-session awareness** (US + India first-class,
  Principle VIII): every price/quote surface shows `open · pre · after · closed · last-close@<tz>`,
  combined with staleness/provenance — a closed/weekend price is **never** shown as live.
- **FR-119** — **Every** interactive element + data surface MUST render its full state set (interaction
  states + empty/loading/error/market-closed/symbol-not-found/stale), enforced via **shared
  primitives**; **0 silent `—`, 0 raw-JSON dead-ends, 0 silent skips.**
- **FR-120** — A **Raycast-grade ⌘K palette**: grouped + scoped (Ask-AI/Agents/Actions/Panels/
  Symbols), **agents ranked above symbols**, symbols query-gated/capped, a free-text **AI-ask** entry
  routing to the agent.
- **FR-121** — A **Tiptap/Obsidian-grade notes editor** (per-stock + general), **markdown as the
  canonical blob** written via **atomic** (Rust temp+rename) persistence, slash menu/tables/wikilinks/
  markdown round-trip, `.md` share/export.
- **FR-122** — A **screener formula-grammar surface**: the existing nested AND/OR `CriterionGroup`
  exposed as a custom-query editor + a formula-leaf via **mathjs in a Web Worker** (**never
  expr-eval**), **agent-configurable** via a host action.
- **FR-123** — **Research presentation** MUST deepen: real tables, ask-a-follow-up, storyline, and a
  **clickable, deduplicated, source-type-badged** sources rail with inline `[n]` hover/jump and
  broken-citations-shown.
- **FR-124** — The **company overview** MUST include an **AI narrative** (The-Take → business →
  storyline → **balanced bull/bear** → risks) as typed blocks beside the deterministic metric cards;
  **numbers never originate in the LLM**, a **post-generation numeric-verification pass** asserts every
  prose numeral exists in the structured metrics; every claim cited; no buy/sell rec.
- **FR-125** — **Shareable briefs, client-side only** (no backend/hosted link): markdown copy/export,
  **PNG** (`html-to-image`, oklch-safe), **PDF** (`window.print()` + print stylesheet; jsPDF fallback).
- **FR-126** — The **screener MUST return the full universe in seconds** (batch quote endpoint + async
  concurrency + caching tiers + warm precompute; **cold ≤ single-digit seconds for S&P 500, sub-second
  warm**) with a **visible skip ledger** — **0 silently dropped symbols**.
- **FR-127** — The four named bugs (screener column overlap, 502 empty-series, date-change crash,
  macOS Layout menu) MUST be **fixed/confirmed with rendered-pixel / trusted-event / native proof.**
- **FR-128** — The **original design language** (`R4_DESIGN_LANGUAGE.md`) MUST be applied: OKLCH
  ramp/accent re-value into historical names (3-place canvas lockstep), type/spacing/unified-motion
  tokens, elevation-by-luminance (**no neon/glow**), warm-clay fallbacks purged, accent ≤5% of pixels.
- **FR-129** — **First-run teaches the agent's power** (interactive "try this" chips that run) and
  **keyboard-first navigation** holds throughout.
- **FR-130** — **Session restore + per-research-space agent memory**: a typed research-space field;
  per-space agent context persisted in the workspace blob and restored on reopen.

### New Success Criteria

- **SC-026** — The three speeds are demonstrated with pixel proof: FAST opens a default cockpit on a
  bare ticker **with no model call**; ORCHESTRATED proposes a panel set + asks-when-unsure through the
  §6.5 bar; DEEP is the single research path. 100% of mutations gated.
- **SC-027** — "tell me more about this" resolves the focused symbol 100% of the time; a host-action
  completeness audit shows screener-filter-write / drawings / save-workspace reachable by agent **and**
  by hand; the agent re-reads state after mutations (no assumed-success defects).
- **SC-028** — Exactly **one** research entry; **0** user-visible mode/angles/backend knobs; **one**
  deep loop (audit).
- **SC-029** — Model swap mid-conversation preserves context on **every** path; Enter sends in **every**
  composer; **one** mode system (audit).
- **SC-030** — Every surface in the failure-mode matrix renders its full state set including
  **market-closed** and **symbol-not-found**; **0** silent `—` / raw-JSON / silent skips (visual
  audit, both US + India).
- **SC-031** — ⌘K groups + scopes; **agents rank above symbols**; AI-ask routes to the agent; symbols
  gated (no >3k flood) — pixel proof.
- **SC-032** — Notes round-trips markdown; the atomic write survives a crash mid-save; `.md` share
  produces a correct file (**opened to verify**).
- **SC-033** — Screener nested AND/OR + a formula leaf both evaluate; the agent writes filters into the
  panel; **`expr-eval` absent** from the tree (audit).
- **SC-034** — A full **S&P 500** screen returns **cold ≤ single-digit seconds, warm sub-second**, with
  **<5% skips ALL itemized** (no silent drop) — measured live.
- **SC-035** — Research sources are deduplicated + clickable across both legs; the overview narrative
  passes the **numeric-verification pass with 0 fabricated numbers**; a brief exports to md/PNG/PDF and
  each **artifact opens correctly**.
- **SC-036** — Each of the four bugs has saved visual/behavioral proof (header gap at narrow width;
  502→clean-empty; no date-crash under synced toggle; menu switches modes).
- **SC-037** — The design language is applied: contrast floors **measured** (body ≥4.5:1, large/non-
  text ≥3:1); **no neon/glow**; warm-clay fallbacks **`rg`-clean**; populated screenshots at **both**
  1920×1080 and 2560×1440 saved.
- **SC-038** — First-run "try this" chips actually run; per-research-space agent memory **persists
  across relaunch**.
- **SC-039** — **The floor holds at every milestone:** §6.5 audit **9/9**; Tier-1 LOCKED files
  byte-for-byte untouched; orders never auto-apply; keyless-first intact; `pnpm ci-local` + smoke-test
  green (audit-grep).

---

## 9. Verification contract (summary — full version in `R4_BUILD_SEQUENCE.md` §3–4)

Non-negotiable, this is the discipline R3 violated:

- **Visual-verification gate** — every UI surface screenshotted via the **Quartz** path, **rendered
  pixels inspected**, saved as evidence, at the panel's real width, **populated**, both 1920×1080 and
  2560×1440. **A DOM/`evaluate_script`/test assertion does NOT count for a visual claim.**
- **No orphan drafts** — every feature integrated + verified, or not started and flagged.
- **Native-surface verification decided up front** — establish whether Computer Use can drive the
  native macOS menu (MCP/CU tools resolve at session start → fresh session if approved mid-run); if
  not, **flag native items operator-verify from the start.**
- **Commit-integrity check** after each deliverable (working tree == HEAD; intended files actually in
  HEAD — the R3 staging-bug class).
- **Stale-binary discipline** — rebuild the sidecar after any sidecar change + confirm the running
  binary is the new one before judging.
- **The end loop** — kill only stale Vysted app/sidecar/dev-server (never Claude/Cursor), open a fresh
  build, drive it from the computer, check every button + every bug, reiterate, then present an honest
  **three-bucket report** (VERIFIED / BROKEN / NEEDS-MANUAL-CHECK). A real flagged bug beats a clean-
  looking report.

---

## 10. Open questions for the operator (the ONE batched block — answer before the build runs)

Everything decidable was decided in-spec. These five are genuine Tier-4 / scope / taste forks; each
carries a recommendation the operator ratifies.

1. **India realtime BYOK — in R4 scope, or a deferred track?** The data ladder (keyless Yahoo →
   broker-WS BYOK Kite/Upstox → paid EODHD) is documented (`R4_BUILD_SEQUENCE` / research). Realtime
   broker-WebSocket tick is a sizable **new subsystem** beyond the experience layer.
   _Recommendation:_ **R4 stays keyless-Yahoo-default** (already shipped) and **documents** the ladder;
   broker-WS realtime + EODHD are a **separate later track**. (Alt: pull Kite/Upstox WS into R4.)

2. **Branch — stay on `003-vysted-rebuild`, or cut a fresh `004`?**
   _Recommendation:_ **cut `004` off `003`** for a clean experience-rebuild history (the brief permits
   either). Low stakes.

3. **Accent value — keep the exact R3-ratified `#818cf8`, or adopt the OKLCH-refined ~12–15%-
   desaturated cool-indigo?** (`R4_DESIGN_LANGUAGE` §2.2.) The hue stays cool-indigo either way; this
   is only the exact stop value.
   _Recommendation:_ **adopt the OKLCH-refined desaturated value** (stops it reading as stock
   `indigo-400`). One-line revert if you prefer the ratified hex.

4. **Sidecar Python-dep tolerance for the screener perf fix.** The fix prefers **pure `httpx` + a
   hand-rolled cookie/crumb** (no new dep). `curl_cffi` (Yahoo bot-evasion) and/or `yahooquery`
   (batch-endpoint fallback adapter) would harden it but add deps to the `--onefile` binary.
   _Recommendation:_ **try pure-httpx first; allow `curl_cffi`/`yahooquery` ONLY if the PyInstaller
   binary still builds + boots** (smoke-test green). Confirm this tolerance.

5. **Deep-research escalation UX (post-collapse).** With one research model, how does "deep" trigger?
   _Recommendation:_ **explicit "go deeper" control + auto-escalate on clear signals** (the model can
   request more rounds within the budget), never an auto-paid-backend. (Alt: pure auto-detect by query
   complexity / always-ask.)

— End of master spec. The four supporting docs complete the executable package. The build window runs
from these without re-discovering anything.
