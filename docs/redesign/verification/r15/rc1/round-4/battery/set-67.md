# batch-16/W1-one-writer-set (set-67) — rc1-battery-5, gate round 4

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad. Own sidecar :52345 for LEAD-032 (in-process, no live sidecar
needed for the patched-transport script). AGENT-090 driven through `scripts/r15/vy.py` against the same :52345
sidecar, provider ollama / llama3.1:8b, under the shared Ollama lock.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-090 | Live ollama re-run of the exact original prompt ("How many ordinary shares does one SIFY ADR represent, and what is SIFY's TTM revenue in USD?"). Tool called: `financial_statements` (ok). Final text: "The ADR-to-ordinary-share ratio is not available from this session's sources. 6 ordinary shares." | Core certified guard holds (no false 1:1/1:2 ratio, no fabricated tool-attribution framing); a trailing "6 ordinary shares." fragment states a true figure with no tool backing it -- the AGENT-090 guard covers `fundamentals` results but not this `financial_statements` path. This is the same no-tool-backing class as R15-LEAD-030/037/038, blocked_tier4 per DECISIONS 4.9-4.12 and the round-4 lead note ("no further rounds on this class... file as a concurrence note, never a fix round"). Filed as a concurrence note here, not a finding. | holds |
| R15-LEAD-032 | In-process real code (`sidecar/services/adr_ratio.py`), only `adr_ratio._get` monkeypatched to sleep 20s then raise `ConnectTimeout` (simulated unreachable EDGAR); `lookup("SIFY")` called twice | First call: `TimeoutError`, bounded at exactly 8.01s (`_TIMEOUT=8.0`); second call: 0.00s (served from the `:miss` cache, `_MISS_TTL=24h`). Code at adr_ratio.py:141-146 confirms `data_cache.set(f"{key}:miss", {})` now runs unconditionally on the except path. | holds |

COVERAGE: 2/2 ids raw; no raw: (none).

Note on R15-AGENT-090: per the round-4 lead note's standing rule for the "local model states a figure for a
subject with no ok tool call behind it" class (DECISIONS 4.9-4.12, also covering LEAD-030/037/038), this run's
residual leak is recorded here as a concurrence observation only -- not filed to findings[], not a regression of
the certified fix, and explicitly not a fix-round candidate.
