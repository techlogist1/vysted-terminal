# Recon — A7:rough-edges

I now have a complete, evidence-backed picture. Four distinct input idioms exist: (1) ring-based `bg-charcoal-800 text-sm focus:ring-amber-400` (watchlist/broker/analyst), (2) `text-xs focus:ring-amber-400` (chat/node), (3) `bg-charcoal-850 border focus-visible:border-amber-500 rounded-control` (quant), (4) `focus:border-amber-400` (settings). Plus `text-sm` vs `text-xs` font-size drift on the same h-8 input shape. Writing the blueprint now.

# Visual / Interaction Rough-Edge Blueprint — Vysted Terminal

## (1) Findings — file:line precise, ranked

**H1 — Panel-header treatment is fragmented (6+ variants).** Same conceptual element (panel title bar) renders differently everywhere:

- News `NewsFeedPanel.tsx:240` `px-4 py-2.5`; BriefPanel `BriefPanel.tsx:206` `px-4 py-2.5`; Marketplace `MarketplacePanel.tsx:62` `px-4 py-3`; but ChatSidebar `ChatSidebar.tsx:652`, SEC (`SecFilingsPanel.tsx:122`, `FilingViewer.tsx:60`, `InsiderTradingTable.tsx:64`), node-editor (`NodeEditorPanel.tsx:413`), broker (`BrokerConnectPanel.tsx:139`), AuditLog (`AuditLogViewer.tsx:102`) all use `px-3 py-2`. **Two header heights coexist app-wide.**
- Title text is worse: `font-serif text-sm` (Brief `:235`), `font-mono text-sm uppercase` (NodeEditor `:415`, AgentBuilder `:238`), `text-sm uppercase` **missing `font-mono`** so it renders in the grotesque (Broker `BrokerConnectPanel.tsx:140`), `font-mono text-xs font-medium uppercase` (News `:241`), `font-serif text-sm font-semibold` (Marketplace `:63`), `font-mono text-xs font-medium` non-uppercase (Chat `ChatSidebar.tsx:654`). A discerning eye sees inconsistent title weight/case/size across tabs.

**H2 — Four conflicting text-input idioms.** Same `h-8` text field, four looks:

- `bg-charcoal-800 … text-sm focus:ring-1 focus:ring-amber-400` (Watchlist `WatchlistPanel.tsx:149`, Analyst `AnalystRatingsPanel.tsx:95`, Broker `BrokerConnectPanel.tsx:412`, BrokerOrderEntry `:169`) — **`text-sm`**.
- `bg-charcoal-800 … text-xs focus:ring-1 focus:ring-amber-400` (Chat composer `ChatSidebar.tsx:1136`, node-editor `:644/662`) — **`text-xs`**.
- `bg-charcoal-850 border-charcoal-700 rounded-control … text-xs focus-visible:border-amber-500` (all of `quant/*`: `OptionPricerPanel.tsx:66`, `BondPricerPanel.tsx:41/121`, `YieldCurvePanel.tsx:151/221`, `GreeksDashboard.tsx:42`) — **different bg, border, radius token, focus idiom AND a different accent stop (amber-500 vs 400)**.
- `bg-charcoal-900 border … focus:border-amber-400` (Settings: `SettingsPanel.tsx:415/441/565`).
  So: 16 files use `focus:ring-amber-400`, 4 use `focus:border-amber-400`, quant uses `focus-visible:border-amber-500`. The Watchlist field at `text-sm` sits next to the Chat composer at `text-xs` — visibly larger type for the identical control.

**H3 — Settings card surface/padding drift.** The card convention is `border-charcoal-700 bg-charcoal-850 … rounded-md border px-4 py-3` (Providers `:176`, PrefRow `:1493`, Modules `:651`, Integrations `:484`, Export `:1357`, About `:1414`). Violations: Layouts list rows `SettingsPanel.tsx:586` use `px-3 py-2`; the Provider-preference inner rows `:978` use `px-3 py-1.5`; the Hardware device card `:763` uses `bg-charcoal-900` (not `-850`) with `p-3`; SearXNG docker card `:447` correct but its `<pre>` `:451` is `bg-charcoal-900`. The Hardware card breaking to `-900` against sibling `-850` cards is the most visible.

