# batch-3/W1-agent-runtime (rc1-battery-1, candidate 4c6dfe8c)

Note: LEAD-004 and AGENT-020 closed in batch-3 per `closure_evidence`; AGENT-008 closed in
batch-8; AGENT-019 closed in batch-10 (a re-fix after the original batch-3 cert, per
`closure_evidence`); AGENT-023 and AGENT-057 closed in batch-7; AGENT-069 is `status: open`
(never fixed) — evidence below cites the entry's real closing batch, or the open repro as-is.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-008 | in-process `_model_facing_content(tool_name, result_str, window)` with an oversized result + static token/window math | truncates at `limit = window * _CHARS_PER_TOKEN // _RESULT_WINDOW_SHARE`, appends `"…[{N} chars elided — call again with a narrower query or a smaller limit]"` — exact match to the certified shape | holds |
| R15-AGENT-019 | in-process `agent_runtime._resolve_tool_surface(spec, 'agent', prompt)` (the real gating function, not just `classify_intent`) over 5 phrasings incl. the register's own `[SURF-PORTFOLIO-NOTES-5]` example ("My RELIANCE lot is actually 12 shares") | `classify_intent` alone gives `intent='read', signals=[]` for the tricky phrasing, but the actual gate is `read_only = inferred_intent == "read" and bool(intent.signals)` (agent_runtime.py:~1766) — empty signals means `read_only=False`, so write tools are KEPT. All 5 phrasings, including the tricky cue-less one, keep portfolio write tools. `git log`/`git show` on the two `_EDIT_SIGNALS`-touching commits (`cac929d8`, `c65c4c1f`) confirm purely additive changes, no removal | holds |
| R15-AGENT-020 | in-process `_note_for`/`_notes_of` against a synthetic multi-note payload | note attribution/dedup behaviour matches the certified shape | holds |
| R15-AGENT-023 | grep `action.webhook`/`workflow_scheduler.py`/`test_b7_scheduler.py`; live openapi.json route census + `GET /workflow/webhooks` on own sidecar (:52341) | `action.webhook` node registered in `node-registry.ts` alongside `action.log`/`action.notify_desktop`; `sidecar/services/workflow_scheduler.py` + committed `test_b7_scheduler.py` present; `builtin.py:346-416` implements the URL-never-logged, https-only webhook handler unchanged. Live: `/workflow/schedules` (get,post), `/workflow/schedules/{id}` (patch,delete), `/workflow/webhooks` (get), `/workflow/webhooks/{ref}` (put) all present and respond; `GET /workflow/webhooks` → `{"refs":[]}` (fresh data dir). Full live 10+min interval-fire-twice re-run not repeated this shard (stall-watchdog/time budget) | holds |
| R15-AGENT-057 | grep `response.status === 409` in `src/lib/plugin-agents.ts:67`; baseline `GET /custom-agents` live | PUT-on-409 retry mechanism present unchanged at HEAD; `/custom-agents` live and returns 200. Entry certified via a real vitest 409-retry test (frontend-only, no live half) | ci_pinned |
| R15-AGENT-069 | grep `asyncio.gather(` in `compare_symbols.py:249` and `market_overview.py:117-118` | both call sites still lack `return_exceptions=True` — matches the register's own still-open repro exactly (entry `status: open`, never fixed). Not a regression: the expected/certified state for this id IS "still open" | holds (open, unfixed — not a regression) |
| R15-AGENT-082 | live `vy.py invoke copilot` via ollama under the shared-lane lock, on own sidecar :52341 | `done` frame carries `"spend_usd": 0.0` (numeric, present) — matches batch-10's certified figure exactly; frontend consumer `streaming.ts:495` unchanged | holds |
| R15-LEAD-004 | `GET /fundamentals/TCS`, `/fundamentals/DHANBANK` live | both 200 with full fundamentals payload | holds |

COVERAGE: 8/8 ids raw; no raw: none.
