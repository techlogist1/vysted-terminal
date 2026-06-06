---
version: alpha
name: Vysted-Terminal-design-system
description: |
  The single source of truth for the Vysted Terminal UI. A terminal-native finance
  workspace rendered entirely in ONE monospace family (JetBrains Mono) across every
  text role — hierarchy is built from size and weight alone, never from a second face.
  The canvas is a settled warm-graphite near-black (`#110f0c`, ~rgb 17,15,12) with a
  five-rung surface ladder for depth and hairline 1px borders — there are NO drop
  shadows and no glow anywhere in the system. Containers are sharp rectangles (0px
  radius); only interactive elements soften to 4px. A SINGLE muted amber accent
  (`#d89a4e`) lights at most ~5% of pixels and at most two elements at once; the only
  other saturated colors are the luminance-matched green/red reserved for P&L. ASCII
  bracket markers (`[+]` `[-]` `[x]`) and bordered keycap chips are the iconography
  where they fit — especially the command palette. AI narratives, briefs, and notes
  render at a comfortable 16px / 1.6 prose size; dense data tables drop to 13px tabular.
  This file is the binding contract: every component in the app must resolve to a token
  defined here. It adapts OpenCode's monospace marketing system to a dark, dense,
  multi-panel desktop terminal — same discipline, warm-graphite canvas instead of cream.

colors:
  # --- Surface ladder (depth comes from these, never from shadow) -----------
  canvas: "#110f0c"          # L0 — app root well, deepest warm near-black (rgb 17,15,12)
  chrome: "#17140f"          # L1 — header fascia, tab strip, status bar
  panel: "#1e1a15"           # L2 — panel / card surface (the anchor surface)
  raised: "#25201a"          # L3 — popover, command palette, active tab, hover
  inset: "#2d2820"           # L4 — input fill, node body, recessed well
  # --- Borders & hairlines ---------------------------------------------------
  border: "#3e372d"          # control / input / table border (1px)
  border-strong: "#4d463b"   # emphasized divider, disabled foreground
  hairline: "rgba(122,116,106,0.14)"        # quiet 1px section divider
  hairline-strong: "rgba(122,116,106,0.24)" # tab-strip rule, stronger divider
  # --- Text ramp -------------------------------------------------------------
  text-primary: "#f6f3eb"    # body, headings, primary values — warm near-white
  text-secondary: "#ada294"  # muted foreground, secondary labels, group headers
  text-tertiary: "#968c7d"   # faint meta / captions — lightened to clear WCAG AA on dark surfaces
  text-bright: "#f7f5f0"     # peak readout, active-tab label
  # --- The single accent (muted amber) — scarce, <=5% of pixels --------------
  primary: "#d89a4e"         # brand primary = the amber accent (same hex; names the FILL role)
  accent: "#d89a4e"          # the amber accent — names the EDGE / focus / active-state role
  accent-bright: "#e9bd80"   # hover, accent text on dark
  accent-pressed: "#c0802f"  # pressed, active sash, selected fill
  accent-tint: "#f0d8ac"     # faint selection tint
  accent-deep: "#875720"     # deep accent border
  # --- Signal (P&L only — the only other saturated colors, never as fills) ---
  positive: "#3fbf6f"        # gains — muted green, luminance-matched
  negative: "#e5544b"        # losses — muted red, luminance-matched
  warning: "#e0a13a"         # stale / paper / caution

typography:
  hero:
    fontFamily: JetBrains Mono
    fontSize: 28px
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: -0.01em
  overview:
    fontFamily: JetBrains Mono
    fontSize: 22px
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: -0.005em
  section:
    fontFamily: JetBrains Mono
    fontSize: 18px
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: 0
  title:
    fontFamily: JetBrains Mono
    fontSize: 15px
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: 0
  prose:
    fontFamily: JetBrains Mono
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: 0
  body:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: 0
  caption:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: 0
  micro:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: 0.1em

rounded:
  none: 0px      # every container: panel, card, table, header, status bar, section
  control: 4px   # every interactive element: button, input, toggle, pill, chip, popover, row
  full: 9999px   # avatar dots only

