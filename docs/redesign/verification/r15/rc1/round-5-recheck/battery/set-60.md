# set-60 — batch-12/W4-research-verdict-parse (rc1-battery-22, shard 22)

Candidate 949c3c9fd49d61ecadc9813a8321bcdfd81178bd.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-RESEARCH-002 | register's exact `python -c` command against `services.research.verify._parse_verdict` for the 3 cited UNVERIFIED strings | all three now parse as `('unverified', ...)` (were `('agree', ...)` pre-fix) | holds |

Notes: the register entry's own note already records a gate-round-5 refutation
of a broader "class claim" (labelled/bracketed/numbered verdict lines), which
was found to hold and was filed separately as R15-LEAD-060 — that class claim
is out of scope for this entry's own stated repro per gate rule change 1 and
is not re-litigated here. No regression found in this set.

COVERAGE: 15/15 ids raw; no raw: none.
