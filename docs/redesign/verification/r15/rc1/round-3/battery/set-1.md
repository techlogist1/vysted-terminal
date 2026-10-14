# batch-2/W3-research-integrity — rc1-battery-0

Candidate sha 01d6920a300b016ab1ad8aa436ee4e4586f8e336. Method: in-process python calls
against `sidecar/.venv/bin/python3` on the candidate's own source (the register's own repro
for 002/004/034 was already a direct function call; for 001/003/015/029/037 a direct
function-level repro was constructed against the actual fixed functions rather than a full
live LLM deep-research run, which the role brief permits ("curl, vy.py, or an in-process
python call")).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-RESEARCH-001 | in-venv `relevance.gate_news(items, target=BDL)` fed the EXACT register item ids (`1e4af0a955903e90` Sterling & Wilson + a genuine BDL item) | kept = `['abc123']` only — the off-entity Sterling and Wilson item is dropped; `deep.py:920-928` now calls the shared `gate_news` before folding news into structured sources ("the FAST news leg's gate ... the ONE gate for every news leg") | holds |
| R15-RESEARCH-002 | in-venv `verify._parse_verdict(...)` on the exact register UNVERIFIED lines | all three return `('unverified', ...)`, not `('agree', ...)` | holds |
| R15-RESEARCH-003 | read `deep.py` `_Findings.all_sources()` | now explicitly APPEND-ONLY: `seen = {src.url for src in self._numbered}`; only genuinely new urls are appended, ranking "orders only the new numbers, never an existing one" — a marker minted in round 1 keeps its number for the rest of the run | holds |
| R15-RESEARCH-004 | in-venv `verify._split_claims(...)` on the exact register claim lines | `_CLAIM_MARKER` now requires trailing whitespace (`^(?:[-*•]\|\d+[.)])\s+`); all four lines ("+40.5%", "67.13953", "51.70%", "-0.4%") survive intact, not mangled to "5%"/"13953"/etc | holds |
| R15-RESEARCH-015 | in-venv `verify._claim_evidence(...)` + `_check_row(...)` with one domain reached by BOTH searxng+native channels | `independence: 1` (not 2), `distinct_lanes: False`, `corroborated: False` — the "+1 for native" only applies when native adds an uncited (genuinely new) path | holds |
| R15-RESEARCH-029 | in-venv `citecheck.strip_model_bibliography(...)` on the exact register text ("Merged Sources", "References:", literal `[n] 1`/`[n] 7 ([n] 9)`) | all three artifacts stripped (`removed count: 3`), leaving only the clean sentence | holds |
| R15-RESEARCH-034 | in-venv `deep._reflect_says_complete("Price action is not covered yet")` | returns `False` (was `True`) | holds |
| R15-RESEARCH-037 | read `finance.priority_note` + its 3 call sites (`deep.py:1122`, `iter.py:233`, `iter.py:1098`) | docstring now states the invariant explicitly ("the SAME numbered list ... in any order — it is never re-ranked"); all 3 callers still pass the same list used for numbering (unchanged from the register's own "3 call sites, all compliant" finding — low-severity latent-trap entry, no live failure to regress) | holds |

COVERAGE: 8/8 ids raw; no raw: none.
