# batch-28/W2-sonnet (rc1-battery-23, round 5)

Candidate: `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Own sidecar `127.0.0.1:52363`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DATA-113 | Live `GET /earnings/<SYM>/estimates` against `:52363` for WIT, PDD, NVO, TSM, AAPL, BIDU, INFY.NS and BABA (the last with `X-Vysted-Region: US`, needed because the default IN-region resolver otherwise maps the bare ticker `BABA` to an unrelated BSE issuer, "Baba Arts Limited" — a probe artifact, not a product defect). | WIT: `revenue_currency` INR (separate from the USD trading `currency`) — the register's mislabel is gone. PDD CNY, NVO DKK, TSM USD(eps)/TWD(revenue), AAPL USD, INFY.NS INR, BIDU currency null, BABA (US region) CNY — every one of batch-28's fresh-case values reproduces exactly. | holds |
| R15-RESEARCH-027 | Live agent run: `vy.py invoke copilot "research KPIT Technologies at normal depth..." --provider ollama --model llama3.1:8b` against `:52363` (Ollama lock held for the single call); source read of `sidecar/services/research/fast.py:105,119`. | `_WITNESS_LEG_TIMEOUT_S=6.0` and `_WEB_ROUND_TIMEOUT_S=8.0` unchanged. Live: the research tool's own execution record (`started_at`/`finished_at`) shows **8.54 s** wall time — under the 15 s target and in line with batch-28's fresh KPIT (6.7s)/Persistent (8.6s). The price and fundamentals legs hit the 6s box exactly (`latency_ms:6002`, dropped, "pulled 2/4 data sources"); the web round carries the 8s constant. (The vy.py-reported 81.5s is llama3.1:8b's own agent-loop overhead around the tool call, not the research tool's wall time — isolated via the `research:begin`/execution-record timestamps.) | holds |

COVERAGE: 2/2 ids raw; no raw: none.
