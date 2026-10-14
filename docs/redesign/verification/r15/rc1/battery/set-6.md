# batch-3/W2-agent-frontend-gate (rc1-battery-1, candidate 4c6dfe8c)

Note: AGENT-007 closed in batch-11, AGENT-012/CODE-FRONTEND-003/UI-001 in batch-3,
AGENT-034 in batch-7, CODE-FRONTEND-002 in batch-4, AGENT-005 in batch-3, per
`closure_evidence`. AGENT-007 is deduplicated with set-50 (same id, one row in `results`).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-005 | in-process `native_search_available(provider, None, model)` | groq `llama-3.3-70b-versatile` → False, gemini `gemini-2.5-pro` → False, `groq/compound` → True, `gemini-3-pro` → True — matches the certified table (code-level; no funded Groq/Gemini key, as the entry's own certification notes) | holds |
| R15-AGENT-007 | see set-50 (same id) | — | see set-50 |
| R15-AGENT-012 | grep committed metering tests | `test_research_metering.py` 5 tests present unchanged at HEAD (nonzero-cost DEEP run, ceiling breach, unmeasured-usage-not-zero, depth-profile ceilings). A live re-derivation attempt (vy.py researcher invoke under the Ollama lock) exited immediately — vy.py's `--options` has no depth-trigger wiring for the invoke route (DEEP is chosen by the model's own tool-call args); not retried given the 52-entry shard budget | ci_pinned |
| R15-AGENT-034 | in-process `RunBudget()` defaults + `DEFAULT_RUN_BUDGET` constant + `maxSteps:0` validation | `RunBudget()` fields are `None` (unset); `DEFAULT_RUN_BUDGET = RunBudget(max_tokens=120_000, max_spend_usd=1.0, max_wall_seconds=600, max_steps=12)` — exact match; `maxSteps:0` raises `ValidationError` (gt=0) | holds |
| R15-CODE-FRONTEND-002 | grep `abort`/`AbortController` in `ChatSidebar.tsx`/`.test.tsx` | present unchanged at HEAD; entry certified via a real vitest render (frontend-only, no live half) | ci_pinned |
| R15-CODE-FRONTEND-003 | grep `"Appended to the General note"` in `host-actions.test.ts:1198` | present unchanged at HEAD | ci_pinned |
| R15-UI-001 | grep for the TipTap notes-editor test files | `notes.test.ts`, `NotesPanel.test.tsx`, `NotesToolbar.test.tsx`, `store/notes.test.ts` all present at HEAD | ci_pinned |

COVERAGE: 7/7 ids raw; no raw: none (AGENT-007's raw lives under set-50).
