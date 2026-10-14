# set-64 — batch-13/W2-research-007-public-suffix-list-registrable-domain-check

Candidate: 1006c6da694ede5776c3dabbd27b305aeb56b5ad. In-process (candidate's own `sidecar/.venv`),
`services.research.finance.domain_tier` / `rank_sources` called directly — no sidecar boot needed
for this pure-function entry.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-RESEARCH-007 | `domain_tier()` on the register's exact URLs (medium.com/investor-diary, wordpress.com/ir path, reuters.com) + fresh cases (reuters `/markets/investors-rush`, a genuine `ir.somecompany.com` subdomain, and `investors.com` — a host that IS its own registrable domain) | medium.com/investor-diary → GENERAL(3); wordpress /ir path → GENERAL(3); reuters (both paths) → PRESS(2); `ir.somecompany.com` → PRIMARY(1) (still works — the fix didn't break legitimate IR subdomains); `investors.com` (news site, not a subdomain) → GENERAL(3), confirming the "host that IS its own registrable domain never qualifies" guard from the docstring; `rank_sources([Medium, Reuters])` → `['Reuters piece', 'Medium piece']` (Reuters now ranks first) | holds |

COVERAGE: 1/1 ids raw; no raw: none.
