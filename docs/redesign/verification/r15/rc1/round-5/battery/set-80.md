# set-80 — batch-29/W1-opus (rc1-battery-16)

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-RESEARCH-001 | in-process `row_relevant` on 5 cases (ON/AMD/ALL/AI targets) + live GET /news?symbols=AI&region=US on :52356 (33 raw items) + in-process `gate_news(items, target=AI/C3.ai)` fed those live items; source confirms `deep.py:918-925` calls `gate_news` and `deep.py:761` calls `row_relevant` at HEAD | all 5 row_relevant cases match cert exactly (ON/Lockheed→False, ON/ON-Semi→True, AI/C3.ai→True, AMD/AMD→True, ALL/Allstate→True); live /news for AI carries 13 alias-tagged off-entity items (Axis Bank hiring, Rajnath Singh defence summit, Air India 171 crash, etc.); `gate_news` drops exactly those 13 and keeps 20 genuinely on-entity C3.ai/AI-sector items — matches batch-29's cert row `AI (C3.ai) \| fresh \| 20 \| 0 \| 0` | holds |

COVERAGE: 1/1 ids raw; no raw: none.

Note: not re-run as a live paid DEEP research call (gpt-4o-mini via vy.py) to conserve the shared $0.90 hosted-lane spend cap for the scenario lane. The gated mechanism itself was proven end-to-end against real live news data through the real `gate_news`/`row_relevant` functions that `deep.py` now calls, which is the exact code path the fix touched.
