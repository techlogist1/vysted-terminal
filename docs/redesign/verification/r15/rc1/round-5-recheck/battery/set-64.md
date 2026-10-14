# batch-16/W1-one-writer-set (set-64) — rc1-battery-2, gate round 5-recheck

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. In-process (candidate's own
`sidecar/.venv`), only `adr_ratio._get` monkeypatched to sleep 20s then raise
`ConnectTimeout` (simulated unreachable EDGAR); `lookup("SIFY")` called twice — everything
else is the real code. The stale `sec:ads-ratio:SIFY:miss` cache row left by an earlier
probe run in this same data-dir copy was cleared from `data_cache.db` before the timed run
so the exception/timeout path actually fired (rather than short-circuiting on an
already-cached miss). Raw output: `raw/set-64/R15-LEAD-032.txt`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-LEAD-032 | In-process real code (`sidecar/services/adr_ratio.py`), only `adr_ratio._get` monkeypatched to sleep 20s then raise `ConnectTimeout`; `lookup("SIFY")` called twice | First call: `TimeoutError`, bounded at exactly 8.01s (`_TIMEOUT=8.0`); second call: 0.00s (served from the `:miss` cache, `_MISS_TTL=24h`). Code at `adr_ratio.py:141-146` confirms `data_cache.set(f"{key}:miss", {})` still runs unconditionally on the except path. | holds |

Matches round-4's own re-run of this exact entry at a prior candidate (`1006c6da`), read as
precedent, never as this round's evidence.

COVERAGE: 1/1 ids raw; no raw: none.
