# Phase 10 — Design System Map: Retiring "INSTRUMENT" (amber-brass / lume-cream / warm brown-black)

Audience: the lead, who is retiring the Phase 9.5 Track D "INSTRUMENT" / JARVIS theme for "Claude after dark."
Purpose: document the FULL theming mechanism so the re-skin is a known, bounded edit — plus enumerate every hardcoded
color that bypasses the token system and must be hunted down separately.

Every claim below is cited to `file:line` against the actual source as of this commit. No speculation.

---

## 0. TL;DR for the re-skin

There are **two** color systems in this app, and they do NOT share a source of truth:

1. **The CSS-variable / Tailwind-utility system** (the "real" design system). Centralized. Re-skinning it touches
   **3 files**: `styles/tokens.css`, `src/app/globals.css`, and `src/app/layout.tsx` (fonts). Everything that renders
   in HTML/CSS — every panel, dockview, shadcn, the header fascia — flows from these. Change the token values, the app
   re-skins.

2. **The canvas color system** (the leak). `lightweight-charts` (6 chart panels) and the ReactFlow node editor render
   to `<canvas>` / inline styles and **cannot read CSS variables**, so they hardcode hex literals. These are NOT
   tokens — they are duplicated copies of token values (and in 3 cases, copies that already drifted off-palette).
   Re-skinning requires editing each of these ~9 files by hand.

So the honest scope: **3 files to re-skin the chrome, plus ~9 files of hardcoded canvas colors that bypass tokens
entirely.** Anyone who says "just change tokens.css" is wrong about the chart panels.

---

## 1. Where the design system lives (the file map)

| Layer                    | File                    | Role                                                                                                                                                                                                                                   |
| ------------------------ | ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Raw tokens               | `styles/tokens.css`     | Tailwind 4 `@theme` block — palette, fonts, radius, motion. Each becomes a utility class.                                                                                                                                              |
| Semantic + chrome        | `src/app/globals.css`   | Maps tokens → shadcn semantic names (`@theme inline`); composite chrome vars; base layer (body bg/font/atmosphere/grain/selection/focus/scrollbars); `@layer components` instrument primitives; the `.dockview-theme-vysted` override. |
| Fonts                    | `src/app/layout.tsx`    | `next/font/google` loads Newsreader + JetBrains Mono, injects `--font-newsreader` / `--font-jetbrains-mono`, sets `class="dark"` on `<html>`.                                                                                          |
| Header fascia / wordmark | `src/app/page.tsx`      | The "VYSTED / Terminal" wordmark + instrument header bar.                                                                                                                                                                              |
| Build glue               | `postcss.config.mjs`    | Only plugin is `@tailwindcss/postcss`. **There is no `tailwind.config.js`** — Tailwind 4 is fully CSS-driven.                                                                                                                          |
| Docs                     | `docs/DESIGN_SYSTEM.md` | Narrative spec of INSTRUMENT. Pure documentation, no runtime effect; update on retire.                                                                                                                                                 |

**No `tailwind.config.{js,ts}` exists** (confirmed: only `postcss.config.mjs`, `next.config.ts`, `eslint.config.mjs`,
`vitest.config.ts` present). Tailwind 4 reads design tokens directly from the `@theme` block in CSS. This is the single
most important mechanical fact: tokens ARE the config.

---

## 2. `styles/tokens.css` — every token enumerated

Header comment `tokens.css:1-14` states the aesthetic and that the `@theme` block makes every token a utility class.
The full `@theme` block is `tokens.css:16-74`. Complete enumeration:

### Charcoal (warm brown-black base) — `tokens.css:19-31`

| Token                  | Value     |
| ---------------------- | --------- |
| `--color-charcoal-950` | `#14110f` |
| `--color-charcoal-925` | `#181512` |
| `--color-charcoal-900` | `#1c1916` |
| `--color-charcoal-875` | `#201c18` |
| `--color-charcoal-850` | `#232019` |
| `--color-charcoal-800` | `#2a2620` |
| `--color-charcoal-700` | `#3a352c` |
| `--color-charcoal-600` | `#4d4639` |
| `--color-charcoal-500` | `#6b6253` |
| `--color-charcoal-400` | `#8a8170` |
| `--color-charcoal-300` | `#aaa291` |
| `--color-charcoal-200` | `#c9c2b2` |
| `--color-charcoal-100` | `#e8e3d6` |

