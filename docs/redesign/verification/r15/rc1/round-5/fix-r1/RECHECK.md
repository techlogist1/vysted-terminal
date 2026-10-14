# RC1 gate round 5 — fix round 1 recheck (rc1-fix-r1-recheck, Opus)

Written 2026-09-27 16:33 IST. Candidate worktree at `633f844071d972b337f4c3526d86555c80df0568` (verified with rev-parse).
Own sidecar booted from the candidate source on :52336 with a copy of the seed data. Its sleep pid was 86439, and it has been stopped.
Evidence dir: `fix-r1/recheck/`.

Method: the fix is frontend-only (`src/modules/sec/InsiderTradingTable.tsx`), and GUI is skipped this round. I therefore
fetched live `/sec/insider/<sym>` payloads from my own candidate sidecar and rendered the candidate's
`InsiderTradingTable` on each payload in jsdom. The only mock was the transport: `sidecarGet` returned the live
body. This ran from a `git archive HEAD` copy of the candidate with its node_modules symlinked, so the candidate
worktree was not written. The scratch check is kept as `recheck/render-live.scratch.tsx.txt` and was not committed.
Per-cell output is in `recheck/render-live.json`, and the run log (4 files, 24 tests passed, which includes the
committed pinning tests) is in `recheck/vitest-sec.log`.

| key | repro | observed | verdict |
|---|---|---|---|
| rc1-drive-panels-layouts:1 | Entry repro: `GET :52336/sec/insider/AAPL` (`recheck/insider-AAPL.json`: 9 rows, all filing-level with reporter_name "", direction/shares/price/value null, code ""), rendered in InsiderTradingTable | Every row reads `2026-09-24 · — · — · 4 · — · — · — · — · —`. 0 rows carry `.text-positive`/`.text-negative`, 0 blank cells and 0 console errors. The header note "Filing index only — the SEC feed lists these filings without per-trade detail (reporter, direction, shares, price); open the filing for its trades." is present | **fixed** |
| rc1-drive-panels-layouts:1 (fresh cases) | Symbols the fix was not written against: MSFT (44 rows), NVDA (27), TSLA (1), all live from :52336 and rendered the same way | Same result for all 72 rows: every absent field shows the neutral `—`, nothing is coloured, no cell is blank, and the note is shown | **fixed** |
| rc1-drive-panels-layouts:1 (adjacent) | Per-trade rows with acquired/disposed directions (the existing "colours acquired and disposed differently" test, unchanged) plus a mixed payload (committed pinning test) | acquired stays `text-positive` and disposed stays `text-negative`. The note is absent when every row has per-trade detail. The fix-r1 ci-local run (2x EXIT=0) and the smoke test (EXIT=0) are green at 633f8440 per `INTEGRATION.md` | no regression |

Title claim ("every economic field blank and absent Direction coloured green"): both halves are gone. No field
renders blank, and nothing is coloured unless the row has a real direction. The fix shape holds: null Direction goes
to the neutral glyph, Reporter `""` goes to the glyph, and a filing-level note is shown. The acceptance holds: the glyph
and no colour on filing-level rows, colours kept on real rows, and the note present only when needed.

Notes (outside the entry, not defects of this fix): the upstream still returns no per-trade insider rows
(sec-edgar-mcp 1.0.8 vs edgartools 5.59.1, already in PLAN.md issues). The note's "open the filing" points at the
panel's Filings tab; the insider row itself is not clickable and shows no accession, so the user matches by date.
`/sec/insider/TSLA?form=all` returns 422 by design, because the UI sends no `form` for "All".
