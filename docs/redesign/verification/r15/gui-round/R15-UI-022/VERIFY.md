# R15-UI-022 — fresh GUI verify at ace7dd768c3b809b0e72b20b20cfc94eea2368bd

Verifier: Opus 5.5 (claude-opus-5-5), fresh context, label gui-verify-R15-UI-022. No GUI, no app launch.
Inputs: register entry, DRIVE.md (claims only), captures + raw/ in this dir, CAPTURES.jsonl, presence.log, code at ace7dd7.

## Registration and presence
All 16 PNGs (ace7dd7-01 … ace7dd7-16) hash-match a CAPTURES.jsonl row with tool `scripts/rig/rig.py capture`,
window_owner "Vysted Terminal". Each sits after a presence.log line for R15-UI-022 ace7dd7 (pre-capture-01
02:49:47Z; pre-batch-A 02:50:28Z idle 1179; pre-batch-B 03:05:57Z idle 918; pre-batch-C 03:21:39Z idle 927;
pre-batch-D 03:37:31Z idle 928). Unregistered captures: none.

## Code at ace7dd7 (src/modules/chart/ChartPanel.tsx)
`handleChartClick`: price = `candleSeries.coordinateToPrice(param.point.y)`; time = `param.time` when numeric;
`{time:null, price, logical}` only when `param.time` is absent. Text tool opens `pendingText` instead of
committing. Delete chip `disabled={!!drawing.locked}`; Delete/Backspace refuses a locked selection.
The pre-fix code (e81c9e7^1) also took `time` from `param.time`; it differed by taking the price from the bar
close when a bar existed and had no `logical` fallback.

## Per part

| # | Check (register note) | Evidence | What it shows | Ruling |
|---|---|---|---|---|
| 1 | Trendline / H-line clicked mid-candle render at the clicked y | 06, 07; raw/ace7dd7-blob-after-batchB.json; raw/ace7dd7-spy-bars-at-anchors.txt | 06: H-line at ~716 (axis 720@719, 700@797) crossing the late-June lower wick, not the bodies. Blob: H-line 2026-06-26 @ 716.453 vs that bar's close 727.18 (L 714.81). 07: trendline drawn in empty space above the candles; blob points 699.06 / 761.34 vs bar closes 676.64 / 714.39 (highs 682.03 / 718.48). Pre-fix code would have snapped all three to the closes. | HOLDS |
| 2 | A click right of the last bar places a visible drawing | 11, 14; raw/ace7dd7-blob-after-batchD.json | 14: a short trendline (display ~1113,468 → 1185,430) right of the last SPY candle (~x 1075), crosshair "25 Oct '26". But it was drawn only after Ichimoku extended the time scale 26 bars into the future; blob points carry `time` 1791604800 / 1792900800 and **no `logical`**. So `param.time` was defined, the `{time:null, logical}` branch (the actual defect path: plain chart, empty space past the last bar) was never hit. The pre-fix code also used `param.time` and a coordinate price where no candle exists, so this capture does not tell fixed from unfixed. | NOT SHOWN (not discriminating) |
| 3 | Text tool asks for a label and shows the typed text, not "label" | 12, 13; raw/ace7dd7-blob-after-batchC.json | 12: inline "Label text" input + Add button after the Text-tool click, no drawing yet. 13: "gui-check" drawn at the clicked spot, form gone, chips H-Line/Trend/Text; no "label" anywhere. Blob kindOptions {"text":"gui-check"}. | HOLDS |
| 4 | Locked drawing: row delete disabled, drawing survives a click on it | 15, 16; raw/ace7dd7-batch-D.json; blob-after-batchD | 15: H-Line chip shows a closed padlock, its × dimmed (others open/normal). 16: after × click, canvas click on the line and chip-select + Backspace, the H-line is still at ~716 and 4 chips remain. Blob: H-line `locked: true`, same anchor, 4 drawings. (Backspace leg only proves nothing was deleted.) | HOLDS |

## Verdict: still_needs_gui
Checks 1, 3 and 4 are visible in registered captures and read back from the isolated autosave blob.
Remaining: check 2 on the null-time path — on a chart with no future timeline (no Ichimoku/whitespace),
pan/scroll into the empty space right of the last bar, click a trendline twice there, and confirm the
drawing renders and its stored points carry `time: null` with a `logical` index. The rig had no drag/scroll
to pan, and the fitContent view (rightOffset 0) leaves no empty space to click.
