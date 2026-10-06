# R6 — Codebase & Design Inventory (Phase A)

> The read-only exploration that feeds R6 Phase B. Regenerated to current HEAD
> (`004-r4-experience-rebuild`, post-R5) by a 12-agent file:line sweep of all 76 audited
> surfaces, measured against the R6 OpenCode-dark target now codified in
> [`VYSTED_DESIGN.md`](./VYSTED_DESIGN.md). This is the **worklist** for Phase 1.
>
> The original Phase-A artifact under this name was never committed; this supersedes the
> stale [`R5_COMPONENT_INVENTORY.md`](./R5_COMPONENT_INVENTORY.md) (which predates the R5
> DataTable migration). Full raw findings (every one of the 542 violations with file:line)
> live in the sweep transcript; this file organizes them into root causes + a per-surface
> worklist.

## Verdict

The palette is **settled and correct** — warm-graphite charcoal ramp + single muted amber,
confirmed in `tokens.css`. R5 already built the shared `DataTable` primitive and migrated the
table family onto it. What remains is **not color** — it is the absence of ONE enforced
discipline. Eight prior passes changed sizes locally; none made every surface resolve to a
single system. The result is the "some big, some small, mismatched feel" the brief describes.

**542 violations across 76 files.** By type:

| Type                        | Count | Nature                                                                                                     |
| --------------------------- | ----: | ---------------------------------------------------------------------------------------------------------- |
| **type-scale**              |   251 | arbitrary `text-[Npx]` / `text-[0.55rem]` + bare `text-xs/sm/base/lg/xl/2xl/3xl` bypassing the named scale |
| **spacing**                 |   103 | off-grid `py-1.5` `gap-0.5` `px-2.5` `gap-5` `py-2.5` not on the 4/8px grid                                |
| **radius**                  |    75 | `rounded-md`/`rounded-full` on containers that must be sharp 0px                                           |
| **control-size**            |    48 | h-5 / h-7 / h-8 / h-9 / h-10 mixed across sibling controls                                                 |
| **font**                    |    24 | chrome on the default **sans (Inter)** / explicit `font-serif`; composer `font-sans`                       |
| **alignment-overlap**       |    14 | columns/popups that collide, clip, or truncate mid-number                                                  |
| **shadow-glow**             |     9 | `shadow-lg` / `shadow-2xl` / `shadow-xs` / amber **glow** — all forbidden                                  |
| info-design / color / other |    18 | key-value dumps, opacity tiers, ad-hoc widths                                                              |

Severity: **234 high · 227 medium · 81 low.** The headline: **~80% of all violations
(type-scale + font + most spacing/radius) collapse into a handful of single-point root
fixes** applied at the token foundation and `ui/button.tsx`. The remaining high-value work is
the targeted no-shadow and collision hitlists below, and the brief's three named surfaces
(equity table, composer, ⌘K).

---

## §1 — Five systemic root causes (fix once, propagate everywhere)

**RC-1 — The chrome defaults to SANS, not mono.** `globals.css` sets the body font to
`--font-serif` (Inter); only data surfaces opt back into `font-mono`. The composer input is
explicitly `font-sans`; `platform/WorkspaceDialog` and others use `font-serif text-sm/xl`. The
single mono mandate is unmet at the root.
→ **Fix:** point `--font-serif` (and the body) at the JetBrains Mono family in `layout.tsx` +
`tokens.css` + `globals.css`; load JetBrains Mono via `next/font`. Then delete explicit
`font-sans`/`font-serif` opt-ins. One change makes the whole app mono. (Task 3a)

**RC-2 —251 text nodes bypass the named type scale.** Every surface leaks `text-[10px]`,
`text-[0.6rem]`, `text-[0.55rem]` (8.8px — illegible), and bare `text-xs/sm/lg/2xl/3xl`. The
scale (`text-micro/caption/body/panel-title/section/overview/hero`) exists and is wired; it is
simply not used.
→ **Fix:** add the missing `text-prose` (16px/1.6) utility, then sweep every `text-[…]`/bare-
Tailwind size to a named role. Mechanical, high-volume — the bulk of Phase 1b. (Task 4)

**RC-3 — `ui/button.tsx` is off-spec and is the most-consumed control.** Base class carries
`text-sm` (14px, off-scale), `rounded-md` (6px), and `shadow-xs` on the outline variant. Size
ladder is `default h-9 · xs h-6 · sm h-8 · lg h-10 · icon size-9 · icon-xs size-6 · icon-sm
size-8 · icon-lg size-10` — five heights, the source of the h-8-vs-h-9 misalignments seen
everywhere.
→ **Fix:** rebuild `button.tsx` to the spec's two-height ladder (**32px standard / 24px
compact**), `text-body`, `rounded-control` (4px), no shadow. This single file resolves a large
share of the control-size + radius + scale findings downstream. (Task 4, do first)

