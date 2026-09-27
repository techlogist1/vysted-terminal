# rc1-battery-9 — set-46 (batch-10/W8-plugins-dock)

Candidate: `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. All three of this set were certified in
batch-10 through committed, register-id-tagged vitest tests (not a live sidecar path); per this
role's brief, the pinned test is named and cited rather than the vitest suite being run.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-AGENT-057 | Pinned tests: `src/lib/plugin-agents.test.ts:57` `"updates an already-registered agent via PUT on a 409 so a revised spec replaces it (R15-AGENT-057)"`, `:71` `"a rejected registration (422) marks the plugin errored with the reason (R15-AGENT-057)"`. Source check: `plugin-agents.ts` now inspects `response.ok`/`status` at the call sites the register evidence names. | Tests and the `response.ok`/`status` checks present unchanged in the candidate source. | ci_pinned |
| R15-CODE-PLATFORM-012 | Pinned tests: `src/components/PluginManagerPanel.test.tsx:118` `"toggling an active plugin off persists enabled:false and detaches it (R15-CODE-PLATFORM-012)"`; `src/lib/plugin-runtime.test.ts:585` `"disablePlugin persists enabled:false and detaches the plugin's contributions"`. | Present unchanged. | ci_pinned |
| R15-CODE-PLATFORM-014 | Pinned tests: `src/lib/plugin-runtime.test.ts:175` `"loadPlugin is idempotent, while reloadPlugin re-runs initialize with fresh secrets"`, `:138` `"loadPlugin honours a persisted disabled config (no initialize)"`. | Present unchanged. | ci_pinned |

COVERAGE: 3/3 ids raw.
