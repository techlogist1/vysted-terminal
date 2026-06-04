# Vysted R4 — Design Language ("Cold Instrument")

> **Status:** Spec — authored in the R4 spec window, to be executed by the build window.
> **Scope:** the complete original visual system for the experience-layer rebuild. This is the
> single source of design truth the build executes against; the master spec
> (`REBUILD_R4_SPEC.md` §3) references it, the failure-mode matrix
> (`R4_FAILURE_MODE_MATRIX.md`) enforces its state rules.
> **Constraints baked in:** dark-only; token NAMES stay historical (re-value only, zero churn
> across ~92 files); canvas palette single-sourced across **three** places in lockstep; honors the
> R3-ratified cool-indigo accent + mark-only brand; complies with Constitution Principle VII
> (Minimal-Dark, density with progressive disclosure).

---

## 0. Why this doc exists (the honest diagnosis)

The recon (`C6`) found the current visual system is **"generic by construction"**: it is the
unmodified Vercel/Geist **shadcn-zinc ramp** + Tailwind **`indigo-400 #818cf8`**, with stock shadcn
`button.tsx`/`dialog.tsx`, **no type scale**, **no spacing system**, **no density craft**, and a
stale "warm clay/espresso" narrative still lurking in `globals.css` comments and dockview fallback
hexes. `tokens.css` literally annotates its stops with "(zinc-950)", "(zinc-900)" — it is the
default ramp, untouched.

The R4 brief's complaint ("a prior pass cheaply copied Claude's UI — forbidden") is **structurally
accurate but mis-aimed**: the problem is not the indigo hue (R3 ratified it; teal is dead). The
problem is the **absence of craft** — there is no system, just defaults. Originality here does **not**
mean swapping the accent again (that thrashes a ratified decision and the 92-file token map). It
means building the system that was never built: a perceptually-even OKLCH neutral ramp with a
deliberate character, a real type scale, a real spacing rhythm, density-as-craft, motion discipline,
and a single coherent **point of view**.

**The point of view: "Cold Instrument."** The chrome disappears; the _data_ is the only thing that
is ever lit. Color is not decoration — it is a pointer to the one thing that is active, live, or
verifiable. A finance terminal you stare at for hours should feel like a precision gauge in a dark
cockpit: neutral, quiet, and exact, with a single cool light that moves to whatever you are working
on. This is synthesized from the principles of Linear (perceptual rigor + density-as-craft), Apple
HIG (deference + contrast floors), Perplexity (accent budget), and Claude's _typographic_ hierarchy
— and it explicitly **rejects** Claude's warm/cream/serif execution, neon glow, saturated SaaS
gradients, and the 90s-terminal cliché.

---

## 1. The four laws (every rule below derives from these)

1. **One accent, rationed.** A single cool-indigo hue is the _only_ non-neutral, non-signal color on
   screen, and it appears on **≤ ~5% of pixels in any view**. It marks exactly four things: the
   active/selected element, the focus ring, the one primary action, and live/verifiable affordances
   (cashtags, citations, agent-driven elements). **Never** a panel fill, **never** a glow, **never**
   ambient.
2. **Hierarchy from type + space + one hairline — not shadows or nested cards.** Depth is expressed by
   a **surface-luminance step**, Apple-style, not by drop-shadows. At most two surface levels are
   visible inside a single panel. One hairline separates groups, not every row.
3. **Motion is feedback — brief, asymmetric, never ambient.** Animation expresses a cause→effect
   relationship (a thing arrived, a value changed, a state toggled). It is never decorative, never
   looping, never a glow. Exits run faster than entrances. `prefers-reduced-motion` collapses
   everything to an instant or an 80ms opacity fade.
4. **Contrast is budget — spent on meaning.** The brightest things on screen are the value that
   changed and the active selection. Chrome, labels, and inactive structure live in the zinc
   mid-band. If everything is emphasized, nothing is.

---

## 2. Color system (OKLCH, re-valued into historical token names)

### 2.1 The historical-name rule (non-negotiable mechanic)

Token names are **fossils** kept so ~92 files re-skin with zero edits. The build **changes values,
never names**. Read the role column, never the literal name:

| Token family (name)                 | Renders                    | Role                                        |
| ----------------------------------- | -------------------------- | ------------------------------------------- |
| `charcoal-*`                        | the **neutral zinc** ramp  | surfaces, borders, text                     |
| `amber-*`                           | the **cool-indigo** accent | the single accent, five states              |
| `brass-*` / `sage-*`                | zinc neutrals              | quiet legacy / secondary data series        |
| `lume`                              | near-white                 | peak readouts, active-tab text              |
| `positive` / `negative` / `warning` | green / red / amber        | **the only saturated colors**, signals only |