### Amber (primary HUD accent) — `tokens.css:34-38`

| Token               | Value                     |
| ------------------- | ------------------------- |
| `--color-amber-200` | `#f9dba6`                 |
| `--color-amber-300` | `#f4c87a`                 |
| `--color-amber-400` | `#e9a94d` (brand/primary) |
| `--color-amber-500` | `#d98e2b`                 |
| `--color-amber-600` | `#b8701a`                 |

### Brass (patinated metal, bezels/rules/ticks) — `tokens.css:42-46`

| Token               | Value     |
| ------------------- | --------- |
| `--color-brass-200` | `#cdb88c` |
| `--color-brass-300` | `#b8965f` |
| `--color-brass-400` | `#9c7c4d` |
| `--color-brass-500` | `#7d6139` |
| `--color-brass-600` | `#5d4829` |

### Lume — `tokens.css:49`

| Token          | Value     |
| -------------- | --------- |
| `--color-lume` | `#f5efe0` |

### Sage (cool counterpoint) — `tokens.css:52-54`

| Token              | Value     |
| ------------------ | --------- |
| `--color-sage-300` | `#b6c4a8` |
| `--color-sage-400` | `#8fa67c` |
| `--color-sage-500` | `#6d8559` |

### Signal (gains/losses, warm-tuned) — `tokens.css:57-60`

| Token                     | Value     |
| ------------------------- | --------- |
| `--color-positive`        | `#7faa6b` |
| `--color-positive-bright` | `#9ccb84` |
| `--color-negative`        | `#c8654b` |
| `--color-negative-bright` | `#e07f63` |

### Typography — `tokens.css:64-65`

| Token          | Value                                                                             |
| -------------- | --------------------------------------------------------------------------------- |
| `--font-serif` | `var(--font-newsreader), ui-serif, Georgia, "Times New Roman", serif`             |
| `--font-mono`  | `var(--font-jetbrains-mono), ui-monospace, "SF Mono", "Cascadia Mono", monospace` |

(The `--font-newsreader` / `--font-jetbrains-mono` inner vars are injected by `next/font` in `layout.tsx:7,13`.)

### Radius — `tokens.css:68-69`

| Token              | Value            |
| ------------------ | ---------------- |
| `--radius-panel`   | `0.375rem` (6px) |
| `--radius-control` | `0.25rem` (4px)  |

### Motion — `tokens.css:72-73`

| Token               | Value                                                 |
| ------------------- | ----------------------------------------------------- |
| `--ease-instrument` | `cubic-bezier(0.2, 0.8, 0.2, 1)`                      |
| `--ease-detent`     | `cubic-bezier(0.34, 1.4, 0.64, 1)` (slight overshoot) |

That is the entire token surface: **34 color tokens, 2 font tokens, 2 radius tokens, 2 easing tokens.**

---

## 3. `src/app/globals.css` — semantic mapping, chrome, cascade order

### 3.1 Import order (cascade-load-bearing) — `globals.css:1-8`

1. `@import "tailwindcss";` (`globals.css:1`)
2. `@import "../../styles/tokens.css";` (`globals.css:4`) — primitives
3. `@import "dockview/dist/styles/dockview.css";` (`globals.css:8`) — dockview base, imported **before** the
   `.dockview-theme-vysted` override below so the override wins the cascade (comment `globals.css:6-7`; also a documented
   CLAUDE.md gotcha).

### 3.2 shadcn semantic mapping — `@theme inline` — `globals.css:12-32`

18 semantic color vars + `--radius`, each pointing at a primitive with a literal hex fallback. This is where shadcn's
`bg-primary`, `text-foreground`, `border-border`, `ring-ring` etc. resolve. The amber/charcoal identity reaches shadcn
through here:

