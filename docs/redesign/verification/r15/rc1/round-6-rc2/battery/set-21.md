# set-21: batch-6/W2-delegate-runs-runtime

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-014 | in-process OpenAIProvider._repair_tool_args, oneshot stubbed to reply with the tool's JSON schema (full / fenced / prose / placeholder echo) for the 8 tools with no required keys | echo accepted after fix: none of 4 forms for any tool; legit news args {'symbols': ['AAPL']} still accepted | holds |

COVERAGE: 1/1 ids raw (set-21); no raw: none
