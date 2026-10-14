# CRITIQUE: `frontend-panels-data-surfaces`

**Subsystem:** Frontend Panels: Chart, Watchlist & Notes (`CODE_PARTITION.json` entry
`frontend-panels-data-surfaces`). 25 owning files, 5,707 LOC: `src/modules/chart/*` (incl.
`drawings/`, the ichimoku / volume-profile primitives, `toolbar.tsx`, `indicators.ts`),
`src/modules/watchlist/*`, `src/modules/notes/*`, `types/drawings.ts`, `src/lib/{chart-theme,
indicator-presets,symbol-autocomplete,fuzzy}.ts`.
**Method:** I invoked the `aposd-critique` skill and followed it. **Assessment independence was degraded
(sequential):** this worker has no sub-agent tool, so I finished and recorded Assessment A (Strategic
Thinker) before running Assessment B (Tactical Tornado). I skipped snapshot persistence to `.aposd/` because
this census file is the artifact.
**Read:** every non-test owning file in full, plus the callers and callees the claims depend on:
`src/store/{chart-drawings,chart-sync,chart-command,notes,symbols}.ts`, `src/lib/host-actions.ts`
(write_note, set_chart_*, loadSymbolIntoChart), `src/lib/workspace.ts` (serialize/restore order),
`src/components/CommandPalette.tsx` (symbol pick), `src/lib/sidecar-client.ts`, and the sidecar
`routers/{history,indicators}.py` and `services/indicators.py` (ichimoku, SUPPORTED_INDICATORS).
**Proofs run:**
- **Isolated sidecar `:52152`:** `/history/BTC%2FUSDT` returns 404, `/quotes/BTC%2FUSDT` returns 404,
  `/fundamentals/BTC%2FUSDT` returns 404, `/indicators/AAPL?indicators=rsi,bogus` returns 4xx
  "Unknown indicator(s)", and `/resolve/autocomplete?q=TC` ranks `TC` above `TCS`.
- **Indicator key parity:** the frontend's 50 keys and the sidecar's 50 keys match (checked with a
  `SUPPORTED_INDICATORS` diff).
- **Tiptap 3.25 scratch snippet** (jsdom, StarterKit + Markdown):
  - `toggleTaskList` is `undefined` and calling it throws a `TypeError`.
  - `setContent` emits 1 `update`.
  - An empty doc serializes as `""`.
- **wry 0.55.1 source:** its `WKUIDelegate` has no `runJavaScriptTextInputPanel`.

---

## Tactical Tornado verdict

**Risk: high in the Notes and chart input paths, low in the rendering leaves.** The leaves are
genuinely deep and careful: the drawing renderers, the volume-profile and ichimoku primitives, the
indicator catalog (50/50 parity with the sidecar) and the chart-theme single source. The tornado is in
the glue. Each panel owns a hand-rolled copy of state that another module also owns. Each copy was
reconciled for the one flow its author tested, and a comment then claims more than that.

| # | Red flag | Where |
|---|---|---|
| 1 | **Two sources of truth, edge-triggered sync.** The Tiptap doc and `useNotesStore` both own the note, and they are reconciled only when the scope changes. | `NotesPanel.tsx:139-148` vs `host-actions.ts:1176-1191`, `workspace.ts:346` |
| 2 | **Save keyed to the wrong moment.** The debounced write uses the scope that is current when the timer fires, and an empty-guard swallows legitimate saves. | `NotesPanel.tsx:166-178` |
| 3 | **Information leakage.** The chart symbol lives in local state, `chart-command.activeSymbol`, `chart-sync.symbol` and the panel-context snapshot, and each producer picked a different inbox. | `ChartPanel.tsx:259-260, 761-799, 884-906`; `CommandPalette.tsx:384` |
| 4 | **Contract outlived its premise.** The drawings contract is "per panel, multi-chart", but the chart became a singleton. | `types/drawings.ts:81-83,105-110` vs `chart/index.ts:24-30` |
| 5 | **Global listener for a panel-local shortcut.** | `ChartPanel.tsx:689-703` |
| 6 | **Input side never built for an output contract.** `locked`, `label` and `kindOptions.text` are rendered or stored but never editable. | `types/drawings.ts:93-99`, `ChartPanel.tsx:669, 1074-1079` |
| 7 | **Temporal race between sibling effects.** Indicators render against whatever candles happen to be cached. | `ChartPanel.tsx:364-419` vs `454-492, 559-602` |
| 8 | **No validation at a boundary.** Agent indicator keys are passed straight to the fetch. | `ChartPanel.tsx:807-812` |
| 9 | **Comments that lie.** | `WikiLinkExtension.ts:5-8` (click-to-chart); `indicator-presets.ts:4-5` (chart seeds presets); `fuzzy.ts:13-14` (palette helper); `ChartPanel.tsx:776-777` (palette uses the command channel); `drawings/base.ts:31`, `factory.ts:72` ("neutral charcoal-300" on an accent-named constant) |
| 10 | **Dead modules kept alive by their tests.** | `indicator-presets.ts`, `fuzzy.ts`, `notes-persistence.ts:80-98` |
| 11 | **React state used as an event bus.** Every crosshair move re-renders the whole panel. | `ChartPanel.tsx:321-325` |
| 12 | **Repetition with divergent invariants.** Four ISO-to-time converters. | `ChartPanel.tsx:147-206, 459-485` |
| 13 | **Browser-only primitive in a desktop webview.** | `NotesToolbar.tsx:146` (`window.prompt`) |

