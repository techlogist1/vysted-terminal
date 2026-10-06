# set-30 — batch-8/W2-provider-readiness-host-actions (rc1-battery-16)

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-AGENT-028 | live POST /llm/keys/validate ollama/gemma3:4b (unpulled) and llama3.1:8b (pulled) on :52356 | `{ok:false, reason:model_not_pulled, detail:"gemma3:4b is not downloaded in Ollama (local) yet."}` / `{ok:true}` | holds |
| R15-AGENT-056 | source read of pinned vitest `arrange_layout's default is a layout-only reset (R15-AGENT-056)` + companion R15-LEAD-048 test | `{}`/`{pattern:"default"}` keep drawings+modules; an unrecognised pattern now fails outright (never resets) per LEAD-048, superseding the original repro's second case with a stricter guarantee | ci_pinned (host-actions.test.ts:1827, :1892) |
| R15-AGENT-081 | source read of pinned vitest `a highlight command spotlights that metric's row (R15-AGENT-081)` | exactly one `[data-highlighted]` row for a known metric | ci_pinned (EquityOverviewPanel.test.tsx:547) |
| R15-CODE-AGENT-006 | live GET /llm/providers on :52356 diffed against `sidecar/config/model_registry.json`; source read of `src/store/model-selection.ts` | 0 diffs across 8 providers; TS `REGISTRY_PROVIDERS` now `import`s the JSON file directly (model-selection.ts:14,32), not a hand copy | holds |
| R15-UI-013 | live POST /llm/keys/validate: openrouter/no-key, openai/fake-key, ollama unpulled/pulled | `not_configured` / `invalid` / `model_not_pulled` / `ok` — 4/7 rows match batch-8 exactly; unreachable/timeout rows confirmed in source (sidecar/routers/llm.py:105-125) not independently re-timed | holds |
| R15-UI-019 | live re-probe of the readiness endpoint the banner reads + pinned vitest `OnboardingBanner (R15-UI-019)` | readiness split (ok:true/false) matches component's showBanner branch; 2 pinned cases green by source | ci_pinned (OnboardingBanner.test.tsx:28) |
| R15-UI-049 | live re-probe of the readiness endpoint + pinned vitest `promoteKeyedProvider (R15-UI-049)` | same readiness split feeds promoteKeyedProvider's guard; 3 pinned cases match | ci_pinned (llm-providers.test.ts:10) |
| R15-UI-057 | live POST /llm/keys/validate with untrimmed fake key for openai/anthropic/groq/deepseek/gemini + source read of KeyEntryDialog.tsx:68 | all 5 return `invalid` "<Provider> rejected this key.", not the old transport error; `key.trim()` present before Save | holds |

COVERAGE: 8/8 ids raw; no raw: none.
