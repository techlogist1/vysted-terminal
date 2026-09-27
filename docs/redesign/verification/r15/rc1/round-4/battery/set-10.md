# Set — batch-4/W1-agent-runtime (rc1-battery-6)

Candidate: `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Own sidecar `:52346` (seed-data copy
`rc1-round-4-data-rc1-battery-6`), reused for the whole shard.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-008 | Code trace: `sidecar/services/agent_runtime.py` `_window_tool_subset`/`_fit_to_window` wired into `invoke_agent` (call sites L2730, L2798); `ollama.py` `DEFAULT_NUM_CTX=16384` unchanged (that half was never the defect). | Full-schema/tool-result overflow now mitigated by domain-cued schema subsetting + oldest-tool-result elision before the round is sent. | holds |
| R15-AGENT-009 | Code trace: `screener_tools.py` pops the unbounded `skip_details` ledger and replaces it with a capped `skip_examples` slice. | Unbounded per-symbol skip ledger no longer reaches the model. | holds |
| R15-AGENT-006 | Code trace (no funded Gemini key this shard, per register's own "NOT TESTED live" caveat): `gemini.py` now reads/writes `thought_signature` on both receipt and replay; `models/llm.py` carries it as internal metadata. | Signature round-trips through the runtime instead of being dropped. | holds |
| R15-LEAD-007 | Code trace: `schemas.py` `gemini_tools()` now emits `parameters_json_schema` (raw JSON Schema) instead of `parameters` (the OpenAPI-subset Schema that rejected int enums / list-valued `type`). | The exact validation-error path the register named is closed structurally. | holds |
| R15-LEAD-008 | Code trace: `native_search.py` `SUPPORTS_NATIVE_SEARCH` excludes `"xai"`; comment cites R15-LEAD-008 directly. | xAI agent turns can never enable provider-level native search, so the 410 path is unreachable. | holds |
| R15-RESEARCH-005 | Pinned test `tests/test_research_synthesis_timeout.py` (register's live 60s+ Ollama repro not re-run this shard — impractical per-id); code trace confirms `SYNTHESIS_TIMEOUT_REASON`/`NOTE` wired from `deep.py` through `iter.py` into `agent_tools/deep_research.py`'s `degraded_reason`. | 4/4 pinned assertions pass, including the exact `execution.degraded_reason == SYNTHESIS_TIMEOUT_REASON` case. | ci_pinned (test_research_synthesis_timeout.py) |
| R15-DATA-041 | Code trace: `compare_symbols.py` `_rank()` computes a `common_start` + 7-day slack cutoff; a symbol whose own window starts later is excluded from best/worst and surfaced via a `note`. | A 2-bar new-listing series can no longer out-rank a full 6-month series. | holds |
| R15-DATA-046 | Live: `GET /macro/NY.GDP.MKTP.KD.ZG?provider=world-bank` with `X-Vysted-Region: IN` on own sidecar `:52346`. | `title: "GDP growth (annual %) — IND"`, `country=IND` in notes — no longer the hardwired USA default. | holds |
| R15-AGENT-011 | Code trace: `src/store/backtest.ts` `loadRun(runId)` GETs `/backtest/runs/{runId}` and adopts it as a complete/active run; `src/lib/host-actions.ts` calls it for an agent-started `run_custom_backtest` result. | The backtest panel is no longer stuck empty when the copilot runs a backtest. | holds |

Raw files: `battery/raw/set-10/R15-*.txt` (9 files, one per id).

COVERAGE: 9/9 ids raw; no raw: none.
