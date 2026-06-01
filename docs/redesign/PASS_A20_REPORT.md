# Pass A.2.0 — total cleanup, deep bug-hunt, animation polish

_Branch `001-agent-native-redesign` (NOT merged to main, NOT version-bumped).
Lead: Opus 4.8 (1M), driving the real running Tauri app through the tauri-mcp rig
with the **display awake** — so every fix below is verified against live pixels +
the live DOM, not just code. This pass deepens Pass A: the most extensive bug-hunt
yet, the 5 operator-found bugs fixed for certain, Apple-grade motion added, and a
wide jank sweep across every panel + plugin + dialog._

> Read order: this report → `PASS_A_REPORT.md` (prior pass) → `POLISH_SWEEP_REPORT.md`.

---

## ⚠️ What needs your eyes first (ranked)

1. **The theme is now continuous — the headline win.** The cold-navy dockview **tab
   strip** (`rgb(16,25,44)` / `rgb(28,28,42)`) that sat above every panel is gone —
   it's warm charcoal now (`rgb(16,14,12)`). That cold strip was the real reason
   Marketplace/Tradesa "looked cold": the **panel bodies were always warm; the tab
   strip above them was navy**, breaking continuity. Open the app and confirm the
   whole cockpit now reads as one warm surface. _(Root cause was invisible to the
   code-readers — dockview 4 nests a `.dv-shell.dockview-theme-abyss` that
   re-declared the `--dv-*` vars; only the live DOM exposed it. See §Bug 4.)_
2. **Multi-portfolio + real empty state.** The fabricated `+107.69%` demo portfolio
   is gone. The panel now manages **multiple named portfolios** (create / rename /
   switch / delete, never below one) with **manual holdings** persisted in the
   workspace blob. Verified live: created "Crypto Bags", added a holding, switched,
   deleted. ⚠️ **One thing to decide** — the sidecar agent tool `get_portfolio`
   still reads the old sidecar SQLite, which now diverges from the UI (see §Surface).
3. **Animations — eyeball the timing.** Six motion seams added (dock open/close,
   diff-gate, mode-switch pill, onboarding banner, dialogs, transcript). They honor
   reduced-motion. The numbers I chose are in §Animation — tell me if any feel slow
   or fast.
4. **Multi-portfolio agent divergence** (the §Surface item) — a real product
   decision, not a bug.

**No STOP-AND-SURFACE guardrail was hit. No LOCKED file was edited. §6.5 audit 9/9.**

---

## The 5 operator-found bugs — fixed + live-verified

