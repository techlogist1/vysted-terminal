# newhigh / R15-AGENT-010 (rc1-verifier:17) — sync resolver on the event loop; explicit yf.Search timeout

Auditor: refutation audit round 2, group newhigh. Written 18:25 IST. Candidate code tree 4c6dfe8c (confirmed at a3275f64). Own sidecar on :52365, scratch data dir.

**Verdict: partial.** The loop-stall half is fixed and holds under fresh phrasings, live. The fix_shape's second clause ("pass an explicit yf.Search timeout") was never implemented. batch-3 PLAN.md §R15-AGENT-010 dropped it from the fix ("Use await asyncio.to_thread(...) and try/except in both"), and the certification only checked the loop. Measured at the candidate, a hung Yahoo still costs 31 s per call and saturates the process-wide default executor.

## 1. Register entry (read)
- Title: agent tools run the synchronous resolver on the event loop.
- Repro: resolve_symbol.py:70 calls resolve directly. "A master miss falls through to yf.Search (yfinance 1.3.0 defaults timeout=30 …; no explicit timeout passed), so the loop can stall 30 s."
- fix_shape: "Wrap both calls in asyncio.to_thread + try/except …, **and pass an explicit yf.Search timeout**."
- defect_class: sync-io-on-event-loop. Status fixed; closure c81d879 (Stage C batch 3).
- Certification: batch-3 VERDICTS.json lists it under `certified` ("max event-loop stall is 17 ms"). It appears in no not_certified list of any stage-c batch, and not in round-1 REFUTATION_AUDIT.json.

## 2. Verifier's refutation, re-run
`git grep -n "yf.Search" 4c6dfe8c -- sidecar/`
```
4c6dfe8c:sidecar/services/symbol_resolver.py:1574:        search = yf.Search(query, max_results=5, news_count=0)
4c6dfe8c:sidecar/tests/test_fundamentals_tool.py:324:        raise RuntimeError("yf.Search timed out")
```
`inspect.signature(yfinance.Search.__init__)` (yfinance 1.3.0 in sidecar/.venv) → `(…, session=None, timeout=30, raise_errors=True)`. The verifier's code-level claim holds: no timeout is passed, so the 30 s default applies.

## 3. The entry's own repro (loop stall), at the candidate
(a) The existing regression tests: `pytest -q tests/test_resolve_symbol_tool.py tests/test_fundamentals_tool.py -k "AGENT or slow or rais or loop or block"` → `2 passed, 22 deselected in 0.56s`.

(b) In-process race: a 5 ms ticker coroutine against `_resolve_symbol` (the agent tool handler), live network, fresh phrasings (scratch a010.py live):
```
'bharat heavy electricals share price': 1.61s status=unresolved resolved=None ticks=228 max_gap_ms=21
'what does kpit technologies do': 0.36s status=unresolved resolved=None ticks=51 max_gap_ms=21
'zyqvorn holdings plc': 0.93s status=disambiguate resolved=None ticks=84 max_gap_ms=21
```
(c) The same race against a HUNG upstream. A local proxy accepts the connection and never answers; the HTTPS_PROXY env is honoured by yfinance's curl_cffi session (scratch a010.py hang):
```
'qwxplorin metals corp': 31.07s status=disambiguate resolved=None ticks=4911 max_gap_ms=21
```
The loop stays live (max gap 21 ms over 4911 ticks), but the tool call takes **31.07 s**, which is exactly yfinance's default timeout.

(d) Live agent runs, llama3.1:8b under /tmp/vysted-r15-ollama.lock (acquired 18:22 IST, released 18:24 IST), on own :52365. /health was polled every 100 ms throughout. The tool calls below are read from the SSE transcript:
- run 1, "Find the listed ticker for Kaveri Seed Company and tell me its sector": tool_use resolve_symbol {"query":"Kaveri Seed Company","region":"IN"}, tool_result ok true. 397 health polls, max latency 92 ms.
- run 2, "which exchange symbol does the company qwxplorin metals trade under?" (a master miss → yf.Search): tool_use resolve_symbol {"query":"qwxplorin metals","region":"IN"}, tool_result ok true. 254 health polls, max latency 79 ms.
No /health stall during either run, so the event-loop half is fixed.

