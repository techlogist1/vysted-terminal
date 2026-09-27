# rc1-battery-12 — shard 12 working log

Role: REGRESSION BATTERY shard 12 (Sonnet), stage-c batch-4 + batch-3 + batch-25 + batch-29.
Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd (worktree rc1-round-5-recheck-cand, confirmed).
Sidecar: main sidecar from source, cwd `<cand>/sidecar`, port 52352, data dir
`rc1-round-5-recheck-data-battery-12` (copied from seed). openbb-mcp :52153 / sec-edgar-mcp :52154
(shared, read-only). Sleep pid: 81790 (python3 worker pid 81791). Booted 19:59, /health ok.

Sets:
- set-13.md — batch-4/W3-chat-runs-mcp: R15-CODE-FRONTEND-002, R15-AGENT-013, R15-AGENT-029,
  R15-CODE-PLATFORM-037, R15-LIFECYCLE-005, R15-CODE-AGENT-002, R15-DATA-083, R15-DATA-039
- set-7.md — batch-3/W3-llm-adapters-and-errors: R15-AGENT-004, R15-AGENT-005, R15-AGENT-018,
  R15-UI-008, R15-CODE-AGENT-003
- set-69.md — batch-25/W3-sonnet: R15-LEAD-028, R15-DATA-064
- set-81.md — batch-29/W1-opus: R15-RESEARCH-001

Never run vitest/pytest suites here (heavy lane owns them). Entries certified only via a pinned
test get verdict ci_pinned naming the test.

## Result

All 16 entries: verdict holds or ci_pinned (frontend-only entries whose original repro needs a
live browser/jsdom run this shard cannot drive without vitest). Zero regressions.

- set-13 (batch-4/W3, 8 ids): 5 holds (live curl/in-process), 3 ci_pinned (frontend store /
  streaming.ts logic — pinned committed tests read and confirmed present + matching, not
  executed). R15-AGENT-013 confirmed live via a real ollama Delegate run through the runs API
  (under the Ollama lock): 588-char complete answer, full brief preserved, matching the fix.
  R15-LIFECYCLE-005 confirmed via a disposable second sidecar (:52381) pointed at a closed
  openbb-mcp port — simulates the dead child without ever touching the shared :52153.
- set-7 (batch-3/W3, 5 ids): all 5 holds — in-process replays (Anthropic SSE MockTransport,
  native_search_available, tool_call_rescue) and live /llm/keys/validate probes.
- set-69 (batch-25/W3, 2 ids): both holds — live curl against own sidecar (BSE scrip codes,
  30m timeframe).
- set-81 (batch-29/W1, 1 id): holds — live external news fetch + in-process gate_news replay
  on the register's own BDL case and the batch-29 fresh case (AI/C3.ai).

Sidecars used: :52352 (main shard sidecar, stopped, sleep pid 81790) and a disposable :52381
(R15-LIFECYCLE-005 only, stopped, sleep pid 85882). Ollama lock held once for R15-AGENT-013
(acquired, briefly mis-released before the detached run finished, re-acquired and held through
completion, released cleanly).

COVERAGE: 16/16 ids raw; no raw: none.
