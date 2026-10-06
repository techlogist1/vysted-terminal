# batch-3/W3-llm-adapters-and-errors (rc1-battery-1, candidate 4c6dfe8c)

Note: all 5 ids actually closed in batch-7 or batch-12 per `closure_evidence` (batch-3's
VERDICTS.md W3 section covers a different id set: AGENT-004/005/018/UI-008). Evidence
below cites the entry's real closing batch.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-027 | in-process `errors.humanize(provider, status=..., detail=...)` over the original captured bodies + fresh cases | OpenAI 429 credit → `insufficient_credit`; OpenAI/Groq/Anthropic context-overflow bodies → `context_overflow`; Gemini/xAI bad-key 400 → `auth`; Ollama `ConnectionRefusedError` → `ollama_not_running`; OpenRouter `:free` 429 (`upstream_provider_shared_pool` marker) → `free_pool_busy`; together 404 decommissioned → `model_not_found` — all match the certified mapping table | holds |
| R15-AGENT-032 | grep "Couldn't apply" in `ChatSidebar.tsx`/`ChatSidebar.test.tsx` | both present unchanged at HEAD; entry certified "vitest-executed" (frontend-only, no live half) | ci_pinned |
| R15-AGENT-045 | in-process `_compare_symbols(['COCHINSHIP','MAZAGONDOCK'])` and a fresh names-only case | `ok:false`, message names `MAZAGONDOCK: unresolved name: 'MAZAGONDOCK' is not a known ticker...`; fresh `['Cochin Shipyard','Mazagon Dock']` → `ok:true`, resolved to `[COCHINSHIP, MAZDOCK]` — exact match to the certified behaviour | holds |
| R15-AGENT-048 | grep `_MAX_REPAIRS_PER_ROUND` in `services/llm/openai.py` | constant is `2`, gate at line 527 unchanged from the certified shape (repairs capped at 2 of 5, each timed/metered) — live 5-bad-call round not re-run this shard (Ollama-lane cost); static confirmation | holds |
| R15-CODE-AGENT-003 | `POST /llm/keys/validate` live with fake OpenRouter, Gemini, xAI keys | all three return `{"ok":false,"reason":"invalid",...}`; Gemini specifically reports "invalid", not a transport error | holds |

COVERAGE: 5/5 ids raw; no raw: none.