| Semantic                       | Maps to                              | Line |
| ------------------------------ | ------------------------------------ | ---- |
| `--color-background`           | `charcoal-950`                       | `13` |
| `--color-foreground`           | `charcoal-100`                       | `14` |
| `--color-card`                 | `charcoal-900`                       | `15` |
| `--color-card-foreground`      | `charcoal-100`                       | `16` |
| `--color-popover`              | `charcoal-875`                       | `17` |
| `--color-popover-foreground`   | `charcoal-100`                       | `18` |
| `--color-primary`              | `amber-400`                          | `19` |
| `--color-primary-foreground`   | `charcoal-950`                       | `20` |
| `--color-secondary`            | `charcoal-800`                       | `21` |
| `--color-secondary-foreground` | `charcoal-100`                       | `22` |
| `--color-muted`                | `charcoal-800`                       | `23` |
| `--color-muted-foreground`     | `charcoal-400`                       | `24` |
| `--color-accent`               | `sage-400`                           | `25` |
| `--color-accent-foreground`    | `charcoal-950`                       | `26` |
| `--color-border`               | `charcoal-700`                       | `27` |
| `--color-input`                | `charcoal-700`                       | `28` |
| `--color-ring`                 | `amber-400`                          | `29` |
| `--color-destructive`          | `negative`                           | `30` |
| `--radius`                     | `0.375rem` (literal, not the token!) | `31` |

> Adversarial note: `--radius` at `globals.css:31` is the literal `0.375rem`, NOT `var(--radius-panel)`. It duplicates
> the value rather than referencing the token. A re-skin that changes `--radius-panel` in tokens.css will silently NOT
> change shadcn radii. Minor, but it's a token-bypass.

### 3.3 Composite "instrument-chrome" vars (plain `:root`, not `@theme`) — `globals.css:39-46`

These are multi-value shadows/rgb that can't be single-value utilities:

- `--hairline: rgb(156 124 77 / 0.28)` — brass-400 @ 28% (`globals.css:40`). **This is brass-400 expanded to raw RGB,
  not `rgb(var(...))`** — a hardcoded copy.
- `--hairline-strong: rgb(184 150 95 / 0.45)` (`globals.css:41`) — brass-300-ish, also raw.
- `--bezel-shadow` — composite inset/lume/black shadow (`globals.css:42-44`).
- `--glow-amber: 0 0 0 1px rgb(233 169 77 / 0.35), 0 0 12px rgb(233 169 77 / 0.15)` (`globals.css:45`) — amber-400
  expanded to raw RGB.

### 3.4 `@layer base` — applies to EVERY surface automatically — `globals.css:48-113`

- `* { border-color: var(--color-border); }` (`49-51`) — global default border color.
- `html, body`: bg `--color-background`, color `--color-foreground`, `font-family: var(--font-mono, …)` (so the whole
  app is monospace by default), `font-variant-numeric: tabular-nums`, `font-feature-settings: "tnum" 1, "calt" 0`,
  antialias, optimizeLegibility (`53-66`). The tabular-nums default is the "single biggest instrument tell" per the
  design doc.
- `body` atmosphere: two radial gradients — amber phosphor bloom top + radial vignette — `background-attachment: fixed`
  (`71-76`). The amber bloom is hardcoded `rgb(233 169 77 / 0.05)` (`73`).
- `body::before` grain overlay: fixed, `opacity: 0.035`, SVG `feTurbulence` data-URI (`80-88`).
- `body > * { position: relative; z-index: 1; }` keeps the shell above grain (`91-94`).
- `h1,h2,h3 { font-family: var(--font-serif…); letter-spacing: -0.01em; }` (`96-101`) — serif headings.
- `::selection { background: rgb(233 169 77 / 0.28); color: var(--color-lume…); }` (`104-107`) — amber-phosphor
  selection (hardcoded amber RGB).
- `:focus-visible { outline: 1px solid var(--color-amber-400…); }` (`109-112`) — amber HUD focus ring everywhere.

### 3.5 `@layer components` — opt-in instrument primitives — `globals.css:116-148`

- `.hud-label` — uppercase, tracked, `color: var(--color-brass-300…)` (`118-124`). **This is the ONLY place brass color
  reaches the DOM** (see §6).
- `.instrument-bezel` — `box-shadow: var(--bezel-shadow)` + top lume highlight (`127-130`).
- `.tick-rule` — repeating brass-tick gradient using `--hairline` (`133-142`).
- `.hud-active` — `box-shadow: var(--glow-amber)` (`145-147`).

### 3.6 `.dockview-theme-vysted` override — `globals.css:154-189`

