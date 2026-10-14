# Set: lows-P1/plugins (set-66) — rc1-battery-2 @ ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-PLATFORM-049 | code read of marketplace.ts remove() + test presence (keychain not drivable without GUI) | remove() calls deleteSecret for each grantedSecretId (marketplace.ts:193, :225); test marketplace.test.ts:107 "remove(vysted-news) deletes each granted secret; disable does not" | ci_pinned (src/store/marketplace.test.ts R15-CODE-PLATFORM-049) |
| R15-UI-089 | GET /news/sources/status with X-Vysted-Newsapi-Key bogus vs none; newsapi.org direct | bogus -> {"newsapi":"unauthorized"} (direct newsapi.org 401); none -> "absent"; store probeNewsApiKeyOrThrow (marketplace.ts:39) blocks save; test MarketplacePanel.test.tsx:155 | holds |
| R15-DOCS-022 | read docs/PLUGIN_DEVELOPMENT.md Roadmap vs source | "Shipped since v0.3.0" lists app.shell().sidecar pattern, node-editor consumer, syncPluginAgents with the picker noted as still missing (R15-AGENT-014); sources confirm | holds |

COVERAGE: 3/3 ids raw (battery/raw/set-66/); no raw: none
