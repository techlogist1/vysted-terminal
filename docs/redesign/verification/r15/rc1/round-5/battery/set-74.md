# batch-28/W1-opus (rc1-battery-7, set-74)

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98, own sidecar :52347. In-process python calls
into the real candidate `sidecar/.venv` for the runtime-function entries; source reads for the
purely structural fix.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-AGENT-001 | In-process: `services.agent_tools.research.model_view()` on a fraction-unit fundamentals payload (COCHINSHIP/KPITTECH figures from the register) | dividend_yield/revenue_growth/earnings_growth/roe/operating_margin/profit_margin all rewritten to correctly-scaled percent strings ("0.82%","2.40%","-19.37%","16.45%","12.25%","8.84%") — exact match to the cert | holds |
| R15-AGENT-092 | Source read: run_manager.py `undispatched` dict + `_on_tool_result`/`_deliver` gating | a halted round's undispatched host action is never popped into `host_actions`/`brief`; `_output()` cannot deliver it | holds |
| R15-AGENT-094 | In-process: `_coerce()` + `_normalise_tool_args()` on a union-typed (`["array","string"]`) arrange_layout-shaped schema | no `TypeError: unhashable type: list`; union types short-circuit to the validator (line 908-921) | holds |
| R15-AGENT-095 | In-process: `_guard_ratio_claims()` on the register's exact SIFY sentence + 5 unseen date shapes | the dated, sourced ADR-ratio sentence is kept in all 6 cases; dated fabrications still replaced | holds |
| R15-LEAD-014 | Source read: llm/openai.py `_SCHEMA_KEYWORDS` + repair-reply key check | a schema-echo reply (keyed by JSON-Schema keywords) is detected and rejected/retried, not accepted as args | holds |

COVERAGE: 5/5 ids raw; no raw: none.
