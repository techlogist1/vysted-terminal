# batch-10/W2-catalog-hostactions — rc1-battery-4 (round 5)

Candidate: 9bc600ece2ce6343a6aa48f130d7620b1466bb98. Sidecar :52344.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-084 | live llama3.1:8b `invoke copilot "draw a support line at 1450 on the RELIANCE chart"` against :52344 | `tool_use add_chart_drawing {panelId:"chart", kind:"horizontal-line", points:[{price:1450,...}]}` → `tool_result ok:true` → `research_step` notice "Staged for your review, not applied yet: add_chart_drawing" (proposed-changes gate holds); assistant text confirms staged, not applied | holds |
| R15-CODE-AGENT-013 | in-process probe (candidate `.venv`): `catalog.internal_tool_ids()`/`agent_selectable_tool_ids()`/`default_grant_tool_ids()`/`mcp_capabilities()` | internal=56, selectable=56, default_grant=55 (not all three equal — `default_grant=False` is live on at least one capability); `aliases` read at `catalog.py:1824` inside `resolve_tool_ids`; mcp count=32 (a real, non-trivial projection, not the whole catalog echoed) | holds |
| R15-CODE-PLATFORM-021 | `POST /portfolio/positions`, `PUT/DELETE /portfolio/positions/AAPL`, `GET /portfolio/positions` on :52344 | POST→405, PUT→404, DELETE→404, GET→`[]` — sidecar ledger write routes still gone; frontend store remains the one truth (exact match to certification) | holds |
| R15-RESEARCH-030 | live llama3.1:8b `invoke copilot "what did management say about growth and margins on the last earnings call for KPITTECH"` against :52344 | `tool_use earnings_call_transcript {symbol:"KPITTECH"}` → `tool_result ok:true`; assistant answer quotes specific management commentary (Kishor Patil, margins, Qorix loss) from the filed transcript — matches certification's KPITTECH case | holds |

COVERAGE: 4/4 ids raw; no raw: none.
