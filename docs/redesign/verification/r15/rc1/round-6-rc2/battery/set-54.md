# Set: batch-11/W7-preferences (set-54) — candidate ace7dd76, sidecar :52345

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-087 | source check of settings store + SettingsPanel + failure codes (settings UI is GUI; drag-reorder/notice chip unexercised per batch verifier) | store has startLayout, paletteShowRecents, paletteSymbolScope; SettingsPanel "Fallback order" (:466); orderedProviders in llm-providers.ts/ChatSidebar/streaming.ts with test llm-providers.test.ts; sidecar errors.py emits provider_5xx/provider_402/ollama_not_running; behaviour pinned by vitest | ci_pinned |

COVERAGE: 1/1 ids raw; no raw: none