**RC-4 — Containers are rounded; the radius vocabulary is inverted.** 75 `rounded-md`/
`rounded-full`/`rounded-[Npx]` on panels, sections, dropdowns, cards, criterion rows, nodes.
The spec inverts this: containers 0px, interactive 4px.
→ **Fix:** set `--radius-panel` to 0px (so every `rounded-panel` consumer goes sharp), keep
`--radius-control` at 4px, and sweep stray `rounded-md/lg/xl/full` on containers to sharp.
(Task 3a + 4)

**RC-5 — No control-height discipline → off-grid spacing everywhere.** Inputs at h-7/h-8/h-9,
toggles h-9, send size-10, answer input h-5; padding `py-1.5`/`px-2.5`/`gap-0.5` chosen to
visually patch the mismatches.
→ **Fix:** the spec's two control heights + the 4/8px spacing tokens; re-derive each control
from them. Eliminates both the control-size and most spacing findings. (Task 4)

---

## §2 — No-shadow hitlist (the §3/§16 no-glow rule — 9 sites, all must go)

Depth = surface ladder + 1px hairline only. Remove every one:

| File:line                           | Current                        | Fix                                            |
| ----------------------------------- | ------------------------------ | ---------------------------------------------- |
| `chat/SlashCommandPicker.tsx:35`    | `shadow-lg`                    | drop; `raised` surface + 1px `hairline-strong` |
| `chat/MentionPicker.tsx:43`         | `shadow-lg`                    | drop; same                                     |
| `components/ui/button.tsx:8,15`     | `shadow-xs` (outline)          | drop from `buttonVariants`                     |
| `node-editor/VystedNode.tsx:48`     | `shadow-sm`                    | drop; surface step                             |
| `node-editor/VystedNode.tsx:49`     | `shadow-amber-500/20` **glow** | drop; selected = 1px accent border             |
| `components/ui/dialog.tsx:56`       | `shadow-lg`                    | drop; `raised` + 1px hairline                  |
| `components/KeyEntryDialog.tsx:94`  | `shadow-2xl`                   | drop                                           |
| `components/KeyEntryDialog.tsx:121` | `shadow-2xl`                   | drop                                           |

(The `dialog.tsx` fix covers most dialogs centrally; `KeyEntryDialog` re-declares its own.)

---

## §3 — Collision / clipping / truncation hitlist (14 — what DOM checks missed)

The brief's "numbers must never collide or truncate mid-number" + ⌘K clipping. Verify each on
the **real rendered window** in Phase 2:

| File:line                                                                   | Defect                                                                                     | Fix direction                                                       |
| --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------- |
| `backtest/BacktestResultView.tsx:228-350`                                   | trade table cells `max-w-0 overflow-hidden` → prices clip **mid-number** (`123.456`→`123`) | real column widths, right-aligned tabular, no `max-w-0` on numerics |
| `research/brief-blocks.tsx:535`                                             | metric grid `gap-px` cells `px-3.5`, long value overflows w/o ellipsis                     | fixed cells, `tabular-nums`, ellipsis/wrap control                  |
| `research/brief-blocks.tsx:513`                                             | metric price line `flex-wrap` — symbol chip + price + change collide/wrap on narrow        | right-align numerics, no unguarded wrap                             |
| `equity-overview/EquityOverviewPanel.tsx:805`                               | header mixes 22/15/13/12px on `items-baseline` → baselines misalign                        | one headline scale + aligned secondary row                          |
| `screener/ScreenerCriteriaBuilder.tsx:126` / `CriterionGroupEditor.tsx:136` | fixed `grid-cols-[8rem_9rem_…]` → long field names overflow                                | min-w-0 + truncate, or flexible track                               |
| `screener/ScreenerResultsTable.tsx:349-358`                                 | summary `X rows (Y eval, Z skip, N ms)` bare spans collide narrow                          | structured, gap-guarded                                             |
| `notes/NotesPanel.tsx:338-369, 373-405`                                     | slash + wikilink popups positioned by inline `left` → clip at viewport edge                | boundary detection / max-width                                      |
| `chat/ChatSidebar.tsx:1374-1442`                                            | composer picker `absolute bottom-full` can extend up over transcript                       | scroll container + bounded max-h                                    |
| `macro/MacroSeriesPicker.tsx:124-173`                                       | dropdown `max-h-48` can clip results narrow                                                | responsive max-h / scroll                                           |
| `node-editor/workflow-run-overlay.tsx:496`                                  | `absolute top-0 right-0 z-10` overlaps toolbar/canvas controls                             | reserve gutter / reflow                                             |
| `components/PluginManagerPanel.tsx:57-64`                                   | empty state `max-w-xs`, text can overflow                                                  | constrain + wrap                                                    |
| `components/KeyEntryDialog.tsx:121-170`                                     | `gap-0 p-0` + h-9 input, tight                                                             | spec dialog padding                                                 |