**H4 — ChatSidebar header stack: 6 stacked thin `border-b` bars, inconsistent vertical padding + label sizing.** Header `py-2` (`:652`) → ModeBar consequence row `py-1` (`ModeBar.tsx:67`) → RosterStrip `py-1.5` (`:860`) → AgentHud `py-1` (`AgentHud.tsx:68`) → AutonomyToggle `py-1` (`:68`) → ContextBadge `py-1` (`:894`). Label sizes mix `text-[0.6rem]` (most) but header title is `text-xs`. The cumulative rhythm is uneven — a designer reads it as "stacked strips that don't line up."

**H5 — Accent-stop drift: `amber-300` vs `amber-400` for the same affordance.** Mode-bar active tab text is `text-amber-300` (`ModeBar.tsx:46`); header Agent-toggle active is `text-amber-300` (`page.tsx:184`); but the Sparkles icon `ChatSidebar.tsx:653`, all section icons, RefreshCw, etc. are `text-amber-400`. Retry link goes `text-amber-400 hover:text-amber-300` (`:774`) while News retry goes `text-amber-400 hover:text-amber-300` (consistent) — but ContextBadge/Lens labels never light. The quant inputs' `amber-500` focus (H2) is the same bug class.

**H6 — `<select>` chrome is inconsistent.** Settings `Select` (`:1466`) wraps a `appearance-none` select + custom `ChevronDown` overlay (warm, on-brand). But AgentHud selects (`AgentHud.tsx:70/83`) and the RosterStrip select (`ChatSidebar.tsx:863`) are **bare native `<select>`** — they show the cold WKWebView OS chevron, exactly the chrome Settings deliberately strips. Watchlist asset-class select (`WatchlistPanel.tsx:152`) DOES strip it with its own chevron (`:163`). So three of the app's selects show the OS glyph and the design-system note about "warm chevron" is only half-applied.

**H7 — `Button` default variant is off-system.** `button.tsx:8` base is `text-sm`/`gap-2`; the app is `font-mono text-xs`. Default/sm buttons render in the grotesque at `text-sm` while everything around them is mono `text-xs`. The `sm` size (`:23`) is `h-8` with no `font-mono` — buttons read a touch large and in the wrong face vs adjacent labels. (Used pervasively in Settings, Watchlist, etc.)

**H8 — News "neutral" sentiment vs unscored is a 1-stop color difference that's nearly invisible.** `NewsFeedPanel.tsx:51` neutral→`text-charcoal-300`, unscored→`text-charcoal-400` (`:53`). One stop apart on muted text is imperceptible; the dot fill (`:73`, filled vs hollow) carries the real signal but the label color adds noise without information.

**H9 — Watchlist row vertical padding (`py-2`, `WatchlistPanel.tsx:255`) differs from News row (`py-3`, `:100`) and the chat list gap.** Not adjacent, lower priority, but the two flagship "list" panels have different row rhythm.

**H10 — `tracking-wide uppercase` micro-labels lack a shared class.** `.hud-label` exists in `globals.css:136` (the canonical uppercase tracked label) but almost nobody uses it — Lens/Autonomy/Context/ModeBar/News all hand-roll `tracking-wide uppercase font-mono text-[0.6rem]` (or `text-[10px]`, or `text-[0.65rem]`) inline with slightly different sizes (`0.6rem` vs `10px` vs `0.65rem`). No single label scale.

## (2) Exact change plan

