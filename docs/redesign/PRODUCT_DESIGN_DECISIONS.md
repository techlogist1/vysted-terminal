# Vysted R4 — Product Design Decisions (the taste authority)

> **Status:** RATIFIED for the R4 session-3 build. This is the single document every
> teammate obeys so the result is ONE coherent look, not six interpretations.
> **Ground truth:** the reference screenshots in `docs/redesign/references/`
> (`perplexity-home.png`, `cursor-agent.png`, `cursor-plan.png`). When this doc and a
> screenshot disagree, the screenshot wins and this doc is corrected. When this doc and a
> UI-rigor skill default disagree, **this doc wins** (skills supply execution rigor —
> contrast math, states, a11y — never the taste).
>
> **What changed vs the prior build (the two measured failures, reversed):**
>
> 1. The app went **cold** (cold-zinc OKLCH hue 264 + cool-indigo accent `#7e88e8`). The
>    references are **warm near-black, no blue**. → Warm Graphite ramp + a single muted
>    **amber** accent.
> 2. The app **shrank** (composer `h-8`/12px, pills at **9.6px**, header `h-9`). The
>    references **breathe**. → A comfortable control scale; everything grows.
>
> The design language formerly named "Cold Instrument" is renamed **"Warm Graphite."**
> (Do not use the words _clay_, _espresso_, or _warm instrument_ anywhere — they collide
> with the stale-code grep gate and name a different, retired system.)

---

## 0. Values extracted from the references (measured pixels, not guesses)

Sampled with a stdlib PNG decoder over the saved references:

| Surface           | Perplexity                      | Cursor                                         | Conclusion                |
| ----------------- | ------------------------------- | ---------------------------------------------- | ------------------------- |
| Deep background   | `#181614` (R−B **+4**)          | `#121108` (R−B **+10**)                        | warm near-black, no blue  |
| Panel / card      | `#1f1d1b`                       | `#1a1814`                                      | warm graphite ≈ `#1a1814` |
| Raised input/card | —                               | `#43413d` / `#453e35`                          | warm, clearly delineated  |
| **Accent**        | barely used (one small control) | **`#c08030`** (R−B **+144**, dominant cluster) | a single muted **amber**  |

The references are **warm** at every sampled point (R ≥ B by +4…+16). The only saturated
accent in Cursor is the amber on the active "Plan" pill and the "Continue" button. That is
the entire accent budget.

---

## 1. The neutral ramp — "Warm Graphite" (token name: `charcoal-*`)

OKLCH hue ≈ **70–80** (warm, faint yellow-brown), chroma ≤ 0.008, perceptually-even steps.
Every value is warm (R ≥ G ≥ B, small deltas). **Token NAMES stay** (`charcoal-*`) so the
~92 files referencing them re-skin with zero edits — only VALUES change.

| Token               | Hex                 | Role                                                     |
| ------------------- | ------------------- | -------------------------------------------------------- |
| `charcoal-950`      | `#0e0d0b`           | app root well (deepest)                                  |
| `charcoal-925`      | `#131210`           | header fascia, tab strip                                 |
| `charcoal-900`      | `#1a1814`           | **panel / card surface** (the anchor)                    |
| `charcoal-875`      | `#211e19`           | popover / active tab / hover surface                     |
| `charcoal-850`      | `#29251f`           | raised inset — input fill, node bg                       |
| `charcoal-800`      | `#312c25`           | muted / secondary surface                                |
| `charcoal-700`      | `#39332b`           | borders / inputs / dividers                              |
| `charcoal-600`      | `#4a443a`           | strong border / disabled fg                              |
| `charcoal-500`      | `#79736a`           | **tertiary** text — faint label, kbd, process/meta lines |
| `charcoal-400`      | `#a8a095`           | **secondary** text — muted foreground                    |
| `charcoal-300`      | `#d3cec5`           | secondary-bright text                                    |
| `charcoal-200`      | `#e9e4dc`           | bright secondary / chart text                            |
| `charcoal-100`      | `#f5f2ec`           | **primary** text / foreground (warm near-white)          |
| `lume`              | `#f7f5f0`           | peak near-white (active tab text, peak readouts)         |
| `brass-*`, `sage-*` | aligned to the ramp | quiet secondary neutrals (see token file)                |

