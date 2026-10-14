# batch-11/W7-preferences (rc1-battery-1, candidate 4c6dfe8c)

Note: closed in batch-11 per `closure_evidence` (matches the task's own set label).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-087 | grep `PROVIDER_FAILURE_CODES` in `src/modules/chat/streaming.ts`; grep the 6 named codes in `sidecar/services/errors.py`; presence of `llm-providers.test.ts` | `PROVIDER_FAILURE_CODES = new Set(["auth","provider_402","insufficient_credit","network","ollama_not_running","provider_5xx"])` at `streaming.ts:69-76` — byte-identical to the certified set; all 6 codes independently confirmed present in `errors.py`. `llm-providers.test.ts` covers `orderedProviders` fallback behaviour. GUI feel (drag reorder, notice chip) remains unexercised headless per batch-11's own note — separate later GUI workflow, not this shard's job | ci_pinned |

COVERAGE: 1/1 ids raw; no raw: none.