---

## §4 — Per-surface worklist

Each surface: scope files, one-line state, key clusters, and current control inventory.
Bring every control to the spec's **32px standard / 24px compact** ladder.

### 1. equity-overview (brief's named #1 — worst offender)

`EquityOverviewPanel.tsx`. **30+ violations.** All section containers `rounded-md` (→0px);
header baseline mismatch (805); search **input h-9 vs Load button h-8** (4px misalign);
off-grid `py-0.5`/`gap-y-1`/`mx-0.5`; icons `size-3.5`/`size-5` off-scale. Fundamentals already
humanized (R5) but still rendered in a section that needs sharp edges + the DataTable numeric
treatment. Controls: search h-9 → 32px; Load (size=sm h-8) → 32px; autocomplete rows `py-1.5`;
quick-load buttons `py-1.5 px-3`.

### 2. screener + watchlist

`Screener{Panel,CriteriaBuilder,Presets,ResultsTable,FormulaLeaf}`, `CriterionGroupEditor`,
`WatchlistPanel`. **47 violations.** `text-[10px]`/bare `text-xs` throughout; criterion/group
containers `rounded-md` (→0px); preset buttons `rounded-full` (→4px); criterion grids can
overflow (§3); **watchlist symbol input + asset-class select h-9** while other inputs ~h-8;
non-standard `size-icon-xs`/`size-icon-sm` button variants. ResultsTable `min-w-[920px]`.

### 3. analyst-ratings + earnings + sec

