# Recon — A8:dualpanel-axislock

I have everything I need. The test already renders `<ChartPanel api={{ id: "chart-A" }} />`, confirming dockview passes `props.api.id` and the test harness mirrors it. Now I'll write the dense blueprint.

# Dual-Panel Shared-Time-Axis Lock — Refactor Blueprint (Track 6 #3)

## 1) Findings — what exists today (file:line precise)

**Singleton command channel** — `src/store/chart-command.ts`. One global slot per command kind: `command`, `indicatorCommand`, `comparisonCommand` (each `{…, seq}`), plus three `active*` report slots. Mutators `loadSymbol/setIndicators/setComparison` (lines 59–75) bump `seq` only; **no target panel**. So with two charts open, a `loadSymbol("AAPL")` lands on _every_ mounted chart (all subscribe to the same slot) — exactly why side-by-side compare with distinct symbols is impossible today.

**ChartPanel consumes the singleton** — `src/modules/chart/ChartPanel.tsx`:

- `panelId` already resolved from dockview: `usePanelId(props.api)` (L191–195, L205); `ChartPanelProps { api?: { id?: string } }` (L186–188). Dockview 6.2.2 passes `props.api.id`; the test already renders `<ChartPanel api={{ id: "chart-A" }} />` (ChartPanel.test.tsx:460+).
- Command-consume effects: symbol L697–711, indicator L723–738 (already has an optional `cmd.symbol` scope guard), comparison L748–757. Each reads the global slot and applies unconditionally (symbol/comparison) — **no panel match**.
- Report-back effects: L715–717, L742–744, L760–762 → `reportActive*` (last-writer-wins across panels; already lossy with 2 charts).
- **Cross-chart sync (the model for axis-lock)** — broadcast effect L765–790: subscribes `subscribeCrosshairMove` + `timeScale().subscribeVisibleLogicalRangeChange(onRange)`; `onRange` reads `getVisibleRange()` and calls `broadcastVisibleRange(panelId, from, to)`. Consume effect L664–677: guards `broadcast.source === panelId` (self-echo skip) then `timeScale().setVisibleRange({from,to})`. **This is opt-in per-panel (`syncSubscriptions.visibleRange`), uses TIME range not logical range, and has no re-entrancy guard** — it relies on `setVisibleRange`-not-equal-to-current being a cheap no-op, which works for the loose existing sync but will oscillate under a tight bidirectional logical-range lock.
- `chart-sync.ts` bus (`setVisibleRange` L77–80, `selectSubscriptions` L114) is the precedent shape: per-panel `subscriptions` record, `source`-stamped payloads, `seq` re-trigger.

**Callers of the singleton** (all must keep working — backward-compat surface): `src/lib/host-actions.ts` L329 (`set_chart_symbol`), L342 (`set_chart_indicators`), L402/420–427 (`arrange_layout`, incl. `compare` → `loadSymbol(syms[0]) + setComparison(syms[1])`), `src/store/command-palette.ts` L129, `src/modules/chat/ChatSidebar.tsx` L352, `src/lib/dev-mcp-bridge.ts` L30.