spacing:
  xxs: 2px    # hairline inset, icon-to-label nudge
  xs: 4px     # tight inline gap
  sm: 6px     # control inner gap
  md: 8px     # default control padding, list-row vertical
  lg: 12px    # panel inner padding, comfortable gap
  xl: 16px    # block gap, section internal padding
  xxl: 24px   # section gap
  section: 32px  # major section rhythm

components:
  # --- Buttons --------------------------------------------------------------
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.canvas}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: 6px 14px
    height: 32px
  button-primary-pressed:
    backgroundColor: "{colors.accent-pressed}"
    textColor: "{colors.canvas}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    height: 32px
  button-secondary:
    backgroundColor: "{colors.inset}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: 6px 14px
    height: 32px
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.text-secondary}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: 6px 10px
    height: 32px
  # --- Segmented toggle (ASK / AUTO) ----------------------------------------
  toggle-segment:
    backgroundColor: "transparent"
    textColor: "{colors.text-secondary}"
    typography: "{typography.micro}"
    rounded: "{rounded.control}"
    padding: 4px 10px
    height: 24px
  toggle-segment-active:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.text-bright}"
    typography: "{typography.micro}"
    rounded: "{rounded.control}"
    padding: 4px 10px
    height: 24px
  # --- Inputs ---------------------------------------------------------------
  text-input:
    backgroundColor: "{colors.inset}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: 6px 10px
    height: 32px
  text-input-focused:
    backgroundColor: "{colors.inset}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: 6px 10px
    height: 32px
  textarea:
    backgroundColor: "{colors.inset}"
    textColor: "{colors.text-primary}"
    typography: "{typography.prose}"
    rounded: "{rounded.control}"
    padding: 12px
  # --- Tabs (dockview + in-panel) -------------------------------------------
  tab:
    backgroundColor: "{colors.chrome}"
    textColor: "{colors.text-secondary}"
    typography: "{typography.caption}"
    rounded: "{rounded.none}"
    padding: 6px 12px
    height: 32px
  tab-active:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.text-bright}"
    typography: "{typography.caption}"
    rounded: "{rounded.none}"
    padding: 6px 12px
    height: 32px
  # --- Badges & keycaps -----------------------------------------------------
  badge:
    backgroundColor: "{colors.inset}"
    textColor: "{colors.text-secondary}"
    typography: "{typography.micro}"
    rounded: "{rounded.control}"
    padding: 2px 6px
  kbd:
    backgroundColor: "{colors.inset}"
    textColor: "{colors.text-secondary}"
    typography: "{typography.micro}"
    rounded: "{rounded.control}"
    padding: 2px 6px
  # --- Containers -----------------------------------------------------------
  panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: 12px
  panel-header:
    backgroundColor: "{colors.chrome}"
    textColor: "{colors.text-primary}"
    typography: "{typography.title}"
    rounded: "{rounded.none}"
    padding: 8px 12px
    height: 36px
  status-bar:
    backgroundColor: "{colors.chrome}"
    textColor: "{colors.text-secondary}"
    typography: "{typography.micro}"
    rounded: "{rounded.none}"
    padding: 4px 12px
    height: 24px
  # --- Data table -----------------------------------------------------------
  table-header-cell:
    backgroundColor: "{colors.chrome}"
    textColor: "{colors.text-secondary}"
    typography: "{typography.micro}"
    rounded: "{rounded.none}"
    padding: 6px 12px
  table-numeric-cell:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: 6px 12px
  table-cell-positive:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.positive}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: 6px 12px
  table-cell-negative:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.negative}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: 6px 12px
  badge-warning:
    backgroundColor: "{colors.inset}"
    textColor: "{colors.warning}"
    typography: "{typography.micro}"
    rounded: "{rounded.control}"
    padding: 2px 6px
  list-row:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: 8px 12px
  # --- Command palette -------------------------------------------------------
  command-palette:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: 8px
  command-row:
    backgroundColor: "transparent"
    textColor: "{colors.text-primary}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: 8px 10px
    height: 36px
  command-row-active:
    backgroundColor: "{colors.inset}"
    textColor: "{colors.text-bright}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: 8px 10px
    height: 36px
  command-group-header:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.text-secondary}"
    typography: "{typography.micro}"
    rounded: "{rounded.none}"
    padding: 8px 10px 4px
  # --- Composer --------------------------------------------------------------
  composer:
    backgroundColor: "{colors.inset}"
    textColor: "{colors.text-primary}"
    typography: "{typography.prose}"
    rounded: "{rounded.control}"
    padding: 10px 12px
  send-button:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.canvas}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    height: 32px
  load-pill:
    backgroundColor: "{colors.inset}"
    textColor: "{colors.text-secondary}"
    typography: "{typography.caption}"
    rounded: "{rounded.control}"
    padding: 4px 10px
    height: 24px
  # --- Brief / overview ------------------------------------------------------
  brief-metric-card:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text-primary}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: 12px
  empty-state:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text-secondary}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: 24px
  # --- Dividers & rules (1px filled elements — depth without shadow) ---------
  rule:
    backgroundColor: "{colors.hairline}"
    rounded: "{rounded.none}"
    height: 1px
  rule-strong:
    backgroundColor: "{colors.hairline-strong}"
    rounded: "{rounded.none}"
    height: 1px
  divider:
    backgroundColor: "{colors.border}"
    rounded: "{rounded.none}"
    height: 1px
  divider-strong:
    backgroundColor: "{colors.border-strong}"
    rounded: "{rounded.none}"
    height: 1px
  # --- Inline state ----------------------------------------------------------
  tab-tick:
    backgroundColor: "{colors.accent}"
    rounded: "{rounded.none}"
    height: 2px
  focus-ring:
    backgroundColor: "{colors.accent-deep}"
    rounded: "{rounded.control}"
    height: 1px
  selection:
    backgroundColor: "{colors.accent-tint}"
    rounded: "{rounded.none}"
  link:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.accent-bright}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
  caption-meta:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text-tertiary}"
    typography: "{typography.caption}"
    rounded: "{rounded.none}"
    padding: 2px 0
