# Vysted Terminal — Design System ("Claude after dark")

Phase 10. Replaces the Phase 9.5 "INSTRUMENT" amber-brass / lume-cream /
warm-brown-black chronograph system.

**Source of truth:** `styles/tokens.css` (the `@theme` token block) +
`src/app/globals.css` (shadcn semantic mapping + chrome primitives + dockview
theme). **Canvas mirror:** `src/lib/chart-theme.ts` — lightweight-charts and the
drawing primitives render to `<canvas>` and cannot read CSS variables, so they
import their palette from this one module (never re-declare hex per chart file).

## The concept

A warm **espresso near-black** base (red-brown undertone — never cold slate,
never flat `#000`) carrying a single **coral / clay accent** (`#d97757`, the
canonical Claude clay). **Cream / warm-paper** body text. A humanist display
serif (**Fraunces**, with its optical-size + SOFT axes) over a precise data mono
(**JetBrains Mono**). Bloomberg / JARVIS information density, expressed in
Claude's restrained, warm, human language.

In one line: **take the amber-brass chronograph apart, keep its density and
warmth, and rebuild it in Claude's coral-on-espresso palette with a humanist
serif nameplate.**

## Deliberately NOT

- **No cold neutrals.** Every dark is red-brown-tinted espresso, never slate /
  zinc, never flat black.
- **No cyan HUD cliché.** A cold teal (`#4ec9a3`) had drifted into the earnings
  chart; it is gone.
- **No purple/blue gradients. No Inter/Roboto.** Humanist serif display + a
  precise data mono only.
- **Not skeuomorphic.** Retired from INSTRUMENT: amber phosphor accent, brass
  bezels / gauge ticks, sage as a second accent, CRT bloom, heavy film grain,
  beveled "watch-dial" panel edges. Kept: density, warmth, tabular numerics.

## Token naming caveat (read this before touching colors)

To re-skin 80+ files with **zero edits**, the token **names** were kept from the
retired system and only the **values** changed. The names are therefore
historical, not literal:

| Token family | Renders as            |
| ------------ | --------------------- |
| `charcoal-*` | espresso near-blacks  |
| `amber-*`    | the coral/clay accent |
| `brass-*`    | warm neutral (taupe)  |
| `sage-*`     | muted clay neutral    |
| `lume`       | warm cream            |

Read the role, not the name. (A project-wide rename to `espresso-*` / `coral-*`
is an optional future cleanup; not done here to avoid an 80-file churn.)

## Tokens

### Espresso base (`charcoal-*`) — warm near-blacks, 950 deepest → 100 body text

`950 #1a1512` (root bg) · `925 #1f1916` (header/tabs) · `900 #241d19` (panel) ·
`875 #29211d` (popover/active tab) · `850 #2e2521` · `800 #352a25` (muted) ·
`700 #473a33` (borders) · `600 #5c4d44` · `500 #796759` · `400 #998778` (muted
fg) · `300 #b8a698` · `200 #d6c8bb` (chart text) · `100 #ece3d9` (body text).
Hue ~38–40° (red-brown), low chroma on the darks so the base reads warm-neutral.

### Coral accent (`amber-*`) — one hue family (~33°), states 200→600

`200 #f0c4b4` (faint glow / selection tint) · `300 #e69e84` (hover) ·
**`400 #d97757` (brand / default)** · `500 #c2603f` (pressed / active-sash) ·
`600 #a44a30` (deep border). The only accent in the system.

### Warm neutral (`brass-*`) + muted clay (`sage-*`)

No metal, no second accent. `brass-300 #a8917f` is the `.hud-label` legend tone;
`brass-400 #85705f` is the scrollbar rail tone. `sage-*` is a desaturated clay
for secondary/comparison data series so they never compete with coral.

### Cream (`lume`) `#f5f1ea`

Active-tab text, peak readouts, selection text. Warm paper-white (faintly
pink-warm, never green).

### Semantic — three distinguishable warm hues

- `--color-positive #7fa96a` (warm moss green, hue 135°) + `-bright #9fc97f`.
- `--color-negative #cf5b48` (brick red, hue 28°) + `-bright #e3705a`.
- `--color-warning #e0a458` (amber-gold, hue 70°) — **the one new token.**
  Caution states (kill-switch armed, paper-vs-live, stale data, static-IP
  banner) need a third semantic that is neither good (green), bad/loss (red),
  nor brand (coral).

