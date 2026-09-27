# Regression battery — set-63 (batch-16/W1-one)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Own sidecar on `:52345`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-032 | In-process `services.adr_ratio.lookup("TSM")` twice against a real black-hole TCP listener (accepts, never answers; `HTTPS_PROXY`/`ALL_PROXY` pointed at it) — the same fresh-case shape batch-16 used | First `lookup("TSM")`: `TimeoutError`, returned `None` in 8.01s (the `_TIMEOUT=8.0` bound). Second `lookup("TSM")`: returned `None` in 0.00s, no new network call (the exception path now caches `f"{key}:miss"` before returning, `adr_ratio.py:150-151`) | holds |

COVERAGE: 1/1 ids raw.
