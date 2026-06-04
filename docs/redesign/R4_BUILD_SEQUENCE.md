# Vysted R4 — Build Sequence & Verification Contract

> **Status:** Spec — the execution plan the build window runs start-to-finish. It encodes the
> **priority spine** (so a partial drops polish, not features), the **dependency/binary discipline**,
> and the **non-negotiable verification contract**. Pairs with `REBUILD_R4_SPEC.md` (the what/why),
> `R4_STALE_CODE_REGISTER.md` (what to remove), `R4_FAILURE_MODE_MATRIX.md` (state proofs), and
> `R4_DESIGN_LANGUAGE.md` (visual proofs).
> **Branch:** stay on `003-vysted-rebuild` **or** cut a fresh `004` off it. **No merge to main. No
> version bump (stays `0.8.0`).**

---

## 0. The floor (holds at EVERY milestone — never negotiable)

Before any commit is considered done, and as a hard gate at every tier boundary:

- **§6.5 audit 9/9** (`sidecar/tests/test_safety_end_to_end.py` — `test_audit_1..8` + `8b`).
- **Tier-1 LOCKED files byte-for-byte untouched:** `types/plugin.ts`, `types/safety.ts`,
  `types/broker.ts`, `sidecar/models/{safety,broker,audit_log,kill_switch}.py`,
  `sidecar/services/broker_base.py`, `src-tauri/src/kill_switch.rs`,
  `sidecar/tests/test_safety_end_to_end.py`, `.github/workflows/*`, `src-tauri/tauri.conf.json`,
  `LICENSE`/`COMMERCIAL_LICENSE.md`, `CLAUDE.md`. Route around them via Tauri core + capabilities +
  new catalog capabilities + new host-actions (the menu pattern).
- **Orders never auto-apply**; brokers GET-only; secrets keychain-only/per-request/never logged or
  shell-extracted; keyless-first (works with zero keys).
- **No new Python/sidecar dependency** without verifying the PyInstaller `--onefile` binary still
  builds **and boots** (smoke-test). Frontend npm deps are fine.
- `tauri.conf.json` `app.windows[0].dragDropEnabled: false` stays (load-bearing for HTML5 drag).
- Constitution Principle II: any new agent tool is registered in `catalog.py` only — never hand-edit
  `TOOL_SCHEMAS` / the allow-list / the MCP projection.

---

## 1. Priority spine (4 tiers — each fully integrated + visually verified before the next)

The brief's mandate: _a partial drops polish, not features._ Build in this order; do not start a tier
until the previous tier is integrated **and** has its visual/behavioral proofs.

### TIER 1 — Agent-OS spine + coherence audit (the most important pillar)

_Goal: the agent reliably drives the whole app at three coherent speeds, and the app speaks one
interaction language. This is mostly hardening + collapsing what already exists, not from-zero._

1. **Collapse the research modes into ONE seamless model** (master §1, §2.1). Remove the 3 chat
   triggers (`/research`, `/deep`, `/deep heavy`) and the 5 internal paths' user-visibility; `mode`/
   `angles`/`backend`/`single` become **internal escalation**, not user knobs. One `research` entry;
   "go deeper" escalates in place. Unify the two deep loops (register `S-9`). Perplexity becomes an
   explicit opt-in-per-run DEEP backend or is removed (register `S-10`).
2. **The three speeds** (master §1):
   - **FAST** — a bare `@TICKER` / quick command opens the default cockpit **instantly, LLM-free**
     (the gap C2 found — today `@TICKER` only inserts a token). Wire the instant-cockpit path on the
     existing `loadSymbolIntoChart` / `arrange_layout` primitives.
   - **ORCHESTRATED** — "open Route Mobile" → the agent **proposes** the panel set ("Equity Overview +
     Brief + Chart for ROUTE.NS — also peers + news?") and **asks when genuinely unsure** (the second
     gap C2 found — `decompose` never asks today). Add a bounded clarify/ask affordance; route the
     proposal through the existing §6.5 proposed-changes bar.
   - **DEEP** — the single collapsed research path.
