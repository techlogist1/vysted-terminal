# RC1 gate round 5 — fix round 1 plan (triage: rc1-fix-r1-triage)

Base: 9bc600ece2ce6343a6aa48f130d7620b1466bb98 (candidate worktree verified at this sha). Written 2026-09-27 16:07 IST.
Findings to close: `rc1-drive-panels-layouts:1`. No own sidecar was booted: the record's raw JSON
(`r15/surface/panels-layouts/rc1/round-5/06-sec-insider-aapl.json`, own :52323 and shared :52152 identical)
plus the code below are conclusive, so no reproduction was needed.

## rc1-drive-panels-layouts:1 — REAL (medium)

**Mechanism.** `GET /sec/insider/AAPL` returns 9 filing-level rows (reporter_name "", direction null,
shares/price/value null, transaction_code ""). The sidecar keeps these on purpose since R15-DATA-038:
sec-edgar-mcp 1.0.8 `get_insider_transactions` returns filing-index rows only, and its owner lookup reads
`ownership.owner_name`, an attribute edgartools 5.59.1 `Ownership` does not have (it exposes
`insider_name`). That swallowed `AttributeError` is why reporter_name is always empty. The frontend then
misrenders the gaps in `src/modules/sec/InsiderTradingTable.tsx`:
- the Direction cell (:61-72) is `t.direction === "disposed" ? "text-negative" : "text-positive"`, so a
  null direction renders an empty **green** span, styled as an acquisition. Because the cell renderer returns a
  non-null element, DataTable's `—` null glyph is never used.
- the Reporter column (:38-44) returns `t.reporter_name` (""), which bypasses the null glyph and leaves
  the cell blank. The Code column at :59 already uses `|| null` for the same case.
- nothing on screen says the rows are filing-index entries with no per-trade detail.

This is one defect class, "an absent value rendered as a present one", showing up twice in the same file.

**Fix (writer `insider-table`, sonnet).** In `InsiderTradingTable.tsx`:
1. The Direction cell returns `null` when `t.direction` is null, so the neutral `—` glyph shows. Colour
   applies only to the two real directions.
2. Reporter uses `t.reporter_name || null`.
3. When any shown row is filing-level (`direction === null && shares === null`), the header shows a muted
   caption (testid `insider-filing-level-note`) along the lines of "Filing index only — the SEC feed lists these filings
   without per-trade detail (reporter, direction, shares, price); open the filing for its trades." The
   wording must not claim the filing itself withholds the detail.

No sidecar or type change is needed: `types/sec.ts` already types direction and shares as nullable.

**Acceptance (pinning test).** Add one focused test to `src/modules/sec/InsiderTradingTable.test.tsx`. It
mocks a mixed payload with one filing-level row (reporter_name "", direction null, shares null) plus one
per-trade `acquired` row and one per-trade `disposed` row. It asserts:
- the filing-level row's Direction and Reporter cells render `—`, and no element in that row carries
  `text-positive` or `text-negative`;
- the acquired row keeps `text-positive` and the disposed row keeps `text-negative`;
- `insider-filing-level-note` is present.

A second assertion in the same test re-renders with only per-trade rows and checks that the note is absent.
The existing "colours acquired and disposed differently" test must stay green unchanged.
Gates: `pnpm vitest run src/modules/sec`, `pnpm typecheck`, `pnpm lint`, `pnpm format:check`.

**Files:** `src/modules/sec/InsiderTradingTable.tsx`, `src/modules/sec/InsiderTradingTable.test.tsx`.

## Rejected / deferred

None.

## Issues for the lead (outside this entry; not in the diff)

- **Insider enrichment is not possible through the bundled MCP.** Every sec-edgar-mcp 1.0.8 insider tool
  (`get_insider_transactions`, `get_form4_details`, `analyze_form4_transactions`) reads `owner_name`,
  `owner_title` and `transactions` attributes that edgartools 5.59.1 does not expose. The upstream therefore
  never returns a reporter or a trade. Getting real per-trade rows would mean the sidecar parsing the Form 4
  ownership XML itself (httpx to sec.gov, as `_load_company_tickers` already does) or an upstream bump.
  That is a feature, not this entry's fix.
- `sidecar/services/sec_filings_provider.py:417-430` `_direction_from_code` maps code `X` (exercise of
  an in-the-money derivative) to `disposed`, and an empty code to `acquired`. The empty branch is
  unreachable (the only caller checks that the code is truthy). The Form 4 A/D flag is the authority on
  direction. Today no live row reaches this function, because the upstream sends no codes.
