# rc1-fix-r1-triage log (gate round 4, fix round 1)

- Candidate worktree HEAD verified 1006c6da694ede5776c3dabbd27b305aeb56b5ad.
- Own sidecar :52331 from candidate source on seed copy rc1-round-4-data-rc1-fix-r1-triage (sleep pid 17157, python 17158); log fix-r1/triage-sidecar.log.
- rc1-scenarios:1 — read agent_runtime.py _dispatch_round/_auto_publish_event/_end_of_turn_notices + transcript rb-brief-local-t1.jsonl: no staged notice for the synthetic __autobrief under ask. REAL -> W1 (opus).
- rc1-datapack:1 — live /fundamentals/SIFY: financial_currency INR labels the INR sizes; agent view '₹4,651 cr'; panels format with financial_currency. REJECTED (evidence/datapack-1-sify.txt).
- rc1-drive-screener:1 — AUTO result 'dispatched', headless read-back 'dispatched_unconfirmed'; frontend auto-applies panel kind. Model narration only. REJECTED.
- rc1-drive-panels-layouts:1 — fetched both 247wallst articles: publisher tickers include/primary NYSE:INFY, bodies discuss the Chainlink–Infosys deal. REJECTED (evidence/panels-layouts-1-news.txt).
- rc1-drive-failure-inducer:1/:2 — reproduced live (evidence/failure-inducer-1-2-repro.txt); _provider_error has no malformed-symbol rule; statement/rating getters lack history's empty-frame probe (probe verified: ZZZZNOTREAL.NS -> YFPricesMissingError, TCS.NS -> None). REAL -> W2 (sonnet).
- rc1-battery-9:1 — deep_research._run_loop returns _loop_failed for heavy AND iter since 9703eee7 (R15-CODE-RESEARCH-003, batch-8) deleted the drifted fallback deliberately. REJECTED.
- rc1-battery-14:1 — /resolve 'KPIT Technologies' ties KPITTECH (current name) with BSOFT (former_names.json 'KPIT Technologies Limited') at 1.0; research prefix 'KPIT' then binds BSOFT. REAL -> W3 (sonnet). Ladder behaviour filed as rc1-fix-r1-triage:1 (low).
- Deferred: none; DECISIONS_FOR_OPERATOR.md untouched.
- PLAN: fix-r1/PLAN.md (prettier-clean).
