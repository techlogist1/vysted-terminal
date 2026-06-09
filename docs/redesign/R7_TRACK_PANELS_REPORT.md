# R7 Track P — Panels Polish Report

Branch `worktree-agent-r7-panels`. Scope per `R7_TRACK_PANELS_BRIEF.md`: every
owned panel brought to `VYSTED_DESIGN.md`, one conventional commit per
deliverable, gates (`typecheck` + `lint` + per-module `vitest` + prettier) run
per commit, full `pnpm test` at the end. Binary audit greps over all owned
surfaces: `text-[` = 0 · `rounded-[` = 0 · `shadow-*` = 0 ·
`rounded-(md|lg|xl|2xl)` = 0.

## Per-panel before → after

### Greeks dashboard (quant) — `feat(quant): redesign Greeks dashboard…`

- Before: a small results table stranded in dead space; no inline validation.
- After: input rail (32px fields, segmented payoff, inline validation that
  blocks the POST) | results column filling the width — overview-size price
  header with a request echo, per-greek metric-card grid (2→3→5 columns),
  full-width sensitivity DataTable, composed EmptyState whose CTA runs a real
  compute, first-run skeleton.

### Settings — `feat(settings): sectioned hierarchy…`

- Before: a wall of inconsistent provider rows; 8px checkboxes; "OpenRouter
  (broker)" label.
- After: sectioned hierarchy (AI Providers / Web search / Research / Region &
  locale / Advanced) with jump-nav, 32px rows with a column-stable right
  cluster, readable ToggleSwitch, plain "OpenRouter" label — **and the sidecar
  source of that label fixed** (below). Every pre-existing setting reachable;
  store wiring untouched.

### OpenRouter "(broker)" — killed at the runtime source

The frontend store default fix alone was insufficient:
`useLLMProvidersStore.refresh()` (ChatSidebar mount) mirrors the sidecar
`/llm/providers` payload verbatim, and `sidecar/config/model_registry.json`
still carried `"label": "OpenRouter (broker)"` — so the defect resurfaced live
whenever the sidecar was up. Fixed the registry row and pinned the label in
`sidecar/tests/test_llm_router.py::test_get_providers_returns_all` (the jsdom
no-broker test cannot see the sidecar, so the pin lives sidecar-side).
Out-of-ownership touch, recorded in `INTEGRATION_NOTES_R7_PANELS.md`.

### Equity overview — `feat(equity-overview): composed empty states…`

- Before: instructional placeholder copy rendering as primary content; header
  baseline mismatch.
- After: composed EmptyState with quick-load chips, baseline-aligned header,
  statements at DataTable rhythm, ratings metric strip.

### Option pricer (quant) — `feat(quant): option-pricer, bond-pricer, yield-curve…`

- Before: mixed text-caption/micro inputs, "Fill in the inputs…"
  centered-prose dead empty state, incompatible exercise×engine combos as a
  silent disable, hero-size price (28px is reserved for first-run).
- After: 32px/`text-body` control ladder throughout; engine list + payoff /
  exercise segmented controls as single bordered units; honest inline
  validation (`role=alert`, disables Price, blocks the POST) including the
  American×BS / American×MC incompatibilities; composed EmptyState with a
  live CTA; overview-size price header with request echo + MC standard error;
  Greeks metric-card grid; first-run skeleton.

### Bond pricer (quant)

- Before: no validation at all (NaN-able POST), prose empty state, cramped
  p-2 result cells.
- After: validation (positive face, ordered issue/settle/maturity dates,
  numeric YTM), composed EmptyState, clean-price overview header with request
  echo, dirty/accrued/duration/convexity metric-card grid.

### Yield curve (quant)

- Before: 11px micro-text inputs in the instrument grid, hand-rolled
  `grid-cols-4` sample table, permanently mounted empty chart frame.
- After: instrument grid on the 32px/`text-body` ladder with per-row
  aria-labels; rate column right-aligned tabular; validation (sample count
  3–200, tenor ≥ 1, positive rates); sampled curve through the shared
  DataTable (right-aligned tabular zero rate / DF); the chart mounts only with
  data — pre-bootstrap the surface is the composed EmptyState; first-run
  skeleton.

### Earnings calendar — `feat(earnings): statement-table estimate detail…`

- Before: estimate drill-down as a `grid-cols-3` key-value dump with local
  money formatting; empty chart frame with prose overlay; inline labels with
  `ml-2` inputs off the baseline; skeleton bars with 4px radius.
- After: estimate detail as a sectioned statement table (EPS / Revenue) on the
  shared DataTable, formatted via shared `formatPrice`/`formatUnit`; surprise
  chart renders a dense EmptyState when history is absent; filter row as
  micro-labels-over-32px-inputs on one baseline; skeletons squared. The main
  calendar table stays hand-rolled **only** because of the inline expansion
  row (DataTable has no expansion API — flagged to the lead in the
  integration notes).

### Analyst ratings — `feat(analyst-ratings): kill spinner-as-empty-state…`

- Before: the brief's named defect — `Loading {symbol}…` pulsing prose as the
  fetch window; a failed slice able to read as "No ratings history".
- After: table-shaped skeleton for the fetch window; slice failure with no
  data → composed error EmptyState with Retry (re-fires the slice fetch);
  failure over cached data → inline banner + table stays; no-symbol surface
  is a composed EmptyState; price-target timeline empty → dense EmptyState
  (chart mounts only with data); symbol input + tabs to the 32px ladder.

