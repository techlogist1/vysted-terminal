# set-41 — batch-10/W2-catalog-hostactions (rc1-battery-4)

Candidate: `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. Sidecar `:52344`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-AGENT-013 | In-process (candidate venv): `services.agent_tools.catalog.internal_tool_ids()` / `agent_selectable_tool_ids()` / `default_grant_tool_ids()` / `mcp_capabilities()`, plus a source check of `resolve_tool_ids` for alias reads | `internal=56, selectable=56, default_grant=55` (`selectable != default_grant`, diff = `{'ask_user'}` — `default_grant=False` is live, not dead); `resolve_tool_ids` source references `aliases`; `mcp_capabilities()` returns 32 entries projected from `kind` | holds |
| R15-RESEARCH-030 | In-process (candidate venv) call of `services.agent_tools.disclosure_tools._earnings_call_transcript` for KPITTECH and INFY (own repro's `grep -in transcript catalog.py` + the capability's functional behaviour) | KPITTECH: `ok:true`, NSE PDF filed 2026-08-04, extracted transcript text (CEO commentary); INFY: `ok:true`, filed 2026-07-28, extracted text; `grep -in transcript catalog.py` now hits 3+ times (capability registered) | holds |
| R15-AGENT-084 | Live `vy.py invoke copilot "Draw a support line at 1,450 on the RELIANCE chart"` against `:52344`, provider ollama, model llama3.1:8b, mode agent, autonomy ask (own repro's literal prompt) | `tool_use add_chart_drawing {symbol:RELIANCE, kind:horizontal-line, points:[{price:1450}]}` -> `tool_result ok:true` -> `research_step`: "Staged for your review, not applied yet: add_chart_drawing RELIANCE." (proposed-changes gate, never auto-applied — no trading path); `add_chart_drawing` still present in `host-actions.ts` + `catalog.py`; `hand-action-inventory.test.ts` still present | holds |
| R15-CODE-PLATFORM-021 | `curl` own repro: `POST /portfolio/positions`, `PUT`/`DELETE /portfolio/positions/AAPL`, `GET /portfolio/positions` on `:52344` | `POST -> 405`, `PUT -> 404`, `DELETE -> 404`, `GET -> 200 []` — sidecar ledger write routes stay gone, matches certified state exactly | holds |

Raw: `battery/raw/set-41/<id>.txt`.

COVERAGE: 4/4 ids raw; no raw: none.