**Create `src/lib/ui-classes.ts`** exporting shared constants (this is the highest-leverage fix; "three similar lines beats premature abstraction" but here it's 20+ sites):

```ts
export const PANEL_HEADER =
  "border-charcoal-700 flex items-center justify-between border-b px-3 py-2";
export const PANEL_TITLE =
  "text-charcoal-200 font-mono text-xs font-medium tracking-wide uppercase";
export const FIELD =
  "bg-charcoal-800 text-charcoal-100 placeholder:text-charcoal-400 h-8 rounded-md px-2 font-mono text-xs outline-none focus:ring-1 focus:ring-amber-400 disabled:opacity-50";
export const SETTINGS_CARD = "border-charcoal-700 bg-charcoal-850 rounded-md border px-4 py-3";
export const MICRO_LABEL = "font-mono text-[0.6rem] tracking-wide uppercase";
```

**Edits (per file):**

- **H1:** Unify all panel headers to `px-3 py-2` (change News `:240`, Brief `:206` `py-2.5`→`py-2` & `px-4`→`px-3`; Marketplace `:62` `px-4 py-3`→`px-3 py-2`). Apply `PANEL_TITLE` to every panel `<h2>`: News `:241` (already closest — make it the standard), Broker `:140` (add `font-mono`, `text-sm`→`text-xs`), NodeEditor `:415`/AgentBuilder `:238` (`text-sm`→`text-xs`), Marketplace `:63` (`font-serif`→`font-mono`, add uppercase). **Keep `font-serif` only for content headings** (Brief query `:235`, Equity symbol `:320`) — those are data, not chrome.
- **H2:** Replace all four input class strings with `FIELD`. Watchlist `:149`, Analyst `:95`, Broker `:412`, BrokerOrderEntry `:169/212/223/235` (`text-sm`→shared `text-xs`); quant 7 sites → `FIELD` (drops `bg-850`/`border`/`rounded-control`/`amber-500`); Settings `:415/441/565` → `FIELD` (switch `focus:border`→`focus:ring`). Chat composer `:1136` already matches `FIELD` — make it the template.
- **H3:** Layouts rows `:586` `px-3 py-2`→`px-4 py-3` (or keep tighter for list density but then unify with Provider-pref rows `:978` to one list-row spec `px-3 py-1.5`). Hardware card `:763` `bg-charcoal-900`→`bg-charcoal-850`; `<pre>` `:451` keep `-900` (inset code is intentionally darker — leave, it's a recognized inset pattern).
- **H4:** Normalize the ChatSidebar header stack to a single `py-1.5` rhythm: header `:652` keep `py-2`; RosterStrip `:860` `py-1.5`, AgentHud `:68` `py-1`→`py-1.5`, AutonomyToggle `:68` `py-1`→`py-1.5`, ContextBadge `:894` `py-1`→`py-1.5`. All micro-labels → `MICRO_LABEL`.
- **H5:** Pick one accent rule: **brand/idle icons = `amber-400`; active/selected text = `amber-300`** (already the dominant pattern). Fix quant inputs (covered by H2). No icon changes needed; document the rule in `DESIGN_SYSTEM.md` "Chrome primitives."
- **H6:** Wrap AgentHud's two selects (`AgentHud.tsx:70/83`) and RosterStrip's select (`ChatSidebar.tsx:863`) in the same `appearance-none` + `ChevronDown` overlay pattern as `WatchlistPanel.tsx:152-164`. Extract a tiny `<NativeSelect>` to `ui-classes`/a shared component to avoid 4 copies.
- **H7:** Add `font-mono` to `button.tsx` base (`:8`) and change default text to `text-xs` (or add a `font-mono text-xs` to `sm`/`xs` sizes only, to avoid touching the `lg` CTA). Lowest-risk: append `font-mono` to the cva base string only.
- **H8:** News `:51` neutral → keep `text-charcoal-400` (same as unscored) OR brighten unscored to `-500`; rely on the dot fill for signal. Simplest: drop the neutral/unscored color split, keep both `text-charcoal-400`.
- **H9:** Decide one list-row padding (`py-2` for dense tabular, `py-3` for prose rows is actually defensible — Watchlist is a table, News is prose). **Leave as-is**, note in DESIGN_SYSTEM that tabular rows = `py-2`, prose rows = `py-3`.
- **H10:** Replace inline `tracking-wide uppercase … text-[0.6rem]` micro-labels with `MICRO_LABEL` (or the existing `.hud-label` if the brass tone is wanted). Standardize on `text-[0.6rem]`.

## (3) Risks + safe fallback

- **Shared-constant refactor risk:** a wrong unify changes a panel the operator likes. _Fallback:_ land `ui-classes.ts` constants but apply them file-by-file in separate commits (H1, H2, H4 as independent commits) so any regression reverts one file. **Touch zero Tier-1 files** — all edits are JSX className strings in `src/modules/*` + `src/components/*` + `button.tsx`; none are locked.
- **`button.tsx` (H7) is shadcn-derived, widely used:** adding `font-mono` could shift the destructive/CTA buttons. _Fallback:_ scope `font-mono text-xs` to `xs`+`sm` sizes only, leave `default`/`lg` untouched (the order-confirm CTA stays grotesque-free risk).
- **Select chrome (H6):** `appearance-none` on a select that's keyboard-critical (AgentHud) — verify the dropdown still opens. _Fallback:_ the Watchlist pattern is already proven in-app; copy it verbatim.
- **News color (H8):** removing the neutral stop is a semantic-display change. _Fallback:_ keep it; lowest priority — skip if uncertain.
- **`text-sm`→`text-xs` on inputs (H2):** slightly smaller hit target text. _Fallback:_ `text-xs` is already the majority and matches the mono density system; no a11y regression (font ≥ 11px).

## (4) Verification

- **Lint/format/type gate (catches class typos, broken JSX):** `pnpm format:check && pnpm lint && pnpm typecheck` (run from repo root; per CLAUDE.md `format:check` is the cheapest pre-push guard).
- **Component tests stay green:** `pnpm vitest run src/modules/chat src/modules/news src/modules/watchlist src/components/SettingsPanel.test.tsx` — existing tests assert `data-testid="sentiment-badge"`, button aria-labels, header text; class-only changes must not break them. Run in background if >30s.
- **No Tier-1 drift:** `git diff --name-only` must show only `src/modules/**`, `src/components/**`, `src/lib/ui-classes.ts`, `docs/DESIGN_SYSTEM.md`, `button.tsx` — never `types/*.ts`, `tokens.css` values, `tauri.conf.json`, CI.
- **Visual sign-off (operator, per CLAUDE.md protocol — harness can't drive trusted GUI events):** populated cockpit at 1920×1080 + 2560×1440. Named checks: (a) every panel tab header same height + same title face/case; (b) Watchlist add-field vs Chat composer same type size; (c) AgentHud/Lens selects show the warm chevron (no cold OS glyph); (d) ChatSidebar header strips read as even rhythm; (e) Settings cards all same `-850` surface (Hardware card no longer darker).
- **Tauri rig spot-check (optional, layout only — not trusted events):** `mcp__tauri-mcp__screenshot` of the agent sidebar + Settings panel to diff header alignment before/after.

In short:

- The app is token-clean (1 stray hex, intentional) but **convention-drifted**: panel headers (6 title variants, 2 heights), text inputs (4 idioms incl. wrong accent stop in quant), and settings cards (Hardware breaks to `-850`→`-900`) are the four highest-value unifications.
- Fix via one `src/lib/ui-classes.ts` (PANEL_HEADER/PANEL_TITLE/FIELD/SETTINGS_CARD/MICRO_LABEL) applied in per-area commits; zero Tier-1 files touched.
- Secondary: 3 selects show the cold OS chevron Settings deliberately strips; `Button` base is `text-sm`/grotesque vs the app's mono `text-xs`.
- Confidence: 8/10 — file:line evidence is solid; the only judgment calls are whether `font-serif` content headings (Equity/Brief) should stay (they should) and whether button base should change globally (recommend scoping to xs/sm).
