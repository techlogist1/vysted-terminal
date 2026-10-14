# batch-2/W3-research-integrity (rc1-battery-13, gate round 5)

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98. All five repros re-run as in-process
python calls against the candidate's sidecar venv (`services/research/*` are pure
functions, no network, no LLM), mirroring the round's own repro shapes — no live LLM
spend needed for this set.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-RESEARCH-001 | in-process `relevance.gate_news([...], target=BDL)` with an off-entity item (Sterling and Wilson Rs 985 cr, no symbols) plus an on-entity BDL item | off-entity item dropped, on-entity BDL item kept, note=None (nothing generic injected) | holds |
| R15-RESEARCH-034 | in-process `deep._reflect_says_complete(...)` on the three register strings | `"Price action is not covered yet"` -> False; `"COMPLETE"` -> True; `"No gaps remain"` -> True | holds |
| R15-RESEARCH-004 | in-process `verify._split_claims("revenue growth +40.5%\nP/E 67.13953\n-0.4% YoY margin\n40.5% growth again", limit=10)` + `"P/E 34.42\nGross Margin 51.70%"` | figures intact (40.5%, 67.13953, -0.4%, 34.42, 51.70% — none mangled to 5%/4%/13953/42/70%) | holds |
| R15-RESEARCH-003 | in-process `deep._Findings.all_sources()`: round 1 seeds 2 structured sources (price, fundamentals); round 2 appends 2 higher-domain-tier filings | round-1 markers ([price, fundamentals]) unchanged as a prefix after round 2's re-rank-eligible additions (new sources appended after) — append-only, round-1 prefix stable (`round1_prefix_stable: true`) | holds |
| R15-RESEARCH-029 | in-process `citecheck.strip_model_bibliography(md)` on a register-shaped markdown ("-0.4% ([n] 1)", a 7-item "**Merged Sources**" list, a "References:" "[n] N." list) | removed=3 sections/marker-groups; cleaned text has no "[n]" literal, no "Merged Sources", no "References:" | holds |
| R15-RESEARCH-037 | in-process `finance.priority_note([...])` on an UNRANKED list ordered [general, primary(sec.gov), press(reuters.com)] | `"primary record (...): [2]; tier-1 press: [3]."` — exact match to the batch-2 certified evidence string | holds |

Raw: `battery/raw/set-2/probe_set2.py` (the exact probe script run), `probe_set2_output.json`
(full JSON output) + one pointer file per id excerpting its result.

COVERAGE: 6/6 ids raw; no raw: none.
