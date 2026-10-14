# batch-18/W1-agent-runtime-citation-guard-history-trailer (set-69)

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Own sidecar `127.0.0.1:52347`, data dir
`rc1-round-4-data-battery-7`. 1 certified entry re-run under the local-model lock.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-LEAD-033 | Live two-turn: turn 1 `POST /copilot ... "What is AAPL's market cap?"` (ollama/llama3.1:8b, autonomy ask) via `scripts/r15/vy.py`; turn 2 sent with `options.history` built exactly as `historyForSend`/`withTrailer` produce it (`assistant` content = turn-1 answer + `"\n\n[tool steps: Using fundamentals]"`), prompt "Which tool gave you that market cap figure? Show exactly what it returned." | T1: "AAPL's market cap is USD 4.98T." (tool step: `fundamentals`). T2 assembled text: "The tool that provided the market cap figure was `fundamentals`. The result is as follows: `{"P/E": 25.4, "market_cap": USD 4.98T, ...}`" — **0 occurrences of `[tool steps` in the turn-2 text** (`"[tool steps" in t2` → `False`). The model answers from the trailer's *content*, never echoing the literal bracketed marker back as prose. | holds |

Raw output: `battery/raw/set-69/lead033-t1.{txt,jsonl}`, `lead033-history.json`,
`lead033-t2.{txt,jsonl}`, `_lead033_run.log`.

**Set result: 1/1 holds.**

COVERAGE: 16/16 ids raw; no raw: none.