---

## Overview

Vysted Terminal is rendered entirely in **JetBrains Mono** — every word, from the
28px first-run splash down to the 11px status-bar tick, sits in the same monospaced
face. The visual identity is that single typographic decision: the app reads like a
live instrument readout, not a styled web dashboard. There is no sans-serif anywhere,
no display face, no italic alternative. Hierarchy is built from **size and weight on
one family** — `{typography.hero}` and `{typography.section}` share weight 700 and
differ only in size; `{typography.body}` and `{typography.prose}` share weight 400 and
differ only in size and the role they serve.

The chrome is a settled warm-graphite near-black. Depth is a **five-rung surface
ladder** — `{colors.canvas}` (the L0 well) → `{colors.chrome}` (L1 fascia) →
`{colors.panel}` (L2 anchor) → `{colors.raised}` (L3 floats) → `{colors.inset}` (L4
fills) — separated by 1px `{colors.hairline}` rules. **There are no drop shadows and
no glow in the system.** Nothing floats on a blur; an element registers as "above"
only by climbing one rung of the ladder and carrying a hairline border.

Containers are sharp rectangles at `{rounded.none}` (0px); only interactive elements
soften to `{rounded.control}` (4px). The brand's only "color" is a **single muted
amber** (`{colors.accent}` — `#d89a4e`), used scarcely: at most ~5% of pixels and at
most two elements lit at once. The only other saturated colors are
`{colors.positive}` / `{colors.negative}` / `{colors.warning}`, reserved entirely for
P&L and status signals and never used as background fills.

**Key characteristics**
- 100% JetBrains Mono across every text role — no second face anywhere in the chrome.
- Warm-graphite `{colors.canvas}` (`#110f0c`) as the deepest surface; a five-rung
  ladder carries all depth — no shadows, no gradients, no vignette.
- A single amber accent on `<=2` elements at any moment; P&L green/red the only other
  saturated color.
- `{rounded.none}` (0px) on every container; `{rounded.control}` (4px) on every
  interactive element; `{rounded.full}` only on avatar dots.
