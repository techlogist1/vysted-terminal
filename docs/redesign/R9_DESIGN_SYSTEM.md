# R9 Design System — external authority, one scale, zero off-grid

R8's proportion law was self-graded and its own taste passed things a trained eye rejects.
R9 anchors every visual decision to external authority: **Refactoring UI's principles govern
ideology**, **Linear / Cursor / Claude desktop are the reference truth for density and
proportion**, and conformance is judged by **side-by-side screenshot comparison by a
fresh-context verifier** — never by the implementing agent.

This file supersedes `R8_PROPORTION_LAW.md` §1–§2 (type roles, control scale). R8's §3
overflow law, §5 affordance, and §6 numbers remain in force unchanged — they were sound;
the rendered system under them was not (see Root Cause).

## 0. Root cause R9 fixes (read this first)

The R4 `--spacing-N` theme tokens redefined Tailwind's numeric spacing utilities at HALF
the standard convention — but only for the steps that happened to be defined. Compiled
reality before R9: `h-6` = 12px, `h-7` = 28px (no token → standard multiplier), `h-8` =
16px. **h-7 rendered taller than h-8.** 1,897 call sites resolved against halved tokens,
51 against the standard multiplier, interleaved on every surface. That is the proportion
disease: clipped Settings fields (32px-intent controls rendering 16px), giant-pencil-next-
to-tiny-printer icons, oversized inputs next to undersized buttons.

**The R9 fix: standard Tailwind semantics are restored — 1 unit = 4px, everywhere.** The
halved numeric `--spacing-N` overrides are deleted from `styles/tokens.css`. Every spacing
utility in the app now means what it means in every other Tailwind codebase on earth.
Consequence: every surface must be re-tuned against this law (that is the R9 sweep; do not
"preserve the old look" — the old look was the bug).

## 1. Spacing — 8-pt grid

Base grid **8px**; **4px half-step** permitted everywhere; **2px quarter-step** permitted
ONLY for intra-control optical gaps (icon-to-label, dot offsets) — never for padding or
inter-element rhythm.

**Allowed spacing values (px):** 2*, 4, 8, 12, 16, 20, 24, 28†, 32, 40, 48, 64, 80, 96
(* restricted as above; † controls/rows only). In Tailwind classes that is:
`0.5* 1 2 3 4 5 6 7† 8 10 12 16 20 24`. Anything else — `gap-1.5`, `px-[7px]`, `py-[1px]`,
`mt-9` — is off-grid and fails the audit.

`scripts/audit-design-tokens.mjs` enforces the allowed set statically over `src/` and
`plugins/`; it runs in the gate battery. No new allowlist entries without a one-line
justification in the script.

## 2. Type — one modular scale, six sizes

One ratio (~1.2), snapped to whole px: **11 · 13 · 16 · 19 · 23 · 28**.

Utility names are kept (the ~92 files re-skin by revalue, the R6 trick); several names now
share a size and differ by weight/transform only:

| Utility | px | Role |
|---|---|---|
| `text-micro` | 11 | uppercase eyebrows, provenance chips, keycaps. THE floor — nothing renders below 11px, ever |
| `text-caption` | 13 | data cells (`tabular-nums`), chrome labels, chips, tabs, meta rows |
| `text-body` | 13 | reading prose in the dock, user chat, form labels |
| `text-panel-title` | 13 (weight 500) | panel titles — quiet, Linear-grade; titles do not shout |
| `text-prose` | 16 | wide reading panels only (Brief, Notes ≥420px column) |
| `text-section` | 19 | section heads |
| `text-overview` | 23 | overview / brief head |
| `text-hero` | 28 | rare hero (first-run only) |

12px, 15px, 18px, 22px die. Hierarchy below 16px is expressed by **weight (400/500/700)
and color (charcoal-500/400/100)**, not size — Refactoring UI: size is the bluntest
hierarchy tool; stop leaning on it.

## 3. Controls — one ladder, now actually true

- chrome chips/buttons **h-6 (24px)** · inputs & toolbar fields **h-7 (28px)** · form
  controls (Settings, Order entry) **h-8 (32px)**. Hit target ≥24×24.
