# Set: lows-P1/portfolio (set-67) — rc1-battery-10, candidate ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-078 | test-pin check + validator source | validateHolding refuses blank cost, >1e12 qty, names field for '1,000', negative cost; tests PortfolioPanel.test.tsx:501/508/515, portfolios.test.ts:76; agent path guarded host-actions.ts:754 + DATA-088 test | ci_pinned |
| R15-CODE-PLATFORM-050 | grep for the id:i adapter / index re-join | no `id: i` / holdings[i]; rows map `holding: row.position` (PortfolioPanel.tsx:547) | holds |
| R15-CODE-PLATFORM-051 | grep text-positive in PortfolioPanel.tsx | only the pnlTone helper (line 87); cell uses pnlTone(r.pnl) at 622 | holds |
| R15-CODE-PLATFORM-052 | grep 'Patch an existing holding' | gone (exit 1); doc now 'Replace an existing holding's fields (not a partial merge)' | holds |
| R15-UI-079 | test-pin check + source | FORMULA_TRIGGER prefix on non-number cells (csv.ts); tests csv.test.ts:31,42 | ci_pinned |
