# set-8 — batch-3/W4-research-depth (rc1-battery-20)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. All 7 entries carry pinned tests added
since batch-3 that assert the exact original repro (redirect-blocking SSRF via a real local
HTTP server, retired-model 404 error step, non-zero metered cost, bounded verdict wall, keyless
engine rotation deadline, rejected-key error step). Per the harness rule, pytest suites are not
executed here; each verdict is `ci_pinned` naming the test(s), confirmed by reading the pinned
test source at the candidate sha (raw files under `battery/raw/set-8/`).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-012 | Read `sidecar/tests/test_research_metering.py` (docstring cites AGENT-012/RESEARCH-009). | `test_deep_run_with_reported_usage_has_a_nonzero_cost`, `test_unmeasured_usage_reports_unknown_cost_not_zero` pin non-zero/unknown cost reaching the guard. | ci_pinned |
| R15-DATA-045 | Read `sidecar/tests/test_search_redirect_ssrf.py`. | A real local `ThreadingHTTPServer` 302-redirects `/start` → `/secret`; `test_fetch_page_blocks_a_public_page_that_redirects_to_loopback`, `test_pdf_lane_blocks_the_same_redirect`, `test_impersonated_lane_blocks_the_same_redirect` all assert `secret_hits == 0` and a blocked-redirect error across every lane (httpx, PDF, curl_cffi-impersonated). | ci_pinned |
| R15-LIFECYCLE-006 | Read `sidecar/tests/test_research_model_lane.py` + `test_sonar_lane.py`. | `test_retired_model_404_is_an_error_step_naming_the_model` (docstring: "a retired slug no longer yields a blank turn"), `test_retired_sonar_reasoning_is_not_pinned`. | ci_pinned |
| R15-RESEARCH-006 | Read `sidecar/tests/test_research_verify.py`. | `test_slow_verdicts_cannot_carry_the_round_past_its_wall`, `test_verdicts_reached_in_budget_are_kept_and_the_tail_is_unverified` pin the bounded-loop fix shape (the pre-loop extract/search residual noted in batch-3 issue 5 is out of scope — not re-opened by this pin). | ci_pinned |
| R15-RESEARCH-008 | Read `sidecar/tests/test_keyless_backend.py`, `test_web_search.py`, `test_ddg_backend.py`. | `test_hanging_engine_gets_no_second_attempt_and_the_chain_rotates`, `test_three_engine_deadlines_fit_inside_the_web_search_tool_cap`, `test_keyless_hanging_ddg_serves_brave_inside_the_tool_cap`, `test_ddg_makes_one_request_the_keyless_tier_owns_retry` — all docstring-tagged RESEARCH-008. | ci_pinned |
| R15-RESEARCH-009 | Same as AGENT-012 (shared test file/fix). | `test_tiny_spend_ceiling_breaches_and_forces_synthesis`, `test_research_guard_takes_its_ceilings_from_the_depth_profile` additionally pin the DEEP/ULTRA ceilings. | ci_pinned |
| R15-RESEARCH-010 | Read `sidecar/tests/test_research_model_lane.py` + `test_llm_openai.py`. | `test_rejected_key_401_is_also_an_error_step` (docstring: "a 401 reaches the stream too"); `test_openrouter_validate_key_false_when_key_endpoint_401` / `_true_when_key_endpoint_200` pin the validate half. | ci_pinned |

COVERAGE: 7/7 ids raw; no raw: none.
