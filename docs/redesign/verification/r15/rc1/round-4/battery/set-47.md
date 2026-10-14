# set-47 — batch-10/W8-plugins-dock (rc1-battery-2, gate round 4)

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Both entries are frontend-only
(plugin manager panel / plugin runtime / plugin-agents fetch) with no live/curl-able
repro and no in-process JS/TS execution path available in this shard (candidate
`node_modules/.bin` carries `vitest` only, no `tsx`/`ts-node`; running vitest itself is
the heavy lane's job). Source was read directly to confirm the fix shape is present,
then the verdict defers to the pinned test per the battery rules.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-PLATFORM-012 | source check: `PluginManagerPanel.tsx` `handleToggle` | now calls `useMarketplaceStore.getState()` instead of the bare `runtime.loadPlugin`/`unloadPlugin` the register described as lying | ci_pinned (`src/components/PluginManagerPanel.test.tsx:118`, `src/lib/plugin-runtime.test.ts:585`) |
| R15-AGENT-057 | source check: `src/lib/plugin-agents.ts` | `response.ok` is now checked (:78) and a 409 triggers an explicit `PUT` (:67-69) | ci_pinned (`src/lib/plugin-agents.test.ts:57`) |

## Notes

- Neither entry has a sidecar/HTTP-observable repro distinct from the frontend logic
  itself (the sidecar router side of AGENT-057, `custom_agents.py`, already returned
  the right 4xx/409 pre-fix — the defect was the frontend never inspecting the
  response), so there is no curl/vy.py substitute for the vitest check.
- Source-level confirmation (grep excerpts above, full text in the raw files) shows
  the certified fix shape is present at the cited lines; this is a supporting check,
  not a substitute for actually running the pinned test.

COVERAGE: 2/2 ids raw; no raw: none.
