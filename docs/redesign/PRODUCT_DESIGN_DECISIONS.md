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
