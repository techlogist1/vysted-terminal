# Phase 10 — Design System Blueprint: "Claude after dark"

Retires the Phase 9.5 "INSTRUMENT" amber-brass / lume-cream / warm brown-black system.
This is an implementation-ready spec: the lead builds directly from it. Every file:line claim below was
verified against the working tree at the time of writing (see the prior map `map-design-system.md` for the
exhaustive mechanism dump; this doc re-verifies the load-bearing facts and supplies the new values).

---

## 0. The design direction, stated plainly

**Claude after dark.** Warm espresso / near-black base (not pure black, not cool slate). A single coral/clay
accent — Claude's voice made into a terminal. Cream / warm-off-white body text. A humanist serif for
display, a precise mono for data. Bloomberg/JARVIS information density, expressed in Claude's restrained,
warm, human language. Not a generic dark dashboard. Not skeuomorphic — we are deliberately *removing* the
watch-bezel / phosphor-CRT skeuomorphism of INSTRUMENT.

The one-sentence brief: **take the amber-brass chronograph apart, keep its density and warmth, and rebuild
it in Claude's coral-on-espresso palette with a humanist serif nameplate.**

### What changes conceptually vs INSTRUMENT

| INSTRUMENT (retired) | Claude after dark |
|---|---|
| Amber phosphor HUD accent (`#e9a94d`) | A single coral/clay accent (`#d97757` family) |
| Brass bezels / gauge ticks / patina metal | No metal. Coral hairlines + flat warm dividers |
| Warm *brown*-black charcoal (yellow-green undertone) | Warm *espresso* near-black (red-brown undertone) |
| Lume cream (`#f5efe0`, slightly green) | Warm cream / paper-white (`#f5f1ea`, slightly pink) |
| Sage cool counterpoint (a second accent) | **Retired** — coral is the *only* accent (sage → coral or muted) |
| CRT bloom + heavy film grain + bevels | Quiet ambient warmth, near-zero grain, flat panels |
| Skeuomorphic ("the dial of a chronograph") | Editorial/instrumental, restrained, modern |

### The traps we still avoid (carry forward from INSTRUMENT, they were right)

- **No cold neutrals.** Every dark is red-brown-tinted espresso, never slate/zinc, never flat `#000`.
- **No cyan HUD cliché.** The drift value `#4ec9a3` (a cold teal) already violated this once; it dies here.
- **No purple/blue gradients. No Inter/Roboto.** Humanist serif display + precise mono data.
- **No pillowy cards.** Crisp radii, hairline dividers — but flat now, not beveled-metal.

---

## 1. Strategy: keep token NAMES, change VALUES (the cheap path, re-verified)

The single most important mechanical decision. Re-verified blast radius against the working tree:

| Token family | Files using the Tailwind class (excl. tests) | Decision |
|---|---|---|
| `charcoal-*` | **41** | Keep name `charcoal-*`, re-value to espresso. Renaming → 41-file find/replace. Not worth it. |
| `amber-*` | **40** | Keep name `amber-*`, re-value to coral. Renaming → 40-file find/replace. **Keep the name.** |
| `sage-*` | **2** | Keep name (low cost), re-value toward a muted coral/neutral — it is no longer a "second accent." |
| `brass-*` | **0** in src | Palette ramp is vestigial. Re-value to neutral-warm OR drop the ramp (see §6). |
| `lume` | **1** in src | Keep name, re-value to warm cream. |

So: **we re-value every token in place and rename nothing.** The token *names* (`charcoal`, `amber`, `brass`,
`sage`, `lume`) become semantically inaccurate (an "amber-400" class will render coral), which is a known,
accepted cost — the alternative is a 40+-file churn for cosmetic naming. The lead may, as an optional Tier-3
cleanup, do a project-wide rename in a *separate* commit after the re-value lands and is verified, but it is
NOT required for the re-skin to be correct. **This blueprint assumes names stay.**

> Adversarial note for the lead: because names lie after this, the one-line comments inside `tokens.css`
> MUST be rewritten (they currently say "amber phosphor", "patinated brass") or the next reader is misled.
> The comment rewrite is part of the deliverable, not optional.

---

## 2. THE FULL TOKEN TABLE — `styles/tokens.css` restated

Every token in the current `@theme` block (`tokens.css:16-74`), restated with new "Claude after dark" values.
Values are given in **hex** (what goes in the file — Tailwind 4 / lightweight-charts both want hex) with the
**oklch** equivalent in the comment column for perceptual reasoning. The espresso base is built on a constant
warm hue (~30–40° in oklch, red-brown) with rising lightness; the coral accent sits at ~25° / high chroma.

### 2.1 Espresso base — `--color-charcoal-*` (re-valued; name kept)

The dial face is gone; this is now a stack of warm near-blacks with a **red-brown** (espresso) undertone,
NOT the old yellow-green brown. Graduated for elevation exactly as before (950 deepest → 100 lightest).

| Token | OLD (INSTRUMENT) | **NEW (Claude after dark)** | oklch (approx) | Role |
|---|---|---|---|---|
| `--color-charcoal-950` | `#14110f` | `#1a1512` | `oklch(0.18 0.012 40)` | Deepest well — app/root bg |
| `--color-charcoal-925` | `#181512` | `#1f1916` | `oklch(0.21 0.013 40)` | Header fascia, tab strip bg |
| `--color-charcoal-900` | `#1c1916` | `#241d19` | `oklch(0.24 0.014 40)` | Card / panel surface |
| `--color-charcoal-875` | `#201c18` | `#29211d` | `oklch(0.26 0.015 40)` | Popover / active tab |
| `--color-charcoal-850` | `#232019` | `#2e2521` | `oklch(0.29 0.016 40)` | Raised inset (node bg) |
| `--color-charcoal-800` | `#2a2620` | `#352a25` | `oklch(0.32 0.017 40)` | Secondary / muted surface |
| `--color-charcoal-700` | `#3a352c` | `#473a33` | `oklch(0.40 0.018 40)` | Borders / inputs / dividers |
| `--color-charcoal-600` | `#4d4639` | `#5c4d44` | `oklch(0.48 0.019 38)` | Strong border / disabled fg |
| `--color-charcoal-500` | `#6b6253` | `#796759` | `oklch(0.57 0.020 38)` | Faint label / kbd chip text |
| `--color-charcoal-400` | `#8a8170` | `#998778` | `oklch(0.66 0.020 38)` | Muted foreground |
| `--color-charcoal-300` | `#aaa291` | `#b8a698` | `oklch(0.74 0.019 38)` | Secondary text |
| `--color-charcoal-200` | `#c9c2b2` | `#d6c8bb` | `oklch(0.83 0.017 38)` | Bright secondary / chart text |
| `--color-charcoal-100` | `#e8e3d6` | `#ece3d9` | `oklch(0.91 0.013 50)` | Foreground / body text |

