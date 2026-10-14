# batch-18/W1-agent-runtime-citation-guard (rc1-battery-7)

Candidate `4c6dfe8c`. Own sidecar on `:52347`. 1 certified entry re-run.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-033 | `POST /agents/copilot/invoke` with `options.history` hand-built exactly as `historyForSend`/`withTrailer` produce it (`user: "What is AAPL's market cap?"`, `assistant: "The market cap of AAPL is $4.90T.\n\n[tool steps: Using fundamentals]"`), turn-2 prompt "Which tool gave you that market cap figure? Show exactly what it returned." against `llama3.1:8b`/ollama, `autonomy=ask` | turn-2 assembled text contains **no** `[tool steps` substring (0 occurrences); the model instead made a fresh `price_data` tool call and reasoned from that (a model-quality tangent — it misnamed the earlier tool as `price_data` rather than `fundamentals` — not a trailer leak) | holds |

Raw output: `battery/raw/set-69/*`.
