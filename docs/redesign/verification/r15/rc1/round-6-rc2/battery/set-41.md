# set-41 batch-10/W2-catalog-hostactions (rc1-battery-20, candidate ace7dd76)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-AGENT-013 | in-process catalog projections + alias resolve (raw: raw/set-41/R15-CODE-AGENT-013.txt) | internal 56 / agent_selectable 56 (documented equal by design) / default_grant 55 (ask_user withheld); aliases read (resolve_tool_ids(['macro']) -> macro_series); mcp_capabilities 31 projected | holds |
| R15-RESEARCH-030 | grep transcript in catalog.py; live earnings_call_transcript handler vs NSE for KPITTECH and INFY (raw: raw/set-41/R15-RESEARCH-030.txt) | catalog entry + TOOL_SCHEMAS present; KPITTECH ok filing_date 2026-08-04 (call July 29, 2026), INFY 2026-07-28, source NSE, transcript text returned | holds |
| R15-AGENT-084 | catalog/TOOL_SCHEMAS probe + host-actions grep (raw: raw/set-41/R15-AGENT-084.txt) | add_chart_drawing in catalog and TOOL_SCHEMAS (horizontal-line, trendline), host-actions.ts apply/describe cases, hand-action-inventory.test.ts and test_capability_completeness.py audits exist; live llama agent run not re-run | holds |
| R15-CODE-PLATFORM-021 | curl on own sidecar :52360 (raw: raw/set-41/R15-CODE-PLATFORM-021.txt) | POST /portfolio/positions 405, PUT/DELETE /AAPL 404, GET 200 []; openapi lists GET only; only client reader is the legacy-migration fetch in portfolio/api.ts | holds |