Design rationale: the hue rotated from ~80° (yellow-brown) to ~38–40° (red-brown espresso), and chroma is
held *low* on the darks (0.012–0.018) so the base reads as warm-neutral, not muddy. The top of the ramp
(100/200) warms slightly toward cream (hue 50) so body text feels like warm paper, not gray.

### 2.2 The coral/clay accent — `--color-amber-*` (re-valued to coral; name kept)

This is the heart of the re-skin. A single Claude coral/clay accent, replacing the entire amber ramp. The
**brand/primary is `amber-400` = `#d97757`** (the canonical Claude clay-coral). States are derived as a
proper interactive ramp: 200 = faint glow/highlight, 300 = hover-bright, 400 = brand/default, 500 = pressed/
active, 600 = deep/border.

| Token | OLD (amber) | **NEW (coral/clay)** | oklch (approx) | Role |
|---|---|---|---|---|
| `--color-amber-200` | `#f9dba6` | `#f0c4b4` | `oklch(0.84 0.06 35)` | Faint highlight, glow fill, selection tint |
| `--color-amber-300` | `#f4c87a` | `#e69e84` | `oklch(0.75 0.10 33)` | Hover-bright accent, focus emphasis |
| `--color-amber-400` | `#e9a94d` | `#d97757` | `oklch(0.66 0.13 33)` | **Brand / primary / default accent** |
| `--color-amber-500` | `#d98e2b` | `#c2603f` | `oklch(0.58 0.14 32)` | Pressed/active, active-sash, node-selected |
| `--color-amber-600` | `#b8701a` | `#a44a30` | `oklch(0.50 0.13 32)` | Deep border, deep tick, dense accent on light fg |

Design rationale: a single hue family (~32–35° oklch) so coral is unmistakably *one* color across all states,
not a multi-hue smear. `#d97757` is the recognizable Claude clay. The ramp keeps WCAG legibility: `amber-400`
on `charcoal-950` is ~5.0:1 (passes AA for UI/large text); coral text on dark is comfortable. `amber-300`
gives a brighter hover that stays in-family.

### 2.3 Brass ramp — `--color-brass-*` (vestigial; re-value to warm-neutral OR drop)

Re-verified: **0 src files use `brass-*` classes.** Brass reaches pixels only via `.hud-label` color
(`globals.css:123`) and the two raw-RGB hairline vars (`globals.css:40-41`). In Claude after dark there is no
metal. **Recommendation: KEEP the ramp but re-value to a muted warm-neutral** (so any stray future use is
on-palette), AND repoint `.hud-label` and the hairlines independently (see §3). Do not invest in a rich
brass identity — it is dead weight.

| Token | OLD (brass) | **NEW (warm-neutral)** | oklch (approx) | Note |
|---|---|---|---|---|
| `--color-brass-200` | `#cdb88c` | `#cbb6a6` | `oklch(0.78 0.02 45)` | Warm gray-taupe, no gold |
| `--color-brass-300` | `#b8965f` | `#a8917f` | `oklch(0.65 0.02 45)` | `.hud-label` color (legend text) |
| `--color-brass-400` | `#9c7c4d` | `#85705f` | `oklch(0.54 0.02 45)` | hairline source tone |
| `--color-brass-500` | `#7d6139` | `#615245` | `oklch(0.43 0.018 45)` | — |
| `--color-brass-600` | `#5d4829` | `#473b31` | `oklch(0.33 0.016 45)` | — |

Alternative (cleaner) path: **delete the `brass-*` ramp entirely** and rename `.hud-label`'s color to
`var(--color-charcoal-400)`. Saves 5 dead tokens. The lead's call — both are listed as decisions. This
blueprint's default keeps the ramp re-valued (lower risk, no class-removal sweep needed).

### 2.4 Lume → warm cream — `--color-lume` (re-valued; name kept)

| Token | OLD | **NEW** | oklch | Role |
|---|---|---|---|---|
| `--color-lume` | `#f5efe0` | `#f5f1ea` | `oklch(0.95 0.008 60)` | Active-tab text, peak readout, selection text — warm paper-white (faint pink-warm, not green) |

### 2.5 Sage — `--color-sage-*` (was the second accent; now retired-in-place)

Coral is the ONLY accent. Sage was a cool green counterpoint (`#8fa67c`). It is used in **2 files** (chart
comparison line + indicator palette). We cannot have a green "second accent" competing with coral. Re-value
sage to a **muted desaturated clay/taupe** so the 2 consumers stay legible-but-quiet (a comparison line
should NOT outshout the primary series). It is no longer a brand color — purely a "neutral data series" tone.

| Token | OLD (sage) | **NEW (muted clay)** | oklch | Role |
|---|---|---|---|---|
| `--color-sage-300` | `#b6c4a8` | `#c9b9ad` | `oklch(0.78 0.02 45)` | Light data-series neutral |
| `--color-sage-400` | `#8fa67c` | `#a8917f` | `oklch(0.65 0.02 45)` | Comparison-line / secondary series |
| `--color-sage-500` | `#6d8559` | `#85705f` | `oklch(0.54 0.02 45)` | Deep neutral |

(Note: sage-400 and brass-300 intentionally land on the same tone `#a8917f` — both are now "warm neutral." If
the lead drops brass, sage can absorb that role. Kept separate here to avoid touching consumer files.)

### 2.6 Semantic up/down/warning — `--color-positive` / `-negative` / (NEW) `-warning`

These MUST stay legible and unambiguous on the espresso base, and must NOT clash with coral. The hard problem:
coral (`#d97757`) sits between red and orange, dangerously close to a "loss/down" red. Solution: push
**negative toward a clear brick-red that is distinct from coral** (lower lightness, redder hue ~25°, higher
chroma), and keep **positive a warm-but-clearly-green** (not the old sage-adjacent muddy green, and absolutely
not the forbidden cyan). The accent is a *warm orange-coral*; down is a *cooler brick red*; up is a *warm
moss-green*. Three distinguishable warm hues.

