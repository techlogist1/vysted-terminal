# Teammate A — Phase 2 self-report

Worktree: `worktree-agent-A`. Branched from `origin/main` at `3384054`
(foundation F1+F2+F3 complete) and pushed five commits on top.

## What shipped

### 1. Sidecar — 30 new indicators (target: ≥25)

**All 30 shipped** across six categories. Each has a `compute_*` function in
`sidecar/services/indicators.py`, an `_BUILDERS` dispatch entry, an alias where
one is conventional, and a unit test pinning a known mathematical property.

- **Moving averages (5):** WMA, HMA (Hull), DEMA, TEMA, KAMA
- **Momentum (5):** TSI, KST, Awesome Oscillator, PPO, Ultimate Oscillator
- **Volatility (4):** Std Dev, Bollinger Bandwidth, Donchian Channels,
  Chaikin Volatility
- **Volume (5):** A/D Line, Chaikin Money Flow, Force Index,
  Ease of Movement, VPT
- **Trend (6):** Aroon, Aroon Oscillator, Vortex, Mass Index, Pivot Points,
  SuperTrend
- **Statistical (5):** Linear Regression, Standard Error Bands, HLC3,
  OHLC4, Median Price

`SUPPORTED_INDICATORS` count is now 50 (Phase 1's 20 + Phase 2's 30); the
chart-panel `INDICATOR_CATALOG` mirrors them by hand.

### 2. Indicator catalog UI grouped into 6 categories

Added `category: IndicatorCategory` to `IndicatorDef` and
`indicatorsByCategory()` helper. Selector renders six section headers
(MOVING AVERAGES / MOMENTUM / VOLATILITY / VOLUME / TREND / STATISTICAL)
each with its own 2/3/4-column responsive grid. Visible in screenshots.

### 3. Ten drawing tools

All ten kinds shipped under `src/modules/chart/drawings/`:

- `base.ts` — abstract `DrawingRenderer` + `DrawingPrimitive` collapsing
  the `ISeriesPrimitive<Time>` lifecycle.
- `renderers.ts` — one renderer class per `DrawingKind`: trendline,
  horizontal-line, vertical-line, ray, rectangle, ellipse, fib-retracement,
  fib-extension, parallel-channel, text. Standard fib levels
  (0/0.236/0.382/0.5/0.618/0.786/1) shared between the two fib kinds.
- `factory.ts` — `createDrawingPrimitive(spec)` switch + `pointsRequired(kind)`
  + `DEFAULT_DRAWING_STYLE`.

### 4. Drawing toolbar UI

ChartPanel renders a 10-button toolbar with kind labels (Trend / H-Line /
V-Line / Ray / Rect / Ellipse / Fib Retr / Fib Ext / Channel / Text). Active
state is shown via amber highlight + a "click chart N more time(s)" hint.
Drawing inspector (visible when ≥1 drawing on the panel) lists every
drawing with select / lock-toggle / delete controls + a clear-all button.
Escape clears the active tool/draft; Delete/Backspace removes the
selected drawing.

### 5. Drawing persistence — workspace JSON roundtrip

`SerializedWorkspace.chartDrawings?: WorkspaceDrawings` carries the
`byPanel` map. `serializeWorkspace` snapshots the chart-drawings store,
`deserializeWorkspace` calls `replaceAll` on it (older workspaces without
the field clear drawings on load — verified by test). Roundtrip test in
`src/lib/workspace.test.ts`: serialise → mutate → deserialise → equality.

### 6. Multi-chart sync

- Chart panel converted to `singleton: false`.
- `useChartSyncBus` Zustand store with three independent flavors
  (crosshair / visibleRange / symbol). Subscribers self-identify by
  `source` so they skip self-echoes.
- Toolbar exposes three opt-in toggles (Cx / Zm / Sy).
- `useWorkspaceStore.openPanel` mints a unique panel id when the spec is
  non-singleton so dockview's id-uniqueness invariant holds.

### 7. Comparison overlay

Second-symbol form fetches OHLCV at the active timeframe, optionally
normalises with `(close[i]/close[0]-1)*100`. Renders as a line series on
the same chart; normalised mode rides its own `priceScaleId: 'left'` so
the candle scale is unaffected. % toggle and × remove visible after add.

## What deferred

**None below the 25-indicator floor.** All 30 indicators ship.

## Tier-2/3 autonomous calls (documented in commit bodies)

- **A6 indicator selection:** kept the suggested set verbatim — every
  textbook-standard indicator was tractable as a pure pandas/numpy
  function, no substitutions needed.
- **DEMA/TEMA tests:** asserted *mean* absolute lag vs EMA across the
  settled tail rather than per-point comparison. The lag-reduction
  property is provably true on average but path-dependent at any
  individual bar; pinning a single tail value made the test brittle.
- **`category` field:** added to TypeScript `IndicatorDef` only, not the
  Pydantic `IndicatorSeries` — the sidecar already returns enough
  (`name` + `panel`); category is a pure UI grouping concern. Keeps the
  wire payload lean and avoids cross-language sync.
- **Drawing factory shape:** all ten kinds in one `renderers.ts` file
  rather than ten separate files. Each renderer class is small (~30
  lines), and a single file makes the kind→renderer mapping in
  `factory.ts` and the FIB_LEVELS constant trivially shared.