**Flag count: 13.** The most damning pattern is flag 1. The same store-vs-view split that
`CLAUDE.md` warns about for workspace state recurs here, and the only thing the user hears is a
successful "Appended to the RELIANCE note" while the text is being erased.

---

## Design principles score

| # | Principle | Grade | Evidence (file:line) | Consequence |
|---|---|---|---|---|
| 1 | Strategic over tactical | **violate** | `ChartPanel.tsx:632-676`: the drawing click path snaps to `seriesData.close` and commits `time:null` anchors. Ten renderers (`renderers.ts`) were built and tested against a contract whose input side was never finished (`locked`, text). | The advertised Draw toolset cannot place a level where the user clicks. |
| 2 | Deep modules | **at-risk** | Deep: `VolumeProfilePrimitive` (`volume-profile-primitive.ts:116-177`, one `setBuckets` hides scale mapping and bar-height derivation) and `fetchWatchlistQuotes` (`watchlist/api.ts:30-63`). Not deep: `ChartPanel.tsx:231-1581` is one 1,350-line function holding about 25 `useState` and 20 effects. | Every chart change has to be understood against the whole panel. |
| 3 | Information hiding | **violate** | Note body is owned twice (`NotesPanel.tsx:139-178` + `store/notes.ts`). Drawings have no instrument key (`types/drawings.ts:80-100`). `assetClass` is dropped at the watchlist row click (`WatchlistPanel.tsx:477`). | Data loss (COD-1), drawings shown on the wrong symbol (COD-3), dead crypto clicks (COD-9). |
| 5 | General-purpose modules are deeper | **at-risk** | `symbol-autocomplete.ts:2` claims to be "the ONE wiring", but `equity-overview/api.ts:45-58` re-implements it without `region`. `DrawingSpec.kindOptions: Record<string, unknown>` (`types/drawings.ts:92`) is general in shape, but only `text`/`fontSize` are ever read. | Two locale behaviours for one autocomplete, and an untyped options bag. |
| 6 | Different layer, different abstraction | **violate** | `NotesToolbar.tsx:146` uses `window.prompt`, which wry 0.55.1 (`wry_web_view_ui_delegate.rs:64-141`) does not implement. `ChartPanel.tsx:372,974` passes a slash symbol as a URL path segment. | The Link button is dead on desktop, and crypto history 404s. |
| 7 | Pull complexity downward | **violate** | Each caller re-decides symbol routing (`CommandPalette.tsx:384` uses the sync bus, `host-actions.ts:259` uses chart-command, `WatchlistPanel.tsx:477` uses the equity overview). The indicator-key check is pushed up to the sidecar's 4xx (`ChartPanel.tsx:811`). | A new caller picks an inbox at random. Cmd-K is a no-op (COD-4). |
| 8 | Better together or better apart | **violate** | Price and indicator loads are separate racing effects (`ChartPanel.tsx:364-419` vs `559-602`), yet the indicators are meaningless without their candles. `notes-persistence.ts` is split from the store and never read back. | Another symbol's overlays stay on the chart (COD-7). The `.md` mirror diverges. |
| 9 | Define errors out of existence | **violate** | The empty-guard at `NotesPanel.tsx:169` is meant for mount but also drops a legitimate empty save. One bad indicator key fails the whole request (`api.ts:28-32`). `fetchSymbolCandidates` swallows every failure into `[]` (`symbol-autocomplete.ts:52-54`). | A cleared note resurrects, all indicators vanish, and "sidecar down" reads as "no match". |
| 10 | Design it twice | **violate** | Drawings kept the "per non-singleton panel" key after the singleton decision (`chart/index.ts:24-30` vs `store/chart-drawings.ts:4-7`, which still says "non-singleton"). The sync bus was kept after its multi-chart premise died. | Design debt was shipped as a live feature (the Sync popover). |
| 11 | Comments describe non-obvious | **violate** | `WikiLinkExtension.ts:5-8`, `indicator-presets.ts:4-5`, `fuzzy.ts:13-14`, `ChartPanel.tsx:776-777`, `chart/index.ts:10` ("20-indicator"; there are 50), and `NotesPanel.tsx:90` ("undefined = general"; the store uses `""`). | Readers (and audits) believe features exist that do not. |
| 12 | Comments first | **pass** | Contracts are written before code and are precise where they are true: `types/drawings.ts:37-49` (null-axis semantics), `chart-theme.ts:1-18` (why canvas cannot read CSS vars), and the `ChartPanel.tsx:83-101` collapse ladder. | Intent is recoverable even where the implementation drifted. |
| 13 | Choosing names | **at-risk** | `ACCENT_CORAL`/`coralFill` are gray (`chart-theme.ts:29,50`), documented at `chart-theme.ts:13-17`. Two `CHART_THEME` constants have different shapes (`ChartPanel.tsx:108` vs `chart-theme.ts:80`). `useSymbolsStore as useWatchlistStore` is aliased at `WatchlistPanel.tsx:21`. | Mild cognitive load. The name collisions invite importing the wrong `CHART_THEME`. |
| 14 | Modifying existing code | **violate** | The singleton fix (`chart/index.ts:24-30`) left the multi-chart store comment (`chart-drawings.ts:4-7`), the drawings key, the sync bus and the Sync menu in place. Presets and fuzzy were orphaned rather than removed. | Each change left the surrounding design worse than it found it. |
| 15 | Consistency | **at-risk** | The candle and indicator converters de-duplicate timestamps (`ChartPanel.tsx:147-179`) but the comparison converter does not (`187-206`). The watchlist guards per-symbol crypto failures (`api.ts:46-51`) but lets one equity-batch failure fail everything (`38`). The ToolbarDisclosure Escape is a document listener while the panel's is a window listener (`toolbar.tsx:147`, `ChartPanel.tsx:701`). The ordering is correct but implicit. | Invariants must be rediscovered per function. |
| 16 | Code should be obvious | **violate** | A global Backspace deletes a drawing from any input (`ChartPanel.tsx:696-699`). The Lock toggle has no effect. The slash menu highlights row 0, but Enter inserts a newline (`SlashCommandExtension.ts:75-81`). | The user's model of the UI is wrong in exactly the destructive cases. |
| 17 | Design for the future | **at-risk** | The `asset_class` parameter exists on `fetchIndicators` (`api.ts:26`) but no caller passes it. `presetFor(..., region)` has an unused `region` (`indicator-presets.ts:74-77`). | Speculative seams sit next to unbuilt real paths (crypto charting). |
| 18 | Performance as design | **violate** | `useChartSyncBus(s => s.crosshair)` / `s.visibleRange` is selected as React state (`ChartPanel.tsx:323-324`) and re-published on every pointer move (`852-866`). The watchlist polls every 5 s forever, even after errors and while hidden (`WatchlistPanel.tsx:219-221`). `NotesPanel` subscribes to the whole notes store (`:87`) and passes inline `configure()` extensions, so `useEditor` calls `setOptions` on every render (`@tiptap/react useEditor.ts:223-231`). | Pointer-rate re-renders of the largest panel, plus steady background load. |
| 19 | Increments are abstractions, not features | **at-risk** | The R7-R9 toolbar ladder is a clean increment (`ChartPanel.tsx:83-101,272-278`). The drawing tools and notes editor landed as feature lists (ten kinds, ten slash items) without the abstractions the features need (anchor resolution, store/editor sync). | Features count as shipped while their core interaction is missing. |