| #   | Bug                                                       | Root cause (found live)                                                                                                                                                                                                                                                                                    | Fix                                                                                                                                                                                   | Live proof                                                                                                                                                      |
| --- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Whole-app micro-scroll**                                | `html`/`body` were `overflow:visible` with no viewport lock; a focus/inertia/sub-pixel event nudged the unlocked document (dockview's inner `overflow:auto` chained to it).                                                                                                                                | Lock `html,body` → `height:100%; overflow:hidden; overscroll-behavior:none` + `body{position:fixed;inset:0}`; `<main>` → `h-full w-full`.                                             | DOM: `overflow:hidden`, `position:fixed`, `overscroll-behavior:none` on both. Shell is now immovable.                                                           |
| 2   | **Black bar / seam** between dock + panels                | The 12px resize splitter had **no background**, so the parent `bg-charcoal-950` (the single darkest token) bled through as a dark gutter; plus a 1px `border-r` on the dock.                                                                                                                               | Paint the splitter `bg-charcoal-900` (the panel surface); drop the aside border.                                                                                                      | DOM: splitter bg `rgb(22,20,15)` = charcoal-900 (matches panels); aside `border-right-width: 0px`. Dock+cockpit are one field.                                  |
| 3   | **Command-palette item bleed**                            | shadcn `DialogContent` is a CSS **grid**; the listbox inherited `min-width:auto` and grew to the widest persona row's intrinsic width — overflowing the 512px modal by **~443px** (rows were 954px).                                                                                                       | `overflow-hidden` on the dialog + `min-w-0` + `[scrollbar-gutter:stable]` + `overflow-x-hidden` on the listbox/wrapper so rows truncate to the modal width.                           | DOM before: list 954px (dialog 512). After: list **510px, fully contained** (`contained:true`); `⌘1` badges now sit inside the modal, long subtitles ellipsize. |
| 4   | **Theme discontinuity** (Tradesa V2, Marketplace, panels) | (a) dockview 4 nests a `.dv-shell.dockview-theme-abyss` that re-declared `--dv-*` to cold navy, shadowing the wrapper-only override; (b) Tradesa V2 = a wholesale cold zinc/blue/emerald palette across 10 files; (c) misc undefined-token stragglers (amber-900/950→literal orange, charcoal-50→dropped). | Extend the vysted theme to the `.dv-shell` (warm tabs); convert all 10 Tradesa files to instrument tokens; fix the stragglers; theme the native `<select>` chrome.                    | DOM: tabs `rgb(16,14,12)` warm (was navy). Marketplace + Tradesa render fully warm. **Zero cold/off-token classes remain.**                                     |
| 5   | **Fake default portfolio**                                | The `$107.69%` came from **persisted positions in the dev sidecar SQLite** (computed, not a literal) — the panel read the sidecar.                                                                                                                                                                         | Move portfolio to a frontend store (`src/store/portfolios.ts`) of named portfolios, persisted in the workspace blob; seed ONE empty default; rewire the panel; drop the sidecar CRUD. | DOM: panel reads "This portfolio is empty"; `107.69` absent everywhere. Multi-portfolio CRUD verified live.                                                     |

Evidence screenshots: `docs/screenshots/pass-a20/01-cockpit-warm-marketplace.png` (warm
tabs + warm Marketplace + named-portfolio header), `02-command-palette-contained.png`
(contained rows + badges inside the modal).

---

## Bug 4 — theme continuity, in detail

The decisive find was **live-only**: globals.css `.dockview-theme-vysted` set warm tab
vars, and the code-readers verified that text — but the running app rendered cold navy.
Walking the live DOM ancestor chain exposed a nested
`.dv-shell.dockview-theme-abyss` (dockview 4's default-themed inner shell) that
**re-declares** every `--dv-*` to the abyss navy palette (`#000c18` / `#1c1c2a`), which
the tabs + group-view inherit from the shell, not from our wrapper. The fix scopes the
override to `.dockview-theme-vysted .dv-shell` (equal specificity, later in source → wins).
One selector warmed the entire dockview chrome. **This is exactly why the operator
insisted on pixel verification** — no amount of code-reading would have caught it.

**Tradesa V2** was a genuine wholesale discontinuity (cold near-black panels next to warm
native ones): all 10 rendering files converted — `zinc→charcoal`, `blue→clay/charcoal`,
emerald/red P&L→`positive/negative`, undefined `amber-950`/`red-950`→`warning/negative`,
`purple→clay/charcoal`; the tone map centralised in `_utils.ts`.

**Other stragglers fixed:** ChatSidebar agent bubble (`amber-900/950`→clay),
SecFilings active tab (`charcoal-50`→`lume`), destructive button (`text-white`→`lume`),
and the macOS native `<select>` cold chrome in Settings + AuditLogViewer (now
`appearance-none` + warm chevron + clay focus).

---

## Multi-portfolio + empty state (Bug 5, in full)

New `src/store/portfolios.ts` — a Zustand store modelled on the watchlist precedent:

- **Shape:** `Portfolio { id, name, holdings: Holding[] }`, `Holding { id, symbol,
quantity, costBasis, assetClass, note? }`, plus `activeId`.
- **CRUD:** create (names + activates, returns id), rename, delete (never drops below
  one — a fresh empty replaces the last; switches active if needed), switch,
  add/update/remove holding. `setAll` normalises a corrupt blob (drops empty symbols,
  coerces numerics + class) exactly like `symbols.setEntries`.
- **Persistence:** rides the `SerializedWorkspace.portfolios` blob (serialize +
  guarded deserialize + an autosave subscription in `page.tsx`) — NOT the sidecar,
  NOT localStorage.
- **Panel:** rewired to read the active portfolio's holdings from the store; a header
  bar (named switcher + create / rename / delete); the add-holding form drives the
  store synchronously (the sidecar 50s cold-boot retry + loading skeleton are gone);
  live P&L still joins each holding to a quote and uses the **untouched** `metrics.ts`
  via a thin Holding→Position adapter (so `metrics.test.ts` stays green).
- **Empty state:** the seed is ONE empty portfolio, so a fresh install reads
  "This portfolio is empty — Manually add a stock or crypto holding… No broker
  connection required."
- **Sizing:** the new header bar needed room, so `portfolio-panel` host-side
  min-height went 160→320 (the post-restore grow-snap applies it). Verified: the
  panel grew 219→285px and the empty-state CTA is now visible in the rail.

Live-verified: created "Crypto Bags" → switched (active="Crypto Bags") → added a
holding (`Crypto Bags · 1`, summary computing) → deleted → back to the single empty
"Portfolio". Unit-tested: 10 cases (create/rename/switch/delete/never-zero/add/edit/
remove/validate/empty), all green.

---

## Animation polish — what to eyeball

`tailwindcss-animate` was installed but **never wired into the Tailwind 4 pipeline**, so
every dialog's `animate-in/out` utilities emitted no CSS and popped instantly. Added
`@plugin "tailwindcss-animate"` (now all dialogs fade+zoom), a `prefers-reduced-motion`
guard, an app-level `<MotionConfig reducedMotion="user">`, and a shared `@/lib/motion`
module (house easing `cubic-bezier(0.2,0.8,0.2,1)` mirroring `--ease-instrument`).

| Seam                                  | Motion                                                                | Timing to eyeball                     |
| ------------------------------------- | --------------------------------------------------------------------- | ------------------------------------- |
| Agent dock open/close (⌘B)            | width reveal (content holds full width, outer clips)                  | **260ms**, instant during drag-resize |
| Command palette / all dialogs         | Radix zoom-in-95 + fade (via the plugin)                              | 200ms                                 |
| Diff-gate (trust surface)             | section slides+fades up; cards slide out + siblings reflow (`layout`) | section **240ms**, card 200ms         |
| Mode switch (Ask/Edit/Build/Delegate) | shared-layout sliding pill (`layoutId`)                               | spring (stiffness 520, damping 40)    |
| Onboarding banner + delegate budget   | height+opacity collapse (no layout jolt)                              | 280ms / 220ms                         |
| Transcript messages                   | settle in (opacity+y)                                                 | 180ms                                 |

All gated on `prefers-reduced-motion`. Tell me if the dock 260ms or the pill spring feel
off — they're single-constant tweaks in `src/lib/motion.ts`.

---

## Wide jank sweep (beyond the 5 bugs)

A 17-finding sweep across data + analysis panels + dialogs, all applied:

- **Screener (high):** the criterion-row grid used a comma arbitrary-value
  (`grid-cols-[8rem,9rem,…]`) — invalid in Tailwind 4, so every row's controls stacked
  vertically. Fixed to underscores; results table → `table-fixed`.
- **Watchlist:** sub-dollar crypto rendered "0.00" → magnitude-aware significant digits.
- **Equity-overview:** statement cells no longer clip abbreviated values; absolute change
  shown next to %; rating tallies don't wrap mid-number.
- **Macro:** the loading spinner's double `border-color` made the ring invisible → fixed.
- **Node-editor:** the run overlay was a 4th rail that starved the canvas → absolute
  drawer; hand-rolled modals got ESC/backdrop close; orphan `<li>`→`<p>`.
- **Analyst-ratings:** added a loading state (was mislabelling loading as empty),
  default-loads AAPL (populated-panel convention), connected the active tab; price-target
  chart got an empty overlay.
- **Dialogs:** `DialogContent` gains max-height+scroll so tall dialogs never clip buttons.
- **Settings:** keybinding recorder — **Esc now cancels** instead of being bound.
- Plus: marketplace "Needs key" badge, responsive Greeks grids, idle-hint under errors,
  earnings/news icon empty states, backtest duplicate-label, StatusChrome provider label,
  plugin-manager idle-timer gate. (Safety surfaces: presentation-only — review checkbox,
  confirm gate, testids, audit/kill-switch wiring untouched.)

---

## Gate results

| Gate                                       | Result                           |
| ------------------------------------------ | -------------------------------- |
| `tsc --noEmit`                             | **clean**                        |
| `eslint .`                                 | **clean** (0 errors, 0 warnings) |
| `prettier --check`                         | **clean**                        |
| `vitest` (full)                            | **745 / 745 passed** (101 files) |
| sidecar `pytest test_safety_end_to_end.py` | **9 / 9** (§6.5 audit intact)    |

Not run: full `pnpm ci-local` (cargo/clippy/ruff/sidecar build — heavy/pre-tag) +
`smoke-test-sidecars`. No Rust/Python source changed this pass (all changes are
frontend + the Tradesa frontend), so the sidecar binary needs no rebuild.

---

## Surface to the operator (Tier-3 — not a blocker)

**`get_portfolio` agent tool now diverges from the UI portfolio.** The catalog tool
`get_portfolio` (`sidecar/services/agent_tools/catalog.py`) reads the user's portfolio
from the **sidecar SQLite** — where the old fake data lived. The UI now reads the
**frontend store / workspace blob**, so the two diverge: a fresh install's UI is empty
while `get_portfolio` returns whatever is in the (empty-in-prod) sidecar DB. The agent's
_context_ view stays correct — the panel-context bus publishes the active portfolio's
snapshot — so "what am I looking at" is right; only the explicit tool diverges. I did
**not** rewire `get_portfolio` because the catalog is the governed single-source-of-truth
(Constitution Principle II) and repointing it at the frontend is a real capability change,
out of this pass's UI scope. **Decision for you:** (a) repoint `get_portfolio` at the
frontend portfolio (e.g. via a context bridge), (b) keep manual holdings mirrored to the
sidecar too, or (c) accept the divergence (the context bus already covers the agent).

---

## Guardrails honored

- **No LOCKED file edited** — `types/plugin.ts`, `types/safety.ts`, `types/broker.ts`,
  `tauri.conf.json`, the safety/broker/audit/kill-switch models, `broker_base.py`,
  `kill_switch.rs`, `test_safety_end_to_end.py`, CI — byte-for-byte untouched. Panel
  min-sizes stayed **host-side** in `PanelHost` (never `PanelSpec`).
- **§6.5 presentation-only:** OrderConfirmationDialog (retry→Button) + AuditLogViewer
  (select chevron) restyled only — the mandatory-review checkbox, disabled-until-checked
  Confirm gate, every `data-testid`, and the kill-switch/audit wiring are untouched
  (the Python audit is independent and stays 9/9).
- **Brokers stay read-only.** No order/execution path added; no broker auto-sync built.
- **Rig stays dev-only** (`NODE_ENV` / feature-flag guards intact).

---

## Telemetry

**Workflows (background, parallel subagents):**

| Phase                                                                                             | Agents | Subagent tokens | Tool-uses | Wall-clock |
| ------------------------------------------------------------------------------------------------- | -----: | --------------: | --------: | ---------: |
| Understand (10 readers: shell, seam, palette, theme×2, portfolio, animation, jank×2, dialogs)     |     10 |         918,944 |       224 |     ~6m45s |
| Implement (5 clusters: Tradesa, core-panels, analysis-panels, chat-anim, dialogs-settings-safety) |      5 |         511,300 |       255 |     ~7m19s |
| **Total subagents**                                                                               | **15** |      **~1.43M** |   **479** |          — |

**Lead (Opus 4.8 1M):** all rig driving (live pixel screenshots + DOM measurement —
this is what caught the abyss-shell, the 443px palette overflow, and the
sidecar-not-code fake-portfolio source that the readers got wrong), the
foundation/shell/palette/portfolio build, integration + gate-fixing (2 test fallouts),
the PanelHost sizing fix, and verification.

**Output:** 9 commits (portfolio, shell, palette, panel-jank, dialogs/settings/chrome,
chat-anim, Tradesa, docs-format, panel-host) + this report. ~62 files,
+1.5k/−1.0k. Branch pushed to origin at each checkpoint (`b3be650..2a39964`).
Three live-vs-code discrepancies the rig caught that the readers missed: the cold
dockview tabs (readers trusted globals.css), the palette overflow magnitude (readers
said 8px; live was 443px), and the fake-portfolio source (readers said "no fake data in
code"; live had persisted sidecar rows).
