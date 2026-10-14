# rc1-battery-12 — regression battery shard 12

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98, own sidecar :52352 (data dir
rc1-round-5-data-rc1-battery-12, copied from the round's seed data), shared openbb-mcp
:52153 + sec-edgar-mcp :52154 (read-only, untouched).

Worked 4 sets in order: set-11 (batch-4, 8 ids) -> set-1 (batch-2, 5 ids) -> set-48
(batch-11, 2 ids) -> set-66 (batch-18, 1 id). All 16 re-run against the candidate; all 16
HOLD. No vitest/pytest suites run (battery role never runs the heavy lane); one entry
(CODE-AGENT-009) verified via ast line-count + presence of the pinned test file
(test_runtime_phases.py, 9 tests) rather than executing it.

Live checks used: /resolve, /disclosures/shareholding, /news, /earnings/*/estimates,
/fundamentals/*/income, /backtest/run, /custom-agents, /portfolio/positions against my own
sidecar. In-process checks (candidate's venv, sys.path into sidecar/): builtin.py node
handlers (json_path/sleep/compare/notify/agent_invoke) with stubbed agent_runtime.invoke_agent
to inspect exact wiring without a real LLM call (no ollama lock needed, no OpenRouter/OpenAI
spend); symbol_resolver.resolve with an injected bogus rename row; correctness_gate.symbols_match.

No regressions found. Sidecar stopped cleanly (sleep pid 50268, then worker pid 50271) at end.

COVERAGE: 16/16 ids raw; no raw: none.