### 2.2 Define the ramp in OKLCH, not hand-picked hex

The current ramp is hand-picked sRGB hex (the stock zinc values). **Re-derive every neutral stop and
the accent in OKLCH** so the steps are _perceptually_ even (Linear's discipline) and so the "Cold
Instrument" character is a deliberate, tunable hue/chroma choice rather than an accident of the
default palette.

**Neutral ramp — "cold zinc" (a true-neutral ramp with a barely-perceptible cool cast, hue ≈ 264,
chroma ≤ 0.006 so it reads neutral but not _literally_ the stock shadcn ramp).** Even lightness steps;
keep adjacent _surface_ steps ≤ ~6% L apart (Cursor calm). Authoring values (OKLCH → emit sRGB hex
into `tokens.css`; the table gives target hex for reference):

| Token          | Role                          | OKLCH (L C H)   | ~hex      |
| -------------- | ----------------------------- | --------------- | --------- |
| `charcoal-950` | app/root well                 | 0.145 0.004 264 | `#0a0a0c` |
| `charcoal-925` | header fascia, tab strip      | 0.170 0.004 264 | `#101013` |
| `charcoal-900` | panel / card surface          | 0.205 0.004 264 | `#161619` |
| `charcoal-875` | popover / active tab          | 0.235 0.005 264 | `#1c1c20` |
| `charcoal-850` | raised inset (node bg)        | 0.265 0.005 264 | `#212126` |
| `charcoal-800` | muted / secondary surface     | 0.300 0.005 264 | `#27272b` |
| `charcoal-700` | borders / inputs / dividers   | 0.360 0.005 264 | `#323237` |
| `charcoal-600` | strong border / disabled fg   | 0.420 0.005 264 | `#3f3f46` |
| `charcoal-500` | faint label / kbd text        | 0.560 0.005 264 | `#71717a` |
| `charcoal-400` | muted foreground              | 0.680 0.004 264 | `#a1a1aa` |
| `charcoal-300` | secondary text                | 0.800 0.003 264 | `#d2d2d7` |
| `charcoal-200` | bright secondary / chart text | 0.880 0.002 264 | `#e6e6ea` |
| `charcoal-100` | foreground / body             | 0.960 0.002 264 | `#f4f4f6` |

**Accent — cool-indigo, one hue, five states (honors the R3-ratified indigo family; OKLCH-tuned,
~12–15% desaturated vs the neon `indigo-400` so it reads precise, not vibe-coded).** Hue ≈ 268.

| Token       | Role                                 | OKLCH (L C H)  | ~hex      |
| ----------- | ------------------------------------ | -------------- | --------- |
| `amber-200` | faint tint / selection fill          | 0.86 0.055 268 | `#cdd2f4` |
| `amber-300` | hover-bright / accent text           | 0.74 0.105 268 | `#a8b0ef` |
| `amber-400` | **BRAND / primary / default accent** | 0.66 0.150 268 | `#7e88e8` |
| `amber-500` | pressed / active-sash / selected     | 0.55 0.190 268 | `#5559d6` |
| `amber-600` | deep border / dense accent           | 0.43 0.150 268 | `#3a3aa0` |

> **Decision (Tier-3, building on — not reopening — the R3 ratification):** the _hue stays cool-indigo_.
> The change is (a) OKLCH derivation for even states, (b) a ~12–15% chroma reduction at the brand stop
> so it stops reading as the stock `indigo-400`. If the operator prefers the exact ratified `#818cf8`
> kept byte-identical, that is a one-line revert; flagged as **Q4** in the master spec's open
> questions (low stakes).

**Signals (the only saturated colors; used on numerals/marks only, never as fills):**

| Token             | Value                                      | Use                       |
| ----------------- | ------------------------------------------ | ------------------------- |
| `positive`        | `#3fbf6f` (muted green, luminance-matched) | gains                     |
| `positive-bright` | `#4ade80`                                  | gain flash peak           |
| `negative`        | `#e5544b` (muted red, luminance-matched)   | losses                    |
| `negative-bright` | `#f87171`                                  | loss flash peak           |
| `warning`         | `#e0a13a`                                  | stale/paper/caution badge |

Green and red are **luminance-matched** so neither dominates a P&L column (a red row must not look
"louder" than a green one). Status colors borrow the same muted register. **Never** use a signal
color as a background fill.

### 2.3 Canvas single-sourcing (THE three-place lockstep — do not skip)

`lightweight-charts` and drawings cannot read CSS vars. The accent + canvas palette is single-sourced
in **three** files; a value change touches **all three in the same commit** or the chart/glow drifts:

1. `styles/tokens.css` — `--color-amber-400` (+ the ramp).
2. `src/app/globals.css` — `--accent-rgb` (space-separated rgb of `amber-400`, currently
   `129 140 248` → becomes `126 136 232`).
3. `src/lib/chart-theme.ts` — `ACCENT_CORAL_RGB` (a historical name; carries the indigo rgb).

The chart-theme export names (`ACCENT_CORAL`, `coralFill`) are fossils — they carry indigo values.
Leave the names; change the values.

### 2.4 Elevation = luminance step, never shadow

There is **no** drop-shadow in the structural system. A raised surface is one zinc step lighter than
its parent (`900 → 875 → 850`). The only sanctioned `box-shadow` uses are: (a) the 1px inset
top-edge hairline (`--bezel-shadow`, a _whisper_ of depth), (b) the focus ring, (c) the modal scrim.
**Forbidden:** the `--glow-coral` / `.node-glow` / `.hud-active` neon glow primitives in their current
form — replace the agent-active treatment with a **1px accent border + a single luminance step**, no
blurred glow (the "no neon/glow" mandate). The streaming cursor (`.stream-cursor`) is kept — it is
feedback, not glow.

---

## 3. Typography

**Families (kept; the `--font-serif` slot name is a fossil that renders the UI sans):**

- UI sans: **Inter** (or Geist Sans — both acceptable; this is _not_ the place for a "characterful
  display font" — an instrument wants legibility, and the frontend-design skill's display-font default
  is explicitly counter-steered here). Headings use the same family at display optical sizing with
  `letter-spacing: -0.012em`.
- Data/mono: **Geist Mono** (current) — `tabular-nums` globally, slashed zero. All numerics, tickers,
  prices, and table data ride the mono face so digits never jitter.

**The type scale (NEW — none exists today; ~1.20 modular, snapped to even px):**

| px  | weight  | line-height        | role                                               |
| --- | ------- | ------------------ | -------------------------------------------------- |
| 11  | 510     | 1.3                | micro / `.hud-label` (uppercase, +0.10em tracking) |
| 12  | 400/510 | 1.4                | caption, secondary, kbd chips                      |
| 13  | 400     | 1.35 (dense) / 1.5 | **body + table base**                              |
| 15  | 510     | 1.4                | panel title                                        |
| 18  | 590     | 1.3                | section head                                       |
| 22  | 590     | 1.25               | overview / brief head                              |
| 28  | 590     | 1.2                | rare hero only (first-run)                         |

Weights: **400** body, **510** emphasis/labels (Linear's trick — medium, not bold, carries label
hierarchy), **590** headings. Reading prose (briefs) uses line-height **1.6**; dense table rows
**1.35**; never below 1.3. Ship the scale as named tokens/utilities (`text-body`, `text-panel-title`,
`text-section`, …) so sizes stop being ad-hoc `text-[11px]` scattered per component.

---

## 4. Spacing, radii, density

**Spacing scale (NEW — none exists today; 4px base, 8px rhythm):**
`2 · 4 · 6 · 8 · 12 · 16 · 24 · 32 · 48 · 64`. Component padding draws from `{6, 8, 12}`; section
gaps from `{16, 24, 32}`. Ship as the project's spacing tokens; forbid raw off-scale values
(`gap-2.5`, `px-[7px]`) in new/changed code.

**Radii (kept — already systematized):** `--radius-panel 0.375rem`, `--radius-control 0.25rem`.
Tight + precise; do not introduce a third radius.

**Density (the finance concession + the craft):**

- Table row height **28px** (dense) / **32px** (default); **never below 24px**.
- Numerics **right-aligned, tabular**; text **left-aligned**; one hairline between row _groups_, not
  per row.
- Icons/labels/numerals share a baseline grid (Linear's "feel it after a minute"). One icon family
  (Lucide), consistent stroke (1.5px), consistent sizing tokens (`icon-sm 14`, `icon-md 16`,
  `icon-lg 20`) — no arbitrary mixing.
- Max two surface-luminance levels visible per panel.

---

## 5. Motion

**Duration tiers (the JS `motion.ts` `DUR` and CSS `--duration-*` must be unified into ONE
vocabulary — today they overlap but diverge):**

- **120ms** micro — hover, toggle, button press, color flip, value-flash fade.
- **180ms** default — dropdown, popover, tab switch, selection, palette open.
- **240ms** entrance — panel mount, modal/sheet, sidebar slide.
- **Exits ~30% faster** than entrances (enter 240 → exit 160).

**Easing:**

- enter `cubic-bezier(0.2, 0, 0, 1)` (decelerate, settle) ·
- exit `cubic-bezier(0.4, 0, 1, 1)` ·
- shared `cubic-bezier(0.4, 0, 0.2, 1)`. **Never linear.**

**What animates:** opacity + small transform (≤ 8px translate, ≤ 1.5% scale), selection/focus rings,
the **value-flash** on a data update (120ms tint to accent or gain/loss, then back to neutral — the
signature micro-interaction), list-stagger (30–50ms/item, capped at 8 items).
**What never animates:** data-table layout reflow, chart redraws, anything ambient/looping/glowing.
`prefers-reduced-motion` → opacity-only at ≤80ms; honored both via the CSS media query and
`<MotionConfig reducedMotion="user">`.

**Kill-switch / safety states are _stillness_:** when the kill-switch is active, motion stops, the
accent is suppressed, and the affected surface goes red-bordered and quiet (no glow, no pulse). Calm
is the safety signal.

---

## 6. Component state contract (RIGOR — every interactive element MUST specify all of these)

This is the rigor pass (from `ui-ux-pro-max`, translated from its App-UI scope to **desktop /
keyboard-first**). Every interactive element specifies the full set; the failure-mode matrix enforces
the data-surface subset per panel.

**Universal interaction states:** `default · hover · active/pressed · focus-visible · disabled ·
loading`. Plus, for any data surface: `empty · error · stale · market-closed · symbol-not-found`
(see `R4_FAILURE_MODE_MATRIX.md`).

State rules:

- **focus-visible is mandatory and never removed.** 1px `amber-400` outline, `outline-offset: 1px`
  (kept from current `globals.css`), visible on the keyboard path for _every_ focusable element.
  Removing focus rings is forbidden.
- **hover ≠ the only affordance.** Pointer hover is enhancement; the element must be reachable and
  operable by keyboard with a visible focus state (keyboard-first app).
- **active/pressed** uses a luminance step or `amber-500`, **never a layout-shifting transform** (no
  jitter). Subtle scale (≤1.5%) only on cards/buttons, restored on release.
- **disabled** = opacity 0.4–0.5 + `not-allowed` cursor + the semantic `disabled`/`aria-disabled`
  attribute; never a control that looks active but no-ops.
- **loading** = skeleton/shimmer for >300ms waits (not a blocking spinner); the value-flash for live
  ticks; a button mid-async is disabled with an inline spinner.
- **error** = inline, near the cause, with a **recovery path** (Retry / Edit / what would unlock it),
  never a raw stack/JSON, never color-only.

---

## 7. Accessibility floors (WCAG, dark-mode-specific — hard requirements)

- **Body text ≥ 4.5:1** against its panel surface (`charcoal-100` on `charcoal-900` passes; verify
  the re-valued ramp).
- **Large text (≥18px/≥14px-bold) ≥ 3:1.**
- **Non-text / UI glyphs / data lines / borders ≥ 3:1** against adjacent color. **Secondary text
  `charcoal-400` is labels-only** and must clear 3:1; it is never used for body copy.
- **Focus ring** visible, ≥3:1 against both the element and its background.
- **Color is never the only signal.** Gain/loss carries a sign/arrow + the number, not just
  green/red. Status carries an icon/label, not just a hue. (Colour-blind safety; the muted
  red/green pair already helps.)
- **Dividers/borders visible in dark** (they are — `--hairline` is zinc @ 14–24%); state contrast is
  defined for the dark theme directly, never inferred from a light theme (there is no light theme).
- **Reduced motion** honored everywhere (§5).
- **Data tables:** tabular numerics; sortable headers expose `aria-sort`; provide a keyboard path;
  gridlines low-contrast so they never compete with data; data labels ≥4.5:1, data lines ≥3:1.

---

## 8. Chrome & shell

- **Brand: mark-only, no wordmark** (R3-ratified, kept) — the single `size-2.5 rounded-[3px]`
  `amber-400` pip with `aria-label="Vysted"`. It is the one persistent spot of accent; it does not
  pulse.
- **Header** (`h-9`, `charcoal-925`): mark · divider · Agent toggle (⌘B) · Open-panel (⌘K) · Save
  layout · spacer · `StatusChrome` · Settings. Underlined by one `.tick-rule` hairline.
- **StatusChrome** (kept, refine to tokens): sidecar dot (green/red/pulsing-connecting) ·
  `provider · model` · running-agent count. This is the legible "what's connected" surface (FR-033).
- **dockview theme:** the `--dv-*` overrides stay, but **purge the warm clay/espresso fallback hexes**
  (`#16140f`, `#a06b52`, `#7c5240`, …) and replace every literal fallback with the zinc/indigo value,
  so a missing token degrades to _neutral_, never to warm-brown (see register `S-1`). Active-tab
  underline tick stays (`inset 0 -2px 0 amber-400`).
- **Scrollbars** (kept): quiet zinc rail, accent only on grab.

---

## 9. Shared state primitives (NEW — the biggest structural debt)

Today each of ~20 panels hand-rolls empty/loading/error inline; `src/components/ui/` has only
`button.tsx` + `dialog.tsx`. The build **extracts a shared primitive set** so the failure-mode matrix
is enforced **once**, not duplicated 20×:

- `<Skeleton>` — shimmer block, house durations.
- `<EmptyState icon title hint action>` — used by every panel's no-data path; carries a "try this"
  affordance where relevant.
- `<ErrorState message onRetry detail>` — inline, recovery-first, never raw JSON.
- `<MarketClosedBadge>` / market-session awareness (NEW — **0% covered today**, see §10).
- `<NotFoundState symbol>` — the shared "couldn't resolve {symbol}" affordance (today only
  equity-overview handles it; watchlist silently shows `—`).
- `<StalenessBadge>` / `<ProvenanceBadge>` (extend the existing `DataBadges.tsx`) — `live · stale ·
eod · paper/synthetic`, always carrying provenance (FR-041/065).

These primitives are themed once from the tokens; every panel consumes them. This is what makes "every
interactive element feels intentional" enforceable rather than aspirational.

---

## 10. Market-session awareness (NEW — net-new subsystem the design depends on)

A grep found **zero** market-open/closed/after-hours awareness anywhere in `src/`. The only freshness
signal is the sidecar-driven `StalenessBadge`, which is _data-marked_, not _session-aware_. A weekend
price renders with no "market closed" context. R4 adds a **locale-aware market-session signal** (US +
India per Principle VIII) so every price/quote surface can show `Market closed · last close` /
`Pre-market` / `After-hours` / `Open`. This is both a design primitive (§9) and a data requirement
(master spec FR-118). It is the single most common "graceful state" gap.

---

## 11. Migration map (current → R4) — what the build actually edits

| Area                                        | Today                                      | R4                                                  |
| ------------------------------------------- | ------------------------------------------ | --------------------------------------------------- |
| Neutral ramp                                | stock shadcn-zinc hex                      | OKLCH cold-zinc, re-valued into `charcoal-*`        |
| Accent                                      | `indigo-400 #818cf8` (neon-ish)            | OKLCH cool-indigo, ~12–15% desat, into `amber-*`    |
| Type                                        | ad-hoc `text-[11px]` etc.                  | named ~1.20 scale tokens (§3)                       |
| Spacing                                     | raw Tailwind, off-scale                    | 4/8 scale tokens (§4)                               |
| Motion                                      | two vocabularies (`DUR` vs `--duration-*`) | one unified token set (§5)                          |
| Elevation                                   | mixed; `--glow-coral`/`.node-glow` neon    | luminance-step only; glow primitives removed (§2.4) |
| States                                      | hand-rolled per panel                      | shared primitives (§9)                              |
| Market session                              | none                                       | locale-aware session signal (§10)                   |
| `globals.css` comments + dockview fallbacks | warm "clay/espresso"                       | purged to zinc/indigo (register `S-1`)              |
| `docs/DESIGN_SYSTEM.md`                     | entirely stale (warm clay)                 | rewritten to this doc (register `S-2`)              |

**Zero-churn guarantee:** because names are fossils, the ramp/accent re-value is a **values-only** edit
to `tokens.css` + the two canvas mirrors. Components that use `bg-charcoal-900`/`text-amber-400`
re-skin automatically.

---

## 12. Verification (this doc is only "done" when pixels prove it)

Per the verification contract (master spec §9), every surface touched by the redesign is screenshotted
via the **Quartz path** (`/tmp/rigcap.py`, matched on `kCGWindowOwnerName == "vysted-terminal"`) at
**both 1920×1080 and 2560×1440**, **populated** (real data — `AAPL/MSFT/NVDA/SPY` + `RELIANCE.NS`),
and the rendered pixels inspected — a DOM/`evaluate_script` assertion does **not** count for any
visual claim (the R3 screener-column false-positive is the cautionary tale). Contrast floors (§7) are
measured, not assumed. Saved as evidence under `docs/screenshots/v0.8.0-r4/` (never overwriting).
