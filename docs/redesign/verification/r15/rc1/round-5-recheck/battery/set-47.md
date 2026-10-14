# batch-10/W8-plugins-dock (shard rc1-battery-9)

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Sidecar: source, `127.0.0.1:52355`.

Both entries are frontend React-component / fetch-wrapper behavior with no sidecar route
of their own (Plugin Manager toggle persistence; `syncPluginAgents` response.ok check).
Battery role may not run vitest or drive a GUI, so neither has a live probe of its own
repro from this role. batch-10/VERDICTS.md certified both only through committed vitest
files; verified those are real, git-tracked, permanent tests at this sha (not scratch),
read their bodies, and cross-checked the curl-able half of AGENT-057 (the sidecar 4xx
the frontend now inspects).

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-CODE-PLATFORM-012 | `git ls-files` + read `src/components/PluginManagerPanel.test.tsx:118` and `src/lib/plugin-runtime.test.ts:585` | both tests present, committed, asserting `enabled:false` persists + `detach`/`unloadPlugin` runs on toggle-off | ci_pinned: `PluginManagerPanel.test.tsx` — "toggling an active plugin off persists enabled:false and detaches it (R15-CODE-PLATFORM-012)"; `plugin-runtime.test.ts` — "disablePlugin persists enabled:false and detaches the plugin's contributions" |
| R15-AGENT-057 | `git ls-files` + read `src/lib/plugin-agents.test.ts:57,71`; source-read `src/lib/plugin-agents.ts:67-86` (`response.ok` now checked, failures collected); live `POST /custom-agents` with `tools:["not_a_real_tool_id"]` | test present, committed; source confirms `if (!response.ok) failures.push(...)` replacing the old catch-only path; live sidecar leg: HTTP 422 "unknown tool ids: ['not_a_real_tool_id']" | ci_pinned: `plugin-agents.test.ts` — "updates an already-registered agent via PUT on a 409 so a revised spec replaces it (R15-AGENT-057)" + "a rejected registration (422) marks the plugin errored with the reason (R15-AGENT-057)" |

Raw: `battery/raw/set-47/R15-CODE-PLATFORM-012.txt`, `R15-AGENT-057.txt`,
`R15-AGENT-057-post-response.json`.

COVERAGE: 2/2 ids raw; no raw: none.