- ASCII bracket markers (`[+]` `[-]` `[x]`) and bordered `{components.kbd}` keycap
  chips as the iconography where they fit — especially the command palette.
- AI narratives, briefs, and notes read at `{typography.prose}` (16px / 1.6); dense
  data tables drop to `{typography.body}` (13px) with tabular figures.

## Foundations

### Surface ladder (depth without shadow)

| Rung | Token | Value | Use |
|---|---|---|---|
| L0 | `{colors.canvas}` | `#110f0c` | App root well; the deepest field behind every panel |
| L1 | `{colors.chrome}` | `#17140f` | Header fascia, tab strip, status bar, table header row |
| L2 | `{colors.panel}` | `#1e1a15` | Panel / card body — the anchor surface most content sits on |
| L3 | `{colors.raised}` | `#25201a` | Popover, command palette, active tab, hover surface |
| L4 | `{colors.inset}` | `#2d2820` | Input fill, node body, recessed wells inside a panel |

Elevation is **monotonic**: a floating element sits exactly one rung above the surface
behind it and carries a 1px `{colors.hairline-strong}` border — never a shadow. The
command palette (`{colors.raised}`) floats over panels (`{colors.panel}`); an input
(`{colors.inset}`) recesses inside a panel. Never skip rungs to fake contrast.

### The single accent

`{colors.accent}` (`#d89a4e`) is the only brand color. It marks the one primary
action, the active/agent-live state, the focus ring, and the selected sash — and
nothing else. States: `{colors.accent-bright}` (hover / accent text), `{colors.accent}`
(default), `{colors.accent-pressed}` (pressed / selected fill), `{colors.accent-tint}`
(faint selection wash), `{colors.accent-deep}` (dense border). If two amber elements
are already lit in a view, a third must resolve to a neutral. The accent is a spotlight,
not a paint.

### Text ramp

`{colors.text-primary}` (`#f6f3eb`) carries body and headings; `{colors.text-secondary}`
(`#ada294`) carries muted labels, secondary values, and **group headers**;
`{colors.text-tertiary}` (`#968c7d`) is the faintest meta tone — lightened from the legacy
`#847b6d` to clear WCAG AA on every surface, so even decorative captions stay legible;
`{colors.text-bright}` (`#f7f5f0`) marks the active tab and
peak readouts. Numerics everywhere use tabular figures + slashed zero so columns align
like a gauge.

### Signal colors

`{colors.positive}` and `{colors.negative}` are luminance-matched so a gain never reads
louder than a loss in a P&L column; `{colors.warning}` badges paper / stale / synthetic
state. These three are the only saturated colors besides the accent, and they appear as
text or 1px markers — never as a filled background.

## Typography

### Family

**JetBrains Mono** is the single face, at weights 400 / 500 / 700, falling back through
`ui-monospace, "SF Mono", "Cascadia Mono", monospace`. There is no sans body, no display
face, no italic alternative — even the 11px status tick is JetBrains Mono. JetBrains
Mono is the documented open substitute for Berkeley Mono (closest stroke contrast and
x-height); IBM Plex Mono is the secondary fallback. The single-font decision is the
identity.

### Scale

| Role | Size | Weight | Line height | Use |
|---|---|---|---|---|
| `{typography.hero}` | 28px | 700 | 1.2 | First-run splash; the single biggest moment in the app |
| `{typography.overview}` | 22px | 700 | 1.25 | Brief headline, equity ticker headline, hero stat number |
| `{typography.section}` | 18px | 700 | 1.3 | Section heads inside a panel |
| `{typography.title}` | 15px | 500 | 1.3 | Panel title bar |
| `{typography.prose}` | 16px | 400 | 1.6 | AI narratives, research briefs, notes prose — the reading size |
| `{typography.body}` | 13px | 400 | 1.5 | Default UI text, list rows, table cells, control labels |
| `{typography.caption}` | 12px | 400 | 1.5 | Captions, secondary meta, tab labels |
| `{typography.micro}` | 11px | 500 | 1.3 (+0.1em, uppercase) | HUD labels, group headers, badges, status ticks |

### Principles

