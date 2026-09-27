# batch-11/W7-preferences (shard rc1-battery-17)

Candidate: 9bc600ece2ce6343a6aa48f130d7620b1466bb98.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-087 | Pinned vitest across 5 files: `llm-providers.test.ts:42 describe("orderedProviders (R15-UI-087)")`, `settings.test.ts:199 "provider order, start layout and palette options round-trip; garbled values keep the current ones"`, `SettingsPanel.test.tsx:280 "the provider fallback order is live: the arrows reorder the rows and the store"`, `CommandPalette.test.tsx:186` (palette-option coverage), `PanelHost.test.tsx:55` ("Start with" preference on launch restore), `ChatSidebar.test.tsx:888` (fallback fires on a provider failure before any answer text, not after/on content error) + live source grep: `sidecar/services/errors.py:278 "insufficient_credit"`, `:469 code="provider_5xx"` confirm `PROVIDER_FAILURE_CODES` members exist server-side. | All 6 pinned tests present, unmodified, at the candidate sha; sidecar error codes the frontend fallback keys on exist. The register's own note that GUI drag-reorder/notice-chip feel is unexercised in a real window still applies — that slice is out of scope here (GUI is skipped this round). | ci_pinned |

Raw: `battery/raw/set-53/R15-UI-087.txt`.

COVERAGE: 1/1 ids raw; no raw: none.