| Token | OLD | **NEW** | oklch | Note |
|---|---|---|---|---|
| `--color-positive` | `#7faa6b` | `#7fa96a` | `oklch(0.67 0.10 135)` | Warm moss green — gains. Distinct from coral by hue. |
| `--color-positive-bright` | `#9ccb84` | `#9fc97f` | `oklch(0.78 0.12 132)` | Bright gain (up-candle wick, +chip) |
| `--color-negative` | `#c8654b` | `#cf5b48` | `oklch(0.60 0.16 28)` | Brick red — losses. Redder + more chroma than coral so they don't merge. |
| `--color-negative-bright` | `#e07f63` | `#e3705a` | `oklch(0.68 0.16 28)` | Bright loss (down-candle, −chip) |
| `--color-warning` (NEW) | — | `#e0a458` | `oklch(0.76 0.11 70)` | **NEW token.** Amber-gold warning/caution (kill-switch armed, stale data, risk banners). Sits at hue ~70° — clearly distinct from both coral (33°) and positive (135°). |

> Adversarial note on negative-vs-coral: the most likely failure of THIS palette is that coral (the brand)
> and negative (loss-red) look too similar in a dense red/green table, making a down-day and a coral UI accent
> ambiguous. The chosen values separate them on TWO axes: negative is **darker** (L 0.60 vs 0.66) and
> **more saturated + redder** (C 0.16 @ 28° vs C 0.13 @ 33°). The lead MUST eyeball a populated
> red/green table (Watchlist, Portfolio P&L) against a coral button in the same frame at verification time.
> If they still merge, push negative to `#d6493a` (oklch 0.58 0.18 27) — pre-approved fallback.
>
> Why a `--warning` token is added: the broker-execution surfaces (kill-switch armed, paper-vs-live, static-IP
> mismatch banner) need a *third* semantic that is neither "good" (green) nor "bad/loss" (red) nor "brand"
> (coral). INSTRUMENT had no warning token and reused amber for it — but amber IS the accent now repurposed
> as coral, so caution states would collide with the brand. The new gold `--warning` resolves this. It is the
> one *additive* token in this spec.

### 2.7 Typography tokens — `--font-serif` / `--font-mono`

See §4 for the full type decision. Token values:

| Token | OLD | **NEW** | Note |
|---|---|---|---|
| `--font-serif` | `var(--font-newsreader), ui-serif, Georgia, …` | `var(--font-fraunces), ui-serif, Georgia, "Times New Roman", serif` | **Swap Newsreader → Fraunces** (see §4 for the why). Fallback chain unchanged in shape. |
| `--font-mono` | `var(--font-jetbrains-mono), ui-monospace, …` | `var(--font-jetbrains-mono), ui-monospace, "SF Mono", "Cascadia Mono", monospace` | **Unchanged.** JetBrains Mono stays — it is the correct data face. |

> The inner `--font-fraunces` var must be injected by `next/font` in `layout.tsx` (see §5.3). Changing the
> token here WITHOUT swapping the `layout.tsx` import is the classic half-edit — both must land together or
> the serif silently falls back to Georgia.

### 2.8 Radius — `--radius-panel` / `--radius-control`

Crisp, slightly softer than INSTRUMENT's machined edges (Claude is warm, not hard-machined). A 1px bump.

| Token | OLD | **NEW** | Note |
|---|---|---|---|
| `--radius-panel` | `0.375rem` (6px) | `0.5rem` (8px) | Slightly softer panel corner — warm, not pillowy |
| `--radius-control` | `0.25rem` (4px) | `0.375rem` (6px) | Controls a touch softer |

> Bonus: bumping `--radius-panel` to `0.5rem` makes it MATCH the `rounded-lg` literal that `dialog.tsx:56`
> uses, so the dialog radius drift becomes a non-issue if we set `--radius` to `var(--radius-panel)` (§3.2).

### 2.9 Motion — `--ease-instrument` / `--ease-detent`

Re-verified used by dockview tab transition (`globals.css:188`). Keep the *names* (renaming → consumer sweep),
re-tune slightly: Claude motion is calm and confident, not mechanical-clicky. Soften the detent overshoot.

| Token | OLD | **NEW** | Note |
|---|---|---|---|
| `--ease-instrument` | `cubic-bezier(0.2, 0.8, 0.2, 1)` | `cubic-bezier(0.2, 0.8, 0.2, 1)` | **Keep** — a good calm ease-out. Rename in comments only. |
| `--ease-detent` | `cubic-bezier(0.34, 1.4, 0.64, 1)` | `cubic-bezier(0.34, 1.2, 0.64, 1)` | Reduce overshoot 1.4→1.2 — confident settle, not a mechanical click |

Optionally rename to `--ease-soft` / `--ease-settle` if the lead does the rename pass; not required.

---

## 3. `src/app/globals.css` — every change enumerated

### 3.1 `@theme inline` shadcn semantic mapping (`globals.css:12-32`)