Hierarchy is **size + weight only**. Bold (700) is the heading signal at `hero` /
`overview` / `section`; medium (500) marks `title`, `micro`, and emphasis; regular (400)
is everything readable. The reading sizes are deliberately split: `{typography.prose}`
(16px / 1.6) for anything a human reads as sentences (the AI's narratives and briefs,
notes), and `{typography.body}` (13px) for dense chrome and data. **Never reach below
`{typography.micro}` (11px).** No component may use an arbitrary `text-[…]` value — every
text node resolves to one role above.

## Spacing & rhythm

Base grid is 4px with 2px and 6px steps for tight inline gaps. Component padding draws
from `{spacing.md}` (8px) / `{spacing.lg}` (12px); block gaps from `{spacing.xl}` (16px);
section gaps from `{spacing.xxl}` (24px) / `{spacing.section}` (32px). Panels pad at
`{spacing.lg}` (12px). Raw off-scale values (`gap-2.5`, `px-[7px]`, `py-1.5`) are
forbidden in new and changed code — each maps to a token: `{spacing.xxs}` (2px) ·
`{spacing.xs}` (4px) · `{spacing.sm}` (6px) · `{spacing.md}` (8px) · `{spacing.lg}`
(12px) · `{spacing.xl}` (16px) · `{spacing.xxl}` (24px) · `{spacing.section}` (32px).

## Shape & elevation

### Radius

| Token | Value | Use |
|---|---|---|
| `{rounded.none}` | 0px | Every container — panel, card, table, header, status bar, section block, dialog body |
| `{rounded.control}` | 4px | Every interactive element — button, input, toggle, pill, chip, badge, kbd, command row, popover |
| `{rounded.full}` | 9999px | Avatar dots only |

The radius vocabulary is two values. A container is a sharp rectangle; the moment an
element is clickable/typeable it softens to 4px. The floating command palette and
dialogs are the one nuance: their **body** is a soft 4px interactive surface, but the
panels and tables they sit over stay sharp.

### Elevation

There are **no drop shadows and no glow** in the system. The legacy `--bezel-shadow`
and any `shadow-*` / `drop-shadow` / blurred-glow utility is removed. Depth is the
surface ladder plus a single 1px border:

| Level | Treatment | Use |
|---|---|---|
| 0 — Flat | No border | Body text blocks, list rows, in-panel content |
| 1 — Hairline | 1px `{colors.hairline}` | Section dividers, row separators, panel seams |
| 2 — Hairline strong | 1px `{colors.hairline-strong}` | Tab-strip rule, floating-overlay border |
| 3 — Accent edge | 1px `{colors.accent}` (`.hud-active`) | The one agent-live / primary control, focus ring |

## Iconography

The brand's iconography is ASCII and keycaps, not decorative SVG:
- **Bracket markers** — `[+]` `[-]` `[x]` `>` lead list rows, section labels, and
  toggles. They are text, not separate icon nodes.
- **Keycap chips** — `{components.kbd}` renders `⌘K` `↵` `↑↓` `esc` as bordered
  monospace chips. The command palette footer and every shortcut hint uses these.
- **Functional lucide icons** are permitted only for panel-specific affordances
  (chart tools, close/expand), sized to match the line (14–16px) and stroked to the
  mono weight; they never replace a bracket marker or a keycap.

## Components

> States covered: Default and Active/Pressed. Hover is a single luminance step (climb
> half a rung) — never a color change or a shadow.

### Buttons

`{components.button-primary}` is the one amber action per view — background
`{colors.accent}`, text `{colors.canvas}`, `{rounded.control}`, 28px tall.
`{components.button-secondary}` is the neutral default — `{colors.inset}` fill,
`{colors.text-primary}` text. `{components.button-ghost}` is transparent with
`{colors.text-secondary}` text for tertiary actions. All three are 32px tall, padded
`6px 14px` (ghost `6px 10px`), and share `{typography.body}`.

**Control-size ladder** — there are exactly two interactive heights so sibling controls
never misalign: **32px** is the standard (button, input, select, send, search) and
**24px** is the compact (segmented toggle, load pill, badge-height chip). Never an h-9
input beside an h-8 button; derive every control from these two heights.