**Summary: 1 pass, 6 at-risk, 11 violate (1/18 pass).** Information Leakage (book #4) is graded in the
Tactical Tornado scan (flags 1 and 3) rather than as a row.

---

## Overall impression

The leaves are good engineering. `VolumeProfilePrimitive` and `IchimokuCloudPrimitive` hide
coordinate mapping behind one setter. The indicator catalog matches the sidecar key for key.
`chart-theme.ts` is a real single source that `tokens.css` agrees with today (`#161616`,
`#a8a8a8`, `#3fbf6f`, `#e5544b` all match). The watchlist's column drop-priority ladder is careful.

The panels are shallow wrappers around several half-owned states, and every serious finding
comes from state that more than one module owns:
- the note body (editor vs store);
- the chart symbol (four stores);
- a drawing's instrument (nowhere);
- a symbol's asset class (dropped at the click).

**The single biggest opportunity: give each piece of panel state exactly one owner and make every
other surface read from or command that owner.** Concretely:
- **Notes:** the store owns the body and the editor mirrors it.
- **Chart:** chart-command owns symbol, indicators and compare. Delete chart-sync and persist the chart
  state in the workspace blob.
- **Drawings:** key them by instrument.

---

## What's working

1. **The drawing renderers and the base primitive** (`drawings/base.ts:156-196`,
   `renderers.ts`). One `DrawingPrimitive` hosts any renderer, converters are injected on `attached`,
   and null axes are tolerated per kind. Adding a kind is one class plus one switch arm
   (`factory.ts:24-47`), so change amplification stays low.
2. **The price-load error handling** (`ChartPanel.tsx:364-419, 1500-1511`). It clears the prior
   series on empty data, separates the in-EOD-only reason from "no data", adds a retry nonce and an
   opaque overlay, and honours freshness and session labels. This is the pattern the indicator path
   should copy.
3. **The watchlist provenance and liveness honesty** (`WatchlistPanel.tsx:92-130`). A non-live quote
   never flashes and never colours its change, which removes a class of "stale price read as a live
   move" errors by construction.

---

## Priority issues

- **[P0] The Notes editor and store both own the note body.**
  - **Findings:** COD-1, COD-2.
  - **Principle:** Information hiding (#3), define errors out (#9).
  - **Symptom:** Unknown unknowns. Any non-editor writer (agent `write_note`, workspace load) is
    silently overwritten.
  - **Why it matters:** Data loss comes with a false success message, on the flow the product pitches
    ("the agent writes into your notes").
  - **Fix:** In `NotesPanel.tsx`:
    - Subscribe to `noteFor(scope)`.
    - Keep `lastWrittenRef`. When the store value differs from it, call
      `setContent(v, {emitUpdate:false})`.
    - Capture `{scope, md}` on each update and flush on scope change and unmount.
    - Replace the `:169` guard with a "user-edited" flag.
- **[P1] Chart state has no single owner.**
  - **Findings:** COD-3, COD-4, COD-12.
  - **Principle:** Information leakage (Tactical Tornado scan flag 1 and flag 3 area); pull complexity
    downward (#7).
  - **Symptom:** Change amplification. Four stores hold the symbol, drawings have no instrument, and
    the sync bus has no peer.
  - **Why it matters:** Cmd-K ticker picks do nothing, drawings follow the user across instruments, a
    relaunch resets to SPY, and the panel re-renders at pointer rate.
  - **Fix:**
    - Route every symbol producer through `loadSymbolIntoChart`.
    - Delete `chart-sync` and the Sync popover.
    - Add `symbol` (and `timeframe`) to `DrawingSpec` and filter drawings by them.
    - Persist `{symbol, timeframe, indicators, compare}` in `SerializedWorkspace`.
- **[P1] The drawing input path does not match the drawing contract.**
  - **Findings:** COD-5, COD-6.
  - **Principle:** Strategic over tactical (#1), obviousness (#16).
  - **Symptom:** Cognitive load for the user. Anchors snap to the close, off-bar drawings are
    invisible, Text is fixed to "label", Lock does nothing, and Backspace in any input deletes a
    drawing.
  - **Why it matters:** The analysis toolset is unusable for real levels, and user work is silently
    destroyed.
  - **Fix:** In `handleChartClick`:
    - Resolve the price with `coordinateToPrice(param.point.y)`.
    - Resolve off-bar time through `coordinateToTime`.
    - Scope the delete shortcut to the chart container and skip inputs.
    - Honour `locked`, or remove the Lock control.
    - Add inline text entry for the Text tool.
- **[P2] The indicator path has no boundary validation and no stale-state clearing.**
  - **Findings:** COD-7, COD-8.
  - **Principle:** Better together (#8), define errors out (#9).
  - **Symptom:** Unknown unknowns. Another symbol's overlays are shown, and one bad agent key blanks
    every indicator.
  - **Fix:**
    - Clear the indicator series at the start of each load and in the `catch`.
    - Render indicators only for the committed `{symbol, timeframe}`.
    - Filter command keys through `indicatorByKey`.
- **[P2] Symbol identity drops asset class.**
  - **Finding:** COD-9.
  - **Principle:** Information hiding (#3).
  - **Symptom:** Unknown unknowns. Two of the six default watchlist rows open a 404 overview, and
    crypto can never be charted.
  - **Fix:**
    - Pass `{symbol, assetClass}` through `openCompanyOverview` and `loadSymbolIntoChart`.
    - Route crypto to `cryptoHistory`.
    - Stop putting `/`-bearing symbols in path segments.

---

## Persona walkthrough

**Tactical Tornado.** The Tornado made the Notes panel work for the demo flow: type, switch
chip, type. It then bolted on each new writer without asking who owns the body:
- `write_note` in `host-actions.ts:1176-1191` writes the store and calls `openPanel("notes")`.
- The editor's `prevScopeRef` gate (`NotesPanel.tsx:143`) guarantees the new text is never shown.
- The next debounced save (`:168-178`) guarantees it is erased.

The chart shows the same pattern. The singleton fix (`chart/index.ts:24-30`) was a one-line
`singleton: true` that left the drawings key, the chart-sync bus, the Sync popover and the
multi-chart comments in place. When Cmd-K "didn't work", a second always-consumed channel was added
(`ChartPanel.tsx:775-793`) rather than moving the palette onto it, and the comment claims the palette
was fixed.

**Strategic Thinker.** The Strategic Thinker would design each panel's state twice before writing
effects. For Notes, the choice is between "editor-authoritative with store mirror" and
"store-authoritative with editor view". Every external writer is a store writer (agent, workspace
load, a future sync), so they would pick store-authoritative, and the P0 disappears by
construction. For the chart, they would define one `ChartState` (symbol, assetClass, timeframe,
indicators, compare, drawings keyed by symbol) that is owned by the chart-command store and
persisted in the workspace blob. `ChartPanel` then shrinks to "render ChartState and emit
commands". With the multi-chart premise dead, chart-sync, `reportActive*` and the panel-context
duplication all collapse into reads of one store.

---

## Minor observations

- **Indicator colours:** `INDICATOR_COLORS[lineIndex % n]` (`ChartPanel.tsx:519`) colours every
  single-line overlay `#ededed`, so SMA and EMA are indistinguishable except by their title label
  (folded into COD-15).
- **Chart-theme lockstep drift:** the three-place lockstep is held only by a comment. `chart-theme.ts:45`
  labels `ACCENT_CORAL_RGB` (`204, 204, 204`) "three-place lockstep", but `globals.css:55`
  `--accent-rgb` is `120 120 120`. Either the roles differ and the comment is wrong, or the values
  have drifted. `CLAUDE.md`'s "zinc + cool-indigo" description of this palette is also stale against
  `tokens.css` (pure grays). No test enforces the mirror.
- **Unused fib-retracement values:** `FibRetracementRenderer` computes `yB` and then `void yB`
  (`renderers.ts:177,199`). `DrawingConverters.paneSize` returns `{0,0}` and is never used
  (`base.ts:180-183`).
- **Sidecar coupling on label strings:** the Ichimoku cloud and Parabolic SAR dispatch on sidecar
  label strings (`"Senkou Span A"`, `"parabolic_sar"`, `ChartPanel.tsx:505,534-535`). This is
  stringly-typed coupling across the process boundary with no shared constant.
- **SymbolChipInput commits on blur:** it commits a half-typed symbol on blur (`NotesPanel.tsx:459`),
  so clicking away switches the scope to a partial ticker. The scope-chip comment says "up to 5" but
  the code slices 8 (`:204-208`).
- **Watchlist autocomplete blur:** `onBlur={() => setTimeout(..., 120)}` has no cleanup
  (`WatchlistPanel.tsx:339`).
- **SPY default:** `DEFAULT_SYMBOL = "SPY"` (`ChartPanel.tsx:80`) is a US default in an
  Indian-markets product. Every relaunch lands there because the chart state is not persisted
  (COD-3).
- **Stale WikiLink symbols:** WikiLink `getSymbols` captures the first render's `symbolEntries`
  (`NotesPanel.tsx:105-110,125`). Extension options are fixed at plugin creation, so watchlist
  additions do not appear in `[[` suggestions until the panel remounts.

## Questions to consider

- If the notes store were the only owner of the note body, would `persistNoteMd` need to exist
  in the panel at all, rather than as a store subscriber that also covers agent writes?
- With the chart a singleton, is there any remaining caller for `chart-sync`? Could `ChartPanel`
  drop its ~120 lines of sync effects and the Sync popover?
- Should a drawing belong to `(symbol)` or to `(symbol, timeframe)`, given that daily-anchored
  times do not exist on intraday bars and `timeToCoordinate` returns null for them?
- Could the indicator catalog be served by the sidecar (one GET) so key parity is structural
  rather than a 50-line hand mirror?

## Findings index (raw file `census/raw/code-frontend-panels-data-surfaces.json`)

| raw_id | sev | title |
|---|---|---|
| COD-frontend-panels-data-surfaces-1 | critical | Notes editor ignores store writes to the focused scope, and the next keystroke erases agent/workspace note content |
| COD-frontend-panels-data-surfaces-2 | high | Debounced save: a cleared note never persists, and edits within 600 ms of a scope switch or close are lost |
| COD-frontend-panels-data-surfaces-3 | high | Drawings keyed by panel only: shown on every symbol and after relaunch. Chart symbol/timeframe/indicators are not persisted |
| COD-frontend-panels-data-surfaces-4 | high | Cmd-K ticker pick is a no-op (palette uses the opt-in sync bus). Four stores hold the chart symbol, and Sync is dead UI |
| COD-frontend-panels-data-surfaces-5 | medium | A global Backspace/Delete deletes the selected drawing from any input and ignores lock |
| COD-frontend-panels-data-surfaces-6 | medium | Drawing anchors snap to the close, off-bar drawings are invisible, Text is always "label", and Lock is dead |
| COD-frontend-panels-data-surfaces-7 | medium | The previous symbol's indicators persist through load and error. SAR is computed against stale candles |
| COD-frontend-panels-data-surfaces-8 | medium | Unvalidated agent indicator keys: one unknown key fails all indicators |
| COD-frontend-panels-data-surfaces-9 | medium | Crypto rows open a 404 overview, and the chart cannot chart crypto |
| COD-frontend-panels-data-surfaces-10 | medium | Task List throws a TypeError, slash/wiki menus are keyboard-dead, and wikilinks are plain text |
| COD-frontend-panels-data-surfaces-11 | medium | The Notes Link button uses `window.prompt`, which is unsupported in the macOS Tauri webview |
| COD-frontend-panels-data-surfaces-12 | medium | The whole ChartPanel re-renders on every crosshair move and pan |
| COD-frontend-panels-data-surfaces-13 | medium | Watchlist add/remove snapshot race, stale autocomplete pick on Enter, and polling that never backs off |
| COD-frontend-panels-data-surfaces-14 | low | Dead modules with tests (indicator-presets, fuzzy, exportNoteMd) and a write-only `.md` mirror |
| COD-frontend-panels-data-surfaces-15 | low | The comparison "%" normalizes one side onto a hidden scale, with no de-dup, and overlays share a colour |

**Cross-subsystem note:** COD-4's producer (`CommandPalette.tsx`) belongs to
`frontend-panels-agent-shell`, and COD-1's second writer (`host-actions.ts` write_note) belongs to
`host-actions-proposed-changes`. Both are graded here because the consumer-side ownership defect lives
in this subsystem.

## Run notes

- Target: 25 owning files, all non-test files read in full. The 6 test files were skimmed for coverage.
- Assessment independence: degraded (sequential; no sub-agent tool).
- Ignore list: none (`.aposd/critique/ignore.md` absent).
- Snapshot persistence: skipped (census file is the artifact).
- Temp files: one jsdom snippet in the session scratchpad, not in the repo.
- Model: claude-opus-5-5[1m].
