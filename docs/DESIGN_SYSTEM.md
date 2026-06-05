# Vysted Terminal — Design System (R4 "Warm Graphite")

R4 experience rebuild. Replaces every prior system — the retired "Claude after dark"
espresso/coral system (#1a1512 base, #d97757 accent, Fraunces) and the interim
warm-instrument clay variant — both of which are referenced in this file only to
name what was retired. The authoritative values are **always** the live source files;
this document is a faithful mirror, not a substitute.

**Primary sources of truth (read these first):**

- `styles/tokens.css` — the Tailwind 4 `@theme` block; every token name and value.
- `src/app/globals.css` — shadcn semantic mapping, `--accent-rgb`, chrome primitives,
  dockview theme, NO-GLOW rule.
- `src/lib/chart-theme.ts` — canvas palette lockstep (FR-030); the only file that
  declares hex for chart/drawing surfaces.
- `docs/redesign/PRODUCT_DESIGN_DECISIONS.md` — the taste authority; the pixel
  measurements and acceptance criteria from the reference screenshots.

---

## The concept

A **perceptually-even warm-graphite neutral ramp** (OKLCH hue ~75, chroma <= 0.008,
R >= G >= B at every step — a faint warm cast, never blue, never flat black, never
warm-orange) carrying a **single muted amber accent** (OKLCH hue ~70, an earthy gold
modeled on the reference apps' dominant cluster at `#c08030`). The accent lights at
most 5% of pixels and never more than two interactive elements at once. Everything
else is warm neutral — the P&L signals (muted green / muted red) are the only other
saturated colors, and they appear only in data columns.

In one line: **a flat warm-graphite field with one amber signal and luminance-only
hierarchy — density without noise.**

## Deliberately NOT

- **No cold neutrals.** Every dark is warm (R >= G >= B). No slate, no zinc, no blue.
- **No glow, no bloom, no ambient gradient.** The body is a flat field. Elevation is
  expressed as a luminance step + a 1px border, nothing else.
- **No second accent.** The retired sage-green accent is gone. Amber is the only hue
  in chrome. Signal colors (green/red) are data, not chrome.
- **No skeuomorphic chrome.** Retired with the INSTRUMENT system: brass bezels, gauge
  ticks, phosphor bloom, CRT grain, beveled panel edges.

---

## Token naming caveat — read before touching colors

The token **names** (`charcoal`, `amber`, `brass`, `sage`, `lume`) are kept from
retired systems so the ~92 files that reference them as Tailwind classes re-skin with
zero edits. Only the **values** changed. The names are therefore historical and must
not be read literally:

| Token family | Renders as                              |
| ------------ | --------------------------------------- |
| `charcoal-*` | Warm Graphite neutral ramp              |
| `amber-*`    | Muted amber accent (the only accent)    |
| `brass-*`    | Warm-neutral secondaries (ramp-aligned) |
| `sage-*`     | Warm-neutral secondaries (ramp-aligned) |
| `lume`       | Warm near-white                         |

Read the role column. A project-wide rename is a documented future cleanup item; it
was not done here to avoid churning ~92 files.

---

## Tokens

### Warm Graphite neutral ramp (`charcoal-*`)

OKLCH-derived, hue ~75, chroma <= 0.008, perceptually even steps. Every value is
warm (R >= G >= B, small deltas). Source: `styles/tokens.css`.

| Token          | Hex       | Role                                             |
| -------------- | --------- | ------------------------------------------------ |
| `charcoal-950` | `#0e0d0b` | App root well (deepest)                          |
| `charcoal-925` | `#131210` | Header fascia, tab strip                         |
| `charcoal-900` | `#1a1814` | Panel / card surface (the visual anchor)         |
| `charcoal-875` | `#211e19` | Popover / active tab / hover surface             |
| `charcoal-850` | `#29251f` | Raised inset — input fill, node background       |
| `charcoal-800` | `#312c25` | Muted / secondary surface                        |
| `charcoal-700` | `#39332b` | Borders / inputs / dividers                      |
| `charcoal-600` | `#4a443a` | Strong border / disabled foreground              |
| `charcoal-500` | `#79736a` | Tertiary text — faint label, kbd, process/meta   |
| `charcoal-400` | `#a8a095` | Secondary text — muted foreground                |
| `charcoal-300` | `#d3cec5` | Secondary-bright text                            |
| `charcoal-200` | `#e9e4dc` | Bright secondary / chart axis text               |
| `charcoal-100` | `#f5f2ec` | Primary text / foreground (warm near-white)      |
| `lume`         | `#f7f5f0` | Peak near-white — active-tab text, peak readouts |

### Muted amber accent (`amber-*`)

OKLCH hue ~70 (amber/gold), restrained — earthy gold, not neon, not pure orange.
Five states from faint tint to deep border. Source: `styles/tokens.css`.

| Token       | Hex       | Role                                 |
| ----------- | --------- | ------------------------------------ |
| `amber-200` | `#f0d8ac` | Faint tint / selection fill          |
| `amber-300` | `#e9bd80` | Hover-bright / accent text on dark   |
| `amber-400` | `#d89a4e` | **BRAND / primary / default accent** |
| `amber-500` | `#c0802f` | Pressed / active sash / selected     |
| `amber-600` | `#875720` | Deep border / dense accent           |

The `--accent-rgb` in `globals.css` is `216 154 78` (the RGB decomposition of
`#d89a4e`). All three files — `tokens.css`, `globals.css`, and `chart-theme.ts` —
must be updated in lockstep whenever the accent changes (see FR-030 below).

### Warm-neutral secondaries (`brass-*`, `sage-*`)

Ramp-aligned warm neutrals. No metal, no second accent. `brass-300` (`#a8a095`) is
the `.hud-label` legend tone. `sage-*` values are aligned to the same warm-graphite
ramp and used for secondary comparison data series so they never compete with the
amber accent.

### Signal colors

The only other saturated colors in the system. Never used as background fills;
reserved for P&L data columns and caution badges.

- `--color-positive` `#3fbf6f` — gains / muted green, luminance-matched to loss.
- `--color-positive-bright` `#4ade80` — gain flash peak.
- `--color-negative` `#e5544b` — losses / muted red, luminance-matched to gain.
- `--color-negative-bright` `#f87171` — loss flash peak.
- `--color-warning` `#e0a13a` — caution badge (stale data, paper-vs-live, kill-switch
  armed). Yellower than the brand amber and only ever appears as a labelled badge, so
  it does not read as the accent.

**Amber-vs-loss separation note.** The amber brand accent (hue ~70) and the negative
loss color (hue ~8, a muted red) are separated on two axes — different hue family and
different luminance — and do not risk merging in a populated P&L table. Verify on a
real watchlist with prices alongside the active composer or focus ring.

---

## Three contrast tiers — weight and opacity, never color

Hierarchy is expressed through font weight, opacity/tone, and size alone. No
additional accent colors are introduced to signal importance.

| Tier          | Token                    | Weight           | Use                                                   |
| ------------- | ------------------------ | ---------------- | ----------------------------------------------------- |
| **Primary**   | `charcoal-100` `#f5f2ec` | 400–510          | Content — prose, prices, answers, headings            |
| **Secondary** | `charcoal-300/400`       | 400              | Supporting labels, table secondaries, descriptions    |
| **Tertiary**  | `charcoal-500` `#79736a` | 400, often small | Process/meta — "Read …", "Thought …", timestamps, kbd |

Headings lead by size + weight (`--font-weight-heading` 590), not by color. Amber
text (`amber-300`) is reserved for the active/selected affordance only, not for
general emphasis. Source: `docs/redesign/PRODUCT_DESIGN_DECISIONS.md` §4.

---

## Type scale

R4 introduces a named type scale defined in `styles/tokens.css` as Tailwind 4
`@theme` values and `@utility` classes. Components use `text-body` / `text-caption`
/ `text-panel-title` instead of ad-hoc `text-[11px]`.

| Utility            | Size | Line-height    | Weight | Use                            |
| ------------------ | ---- | -------------- | ------ | ------------------------------ |
| `text-micro`       | 11px | heading (1.3)  | 510    | HUD label (uppercase, +0.10em) |
| `text-caption`     | 12px | body (1.5)     | 400    | Caption, secondary, kbd chips  |
| `text-body`        | 13px | body (1.5)     | 400    | Body + table base              |
| `text-panel-title` | 15px | heading (1.3)  | 510    | Panel title                    |
| `text-section`     | 18px | heading (1.3)  | 590    | Section head                   |
| `text-overview`    | 22px | display (1.25) | 590    | Overview / brief head          |
| `text-hero`        | 28px | hero (1.2)     | 590    | Rare hero (first-run only)     |

Minimum interactive text is 12px; primary inputs are 14px; dense data tables stay
at 13px. Source: `styles/tokens.css` type-scale block and `PRODUCT_DESIGN_DECISIONS.md` §5.

**Font faces.** The `--font-serif` slot name is historical. It now carries the
**Inter-class UI sans** (loaded via `next/font` into `--font-display`), not a serif.
`--font-mono` carries **JetBrains Mono** for data/code with global `tabular-nums` +
slashed-zero. The `h1–h3` rule in `globals.css` resolves `--font-serif` → the UI
sans, so headings and body share the same grotesque face at different weights.

---

## Spacing and radius rhythm

### Spacing (source: `styles/tokens.css`)

4px base, 8px rhythm. Component padding from {6, 8, 12}px; section gaps from
{16, 24, 32}px. Raw off-scale values (`px-[7px]`, `gap-2.5`) are forbidden in
new or changed code.

Named spacing tokens: `--spacing-1` (2px) through `--spacing-32` (64px), following
a 2/4/6/8/12/16/24/32/48/64px progression.

### Radius (source: `styles/tokens.css`)

`--radius-control: 0.25rem` for small controls. `--radius-panel: 0.375rem` for
cards and panels. The composer and command palette may use `rounded-lg` (0.5rem) to
match the reference generosity. The shadcn `--radius` token tracks `--radius-panel`.

---

## NO-GLOW rule (mandatory, non-negotiable)

The body background is a **flat warm-graphite field** (`background-image: none` in
`globals.css`). There are no ambient radial gradients, no bloom, no blurred drop
shadows used as halos, and nothing named glow/bloom/halo/neon/ambient.

**Allowed border treatments:**

- A 1px hard amber border: `box-shadow: 0 0 0 1px var(--color-amber-400)`.
- The inset active-tab tick: `box-shadow: inset 0 -2px 0 var(--color-amber-400)`.
- The quiet 1px bezel: `--bezel-shadow: inset 0 1px 0 rgb(250 248 244 / 0.04), 0 1px 2px rgb(0 0 0 / 0.4)`.

These are borders expressed as `box-shadow`, not glow. The blur radius is 0px or 2px
max (the 2px shadow in `--bezel-shadow` is a drop shadow for depth, not a halo).

**Forbidden:** any `box-shadow` / `filter` / `drop-shadow` with a blur radius > 2px
used as a halo or bloom; any radial/linear/conic gradient as an ambient fill on
chrome, cards, or the canvas.

**Elevation model:** a popover sits on `charcoal-875` with a `charcoal-700` border —
that is the complete elevation system. Luminance step + 1px border; no blurred shadow.

Source: `globals.css` `:root` block (no `--glow-*` primitive defined) and
`PRODUCT_DESIGN_DECISIONS.md` §3.

---

## Empty-state pattern

Dead-text empty panels ("No data.") are forbidden. Every empty state is a composed
placeholder, centered in its panel:

```
        (quiet icon, charcoal-500/600, ~22–26px)
  <headline>            (text-panel-title, charcoal-200, weight 510)
  <one calm line>       (text-caption, charcoal-500)
  [ optional single CTA ]   (ghost/outline button, amber only if primary action)
```

Implemented as a shared `<EmptyState icon headline hint cta? />` component.
Source: `PRODUCT_DESIGN_DECISIONS.md` §8.

---

## Canvas-tokens lockstep rule (FR-030)

Canvas elements (`<canvas>`) cannot read CSS custom properties. The canvas palette
is mirrored once in `src/lib/chart-theme.ts`. When any token changes:

1. Update `styles/tokens.css` — the `--color-*` value.
2. Update `src/app/globals.css` — `--accent-rgb` (if the amber accent changed).
3. Update `src/lib/chart-theme.ts` — the matching exported constant.

Updating fewer than all three in one commit causes the canvas to drift off-palette.
The export names in `chart-theme.ts` (`ACCENT_CORAL`, `coralFill`, etc.) are
historical and now carry the muted amber values — do not read them literally.

**Current canvas palette (mirror of `src/lib/chart-theme.ts`):**

| Export                | Value            | Token mirror    | Role                 |
| --------------------- | ---------------- | --------------- | -------------------- |
| `CHART_SURFACE`       | `#1a1814`        | `charcoal-900`  | Chart background     |
| `CHART_TEXT`          | `#a8a095`        | `charcoal-400`  | Axis / label text    |
| `CHART_TEXT_MUTED`    | `#79736a`        | `charcoal-500`  | Secondary labels     |
| `CHART_GRID`          | `#312c25`        | `charcoal-800`  | Gridlines            |
| `CHART_BORDER`        | `#39332b`        | `charcoal-700`  | Scale borders        |
| `CHART_CROSSHAIR`     | `#4a443a`        | `charcoal-600`  | Crosshair            |
| `ACCENT_CORAL`        | `#d89a4e`        | `amber-400`     | Brand / primary line |
| `ACCENT_CORAL_BRIGHT` | `#e9bd80`        | `amber-300`     | Emphasis line        |
| `ACCENT_CORAL_DEEP`   | `#875720`        | `amber-600`     | Deep accent line     |
| `ACCENT_CORAL_RGB`    | `"216, 154, 78"` | `--accent-rgb`  | Alpha fills          |
| `POSITIVE`            | `#3fbf6f`        | signal-positive | Gain lines           |
| `NEGATIVE`            | `#e5544b`        | signal-negative | Loss lines           |
| `WARNING`             | `#e0a13a`        | signal-warning  | Caution              |
| `NEUTRAL`             | `#a8a095`        | `charcoal-400`  | Comparison series    |
| `NEUTRAL_LIGHT`       | `#d3cec5`        | `charcoal-300`  | Light neutral series |

---

## Chrome primitives (`src/app/globals.css`)

### shadcn semantic mapping (`@theme inline`)

The Vysted primitives map onto shadcn/ui semantic names so every shadcn component
inherits the Warm Graphite palette without overrides:

- `--color-background` → `charcoal-950` (`#0e0d0b`)
- `--color-foreground` → `charcoal-100` (`#f5f2ec`)
- `--color-card` → `charcoal-900` (`#1a1814`)
- `--color-popover` → `charcoal-875` (`#211e19`)
- `--color-primary` / `--color-accent` / `--color-ring` → `amber-400` (`#d89a4e`)
- `--color-border` / `--color-input` → `charcoal-700` (`#39332b`)
- `--color-muted-foreground` → `charcoal-400` (`#a8a095`)
- `--color-destructive` → signal-negative (`#e5544b`)

### Composite chrome vars (`:root`)

- `--accent-rgb: 216 154 78` — RGB decomposition of `amber-400`; drives
  `rgb(var(--accent-rgb) / <alpha>)` throughout globals and dockview rules.
- `--hairline: rgb(122 116 106 / 0.14)` — warm neutral at 14%; quiet fine divider.
- `--hairline-strong: rgb(122 116 106 / 0.24)` — warm neutral at 24%; panel seams.
- `--bezel-shadow` — 1px inset light lip + 1px drop shadow; flat depth, no blur halo.
- No `--glow-*` primitive. Active state is `0 0 0 1px var(--color-amber-400)`.

### Utility classes

- `.hud-label` — uppercase, 0.12em tracking, `charcoal-400` (`#a8a095`).
- `.instrument-bezel` — applies `--bezel-shadow`.
- `.tick-rule` — a single flat 1px warm hairline divider.
- `.hud-active` — 1px amber border + `charcoal-875` background. No blur.
- `.node-active` — 1px amber border + `charcoal-875` background (node-editor variant).
- `.stream-cursor` — 2px amber bar that blinks while tokens arrive; feedback, not glow.

### Body background

`background-image: none` — a single flat warm near-black (`charcoal-950`). No
ambient gradient, no grain, no vignette. The body is also `position: fixed; inset: 0`
to pin the viewport and prevent whole-app micro-scroll from dockview focus events.

### Selection and focus

- `::selection` — amber @ 30% background, `lume` text.
- `:focus-visible` — 1px solid `amber-400`, offset 1px.

### Scrollbars

Quiet warm-neutral rail (`charcoal-400` @ 40%); thumb lifts to amber accent @ 55%
on hover. Resting state is deliberately subdued.

---

## Dockview theming (`.dockview-theme-vysted`)

Applied as `dockview-theme-dark dockview-theme-vysted` on the panel host. The dark
base supplies defaults; the Vysted rule overrides all visible surfaces. Also targets
`.dockview-theme-vysted .dv-shell` to override dockview 4.x's nested shell class
(otherwise the cold navy default bleeds through).

Key overrides sourced from `globals.css`:

- Group view background: `charcoal-900` (`#1a1814`)
- Tab strip background: `charcoal-925` (`#131210`)
- Active tab bg: `charcoal-875` (`#211e19`); active tab text: `lume` (`#f7f5f0`)
- Inactive active-group tab text: `charcoal-400` (`#a8a095`)
- Inactive group tab text: `charcoal-300` / `charcoal-600`
- Panel seam separators: `--hairline-strong` (24% warm neutral)
- Active outline / drag-over border: `amber-400` (`#d89a4e`)
- Active sash: `amber-500` (`#c0802f`)
- Drag-over background: amber @ 14%
- Tab font size: 12px
- Active tab underline tick: `inset 0 -2px 0 amber-400` (non-layout, no-ops if the
  class name drifts in a future dockview version)
- `.dv-view` background: `charcoal-900` so over-scroll never reveals the WKWebView
  default backdrop
- `.dv-split-view-container .dv-view-container .dv-view`: `overflow: hidden` to
  prevent the double-scroll-bar bug (the panel owns the single scroller)

---

## Motion

Unified motion vocabulary with four duration tiers, defined in `styles/tokens.css`:

| Token                 | Value | Use                                            |
| --------------------- | ----- | ---------------------------------------------- |
| `--duration-micro`    | 120ms | Hover, toggle, button press, color/value flash |
| `--duration-default`  | 180ms | Dropdown, popover, tab switch, palette open    |
| `--duration-entrance` | 240ms | Panel mount, modal/sheet, sidebar slide        |
| `--duration-exit`     | 160ms | Exits ~30% faster than entrances               |

Easing: `--ease-enter` for arriving elements; `--ease-exit` for departing;
`--ease-shared` for elements that start and end on screen. Legacy aliases
(`--ease-instrument`, `--ease-detent`, etc.) are kept for existing references.

`prefers-reduced-motion` collapses all animation/transition to 0.01ms via a
`globals.css` media query, and is additionally honoured by the Framer Motion tree
via `<MotionConfig reducedMotion="user">`.

---

## Verification gates

Visual sign-off is the operator's, per the `CLAUDE.md` visual protocol (populated
panels, AAPL anchor, 1920x1080 and 2560x1440). Named gates:

1. **Warmth check** — background reads warm (R > B), not blue, at every surface level.
2. **Accent budget** — amber appears on 0–2 elements at once; never a background wash.
3. **No-glow check** — no blurred bloom on any control, card, or chrome element.
4. **Three tiers visible** — primary/secondary/tertiary text contrast is legible side
   by side in a populated panel (watchlist or brief).
5. **Canvas lockstep** — a populated chart's axis text, gridlines, and accent line
   match the token values listed in the canvas table above; no cold-blue or cyan drift.
6. **Destructive button** — keeps maximum legibility on the loss-red surface.

---

## Retired systems (historical reference only)

The following palettes were used in prior phases and are **not the current system**:

- **"Claude after dark" (Phase 10):** espresso base `#1a1512`, coral accent `#d97757`,
  Fraunces display serif. Retired in the R4 rebuild.
- **Warm-instrument clay:** `amber-400 = #a06b52`, Hanken Grotesk display face,
  `charcoal-950 = #0b0a09`. Retired before R4 shipped.
- **Cold-instrument / cold-zinc:** graphite `#0a0b0d`, ion-blue `#4f86f7` accent.
  Entirely superseded.

All three are gone. If you find a hex from these systems in live code, it is a
regression. The grep gate for the R4 build forbids the tokens and hexes associated
with these retired systems in new or changed code.