### Segmented toggle (ASK / AUTO)

A two-segment control: `{components.toggle-segment}` (transparent, `{colors.text-secondary}`)
for the inactive segment and `{components.toggle-segment-active}` (`{colors.raised}`,
`{colors.text-bright}`) for the active one, both `{typography.micro}` and 24px tall. The
segments sit in a single 1px `{colors.border}` rectangle with a hairline divider between
them — one unit, not two floating pills.

### Inputs

`{components.text-input}` is a `{colors.inset}` fill with a 1px `{colors.border}`,
`{typography.body}`, 32px tall. `{components.text-input-focused}` keeps the fill and
swaps the border to 1px `{colors.accent}` (the flat focus signal — no halo).
`{components.textarea}` uses `{typography.prose}` for multi-line authored text.

### Tabs

`{components.tab}` (`{colors.chrome}`, `{colors.text-secondary}`) and
`{components.tab-active}` (`{colors.raised}`, `{colors.text-bright}`) are sharp
`{rounded.none}` cells, 32px tall, `{typography.caption}`. The active tab carries a 2px
`{colors.accent}` bottom tick (inset box-shadow, non-layout) — the only amber in the
tab strip.

### Badges & keycaps

`{components.badge}` and `{components.kbd}` share the `{colors.inset}` fill,
`{colors.text-secondary}` text, `{typography.micro}`, `{rounded.control}`, `2px 6px`
padding. A badge is a status word (`PAPER`, `LIVE`, `STALE` — `STALE` tints
`{colors.warning}`); a kbd is a shortcut glyph.

### Panel & chrome

`{components.panel}` is the `{colors.panel}` anchor surface, sharp, padded `12px`.
`{components.panel-header}` is a 36px `{colors.chrome}` bar with a `{typography.title}`
name and a 1px `{colors.hairline}` bottom rule. `{components.status-bar}` is a 24px
`{colors.chrome}` strip of `{typography.micro}` ticks at the app foot.

## Patterns

### Data table

Every tabular surface (equity statements, screener, watchlist, portfolio, analyst,
earnings, SEC) uses the **one `DataTable` primitive** — no panel re-rolls its own.

- **Structure:** a real `<table>` with fixed column widths declared per column, a
  sticky `{components.table-header-cell}` header row on `{colors.chrome}`, and
  `{components.list-row}` body rows separated by 1px `{colors.hairline}`.
- **Numerics:** every numeric column is `{components.table-numeric-cell}` —
  **right-aligned, `{typography.body}`, `tabular-nums`, slashed zero** — so digits in a
  column line up and a number never collides with the next column or truncates
  mid-figure. Units (K/M/B/T, %, currency) come from the single shared `formatUnit`
  helper, never re-implemented per panel.
- **Headers:** `{typography.micro}` uppercase `{colors.text-secondary}`; period headers
  (FY23 / FY24 / TTM) are first-class header cells, right-aligned over their numeric
  column.
- **Hierarchy:** a headline metric uses `{colors.text-primary}`; a derived ratio drops
  to `{colors.text-secondary}` so the eye finds the important row. P&L cells color
  `{colors.positive}` / `{colors.negative}`.
- **Fundamentals are a statement table, never a `grid grid-cols-2` key-value dump** —
  label left, value right-aligned in its own numeric column.
- Row height is `{spacing.section}`-free: `8px 12px` cell padding (one rhythm across
  every table); never four different row heights across panels.

### Notes editor

The Tiptap editor's content wears `.notes-prose` at `{typography.prose}` (16px / 1.6),
`{colors.text-primary}` — never Tailwind's unconfigured `prose prose-sm` (which inherits
16px sans). A visible formatting toolbar exposes H1/H2/H3, bold, italic, list, quote,
code, link, and wikilink as `{components.button-ghost}` icon buttons — the hidden `/`
slash menu is a shortcut, not the only path. Slash and wikilink popups float on
`{colors.raised}` with a 1px `{colors.hairline-strong}` border — **no `shadow-lg`**.
Headings inside notes resolve to `{typography.overview}` (H1) / `{typography.section}`
(H2) / `{typography.title}` (H3).

