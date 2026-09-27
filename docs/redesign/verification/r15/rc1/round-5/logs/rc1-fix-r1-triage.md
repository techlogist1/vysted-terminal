# rc1-fix-r1-triage log

- 2026-09-27 16:07 IST: candidate worktree HEAD = 9bc600ece2ce6343a6aa48f130d7620b1466bb98 (OK).
- Read findings/rc1-drive-panels-layouts.json (1 finding) and its evidence 06-sec-insider-aapl.json (9 filing-level rows, all economic fields empty).
- Read InsiderTradingTable.tsx (Direction ternary at :67 makes null green; Reporter at :43 returns "", which bypasses DataTable's null glyph), DataTable null-glyph contract, groupDigits(null) -> "—", types/sec.ts (direction/shares nullable).
- Read sec_filings_provider.py _insider_rows_from_payload (filing-level rows kept on purpose since R15-DATA-038) and the register entry R15-DATA-038.
- Read upstream sec_edgar_mcp/tools/insider.py plus edgartools ownership/forms.py: upstream reads owner_name, which is absent in edgartools 5.59.1 (the attribute there is insider_name), so reporter is always empty upstream. Logged as an issue, not in scope.
- Verdict: real, frontend-only fix, 1 writer (sonnet). No own sidecar booted because the record was conclusive, so there is nothing to stop.
- Wrote fix-r1/PLAN.md.
