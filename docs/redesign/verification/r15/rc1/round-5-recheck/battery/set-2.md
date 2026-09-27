# batch-2/W3-research-integrity — rc1-battery-11 (shard 11)

Candidate sha `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. Method: fresh in-process
Python calls against `sidecar/.venv` on the candidate worktree, importing and
calling the actual fixed functions with sample input matching each entry's own
stated repro figures/text (deterministic function-level probes of the exact
code path each fix touches; no live LLM call needed since these are pure-logic
fixes). Raw output: `battery/raw/set-2/<id>.txt`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-RESEARCH-034 | `_reflect_says_complete('Price action is not covered yet')` | `False` (was `True`); `'COMPLETE'`→`True`, `'No gaps remain'`→`True` | holds |
| R15-RESEARCH-004 | `_split_claims` over lines with leading `+40.5%`, `-0.4%`, `1. 67.13953`, `* 51.70%` | all four figures survive intact (`40.5%`, `-0.4%`, `67.13953`, `51.70%`); no mangled `5%`/`13953` remnants | holds |
| R15-RESEARCH-003 | `_Findings.all_sources()` numbered after round 1 (1 general source), then round 2 adds a primary-tier (bseindia.com) source | round-1 source keeps position `[1]` after round 2; new primary source appended at `[2]`, never re-ranked ahead of the existing marker | holds |
| R15-RESEARCH-029 | `strip_model_bibliography` + `strip_invalid_markers` over synthetic markdown with `**Merged Sources**`, `References:`, `[n] 1`/`[n] 7 ([n] 9)` literals and an out-of-range `[99]` | all bibliography headings + `[n]`-literals removed; valid `[1]` kept; out-of-range `[99]` stripped | holds |
| R15-RESEARCH-037 | `priority_note` over an UNRANKED `[general, primary, press]` list | note correctly names `[2]` primary and `[3]` press — matches each source's actual (unranked) position, not a re-ranked one | holds |

COVERAGE: 5/5 ids raw; no raw: none.