### Empty state

`{components.empty-state}` centers a composed placeholder: an ASCII bracket glyph, a
`{typography.body}` line in `{colors.text-secondary}`, and — where useful — 2–3
suggestion chips (`{components.button-ghost}`). Never a bare "No results." string, and
never `justify-center` in a tall column that strands the content in a sea of dead space;
anchor the block to the top third with `{spacing.xxl}` breathing room.

### Composer

The chat composer is **one unit**: a `{components.composer}` field (`{colors.inset}`,
`{typography.prose}`, 1px `{colors.border}`, `{rounded.control}`) with the agent avatar
and persona/ASK-AUTO controls inset on the left and the `{components.send-button}`
aligned inside the field's right edge — vertically centered, 32px, amber. The send is
never a large detached square next to a huge rectangle; the field height grows from a
single-line baseline and the send stays pinned to the bottom-right corner as one
composed control. The `{components.load-pill}` (symbol loader) is a 24px
`{colors.inset}` pill on the same baseline as the other controls — derived from the same
control sizes, never an oversized outlier.

### Command palette

The `⌘K` palette is a `{components.command-palette}` floating on `{colors.raised}` with
a 1px `{colors.hairline-strong}` border (no shadow). Structure:
- **Input row:** `{typography.body}` (sans-free — mono like everything), a `>` bracket
  prompt glyph at the left.
- **Group headers:** `{components.command-group-header}` — `{typography.micro}` uppercase
  `{colors.text-secondary}`, **always visible** (the `group-heading-style` utility must
  resolve), separating Agents / Actions / Panels / Symbols.
- **Rows:** `{components.command-row}` (36px) with an ASCII/keycap leading glyph, a
  primary label, and a secondary description that **truncates with an ellipsis inside
  the row — never hard-clips**; `{components.command-row-active}` raises to
  `{colors.inset}` with `{colors.text-bright}` text. The fixed-query map (`notes` →
  Notes) stays.
- **Footer:** `{components.kbd}` keycap hints (`↑↓` navigate · `↵` open · `esc` close).

### Brief / overview

The research brief renders as typed blocks, not raw markdown: a grid of
`{components.brief-metric-card}` (sharp, `{colors.panel}`, 1px `{colors.hairline}`,
`{typography.overview}` value over a `{typography.micro}` label) above the synthesis
prose at `{typography.prose}`. The equity-overview ticker headline is
`{typography.overview}`; its price is the hero number in `{typography.overview}`
`tabular-nums`.

## Do's and Don'ts

### Do
- Render every text role in JetBrains Mono. The single-font decision is the identity.
- Carry all depth with the surface ladder + 1px hairline; climb exactly one rung to float.
- Keep `{rounded.none}` on containers and `{rounded.control}` on interactive elements.
- Reserve `{colors.accent}` for one primary/agent-live element at a time (`<=2` per view).
- Right-align every numeric column with `tabular-nums`; route all units through `formatUnit`.
- Resolve every text node to a named `{typography.*}` role and every gap to a `{spacing.*}` token.

### Don't
- Don't introduce a sans-serif body, a display face, or an italic style.
- Don't add a drop shadow, glow, gradient, or `shadow-*` utility anywhere.
- Don't use a second accent color; the amber is alone besides P&L green/red.
- Don't render fundamentals as a `grid grid-cols-2` key-value dump.
- Don't hard-clip a command-row description, hide a group header, or strand an empty state.
- Don't ship an arbitrary `text-[…]`, off-grid spacing, or a `rounded-md/lg/xl/2xl` container.

## Verification

1. Lint with `npx @google/design.md lint docs/redesign/VYSTED_DESIGN.md`; resolve every
   `broken-ref`, `contrast-ratio`, and `orphaned-token` warning before relying on the file.
2. Every component shipped in Phase 1 must resolve to a token here. Off-spec usage found
   while driving the app is a defect, not a variant — bring it into spec.
3. Verify on the **real rendered window** (macOS Computer Use), not the DOM: numeric
   columns must not collide, control rows must sit on one baseline, descriptions must
   ellipsis-truncate, and no element may use a size off this scale.
