# Battery set-47: batch-10/W8-plugins-dock (candidate ace7dd76, shard rc1-battery-3)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-PLATFORM-012 | SSR-bundled candidate PluginRuntime + marketplace store disable/enable (the Plugin Manager toggle path) on vysted-lenses | disable -> state stopped, persisted enabled=false, host.detach("vysted-lenses") called; enable -> state active, enabled=true. Rendered click path pinned by PluginManagerPanel.test (not run here) | holds |
| R15-AGENT-057 | SSR-bundled real syncPluginAgents against live sidecar :52343 with a plugin AgentSpec carrying tool "not_a_real_tool" | rejects: "agent registration failed - custom:vysted-lenses-quant-tutor: HTTP 422 ... unknown tool ids"; second register 409 -> PUT, revised philosophy stored; cleanup removal ok | holds |

COVERAGE: 2/2 ids raw; no raw: none
