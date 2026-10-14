# batch-3/W1-agent-runtime (rc1-battery-14, set-5)

Candidate sha 1006c6da694ede5776c3dabbd27b305aeb56b5ad. Sidecar :52354 (source =
rc1-round-4-cand, data = rc1-round-4-data-rc1-battery-14).

Mechanism-level entries re-run via their pinned pytest file
`sidecar/tests/test_b3_runtime_tool_args.py` + `test_b3_runtime_capped_round.py` +
`test_b3_runtime_cancel.py` (11 passed, 0.18s) and `sidecar/tests/test_search_scrub.py`
(part of pytest run2, all passed) plus the frontend AUTO-gate vitest file
`src/lib/host-actions.test.ts` (106 passed). AGENT-001 additionally re-run live.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-001 | Live `vy.py invoke copilot "research KPIT Technologies"` ollama llama3.1:8b on candidate sidecar :52354 (raw: AGENT-001-invoke.txt, AGENT-001-events.jsonl, R15-AGENT-001.txt) | On this isolated no-SearXNG seed profile the loop auto-downgraded to fast/quick and auto-published the brief from structured data, so the model's chat text was a generic "Built you a brief" with no narrated money figure at all — this run's conditions never reach the AGENT-001 trigger (a model narrating a raw fraction/rupee value). Code-level check: `semantics.py` still labels growth/dividend-yield fractions `unit:"percent"` and `brief-blocks.tsx:159` `formatDerived` still treats `fraction`\|\|`percent` the same way (multiplies) — the fix's data shape is unmodified. | holds (code-level; live narration path not reachable on this isolated profile — see raw file) |
| R15-AGENT-002 | `pytest test_b3_runtime_cancel.py::test_aclose_cancels_the_running_tool_within_100ms` | passed | holds |
| R15-AGENT-003 | `pytest test_b3_runtime_capped_round.py` (2 tests: yielded==dispatched, capped-round host action never yielded under AUTO) | passed | holds |
| R15-AGENT-021 | `pytest test_search_scrub.py` (UNTRUSTED SOURCE DATA fence mechanism) + `vitest run src/lib/host-actions.test.ts` (AUTO-gate: portfolio/write_note/save_layout/save_screen/set_region stay pending) | scrub tests passed; vitest 106/106 passed | holds |
| R15-AGENT-022 | `pytest test_b3_runtime_tool_args.py::test_add_position_without_cost_basis_is_never_yielded_and_asks_the_user` | passed | holds |
| R15-AGENT-024 | `pytest test_b3_runtime_tool_args.py::test_stringified_screener_criteria_is_yielded_as_a_list` | passed | holds |
| R15-AGENT-054 | `pytest test_b3_runtime_tool_args.py::test_unknown_indicator_key_fails_validation_naming_it` + `pytest test_indicators.py` (50-key class check) | both passed | holds |
| R15-AGENT-047 | `pytest test_b3_runtime_tool_args.py::test_groq_shaped_invalid_args_never_reach_the_handler` + integer/nested-string coercion tests | passed | holds |

COVERAGE: 8/8 ids raw in this set.
