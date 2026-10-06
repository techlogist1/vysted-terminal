# batch-11/W7-preferences (shard rc1-battery-17)

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-087 | Frontend preference-depth logic (provider fallback order, palette options, starter-cockpit picker) — no single sidecar endpoint; pinned vitest `llm-providers.test.ts:42` describe "orderedProviders (R15-UI-087)", `settings.test.ts:199` "provider order, start layout and palette options round-trip", `SettingsPanel.test.tsx:280` "the provider fallback order is live", plus `CommandPalette.test.tsx:186`, `PanelHost.test.tsx:55`, `ChatSidebar.test.tsx:836/888`. Supplementary backend check: the failure-code taxonomy the fallback keys on (`auth`, `provider_402`, `insufficient_credit`, `ollama_not_running`, `provider_5xx`, `network`) in `sidecar/services/errors.py`. | All 6 test files present at HEAD, unmodified, real assertions (e.g. `orderedProviders(["groq","anthropic"])` puts them first, rest in catalog order). Backend: all 6 failure codes still present in `errors.py` (lines 254/270/278/325/430-552), matching batch-11's cert ("PROVIDER_FAILURE_CODES ... all exist"). No regression on the register repro (a single default pick with no fallback) — the fallback chain, palette section and starter-cockpit picker are all still built and tested. | ci_pinned |

Raw: `battery/raw/set-55/R15-UI-087.txt`.

COVERAGE: 1/1 ids raw; no raw: none.
