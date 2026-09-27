# batch-11/W2-runtime-schema (set-48)

Candidate: 9bc600ece2ce6343a6aa48f130d7620b1466bb98, own sidecar :52352

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-AGENT-009 | ast parse of sidecar/services/agent_runtime.py for invoke_agent / _dispatch_round line spans; ls+grep sidecar/tests/test_runtime_phases.py | invoke_agent is 101 lines (was 488), _dispatch_round 193 lines; test_runtime_phases.py exists with 9 direct phase tests | holds |
| R15-LIFECYCLE-024 | sqlite3 PRAGMA user_version on all 7 stores at boot, then curl /custom-agents and /portfolio/positions and re-check | data_cache/fundamentals_cache/workflows=1 at boot; custom_agents/portfolio flip 0->1 on first route touch, matching the certified per-store migration behaviour | holds |

COVERAGE: 2/2 ids raw; no raw: none.
