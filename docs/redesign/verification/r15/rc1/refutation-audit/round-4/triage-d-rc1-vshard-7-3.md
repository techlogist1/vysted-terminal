# triage-d / rc1-vshard-7:3 (tie R15-DATA-114) -> partial on R15-DATA-114

Audited 07:24 IST, HEAD bed3b166 (code == 01015033; `sidecar/services/option_chain.py` is untouched by the fix round).

## Entry
R15-DATA-114 (uncached-negative-probe). Title: "... because a negative probe (404/transport error) is never cached, so a transient error can 502 a request while a good cached day sits in cache". fix_shape: "... so a transient error on the today-probe doesn't shadow a good cached day". The fix docstring (`option_chain.py:144-151`) states the intent in general: "a transient upstream failure should not shadow a good cached day".

## Re-run of the shard's in-process repro at HEAD
`cp verifier/shard-7-evidence/oc114.py <scratch>; cd sidecar && TMPDIR=<scratch>/tmp PYTHONPATH=. ./.venv/bin/python <scratch>/oc114.py`
The script stubs `_fetch_fo_day` and `_ist_today` (Tue 2026-09-22), seeds `data_cache` and makes 3 calls to `fetch_latest_fo()` per scenario.
```
A (entry case) TUE=failed: seeded=['2026-09-21'] results=['2026-09-21', '2026-09-21', '2026-09-21'] network_calls=['2026-09-22']
B TUE=404: seeded=['2026-09-21'] results=['2026-09-21', '2026-09-21', '2026-09-21'] network_calls=['2026-09-22']
C fresh: TUE=404, MON=failed: seeded=['2026-09-18'] results=[None, None, None] network_calls=['2026-09-22', '2026-09-21', '2026-09-21', '2026-09-21']
D fresh: TUE=failed, MON uncached: seeded=['2026-09-18'] results=['2026-09-18', '2026-09-18', '2026-09-18'] network_calls=['2026-09-22']
```
Existing pins stay green: `pytest -q tests/test_option_chain.py tests/test_earnings_provider.py tests/test_macro_router.py` gives 49 passed, and no test covers scenario C.

## Code
`sidecar/services/option_chain.py:165-182`: only `day == today` consults and writes the `_probe_key` negative cache. For any older day, `if status == "failed": return None` (:181-182) ends the walk. `get_chain` then raises `OptionChainUnavailable` (:337/:342), which `routers/quant.py:87-88` turns into HTTP 502 "the NSE F&O bhavcopy could not be fetched". The older cached Friday is never reached, and Monday's failure is never cached, so every request re-probes it.
Real trigger: a daily user. On Monday morning the walk fetched and cached Friday (Monday's file was not out yet). On Tuesday morning today is a 404, as it always is before the close, and Monday is uncached. One NSE archive blip then 502s the chain panel and the agent's option-chain tool while Friday sits in cache. Each retry re-hits the failing upstream. Scenario D shows the code already serves an older cached day when today's probe fails, so C's `None` is inconsistent with the fix's own contract.

## Verdict
partial. The entry's stated repro (scenario A, a failed probe on today) holds at HEAD. The same class, an uncached negative probe letting a transient error shadow a cached day, still fails on the walk-back day. The title's general claim ("a negative probe ... is never cached, so a transient error can 502 a request while a good cached day sits in cache") is literally true for that day. This is the tied entry's class, not a new one.
Severity: medium, unchanged. The option chain (panel and agent tool) 502s for a common morning timing; retrying later works.
Certification failures: the register note has no clause. The baseline is 0. With this partial the count is 1.

End-of-audit (07:33 IST): own sidecar pid 90459 on :52435 stopped by pid (health now 000); no child processes; the repo working tree is unchanged apart from these output files.