---

## 2. The accent — a single muted amber (token name: `amber-*`)

OKLCH hue ≈ **65–75** (amber/gold), restrained — earthy gold, **NOT neon, NOT pure
orange**. Modeled on Cursor's `#c08030`. Used on **≤ 5% of pixels** and **at most one or two
interactive elements at a time** (an active pill, a primary CTA, the focus ring, the active
tab tick). NEVER a background wash, NEVER a gradient, NEVER a glow.

| Token       | Hex       | Role                                               |
| ----------- | --------- | -------------------------------------------------- |
| `amber-200` | `#f0d8ac` | faint tint / selection fill                        |
| `amber-300` | `#e9bd80` | hover-bright / accent **text** on dark             |
| `amber-400` | `#d89a4e` | **BRAND / primary / default accent**               |
| `amber-500` | `#c0802f` | pressed / active sash / selected (= Cursor's fill) |
| `amber-600` | `#875720` | deep border / dense accent                         |

**Lockstep (FR-030) — change ALL THREE in one commit or the canvas drifts:**

- `styles/tokens.css` `--color-amber-*` (above) + the `charcoal-*` ramp (§1).
- `src/app/globals.css` `--accent-rgb: 216 154 78;` + every fallback hex.
- `src/lib/chart-theme.ts` `ACCENT_CORAL = #d89a4e`, `ACCENT_CORAL_BRIGHT = #e9bd80`,
  `ACCENT_CORAL_DEEP = #875720`, `ACCENT_CORAL_RGB = "216, 154, 78"`, and the
  `CHART_SURFACE…CROSSHAIR` neutrals re-valued to the Warm Graphite ramp.

**Signals (unchanged — the only other saturated colors, P&L only):** positive `#3fbf6f`,
negative `#e5544b`, warning `#e0a13a`. Warning stays _yellower_ than the brand amber and
only ever appears as a labelled badge ("STALE"/"PAPER"), so it does not read as the accent.

---

## 3. NO GLOW — mandatory, non-negotiable

- **Remove** the `body` ambient `radial-gradient(... rgb(var(--accent-rgb)/0.03) ...)` in
  `globals.css`. The canvas is a **flat** warm field. (The prior build kept a faint indigo
  glow here; it goes completely.)
- **Allowed:** a 1px hard accent border (`box-shadow: 0 0 0 1px …`), the inset active-tab
  tick (`inset 0 -2px 0 …`), and the quiet 1px bezel (`--bezel-shadow`, no blur). These are
  borders, not glow. Re-color their fallback hexes to amber.
- **Forbidden anywhere:** any `box-shadow`/`filter`/`drop-shadow` with a blur radius > 1px
  used as a halo/bloom; any radial/linear/conic gradient used as an ambient light or fill on
  chrome, cards, or the canvas; anything named glow/halo/bloom/neon/ambient.

---

## 4. Three contrast tiers — via weight, opacity, spacing, NEVER color

The current app is flat low-contrast grey-on-black with no hierarchy. Give it hierarchy
_without adding color_ (Cursor dims "Read X" / "Thought 6s" / "Searched Y" against
full-contrast output — same hue family, different weight/opacity):

| Tier          | Token                    | Weight             | Use                                                                   |
| ------------- | ------------------------ | ------------------ | --------------------------------------------------------------------- |
| **Primary**   | `charcoal-100` `#f5f2ec` | 400–510            | the content — brief prose, answers, prices, headings                  |
| **Secondary** | `charcoal-300/400`       | 400                | supporting labels, table secondaries, descriptions                    |
| **Tertiary**  | `charcoal-500` `#79736a` | 400, often smaller | process/meta — "Read …", "Thought …", timestamps, kbd, source domains |

Headings lead by **size + weight** (`--font-weight-heading` 590), not color. Accent text
(`amber-300`) is reserved for the _active/selected_ affordance, not general emphasis.

---

## 5. Sizing & rhythm — the references BREATHE (grow everything)

The prior build shrank controls into capsules. Restore comfortable sizing. **Minimum
interactive text is 12px**; primary inputs are 14px; only dense data tables stay at 13px.

**Control height scale:** `sm = 32px` · `md = 40px` · `lg = 48px`. (Most chrome controls
were 20–32px — lift them.)

| Surface                            | Was                      | Target                                                                             |
| ---------------------------------- | ------------------------ | ---------------------------------------------------------------------------------- |
| Header / top bar                   | `h-9` (36)               | **`h-12` (48)**, brand mark larger, comfortable `gap`                              |
| **Composer input** (the hero)      | `h-8`, 12px, `px-2`      | **min-h ~52px multiline**, 14px, `px-4 py-3`, `rounded-lg`                         |
| Composer toolbar (mode/model/send) | 9.6–10.4px pills         | 12px, pill `h-8`, `px-3`, comfortable gap                                          |
| Send button                        | `size-8` (32)            | **`size-10` (40)**                                                                 |
| ⌘K palette                         | `max-w-xl`, default rows | **`max-w-2xl`**, input `h-12` 14px, rows `py-2.5` 14px, group headers 11px tracked |
| Ticker search / Load               | `w-24`, mixed            | `w-32`+, `h-9`, 14px                                                               |
| Pills / chips / capsules           | `text-[0.6rem]` `py-0.5` | **`text-xs` (12px)** min, `px-2.5 py-1`, `rounded-md`                              |
| Data provenance badges             | `py-[1px]` 10px          | `py-0.5`, `text-[11px]`                                                            |
| dockview tabs                      | 11px                     | 12px (dense — modest bump)                                                         |
| Mention/slash pickers              | 11.2px                   | 13–14px, `py-2`                                                                    |

Spacing draws from the token scale: component padding from {8, 12, 16}, section gaps from
{16, 24, 32}. No raw off-scale values (`px-[7px]`, `gap-2.5`) in new/changed code.

**Caveat (this is a finance terminal, not a landing page):** grow the _interaction_ and
_chrome_ surfaces to reference generosity. Do not bloat dense data grids — tables stay at
the 13px body size with their existing row rhythm. "Breathe" means the composer, palette,
header, buttons, pills, empty states, and brief reading column — the surfaces you touch and
read — not the numeric tables.

---

## 6. Borders, radius, elevation

- **1px borders**, quiet: `charcoal-700` (`#39332b`) for structural, the `--hairline`
  (zinc @ ~14%) for fine dividers. Cards are clearly delineated but calm.
- **Radius:** `--radius-control` `0.25rem` for small controls; `--radius-panel` `0.375rem`
  for cards/panels; the composer and palette may use a slightly larger `rounded-lg`
  (`0.5rem`) to read generous, matching the references.
- **Elevation = a luminance step + a 1px border**, never a blurred shadow. A popover sits
  on `charcoal-875` with a `charcoal-700` border. That is the whole elevation system.

---

## 7. Typography

Clean sans chrome (Inter-class UI sans over a mono data face — the references use clean
sans; the references win over the skill's "avoid Inter" default). Clear weight contrast:
body 400, labels 510, headings 590. Numerics: tabular figures + slashed zero (already set).
Brief reading prose uses `--leading-prose` (1.6) and a comfortable measure.

---

## 8. Empty states — designed surfaces, never dead voids

Much of what read as "cheap" was abandoned-looking empty panels. **Every** empty state is a
composed placeholder, centered in its panel:

```
            ◇  (quiet icon, charcoal-500/600, ~22–26px)
      <headline>            (text-panel-title, charcoal-200, weight 510)
      <one calm line>       (text-caption, charcoal-500)
      [ optional single CTA ]   (ghost/outline button, amber only if primary)
```

No spinners-as-empty-state; no bare `<p class="text-charcoal-400">No data.</p>`. Pattern
ships as one shared `<EmptyState icon headline hint cta?/>` component and replaces every
dead-text surface (analyst tables, broker connect, screener universe, etc.).

The composer empty state additionally shows **teach-the-agent suggestion chips** (§ feature
spec) — Perplexity-style "try this" capsules below the input.

---

## 9. Component-level decisions (the recurring ones)

- **Active pill / selected tab:** amber text (`amber-300`) or amber tick; the _fill_ stays a
  neutral luminance step (`charcoal-875`). Only a _primary CTA_ gets an amber **fill** with
  dark (`charcoal-950`) text (like Cursor's "Continue"). At most one amber-filled element
  visible at a time.
- **Focus ring:** 1px `amber-400`, offset 1px. Selection: `amber` @ 30%.
- **Scrollbars:** quiet warm-neutral rail; thumb lifts to amber @ ~55% on hover.
- **Icons:** lucide, stroke ~1.5–1.75, sized to the control; tertiary tint by default,
  primary on hover.
- **Motion:** keep the existing tiers (micro 120 / default 180 / entrance 240 / exit 160);
  honor reduced-motion. No new motion vocabulary.

---

## 10. Acceptance (how we know it matches)

A surface passes when, placed beside its reference at the same zoom: (a) the background reads
**warm**, not blue; (b) controls are at reference generosity, not shrunken; (c) there are
visibly **three** text tiers; (d) accent appears on **0–2** elements, amber, never neon;
(e) **no glow** anywhere; (f) empty states look intentional. A fresh reviewer who has seen
only the references and the app screenshots should place them in the same family.

---

# R5 addendum — the ENFORCED component patterns (§11–§16)

> R5 finding: §1–§10 are correct but were **not enforced** — components rolled their own tables,
> editor, palette, and empty states with off-scale values. §11–§16 turn the recurring surfaces into
> ONE shared, enforced pattern each. When a surface and its pattern below disagree, the pattern wins.
> Build the primitive once (`Phase 0`), consume it everywhere.

## 11. The table pattern — ONE `DataTable`, no hand-rolled grids

Every tabular/numeric surface (equity-overview statements, screener, analyst, earnings, SEC, portfolio,
watchlist) renders through `src/components/DataTable.tsx`. No more per-panel `<table>` markup.

- **Numbers are right-aligned, `tabular-nums`, single-formatter.** All numeric cells use
  `text-right whitespace-nowrap` + tabular figures (already global). Every value runs through the single
  `src/lib/format.ts` suite (`formatMoney`, `formatCompactMoney`, `formatPercent`, `formatPrice`,
  `formatUnit` K/M/B/T) — **never** a per-panel formatter, **never** an unsuffixed raw number.
- **Header row:** `text-micro` (11px) · weight-510 · `charcoal-400` · uppercase · `px-3 py-1.5`. Numeric
  headers are `text-right` too. Sortable headers add an `aria-sort` + a quiet caret; the active sort key
  is the **only** amber affordance in the table.
- **Body row:** `text-body` (13px) · weight-400 · `px-3 py-1.5` (one rhythm for every dense table). Primary
  values `charcoal-100`; supporting/secondary values `charcoal-400`; subtotals/meta `charcoal-500`.
- **Period / column headers** are first-class: financial statements show explicit period columns
  (`TTM`, `FY2025`, `FY2024`…), right-aligned to their numeric column.
- **Grouped sections** (Valuation / Profitability / Financial Health / …) via a section-header row
  (`text-micro` `charcoal-500`), not ad-hoc spacing.
- **Missing values** render `—` (`charcoal-600`); a row/section that is wholly null collapses to a single
  muted note (`text-caption charcoal-500`), never a wall of dashes.
- **Never** expose snake_case — labels come from a curated map (e.g. `FIELD_GROUPS`).

## 12. The editor pattern — Notes is a real editor with a visible toolbar

Notes uses the **already-installed Tiptap v3** (no editor swap). The chrome is the work.

- A **visible formatting toolbar** (`h-12`, groups separated by `gap-4`): Headings (H1/H2/H3) · Inline
  (bold, italic, code) · Lists (bullet, numbered, task) · Blocks (blockquote, link) · `[[wikilink]]`.
  Each button: `editor.isActive(x)` drives an **amber** active state (text/tick, not a fill); the action is
  `editor.chain().focus().toggleX().run()`. Icons lucide, 16–18px, tertiary default → primary on hover.
- **Live markdown** renders in a `.notes-prose` block locked to the system scale (h2 = `text-section` 18px,
  body = `text-body` 13px, code = mono) — never Tailwind's default 16px prose.
- Popovers (slash, wikilink) use a **1px `charcoal-700` border, no `shadow-lg`** (no-glow). Menu rows `h-9`,
  `text-caption` title + `text-micro` hint.
- Preserve: MD/PNG/PDF export, atomic persistence, wikilinks, slash commands.

## 13. The empty-state pattern — `EmptyState`, fills its container

Use the existing `src/components/EmptyState.tsx` (don't rebuild). Two jobs:

- **Generic dead surfaces** (palette no-results, sparse tables, disconnected panels): the §8 stack
  (quiet icon `charcoal-500` ~22px → `text-panel-title` headline `charcoal-200/510` → one `text-caption`
  `charcoal-500` line → optional single ghost CTA, amber only if primary). A dense `secondary` variant
  (smaller icon, `text-caption`) for inline/secondary panels.
- **Hero empty states** (chat dock, first-run composer) **fill the column** — centered identity block, then
  a **distributed** suggestion set (teach-the-agent chips) that occupies the remaining height. **No
  `justify-center` floating a small block in a tall column** (the R4 dead-void failure). Measure: <20%
  unused vertical space vs the Perplexity reference.

## 14. The composer pattern — input + send are ONE unit

- Input `min-h-[52px]` · `text-sm` (14px) · `rounded-lg` · form `p-4`, `gap-3`. Send `size-10` (40px),
  `rounded-full`, amber fill with `charcoal-950` glyph (the one primary CTA). The pair reads balanced
  (≈1 : N where the send visually anchors the right edge), never "big rectangle + tiny arrow."
- The input reserves a **left inset** (`pl-11`) so a persona/agent indicator never overlaps the placeholder.
  Placeholder is `charcoal-500` (tertiary).
- The control toolbar (mode / lens / provider / model) lifts to `h-9`, `gap-2`; labels are tertiary
  (`charcoal-500`), values secondary. Chrome stays dense (mono `text-xs` ok for data selectors) but on-scale.

## 15. The palette pattern — grouped, truncating, useful-when-empty

- Group headers use the now-defined `.group-heading-style` (`text-micro` · `charcoal-500` · uppercase ·
  0.1em). Groups: Recent · Suggested (empty query) → Agents · Actions · Panels · Symbols (with query).
- Rows: `icon · title (truncate min-w-0) · muted description (truncate) · right kbd/group`. Text **always**
  truncates with ellipsis inside the row; it **never** hard-clips past the panel edge, at any width.
  Palette `max-w-2xl`, input `text-body` sans (not mono), rows `py-2.5`.
- Empty query → `EmptyState`-style recent + suggested actions, **not** an agent dump. Keep the fixed-query
  symbol filter.

## 16. Enforcement — the binary off-scale audit (the gate for "one system")

**The scale is law. New/changed code uses named utilities + tokens only.**

- **Type scale (the only sizes):** `text-micro` 11 · `text-caption` 12 · `text-body` 13 · `text-panel-title`
  15 · `text-section` 18 · `text-overview` 22 · `text-hero` 28. Weights: body 400 · label 510 · heading 590.
  **Minimum interactive text = 12px.** Dense data tables = `text-body` 13.
- **Spacing scale (the only steps):** 2 · 4 · 6 · 8 · 12 · 16 · 24 · 32 · 48 · 64 (`--spacing-*`). Component
  padding from {6, 8, 12}; section gaps from {16, 24, 32}.
- **Control heights:** `sm` 32 · `md` 36–40 · `lg` 48. Send `size-10`. No `h-7`/`h-8` chrome buttons in
  changed code (data selectors may stay dense but on-scale).
- **Radius:** `radius-control` 4px · `radius-panel` 6px · composer/palette may use `rounded-lg` 8px.
- **Binary audit (must be zero in every changed file):**
  - `rg -n 'text-\[' <file>` → **0** (use a named util).
  - `rg -n '\b(gap|p|px|py|pt|pb|pl|pr|m|mx|my|mt|mb|ml|mr)-(2\.5|3\.5|1\.5|0\.5|5|7|9|10|11)\b' <file>`
    reviewed → only values that map to a scale step survive; off-grid (2.5/3.5/7/10…) → **0**.
  - `rg -n 'rounded-\[' <file>` → **0**.
  - `rg -n '#[0-9a-fA-F]{3,6}' <file>` in components → **0** (tokens only).
  - `rg -n 'shadow-(md|lg|xl|2xl)|drop-shadow|blur-' <file>` → **0** (no-glow).
- An undefined utility class (e.g. the old `.group-heading-style`) is a **defect** — Tailwind won't warn,
  so grep for referenced-but-undefined classes when a header/label looks unstyled.
