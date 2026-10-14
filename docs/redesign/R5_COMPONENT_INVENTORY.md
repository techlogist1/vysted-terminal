# R5 — Component Inventory (what is wrong with each surface today)

> Built from a 9-agent file:line audit of the live `004-r4-experience-rebuild` head. The palette is
> **settled** (Warm Graphite + amber, confirmed in `tokens.css`); every defect below is **craft or
> information design**, not color. The design _system_ exists — components fail to enforce it.

Legend: **CRAFT** = visual/interaction polish · **INFO** = information design · **SCALE** = off the
type/spacing system.

---

## 1. Financial data panels — equity-overview (worst offender) + the table family

`src/modules/equity-overview/EquityOverviewPanel.tsx`

- **INFO** `:791` fundamentals render as a `grid grid-cols-2 gap-x-6 gap-y-1` **key-value dump**, not a
  statement table — labels left, values left-aligned after them, no right-aligned numeric column.
- **INFO** `:317–365` `StatementTable` is hand-rolled with inline `colgroup` width% and **no period column
  headers** semantics; sections aren't visually grouped.
- **INFO** `:795` every value renders at `charcoal-100` (primary tier) — **flat hierarchy**, headline metric
  and minor ratio look identical.
- **INFO** number formatting under-formats some fields: the live shot shows `Free cash flow 101.098 USD`
  and `Shares out. 14.698` (missing the **B** suffix) while market cap formats correctly → inconsistent
  formatter routing.
- **CRAFT** the Load/search input overlaps the ticker header (`AAPL Apple Inc … $318.20`).
- **SCALE** `:325` header `text-[0.6rem]` (9.6px); `:258,279` `text-[13px]`/`text-[10px]`; `:624` input
  `h-8`; `:627,639` autocomplete `py-1.5` + `text-[11px]`.
- **Gap:** no shared `DataTable` primitive exists — every table re-rolls this.

**The other tabular panels each diverge** (same data, different look): `screener/ScreenerResultsTable.tsx`
(text-sm + px widths), `analyst-ratings/{RatingsHistory,IndividualAnalyst}Table.tsx` (`text-[0.6rem]`
headers, `py-1.5`), `earnings/EarningsCalendarPanel.tsx` (`text-[0.6rem]`, `py-1.5`),
`sec/{FilingsList,InsiderTrading}Table.tsx` (`text-[11px]`/`text-[10px]`, `py-1`),
`portfolio/PortfolioPanel.tsx` (`text-[0.65rem]`, `py-2`), `watchlist/WatchlistPanel.tsx` (`text-sm`). Six
independent number formatters (`formatNumber`/`fmtNumber`/`formatMoney`/`fmtMarketCap`/`formatBigInt`/
`formatPrice`). **Four different row heights, four different header sizes.**

---

## 2. Notes — `src/modules/notes/NotesPanel.tsx`

- **Good:** Tiptap v3 **already installed & wired** — slash commands, `[[wikilink]]`, atomic persistence
  (`notes-persistence.ts`), and MD/PNG/PDF export all work. The engine is correct.
- **INFO** `:253–283` the toolbar has **no formatting controls** — H1/H2/H3, bold, italic, lists, code,
  quote, link, wikilink are all missing; users rely on hidden `/`.
- **CRAFT** `:332,370` slash/wikilink popups use `shadow-lg` (**glow violation** — must be 1px border).
- **CRAFT** `:124` `prose prose-sm` is **unconfigured** → inherits Tailwind's 16px, off the system scale.
- **SCALE** `:68` `py-0.5`; `:254` toolbar `gap-1.5`; `:289` `text-[11px]`; `:351,390` `text-[10px]`;
  `:124` editor `min-h-[120px]` (cramped).

---

## 3. ⌘K palette — `src/components/CommandPalette.tsx`

- **Root bug** `:225,240,255,271` className `group-heading-style` is **undefined** anywhere → group headers
  render unstyled/invisible → the groups blur into the "wall of agents" the brief describes.
- **Good (keep):** rows already have `truncate min-w-0` (no hard-clip); groups Agents/Actions/Panels/Symbols
  exist; the fixed-query filter ("notes" → Notes) works.
- **INFO** `:214` empty state is a bare "No results." — no composed placeholder, **no empty-query
  suggestions** (recent/suggested).