- **Stable empty references:** `chart-sync.ts` and `ChartPanel` use
  frozen empty references for fallback selectors so `useSyncExternalStore`
  does not see a fresh object every render and trigger an infinite update
  loop. (One I diagnosed during integration testing — surfaced as
  "Maximum update depth exceeded".)

## Tier-4 items

**None.** No `types/plugin.ts` extension needed; no LICENSE change; no
shared-contract change beyond F3's `types/drawings.ts` (which the lead
already shipped).

## Visual verification — POPULATED state

Screenshots saved to `docs/screenshots/v0.3.0/teammate-a/`:

- `chart-1920x1080.png` — chart with MA/Bollinger/RSI/Hull MA/Aroon
  active on populated SPY candles, QQQ comparison overlay added (% on),
  drawing toolbar visible with all 10 kinds, sync controls visible,
  full 50-indicator catalog grouped into six categories.
- `chart-2560x1440.png` — same view at higher resolution.
- `chart-toolbar-active-1920x1080.png` — same chart with the Trend
  drawing tool active (amber highlight, "click chart 2 more time(s)"
  hint visible) plus crosshair + symbol sync toggles enabled.
- `chart-toolbar-active-2560x1440.png` — same at higher resolution.

### Drawing-render screenshot deferral — Tier 3, documented

Inserting actual drawings on the live chart canvas via chrome-devtools
MCP synthesised events did not trigger lightweight-charts'
`subscribeClick` handler (LWC binds to its canvas with isTrusted-event
checks that browser-dispatched events fail). Three approaches tried:

1. Direct `MouseEvent` dispatch on container — not received by LWC.
2. `PointerEvent` + `MouseEvent` on each canvas in pane — not received.
3. POST workspace with drawings via fetch + reload — fetch initially
   blocked (CORS turned out fine; the issue was the sidecar PID I had
   spawned in a Bash background slot died when its stdin closed —
   intentional sidecar behaviour, see CLAUDE.md gotcha).

The drawing primitives have full unit-test coverage (`drawings.test.ts`
asserts each renderer's actual `fillRect`/`stroke`/`ellipse` canvas
calls through a recording mock context) and the toolbar UI is visibly
populated with all 10 tools + the active-state hint visible in
screenshots — the kind of visual proof for the toolbar surface, with
unit tests pinning the renderer-canvas contract.

If the auditor wants on-chart drawing screenshots before merge, a
follow-up would be: spin up `pnpm tauri dev` (real desktop window with
real Tauri-managed sidecar) + manually click two points on the chart
with the Trend tool active. ~5 minutes.

### Tauri bridge in the dev browser — Tier 3, documented

Visual verification via `pnpm dev` requires the Tauri `invoke` shim
because `getSidecarBaseUrl` calls `invoke('get_sidecar_port')`. I used
chrome-devtools MCP's `initScript` to define a minimal
`window.__TAURI_INTERNALS__.invoke` that returns the known dev sidecar
port (51763); no source change in `src/lib/sidecar-client.ts`. Pattern
worth promoting to a documented dev convention if Phase 3+ teammates
also need browser-side visual verification — but a code change to the
shared client is out of my scope.

## Final test / lint / typecheck status

### Frontend (worktree root)

```
pnpm typecheck
> tsc --noEmit
[clean]

pnpm lint
> eslint .
[clean]

pnpm format:check
> prettier --check .
All matched files use Prettier code style!

pnpm test
Test Files  13 passed (13)
     Tests  96 passed (96)
```

### Sidecar (`C:\dev\vystedterminal\sidecar\.venv`)

```
python -m pytest sidecar
143 passed in 1.78s

python -m ruff check sidecar
All checks passed!

python -m ruff format --check sidecar
44 files already formatted
```

## Phase-1 regression

The 20 Phase-1 indicators all still resolve through the same `_BUILDERS`
dispatch (extended, not replaced); Volume Profile / Parabolic SAR / VWAP
/ Ichimoku tests all green; the Phase-1 ChartPanel test cases (RSI
toggle, Volume Profile attach/detach, Ichimoku cloud attach, SAR
markers) all still pass against the rewritten ChartPanel.

## Files I touched

Owned (created/modified):

- `sidecar/services/indicators.py` — +30 compute fns, +30 alias entries
- `sidecar/tests/test_indicators.py` — +29 new tests
- `src/modules/chart/ChartPanel.tsx` — drawings/sync/overlay integration
- `src/modules/chart/ChartPanel.test.tsx` — +6 new tests
- `src/modules/chart/indicators.ts` — category grouping, 50 entries
- `src/modules/chart/index.ts` — singleton:false
- `src/modules/chart/drawings/base.ts` (NEW)
- `src/modules/chart/drawings/renderers.ts` (NEW)
- `src/modules/chart/drawings/factory.ts` (NEW)
- `src/modules/chart/drawings/drawings.test.ts` (NEW)
- `src/store/chart-drawings.ts` (NEW)
- `src/store/chart-drawings.test.ts` (NEW)
- `src/store/chart-sync.ts` (NEW)
- `src/store/chart-sync.test.ts` (NEW)

Touched (within reasonable scope, no shared-contract change):

- `src/lib/workspace.ts` — added `chartDrawings` field to
  `SerializedWorkspace` (additive, optional)
- `src/lib/workspace.test.ts` — +2 tests for drawings roundtrip
- `src/store/workspace.ts` — `openPanel` mints unique id for
  non-singleton specs (the chart panel needs this; no other module
  consumes the change)

`docs/screenshots/v0.3.0/teammate-a/` — 4 PNGs.