Remaps ~22 dockview `--dv-*` vars to the palette (group/tab backgrounds → charcoal shades, active tab color → lume,
separators/dividers/header borders → `--hairline`, active outline → amber-400, active sash → amber-500, drag-over →
`rgb(233 169 77 / 0.14)` + amber-400 border). Full block `155-177`. Plus:

- `.dv-active-tab` lit tick: `box-shadow: inset 0 -2px 0 var(--color-amber-400…)` (`182-184`).
- `.dv-tab` tracking + transition using `--ease-instrument` (`186-189`).

Applied in `src/components/PanelHost.tsx:76`: `className="dockview-theme-dark dockview-theme-vysted h-full w-full"` —
the dark theme supplies defaults, vysted overrides visible surfaces. This is how ALL panels get framed at once.

### 3.7 Scrollbars — `globals.css:194-218`

WebKit + Firefox: thumb `rgb(156 124 77 / 0.4)` (brass), hover `rgb(217 142 43 / 0.7)` (amber-500). Raw RGB, hardcoded.

---

## 4. `layout.tsx` + `page.tsx` — fonts and the wordmark

### Fonts — `layout.tsx`

- `Newsreader({ variable: "--font-newsreader", display: "swap" })` — `layout.tsx:5-9`.
- `JetBrains_Mono({ variable: "--font-jetbrains-mono", display: "swap" })` — `layout.tsx:11-15`.
- `<html lang="en" className={`dark ${newsreader.variable} ${jetbrainsMono.variable}`}>` — `layout.tsx:24`. The `dark`
  class is what activates shadcn dark variants; the two font vars feed `--font-serif`/`--font-mono` in tokens.css.

**To swap fonts app-wide:** change the two `next/font` imports in `layout.tsx:2,5-15` AND the fallback chains in
`tokens.css:64-65`. Both, or the new font won't be the primary.

### Header fascia / wordmark — `page.tsx:77-121`

- `<header className="bg-charcoal-925 instrument-bezel relative flex h-9 …">` (`77`) — charcoal-925 bg + bezel chrome.
- Wordmark: `<span className="font-serif text-sm leading-none tracking-[0.18em] text-amber-400">VYSTED</span>` (`79-81`)
  followed by `<span className="hud-label leading-none">Terminal</span>` (`82`). **The "VYSTED" is serif + amber-400 +
  0.18em tracking; "Terminal" is the brass uppercase hud-label.** This is the brand anchor to redesign.
- Divider `bg-charcoal-700` (`84`); buttons use `text-charcoal-300 hover:text-lume` (`88,100,112`); the kbd chip uses
  `border-charcoal-700 text-charcoal-500` (`93`).
- Bottom `.tick-rule` strip (`117-120`).
- Root `<main className="bg-charcoal-950 …">` (`72`).

All of this is token-class driven — re-skinning tokens carries it, but the _wordmark text/typography choice_ (serif,
tracking, the "VYSTED / Terminal" split) is a deliberate design decision encoded in JSX, not a token.

---

## 5. How tokens propagate to Tailwind utilities, shadcn, panels, dockview

The propagation chain, top to bottom:

1. **Token → utility.** Tailwind 4 reads the `@theme` block in tokens.css and auto-generates a utility for every token:
   `--color-charcoal-900` → `bg-charcoal-900` / `text-charcoal-900` / `border-charcoal-900`; `--font-serif` →
   `font-serif`; `--radius-panel`/`--radius-control` → `rounded-panel`/`rounded-control` (Tailwind 4 derives these).
   No JS config required (`postcss.config.mjs` is the only build glue).
2. **Token → shadcn semantic** via `@theme inline` (`globals.css:12-32`). shadcn components (`button.tsx`, `dialog.tsx`)
   reference only semantic names (`bg-primary`, `bg-background`, `border`, `ring-ring`, `text-muted-foreground`), so
   they inherit the palette through the 18 mappings. Confirmed in `button.tsx:12-19` and `dialog.tsx:34,56,65,114,127`.
3. **Token → base layer** (`globals.css:48-113`): body bg/fg/font/tabular-nums, serif headings, selection, focus,
   atmosphere, grain, scrollbars — applied globally with no per-component opt-in.
