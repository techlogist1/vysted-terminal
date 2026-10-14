# batch-12/W4-w4 (set-59)

Candidate 4c6dfe8c. Own sidecar :52342, data dir rc1-data-battery-2. Raw output: `raw/set-59/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-RESEARCH-002 | In-process (candidate venv): `services.research.verify._parse_verdict` on the register's 3 original repro lines + all 6 labelled forms from the batch-12 acceptance | All 9 cases classify correctly: every `UNVERIFIED`/`DISAGREE`/`AGREE` variant (bare, `Status:` prefix, `>`/markdown-bold, numbered-list, `Result -`, `Verdict:`) parses to its true label (`unverified`/`disagree`/`agree`) — none of the UNVERIFIED forms fall through to the pre-fix false `agree`. Matches batch-12's cert exactly across original + fresh cases. | holds |

Summary: 1 hold, 0 regressions.
