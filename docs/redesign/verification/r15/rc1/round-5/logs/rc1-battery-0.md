# rc1-battery-0 — working log

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98. Own sidecar :52340 (source,
sidecar/.venv), data dir `rc1-round-5-data-rc1-battery-0` (copy of the round's seed
data), openbb-mcp :52153 + sec-edgar-mcp :52154 shared read-only. Sidecar stopped at
end of shard (worker pid 37886 after the mid-run restart for LIFECYCLE-012; original
worker pid 24575).

## set-76 (batch-28/W3-sonnet): DATA-003, DATA-024, DATA-038, RESEARCH-022
All 4 hold. curl against the disclosures/sec routers + one in-process
`KeylessSearchBackend` repro. See battery/set-76.md + raw/set-76/*.txt.

## set-25 (batch-7/W2-delegate-runs-runtime): AGENT-034/035/036/037/038/039/074,
## CODE-AGENT-010/011, LIFECYCLE-012/013, UI-040
11 hold live, UI-040 ci_pinned (frontend store logic pinned in
`src/lib/delegate-runs.test.ts`, out of this role's live-probe scope). Live probes
against `/agents/copilot/runs` + `/runs/*` with provider ollama (llama3.1:8b, under
the local-model lock) and OpenRouter free `nvidia/nemotron-3-super-120b-a12b:free`
(key read in-process from the dev keystore, never printed, via
`X-LLM-Api-Key`/body `api_key`) for AGENT-039's planner half. LIFECYCLE-012 used a
real `kill -9` + sidecar restart against the same data dir mid-run. See
battery/set-25.md + raw/set-25/*.txt.

Self-correction: the very first two ollama-touching calls (AGENT-034's launch and
AGENT-037's launch) went out before I acquired `/tmp/vysted-r15-ollama.lock` — an
oversight, caught immediately after. No lock contention was observed (the lock was
free both times I checked before/after), and every ollama call from that point on
was wrapped in the lock. Noting it here rather than silently proceeding.

No regressions found in either set. findings/rc1-battery-0.json is `[]`.

COVERAGE (both sets): 16/16 ids raw; no raw: none.
