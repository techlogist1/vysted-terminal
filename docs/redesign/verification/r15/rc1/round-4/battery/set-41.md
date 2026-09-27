# set-41 — batch-10/W2-catalog-hostactions (rc1-battery-3)

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad, own sidecar :52343.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-AGENT-013 | Code read (catalog.py:199-225,1793) + in-process python import | `internal`/`mcp` are derived `@property`s (never stored/overwritten), `_cap()` passes only non-defaults, `agent_selectable_tool_ids()` == `internal_tool_ids()` by design; live: internal=56, agent_selectable=56 (equal), default_grant=55 (<56, confirms `default_grant=False` is live), mcp=32 | holds |
| R15-RESEARCH-030 | Live in-process call `disclosure_tools._earnings_call_transcript({"symbol":"KPITTECH"})` | ok:true, available:true, filing_date 2026-08-04, real NSE PDF url, extracted transcript text with management commentary on margins/revenue | holds |
| R15-AGENT-084 | Code read (host-actions.ts:81,106,954,1171,1498; catalog.py:1330) + pinned vitest | `add_chart_drawing` wired end to end (catalog capability + describe/apply switches); `HAND_ACTION_INVENTORY` pins bidirectional coverage + an apply test | ci_pinned (src/lib/hand-action-inventory.test.ts) — live LLM re-drive not repeated given the shared Ollama lane; static+pinned evidence is strong |
| R15-CODE-PLATFORM-021 | Live `POST/PUT/DELETE /portfolio/positions[...]`, `GET /portfolio/positions` on :52343 | POST 405, PUT 404, DELETE 404, GET 200 `[]`; grep of `src/` finds no POST/PUT/DELETE fetch caller on `/portfolio` | holds |

COVERAGE: 4/4 ids raw; no raw: none.
