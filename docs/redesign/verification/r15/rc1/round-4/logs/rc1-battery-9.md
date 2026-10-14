# rc1-battery-9 — REGRESSION BATTERY shard 9 (batch-4 + batch-6 + batch-25)

Candidate sha: 1006c6da694ede5776c3dabbd27b305aeb56b5ad. Own sidecar :52349 (copy of seed data,
sleep-pid 84334 / worker 84336, both stopped at end); LIFECYCLE-007 additionally re-launched a
second isolated candidate sidecar on :52356 under `env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin`
(stopped, pid 88065). No shared port/data touched.

Sets: batch-4/W5-panels-screener (set-14, 9 entries), batch-6/W4-research-funnel (set-23, 5
entries), batch-25/W6-agent-019-agent-093 (set-75, 2 entries). 16 ids total.

## Result (16 ids total)
- holds: 12 (UI-006, DATA-044, DATA-093, UI-003, CODE-FRONTEND-020, LIFECYCLE-007,
  RESEARCH-018, RESEARCH-012, RESEARCH-016, CODE-RESEARCH-002, AGENT-019, AGENT-093)
- regressed: 1 (R15-RESEARCH-017)
- ci_pinned: 3 (R15-UI-004, R15-UI-005, R15-UI-007 — jsdom/vitest-only certifications; vitest
  is barred under the stall rule, so these are re-verified by static trace of the exact
  deterministic code the pinned test exercises, at this sha)

## Key finding
R15-RESEARCH-017 (medium, register): the certified fix ("wraps run_heavy_research in
try/except and falls back to `_single_pass_fallback(...)`, matching DEEP's existing
fallback", batch-6 VERDICTS.md) does not match this candidate. `grep -rn
_single_pass_fallback sidecar` returns zero hits anywhere in the repo. Re-running the exact
injected-fault repro (disclosures.gather_floor raising inside run_heavy_research's prologue)
through the real user-facing wrap (deep_research.py:296-298) returns an honest
`{"ok": false, "message": "Deep research could not finish — ...", "degraded_reason": "..."}`
in under 3s — not the certified `{"ok": true, "loop": "heavy", "n_sources": 14,
"n_filing_sources": 5}` degraded-but-real brief. The original bug's worst symptom (a raw
unhandled exception escaping the tool boundary) is NOT reproduced — the exception is caught
— but the specific fallback-with-real-content mechanism the batch-6 verifier's transcript
described is absent from this sha. Filed as a regression finding; not re-litigated further
per the three-failure/adjudication rules (this is R15-RESEARCH-017's first re-verification
failure this gate).

## Notable harness friction (not a product defect)
The sidecar's agent-tool catalog is NOT registered on bare module import — a standalone
python script must explicitly call `services.agent_tools.registry_v0_6_0
.register_v0_6_0_tools()` and `services.agent_tools.register_v0_5_0_tools()` before
`agent_tools.invoke_tool(...)` resolves anything beyond `backtest_summary`. Cost ~3 failed
probes before diagnosing; noted here so the next in-process research/agent-tools probe in
this gate doesn't re-spend that time.

COVERAGE: 16/16 ids raw; no raw: none.
