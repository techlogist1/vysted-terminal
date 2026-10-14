# R15-UI-022 — fresh GUI verify at 1fddb2b

- verifier: Opus 5.5 (close-verify-R15-UI-022), fresh context, no GUI
- sha: 1fddb2b19dd41ae2085a78ef5d02d7e5ee3af056
- inputs: register entry R15-UI-022 (title, repro, fix_shape, note incl. the ace7dd7 still_needs_gui line), DRIVE.md, the 14 captures + raw/ (batch-01/02.json, rig-03/04.log, blob-after-batch02.json, spy-bars-at-anchors.txt), CAPTURES.jsonl, presence.log, `src/modules/chart/ChartPanel.tsx` at the sha.

## Capture admissibility
All 14 PNGs (01-14) hash to a CAPTURES.jsonl row with tool `scripts/rig/rig.py capture`, window_owner "Vysted Terminal". Each has an earlier presence.log line: 01 after 11:53:45Z, 02-07 after 12:11:07Z (pre-batch-01b, idle 905.4), 08-14 after 12:26:47Z (pre-batch-02, idle 908.4). The 11:54Z batch-01 attempt was refused (rig-02 EXIT=3) and produced no capture. Unregistered captures: none. I opened all of 02-11, 13 and 14 myself. 01 and 12 are setup frames (terms dialog, indicator search) and carry no check.

Coordinate frame: the rig click points are window-relative pt. Captures are 2560x1664 px (2 px/pt). The Read display is 2000x1300 (1.5625 display px/pt).

## Code (at sha)
`handleChartClick`: `price = candleSeries.coordinateToPrice(param.point.y)`, `time = param.time` when numeric, otherwise `{time:null, price, logical}`. A Text commit opens `pendingText` (input "Label text", aria-label "Drawing text"). The chip delete button has `disabled={!!drawing.locked}` and `disabled:opacity-40`. Delete/Backspace returns early for a locked selection.

## Part 1 — H-line and trendline land at the clicked y (mid-candle, away from the close)
- **H-line, click (555.5,496) pt, display y 775.** In 04 the line is drawn at display y ~733, which is ~42 px above the click. I traced the gap: 04 is the first frame with the DRAWINGS row, and that row shrank the pane and rescaled the axis. On the pre-drawing axis (02/03: 720 at y760, 700 at y845), display y 775 maps to ~716.5. The read-back is time 2026-06-25, price **716.453**. On the post-resize axis (04: 720 at y719, 700 at y797), 716.45 maps to y ~733, which is exactly where the line is drawn. So the anchor is the clicked price, and the line followed its price when the scale changed. That bar's C is 732.48 and its L is 727.79, so the anchor is not the close.
- **Trendline, clicks (192,512) and (448,358) pt, display (300,800) and (700,559).** In 05 the line runs from (300,798) to (702,560), a pixel-level match. Read-back: 699.06 on 2025-12-31 (C 676.64) and 761.34 on 2026-05-04 (C 714.39). Both points sit at the clicked y, well above the bars, and neither snapped to a close.
- **In-wick H-line, click (525.4,450.2) pt, display (821,703).** In 08 a second line is drawn at display y ~703, crossing the 9 Jun lower wick. The crosshair marks that bar's close (733.34) ~35 px higher. Read-back: **724.14**, between L 718.95 and the body bottom.
- **Ruling: SHOWN.**

## Part 2 — a trendline clicked twice right of the last bar is visible
- **09, plain chart.** Clicks at display x 1207 (right of the last bar's centre, at the pane edge) give a visible short vertical segment at x ~1205, y ~406-469. The crosshair reads "02 Oct '26". Read-back: both points carry time 2026-10-02 (the last bar), with no `logical`. With fitContent and rightOffset 0, this frame shows no empty space right of the last bar. The click resolved to the last bar, so the off-bar branch was not exercised.
- **13/14, Ichimoku on.** The timeline extends past the last candle. In 14 a new trendline from display (1115,467) to (1185,431) is visible, entirely right of the last SPY candle, with the crosshair at "24 Oct '26". Read-back: times 2026-10-09 and 2026-10-24, with no `logical`.
- The register's ace7dd7 note names the remaining discriminating case: pan a plain chart into empty space, click twice, and see the drawing render with `time:null` plus `logical`. That case was **not driven**, because the rig has no drag or wheel input. The Ichimoku case carries real future times, so pre-fix code would also have drawn it.
- **Ruling: NOT DRIVEN (discriminating case).** The user-visible off-bar trendline holds on a future timeline.

## Part 3 — the Text tool asks for a label; "gui-check" shown, not "label"
- In 06, after the Text-tool click, an inline form at the top-left shows an input with placeholder "Label text" and a caret, plus an **Add** button. Two chips, no Text drawing yet.
- In 07, after typing "gui-check" and pressing Return, **gui-check** is drawn on the chart at ~(397,459) (click display ~(391,469)). The form is gone, a third chip "Text" appears, and "label" is nowhere on the chart.
- Read-back: `kindOptions {"text": "gui-check", "fontSize": 12}`.
- **Ruling: SHOWN.**

## Part 4 — Lock: row delete disabled; a click on the drawing leaves it
- In 10, after clicking the first H-Line chip's lock at (82,816) pt, its icon is a closed padlock (the others stay open) and its × is dimmed. The dimming matches the code's `disabled` plus `disabled:opacity-40`.
- In 11, after × at (103.7,816), a canvas click at (192,469) pt (display (300,733), directly on the locked line), a chip select and Delete, the locked line is still drawn at y ~733. There are still 5 chips and "Clear drawings (5)". Read-back: `locked: true`, price 716.453 unchanged, nothing removed.
- No selected-chip highlight is visible, so the Delete leg shows only that nothing was deleted. Not required by the check.
- **Ruling: SHOWN.**

## Findings
The driver filed none. The evidence shows no defect. The 42 px offset of the first H-line in 04 against its click is fully explained by the DRAWINGS-row resize (the stored price equals the clicked y on the pre-resize axis), so it is not a defect.

## Verdict: PARTIAL
Parts 1, 3 and 4 are visible in registered captures and agree with the isolated autosave read-back. Part 2 is visible only on an Ichimoku future timeline. The register's named discriminating case was not driven: a panned plain chart, with points reading `time:null` plus `logical`. It needs a pan input the rig lacks.