## 4. The unmet clause has a measurable cost at the candidate
In-process (scratch a010-sat.py), with the hung upstream and 12 concurrent distinct master-miss resolves (12 = the asyncio default-executor size on this M1: min(32, cpu+4)), one unrelated `asyncio.to_thread` call is timed after 1 s:
```
default executor workers: 12
unrelated to_thread waited 36.89s while 12 misses hang on yf.Search
```
The script's final `gather` of the 12 hung misses had still not returned a few minutes later, and I killed it at the end of the audit. The misses hold executor slots for at least 37 s (possibly longer if yfinance retries). Every `asyncio.to_thread` in the sidecar shares that executor: the router resolves, the quote and fundamentals fetches, compare_symbols. So with Yahoo hung, a burst of misses starves all of them for ~30-37 s. The 60 s `_LIVE_FAILURE_COOLDOWN_SECONDS` (symbol_resolver.py:131) only engages after the first Search has already burned its 30 s.

## 5. Classification reasoning
- Not verifier_error. The verifier named the exact clause from the entry's own fix_shape and repro, and the grep holds.
- Not regression_confirmed. The entry's headline defect, a loop stall, does not reproduce (sections 3b-3d).
- partial. The fix_shape names two parts, and one is unmet. The entry's repro text itself calls out "no explicit timeout passed".
- Severity of the residual: **medium**. It is no longer a loop stall. It is a 30 s tool latency plus shared-executor starvation, and only while Yahoo is hung.

## 6. Root cause
`sidecar/services/symbol_resolver.py:1574` `yf.Search(query, max_results=5, news_count=0)` passes no `timeout`, so it inherits yfinance 1.3.0's 30 s default.

## 7. Fix shape
Pass an explicit short timeout, e.g. `yf.Search(query, max_results=5, news_count=0, timeout=_LIVE_SEARCH_TIMEOUT_SECONDS)` with a module constant of ~5 s. That is well above the 0.4-2.2 s live misses measured here and in batch 3. A timeout raises, and the existing `except` already records it and sets the 60 s cooldown, so a hung Yahoo costs one 5 s call and not 30 s × every concurrent miss. Fix the resolve_symbol.py:52-53 comment ("up to 30 s") to match.

## 8. Acceptance test
- `sidecar/tests/test_symbol_resolver.py` (or test_resolve_symbol_tool.py): new `test_live_lookup_passes_an_explicit_short_search_timeout`. Monkeypatch `yfinance.Search` with a recorder class that stores its kwargs and exposes `quotes=[]`. Clear `_live_cache` and `_live_cooldown_until`, then call `symbol_resolver._live_lookup("zzqx nonexistent co", "IN")`. Assert `"timeout" in kwargs` and `kwargs["timeout"] <= 10`.
- Live re-proof: `PYTHONPATH=sidecar VYSTED_DATA_DIR=<scratch> sidecar/.venv/bin/python <scratch>/a010.py hang "qwxplorin metals corp"`. The hung-proxy race must finish in ≤ timeout+1 s (not 31 s) with max_gap_ms < 50. Then a010-sat.py: the unrelated to_thread must wait ≤ timeout+2 s.

## 9. Certification-failure count
Batch VERDICTS.json not_certified appearances: 0 (batch-3 lists it certified). Round-1 REFUTATION_AUDIT.json: not present (0). This gate refutation, verdict partial: 1. **Total 1**, from rc1-gate-round-2 only.

## 10. Side observation (not this entry)
Run 2's model answered "PALCO on the BSE" for the nonsense name "qwxplorin metals", after a resolve_symbol tool_result of ok true. The in-process race returned status=disambiguate for the similar "qwxplorin metals corp", so the model presumably picked a disambiguation candidate and stated it as fact. That is a model-grounding question for the agent group, not the resolver loop.