4. **Token → dockview** via `.dockview-theme-vysted` (`globals.css:154-189`), applied at `PanelHost.tsx:76`. Frames all
   54 panel/component files at once.
5. **Token → panels.** Panels are plain React using Tailwind utility classes. Breadth (files referencing each):
   - `charcoal-*`: **44 files**
   - `amber-*`: **43 files** (123 line occurrences)
   - `lume`: 16 files
   - `font-mono`: 46 files; `font-serif`: 7 files
   - `sage-*`: 2 files
   - `brass-*` utility class: **0 source files** (see §6 — the surprise)

So for the HTML/CSS surface, the design system genuinely IS centralized: re-tuning `tokens.css` values + the
`globals.css` mappings/chrome re-skins all 44+ panels, dockview, shadcn, header, and atmosphere in one edit. The doc's
"Application strategy" (`DESIGN_SYSTEM.md:77-93`) is accurate for the non-canvas surface.

---

## 6. ADVERSARIAL FINDING — `brass-*` tokens are nearly dead in the DOM

`brass-*` Tailwind utility classes appear in **zero** non-test source files (`grep -rlE 'brass-[0-9]'` over `src/`
`*.tsx`/`*.ts` → 0). Every `brass` mention in `src/` is either a code comment or the wordmark comment in `page.tsx:76`.
Brass color reaches actual pixels through exactly two indirections:

- `.hud-label { color: var(--color-brass-300…) }` (`globals.css:123`) — used in `page.tsx:82` ("Terminal") only.
- `--hairline`/`--hairline-strong` (`globals.css:40-41`), which are **raw RGB copies** of brass-400/brass-300, NOT
  `var(--color-brass-*)` references. So changing `--color-brass-400` in tokens.css does NOT change the hairlines.

Implication for the retire: the brass _palette ramp_ (`--color-brass-200..600`, `tokens.css:42-46`) is almost vestigial.
The visible "brass" identity is carried by (a) `.hud-label`'s brass-300, and (b) two hardcoded RGB hairline vars. Drop
the brass ramp and you must independently update `globals.css:40-41,123` or the brass look persists/breaks.

---

## 7. ENUMERATED — every hardcoded color that bypasses tokens

Grepped hex + rgb + literal black/white over `src/` and `types/` (excluding `tokens.css`/`globals.css`, which are the
intended definition sites). **73 hex occurrences outside the token files** (including tests). The non-test, runtime ones:

### 7.1 Chart-canvas theme blocks (lightweight-charts can't read CSS vars) — 6 files

Each repeats the same charcoal/sage/signal palette as hex literals with `// charcoal-900` style comments:

