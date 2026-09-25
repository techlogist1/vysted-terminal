# RC1 battery shard 1 (rc1-battery-1) — working log

- Candidate sha: 4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a
- Own sidecar: 127.0.0.1:52341, cwd `<cand>/sidecar`, data dir `scratchpad/rc1-data-battery-1` (copy of rc1-seed-data)
- Sleep pid to kill at teardown: 73534 (wrapper bash pid 73532)
- Shared MCP: openbb-mcp :52153, sec-edgar-mcp :52154 (read-only, untouched)
- LLM lane: local llama3.1:8b via Ollama first; spend ledger checked, total $0.179 of $8.00 cap before this shard.

## Sets (batch-3, stage-c)
- set-5 = W1-agent-runtime (9 ids)
- set-6 = W2-agent-frontend-gate (7 ids)
- set-7 = W3-llm-adapters-and-errors (6 ids)
- set-8 = W4-research-depth (7 ids)
- set-9 = W5-india-data-witnesses (8 ids)

Source of original repros/evidence: docs/redesign/verification/r15/stage-c/batch-3/VERDICTS.md
(and PLAN.md for repro mechanics). Re-running against candidate, not judging from diff.

## Progress
- [x] set-5 — all 9 hold (2 via direct function repro of exact code paths: `_normalise_tool_args`, `_model_facing_content`, `_dispatch_tool_with_progress`, `_resolve_tool_surface`, scripted-adapter `invoke_agent` loop)
- [x] set-6 — all 7 ci_pinned (frontend-only mechanisms; no GUI, no vitest run per constraints; committed tests read at HEAD confirm each mechanism unchanged)
- [x] set-7 — all 6 hold/ci_pinned (native_search_available, tool_call_rescue, errors.humanize, live /llm/keys/validate; AGENT-004 ci_pinned since its scratch anth_proof.py repro script no longer exists)
- [x] set-8 — all 7 hold/ci_pinned (RESEARCH-007/DATA-045/LIFECYCLE-006/RESEARCH-008 timing live/direct; RESEARCH-009/AGENT-012/RESEARCH-006 ci_pinned via test_research_metering.py/test_research_verify.py — a supplementary live DEEP llama3.1:8b run was started but killed after 30+min with no output, degraded by the same SearXNG upstream block RESEARCH-008 found)
- [x] set-9 — all 8 hold/ci_pinned (DATA-005/LEAD-002/DATA-019/DATA-022 live on candidate sidecar; DATA-021 via a direct `_merge_bse_split` repro with synthetic BSE input, since BSE's live SHP index is still 403-blocked this session — same as batch-3's own verifier hit; RESEARCH-011 confirmed via the same code path DATA-021 exercised; RESEARCH-013 via chain-grep + dynamic-stamp read + live exchange-source check; RESEARCH-010 validation-half live, error-half ci_pinned)

## Teardown
- Own sidecar (:52341) stopped by killing its sleep pid 73534 — confirmed dead, /health no longer responds.
- Loopback SSRF canary (:52490) stopped (pid 87164).
- Shared stack (main :52152, openbb-mcp :52153, sec-edgar-mcp :52154) — untouched throughout, never restarted.
- Supplementary live DEEP research009 job (pid 88168) killed after 30+min hang (SearXNG-degraded); its ci_pinned verdict does not depend on it.

## Environment conditions found (not product defects, both already documented in batch-3's own VERDICTS.md)
1. BSE `api.bseindia.com` SHP-index/scrip-header 403 (Akamai) from this IP this session — `www.bseindia.com` still serves attachments/XBRL fine. Confirmed via a direct probe.
2. Shared SearXNG (`vysted-searxng` :8888) upstream-degraded this session: `brave: Suspended: too many requests; duckduckgo: CAPTCHA; startpage: Suspended: CAPTCHA` — confirmed via `/search/searxng/status`. The `web_search` tool still returned within its 25s cap (7.5-8.1s), just with 0 rows.

## Final counts (37 entries)
holds: 26, ci_pinned: 11, regressed: 0, needs_gui: 0, blocked_env: 0
(ci_pinned: AGENT-080, CODE-FRONTEND-008, CODE-FRONTEND-003, CODE-FRONTEND-014, UI-001, UI-002,
AGENT-014 (set-6, no GUI/no vitest), AGENT-004 (set-7, scratch repro script no longer exists),
RESEARCH-009, AGENT-012, RESEARCH-006 (set-8, live DEEP run degraded by SearXNG/slow local
model). RESEARCH-010 counted under "holds" — its validation half was live-confirmed on the
candidate; only its error half rode a committed test.)

