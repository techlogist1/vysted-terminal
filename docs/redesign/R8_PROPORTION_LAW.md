# R8 Proportion Law — the one system every surface obeys

The R7 type scale (tokens.css: micro 11 / caption 12 / body 13 / panel-title 15 / prose 16 /
overview 18 / section 22 / hero 28) is sound and stays. R8 governs **which roles use which
step, how controls are sized, and how overflow is handled** — the three places the chaos
lives. Every team builds against this file; verification audits the rendered screen against it.

## 1. Type roles (what may use what)

| Role | Step | Where |
|------|------|-------|
| Reading prose (assistant chat, brief body, notes editor, learner explanations) | `text-body` 13 in the dock; `text-prose` 16 ONLY in wide reading panels (Notes, Brief at ≥420px column) | Brief body must downshift to `text-body` below 420px panel width — never 16px in a 200px column |
| User chat message | `text-body` 13 — same step as assistant prose, distinguished by container (border/bg), never by size | kills the "enormous user type" defect |
| Data cells (watchlist, screener, portfolio, tables) | `text-caption` 12, `tabular-nums` | price/change/etc. |
| Panel headers / titles | `text-panel-title` 15 | one per panel |
| Chrome labels (toolbar buttons, chips, tabs, meta rows) | `text-caption` 12 | NOT micro |
| Micro-status (provenance chips, timestamps, keycap hints, section eyebrows) | `text-micro` 11 — the floor. NOTHING renders below 11px, ever, including via transforms | marketplace micro-text class |

## 2. Control scale (one ladder, no ad-hoc sizing)

- **Controls:** chrome chips/buttons h-6 (24px); inputs & toolbar fields h-7 (28px); form
  controls (Settings, Order Entry) h-8 (32px). Hit target ≥ 24×24 always.
- **Icons:** 12px inside h-6 chrome; 14px inside h-7/h-8; 16px only for primary actions
  (composer send/plus). A surface's icons are ONE size — no giant-pencil-next-to-micro-printer.
- **Primary action buttons** (composer send/stop/plus): 28×28 with a 16px icon.
- **Symbol/ticker inputs** (chart toolbar, watchlist add): min-w to fit 12 characters
  ("SAKSOFT.NS" + padding) — `min-w-[7.5rem]`, never less.

## 3. Overflow law (clipping impossible by construction)

1. **Meaningful labels never mid-word truncate.** A label either (a) fits via min-w, (b) has a
   designed short form (model names: "DeepSeek V4" not "DEEPSEEK-V4-FLA…"; map at the
   formatter, not CSS), or (c) collapses to an icon+tooltip at narrow widths. `truncate` is
   allowed only for user-content (titles, headlines, file names) where ellipsis is honest.
2. **Numeric columns can never collide.** Tables (watchlist, portfolio) define explicit
   column tracks (grid or fixed flex-basis) with a ≥8px gutter; change% gets its own track;
   when the panel is narrower than the tracks' minimum, the row drops a column by priority
   (provenance chip → change% → price stays) instead of overlapping.
3. **Descender-safe heights.** Any fixed-height container holding text reserves
   ceil(fontSize × lineHeight) + 2px. h-6 + caption(12×1.5=18) ✓; anything tighter (the
   timeframe row class) moves to py-based sizing.
4. **Every flex row that can starve declares its collapse order** as width-based steps
   (container queries or measured breakpoints): full → short-labels → icons-only → overflow
   menu ("⋯"). Rows never overlap; the meta row, chart toolbar, brief meta header, settings
   section chips, and header status all get explicit collapse ladders.
5. **Buttons never wrap their label to two lines** (`whitespace-nowrap` + min-w or short
   form). "SET DEFAULT" class: fit, shorten ("DEFAULT"), or icon.

## 4. Density per surface

- **Data-dense** (watchlist, screener results, portfolio, audit log): caption cells, micro
  chips, 28px rows, hairline separators.
- **Reading** (chat transcript, brief, notes, learner flows): body/prose per §1, 1.5-1.6
  leading, max-w-prose in wide panels, lists indent 1.25rem and never overflow the column.
- **Forms** (settings, order entry, agent builder): body labels, caption hints, h-8 controls,
  label column min-w so the control column aligns; sections breathe (16px+ between groups).
- **Chrome** (toolbars, tab strips, meta rows): caption, h-6, gap-1.5, quiet (charcoal-300)
  until hover (lume), active = accent.

## 5. Affordance

- Anything clickable shows it: hover state (text/bg step) + cursor-pointer + (for chips) a
  subtle 1px border or bg vs static text. Status-bar chips (agent/lens/depth/ASK-AUTO/model)
  get separation (gap + hairline or pill bg) and a hover treatment.
- The active research-depth stop carries the accent + a one-shot scale/pulse animation when a
  run is live at that depth (motion-reduced honored).

## 6. Numbers

- Currency formats by the INSTRUMENT's currency, never the locale default (no ₹ on AAPL).
- Cost lines: "$0.0000" never renders — below $0.005 show "<$0.01" or omit; tokens use
  compact form ("12.4k tok").
