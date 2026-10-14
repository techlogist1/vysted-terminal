# batch-8/W5-agent-runtime-research (rc1-battery-23, round 5)

Candidate: `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. In-process Python against the candidate's
`sidecar/.venv`, run from the candidate worktree's `sidecar/` cwd. All model-registry edits were
done as in-memory monkeypatches of `model_registry._PROVIDERS_BY_ID` (restored before exit) —
the read-only candidate worktree was never written to.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-CODE-AGENT-004 | Source check: `sidecar/services/llm/gemini.py:187-198`. | `output_tokens = candidates_token_count + thoughts_token_count`, `input_tokens = prompt_token_count + tool_use_prompt_token_count` — the exact formula the register/batch-8 pinned (800+6000=6800 output, 1000+200=1200 input); `BudgetGuard._usage_tokens` sums both for the ceiling check. | holds |
| R15-CODE-AGENT-007 | In-process: `llm.get_provider("deepseek"/"xai")` before and after monkeypatching `model_registry._PROVIDERS_BY_ID["deepseek"/"xai"]["default_base_url"]`. | Before: `https://api.deepseek.com`, `https://api.x.ai/v1`. After the in-memory edit: `https://edited.deepseek.example/v9`, `https://edited.x.example/v2` — dispatch tracks the registry live, no drift. | holds |
| R15-CODE-AGENT-016 | In-process: `agent_runtime._load_schema()` + a scratch agent JSON with `defaultProvider:"openrouter"` through `_discover_specs()` on a copy of the real agents dir. | Schema enum is `[anthropic, openai, gemini, groq, ollama, deepseek, xai, openrouter]` (derived live from `model_registry.provider_ids()`, no hardcoded copy on disk); the openrouter agent loaded, roster 13 -> 14. | holds |
| R15-CODE-RESEARCH-003 | `grep -n run_deep_research sidecar/services/agent_tools/deep_research.py` (0 hits) + read of `_run_loop` (deep_research.py:239-317). | `run_deep_research` is gone; `_run_loop` dispatches only to `run_heavy_research`/`run_iter_research`, each independently wrapped so an exception returns `_loop_failed(loop, exc)` -> `{ok:false, message:"Deep research could not finish — the <loop> research loop failed: ...", execution_loop:<loop>}`. | holds |
| R15-LEAD-019 | In-process: `budget_guard.price_per_million("openrouter","nvidia/nemotron-3-super-120b-a12b:free")` and `estimate_spend_usd(..., 64895)`. | Rate 0.0, spend 0.0 for 64,895 tokens on the exact register slug (vs batch-7's phantom 0.12979 pre-fix). A control unlisted **paid** slug still meters (0.12979 for the same token count) via `DEFAULT_RATE_PER_M`, so the zero-rate is scoped to `openrouter` `:free` only (`_priced_rate`, budget_guard.py:80-88). | holds |
| R15-LIFECYCLE-014 | In-process: `_discover_specs()` on a scratch agents dir with one schema-violating file, and on a missing directory. | The bad file is skipped with a named reason (`degraded_agents` entry), the rest of the roster still loads; a missing dir returns `{}` **and** a non-empty degraded entry `"agents directory not found"` — the pre-fix silent-`{}` case is gone. | holds |

COVERAGE: 6/6 ids raw; no raw: none.
