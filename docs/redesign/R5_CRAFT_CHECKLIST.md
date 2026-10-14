# R5 — Binary Craft Checklist (the acceptance gate)

> This is the gate, **not** a reviewer's "cohesive 4/5" vibe score (which shares the builder's blind spot).
> Each item is **PASS only with a real-app screenshot** (Quartz / tauri-mcp) showing populated state — and
> the operator's eye is the final arbiter. A Claude reviewer checks **these binary items only**.

**Result of the R5 verification run (live, branch `004-r4-experience-rebuild`, AAPL loaded):**

| #   | Surface              | Binary criteria (all must hold)                                                                                                                                                                                                                    | Result                 | Proof shot                                                   |
| --- | -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- | ------------------------------------------------------------ |
| 1   | Equity overview      | (a) no snake_case · (b) every figure unit+sign formatted (`$4.51T`, `$101.09B`, never bare) · (c) period column headers (2025-09-30…×5) · (d) right-aligned tabular numerics · (e) grouped sections · (f) graceful `—` · (g) on shared `DataTable` | **PASS**               | `r5/r5-02-equity-aapl.png`, `r5/r5-06-equity-statements.png` |
| 2   | Notes                | visible toolbar H1/H2/H3 · bold · italic · bullet · numbered · code · blockquote · link · `[[wikilink]]`, live markdown render; MD/PNG/PDF export preserved (20/20 tests)                                                                          | **PASS**               | `r5/r5-05-notes.png`                                         |
| 3   | ⌘K palette           | (a) ellipsis truncation **inside** rows, never hard-clips · (b) visible group headers (Suggested/Agents/Actions/Panels) · (c) empty state = curated Suggested, not an agent dump · (d) "notes" still surfaces Notes                                | **PASS**               | `r5/r5-03-cmdk-palette.png`                                  |
| 4   | Composer             | input + send one balanced unit; mode glyph in reserved `pl-11` gutter never overlaps the placeholder                                                                                                                                               | **PASS**               | `r5/r5-05-notes.png` (composer, bottom-left)                 |
| 5   | Left dock            | empty state fills the column (identity → TRY THIS → distributed chips), no dead void; dock 310px, chart fraction 0.60                                                                                                                              | **PASS**               | `r5/r5-07-cockpit-overview.png`                              |
| 6   | One scale everywhere | scale enumerated (PRODUCT_DESIGN_DECISIONS §16); grep proves **zero** `text-[…]` / `rounded-[…]` / off-grid spacing in every changed file; the shared `cn` font-size bug fixed                                                                     | **PASS** (code grep)   | n/a — grep gate (see report)                                 |
| 7   | Keychain             | after one "Always Allow", key access → rebuild → key access does **not** re-prompt; secrets keychain-only                                                                                                                                          | **NEEDS-MANUAL-CHECK** | `docs/redesign/KEYCHAIN_DEV_SIGNING.md` (operator-attended)  |

## Notes on the run

- A defect was caught **only because the gate is binary** (not a vibe score): the income/balance/cash-flow
  statements first rendered the provider's raw snake_case keys (`free_cash_flow`, `repurchase_of_common_equity`).
  Fixed with `humanizeLineLabel`; re-verified live → **0 snake_case visible**.
- The biggest systemic find — the shared `cn()` silently dropping custom font sizes (tailwind-merge
  mis-classification) — was surfaced by the data-panels teammate and fixed in `src/lib/utils.ts`; it also
  made the failing `EmptyState` tier test pass. This very likely defeated the type scale across ~90 files in
  prior passes.
- #7 cannot be screenshot-proven (it needs the operator's one-time self-signed cert + an "Always Allow"
  click + a rebuild). The fix is shipped and the runbook is exact; honestly reported as NEEDS-MANUAL-CHECK.

## Pass procedure (as run)

1. Killed stale state, rebuilt-checked sidecars (fresh, no Python changed), relaunched `tauri dev` via the
   rig on the webpack path; confirmed render; loaded AAPL.
2. Captured each surface populated, dark, 2560×1664 via the Quartz path (`/tmp/rigcap.py`) into
   `docs/redesign/verification/r5/`.
3. Assembled `docs/redesign/verification/COMPARISON_R5.html` (before vs after vs reference).
