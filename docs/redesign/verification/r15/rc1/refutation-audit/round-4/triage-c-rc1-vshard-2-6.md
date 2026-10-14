# triage-c — rc1-vshard-2:6 (tie R15-UI-021)

Auditor: triage-c, rc1 gate round 4. Written 07:29 IST. HEAD is 7c450c8e and its code tree equals 01015033; `git diff 01015033 HEAD -- src` is empty.

**Verdict: partial on R15-UI-021. Severity: medium (kept).**

## Shard claim

rc1-vshard-2:6 reports this sequence: two ChartPanels each have a selected trendline, the user clicks a non-focusable spot, and one Backspace on `document.body` deletes the drawing in both charts.

## Tied entry

R15-UI-021 is fixed (batch 6, d2e0e78 + 4c9f751) and has the class `global-listener-scope`.

- **Title:** "Pressing Backspace/Delete anywhere in the app (chat composer, symbol box) deletes the selected chart drawing".
- **root_cause:** "A panel-scoped shortcut installed as a global listener; **selectedDrawingId persists after focus leaves the chart**."
- **fix_shape:** "Bail when event.target is input/textarea/contentEditable **or outside containerRef**; skip locked drawings."

The review follow-up 4c9f7516 deliberately exempted `document.body` from the outside-root bail. The reason is that WebKit does not focus a clicked chip, so a Delete pressed after selecting the chip targets body.

## Code at HEAD

src/modules/chart/ChartPanel.tsx:810-837 is a window `keydown` listener. One copy is installed per ChartPanel instance.

```
if ((event.key === "Delete" || event.key === "Backspace") && selectedDrawingId) {
  const target = event.target instanceof Element ? event.target : null;
  if (!target ||
      (target !== document.body && !rootRef.current?.contains(target)) ||   // :825
      target.closest(TEXT_ENTRY_SELECTOR) ||
      drawings.find((d) => d.id === selectedDrawingId)?.locked) { return; }
  removeDrawing(panelId, selectedDrawingId);
```

A body-targeted key passes the scope check in every chart instance. Each instance's `selectedDrawingId` is still set, because it is cleared only by Escape, by a delete, or by that chart's own inspector actions (:815, :832, :1210-1248). Nothing clears it when the user moves to another chart or panel.

## Re-run at HEAD

The test is a scratch vitest over a `git archive HEAD` copy of src at `$S/fe`. It reuses the real ChartPanel.test.tsx harness header, and the added cases are saved as `$S/TRIAGEC_UI021.cases.tsx.txt`.

```
cd $S/fe && ./node_modules/.bin/vitest run src/modules/chart/TRIAGEC_UI021.test.tsx   -> 2 failed | 2 passed (4), EXIT=1
R0 composer Backspace {"chartA":1,"chartB":0}
R1 activeElement before key body
R1 after one Delete on body {"chartA":0,"chartB":0}
R2 after one Backspace on body {"chartA":0,"chartB":0}
R3 single chart, key after clicking elsewhere {"chartA":0,"chartB":0}
```

- **R0, the entry's own repro:** Backspace typed in a composer textarea deletes nothing. The stated repro holds.
- **R1, the everyday multi-chart case:** the user selects a line on chart A to inspect it and moves on. Later they select a line on chart B and press Delete. Focus stays on body, as it does on WebKit. **Both lines are deleted.** The drawing store has no undo.
- **R2, the shard's case:** reproduced exactly (0/0 instead of 1/1).
- **R3, single chart:** the user selects a drawing, clicks a non-focusable spot in another panel, then presses Backspace. The drawing is deleted. This follows directly from the same stale selection; it is less clear-cut on its own because of the WebKit trade-off.

## Duplicate search

A register grep for Backspace, selectedDrawingId, delete key, and drawing…delet returns three entries:

- R15-UI-021: this entry.
- R15-CODE-FRONTEND-005: autosave, unrelated.
- R15-UI-022: anchor placement, unrelated.

## Classification

The entry's stated repro (a composer or symbol box) no longer deletes. The residual still reproduces, and it is the entry's own named root cause: "selectedDrawingId persists after focus leaves the chart". The listener is still effectively global through the body exemption, and the fix_shape's "outside containerRef" bail does not hold for body.

That makes this **partial** on R15-UI-021, not a new defect and not a duplicate. Severity stays **medium**. A single keypress aimed at one chart silently destroys user-drawn work in other charts, with no undo. The trigger (select in A, later select in B, press Delete) is ordinary multi-chart use. The workaround is to press Escape before switching charts.

## Root cause

src/modules/chart/ChartPanel.tsx:825 exempts `document.body` from the per-panel scope check for every ChartPanel instance. Each instance's `selectedDrawingId` (the state behind :817) survives the user leaving that chart, because nothing clears it on outside interaction. So one body-targeted Delete/Backspace deletes the selected drawing in every chart that still holds a selection.

## Fix shape

Clear a chart's selection when the user interacts outside it. The listener effect at :810-837 would also register a `pointerdown` listener on `document` that calls `setSelectedDrawingId(null)` when `!rootRef.current?.contains(event.target)`. The body exemption then applies only to the chart the user last clicked in. This keeps the WebKit chip-then-Delete path of 4c9f7516, because the chip is inside the root.

An equivalent alternative is to honour the body case only when this panel is the focused dockview panel (`usePanelContextBus.getState().focusedSource === panelId`).

## Acceptance test

Add a case to src/modules/chart/ChartPanel.test.tsx. Render `<ChartPanel api={{id:'chart-A'}}/>` and `<ChartPanel api={{id:'chart-B'}}/>`, each with one SPY/1d trendline. Click A's "Select trendline" chip, then B's chip (firing pointerDown on each before the click), then `fireEvent.keyDown(document.body,{key:'Delete'})`. Assert that chart-A has 1 drawing and chart-B has 0.

Add a second case: select A's chip, `fireEvent.pointerDown` on an element outside both charts, then Backspace on body. Assert that chart-A still has 1 drawing.

The existing "Delete with nothing focused still deletes" test must stay green.

Live re-proof: the scratch command above must report 4 passed. For R3 the expected result becomes chartA 1.

## Certification-failure count

- The R15-UI-021 note has no 'certification failures so far' clause.
- The batch VERDICTS certified it in batch-6, and it appears in no not_certified list.
- No REFUTATION_AUDIT file has a regression_confirmed or partial verdict for it.

The baseline is 0. This partial adds 1, for a total of **1**.