- **SCALE/CRAFT** `:191` `gap-2.5`/`py-3.5`; `:309,342` rows `py-2.5`; `:198` input `text-[0.95rem]` +
  `font-mono` (should be sans body); `:318,351` `text-[11px]`/`text-[10px]`.

---

## 4. Composer — `src/modules/chat/ChatSidebar.tsx`

- **CRAFT** `:1409` input `min-h-[64px]` (arbitrary) vs `:1416` send `size-11` → reads "huge rectangle +
  small send," not a unit. `:1384` form `gap-2.5` (off-grid).
- **CRAFT** `:1409` input has **no left inset** (`px-3.5` only) — nothing reserves room for a persona/agent
  indicator, so it collides at zero inset. (Verify the "N / 1 Issue" badge in the before-shot — keep any
  such element out of the input box.)
- **SCALE** `:1085,1125` ModeSwitch/PersonaSelect `h-8`; `AgentHud.tsx:66` selects `h-8`; `:1073`
  `gap-0.5` between mode pills (cramped).

---

## 5. Left agent/chat dock + three-pane balance

- **INFO** `ChatSidebar.tsx:1168` empty state uses `justify-center` in a tall `flex-1` column → ~50% dead
  space top and bottom; suggestion chips crammed at the very bottom with no inter-section rhythm.
- **CRAFT** `src/store/agent-dock.ts:14` dock `DEFAULT_WIDTH = 380` (oversized; Cursor's is ~310) → squeezes
  the chart. `src/config/default-layout.ts:61` `CHART_WIDTH_FRACTION = 0.55`.
- **SCALE** `ChatSidebar.tsx:823` agent-spaces tabs `text-[0.65rem]` (10.4px, below the 12px floor).
- **Note** `PanelHost.tsx` dockview: use pixel `setSize` after panels mount; never proportional initial
  widths (rAF/redistribute gotcha).

---

## 6. Cross-cutting scale violations (the "some big, some small" problem)

56+ arbitrary `text-[…]` + off-grid spacing across the app, e.g.: `SettingsPanel.tsx` (18+ instances of
`text-[0.6rem/0.65rem/0.7rem]`), `OnboardingFlow.tsx` (`px-7 py-7`, `gap-5`, `px-3.5 py-2.5`, `py-10`,
`rounded-[2px]`), `PlanView.tsx` (`text-[0.6rem/0.68rem/0.55rem]`, `px-1 py-px`), `ResearchActivity.tsx`
(`text-[0.62rem]`), `DataBadges.tsx` (`px-1.5 py-0.5 text-[11px]`), `ui/button.tsx` (`px-1.5/px-2.5/gap-1.5`).
**Every one maps to an existing named utility or token** — the scale is defined, just not used.

---

## 7. Keychain re-prompt (macOS dev) — `src-tauri/src/keychain.rs`, `Cargo.toml:34`

- Root cause: `tauri.conf.json` bundle has **no `macOS.signingIdentity`** → dev builds are ad-hoc/unsigned →
  **a different code signature every `tauri dev` rebuild** → the keychain ACL (trusts one signature)
  invalidates → re-prompt. The `keyring` v3 + `apple-native` integration itself is correct.
- Fix must live **outside** `tauri.conf.json` (Tier-1): a stable self-signed dev signing identity +
  `APPLE_SIGNING_IDENTITY` in the dev path + a one-time `security set-key-partition-list`. Carry-forward
  noted in `BLOCKERS.md:68`.

---

## Shared-primitive gaps (build once, consume everywhere)

| Need                          | State                         | Action                                |
| ----------------------------- | ----------------------------- | ------------------------------------- |
| `DataTable`                   | **missing**                   | create `src/components/DataTable.tsx` |
| Unified number/unit formatter | partial (`src/lib/format.ts`) | extend; add `formatUnit` K/M/B/T      |
| `.group-heading-style` util   | **undefined** (referenced)    | define in `globals.css`               |
| `EmptyState`                  | **exists & correct**          | reuse; add dense `secondary` variant  |
| `Button`                      | exists                        | harden off-grid padding/gap           |
| Tiptap prose config           | unconfigured                  | scoped `.notes-prose` at system scale |
