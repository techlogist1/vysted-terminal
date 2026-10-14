# R15-LEAD-145 (gui-close-3) — fresh GUI verifier

## Attempt 1 @ f163d858 — no verifier ruling

The drive at f163d858 was blocked_env: the screen was locked and no capture was taken (DRIVE.md, first section). There was nothing to verify, so this section only records that.

---

# Attempt 2 — 2026-10-04, at 9f6bd4be5837aa982f2fb0828899856e275503cc

- verifier: close-verify-R15-LEAD-145 (Opus 5.5, fresh context). Inputs: the check, the register entry, DRIVE.md, the captures and raw files in this directory, CAPTURES.jsonl, presence.log, and the code at the sha. I did not use the GUI or launch the app.
- code read at the sha: 67531aef (src/store/portfolios.ts `seedDefaultPortfolio` records each row `validateHolding` rejects as `importSkipped` with `reason = check.message`; `dismissImportNotice`; src/lib/workspace.ts persists and restores `importSkipped` / `importNoticeDismissed` in the portfolios slice; src/modules/portfolio/PortfolioPanel.tsx adds the selector suffix ` · N not imported`, a role=status notice with Dismiss, and the summary caveat `excludes N rows not imported`, which does not depend on the dismissed flag). 0012eca6 and a9427162 change only the agent context and preamble. No chat turn was sent, so they are not on screen. `validateHolding` returns on the first failure, and it checks quantity before cost.

## Capture registration
All 45 files `9f6bd4b-01..45` have a sha256 row in CAPTURES.jsonl with tool `scripts/rig/rig.py capture` and window_owner `Vysted Terminal`. `-11` has the same sha256 as `-09` (43fb42ae…). `-38`..`-45` have the same sha256 as `-37` (9c91681d…). Each is covered by that row. A presence.log line comes before every batch: pre-batch-b01 14:44:07Z (captures from 14:44:08Z), pre-batch-b02 15:31:25Z (from 15:31:27Z), pre-batch-b03 15:47:37Z (from 15:47:38Z). Nothing is unregistered. I opened each capture with Read. The walk captures 13-24 were also read as symbol/qty crops from the same files (scratchpad only). A pixel diff showed that 30 matches 28 and 32-34 match 31/35 except for a caret or focus ring.

## Per part

### (1) Portfolio lists the 81 importable rows
- Evidence: 08, 12, 13-24 (table walk), 25/26/27 (wide table T066-T080 with avg cost), 37 (AAPL with an EOD quote).
- What it shows: the selector reads `Portfolio · 81 · 3 not imported`. The table holds AAPL 10 and T001..T080. Each quantity is n+1, from T001 2 to T080 81, and the walk windows overlap with no gaps: 13/14 AAPL-T012, 15 T007-T019, 16 T015-T027, 17 T023-T035, 18 T031-T043, 19 T039-T051, 20 T047-T059, 21 T055-T067, 22 T063-T075, 23/24 T068-T080. In 24, focus leaves the table to the composer after T080, so T080 is the last row. No AAPL 1e15 or AAPL -50 row appears. Avg cost is shown for T066..T080 (₹660.00..₹800.00 = 10n, equal to before.txt). AAPL's cost can be derived from 37: MV $3,336.90 and P&L +$1,836.90 give a cost of $1,500 for 10 shares, which is 150 and equal to before.txt. Cost bases for T001-T065 never appear on screen.
- Ruling: shown for all 81 symbols and quantities, and for the cost of AAPL and T066-T080. **Not shown on screen: cost bases for T001-T065.** after-http.txt checks only the legacy ledger (84 rows, 3 flagged present). No difference from before.txt appears in any capture.