3. **Situational awareness hardening** (master §1): keep injecting `__terminal__` every turn; unify the
   two duplicate capture sites (`S-18`); after any app-mutating host action, force a state re-read
   (computer-use's "evaluate the outcome" rule) so "tell me more about this" always resolves the live
   focus.
4. **Close the host-action gaps** (master §1): add `write_screener_filters` (the agent can run a screen
   but cannot write filters into the panel — C2), drawing/annotation actions, `save_workspace`,
   `remove_from_watchlist`; make `set_chart_indicators`/`close_panel`/`focus_panel` plan-stageable
   (`S-17`). Every new mutating capability registers in `catalog.py` and rides the §6.5 gate.
5. **Coherence audit fixes** (master §2): one mode system (`S-15`); model-swap preserves context on the
   raw-chat path too (C4); Enter-sends verified across every composer; fix the brief mode-badge casing
   (`S-6`) + step-kinds (`S-7`); find every hardcoded-should-be-dynamic and fix or guard (`F`).

**Tier-1 done when:** a scripted conversation opens a cockpit at each speed; the proposal bar gates an
orchestrated open; "tell me more about this" resolves the focused symbol; one research path; §6.5 9/9.
**Visual proof:** Quartz screenshots of FAST/ORCHESTRATED/DEEP outcomes, populated.

### TIER 2 — The feature builds (the four marked were R3 orphans — build PROPERLY, not salvaged)

_Each feature is fully integrated + visually verified, or not started and flagged. NO orphan drafts._

1. **⌘K Raycast-grade palette** (master §4.1; register `S-21a`) — `pnpm add cmdk`. Grouped + scoped:
   **Ask AI (forceMount, top) → Agents → Actions → Panels → Symbols** (symbols query-gated, capped,
   below agents; flip the current backwards weighting). Cross-group score offsets in the custom
   `filter`; recency/frequency boost; `Backspace`-on-empty pops a sub-scope; the AI-ask row routes the
   query to the agent. Symbols never flood (cmdk dies >3k items — gate + virtualize).
2. **Tiptap notes editor** (master §4.2; register `S-21b`) — `pnpm add @tiptap/react @tiptap/markdown
@tiptap/extension-table …`. Headless extensions (not the React-18-leaning prebuilt UI Components);
   `useEditor({ immediatelyRender: false })` + `'use client'` for static export; persist **markdown as
   the canonical blob** via a **Rust atomic temp+rename** Tauri command (not JS `writeTextFile`); per-
   stock + general scoping on the existing `store/notes.ts`; slash menu, tables, `[[`-wikilinks,
   markdown round-trip; share/export to `.md`.
3. **Screener formula grammar** (master §4.3; register `S-21c`) — `pnpm add mathjs`. Expose the existing
   recursive `CriterionGroup` AND/OR grammar as a screener.in-style nested group editor (backend
   already evaluates it; UI only sends flat OR today) + a custom formula-leaf evaluated with **mathjs
   in a Web Worker**. **NEVER `expr-eval` (CVE-2025-12735, CVSS 9.8 RCE).** Agent-configurable via the
   new `write_screener_filters` host action.
4. **Screener performance + reliability** (master §5.4; this is a Tier-2 feature, not polish) — replace
   the per-symbol `.info` scrape with the **Yahoo v7 batch quote endpoint** (≤50 symbols/req, cookie+
   crumb reused, `httpx.AsyncClient` + `Semaphore(8)` + `gather(return_exceptions=True)`, `read=15s`),
   **skip-accounting** (`requested − returned` set diff, itemized — never silent), caching tiers
   (quote 15–60s, fundamentals hours), and a warm-universe precompute worker. Target: cold ≤ single-
   digit seconds for full S&P 500, sub-second warm, <5% skips all itemized. **No new Python dep that
   breaks the onefile binary** (httpx already present; `curl_cffi` only if the smoke-test still boots).
5. **The four bug fixes** (failure-matrix §4): screener column overlap (responsive table + `<th>`
   truncate), 502 empty-series (clean 200-empty/retry), date-change crash (`setVisibleRange` guard),
   macOS Layout menu (code done — ratify).

**Tier-2 done when:** each feature is mounted, integrated, and **visually verified at real panel width**
across the relevant universes (US + India); deps in `package.json` and imported by mounted panels; the
screener returns full-500 in seconds with a skip ledger; the four bugs have their visual/behavioral
proofs.

### TIER 3 — Research presentation + narrative + sharing

1. **Research presentation deepening** (master §4.4) — real `<table>` blocks (done-ish), **ask-a-
   follow-up on a brief**, storyline/narrative structure, **excellent clickable + deduplicated
   SOURCES** (one entry per unique source across structured + web legs; inline `[n]` hover-preview;
   source-type badges; broken-citation shown not hidden). Fix the 0-source floor message + mode badge.
2. **Company-overview AI narrative** (master §4.5) — the synthesis "story" section that R3 shipped the
   core overview for but **not** the narrative. Structure: **The Take → business → storyline → balanced
   bull/bear → risks**, rendered as typed blocks **beside** the deterministic metric cards. **Numbers
   never originate in the LLM**; a **post-generation numeric-verification pass** asserts every numeral
   in the prose exists in the supplied structured metrics (the highest-leverage guardrail) — strip/mark
   any that don't. Cite every claim; no buy/sell rec.
3. **Shareable briefs — client-side only, no backend** (master §4.6):
   - **Markdown** — serialize from `brief.structured` + the parsed block AST; copy via `ClipboardItem`
     (user-gesture, focus-sensitive) + save via Tauri `plugin-dialog` `save()` + `plugin-fs`.
   - **PNG** — `pnpm add html-to-image`; `toPng({ pixelRatio: 2 })` (oklch-safe in WebView — **do not
     use html2canvas**, it crashes on Tailwind-4 oklch); pre-empt the WebKit font double-render
     (call twice or pin `fontEmbedCSS`).
   - **PDF** — `window.print()` + a dedicated `@media print` stylesheet (paginated, selectable, oklch-
     safe; Tauri has no cross-platform print API); `jsPDF` + `jspdf-autotable` as the silent-save
     fallback for tables.

**Tier-3 done when:** a brief renders narrative + dedup'd sources; the overview narrative passes the
numeric-verification audit (0 fabricated numbers); md/PNG/PDF export each produce a correct artifact —
**verified by opening the exported file**, not just firing the handler.

### TIER 4 — UI polish + motion (LAST — drops first if time runs out)

1. **Apply the design language** (`R4_DESIGN_LANGUAGE.md`) — re-value the OKLCH zinc ramp + accent into
   the historical token names (3-place canvas lockstep); ship the type scale, spacing scale, unified
   motion tokens; remove the neon glow primitives; purge the warm clay fallbacks (`S-1`/`S-2`).
2. **Shared state primitives** (design §9) — extract `<Skeleton>/<EmptyState>/<ErrorState>/
<MarketClosedBadge>/<NotFoundState>` + extend `<StalenessBadge>`; refactor panels onto them.
3. **Market-session awareness** (design §10 / matrix §3) — the locale-aware session signal across all
   price surfaces.
4. **First-run that teaches the agent's power** (master §5.1) — replace the keys-only onboarding nudge
   with interactive "try this" chips that actually run ("open Reliance" / "screen for quality
   compounders").
5. **Keyboard-first nav + session restore + per-research-space agent memory** (master §5.2/§5.3) —
   typed research-space field (`S-19`); persist per-space agent context in the workspace blob.

**Tier-4 done when:** every redesigned surface is screenshotted (Quartz, both resolutions, populated)
and the rendered pixels match the design language; contrast floors measured; reduced-motion verified.

---

## 2. Dependency ledger (decide up front)

**Frontend (npm — fine to add):** `cmdk`, `@tiptap/react` + `@tiptap/markdown` + `@tiptap/extension-*`,
`mathjs`, `html-to-image`, `jspdf` + `jspdf-autotable`. Each `--frozen-lockfile`-clean; `pnpm ci-local`
typecheck + vitest green.

**Sidecar (Python — gated):** prefer **no new dep** for the screener perf fix (`httpx` already present).
If `curl_cffi` (Yahoo bot-evasion for the cookie/crumb bootstrap) or `yahooquery` (batch-endpoint
fallback adapter) is genuinely needed, **first verify the PyInstaller `--onefile` binary still builds
and boots** via `pnpm sidecars:build && node scripts/smoke-test-sidecars.mjs` — audit the three
`--onefile` silent-drop classes (`--copy-metadata` / `--collect-data` / `--add-data`). A dep that
breaks the binary is rejected even if `cargo test` passes (the binary gap ci-local can't see).

**No model/data dep changes** beyond config: deepseek-v4-flash stays the keyless default (R8 confirmed
it serves + non-thinking-by-default — the R3 hang fear was overstated); fix the stale OpenAI
`gpt-4.1-mini` default (`S-14`).

---

## 3. The verification contract (NON-NEGOTIABLE — this is the discipline R3 violated)

1. **VISUAL-VERIFICATION GATE.** Every UI surface is **screenshotted and the RENDERED PIXELS
   inspected**, the screenshot **saved as evidence**. **A DOM / `evaluate_script` / `.test.tsx`
   assertion does NOT count for anything visual** — the R3 screener-column false-positive (a passing
   DOM check that missed visual overlap) is the cautionary tale. Nothing is "done" without a screenshot
   showing the correct result **at the panel's real width across the relevant universes** (US + India).
   - **Capture path:** the **Quartz `/tmp/rigcap.py`** path (bridge-independent, matched on
     `kCGWindowOwnerName == "vysted-terminal"`) — the tauri-mcp `screenshot` tool **wedges the bridge**
     on an occluded WKWebView. `evaluate_script` reads live state regardless of focus (fine for state
     reads, **not** for visual proof).
   - **Resolutions:** both **1920×1080 and 2560×1440**, **populated** (real data), saved under
     `docs/screenshots/v0.8.0-r4/` — **never overwrite** existing shots.
   - **Canvas-interactive surfaces** (chart drag/pan, drawings, node editor, Radix dismiss-on-select)
     need **Playwright trusted (`isTrusted=true`) events** — chrome-devtools/tauri-mcp **cannot
     synthesize** them. Drive the **web build** at `localhost:3000/?sidecar-port=NN`.
2. **NO ORPHAN DRAFTS.** Every feature is **fully integrated + verified, or not started and flagged.**
   No code authored "for later." Deps are installed and imported by mounted panels, or the feature
   isn't claimed.
3. **NATIVE-SURFACE verification decided UP FRONT.** Establish at the start whether **Computer Use can
   drive the native macOS menu** (repackage display name to "Vysted"/`com.vysted.desk`, `caffeinate`).
   **Critical load-timing caveat:** MCP servers + Computer Use tools resolve at **session start** —
   anything approved mid-session needs a **fresh session**. If Computer Use genuinely can't drive the
   native menu, **flag the native items as operator-verify from the start** (don't claim them verified).
   The macOS Layout menu (Bug-4) is the canonical native item: code-complete, **pending one human/CU
   click**.
4. **COMMIT-INTEGRITY check after each deliverable.** `git status` clean (working tree == HEAD); the
   _intended_ files are actually committed (R3 hit a staging bug where a `git add`+`git rm` atomic op
   dropped the real edits — verify the diff is in HEAD, not just the working tree).
5. **STALE-BINARY discipline.** After **any** sidecar change: `pnpm sidecars:build` → smoke-test →
   **confirm the running binary is the new one** before judging behavior. `cargo test` never runs the
   binary; the smoke-test does.
6. **Keyed model/research claims** run through the **live native app** (keychain `invoke` only works
   inside the real Tauri webview) — never by curling a provider with an extracted secret.
7. **The release gate** (before tagging — though R4 does **not** tag/bump): `pnpm ci-local` (mirrors CI
   byte-for-byte) + `node scripts/smoke-test-sidecars.mjs` + §6.5 9/9. Cheapest in-sprint guard:
   `pnpm format:check`; before any Python commit `ruff format <files> && ruff format --check sidecar &&
ruff check sidecar`.

---

## 4. The end loop (no mid-stop — run to a verified state, then present)

After the build tiers, before presenting:

1. **Kill ONLY stale VYSTED instances** — the app, sidecar, and dev-server processes. **NEVER** kill
   Claude/Cursor processes (that kills the agent host).
2. **Open a fresh build**, reload, and **drive it from the computer**: check **every button and every
   bug**, at real panel widths, populated, US **and** India symbols.
3. **Reiterate** — fix what the live drive surfaces; re-verify with pixels.
4. **Only then present** an honest **three-bucket final report**: **VERIFIED** (pixel/behavior proof
   saved) · **BROKEN** (with the real defect named) · **NEEDS-MANUAL-CHECK** (native menu / keyed runs
   the rig can't drive). **A real flagged bug beats a clean-looking report.**

---

## 5. Suggested commit order (one commit per concrete deliverable, conventional, no emojis)

Tier 1: `refactor(research): collapse 5 paths + 3 triggers into one model` · `feat(agent): FAST
instant-cockpit on bare ticker` · `feat(agent): ORCHESTRATED propose-and-ask via §6.5 bar` · `feat(agent):
host-actions for screener-filters/drawings/save-workspace` · `fix(coherence): one mode system + raw-chat
context + brief mode-badge casing`.
Tier 2: `feat(palette): cmdk Raycast-grade grouped/scoped + AI-ask` · `feat(notes): Tiptap markdown
editor + atomic blob` · `feat(screener): nested AND/OR + mathjs-worker formula grammar` · `perf(screener):
batch quote endpoint + skip ledger + warm cache` · `fix(screener): responsive table + th truncate` ·
`fix(chart): empty-series 200 + setVisibleRange guard`.
Tier 3: `feat(research): dedup'd sources rail + follow-up + tables` · `feat(overview): AI narrative +
numeric-verification pass` · `feat(brief): client-side md/PNG/PDF export`.
Tier 4: `style(design): OKLCH zinc+indigo re-value + type/spacing/motion tokens` · `feat(ui): shared
state primitives + market-session badge` · `feat(onboarding): teach-the-agent first-run` ·
`feat(workspace): per-research-space agent memory`.
Cleanup (woven through): `chore(cleanup): purge warm-clay fallbacks + rewrite DESIGN_SYSTEM` ·
`chore(cleanup): remove dead registry/tongyi-pyc + unify __terminal__ capture`.

Each commit: floor green (§0), its deliverable's verification proof saved.
