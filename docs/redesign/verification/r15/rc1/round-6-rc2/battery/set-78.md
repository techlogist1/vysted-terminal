# lows-P2/frontend-panels-agent-shell (set-78) — rc1-battery-14 at ace7dd768c3b809b0e72b20b20cfc94eea2368bd

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-CODE-FRONTEND-022 | source check of CommandPalette.tsx agent row (design/latent finding; no runtime repro) | the `replace(/^agent:/, '')` strip is gone (0 hits); line 199-200 `if (item.agentSummary) setActiveAgent(item.agentSummary.id)` | ci_pinned (src/components/CommandPalette.test.tsx:281 "agent row selection uses agentSummary.id") |

COVERAGE: 1/1 ids raw; no raw: none
