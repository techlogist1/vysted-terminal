# batch-8/W2-provider-readiness-host-actions

Candidate 4097dac4. Own sidecar :52346. Raw output: `raw/set-29/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-UI-013 | `curl -X POST :52346/llm/keys/validate -d '{"provider":"ollama","model":"gemma3:4b"}'` / `llama3.1:8b` / `{"provider":"openrouter"}` | `model_not_pulled`; `ok:true`; `not_configured` "No API key is set for OpenRouter." — matches register table exactly | holds |
| R15-AGENT-028 | same `/llm/keys/validate` calls as above | `{"ok":false,"reason":"model_not_pulled","detail":"gemma3:4b is not downloaded in Ollama (local) yet."}`; pulled model `ok:true` | holds |
| R15-UI-057 | `curl -X POST :52346/llm/keys/validate -d '{"provider":"openai","api_key":"sk-fake-not-real-key "}'` (trailing space); same for gemini | `{"ok":false,"reason":"invalid","detail":"OpenAI rejected this key."}` / "Google Gemini rejected this key." — never the pre-fix "transport error: Connection error." | holds |
| R15-UI-049 | `src/store/llm-providers.test.ts` ("a key saved while the keyless default is not ready becomes the default", "a keyless default that is ready is kept", "never replaces a keyed default the user chose") | Pinned tests present, source unchanged, not re-run (vitest banned) | ci_pinned |
| R15-UI-019 | `src/components/OnboardingBanner.test.tsx` ("no banner for a working local model with no cloud key", "shows when no key is set...", "a dismissal survives a remount") | Pinned tests present | ci_pinned |
| R15-CODE-AGENT-006 | `src/store/model-selection.test.ts` ("a registry default_model edit is the new default with no override, and a JSON-only model survives restore") | Pinned test present | ci_pinned |
| R15-AGENT-055 | `src/lib/layout-templates.test.ts` ("single-focus: just the chart, maximized", "compare: single chart-focused layout, maximized", "macro-scan: macro anchor + chart right + screener below", "arrange_layout describes the named templates (B2)") | Pinned tests present, cover the exact drift (tool description vs planLayout) named in the register | ci_pinned |
| R15-AGENT-056 | `src/store/workspace.test.ts` ("resetToDefaultLayout (Settings / menu) is the factory reset: drawings and module choices go") | Pinned test present | ci_pinned |
| R15-AGENT-081 | `src/store/equity-command.test.ts` ("carries highlightMetric through and drops it on the next plain issue") | Pinned test present | ci_pinned |

Summary: 3 holds (live `/llm/keys/validate` backend contract matches register exactly), 6 ci_pinned (frontend store/component logic; vitest suite not re-run per stall rule, source unchanged since batch-8 certification, tests present and named). No regressions.
