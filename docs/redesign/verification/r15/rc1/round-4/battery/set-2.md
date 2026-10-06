# batch-2/W3-research-integrity (rc1-battery-24)

Candidate: 1006c6da694ede5776c3dabbd27b305aeb56b5ad. All six repros re-run as in-process
python calls against the candidate's sidecar venv (services/research/* are documented
"pure functions, no network, no LLM — fully unit-testable"), using the register's exact
repro strings/shapes — no live LLM spend needed for this set.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-RESEARCH-001 | in-process `relevance.gate_news([...], target=BDL)` with the exact offending item (Sterling and Wilson Rs 985 cr, symbols:[]) plus an on-entity BDL item | off-entity item dropped, on-entity BDL item kept, note=None (nothing "generic" injected) | holds |
| R15-RESEARCH-034 | in-process `deep._reflect_says_complete(...)` on the three register strings | `"Price action is not covered yet"` -> False; `"COMPLETE"` -> True; `"no gaps"` -> True (all match certified) | holds |
| R15-RESEARCH-004 | in-process `verify._split_claims("revenue growth +40.5%\nP/E 67.13953\n-0.4% YoY margin\n40.5% growth again")` + `"P/E 34.42\nGross Margin 51.70%"`; grep of the cross-check summary line | figures intact (40.5%, 67.13953, -0.4%, 34.42, 51.70% — none mangled to 5%/4%/13953/42/70%); summary line now separates agreed/unverified/disagreements (verify.py:521,540,544) instead of lumping unverified into "verified" | holds |
| R15-RESEARCH-003 | in-process `deep._Findings.all_sources()`: round 1 seeds 3 sources (price [2], fundamentals [3]); round 2 appends 5 higher-domain-tier filings | markers [2]/[3] for price/fundamentals unchanged after round 2's re-rank-eligible additions (new sources numbered [4]-[8]) — append-only, round-1 prefix stable | holds |
| R15-RESEARCH-029 | in-process `citecheck.strip_model_bibliography(md)` on a register-shaped markdown ("-0.4% ([n] 1)", a 7-item "**Merged Sources**" list, a "References:" "[n] N." list) | removed=3 sections/marker-groups; cleaned text has no "[n]" literal, no "Merged Sources", no "References:" | holds |
| R15-RESEARCH-037 | in-process `finance.priority_note([...])` on an UNRANKED list ordered [general, primary(sec.gov), press(reuters.com)] | `"primary record (...): [2]; tier-1 press: [3]."` — exact match to batch-2's certified evidence string | holds |

COVERAGE: 6/6 ids raw; no raw: none.