11 files. **47 violations.** 25× bare `text-xs/sm`; 6× `text-[10px]/[11px]`; pervasive
`py-1.5` table rows (off-grid — comes from DataTable's row padding, fix centrally);
**inputs split h-8 (analyst) vs h-9 (earnings)**; `gap-0.5` (2px) in SEC panel header;
`FilingViewer` heavy bare-Tailwind + `text-[12px] leading-relaxed`. Tables already on DataTable.

### 4. portfolio + macro + quant

8 files. **57+ type-scale violations** (the densest). `text-[10px]` and bare `text-xs`
everywhere; quant readouts use `text-3xl`/`text-2xl`/`text-lg`/`text-sm` (→ hero/overview/…);
**control chaos: portfolio h-9, quant fields h-8, instrument rows h-7, payoff toggle h-7**;
`PortfolioPanel` inputs `rounded-md`; `MacroChart`/`MacroSeriesPicker` `rounded-md`/`rounded-full`

- `px-2.5 py-1.5`. YieldCurve output table numerics not right-aligned/tabular. Font: compliant
  (all mono) — these are scale/control fixes.

### 5. chart + research (brief block)

`ChartPanel`, `research/BriefPanel`, `research/brief-blocks`. Research mixes bare
`text-xs/sm/base/xl` + arbitrary `text-[9px]/[12px]`; chart off-grid `gap-1.5/py-1.5/gap-0.5`

- `rounded-[3px]`/`rounded-md`/`rounded-full`; **brief metric grid + price line collisions
  (§3)**. Brief body should adopt `text-prose` (16/1.6) for synthesis; metric cards sharp.

### 6. notes editor

`NotesPanel`, `NotesToolbar`. **9 high.** Slash/Wiki popups `shadow-lg` (§2) + viewport clip
(§3); containers `rounded-md`; editor `min-h-[200px]` arbitrary; **export status line
`font-mono`** (chrome should be the global mono, not an opt-in); ToolbarButton `size-8` ok →
24/32 ladder; slash/wiki items `h-9`; ScopeChip/SymbolChip `px-2 py-1`. Engine (Tiptap) is
correct — this is chrome only. (Brief: add visible formatting toolbar — already partly via
`NotesToolbar`; verify H1/H2/H3/bold/italic/list/quote/code/link/wikilink present.)

### 7. chat composer + agent dock (brief's named #2)

`ChatSidebar`, `AgentHud`, `AgentsRail`, `BudgetConfig`, `PlanView`, `ProposedChangesReview`,
`ResearchActivity`, `SuggestionChips`, `Mention/SlashCommandPicker`, `AgentDock`.
**Most fragmented control sizing in the app:** composer input `min-h-[52px]` + **send
`size-10` (40px) `rounded-full` detached → 12px mismatch**; composer input **`font-sans`**
(violates mono); mode/lens/autonomy/provider selects `h-9 rounded-md`; answer input `h-5`;
budget input `h-7`; **dangerously small `text-[0.55rem]`/`[0.6rem]`/`[0.65rem]`** across
PlanView/ProposedChanges/ResearchActivity/AgentsRail. → Rebuild composer as ONE unit
(field + inset controls + 32px amber send aligned inside, `rounded-control`); all selects to
32px; sweep micro-rems to `text-micro`/`text-caption`.

### 8. news + marketplace + plugin-manager

`NewsFeedPanel`, `MarketplacePanel`, `PluginManagerPanel`. 29 arbitrary `text-[…]` + 10 bare
Tailwind; `MarketplacePanel:237,310` **`text-[0.55rem]` (8.8px illegible)**; `py-2.5` off-grid;
container `rounded-md`; plugin-manager empty state overflow (§3).

### 9. agent-builder + node-editor

`AgentBuilderPanel`, `form`, `NodeEditorPanel`, `VystedNode`, `node-palette`,
`workflow-run-overlay`, `workflow-save-dialog`. Strong baseline (mono + scale mostly).
`VystedNode` **`shadow-sm` + amber glow** (§2); `rounded-control` misapplied to badges; run
overlay absolute overlap (§3); some `rounded-md` containers.

### 10. broker-connect + safety + platform + backtest

`Broker{ConnectPanel,OrderEntry,ReadsSection}`, `kite-static-ip-banner`, `safety/{AuditLogViewer,
DisclaimerFlow,OrderConfirmationDialog}`, `platform/WorkspaceDialog`, `backtest/{Panel,
ResultView,strategy-picker}`. Extensive `text-[9px]/[10px]/[0.6rem]`; **`font-serif text-sm/xl`
(sans leak)**; `py-2.5` off-grid; container `rounded-md`; **backtest trade table mid-number
truncation (§3, worst)**; input h-7 amid h-6/8/9/10 buttons. ⚠️ Safety/broker LOGIC is Tier-1 —
**touch only className/markup, never the §6.5 confirm-gate, audit, kill-switch, or broker ABC.**

### 11. core: CommandPalette / DataTable / DataBadges / EmptyState / StatusChrome / ui

`StatusChrome` `text-[11px]` → `text-micro`; **`ui/button.tsx` the linchpin (RC-3, §2)**;
`ui/dialog.tsx` `shadow-lg` (§2); `DataTable` row padding `py-1.5` (the off-grid source for
every migrated table — fix here, propagates); `DataBadges` `px-1.5 py-0.5 text-[11px]`;
`CommandPalette` — verify `group-heading-style` resolves (globals.css defines it), descriptions
ellipsis-truncate not hard-clip, "notes"→Notes fixed query. `EmptyState` correct — reuse.

### 12. core: SettingsPanel / OnboardingFlow / OnboardingBanner / KeyEntryDialog / PanelHost

`SettingsPanel` 18+ `text-[0.6rem/0.65rem/0.7rem]`; `OnboardingFlow` `px-7 py-7 gap-5 py-10
rounded-[2px]`; **`KeyEntryDialog` `shadow-2xl` ×2 (§2)** + tight `gap-0 p-0`; pervasive
`font-serif` + bare Tailwind. `PanelHost` is layout-critical (dockview) — className only.

---

## §5 — Sequencing (how the worklist collapses)

1. **Token foundation** (Task 3a): RC-1 (mono default), RC-4 (`--radius-panel`→0). Re-skins the
   whole app's font + container radius in 3 files.
2. **`ui/button.tsx`** (Task 4, first): RC-3 + RC-5. Propagates control height/radius/scale to
   every button consumer.
3. **`DataTable.tsx` + `dialog.tsx`** (Task 4): fixes table row padding (every migrated table)
   and dialog shadow (every dialog) centrally.
4. **No-shadow hitlist** (§2): 5 remaining files after button/dialog.
5. **Type-scale sweep** (RC-2): mechanical `text-[…]`→named across all surfaces.
6. **Collision hitlist** (§3) + the three named surfaces (equity table, composer, ⌘K): hand work.
7. **Lead consistency reconciliation** across the whole app, then Phase 2 Computer-Use hunt.

Raw findings (all 542, file:line) — sweep `wf_532b5e22-a54`, transcript under the session
`workflows/` dir. Re-grep per surface during Phase 1 for the exact line list.
