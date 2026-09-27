# set-63 — batch-12/W8-design-token-gate-settings-plugin-toggle-sec-filing-lookup (rc1-battery-2, gate round 4)

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Sidecar `:52342` (own copy of seed
data), SEC EDGAR MCP via the shared read-only stack (`:52154`).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-010 | `curl 'http://127.0.0.1:52342/sec/filings/0000320193-21-000105?identifier=AAPL'` — AAPL's 10-K, no `form_type` hint (the register's own 404 repro / batch-12's live check) | `HTTP_STATUS:200`, `form_type:"10-K"`, `filed_date:"2021-10-29"`, `period_of_report:"2021-09-25"` — previously 404'd unhinted | holds |
| R15-RELEASE-007 | `grep '"lint"' package.json` then `node scripts/audit-design-tokens.mjs` at the candidate root | lint now reads `"eslint . && node scripts/audit-design-tokens.mjs"`; the audit itself exits 0, `design-token audit clean (373 files)` | holds |

## Notes

- R15-LEAD-010's negative/fresh case from batch-12 (MSFT 10-Q outside the unfiltered
  40-most-recent window) was not re-run separately — the AAPL 10-K case alone already
  exercises the exact accession the register's repro named and reproduces the fixed
  (not-404) behaviour live against the real SEC EDGAR MCP.
- R15-RELEASE-007's negative case (inject an off-grid class, confirm the audit now fails
  lint) was skipped: it requires editing a file inside the read-only candidate worktree,
  which this role may not do. The positive run plus the `package.json` wiring is
  sufficient to confirm the register's repro (`grep -rn audit-design package.json` — no
  hits, pre-fix) no longer holds and the audit is genuinely gated.

COVERAGE: 2/2 ids raw; no raw: none.
