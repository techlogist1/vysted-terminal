# batch-8/W2-provider-readiness-host-actions (set-31) — rc1-battery-14 at ace7dd768c3b809b0e72b20b20cfc94eea2368bd

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-UI-013 | live POST /llm/keys/validate on :52354: openrouter no key, openai fake key, openai base_url dead port, ollama gemma3:4b / llama3.1:8b | not_configured / invalid / unreachable "Could not reach OpenAI" / model_not_pulled / ok (client-side timeout+Cancel UI is vitest-pinned) | holds |
| R15-AGENT-028 | live validate ollama gemma3:4b + /llm/chat on unpulled model (Ollama lock held) | validate reason model_not_pulled; chat error frame code model_not_pulled, action "Run `ollama pull ...`" (not "pick another model") | holds |
| R15-UI-057 | live validate with trailing space / newline key for openai, anthropic, groq, deepseek, gemini; KeyEntryDialog trim | all 10 -> reason invalid "<Provider> rejected this key."; KeyEntryDialog.tsx:68 key.trim() | holds |
| R15-UI-019 | React banner render (GUI/jsdom only); source + test names checked | banner gated on live readiness (useKeylessReadiness), dismissal persisted in store; OnboardingBanner.test.tsx "no banner for a working local model", "a dismissal survives a remount" | ci_pinned (src/components/OnboardingBanner.test.tsx) |
| R15-UI-049 | store logic; source + test names checked | promoteKeyedProvider exists (llm-providers.ts:92), wired in KeyEntryDialog.tsx:89 | ci_pinned (src/store/llm-providers.test.ts "promoteKeyedProvider (R15-UI-049)") |
| R15-CODE-AGENT-006 | live GET /llm/providers vs model_registry.json; TS imports | 8/8 providers, 0 diffs; model-selection.ts imports registry JSON, no hand copy | holds |
| R15-AGENT-056 | host-actions source (applyHostAction needs React/zustand harness); tests named | default/unknown arrange -> ws.resetLayout() (drawings+modules kept); unknown pattern fails "unrecognised layout"; gate text "drawings and modules kept" | ci_pinned (src/lib/host-actions.test.ts :1728-1729 / arrange_layout block) |
| R15-AGENT-055 | in-process catalog arrange_layout description; template tests | description no longer promises dual charts / heatmap / stats | ci_pinned (src/lib/layout-templates.test.ts planLayout cases) |
| R15-AGENT-081 | in-process catalog description + highlightMetric consumers | EquityOverviewPanel.tsx:864,867 now reads highlightMetric | ci_pinned (EquityOverviewPanel.test.tsx "a highlight command spotlights that metric's row (R15-AGENT-081)") |

COVERAGE: 9/9 ids raw; no raw: none
