# unplanned-5

Candidate 4097dac4. Own sidecar :52346. Raw output: `raw/set-50/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-RESEARCH-010 | `curl -X POST :52346/llm/keys/validate -d '{"provider":"openrouter","api_key":"sk-or-v1-R15CANARY-this-is-not-a-real-key"}'` (the register's exact canary key) | `{"ok":false,"reason":"invalid","detail":"OpenRouter rejected this key."}` — the pre-fix behavior was `{"ok":true}` for any string; now a real OpenRouter round-trip rejects the canary | holds |

Summary: 1 hold. No regressions.
