# Vysted Terminal — Design System ("INSTRUMENT")

Phase 9.5 / Track D. The one coherent visual language for the whole app. This
documents the decisions so they can be reacted to and extended; the source of
truth is `styles/tokens.css` (palette/type/radius/motion) + `src/app/globals.css`
(semantic mapping, atmosphere, instrument chrome, dockview theme).

## The concept

**A warm, machined, analog-precision terminal.** The amber phosphor of an
early-90s Bloomberg CRT meeting the dial of a fine mechanical chronograph:
patinated-brass bezels, lume-cream highlights, amber HUD accents on a _warm
brown-black_ — Bloomberg-grade density, restrained and precise, legible.

It is the operator's anchor made literal: 90s-vintage-classy, warm over
harsh-modernism, mechanical-instrument texture (fine watches, analog gauges),
restrained and precise, high-density but legible — Tony Stark / JARVIS technical
warmth.

### Deliberately NOT (the generic-AI-dashboard traps we avoid)

- **No cold neutrals.** Every dark is brown-tinted charcoal, never slate/zinc or
  flat `#000`.
- **No cyan HUD cliché.** Warmth comes from amber + patinated brass, not the
  default sci-fi cyan.
- **No purple/blue gradients, no Inter/Roboto.** Type is an editorial serif
  (Newsreader) for headings + a precise monospace (JetBrains Mono) for data.
- **No pillowy cards.** Crisp radii, hairline bezels, machined edges.

## Tokens

### Color (`styles/tokens.css`)

- **Charcoal 950→100** — the warm dial face, graduated for elevation (950 = the
  deepest well; 925/900/875 = stacked surfaces; 800/700 = raised chrome &
  borders). Brown-tinted throughout.
- **Amber 200→600** — the primary HUD accent (phosphor-warm). `amber-400` is the
  brand/primary; `amber-200` for fine highlights/glow.
- **Brass 200→600** — patinated metal for bezels, hairline rules, and gauge
  ticks. Desaturated bronze (instrument patina), never shiny gold.
- **Lume** (`#f5efe0`) — the watch-lume cream for peak readouts / active state.
- **Sage 300→500** — the cool counterpoint accent.
- **Signal** — `positive` / `negative` (+ `-bright` variants) for gains/losses,
  warm-tuned to the dial rather than pure RGB green/red.

### Type

- **Serif (Newsreader)** — headings + the `VYSTED` wordmark; high-contrast,
  editorial, "fine-watch nameplate." Slightly negative tracking.
- **Mono (JetBrains Mono)** — body, data, every numeric. **Tabular figures are on
  globally** (`font-variant-numeric: tabular-nums`) so prices, tables, and stats
  align like a gauge readout — the single biggest "instrument" tell.

### Radius / density / motion

- **Radius** — crisp: `--radius-panel` 6px, `--radius-control` 4px. Machined, not
  soft.
- **Density** — high. Mono at 11–12px for chrome/labels; compact control heights.
- **Motion** — `--ease-instrument` `cubic-bezier(0.2,0.8,0.2,1)` (precise) and
  `--ease-detent` (a slight overshoot "click"). Short durations (~120ms).

## Instrument chrome primitives (`globals.css`)

- `--hairline` / `--hairline-strong` — brass-tinted 1px rules (the dial's fine
  divisions). Used as dockview separators and section dividers.
- `--bezel-shadow` + `.instrument-bezel` — a beveled panel edge (top lume
  highlight + dark inset), the watch-bezel treatment for chrome surfaces.
- `.tick-rule` — a row of fine brass gauge ticks (under the header fascia).
- `.hud-label` — uppercase, tracked, brass section legend.
- `.hud-active` / `--glow-amber` — amber bloom for an active/primary control.
- **Atmosphere** — a fixed body layer: a faint amber phosphor bloom at the top
  edge, a subtle radial vignette, and a restrained film/phosphor **grain**
  overlay (~3.5% opacity — texture, not noise).
- **Selection** amber-phosphor; **focus** a crisp 1px amber HUD ring everywhere.
- **Scrollbars** brass-tinted thin rails (Chromium + Firefox parity).

## Application strategy (why it reaches the whole app)

The palette and chrome are centralized, so the system propagates without touching
every panel:

1. **Tokens** are Tailwind utilities (`bg-charcoal-900`, `text-amber-400`,
   `text-brass-300`, …) — every existing panel already consumes them, so
   re-tuning the token values + adding brass/lume shifts the whole app.
2. **`globals.css` base** (tabular numerics, selection, focus, serif headings,
   atmosphere, scrollbars) applies to every surface automatically.
3. **The dockview theme** restyles the cockpit frame (brass hairline separators,
   amber active-tab tick, warm drag-over glow) for all panels at once.
4. **The header fascia** (`page.tsx`) is the machined brand anchor: serif wordmark
   - brass tick-rule + bezel.

Opt-in primitives (`.hud-label`, `.tick-rule`, `.instrument-bezel`,
`.hud-active`) let individual panels deepen the instrument feel over time.

## Customizable

Everything is a CSS variable in `styles/tokens.css` + `globals.css`. Re-tuning a
single token (e.g. the amber hue, the grain opacity, a radius) re-skins the whole
terminal — true to the "sandbox / make it yours" product intent. A future light
theme slots in by overriding the same semantic `@theme inline` mapping.

## Verification note

Live visual capture (populated-state screenshots at both resolutions per the
CLAUDE.md visual-verification protocol) is **operator-manual** for this pass: the
agent harness runs the Tauri bundle at click-tier, which cannot drive the GUI
with real data, and `chrome-devtools` cannot synthesize the trusted events the
canvas surfaces need. The system is verified to **compile and pass `pnpm
ci-local`**; the rendered review (and the per-release `docs/screenshots/` set) is
the operator's morning gate.
