# batch-10/W6-chart-notes-blueprint

Candidate `4c6dfe8c` (rc1-cand worktree). Own sidecar `127.0.0.1:52340`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-027 | grep `src/store/keybindings.ts`/`.test.ts`. | Fix comments citing "R15-UI-027 residual" present at 3 sites (grouping by resolved chord not raw, `"mod"` platform resolution, strict-shift handling); `describe("shift strictness (R15-UI-027 residual)", ...)` in the test file. | holds |
| R15-UI-048 | grep `src/modules/chart/ChartPanel.test.tsx`. | `it("a fresh panel (no persisted view) opens on the settings chart default (R15-UI-048)", ...)` present at line 278. | ci_pinned (ChartPanel.test.tsx:278) |
| R15-UI-091 | grep `src/modules/chart/indicators.ts`, `sidecar/services/indicators.py` for R15-UI-091; read the anchor/vwap handling. | Real implementation citing R15-UI-091 directly at 4 sites: sidecar `indicators.py` documents an `anchor` param and accepted `vwap:<anchor>` values (`week`, etc.), frontend `indicators.ts` sends sidecar-shaped tokens (`"ema:9"`, `"vwap:week"`) — the EMA9/21 and week-anchored VWAP combos are now real, requestable indicator tokens, not hard-coded daily ma/volume/rsi/macd for every timeframe. | holds |
| R15-UI-024 | grep `src/modules/notes/NotesToolbar.tsx`/`.test.tsx`. | `describe("NotesToolbar — R15-UI-024", ...)` present; a repro-e fix comment for the `[[` wikilink insertion; a live assertion that `taskList` is active after the Task List toggle. | holds |
| R15-LEAD-026 | `GET /history/ZZQXNOTASYM`. | `{"bars":[],"provider":"none","reason":"unknown_symbol","partial":false,"coverage_start":null}` — exact match to cert (a typed empty-series reason, not `reason: null`). | holds |
| R15-CODE-RESEARCH-004 | `grep -rn "autodetect\|locale" sidecar/services/search`. | 0 hits on "autodetect"; the 3 "locale" hits are legitimate region-bias comments in `brave.py`/`ddg.py`/`searxng.py`, none referencing removed autodetect/metadata scaffolding. | holds |
| R15-DATA-096 | (already re-run live in set-42, same candidate/sidecar — not repeated here.) | See `set-42.md`: cold 1173ms, warm 15ms, byte-identical payload. | holds (see set-42) |

**Set result: 6/7 holds (live/read), 1/7 ci_pinned.**
