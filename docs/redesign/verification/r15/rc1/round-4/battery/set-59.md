# Set 59 — batch-12/W4-research-verdict-parse-source-authority (rc1-battery-20)

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Pure-Python check, no
sidecar/network needed — ran directly against the candidate's sidecar venv.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-RESEARCH-002 | `services.research.verify._parse_verdict('UNVERIFIED - no source confirms the 23% operating margin.')` and the other two proven UNVERIFIED strings + AGREE/DISAGREE controls (candidate venv) | all three UNVERIFIED strings → `('unverified', ...)`; AGREE/DISAGREE controls → `('agree', ...)`/`('disagree', ...)` — the substring-scan bug (which used to return `('agree', ...)` for these) is fixed; the parser now reads the leading verdict token | holds |

COVERAGE: 1/1 ids raw.