### (2) Notice names every flagged row with its reason
- Evidence: 08 (also 09, 10; partly 01, 03-07).
- What it shows: "3 holdings from your previous version could not be imported." / "Totals, P&L and weights exclude these rows. Short lots (negative quantity) and quantities above 1e12 are not supported in this version; the rows are kept in the old ledger." / `AAPL 1,000,000,000,000,000 @ 0.00000001 — Quantity is too large` / `AAPL -50 @ -10 — Quantity must be greater than 0` / `AAPL 1,000,000,000,000,000 @ 0.00000001 — Quantity is too large`, plus "× Dismiss". These are the three before.txt flags: ids 2, 3 and 4, with symbol, quantity and cost exact.
- Ruling: **passed**. Every flagged row is named with a reason. The reason for id 3 leaves out the negative cost (finding 1).

### (3) Count/summary caveat persists after dismiss
- Evidence: 10 (before dismiss: notice plus the amber caveat), 09/11 (focus on Dismiss), 12 (after Return: notice gone).
- What it shows: before dismiss, the selector reads `· 3 not imported` and the summary ends `· excludes 3 rows not imported`. After dismiss (12), the notice is gone and both caveats are unchanged. They are still present in 13-27.
- Ruling: **passed**.

### (4) Totals do not present themselves as the whole 0.8.0 book
- Evidence: 08/12 (no quotes), 37 (one EOD quote, after relaunch).
- Caveat text next to the totals: without quotes, "Market value: — (no live quotes) · Total P&L: — · Concentration: —% · 81 without a live quote · excludes 3 rows not imported". With a quote, "Market value: $3,336.90 · Total P&L: +$1,836.90 (+122.46%) · Concentration: 100.0% · 80 without a live quote · as of Oct 3, 2026 at 1:30 AM · excludes 3 rows not imported". The caveat is amber and sits on the same summary line. Before dismiss, the notice also said that totals, P&L and weights exclude these rows.
- Ruling: **passed**. (Observation, outside LEAD-145: Concentration 100.0% and the RISK block are computed over the single quoted holding. "80 without a live quote" sits next to them on the same line, which is pre-existing behaviour and not filed here.)

### (5) Relaunch: no re-import, notice stays dismissed, caveat persists
- Evidence: 28 (first screen of launch 2, pid 63860, same data dir per raw/9f6bd4b-launch-2.txt and sidecar-args-2.txt), also 29-37.
- What it shows: no import notice. The selector reads `Portfolio · 81 · 3 not imported` and the summary still reads `excludes 3 rows not imported`. The table is unchanged (AAPL 10, T001 2 …). The code at the sha resets the dismissed flag to false on a re-import (`setImportRecord(skipped, false)`), so a re-run would have shown the notice again. Its absence, with 81 rows and no duplicates, is consistent with no re-import.
- Ruling: **passed**.

### (6) Settings -> Advanced -> Layouts lists 'phase9test'
- Evidence: 27 (b02 reached Advanced; the Layouts heading, "Save current layout as…" and the "Start with" card are visible, and the saved-layout list is below the fold). 29-35: b03 clicks missed (Sections menu never opened again).
- Ruling: **not driven**. No capture shows 'phase9test'.

## Driver findings
1. "The import notice gives only the first validation failure for AAPL -50 @ -10 and leaves out the negative cost": **confirmed** in 08, and in code (`validateHolding` returns at `quantity <= 0` before it checks cost). Severity low (cosmetic/wording). The row is named with its quantity and cost (-10 is visible), it is excluded, and the totals carry the caveat.
2. "A driver mis-click reordered the provider fallback order (isolated run copy only; this is not a product defect)": **confirmed** as a driver side effect. 28/29 show Anthropic, OpenAI, Gemini; 31-35 show Anthropic, Gemini, OpenAI. This is not a product defect, and it happened only in the isolated run-copy profile.

No further LEAD-145 defect is visible in the captures.

## Verdict
**partial**. Everything that was driven holds: the import ran at boot, 81 rows match before.txt in symbol and quantity, the notice names all 3 flagged rows with reasons, and the count and summary caveats survive dismiss and relaunch with no re-import. Not driven: (6) Layouts listing 'phase9test', and on-screen cost bases for T001-T065.
