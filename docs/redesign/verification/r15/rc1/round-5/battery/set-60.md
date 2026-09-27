# Set 60 — batch-12/W8-design-token (regression battery shard 14)

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-010 | live `GET /sec/filings/{accession}?identifier=...` unhinted (no `form_type`), AAPL 10-K `0000320193-21-000105` and fresh MSFT 10-Q `0001564590-22-035087` | AAPL: HTTP 200, sections returned (Business, Risk Factors). MSFT: HTTP 200, `form_type: "10-Q"`, `period_of_report: "2022-09-30"`, `filed_date: "2022-10-25"` — both resolve unhinted (pre-fix this 404'd). | holds |
| R15-RELEASE-007 | `node scripts/audit-design-tokens.mjs` over the candidate `src/`; negative case: a scratch copy of `brief-blocks.tsx` with `gap-1.5 px-[7px] text-[12px]` injected, scanned from the scratch copy only (candidate worktree untouched, read-only per role rules) | Positive: "design-token audit clean (373 files)" (cert: 372 — +1 file since batch, not a regression). Negative: exactly 3 violations reported at the injected line — `gap-1.5` (off-grid step), `px-[7px]` and `text-[12px]` (arbitrary value) — identical to the cert's own negative case. | holds |

COVERAGE: 2/2 ids raw; no raw: none.
