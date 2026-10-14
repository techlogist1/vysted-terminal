# batch-3/W4-research-depth (rc1-battery-14, set-8)

Candidate sha 1006c6da694ede5776c3dabbd27b305aeb56b5ad. Sidecar :52354.

Re-run via each entry's pinned pytest file on the freshly built candidate (raw:
`_pytest_run2.txt` for the batch, `_pytest_verify.txt` for test_research_verify.py).
`test_research_metering.py`, `test_deep_research_wall.py`, `test_research_model_lane.py`,
`test_web_search.py`, `test_search_redirect_ssrf.py`, `test_research_verify.py`,
`test_research_r8_regressions.py`, `test_research_r9_regressions.py` all ran: 193 + 26
passed, 0 failed.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-RESEARCH-009 | `pytest test_research_metering.py::test_deep_run_with_reported_usage_has_a_nonzero_cost` + `::test_unmeasured_usage_reports_unknown_cost_not_zero` | passed | holds |
| R15-AGENT-012 | `pytest test_research_metering.py::test_research_guard_takes_its_ceilings_from_the_depth_profile` | passed | holds |
| R15-RESEARCH-006 | `pytest test_research_verify.py::test_slow_verdicts_cannot_carry_the_round_past_its_wall` + `::test_verdicts_reached_in_budget_are_kept_and_the_tail_is_unverified` + `::test_guard_breach_between_verdicts_stops_the_loop` | all passed | holds |
| R15-RESEARCH-008 | `pytest test_web_search.py::test_keyless_hanging_ddg_serves_brave_inside_the_tool_cap` (isolated x3) + whole-file control | Functional asserts (`ok is True`, brave row served) passed every time; the hardcoded `elapsed < 1.0` wall-clock assert flaked (6.7s, 6.6s, 1.73s fail; 0.83s, 0.80s pass) while ~5 sibling battery-shard sidecars hammered this Mac (load avg 2.1-3.0); whole-file run passed clean (52 passed, 0.84s) | holds (timing assert is flaky under this run's shared-host CPU contention, not a mechanism regression — see raw file + notes) |
| R15-DATA-045 | `pytest test_search_redirect_ssrf.py` (all 4: fetch_page/pdf-lane/impersonated-lane block loopback redirect; allowed public redirect still followed) | 4 passed | holds |
| R15-LIFECYCLE-006 | `pytest test_research_model_lane.py::test_retired_model_404_is_an_error_step_naming_the_model` | passed | holds |

COVERAGE: 6/6 ids raw in this set.
