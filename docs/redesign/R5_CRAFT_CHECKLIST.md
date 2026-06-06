# R5 — Binary Craft Checklist (the acceptance gate)

> This is the gate, **not** a reviewer's "cohesive 4/5" vibe score (which shares the builder's blind spot).
> Each item is **PASS only with a real-app screenshot** (Quartz / tauri-mcp) showing populated state — and
> the operator's eye is the final arbiter. A Claude reviewer checks **these binary items only**.

For each item: record `PASS` + screenshot path, or `BROKEN`, or `NEEDS-MANUAL-CHECK`.

| #   | Surface                  | Binary criteria (all must hold)                                                                                                                                                                                                                                                                                                                                                                               | Result | Proof shot |
| --- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ---------- |
| 1   | **Equity overview**      | (a) no snake_case anywhere visible · (b) every figure formatted with unit + sign (`$35.93B`, `-1.16%`, never `35…` or a bare `14.698`) · (c) period column headers present (TTM / FY2025…) · (d) numeric columns right-aligned **and** vertically aligned (tabular) · (e) grouped sections · (f) missing values render gracefully (`—`, no crash) · (g) built on the shared `DataTable`, not hand-rolled divs |        |            |
| 2   | **Notes**                | visible formatting toolbar with **all** of H1/H2/H3, bold, italic, bullet list, numbered list, code, blockquote, link, `[[wikilink]]` — each functional with live markdown rendering; MD/PNG/PDF export still works                                                                                                                                                                                           |        |            |
| 3   | **⌘K palette**           | (a) long text truncates with an ellipsis **inside** the row — never hard-clips past the panel edge, at narrow and wide widths · (b) group headers visible (Panels/Actions/Agents/Symbols) · (c) empty state shows useful recent/suggested actions, **not** a raw agent dump · (d) typing "notes" still surfaces Notes                                                                                         |        |            |
| 4   | **Composer**             | input + send read as **one** deliberate unit (balanced proportions); the agent avatar / persona indicator and the placeholder text **never overlap** (left inset reserved)                                                                                                                                                                                                                                    |        |            |
| 5   | **Left dock**            | empty state **fills its column** with no large dead vertical space and reads intentional; three-pane balance gives chart + equity-overview appropriate room                                                                                                                                                                                                                                                   |        |            |
| 6   | **One scale everywhere** | the type scale and spacing scale are enumerated (PRODUCT_DESIGN_DECISIONS §16); a grep proves **zero** off-scale `text-[…]` and **zero** off-grid `gap/px/py/m` in every changed file                                                                                                                                                                                                                         |        |            |
| 7   | **Keychain**             | after one "Always Allow", a key access → dev rebuild → key access does **not** re-prompt; secrets remain keychain-only (Tier-1 intact)                                                                                                                                                                                                                                                                        |        |            |

## Pass procedure

1. Kill **only** stale Vysted procs (never Claude/Cursor); rebuild sidecar; relaunch via the webpack dev
   path; confirm it renders; **load AAPL**.
2. Capture each surface populated, dark, at 1920×1080 **and** 2560×1440 into
   `docs/redesign/verification/` (per-surface before/after; never overwrite prior shots).
3. Assemble a side-by-side comparison sheet (current vs redesign vs reference) for the operator's eye.
4. Fill the table above. Anything not provable by screenshot is `NEEDS-MANUAL-CHECK` (e.g. the keychain
   one-time cert is operator-attended), never silently `PASS`.