**Compare template is single-chart-overlay** — `layout-templates.ts` L167–178: `compare` adds ONE `chart-panel`, maximized; the second symbol rides as an overlay via `setComparison`. True side-by-side needs a second panel id (dockview rejects duplicate ids, so it can't be a second `"chart-panel"` with id `"chart"`).

## 2) Exact change plan

### A. `src/store/chart-command.ts` — target-addressed channel (backward compatible)

Change each command slot from a single object to **`Map<targetPanelId, Cmd>` + a broadcast slot**. Keep the `active*` slots as a `Record<panelId, …>` so reports stop clobbering.

New shape:

```ts
const BROADCAST = "*"; // sentinel target = every chart (legacy behavior)
type SymCmd = { symbol: string; timeframe?: string; seq: number };
interface ChartCommandState {
  commands: Record<string, SymCmd | undefined>; // keyed by panelId or "*"
  indicatorCommands: Record<string, { indicators: string[]; seq: number } | undefined>;
  comparisonCommands: Record<string, { symbol: string; seq: number } | undefined>;
  activeSymbols: Record<string, string>; // per-panel reports
  activeIndicators: Record<string, string[]>;
  activeComparisons: Record<string, string | null>;
  // mutators: target defaults to BROADCAST so every existing call site is unchanged
  loadSymbol: (symbol: string, timeframe?: string, target?: string) => void;
  setIndicators: (indicators: string[], symbol?: string, target?: string) => void;
  setComparison: (symbol: string, target?: string) => void;
  reportActiveSymbol: (panelId: string, symbol: string) => void; // +panelId arg
  reportActiveIndicators: (panelId: string, keys: string[]) => void;
  reportActiveComparison: (panelId: string, symbol: string | null) => void;
}
```

- `loadSymbol(sym, tf, target = BROADCAST)` → `set(s => ({ commands: { ...s.commands, [target]: { symbol, timeframe, seq:(s.commands[target]?.seq ?? 0)+1 } } }))`. Same pattern for the other two mutators.
- **Back-compat read selectors** — add helpers so existing single-chart accessors don't break:
  - `selectCommandFor(state, panelId): SymCmd | undefined` → `state.commands[panelId] ?? state.commands[BROADCAST]` (panel-specific wins; falls back to broadcast). Same for indicator/comparison. **This is the broadcast/default-target fallback the task requires.**
  - `selectActiveSymbol(state)` (legacy host-actions diff "before") → return the single active symbol if exactly one chart, else the focused panel's (read `usePanelContextBus.getState().focusedSource`), else first. Keep a `activeSymbol` getter shim that returns `Object.values(activeSymbols)[0] ?? null` so `host-actions.ts` L176/L187 keep compiling.
- `resetChartCommandStoreForTests` (L79) → reset all six records to `{}`. **Update `chart-command.test.ts`** (asserts `state.command`/`activeSymbol` etc.) to the new record shape — mechanical.
- Export `BROADCAST` + the three `select*For` helpers + a new **`useAxisLockStore` slice** (below) — keep axis-lock in the SAME file or a sibling `src/store/axis-lock.ts` (prefer sibling; it has its own re-entrancy concern). I recommend a sibling `axis-lock.ts`.

### B. `src/store/axis-lock.ts` — NEW (the shared-logical-axis lock group)

```ts
interface AxisLockState {
  lockedGroup: string[] | null; // panelIds locked together, null = off
  range: { from: number; to: number; source: string; seq: number } | null;
  setLock: (panelIds: string[] | null) => void;
  broadcastRange: (source: string, from: number, to: number) => void;
}
```

- `lockedGroup` is the membership set; `range` carries a **logical** range (`{from,to}` floats from `LogicalRange`) plus `source` + `seq`. `broadcastRange` bumps `seq`.
- `isLocked(state, panelId) = state.lockedGroup?.includes(panelId) ?? false`.
- Persist `lockedGroup` into the workspace blob (see E).

### C. `src/modules/chart/ChartPanel.tsx` — consume per-panel + axis-lock

1. **Command consume (L697–757):** replace the three global selectors with the fallback selectors:
   `const chartCommand = useChartCommandStore(s => selectCommandFor(s, panelId));` (same for indicator/comparison). Effects bodies unchanged — they already react to a `seq`-bumped object. A panel-specific command supersedes a broadcast one within the same selector.
2. **Reports (L716, L743, L761):** pass `panelId`: `reportActiveSymbol(panelId, symbol)` etc.
3. **Axis-lock — replace the loose visible-range path with a guarded logical-range lock.** This is additive to the existing opt-in `visibleRange` sync (keep that for the legacy multi-chart loose-sync UI; axis-lock is the new tight bidirectional mode). In the broadcast effect (L765–790) the chart already owns `onRange`; add:

```ts
const applyingRef = useRef(false); // re-entrancy guard (module-level ref)
const onRange = (range: LogicalRange | null) => {
  if (!range) return;
  if (useAxisLockStore.getState().isLockedFor(panelId)) {
    if (applyingRef.current) return; // we set it ourselves → don't rebroadcast
    useAxisLockStore.getState().broadcastRange(panelId, range.from, range.to);
  }
  // ... keep existing loose visibleRange broadcast unchanged
};
```

New consume effect (mirror L664–677), subscribing to `useAxisLockStore(s => s.range)`:

```ts
useEffect(() => {
  if (!isLockedFor(panelId) || !axisRange || axisRange.source === panelId) return;
  const ts = chartRef.current?.timeScale();
  if (!ts) return;
  applyingRef.current = true;
  ts.setVisibleLogicalRange({ from: axisRange.from, to: axisRange.to });
  // clear the guard AFTER lightweight-charts fires its own range-change synchronously;
  // a microtask is enough (lwc dispatches subscribeVisibleLogicalRangeChange synchronously
  // inside setVisibleLogicalRange).
  applyingRef.current = false;
}, [axisRange, panelId, lockedMembership]);
```

**Use logical range** (`setVisibleLogicalRange`/`subscribeVisibleLogicalRangeChange`), not time range — logical range stays in lock-step bar-for-bar regardless of differing symbol bar counts, and the existing `onRange` already receives a `LogicalRange`. 4. **Lock UI:** add a toolbar button in the Sync group (L1042–1069) — "Lock ⟂" — calling `setLock([...currentChartPanelIds])`. Source the member ids from `useWorkspaceStore.getState().dockviewApi?.panels` filtered to `component === "chart-panel"`. Reuse the existing `Lock/Unlock` lucide import (L21).

### D. `src/lib/host-actions.ts` — compare → true dual panel (Tier-2, autonomous)

In `arrange_layout` `compare` branch (L421–423): after `applyLayoutTemplate(api, "compare", …)`, target the two charts explicitly:

```ts
cc.loadSymbol(syms[0], undefined, "chart"); // panel id "chart"
cc.loadSymbol(syms[1], undefined, "chart-compare");
useAxisLockStore.getState().setLock(["chart", "chart-compare"]);
```

The default `compare` template (overlay) stays the fallback; add a `compare-split` template (see E) that the planner selects when the second chart panel is wanted.

### E. `src/lib/layout-templates.ts` — add the second chart panel

- Add `PANEL.chartCompare = { id: "chart-compare", component: "chart-panel" }` (L28/L113). Two panels, same component, **distinct ids** — dockview-legal.
- Add a `compare-split` `LayoutTemplate` (L20, L167): two `chart-panel`s side-by-side (`{ id:"chart", … }`, `{ id:"chart-compare", position:{ referencePanel:"chart", direction:"right" } }`), `focus: "chart"`, no maximize. The existing `compare` (overlay) stays unchanged for back-compat.

### F. Workspace persistence — `src/lib/workspace.ts`

Add `axisLock: string[] | null` to `SerializedWorkspace`; serialize from `useAxisLockStore.getState().lockedGroup`; restore via `setLock(...)` (guard older blobs: `?? null`). Per the CLAUDE.md "persisted UI state rides the workspace blob" rule.

## 3) Risks + safe fallback per risk

| Risk                                                                                                         | Mitigation / fallback                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Feedback loop** (A sets B's range → B's `subscribeVisibleLogicalRangeChange` fires → rebroadcasts → A...). | `applyingRef` re-entrancy guard around `setVisibleLogicalRange` (lwc fires the change callback _synchronously_ inside the setter, so the flag is still true when the echo arrives). Plus `source === panelId` self-skip in the consume effect. Belt-and-suspenders: `seq`-gate ignores a range whose `seq` we already applied.                                                                                                 |
| **Target panel not mounted** (command addressed to `chart-compare` before it exists).                        | The command sits in `commands["chart-compare"]` until that panel mounts; on mount its consume effect reads the pending slot (effects already adopt a pending command on mount — L708). If the panel never opens, the command is inert (no crash) — identical to today's "no consumer" behavior. Host-actions `ensureChartOpen()` opens `chart` first; for split, call the split template before issuing the targeted commands. |
| **Lock references a closed panel** (user closes `chart-compare`).                                            | ChartPanel unmount cleanup (L302–318) calls `unregisterPanel`; add an `axisLock.removeMember(panelId)` there. If the group drops below 2 members, `setLock(null)` auto-disables.                                                                                                                                                                                                                                               |
| **Differing bar counts / timeframes between A & B** make logical ranges semantically misaligned.             | Logical-range lock still keeps panning/zoom in lock-step _visually_; document that meaningful overlap requires same timeframe. Lock is opt-in, so the user controls it. Fallback: the loose TIME-range `visibleRange` sync stays available for cross-timeframe alignment.                                                                                                                                                      |
| **Back-compat break** for the ~6 singleton callers.                                                          | All mutators default `target = BROADCAST`; `selectCommandFor` falls back to the broadcast slot → every existing single-chart call is byte-for-byte unchanged in behavior. Only `report*` signatures gain a `panelId` arg (3 internal call sites in ChartPanel).                                                                                                                                                                |
| **No Tier-1 file touched.**                                                                                  | All edits are in `src/store/*`, `src/modules/chart/*`, `src/lib/*` — none are locked. Confirm: no change to `types/plugin.ts`, safety, or §6.5.                                                                                                                                                                                                                                                                                |

## 4) Verification — exact steps

- **vitest (store):** `pnpm vitest run src/store/chart-command.test.ts src/store/axis-lock.test.ts` — assert: `loadSymbol("AAPL", undefined, "chart-A")` writes only `commands["chart-A"]`; `selectCommandFor(state,"chart-B")` falls back to `commands["*"]`; broadcast `loadSymbol("X")` reaches both; `setLock(["A","B"])` then `broadcastRange("A",10,50)` yields `range.source==="A"`; `removeMember("B")` collapses the group.
- **vitest (panel):** `pnpm vitest run src/modules/chart/ChartPanel.test.tsx` — extend the existing `<ChartPanel api={{ id:"chart-A" }} />` cases (L460+): render A and B; issue a panel-`A` symbol command; assert only A's symbol input updates (B unchanged) — proves targeting. Add a re-entrancy test: mock `chartRef` timeScale, fire `broadcastRange` from A, assert B's `setVisibleLogicalRange` called once and B does **not** rebroadcast (spy on `axisLock.broadcastRange`).
- **vitest (host-actions/layout):** `pnpm vitest run src/lib/host-actions.test.ts src/lib/layout-templates.test.ts` — assert `compare-split` plan has two distinct ids (`chart`,`chart-compare`) side-by-side, and the `arrange_layout` compare path issues two targeted `loadSymbol` calls + `setLock`.
- **Full gate:** `pnpm typecheck && pnpm vitest run` (record shapes change the store's TS surface — typecheck catches every stale caller).
- **rig (live, populated):** `mcp__tauri-mcp__start_session` → `evaluate_script` to call `applyLayoutTemplate(__vystedDockview,"compare-split")` + targeted `loadSymbol("NVDA",_,"chart")` / `loadSymbol("AMD",_,"chart-compare")` → `setLock(["chart","chart-compare"])`. `screenshot` two charts at 1920×1080; pan/zoom the LEFT chart via Playwright trusted wheel events (chrome-devtools can't synthesize `isTrusted` — per CLAUDE.md), screenshot to prove the RIGHT chart's logical range moved in lock-step and did **not** oscillate (no jitter = guard works). Capture both 1920×1080 and 2560×1440 into `docs/screenshots/v<tag>/`.
- **curl:** none — pure frontend; sidecar `/history` already exercised by the existing chart fetch.

Key files: `src/store/chart-command.ts`, NEW `src/store/axis-lock.ts`, `src/modules/chart/ChartPanel.tsx` (L191–205, 664–711, 716/743/761, 765–790, 1042–1069), `src/lib/host-actions.ts` L321–343/421–427, `src/lib/layout-templates.ts` L20/28/113/167, `src/lib/workspace.ts`, plus tests `src/store/chart-command.test.ts`, `src/modules/chart/ChartPanel.test.tsx`, `src/lib/{host-actions,layout-templates}.test.ts`.
