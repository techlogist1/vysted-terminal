# set-10 — batch-3/unassigned (rc1-battery-20, round 5-recheck)

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. R15-RESEARCH-010 was certified in round-5
under a pinned-test set (round-5 `battery/set-8.md`, "batch-3/W4-research-depth") — that
set's own instruction was to re-read the pinned test source at the candidate sha rather than
execute pytest (heavy lane owns pytest); followed the same approach here.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-RESEARCH-010 | source read `sidecar/tests/test_research_model_lane.py` + `sidecar/tests/test_llm_openai.py` | `test_rejected_key_401_is_also_an_error_step` (test_research_model_lane.py:290, docstring: "a 401 reaches the stream too") present; `test_openrouter_validate_key_false_when_key_endpoint_401` (test_llm_openai.py:293) and `test_openrouter_validate_key_true_when_key_endpoint_200` (test_llm_openai.py:311) present — all three unmodified in intent, matching round-5 cert exactly | ci_pinned (`sidecar/tests/test_research_model_lane.py::test_rejected_key_401_is_also_an_error_step`, `sidecar/tests/test_llm_openai.py::test_openrouter_validate_key_false_when_key_endpoint_401`, `sidecar/tests/test_llm_openai.py::test_openrouter_validate_key_true_when_key_endpoint_200`) |

Raw: `battery/raw/set-10/R15-RESEARCH-010.txt`.

COVERAGE: 1/1 ids raw; no raw: none.