- `src/modules/chart/ChartPanel.tsx:66-88` — `CHART_THEME` + `CANDLE_THEME`: bg `#1c1916`, text `#c9c2b2`, grid
  `#2a2620`, borders `#3a352c`, crosshair `#4d4639`; candles `#7faa6b`/`#c8654b` (×3 each); comparison line `#8fa67c`
  (`:88`); trend overlay `#8fa67c`/`#c8654b` (`:389`). Font family string at `:68` references `var(--font-jetbrains-mono)`
  (the one canvas place a CSS var works, because it's a font-family string lightweight-charts forwards to CSS).
- `src/modules/quant/YieldCurvePanel.tsx:32-45` — same theme block + `const AMBER = "#e8b441"` (`:45`).
- `src/modules/analyst-ratings/PriceTargetTimeline.tsx:17-30` — same theme block + `const AMBER = "#e8b441"` (`:30`).
- `src/modules/backtest/BacktestResultView.tsx:28-42` — same theme block + `const NEGATIVE = "#c8654b"` (`:41`),
  `const AMBER = "#e8b441"` (`:42`); area series `rgba(200, 101, 75, 0.45)` / `…0.05)` (`:108-109`).
- `src/modules/macro/MacroChart.tsx:19-32` — same theme block + `const LINE_COLOR = "#c39a3e"` commented "amber-600 —
  Vysted accent" (`:32`).
- `src/modules/earnings/EarningsSurpriseChart.tsx:17-31` — same theme block + `const POSITIVE = "#4ec9a3"` (`:30`),
  `const NEGATIVE = "#c8654b"` (`:31`).

### 7.2 Chart indicator / drawing palettes

- `src/modules/chart/indicators.ts:160-165` — `INDICATOR_COLORS`: `#e9a94d` (amber-400), `#8fa67c`, `#c9c2b2`,
  `#f4c87a`, `#b6c4a8` (token mirror, commented).
- `src/modules/chart/drawings/base.ts:30` — `DEFAULT_DRAWING_COLOR = "#e9a94d"`; fill fallback `rgba(233, 169, 77, 0.12)`
  (`:104`).
- `src/modules/chart/drawings/factory.ts:72,75` — `color: "#e9a94d"`, `fillColor: "rgba(233, 169, 77, 0.12)"`.
- `src/modules/chart/drawings/renderers.ts:193,227,296` — fill fallback `"#e9a94d"` (×3).
- `src/modules/chart/volume-profile-primitive.ts:33-34` — `HISTOGRAM_FILL = "rgba(233, 169, 77, 0.2)"` (amber-400 @20%).
- `src/modules/chart/ichimoku-cloud-primitive.ts:22,24` — `POSITIVE_FILL = "rgba(143, 166, 124, 0.15)"` (sage),
  `NEGATIVE_FILL = "rgba(200, 101, 75, 0.15)"` (negative).

### 7.3 OFF-PALETTE DRIFT — values that are NOT any token (highest-priority cleanup)

These claim in comments to be theme colors but do not match any value in `tokens.css`:

- `#e8b441` — used as `AMBER` in **3** files (`YieldCurvePanel.tsx:45`, `PriceTargetTimeline.tsx:30`,
  `BacktestResultView.tsx:42`). The real amber-400 is `#e9a94d`, amber-500 `#d98e2b`. `#e8b441` is neither.
- `#c39a3e` — `MacroChart.tsx:32` `LINE_COLOR`, commented "amber-600 — Vysted accent." amber-600 is actually `#b8701a`.
  Wrong.
- `#4ec9a3` — `EarningsSurpriseChart.tsx:30` `POSITIVE`. The token positive is `#7faa6b`; `#4ec9a3` is a cold teal-green,
  exactly the "cyan cliché" the design system explicitly forbids (`DESIGN_SYSTEM.md:24`). It already broke the theme.

### 7.4 Literal black/white Tailwind utilities (token-bypass, not hex)

- `src/components/ui/dialog.tsx:34` — overlay `bg-black/50` (should arguably be a charcoal/backdrop token).
- `src/components/ui/button.tsx:14` — destructive variant `text-white`.
- Node editor backdrops use `bg-charcoal-950/60` (tokened) — `NodeEditorPanel.tsx:737`, `workflow-save-dialog.tsx:69`.

### 7.5 Radius drift

- `dialog.tsx:56` uses `rounded-lg` (Tailwind default 0.5rem), not the panel radius token (0.375rem). `dialog.tsx:65`
  uses `rounded-xs`. `--radius` in `globals.css:31` is a literal duplicate of 0.375rem rather than `var(--radius-panel)`.

### 7.6 Test-file hex (cosmetic, update for consistency, not runtime)

`src/lib/workspace.test.ts:151,162,192`, `src/modules/chart/ChartPanel.test.tsx:496`,
`src/store/chart-drawings.test.ts:12` reference `#e9a94d`/`#8fa67c`/`#fff` as expected drawing-style defaults — they
will need updating if the default drawing color changes.

### 7.7 ReactFlow node editor (Tailwind classes, themeable; canvas dots are library default)

- `src/modules/node-editor/VystedNode.tsx:42-67` — `border-charcoal-700 bg-charcoal-850`, selected
  `border-amber-500 shadow-amber-500/20`, handles `!border-amber-400 !bg-amber-400`.
- `NodeEditorPanel.tsx:472` — `<Background gap={16} size={1} />` uses ReactFlow's **default dot color** (no color prop),
  so the canvas grid dots are NOT themed by tokens and NOT by a hardcoded value here — they fall to the library default.
  Worth an explicit `color`/`bgColor` prop in the re-skin.
- Run/save overlays (`workflow-run-overlay.tsx`, `workflow-save-dialog.tsx`) use amber-500/amber-400 + charcoal classes
  (tokened, themeable).

---

## 8. Exactly what to change to re-skin app-wide ("Claude after dark")

**Tier 1 — the centralized system (re-skins ~95% of pixels):**

1. `styles/tokens.css:19-73` — replace the palette values (charcoal/amber/brass/lume/sage/signal), fonts, radius, motion.
   Renaming token _families_ (e.g. amber→something) is a bigger blast: 43 files use `amber-*` (123 lines) and 44 use
   `charcoal-*`. Cheapest path = keep token NAMES, change VALUES. If renaming, it's a project-wide find/replace of class
   names too.
2. `src/app/globals.css`:
   - `@theme inline` 18 semantic mappings (`12-32`) + `--radius` literal (`31`).
   - Composite chrome vars (`40-46`): `--hairline`, `--hairline-strong`, `--bezel-shadow`, `--glow-amber` — all raw RGB,
     must be hand-edited (they don't follow token renames).
   - Base atmosphere/selection/focus hardcoded amber RGB: `73` (bloom), `104` (selection), grain opacity `86`.
   - `.hud-label` brass color (`123`).
   - `.dockview-theme-vysted` block (`154-189`) incl. drag-over RGB `174` and active-tab amber `183`.
   - Scrollbar RGB (`204,211,217`).
3. `src/app/layout.tsx:2,5-15` — swap fonts; mirror the fallback chains in `tokens.css:64-65`.
4. `src/app/page.tsx:79-82` — the wordmark typography/text decision (serif + amber-400 + 0.18em + brass "Terminal").
5. `docs/DESIGN_SYSTEM.md` — rewrite (pure docs; flag as the old spec being retired).

**Tier 2 — the canvas leak (must be edited file-by-file, NOT carried by tokens):** 6. Six lightweight-charts theme blocks: `ChartPanel.tsx:66-88`, `YieldCurvePanel.tsx:32-45`,
`PriceTargetTimeline.tsx:17-30`, `BacktestResultView.tsx:28-42,108-109`, `MacroChart.tsx:19-32`,
`EarningsSurpriseChart.tsx:17-31`. 7. Chart accent/indicator/drawing palettes: `indicators.ts:160-165`, `drawings/base.ts:30,104`,
`drawings/factory.ts:72,75`, `drawings/renderers.ts:193,227,296`, `volume-profile-primitive.ts:33-34`,
`ichimoku-cloud-primitive.ts:22,24`, plus the `#8fa67c`/`#c8654b` at `ChartPanel.tsx:389`. 8. **Fix the 3 drift values while retiring:** `#e8b441` (×3), `#c39a3e`, `#4ec9a3` — none are tokens; `#4ec9a3` already
violates the "no cyan" rule. 9. shadcn literals: `dialog.tsx:34` (`bg-black/50`), `dialog.tsx:56` (`rounded-lg`), `button.tsx:14` (`text-white`). 10. ReactFlow `<Background>` at `NodeEditorPanel.tsx:472` — add explicit themed `color`/`bgColor`. 11. Tests asserting old hex: `workspace.test.ts:151,162,192`, `ChartPanel.test.tsx:496`, `chart-drawings.test.ts:12`.

**Tier 3 — recommended structural fix (so the next retire is one file):** centralize the canvas palette. Create a single
TS module (e.g. `src/lib/chart-theme.ts`) exporting the hex constants, and have all 6 chart files + drawings import from
it. Today each file re-declares the palette, which is why the 3 drift values diverged unnoticed. This makes the canvas
surface as close to single-source as CSS-variable-blind canvas allows.

---

## 9. Notes / non-issues verified

- **No stray Inter/Roboto/sans-serif** anywhere in source (grep hits were substring false positives: "pointer",
  "interface", "interval"). Fonts are exclusively Newsreader + JetBrains Mono.
- **`src-tauri/tauri.conf.json`** only sets `"theme": "Dark"` (window-chrome theme, line ~22); no `decorations`/
  `transparent`/`backgroundColor`/titlebar color to retheme. No Rust-side color.
- **No `tailwind.config.*`** — Tailwind 4 is CSS-only; tokens.css `@theme` is the config.
- The HTML/CSS design system is genuinely centralized; the only real leak is the canvas (charts + ReactFlow background),
  which is an inherent limitation of `<canvas>` not reading CSS variables, not a design mistake — but it does mean
  "change tokens.css and you're done" is false for the chart panels.
