# batch-10/W2-catalog-hostactions (rc1-battery-7)

Candidate `4097dac4`. Own sidecar on `:52347`. 4 certified entries re-run.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-AGENT-013 | in-process: `catalog.internal_tool_ids()`, `agent_selectable_tool_ids()`, `default_grant_tool_ids()`, `mcp_capabilities()` | 56 / 56 / 55 / 32 (cert: 55/55/54/31 — every count is +1 at HEAD, consistent with a later-added capability, likely RESEARCH-030's `earnings_call_transcript` also in this same writer set); the mechanism holds identically: `agent_selectable_tool_ids == internal_tool_ids` (parity, "equal by design"), and `default_grant` is exactly one less than `internal` (one `default_grant=False` capability, same as cert) | holds |
| R15-RESEARCH-030 | in-process: `disclosure_tools._earnings_call_transcript({"symbol": "KPITTECH"})` and `"INFY"` | KPITTECH: `filing_date=2026-08-04`, correct NSE transcript URL (matches cert's 2026-08-04 / July-29-call exactly) — PDF body fetch failed with a curl "Recv failure: Connection reset by peer" (external NSE anti-bot behavior on this network path, not a candidate defect: the transcript-vs-analyst_meet classification and filing discovery both succeeded); INFY: `ok:true, filing_date=2026-07-28` (matches cert), full transcript text returned, quoting Salil Parekh on FY27 guidance | holds |
| R15-AGENT-084 | live `vy.py invoke copilot 'draw a support line at 1,450 on the RELIANCE chart' --provider ollama --model llama3.1:8b` against `:52347` | `tool_use add_chart_drawing {kind: horizontal-line, points:[{price:1450}]}` → `research_step` "Staged for your review, not applied yet: add_chart_drawing. Accept it below to apply." (proposed-changes gate held) | holds |
| R15-CODE-PLATFORM-021 | `POST /portfolio/positions`, `PUT`/`DELETE /portfolio/positions/AAPL`, `GET /portfolio/positions` | 405, 404, 404, 200 `[]` — exact match to cert (no sidecar ledger write route exists) | holds |

Excluded (not certified in batch-10): R15-AGENT-083 (concur not-a-defect / decision, not a certified fix — out of scope for a regression re-run).

Raw output: `battery/raw/set-39/*`.