### Marketplace — `feat(marketplace,plugin-manager)…`

- Before: sentences set in the uppercase 11px micro role (header blurb, card
  descriptions, credential instructions); caption-size entry names;
  borderless credential inputs.
- After: descriptions/blurbs/disclaimers at caption; entry names at
  `text-body` 500 matching plugin-manager rows; state chips stay micro (the
  11px floor) with badge padding; install/enable/disable rows on the 32px
  ladder (error Re-enable on the 24px compact); credential inputs to the law
  (inset fill, 1px border, 32px, body text); weight-600 header dropped to the
  panel-title role.

### Plugin manager

- Before: 8px `size-4` checkbox toggle; hand-rolled empty state; `<p>` nested
  inside `<ul>` in the skeleton.
- After: readable 32px ToggleSwitch (sr-only checkbox keeps the
  `role="switch"` test/AT contract; mirrors the SettingsPanel switch — lift
  to shared flagged in integration notes); composed EmptyState with an Open
  Marketplace CTA; valid skeleton markup; redundant `font-mono` stripped.

### News feed

- Before: hand-rolled, vertically-stranded error and empty states; bare text
  Refresh affordance; source/time meta on the uppercase micro role.
- After: composed EmptyStates (error with Retry CTA, no-headlines with
  NewsAPI hint + Refresh CTA); Refresh as a 24px ghost Button (reads
  "Loading…" during the fetch, per the existing test contract); meta at
  caption; symbol chips stay micro (ticker labels).

### Macro

- Before: a literal spinner standing in for the chart while loading;
  hand-rolled centered error/idle states; pulsing "Loading featured series…"
  prose in the picker; caption-size search input.
- After: chart-shaped skeleton with an honest meta line; error + idle as
  composed EmptyStates (error CTA re-fires the series load); picker catalog
  window as a row skeleton; no-results / no-featured as dense EmptyStates;
  search input on the 32px/`text-body` law; result meta at caption.

### SEC filings

- Before: "Loading filings…" prose as the table's fetch window; weight-600
  titles; micro-role section nav (uppercased real section titles); caption
  inputs at px-2.
- After: row-shaped skeleton fetch window; filing-viewer no-detail error as a
  composed EmptyState with Retry (+ back-to-list); section nav + word counts
  at caption; panel-title-role headings; inputs at 32px/`text-body`/px-3;
  accession at caption tabular.

### Portfolio

Already largely law-clean (DataTable + EmptyState + 32px form from R6).
Sweep: asset-class select aligned to `text-body` like its sibling inputs;
quotes-stale Retry promoted to a 24px ghost Button.

### Notes

Editor/toolbar already law-clean from a prior pass. Sweep: scope chips +
add-symbol affordance to the 24px compact ladder; the active chip is a quiet
luminance step with bright text (was an inverted near-white fill, louder than
the law's segmented-active treatment); `[+] symbol` bracket marker.

## Verification

- Per-commit: `pnpm typecheck` (clean) + `pnpm lint` (0 errors; one
  pre-existing `react-hooks/exhaustive-deps` warning in
  `EquityOverviewPanel.tsx` predating this pass) + module vitest + prettier.
- Full `pnpm test` green at the end of the track (see final commit).
- Sidecar: `ruff format`/`check` clean; `pytest tests/test_llm_router.py`
  green (label pin included).
- Audit greps (all owned surfaces): `text-[` 0 · `rounded-[` 0 · `shadow-*`
  0 · `rounded-(md|lg|xl|2xl)` 0.

## For the lead to eyeball live

- **Settings**: provider rows with the sidecar UP — the dropdown and rows must
  read "OpenRouter" (the registry fix is what kills it; confirm no other
  cached payload reintroduces it).
- **Quant trio**: rail widths at narrow panel sizes (option/bond w-72, yield
  curve w-80); the metric grids stepping 2→3→5 at `md`/`xl`; yield-curve
  chart + DataTable after a real bootstrap against the live sidecar.
- **Earnings drill-down**: expanded row with real surprises (chart) and the
  sectioned estimate statement; a symbol with no surprise history should show
  the dense empty state, not a dead chart.
- **Analyst ratings**: kill the sidecar mid-session — the error EmptyState's
  Retry must recover each tab independently.
- **Marketplace**: install → needs-key → configure → enabled chip transitions;
  credential form inputs against a live keychain.
- **Plugin manager**: toggle a real plugin off/on with the new switch; the
  pending state must keep the switch disabled until the runtime settles.
- **News/macro**: cold-boot the app — the skeletons should resolve into data
  without latching error states (both panels auto-retry on sidecar bind).

## NEEDS-MANUAL-CHECK

- The yield-curve / price-target / surprise charts now mount only when data
  exists; jsdom mocks `createChart`, so the autoSize behaviour of a chart
  mounting into an already-laid-out container needs one live look.
- Settings keychain flows (Exa key save/remove, provider key dialogs) —
  wiring untouched, only a live keychain proves them.
- Settings `scrollIntoView` smooth-scroll inside the dockview scroller.
- `EmptyState` dense variant inside the macro picker's `max-h-48` listbox —
  confirm it doesn't push the list into scroll on small panels.
- The plugin-manager ToggleSwitch duplicates the SettingsPanel switch by
  design (shared components are the lead's) — lift to `components/ui` when
  convenient.