- Icons: **12px** inside h-6 · **14px** inside h-7/h-8 · **16px** only for the composer's
  primary actions (plus/send). One icon size per surface.
- Rows: data rows 28px; form rows 32px; dockview tabs 28px.
- Symbol/ticker inputs size to content class: `w-[8.5rem]` fits "SAKSOFT.NS" + padding —
  symbol inputs are FIXED width, not flex-greedy (the R8 chart toolbar bug).
- Text containers reserve `ceil(fontSize × lineHeight) + 2px` (descender rule, R8 §3.3).

## 4. Color — monochrome field, scarce heat

The R6 Pure Black doctrine stands: pure-neutral zinc ramp, ONE scarce accent
(peach `amber-400 #fab283`) reserved for live agent activity, luminance-matched green/red
for P&L data only. R9 adds exactly one designed family — **research depth heat** — and
permits subtle Cursor-grade tinting ONLY through these tokens:

| Token | Value | Meaning |
|---|---|---|
| `--color-depth-normal` | `#f7f7f7` (lume) | NORMAL — quiet, near-white |
| `--color-depth-deep` | `#fab283` (amber-400) | DEEP — the brand peach |
| `--color-depth-ultra` | `#f08a4b` | ULTRA — hotter ember, one step more saturated; distinct from `negative` #e5544b (red, reserved for losses) |

Escalation reads as heat in one tonal family: white → peach → ember. The composer send
button fill keys to the active depth (armed state); the depth selector's active stop uses
the same token. Use nowhere else without a DECISIONS entry.

**Fewer borders** (Refactoring UI): prefer background-step or spacing separation over
hairlines. Hairlines survive where spacing cannot separate (table rows, dockview
separators, popover edges). Do not add a border where a `charcoal-875` surface step or
16px of space does the job.

## 5. Radius & motion

Unchanged: containers sharp (0), interactive controls 4px; motion tiers
120/180/240/160ms with the existing easings. "Claude-exact composer" means Claude's
**structure** (one input row, + inside-left, send inside-right, menu absorption) — NOT its
radius language. Vysted stays sharp.

## 6. Reference anchoring (how conformance is judged)

- References: **Claude desktop** (composer anatomy, transcript rhythm), **Cursor**
  (toolbar/chrome density, tinted hierarchy), **Linear** (panel chrome, settings forms,
  list density). Reference captures live in `docs/redesign/references/r9/`.
- Every visual claim ("composer matches reference") is verified by a fresh-context agent
  viewing OUR capture beside the REFERENCE capture, judging: proportion, density,
  whitespace, hierarchy, alignment. The implementing agent's own screenshot review proves
  nothing.
- Whitespace is generous BY DEFAULT (Refactoring UI: start with too much, remove): panel
  content padding 16px; section gaps 24px; dense data surfaces may compress to 8/12 but
  never below.

## 7. Per-surface density (R8 §4 carried, revalued)

- **Data-dense** (watchlist, screener, portfolio, audit log): caption-13 tabular cells,
  micro-11 chips, 28px rows, hairline separators.
- **Reading** (transcript, brief, notes): body-13 in dock, prose-16 in wide panels,
  leading 1.5–1.6, max-w-prose, 16px+ block spacing.
- **Forms** (settings, order entry): body-13 labels, micro-11 hints as eyebrows or
  caption-13 muted, h-8 controls, 24px between groups, label column min-w aligned.
- **Chrome** (toolbars, tab strips, meta rows): caption-13, h-6 controls, gap-2 (8px),
  quiet charcoal-300 → hover lume → active accent.

## 8. What every team must do

1. Build against THIS law, not against the app's previous rendered look.
2. Run `node scripts/audit-design-tokens.mjs` on your partition before pushing — zero
   violations.
3. Capture your surfaces at 1280 AND 960 width; no clipped/truncated/overlapping text at
   either; collapse ladders per R8 §3.4 where rows can starve.
4. Submit captures for side-by-side reference verification; expect rejection and a fix
   round — the verifier's eye is the gate, not yours.
