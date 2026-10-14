# lows-P1/llm-adapters (set-64), shard rc1-battery-9, candidate ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DOCS-014 | read CURRENT_STATE.md first-token section; recompute spend-ledger medians | section present with per-provider rows + sources, first-token honestly marked unmeasured (total-call proxy). Ledger has grown since the doc snapshot, so now-medians differ (openrouter 2.3 vs 3.5, openai 6.0 vs 3.8, ollama 59.6 vs 110) | holds |

COVERAGE: 1/1 ids raw; no raw: none
