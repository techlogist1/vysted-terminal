# batch-8/W5-agent-runtime-research (set-34.md) — rc1-battery-21, round 5-recheck

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Sidecar :52361.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-AGENT-004 | design repro (needs a real billed Gemini thinking round; not run to avoid spend). Source re-check + pinned test `test_usage_meters_thinking_and_tool_use_prompt_tokens`. | `gemini.py` now computes `output_tokens = candidates_token_count + thoughts_token_count`, `input_tokens = prompt_token_count + tool_use_prompt_token_count`, both None-safe — matches fix_shape verbatim. Not executed (no pytest suites in this role). | ci_pinned |
| R15-LEAD-019 | in-process call: `services.budget_guard.price_per_million('openrouter','nvidia/nemotron-3-super-120b-a12b:free')` (the exact slug from the register) vs `DEFAULT_RATE_PER_M` | returned `0.0` (not `DEFAULT_RATE_PER_M=5.0`); `_priced_rate` special-cases any `…:free` OpenRouter slug generically. | holds |
| R15-CODE-AGENT-007 | in-process call: compare `model_registry.default_base_url_for('deepseek'\|'xai'\|'openrouter')` to `llm.DEEPSEEK_BASE_URL`/`XAI_BASE_URL`/`OPENROUTER_BASE_URL` | all three constants now derive from `model_registry.default_base_url_for(...)` at import time — single-sourced (equal by construction, confirmed at runtime). | holds |
| R15-CODE-AGENT-016 | `sidecar/agents/_schema.json` no longer declares a `defaultProvider` enum at all (loader fills it from `model_registry.provider_ids()`); live `GET /agents` | `/agents` returns 13 agents (full roster — the register's stale 7-id enum previously silently dropped an `openrouter`-default agent to 12). | holds |
| R15-LIFECYCLE-014 | live `GET /agents` + `GET /health` | `/agents` count=13 (>0), `/health.agents_degraded=[]` — matches the smoke test's own probe shape (`scripts/smoke-test-sidecars.mjs` checks `/agents` count>0 and `/health.agents_degraded` empty). | holds |
| R15-CODE-RESEARCH-003 | design repro (structural). Source re-check: `sidecar/services/research/deep.py` module docstring states `run_deep_research` "was removed (R15-CODE-RESEARCH-003): it was a drifted second copy reachable only from an except fallback"; `grep run_deep_research sidecar/services/agent_tools/deep_research.py` → no matches (the except-fallback call site is gone too). | Deleted, not merely fixed in place — matches the fix_shape's first option ("Delete run_deep_research"). | holds |

COVERAGE: 6/6 ids raw; no raw: none.