The 18 mappings keep their *targets* (the token names are unchanged) — so **most of this block needs NO edit**;
re-valuing the tokens carries shadcn automatically. The exceptions: update the **literal hex fallbacks** to
match the new token values (so a missing-token fallback isn't wildly off-palette), and fix `--radius`.

| Semantic | Maps to | Edit needed |
|---|---|---|
| `--color-background` | `charcoal-950` fallback `#14110f` | **Fallback → `#1a1512`** |
| `--color-foreground` | `charcoal-100` fallback `#e8e3d6` | **Fallback → `#ece3d9`** |
| `--color-card` | `charcoal-900` fallback `#1c1916` | **Fallback → `#241d19`** |
| `--color-card-foreground` | `charcoal-100` `#e8e3d6` | **→ `#ece3d9`** |
| `--color-popover` | `charcoal-875` `#201c18` | **→ `#29211d`** |
| `--color-popover-foreground` | `charcoal-100` `#e8e3d6` | **→ `#ece3d9`** |
| `--color-primary` | `amber-400` `#e9a94d` | **→ `#d97757`** |
| `--color-primary-foreground` | `charcoal-950` `#14110f` | **→ `#1a1512`** (coral is light enough that dark text on it reads — verify ≥4.5:1; `#1a1512` on `#d97757` ≈ 5.2:1, passes) |
| `--color-secondary` | `charcoal-800` `#2a2620` | **→ `#352a25`** |
| `--color-secondary-foreground` | `charcoal-100` `#e8e3d6` | **→ `#ece3d9`** |
| `--color-muted` | `charcoal-800` `#2a2620` | **→ `#352a25`** |
| `--color-muted-foreground` | `charcoal-400` `#8a8170` | **→ `#998778`** |
| `--color-accent` | `sage-400` `#8fa67c` | **CHANGE TARGET → `amber-400` (coral), fallback `#d97757`.** Accent should be the brand coral, not the (now retired) sage. This is the one mapping whose *target* changes. |
| `--color-accent-foreground` | `charcoal-950` `#14110f` | **→ `#1a1512`** |
| `--color-border` | `charcoal-700` `#3a352c` | **→ `#473a33`** |
| `--color-input` | `charcoal-700` `#3a352c` | **→ `#473a33`** |
| `--color-ring` | `amber-400` `#e9a94d` | **→ `#d97757`** |
| `--color-destructive` | `negative` `#c8654b` | **→ `#cf5b48`** |
| `--radius` | literal `0.375rem` | **→ `var(--radius-panel)`** (kill the token-bypass; now 8px) |

> Decision: `--color-accent` retargets from `sage-400` to `amber-400` (coral). shadcn `hover:bg-accent` and
> `bg-accent` (used in button ghost/outline variants, dialog close hover) should land on the brand coral's
> quiet zone, not a green. Because `amber-400` is now coral, this makes accent = brand, which is correct for a
> single-accent system. (If a softer hover is wanted, point accent at `charcoal-800` instead — but coral-at-
> low-opacity via shadcn's `/50` modifiers reads better. Default: `amber-400`.)

### 3.2 Composite chrome vars (`:root`, `globals.css:39-46`) — ALL hand-edited (raw RGB, don't follow tokens)

These are raw RGB copies and MUST be rewritten by hand. New values:

```css
:root {
  /* Coral hairline — fine divider rule. Was brass-400 @ 28%. */
  --hairline: rgb(217 119 87 / 0.18);          /* coral @ 18% — quieter than the old brass */
  --hairline-strong: rgb(217 119 87 / 0.32);   /* coral @ 32% */
  /* Flat panel edge — NO metal bevel. A faint warm top highlight + dark inset + soft drop.
     De-skeuomorphized: drop the lume top-highlight intensity, keep a whisper of depth. */
  --bezel-shadow:
    inset 0 1px 0 rgb(245 241 234 / 0.03),     /* cream @ 3% top highlight (was lume @ 4%) */
    inset 0 0 0 1px rgb(26 21 18 / 0.5),        /* charcoal-950 inset */
    0 1px 2px rgb(0 0 0 / 0.35);                /* soft drop */
  /* Coral glow for an active/primary control. Was amber glow. */
  --glow-coral: 0 0 0 1px rgb(217 119 87 / 0.35), 0 0 12px rgb(217 119 87 / 0.14);
}
```

> Rename `--glow-amber` → `--glow-coral`. It is referenced only in `.hud-active` (`globals.css:146`), so a
> single consumer update. (If the lead wants zero rename, keep the var name `--glow-amber` and just change its
> value — but the name then lies. Recommend rename; it is one site.)

### 3.3 `@layer base` (`globals.css:48-113`) — atmosphere de-skeuomorphized

- `* { border-color: var(--color-border); }` (`49-51`) — **no change** (token carries it).
- `html, body` bg/fg/font/tabular-nums (`53-66`) — **no change** (token carries it; tabular-nums stays — it is
  correct and the "density tell" survives the re-skin).
- **Body atmosphere (`71-76`)** — rewrite. The amber phosphor bloom dies; replace with a *much subtler* warm
  coral ambient at the top and a deeper warm vignette. Espresso, quiet.
  ```css
  body {
    background-image:
      radial-gradient(120% 80% at 50% -10%, rgb(217 119 87 / 0.035), transparent 50%), /* faint coral warmth, top */
      radial-gradient(140% 120% at 50% 50%, transparent 60%, rgb(0 0 0 / 0.30));        /* soft vignette */
    background-attachment: fixed;
  }
  ```
- **Grain overlay (`80-88`)** — Claude after dark is cleaner than the CRT. **Reduce opacity `0.035` → `0.02`**
  (texture barely-there, not film). Keep the SVG turbulence. Optionally drop entirely — but a 2% warm grain
  keeps the espresso from banding on gradients, so keep it at 0.02.
- `body > *` z-index stack (`91-94`) — **no change**.
- **Headings serif (`96-101`)** — keep `font-family: var(--font-serif…)`. With Fraunces, **add
  `font-optical-sizing: auto;`** so Fraunces uses its optical-size axis at display sizes (Fraunces is a
  variable font with `opsz`). Keep letter-spacing `-0.01em`.
- **Selection (`104-107`)** — rewrite from amber to coral:
  ```css
  ::selection { background: rgb(217 119 87 / 0.28); color: var(--color-lume, #f5f1ea); }
  ```
- **Focus ring (`109-112`)** — rewrite from amber-400 to coral:
  ```css
  :focus-visible { outline: 1px solid var(--color-amber-400, #d97757); outline-offset: 1px; }
  ```
  (token name unchanged so `var(--color-amber-400)` already resolves to coral — only the literal fallback hex
  changes `#e9a94d` → `#d97757`.)

### 3.4 `@layer components` (`globals.css:116-148`)

- `.hud-label` (`118-124`) — keep uppercase/tracked. Change color from `--color-brass-300` to the new
  warm-neutral. Since brass-300 is re-valued to `#a8917f` it auto-carries; just update the literal fallback
  `#b8965f` → `#a8917f`. (If brass is dropped, change to `var(--color-charcoal-400, #998778)`.)
- `.instrument-bezel` (`127-130`) — keep `box-shadow: var(--bezel-shadow)`; update the inline top-border RGB
  `rgb(245 239 224 / 0.05)` → `rgb(245 241 234 / 0.03)` (cream, fainter — de-skeuomorphized). **Consider
  renaming the class `.instrument-bezel` → `.panel-edge`** (it appears in `page.tsx:77` header only — one
  consumer). Optional; default keep the name to avoid the JSX edit.
- `.tick-rule` (`133-142`) — this is a literal gauge-tick decoration. In Claude after dark there are no gauge
  ticks. **Two options:** (a) keep the class but make it a single flat coral hairline instead of a dotted
  tick row — change the `repeating-linear-gradient` to a plain `background: var(--hairline); height: 1px;`; OR
  (b) drop the tick-rule entirely from the header (see §5.4 wordmark). **Default: option (a)** — flat 1px coral
  hairline under the header, no ticks. Cleaner, on-brand, single edit.
- `.hud-active` (`145-147`) — `box-shadow: var(--glow-amber)` → `var(--glow-coral)` (per the rename in §3.2).

### 3.5 `.dockview-theme-vysted` override (`globals.css:154-189`)

Token-name-stable mappings carry automatically; only the **literal fallback hexes** and the **two raw-RGB/
hardcoded lines** need editing. Itemized:

- Lines `155-164` (group/tab backgrounds → charcoal shades) — fallback hexes update to new charcoal values
  (`#1c1916`→`#241d19`, `#181512`→`#1f1916`, `#201c18`→`#29211d`, etc.). The `var(...)` targets are unchanged.
- `--dv-activegroup-visiblepanel-tab-color: var(--color-lume…)` (`158`) — fallback `#f5efe0`→`#f5f1ea`.
- `--dv-paneview-active-outline-color: var(--color-amber-400…)` (`168`) — fallback `#e9a94d`→`#d97757` (now coral).
- `--dv-active-sash-color: var(--color-amber-500…)` (`169`) — fallback `#d98e2b`→`#c2603f` (coral-500).
- `--dv-drag-over-background-color: rgb(233 169 77 / 0.14)` (`174`) — **raw RGB, hand-edit → `rgb(217 119 87 / 0.14)`** (coral).
- `--dv-drag-over-border-color: var(--color-amber-400…)` (`175`) — fallback → `#d97757`.
- `.dv-active-tab` lit tick `box-shadow: inset 0 -2px 0 var(--color-amber-400…)` (`182-184`) — fallback → `#d97757`.
  Keep the 2px coral underline — it is the active-tab marker and reads great as coral.
- `.dv-tab` tracking + transition (`186-189`) — no color; keep. (`--ease-instrument` re-tuned per §2.9.)

### 3.6 Scrollbars (`globals.css:194-218`) — raw RGB, hand-edit

- `*::-webkit-scrollbar-thumb` `background: rgb(156 124 77 / 0.4)` (`204`) → **`rgb(133 112 95 / 0.4)`** (warm-neutral, brass-400's new tone) — a quiet rail, NOT coral (a coral scrollbar everywhere is too loud).
- `*::-webkit-scrollbar-thumb:hover` `rgb(217 142 43 / 0.7)` (`211`) → **`rgb(217 119 87 / 0.6)`** (coral on hover — the rail lights coral when grabbed).
- Firefox `scrollbar-color: rgb(156 124 77 / 0.4) transparent` (`217`) → **`rgb(133 112 95 / 0.4) transparent`**.

---

## 4. Typography decision

### 4.1 Display serif — SWAP Newsreader → **Fraunces**

The brief asks: confirm or swap; Newsreader is present; evaluate vs Fraunces / Source Serif. The decision:

**Swap to Fraunces.** Reasoning, adversarially:

- **Newsreader** is a fine *reading* serif (Google's news-body face) — it is humanist but *quiet*, low-contrast,
  designed to disappear into paragraphs. As a *display/nameplate* face for a brand wordmark it under-delivers:
  it has no real personality at large sizes. The current wordmark is described as "weak" partly *because*
  Newsreader is a body face doing a display job.
- **Fraunces** is purpose-built for exactly this: a "display-leaning, old-style soft-serif" with a variable
  **optical-size (`opsz`)** axis, a **`SOFT`** axis, and a **`WONK`** axis. At display sizes it gets
  characterful, warm, slightly idiosyncratic ledges and a high-contrast elegance — humanist *and* distinctive.
  It is the single best match for "humanist serif for display/headers" with Claude's warm-but-editorial voice.
  Anthropic/Claude's own editorial type language leans into a warm high-contrast serif; Fraunces is the
  closest free Google-Fonts analog.
- **Source Serif** (the other candidate) is more neutral/corporate (Adobe's Source family) — competent but
  characterless; it would read closer to a generic publishing default. Rejected: not distinctive enough.

So: **Fraunces for display (`--font-serif`), used at headings + the wordmark, with `font-optical-sizing:
auto` and a heavier display weight for the wordmark.** Fraunces is on Google Fonts → drops into `next/font/
google` exactly like Newsreader (zero new infra). Subset it (`latin`), weights we actually use (see scale).

> Risk check: Fraunces is a large variable font. `next/font/google` self-hosts and subsets it, so the network
> cost is bounded; we only use it for headings + wordmark (7 files use `font-serif`), not body. Acceptable.

### 4.2 Mono — KEEP **JetBrains Mono**

Unchanged. It is the correct data/numeric face: clear tabular figures, distinct `0`/`O`/`1`/`l`, good at 11px.
No reason to churn. The whole-app default `font-family: var(--font-mono)` (`globals.css:57`) and global
`tabular-nums` stay — this is the density backbone and survives the re-skin intact.

### 4.3 Type scale (documented, mostly already in use via Tailwind defaults)

The app already runs dense: chrome/labels at 10–12px mono. Codify the scale in the doc:

| Role | Face | Size | Weight | Tracking | Notes |
|---|---|---|---|---|---|
| Wordmark "VYSTED" | Fraunces (display) | 16–18px | 600 (SemiBold) | `0` to `+0.01em` | opsz auto; see §5.4 — NOT the old 0.18em spaced-out caps |
| Panel/section heading (h1–h3) | Fraunces | 14–20px | 500–600 | `-0.01em` | optical-sizing auto |
| HUD label / legend (`.hud-label`) | JetBrains Mono | 10px (`0.625rem`) | 400 | `0.12em` upper | tone-down tracking 0.14→0.12em |
| Body / control text | JetBrains Mono | 12px (`text-xs`) | 400 | `0` | |
| Data / numerics / tables | JetBrains Mono | 11–12px | 400 | `0` | `tabular-nums` global |
| Dense table micro-labels | JetBrains Mono | 10px (`text-[10px]`) | 400 | `0` | kbd chips, sub-labels |

No new size tokens needed — Tailwind's default scale + the existing inline sizes cover it; the scale above is
*documentation* of current practice, adjusted only where the wordmark/tracking changes.

---

## 5. The new "VYSTED" wordmark / header concept

### 5.1 Why the current one is weak (verified, `page.tsx:77-121`)

The current header: a `bg-charcoal-925` bar with `instrument-bezel` chrome, "VYSTED" in
`font-serif text-sm tracking-[0.18em] text-amber-400` followed by a brass-uppercase "Terminal" `.hud-label`,
a brass `.tick-rule` strip along the bottom. Problems:
1. **Newsreader at 14px (`text-sm`) with 0.18em tracking** is the worst case — a quiet body serif, too small,
   spaced so wide the letterforms disconnect into "V Y S T E D". It reads as a *caption*, not a wordmark.
2. **Two type systems fighting**: serif "VYSTED" + mono "Terminal" with no relationship — two voices, no lockup.
3. **Amber on charcoal** at 14px is low-presence; the brand color is doing nothing.
4. The brass tick-rule + bezel are skeuomorphic noise around a weak mark.

### 5.2 The new concept — a confident coral-on-espresso lockup

**Concept: a tight Fraunces nameplate with a single coral mark.** The wordmark becomes a real lockup:

- **"VYSTED"** set in **Fraunces, ~17px, weight 600, tracking `+0.01em` (near-normal, NOT 0.18em)**, color
  `--color-charcoal-100` (warm cream) — so the *name* is calm cream, confident, legible. Fraunces's display
  character at 17px/600 gives it presence the old mark lacked.
- **A single coral accent glyph** preceding or punctuating the name: a small **coral square/dot mark**
  (8×8px `--color-amber-400` rounded-[2px]) acting as the "lit" brand pip — the one spot of coral in the
  header, so the eye lands on brand instantly. (Replaces the diffuse amber wordmark color with a concentrated
  coral mark — more distinctive, more "product".)
- **"TERMINAL"** as a smaller mono `.hud-label` set tight beside/under VYSTED, in `--color-charcoal-500`
  (quiet). The relationship is now intentional: serif name + mono descriptor, baseline-aligned, the descriptor
  visibly subordinate (smaller, dimmer, mono).

Concrete JSX (the lead drops this into `page.tsx`, replacing lines `78-83`):

```tsx
<div className="flex items-center gap-2 select-none">
  {/* coral brand pip — the single lit accent in the fascia */}
  <span aria-hidden="true" className="bg-amber-400 h-2 w-2 rounded-[2px]" />
  <span className="font-serif text-charcoal-100 text-[17px] leading-none font-semibold tracking-[0.01em]">
    VYSTED
  </span>
  <span className="hud-label leading-none mt-px">Terminal</span>
</div>
```

(`bg-amber-400` = coral after re-value; `font-serif` = Fraunces; `text-charcoal-100` = warm cream.)

### 5.3 Header bar treatment (`page.tsx:77`)

- Keep `bg-charcoal-925` (re-valued espresso) — correct fascia tone.
- **Drop `instrument-bezel`** from the header className (de-skeuomorphize — no watch-bezel). Replace its visual
  job with a single bottom hairline: keep the `.tick-rule` element (`117-120`) but per §3.4 it is now a flat
  1px coral hairline, not a tick row. Net: a clean espresso bar with a quiet coral underline. (If the lead
  keeps `.instrument-bezel`/renames it `.panel-edge`, the faint inset still works — but the cleaner look drops it.)
- Header height `h-9` (36px), gaps, button styling: keep. Button hover `hover:text-lume` (`88,100,112`) — keep
  (`lume` re-valued to warm cream; reads as "lights up on hover"). The `⌘K` kbd chip border/text
  (`border-charcoal-700 text-charcoal-500`) carries via tokens.

### 5.4 Font wiring (`layout.tsx`)

Swap the import. New `layout.tsx:2,5-9`:
```tsx
import { Fraunces, JetBrains_Mono } from "next/font/google";

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  display: "swap",
  axes: ["opsz", "SOFT"],   // optical size + soft-serif axis for warm display character
});
```
And `layout.tsx:24` className: `dark ${fraunces.variable} ${jetbrainsMono.variable}`. JetBrains Mono import
unchanged. **The `--font-fraunces` var name MUST match `tokens.css` `--font-serif`'s inner reference (§2.7).**

> Note: `next/font/google`'s `Fraunces` with `axes` requires the variable-font subset; if the build complains
> about a static weight conflict, drop `axes` and pass `weight: ["400","500","600"]` instead — Fraunces ships
> named weights too. Default to `axes` for the optical-size benefit; fall back to explicit weights if CI's
> font fetch is unhappy.

---

## 6. The application plan — exact files, in dependency order

### Tier 1 — the centralized system (re-skins ~95% of pixels). 4 files.

1. **`styles/tokens.css`** — replace ALL values per §2 (charcoal/amber/brass/lume/sage/positive/negative,
   ADD `--color-warning`, swap `--font-serif` inner var, bump radii, re-tune `--ease-detent`). Rewrite the
   header comment (`:1-14`) + every inline palette comment (they currently say amber/brass/phosphor — they
   will lie). This is the single biggest edit.
2. **`src/app/globals.css`** — per §3: update `@theme inline` fallback hexes + retarget `--color-accent` to
   `amber-400` + fix `--radius` to `var(--radius-panel)` (§3.1); rewrite the 4 composite chrome vars, rename
   `--glow-amber`→`--glow-coral` (§3.2); rewrite body atmosphere, drop grain to 0.02, add
   `font-optical-sizing: auto` to headings, rewrite selection + focus to coral (§3.3); update `.hud-label`/
   `.instrument-bezel`/`.tick-rule`/`.hud-active` (§3.4); update `.dockview-theme-vysted` fallbacks + 2 raw-RGB
   lines (§3.5); update scrollbar RGB (§3.6).
3. **`src/app/layout.tsx`** — swap `Newsreader`→`Fraunces` import + `--font-newsreader`→`--font-fraunces`
   variable + className (§5.4). JetBrains Mono unchanged.
4. **`src/app/page.tsx`** — replace the wordmark lockup `78-83` (§5.2); drop `instrument-bezel` from header
   className `77` if going clean (§5.3).

### Tier 2 — the canvas leak (NOT carried by tokens; hand-edit each). Re-verified file list.

Canvas (`lightweight-charts` + drawing primitives) can't read CSS vars, so every hex is a hardcoded copy.
**While editing, fix the 3 drift values — they were never tokens.** New canvas hex map (espresso/coral):

| Old hardcoded hex | Meaning | **New hex** |
|---|---|---|
| `#1c1916` (chart bg) | charcoal-900 | `#241d19` |
| `#c9c2b2` (chart text) | charcoal-200 | `#d6c8bb` |
| `#2a2620` (grid) | charcoal-800 | `#352a25` |
| `#3a352c` (scale borders) | charcoal-700 | `#473a33` |
| `#4d4639` (crosshair) | charcoal-600 | `#5c4d44` |
| `#7faa6b` (up candle) | positive | `#7fa96a` |
| `#c8654b` (down candle / negative) | negative | `#cf5b48` |
| `#8fa67c` (comparison line / sage) | sage-400 | `#a8917f` (muted neutral) |
| `#e9a94d` (amber accent, drawings) | amber-400 | `#d97757` (coral) |
| `#f4c87a` (indicator) | amber-300 | `#e69e84` (coral-300) |
| `#b6c4a8` (indicator) | sage-300 | `#c9b9ad` (muted) |
| `rgba(233, 169, 77, X)` (amber fills) | amber-400 @ X | `rgba(217, 119, 87, X)` (coral) |
| `rgba(143, 166, 124, 0.15)` (ichimoku +) | sage | `rgba(127, 169, 106, 0.15)` (positive) |
| `rgba(200, 101, 75, 0.15)` (ichimoku −) | negative | `rgba(207, 91, 72, 0.15)` (new negative) |
| **`#e8b441` (DRIFT ×3)** | claimed amber, isn't | `#d97757` (coral) |
| **`#c39a3e` (DRIFT)** | claimed amber-600, isn't | `#a44a30` (coral-600) |
| **`#4ec9a3` (DRIFT — cyan!)** | claimed positive, is cold teal | `#7fa96a` (positive) |

Files (re-verified present):
5. `src/modules/chart/ChartPanel.tsx` — `CHART_THEME` (`66-77`), `CANDLE_THEME` (`79-86`),
   `COMPARISON_LINE_COLOR` (`88`), trend overlay `#8fa67c`/`#c8654b` (`389`), comparison line consumer (`746`).
6. `src/modules/quant/YieldCurvePanel.tsx` — theme block + `const AMBER = "#e8b441"` (`45`, DRIFT → coral).
7. `src/modules/analyst-ratings/PriceTargetTimeline.tsx` — theme block + `const AMBER = "#e8b441"` (`30`, DRIFT).
8. `src/modules/backtest/BacktestResultView.tsx` — theme block + `const NEGATIVE = "#c8654b"` (`41`),
   `const AMBER = "#e8b441"` (`42`, DRIFT), area-series `rgba(200,101,75,…)` fills (`108-109`).
9. `src/modules/macro/MacroChart.tsx` — theme block + `const LINE_COLOR = "#c39a3e"` (`32`, DRIFT → `#a44a30`).
10. `src/modules/earnings/EarningsSurpriseChart.tsx` — theme block + `const POSITIVE = "#4ec9a3"` (`30`, DRIFT
    cyan → `#7fa96a`), `const NEGATIVE = "#c8654b"` (`31` → `#cf5b48`).
11. `src/modules/chart/indicators.ts` — `INDICATOR_COLORS` (`160-166`): the 5-color palette → coral/neutral set.
12. `src/modules/chart/drawings/base.ts` — `DEFAULT_DRAWING_COLOR = "#e9a94d"` (`30` → `#d97757`); fill
    fallback `rgba(233,169,77,0.12)` (`104` → `rgba(217,119,87,0.12)`).
13. `src/modules/chart/drawings/factory.ts` — `color: "#e9a94d"` (`72`→coral), `fillColor: "rgba(233,169,77,
    0.12)"` (`75`→coral).
14. `src/modules/chart/drawings/renderers.ts` — fill fallback `"#e9a94d"` ×3 (`193,227,296`→`#d97757`).
15. `src/modules/chart/volume-profile-primitive.ts` — `HISTOGRAM_FILL = "rgba(233,169,77,0.2)"` (`34`→coral).
16. `src/modules/chart/ichimoku-cloud-primitive.ts` — `POSITIVE_FILL` (`22`), `NEGATIVE_FILL` (`24`) per table.

### Tier 2b — shadcn + ReactFlow literals (re-verified).

17. `src/components/ui/dialog.tsx` — overlay `bg-black/50` (`34`) → **`bg-charcoal-950/70`** (espresso backdrop,
    not flat black); content `rounded-lg` (`56`) → leave as-is *if* `--radius-panel` is bumped to `0.5rem`
    (now matches), OR change to `rounded-[var(--radius-panel)]`; close-button `rounded-xs` (`65`) → keep.
18. `src/components/ui/button.tsx` — destructive `text-white` (`14`) → **`text-charcoal-100`** (warm cream, not
    pure white — on-brand; `#ece3d9` on `#cf5b48` destructive ≈ 3.0:1, large/bold UI text passes; if it fails
    contrast for the lead, keep `text-white` for destructive only).
19. `src/modules/node-editor/VystedNode.tsx` — `border-charcoal-700 bg-charcoal-850` carries via tokens;
    selected `border-amber-500 shadow-amber-500/20` (`43`) → coral via tokens (amber-500 re-valued); handles
    `!border-amber-400 !bg-amber-400` (`54,67`) → coral via tokens. **No edit needed — all tokened.** (Listed
    so the lead knows it's covered.)
20. `src/modules/node-editor/NodeEditorPanel.tsx` — `<Background gap={16} size={1} />` (`472`) uses ReactFlow's
    **default dot color** (not themed). **Add `color="#473a33"` (charcoal-700) and `bgColor="#1a1512"`
    (charcoal-950)** so the canvas grid matches espresso. This is the one genuinely-unthemed node-editor surface.

### Tier 2c — tests asserting old hex (update so CI stays green).

21. `src/lib/workspace.test.ts` (`151,162,192`), `src/modules/chart/ChartPanel.test.tsx` (`496`),
    `src/store/chart-drawings.test.ts` (`12`) — update expected `#e9a94d`/`#8fa67c`/`#fff` defaults to the new
    `#d97757`/`#a8917f` (and whatever `DEFAULT_DRAWING_COLOR` becomes). **Must land in the same commit as
    `drawings/base.ts`** or `pnpm ci-local` (vitest step) goes red.

### Tier 3 — recommended structural fix (so the NEXT re-skin is one file).

22. Create **`src/lib/chart-theme.ts`** exporting the canvas hex constants (`CHART_SURFACE`, `CHART_TEXT`,
    `CHART_GRID`, `CHART_BORDER`, `CHART_CROSSHAIR`, `ACCENT_CORAL`, `POSITIVE`, `NEGATIVE`, `NEUTRAL`,
    `INDICATOR_PALETTE`, fill helpers). Refactor all 12 canvas files (#5–#16) to import from it. This is why the
    3 drift values diverged unnoticed — six independent copies. Doing this DURING the re-skin (not after) means
    the new values are written once. **Strongly recommended** — it converts the canvas surface from "12 files
    to hand-edit every re-skin" to "1 file". Listed as Tier 3 because it is optional for *correctness* but it
    is the single highest-leverage cleanup and the lead should do it now while every file is already open.

### Tier 4 — the doc.

23. **`docs/DESIGN_SYSTEM.md`** — full rewrite per §7 below. Pure docs, no runtime effect, but it is the spec
    of record and currently describes the retired INSTRUMENT system end to end.

### What does NOT change (verified non-issues)

- **No `tailwind.config.*`** exists — Tailwind 4 reads `@theme` from CSS. Nothing to edit there.
- **`src-tauri/tauri.conf.json`** only sets `"theme": "Dark"` (OS window chrome) — no color to retheme. The
  espresso titlebar is the OS dark default; acceptable.
- **No stray Inter/Roboto** anywhere — fonts are exclusively the two `next/font` imports.
- The 40 `amber-*` / 41 `charcoal-*` / 2 `sage-*` / 1 `lume` consumer files need **zero edits** — they carry
  via re-valued tokens. That is the entire point of the keep-names strategy.

---

## 7. `docs/DESIGN_SYSTEM.md` — rewrite outline

Replace the current 110-line INSTRUMENT doc with the same skeleton, re-voiced for Claude after dark:

1. **Title + framing** — "Vysted Terminal — Design System (Claude after dark)". Phase 10. Source of truth =
   `styles/tokens.css` + `src/app/globals.css`; canvas mirror = `src/lib/chart-theme.ts` (if Tier 3 done).
2. **The concept** — warm espresso near-black base, single coral/clay accent, cream body, humanist serif
   (Fraunces) display + mono (JetBrains) data, Bloomberg/JARVIS density in Claude's restrained warm voice.
   "Take the chronograph apart, keep the density and warmth, rebuild it in coral-on-espresso."
3. **Deliberately NOT** — the four traps (no cold neutrals, no cyan, no purple/Inter, no pillowy/skeuomorphic),
   PLUS the explicit "retired from INSTRUMENT: amber, brass, sage-as-accent, CRT bloom, heavy grain, bevels."
4. **Tokens** — the full §2 table condensed: espresso base 950→100, coral accent 200→600 (states), warm-neutral
   (ex-brass), cream (`lume`), muted (`sage`), semantic positive/negative/**warning** (call out the new warning
   token + the coral-vs-negative separation rule), radii, motion.
5. **Type** — Fraunces (display/wordmark, opsz auto) + JetBrains Mono (body/data, global tabular-nums = the
   density tell). The type scale table from §4.3.
6. **Wordmark** — the new coral-pip + Fraunces "VYSTED" + mono "Terminal" lockup; why the old one was weak.
7. **Chrome primitives** — coral hairlines, flat panel edge (de-skeuomorphized), the flat coral header
   hairline (ex-tick-rule), `.hud-label`, `.hud-active`/`--glow-coral`, quiet ambient warmth + 2% grain,
   coral selection + focus, warm scrollbars (coral-on-grab).
8. **Application strategy** — keep-names re-value → 40+ panels carry free; globals base; dockview theme;
   header. The canvas leak + chart-theme.ts single-source. The 3 retired drift values.
9. **Customizable** — re-tune one token re-skins the app; light theme slots via the same `@theme inline`.
10. **Verification note** — operator-manual populated-state capture (carry forward the existing note); flag the
    coral-vs-negative eyeball check + the destructive-button contrast check as named verification gates.

---

## 8. Adversarial summary — the failure modes the lead must check

1. **Half-edit: token `--font-serif` swapped to Fraunces but `layout.tsx` still imports Newsreader** → silent
   fallback to Georgia. Both must land together (§2.7 + §5.4).
2. **Coral vs loss-red merge** in dense red/green tables (§2.6). The #1 palette risk. Eyeball a populated
   Watchlist/Portfolio against a coral button; fallback negative `#d6493a` pre-approved.
3. **Canvas drift survives** because someone "just changed tokens.css." The 12 canvas files + 3 drift values
   do NOT follow tokens. The chart-theme.ts refactor (Tier 3) is the durable fix.
4. **`--radius` still a literal** if §3.1 is skipped — shadcn radii won't track `--radius-panel`. Set it to
   `var(--radius-panel)`.
5. **Token comments still say "amber/brass/phosphor"** after the re-value — the names lie *and* the comments
   lie. Rewrite both (§1, §6.1).
6. **destructive `text-white` → warm cream** may dip below contrast on the brick-red — verify, keep white if
   it fails (§6 #18).
7. **Tests assert old hex** — `chart-drawings.test.ts` etc. go red unless updated in the same commit (§6 #21).
8. **`--color-accent` left on sage** → green hover states in a single-coral-accent system. Retarget to
   `amber-400` (§3.1).

Gate everything through `pnpm ci-local` + the operator's populated-state screenshot pass (both resolutions per
the CLAUDE.md visual protocol) before the tag. The agent harness cannot drive the GUI — visual sign-off is the
operator's.
