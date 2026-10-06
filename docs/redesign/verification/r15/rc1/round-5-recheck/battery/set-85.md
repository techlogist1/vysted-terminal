# batch-30/WriterA-r15-data-030 — rc1-battery-14 (gate round 5-recheck, candidate 949c3c9f)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-050 | In-process `services.research.relevance.row_relevant` against a `ResearchTarget(GE, "GE Aerospace")` for the literal repro title, plus held-back (SM), fresh (CF, MP), still-irrelevant (AI) and control (ON) cases (`raw/set-85/R15-LEAD-050.txt`) | `"GE beats estimates on jet engine demand"` for GE -> `True` (was the regression's `False`). Held-back SM and fresh CF/MP cases also `True`. Still-irrelevant "AI stocks slide on rate fears" for AI stays `False` as the fix_shape requires. Control ON stays `True`. Exact match to the certified table. | holds |

COVERAGE: 1/1 ids raw; no raw: none.
