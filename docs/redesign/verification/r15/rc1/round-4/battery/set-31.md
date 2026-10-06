# set-31 — batch-8/W2-provider-readiness-host-actions (rc1-battery-12)

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad, sidecar :52352 (source, rc1-round-4-data-battery-12).

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-UI-013 | POST /llm/keys/validate: openrouter no-key, openai fake key, ollama gemma3:4b (unpulled), ollama llama3.1:8b (pulled) | not_configured / invalid / model_not_pulled / ok — exact match to batch-8 certification | holds |
| R15-AGENT-028 | POST /llm/keys/validate ollama+gemma3:4b -> model_not_pulled; live POST /llm/chat ollama+gemma3:4b (ollama-lock held) | validate: "gemma3:4b is not downloaded..."; chat SSE error frame code=model_not_pulled, action "Run `ollama pull gemma3:4b`..." — not the old "pick another model" text | holds |
| R15-UI-057 | POST /llm/keys/validate with trailing-space key for openai/anthropic/groq/deepseek/gemini | all return {"ok":false,"reason":"invalid","detail":"<Provider> rejected this key."} — no "transport error: Connection error." | holds |
| R15-UI-049 | static: src/store/llm-providers.ts:92-105 promoteKeyedProvider logic | matches certified promote/no-promote/never-displace-ready behavior; no HTTP surface | ci_pinned (src/store/llm-providers.test.ts) |
| R15-UI-019 | static: src/components/OnboardingBanner.tsx:26-49 gate logic | gates on defaultLaneNotReady, not just hasAnyKey; dismissal persisted | ci_pinned (src/components/OnboardingBanner.test.tsx) |
| R15-CODE-AGENT-006 | curl GET /llm/providers vs sidecar/config/model_registry.json vs src/store/model-selection.ts import | frontend statically imports the registry JSON (no hand-copied table); live values match JSON for all 8 providers | holds |
| R15-AGENT-055 | static: src/lib/layout-templates.ts planLayout (JSON-role-driven) | matches certified per-template role placement; no HTTP surface for catalog description | ci_pinned (src/lib/layout-templates.test.ts) |
| R15-AGENT-056 | static: src/lib/host-actions.ts:1579-1667 arrange_layout default/unknown branch | calls ws.resetLayout() (layout-only), not resetToDefaultLayout(); comment cites R15-AGENT-056 explicitly | ci_pinned (src/store/workspace.test.ts, src/lib/host-actions.test.ts) |
| R15-AGENT-081 | static: src/lib/host-actions.ts open_company_overview + EquityOverviewPanel.tsx:817-866 | highlightMetric consumed: setSpotlight/resolveMetric, data-highlighted row, querySelector scroll-to | ci_pinned (src/store/equity-command.test.ts) |

COVERAGE: 9/9 ids raw; no raw: none.