> **Coral-vs-loss separation (the #1 palette risk).** Coral (brand, 33°) and
> negative (loss-red, 28°) sit close in hue. They are separated on **two axes**:
> negative is darker (L 0.60 vs 0.66) and redder + more saturated (C 0.16 vs
> 0.13). Verify a populated red/green table (Watchlist/Portfolio P&L) against a
> coral button in the same frame; pre-approved fallback negative is `#d6493a`.

### Radii / motion

`--radius-panel 0.5rem`, `--radius-control 0.375rem` (crisp but warm).
`--radius` (shadcn) tracks `--radius-panel`. Motion: calm ease-out
(`--ease-instrument`), gentle settle (`--ease-detent`, overshoot softened).

## Type

- **Fraunces** (display) — headings (`h1–h3`) + the wordmark,
  `font-optical-sizing: auto` so it uses display optics at large sizes. Variable
  `opsz` + `SOFT` axes via `next/font/google` in `layout.tsx` (`--font-fraunces`).
- **JetBrains Mono** (data) — everything else; the app's default body font with
  global `tabular-nums` (the density tell). Unchanged.

| Role                  | Face     | Size  | Weight  | Tracking  |
| --------------------- | -------- | ----- | ------- | --------- |
| Wordmark "VYSTED"     | Fraunces | 17px  | 600     | `+0.01em` |
| Panel heading (h1–h3) | Fraunces | 14–20 | 500–600 | `-0.01em` |
| HUD label / legend    | Mono     | 10px  | 400     | `0.12em`  |
| Body / control / data | Mono     | 11–12 | 400     | `0`       |

## Wordmark

A confident coral-on-espresso lockup (the old Newsreader-14px-at-0.18em mark read
as a caption): a single **coral brand pip** (8×8 rounded square) + **"VYSTED"** in
Fraunces 17px/600 warm cream + a subordinate mono **"Terminal"** descriptor.
Serif name + mono descriptor, an intentional lockup. See `src/app/page.tsx`.

## Chrome primitives (`globals.css`)

- Coral hairlines (`--hairline` coral @ 18%, `--hairline-strong` @ 32%).
- Flat panel edge (`--bezel-shadow`) — a whisper of warm depth, no metal bevel.
- `.tick-rule` is now a single flat 1px coral hairline (was a gauge-tick row).
- `--glow-coral` for active controls (`.hud-active`).
- Quiet warm atmosphere: a faint coral ambient top + soft vignette; 2% warm grain
  (down from 3.5%) to prevent gradient banding on the espresso base.
- Coral selection + coral focus ring. Warm-neutral scrollbars that light coral on
  grab (a coral rail everywhere would be too loud).
- dockview theme (`.dockview-theme-vysted`): espresso surfaces, coral active-tab
  underline + active outline + drag-over, `.dv-view` painted so over-scroll never
  reveals the WKWebView backdrop.

## Application strategy

- **Keep-names re-value** carries ~95% of pixels: 40 `amber-*`, 41 `charcoal-*`,
  2 `sage-*`, 1 `lume` consumer files re-skin with **zero edits**.
- **Tier 1 (4 files):** `styles/tokens.css`, `src/app/globals.css`,
  `src/app/layout.tsx` (Fraunces), `src/app/page.tsx` (wordmark + dropped bezel).
- **Canvas (12 files):** all import `src/lib/chart-theme.ts` — the single source
  for chart surfaces, coral accent, semantic colors, fill helpers, and the
  indicator palette. This is also why three values had silently drifted
  (`#e8b441`, `#c39a3e`, the cyan `#4ec9a3`) — six independent copies; now one.
- shadcn dialog overlay → espresso (`bg-charcoal-950/70`); ReactFlow node-editor
  `Background` dots pinned to the espresso palette (it isn't CSS-themed).

## Known deviations (deliberate)

- The **destructive button** keeps `text-white` (not warm cream) — a danger
  control where max legibility on the brick-red beats palette purity (cream on
  `#cf5b48` is ~3.1:1; white ~4:1). Low-frequency, high-stakes; legibility wins.
- The node-editor SAR uptrend dot and the indicator overlay palette shifted tone
  slightly (sage→clay-neutral, and the indicator order is now the curated
  `chart-theme` palette) — intentional consequence of single-sourcing.

## Customizable

Re-tuning one token in `tokens.css` (+ its `chart-theme.ts` mirror) re-skins the
app. A light theme slots in via the same `@theme inline` mapping (light theme is
a documented future item — dark only ships now).

## Verification

The agent harness cannot drive the GUI; populated-state visual sign-off is the
operator's, per the CLAUDE.md visual protocol (AAPL anchor + 5-panel cockpit +
both 1920×1080 and 2560×1440). Named gates: (1) the **coral-vs-loss** eyeball on a
populated Watchlist/Portfolio against a coral button; (2) the **destructive-button
contrast** check; (3) confirm **Fraunces** actually loads (not the Georgia
fallback) in the wordmark + headings.
